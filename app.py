import csv
import hashlib
import hmac
import io
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
from atividade_pratica import atividade_pratica

st.set_page_config(page_title="Bioestatística | ANOVA e comparações múltiplas", page_icon="📊", layout="centered")

QUESTOES = [{'id': 1,
  'tipo': 'unica',
  'texto': 'Um estudo compara a força muscular média de três grupos independentes de adultos. Os resíduos '
           'são aproximadamente normais e as variâncias são semelhantes. Qual análise global é a mais '
           'apropriada?',
  'opcoes': ['ANOVA de uma via',
             'ANOVA de medidas repetidas',
             'Teste de Friedman',
             'Teste de Kruskal–Wallis'],
  'corretas': [0],
  'explicacao': 'A ANOVA de uma via avalia a igualdade das médias em três ou mais grupos independentes, sob '
                'os pressupostos descritos.'},
 {'id': 2,
  'tipo': 'unica',
  'texto': 'Os mesmos 20 voluntários realizam um teste de equilíbrio em três momentos. O desfecho é '
           'contínuo; as diferenças e os resíduos apresentam comportamento aproximadamente normal, e a '
           'esfericidade é atendida. Qual teste global é mais adequado?',
  'opcoes': ['Kruskal–Wallis',
             'ANOVA de uma via para medidas repetidas',
             'ANOVA de uma via para grupos independentes',
             'Teste de Dunn'],
  'corretas': [1],
  'explicacao': 'A ANOVA de medidas repetidas considera a correlação entre avaliações da mesma pessoa; '
                'esfericidade é um pressuposto importante para o F não corrigido.'},
 {'id': 3,
  'tipo': 'unica',
  'texto': 'Dezesseis pacientes recebem três avaliações da mesma escala ordinal de sintomas. Deseja-se '
           'verificar uma mudança global nas avaliações relacionadas. Qual teste escolher?',
  'opcoes': ['ANOVA de uma via', 'Kruskal–Wallis', 'Friedman', 'Tukey'],
  'corretas': [2],
  'explicacao': 'Friedman é um teste por postos para três ou mais condições relacionadas, aplicável a '
                'medidas ao menos ordinais.'},
 {'id': 4,
  'tipo': 'unica',
  'texto': 'Três grupos independentes recebem intervenções diferentes. O desfecho ordinal tem forte '
           'assimetria. Qual teste global é adequado para comparar os grupos?',
  'opcoes': ['Friedman', 'ANOVA de medidas repetidas', 'Teste t pareado', 'Kruskal–Wallis'],
  'corretas': [3],
  'explicacao': 'Kruskal–Wallis é uma alternativa baseada em postos para comparar três ou mais grupos '
                'independentes; não deve ser interpretado automaticamente como teste de medianas.'},
 {'id': 5,
  'tipo': 'vf',
  'texto': 'Após uma ANOVA de uma via significativa, o teste de Tukey pode ser utilizado para identificar '
           'quais pares de médias diferem, controlando o erro familiar das comparações por pares.',
  'opcoes': ['Verdadeiro', 'Falso'],
  'corretas': [0],
  'explicacao': 'Tukey HSD foi desenvolvido para comparações múltiplas de pares de médias após ANOVA de '
                'grupos independentes, sob pressupostos apropriados.'},
 {'id': 6,
  'tipo': 'unica',
  'texto': 'Depois de uma ANOVA de uma via significativa, um pesquisador quer comparar todos os pares de '
           'médias de quatro grupos independentes com variâncias aproximadamente iguais. Qual procedimento '
           'pós-hoc é o mais diretamente indicado?',
  'opcoes': ['Friedman', 'Tukey HSD', 'Dunn', 'Shapiro–Wilk'],
  'corretas': [1],
  'explicacao': 'Tukey HSD compara todos os pares de médias e controla o erro do conjunto de comparações. '
                'Para variâncias desiguais, seriam preferíveis alternativas como Games–Howell.'},
 {'id': 7,
  'tipo': 'unica',
  'texto': 'Um teste de Kruskal–Wallis foi significativo para quatro grupos independentes. Qual é um '
           'procedimento usual para investigar diferenças entre pares, com ajuste para múltiplas '
           'comparações?',
  'opcoes': ['Dunn com ajuste de Holm',
             'Tukey HSD sem ajuste',
             'ANOVA de medidas repetidas',
             'Teste t pareado sem ajuste'],
  'corretas': [0],
  'explicacao': 'O pós-hoc de Dunn compara pares por postos após Kruskal–Wallis e seus valores p podem ser '
                'ajustados por Holm ou Bonferroni.'},
 {'id': 8,
  'tipo': 'unica',
  'texto': 'Uma ANOVA de medidas repetidas com quatro momentos foi significativa, mas o teste de '
           'esfericidade indicou violação desse pressuposto. Qual é uma atitude apropriada?',
  'opcoes': ['Ignorar a esfericidade porque há quatro momentos',
             'Trocar automaticamente por Kruskal–Wallis',
             'Aplicar uma correção como Greenhouse–Geisser e planejar comparações pareadas ajustadas',
             'Usar Tukey HSD de grupos independentes sem considerar os participantes'],
  'corretas': [2],
  'explicacao': 'Greenhouse–Geisser ajusta os graus de liberdade do teste F na presença de violação da '
                'esfericidade. As comparações posteriores devem preservar o pareamento.'},
 {'id': 9,
  'tipo': 'vf',
  'texto': 'O ajuste de Bonferroni costuma ser menos conservador que o método sequencial de Holm para os '
           'mesmos valores p e a mesma família de hipóteses.',
  'opcoes': ['Verdadeiro', 'Falso'],
  'corretas': [1],
  'explicacao': 'Holm controla o erro familiar e é pelo menos tão poderoso quanto Bonferroni; Bonferroni não '
                'é menos conservador.'},
 {'id': 10,
  'tipo': 'multipla',
  'texto': 'Em comparações múltiplas, selecione TODAS as afirmações corretas.',
  'opcoes': ['O método de Holm ajusta comparações levando em conta a ordem dos valores p.',
             'Bonferroni pode ser empregado em comparações pareadas, desde que a família de testes seja '
             'definida.',
             'O teste de Dunn é um pós-hoc baseado em postos, utilizado após Kruskal–Wallis.',
             'O teste de Tukey HSD substitui a análise global de Friedman em dados pareados.'],
  'corretas': [0, 1, 2],
  'explicacao': 'Holm e Bonferroni controlam o erro familiar; Dunn é uma abordagem de comparações por postos '
                'para grupos independentes. Tukey HSD não substitui Friedman nem incorpora o pareamento.'}]

