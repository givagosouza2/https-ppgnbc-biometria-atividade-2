# Questionário Streamlit — ANOVA e comparações múltiplas

Inclui 10 questões com correção automática e laboratório CSV de três ou mais grupos/condições.

## Instalar e executar

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

## Estruturas de CSV

- **Independentes:** uma coluna `grupo` (A/B/C/...) e outra numérica `valor`; uma linha por observação. Veja `exemplo_grupos.csv`.
- **Repetidas:** uma linha por participante, colunas `id`, `antes`, `durante`, `depois` (ou outras condições). Veja `exemplo_repetidas.csv`.

No laboratório, as análises são calculadas sobre as variáveis escolhidas. O discente pode baixar descrições e comparações, interpretar pressupostos e enviar a atividade aberta ao professor.

## Pormenores estatísticos

- Independentes: ANOVA clássica; Q-Q e Shapiro dos resíduos, Shapiro por grupo, Brown–Forsythe, Tukey HSD. Para variâncias desiguais, considerar **Welch ANOVA e Games–Howell** fora deste módulo.
- Independentes não paramétricos: Kruskal–Wallis e pós-hoc Dunn com Holm ou Bonferroni.
- Repetidas: ANOVA de medidas repetidas; Mauchly, correção Greenhouse–Geisser quando aplicável, pós-hoc t pareado Holm/Bonferroni.
- Repetidas não paramétricas: Friedman e pós-hoc Wilcoxon pareado com Holm/Bonferroni.
- Requer pelo menos 3 grupos/condições; a inferência pressupõe independência entre unidades experimentais.
- Resultados abertos têm correção manual pelo professor.

## Área do professor e privacidade

Configure `SENHA_PROFESSOR` via variável de ambiente ou em `.streamlit/secrets.toml`:

```toml
SENHA_PROFESSOR = "SUBSTITUA_POR_UMA_SENHA_FORTE"
```

Sem essa configuração, a área do professor permanece desativada. As respostas são guardadas em **SQLite local**, sem durabilidade garantida no Streamlit Community Cloud. Para aplicações reais com turma, implemente banco persistente e controles de acesso. Evite enviar dados sensíveis de pesquisas reais à plataforma sem autorização adequada.