LETRAS = "ABCD"
DB_PATH = Path(os.environ.get("QUIZ_DB_PATH", "resultados_anova.sqlite3"))


def criar_banco():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_utc TEXT NOT NULL,
            nome TEXT NOT NULL,
            matricula TEXT NOT NULL,
            turma TEXT NOT NULL,
            nota INTEGER NOT NULL,
            total INTEGER NOT NULL,
            respostas_json TEXT NOT NULL
        )""")


def guardar_resultado(nome, matricula, turma, respostas, nota):
    criar_banco()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO resultados (data_utc, nome, matricula, turma, nota, total, respostas_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), nome, matricula, turma,
             nota, len(QUESTOES), json.dumps(respostas, ensure_ascii=False)),
        )


def formatar_opcao(q, indice):
    if q["tipo"] == "vf":
        return q["opcoes"][indice]
    return f"{LETRAS[indice]}) {q['opcoes'][indice]}"


def serializar_resposta(q, indices):
    return "; ".join(formatar_opcao(q, i) for i in sorted(indices)) if indices else "Sem resposta"


def resultado_para_csv(nome, matricula, turma, respostas):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Nome", nome])
    writer.writerow(["Matrícula", matricula])
    writer.writerow(["Turma", turma])
    writer.writerow(["Questão", "Resposta do aluno", "Gabarito", "Acertou"])
    for q in QUESTOES:
        atual = respostas[str(q["id"])]
        certo = atual == q["corretas"]
        writer.writerow([q["id"], serializar_resposta(q, atual), serializar_resposta(q, q["corretas"]), "Sim" if certo else "Não"])
    writer.writerow(["Nota", sum(respostas[str(q["id"])] == q["corretas"] for q in QUESTOES)])
    return buf.getvalue().encode("utf-8-sig")


def obter_senha():
    try:
        return st.secrets.get("SENHA_PROFESSOR", os.environ.get("SENHA_PROFESSOR", ""))
    except (FileNotFoundError, KeyError):
        return os.environ.get("SENHA_PROFESSOR", "")


st.title("📊 ANOVA, testes por postos e pós-hoc")
st.write("**10 questões • 1 ponto por questão • Bioestatística**")
st.caption("ANOVA de uma via · ANOVA de medidas repetidas · Friedman · Kruskal–Wallis · Holm · Bonferroni · Tukey · Dunn")

aba_aluno, aba_pratica, aba_professor = st.tabs(["🧑‍🎓 Questionário do aluno", "🔬 Atividade prática (CSV)", "👩‍🏫 Área do professor"])

with aba_aluno:
    if not st.session_state.get("concluido", False):
        st.info("Responda todas as questões e clique em **Enviar respostas**. O sistema exibirá a nota e o feedback após o envio.")
        with st.form("form_questionario"):
            nome = st.text_input("Nome completo *", max_chars=150)
            matricula = st.text_input("Matrícula ou identificador *", max_chars=60)
            turma = st.text_input("Turma (opcional)", max_chars=100)
            escolhas = {}
            for q in QUESTOES:
                st.divider()
                st.markdown(f"**Questão {q['id']} — 1 ponto**")
                st.write(q["texto"])
                if q["tipo"] == "multipla":
                    st.caption("Marque todas as alternativas que considerar corretas.")
                    escolhas[str(q["id"])] = [i for i in range(len(q["opcoes"])) if st.checkbox(formatar_opcao(q, i), key=f"q{q['id']}_{i}")]
                else:
                    opc = ["Selecione uma alternativa"] + [formatar_opcao(q, i) for i in range(len(q["opcoes"]))]
                    valor = st.radio("Resposta", opc, index=0, key=f"q{q['id']}", label_visibility="collapsed")
                    escolhas[str(q["id"])] = [] if valor == opc[0] else [opc.index(valor) - 1]
            enviado = st.form_submit_button("Enviar respostas e ver nota", type="primary", use_container_width=True)

        if enviado:
            if not nome.strip() or not matricula.strip():
                st.error("Preencha nome e matrícula/identificador.")
            elif any(not escolhas[str(q["id"])] for q in QUESTOES):
                st.error("Responda todas as 10 questões antes de enviar.")
            else:
                nota = sum(escolhas[str(q["id"])] == q["corretas"] for q in QUESTOES)
                try:
                    guardar_resultado(nome.strip(), matricula.strip(), turma.strip(), escolhas, nota)
                except sqlite3.Error as err:
                    st.warning(f"Não foi possível salvar na base local ({err}). Faça o download do resultado após o envio.")
                st.session_state.update({"concluido": True, "nome_aluno": nome.strip(),
                                         "matricula_aluno": matricula.strip(), "turma_aluno": turma.strip(),
                                         "respostas_aluno": escolhas, "nota_aluno": nota})
                st.rerun()
    else:
        nota = st.session_state["nota_aluno"]
        st.success("Questionário concluído!")
        st.metric("Sua nota", f"{nota} / {len(QUESTOES)}", f"{nota / len(QUESTOES) * 100:.0f}% de acertos", delta_color="off")
        st.write(f"**Aluno(a):** {st.session_state['nome_aluno']}")
        st.subheader("Correção comentada")
        for q in QUESTOES:
            dada = st.session_state["respostas_aluno"][str(q["id"])]
            correto = dada == q["corretas"]
            with st.expander(f"{'✅' if correto else '❌'} Questão {q['id']} — {'Acertou' if correto else 'Errou'}"):
                st.write(q["texto"])
                st.write("**Sua resposta:**", serializar_resposta(q, dada))
                st.write("**Resposta correta:**", serializar_resposta(q, q["corretas"]))
                st.write("**Explicação:**", q["explicacao"])
        st.download_button("📥 Baixar meu resultado (CSV)",
                           resultado_para_csv(st.session_state["nome_aluno"], st.session_state["matricula_aluno"],
                                              st.session_state["turma_aluno"], st.session_state["respostas_aluno"]),
                           file_name="meu_resultado_anova.csv", mime="text/csv", use_container_width=True)
        if st.button("Iniciar uma nova tentativa neste navegador"):
            for chave in list(st.session_state):
                if chave.startswith("q") or chave in {"concluido", "nome_aluno", "matricula_aluno", "turma_aluno", "respostas_aluno", "nota_aluno"}:
                    del st.session_state[chave]
            st.rerun()

with aba_pratica:
    if st.session_state.get("concluido", False):
        atividade_pratica()
    else:
        st.info("Conclua primeiro as 10 questões do questionário para liberar a atividade prática.")

with aba_professor:
    senha_configurada = obter_senha()
    if not senha_configurada:
        st.warning("A área do professor está desativada. Configure SENHA_PROFESSOR em .streamlit/secrets.toml ou como variável de ambiente.")
    else:
        senha = st.text_input("Senha do professor", type="password", key="senha_digitada")
        if senha and hmac.compare_digest(senha, str(senha_configurada)):
            try:
                criar_banco()
                with sqlite3.connect(DB_PATH) as conn:
                    df = pd.read_sql_query("SELECT data_utc, nome, matricula, turma, nota, total, respostas_json FROM resultados ORDER BY id DESC", conn)
            except sqlite3.Error as err:
                st.error(f"Falha ao abrir o banco de resultados: {err}")
            else:
                st.metric("Tentativas registradas", len(df))
                if not df.empty:
                    st.metric("Nota média (tentativas)", f"{df['nota'].mean():.2f} / {len(QUESTOES)}")
                    st.dataframe(df.drop(columns=["respostas_json"]), hide_index=True, use_container_width=True)
                    st.download_button("📥 Baixar respostas da turma (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                                       "respostas_turma.csv", "text/csv", use_container_width=True)
                    acertos = []
                    for q in QUESTOES:
                        n = sum(json.loads(row)[str(q["id"])] == q["corretas"] for row in df["respostas_json"])
                        acertos.append({"Questão": f"Q{q['id']}", "Percentual de acertos": round(100 * n / len(df), 1)})
                    st.subheader("Percentual de acertos por questão")
                    st.bar_chart(pd.DataFrame(acertos).set_index("Questão"))
                    st.caption("Os percentuais consideram tentativas, não alunos únicos. Tentativas repetidas permanecem registradas.")
                else:
                    st.info("Ainda não existem respostas registradas neste banco de dados.")
        elif senha:
            st.error("Senha incorreta.")

st.divider()
st.caption("Aviso para o professor: os resultados são armazenados em SQLite local. Em hospedagem gratuita do Streamlit Community Cloud, o armazenamento em disco pode ser perdido após reinicializações ou recriações do aplicativo. Para coleta permanente, use um banco de dados externo ou solicite aos alunos os CSVs individuais. Informe aos alunos a finalidade da coleta e limite o acesso aos dados pessoais.")
