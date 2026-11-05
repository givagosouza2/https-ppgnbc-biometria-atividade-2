import io
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.stats as stats
import streamlit as st
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.anova import AnovaRM
from statsmodels.stats.multicomp import pairwise_tukeyhsd
import scikit_posthocs as sp


def descritiva(v):
    s=pd.Series(v).dropna().astype(float)
    n=len(s)
    if not n: return {}
    return dict(n=n, media=s.mean(), mediana=s.median(), dp=s.std(ddof=1), variancia=s.var(ddof=1),
                erro_padrao=s.sem(), minimo=s.min(), Q1=s.quantile(.25), Q3=s.quantile(.75),
                maximo=s.max(), amplitude=s.max()-s.min(), IQR=s.quantile(.75)-s.quantile(.25),
                assimetria=stats.skew(s,bias=False) if n>=3 else np.nan,
                curtose_excesso=stats.kurtosis(s,fisher=True,bias=False) if n>=4 else np.nan)


def shapiro(v):
    v=np.asarray(pd.Series(v).dropna(),float)
    if len(v)<3 or np.unique(v).size<3: return 'Indisponível (n<3 ou sem variação suficiente)'
    if len(v)>5000: return 'n>5000: Shapiro–Wilk não executado (limitação para interpretação do p)'
    try:
        r=stats.shapiro(v)
        return f'W={r.statistic:.4f}; p={r.pvalue:.4g}'
    except ValueError as e: return f'Não calculável: {e}'


def grafico(v, nome):
    a=np.asarray(pd.Series(v).dropna(),float)
    if len(a)<3: return
    fig,ax=plt.subplots(1,2,figsize=(11,3.7))
    ax[0].hist(a,bins='auto',edgecolor='black',alpha=.7)
    ax[0].set(title=f'Histograma: {nome}',xlabel='Valor',ylabel='Frequência')
    if len(np.unique(a))>1: stats.probplot(a,dist='norm',plot=ax[1])
    else: ax[1].text(.5,.5,'Variável constante',ha='center',va='center')
    ax[1].set_title('Q-Q plot (normal)')
    fig.tight_layout(); st.pyplot(fig); plt.close(fig)


def csv_bytes(df): return df.to_csv(index=False).encode('utf-8-sig')


def arquivo_csv():
    up=st.file_uploader('Carregue o arquivo CSV',type='csv',key='anova_csv')
    if up is None: return None
    raw=up.getvalue()
    if len(raw)>15_000_000:
        st.error('Arquivo acima do limite didático de 15 MB.'); return None
    separador=st.selectbox('Separador',['Automático',',',';','Tabulação'],key='sep_anova')
    decimal=st.selectbox('Separador decimal',['.',','],key='dec_anova')
    try:
        kwargs=dict(sep=None,engine='python') if separador=='Automático' else dict(sep='\t' if separador=='Tabulação' else separador)
        df=pd.read_csv(io.BytesIO(raw),decimal=decimal,**kwargs)
        if df.empty: st.warning('CSV vazio.'); return None
        st.write('Prévia dos dados'); st.dataframe(df.head(12),use_container_width=True)
        return df
    except Exception as e: st.error(f'Erro ao ler CSV: {e}'); return None


def independentes(df):
    st.markdown('### Três ou mais grupos independentes')
    cat=st.selectbox('Coluna que identifica os grupos',df.columns,key='grupo_anova')
    vars_num=[c for c in df.columns if c!=cat and pd.api.types.is_numeric_dtype(df[c])]
    if not vars_num: st.warning('É necessária uma coluna numérica e outra com os grupos.'); return
    resp=st.selectbox('Variável quantitativa de resposta',vars_num,key='valor_anova')
    dados=df[[cat,resp]].dropna().copy(); dados=dados.rename(columns={cat:'grupo',resp:'valor'})
    dados['grupo']=dados['grupo'].astype(str)
    grupos={x:sub['valor'].to_numpy(dtype=float) for x,sub in dados.groupby('grupo',sort=True)}
    if len(grupos)<3: st.warning('É necessário haver ao menos três grupos com observações válidas.'); return
    if any(len(v)<2 for v in grupos.values()): st.warning('Cada grupo precisa de pelo menos duas observações.'); return
    st.write('**Estatística descritiva**')
    desc=pd.DataFrame([{'grupo':g,**descritiva(v)} for g,v in grupos.items()])
    st.dataframe(desc,use_container_width=True,hide_index=True)
    st.download_button('Baixar descritivas (CSV)',csv_bytes(desc),'descritivas_grupos.csv','text/csv')
    st.write('**Normalidade (Shapiro–Wilk por grupo)**')
    st.dataframe(pd.DataFrame([{'Grupo':g,'Shapiro–Wilk':shapiro(v)} for g,v in grupos.items()]),hide_index=True)
    for g,v in grupos.items():
        with st.expander(f'Gráficos: {g}'):
            grafico(v,g)
    try:
        lev=stats.levene(*grupos.values(),center='median')
        st.write(f'**Homocedasticidade (Levene/Brown–Forsythe):** F={lev.statistic:.4g}; p={lev.pvalue:.4g}')
    except ValueError: st.warning('Não foi possível calcular Levene.')
    st.caption('Shapiro–Wilk e Levene oferecem evidências, não garantias, dos pressupostos. A ANOVA considera também resíduos, independência e desenho amostral.')
    teste=st.radio('Teste global a executar',['ANOVA de uma via','Kruskal–Wallis'],horizontal=True,key='teste_ind')
    adjust=st.selectbox('Ajuste para comparações múltiplas',['Holm','Bonferroni'],key='adj_ind')
    method={'Holm':'holm','Bonferroni':'bonferroni'}[adjust]
    if teste=='ANOVA de uma via':
        try:
            f=stats.f_oneway(*grupos.values())
            st.write(f'**ANOVA:** F={f.statistic:.4g}, p={f.pvalue:.4g}')
            st.write('**Pós-hoc: Tukey HSD**')
            tuk=pairwise_tukeyhsd(dados.valor,dados.grupo)
            st.text(str(tuk.summary()))
            st.caption('Tukey HSD já controla o erro familiar para todos os pares; não é necessário aplicar Holm ou Bonferroni por cima dele. A seleção de ajuste acima se aplica ao pós-hoc de Dunn.')
            # Resíduos centrados pelas médias dos grupos
            resid=dados.valor-dados.groupby('grupo').valor.transform('mean')
            st.write('**Normalidade dos resíduos:**',shapiro(resid))
            with st.expander('Histograma e Q-Q plot dos resíduos'):
                grafico(resid,'resíduos ANOVA')
        except Exception as e: st.error(f'ANOVA não calculável: {e}')
    else:
        try:
            r=stats.kruskal(*grupos.values())
            st.write(f'**Kruskal–Wallis:** H={r.statistic:.4g}, p={r.pvalue:.4g}')
            st.write(f'**Pós-hoc de Dunn, ajuste {adjust}**')
            matriz=sp.posthoc_dunn(dados,val_col='valor',group_col='grupo',p_adjust=method)
            st.dataframe(matriz,use_container_width=True)
            st.download_button('Baixar matriz Dunn (CSV)',csv_bytes(matriz.rename_axis('grupo').reset_index()),'dunn.csv','text/csv')
            st.caption('Kruskal–Wallis e Dunn usam postos. Diferenças nas distribuições não equivalem necessariamente a diferenças de medianas.')
        except Exception as e: st.error(f'Kruskal–Wallis/Dunn não calculável: {e}')


def repetidas(df):
    st.markdown('### Três ou mais condições relacionadas')
    st.caption('Formato esperado: uma linha por participante, com as avaliações em colunas numéricas distintas.')
    id_col=st.selectbox('Identificador do participante',['Gerar identificador pela linha']+list(df.columns),key='id_rm')
    available=[c for c in df.columns if c!=id_col and pd.api.types.is_numeric_dtype(df[c])]
    cols=st.multiselect('Colunas das condições ou momentos (pelo menos três)',available,default=available[:3],key='cols_rm')
    if len(cols)<3: st.info('Selecione pelo menos três condições.');return
    x=df[cols].apply(pd.to_numeric,errors='coerce')
    n0=len(x); x=x.dropna()
    if len(x)<3: st.warning('São necessários pelo menos três participantes com todas as medidas.');return
    if id_col!='Gerar identificador pela linha':
        ids=df.loc[x.index,id_col]
        if ids.isna().any() or ids.duplicated().any(): st.error('Identificadores ausentes ou duplicados.');return
    else: ids=pd.Series(range(1,len(x)+1),index=x.index)
    if len(x)<n0: st.warning(f'Análise por casos completos: {n0-len(x)} linha(s) removidas por valores ausentes.')
    st.dataframe(pd.DataFrame([{'condicao':c,**descritiva(x[c])} for c in cols]),hide_index=True,use_container_width=True)
    st.write('**Normalidade por condição (descritiva):**')
    for c in cols:
        st.write(f'{c}: {shapiro(x[c])}')
        with st.expander(f'Histograma e Q-Q: {c}'):
            grafico(x[c],c)
    st.caption('Para ANOVA de medidas repetidas, examine principalmente resíduos/contrastes, esfericidade e independência entre participantes; a normalidade de cada coluna isoladamente é insuficiente.')
    teste=st.radio('Teste global a executar',['ANOVA de uma via para medidas repetidas','Friedman'],horizontal=True,key='teste_rm')
    adj=st.selectbox('Correção dos valores p das comparações pareadas',['Holm','Bonferroni'],key='adj_rm')
    method={'Holm':'holm','Bonferroni':'bonferroni'}[adj]
    if teste=='ANOVA de uma via para medidas repetidas':
        try:
            long=x.copy();long['_id']=ids.to_numpy()
            long=long.melt(id_vars='_id',var_name='condicao',value_name='valor')
            model=AnovaRM(long,depvar='valor',subject='_id',within=['condicao']).fit()
            st.text(str(model.anova_table))
            import pingouin as pg
            sph=pg.sphericity(x[cols])
            st.write(f'**Esfericidade (Mauchly):** W={sph.W:.4g}; p={sph.pval:.4g}')
            rm=pg.rm_anova(data=long,dv='valor',within='condicao',subject='_id',correction=True,detailed=True)
            st.write('**ANOVA com informação sobre correção Greenhouse–Geisser:**')
            st.dataframe(rm,use_container_width=True,hide_index=True)
            st.caption('Se a esfericidade for violada, interprete o p corrigido (p-GG-corr), quando disponível; a análise não substitui a avaliação das características dos resíduos.')
        except Exception as e: st.error(f'ANOVA de medidas repetidas não calculável: {e}');return
    else:
        try:
            r=stats.friedmanchisquare(*(x[c] for c in cols))
            st.write(f'**Friedman:** χ²={r.statistic:.4g}; p={r.pvalue:.4g}')
        except Exception as e: st.error(f'Friedman não calculável: {e}');return
    linhas=[]
    for a,b in itertools.combinations(cols,2):
        try:
            if teste=='Friedman':
                r=stats.wilcoxon(x[a],x[b],zero_method='wilcox',alternative='two-sided')
                tname='Wilcoxon pareado'; estat=r.statistic; pv=r.pvalue
            else:
                r=stats.ttest_rel(x[a],x[b]);tname='t pareado';estat=r.statistic;pv=r.pvalue
            linhas.append(dict(par=f'{a} × {b}',teste=tname,estatistica=estat,p_bruto=pv))
        except ValueError:
            linhas.append(dict(par=f'{a} × {b}',teste='Não calculável',estatistica=np.nan,p_bruto=np.nan))
    res=pd.DataFrame(linhas)
    valid=res.p_bruto.notna()
    if valid.any():
        res.loc[valid,'p_ajustado']=multipletests(res.loc[valid,'p_bruto'],method=method)[1]
    st.write(f'**Comparações pareadas exploratórias com correção {adj}:**')
    st.dataframe(res,use_container_width=True,hide_index=True)
    st.download_button('Baixar comparações (CSV)',csv_bytes(res),'comparacoes_pareadas.csv','text/csv')
    st.caption('Essas comparações são testes pareados com ajuste de multiplicidade. Não são o teste de Dunn, que é destinado a postos entre grupos independentes, nem Tukey HSD.')


def atividade_pratica():
    st.header('🔬 Laboratório prático — ANOVA e testes por postos')
    st.write('Carregue um CSV, investigue a distribuição e os pressupostos, execute o teste global e interprete as comparações múltiplas.')
    df=arquivo_csv()
    if df is None:return
    tipo=st.radio('Qual é o delineamento do estudo?',['Grupos independentes','Condições repetidas nos mesmos participantes'],key='tipo_pratica_anova')
    if tipo=='Grupos independentes': independentes(df)
    else: repetidas(df)
    st.divider()
    st.subheader('Atividade de interpretação do discente')
    perguntas=[
        '1. Descreva a tendência central, dispersão, assimetria e curtose das condições ou grupos.',
        '2. O que sugerem o histograma, o Q-Q plot e o teste de Shapiro–Wilk? Quais são as limitações dessas evidências?',
        '3. Que pressupostos são pertinentes para este delineamento (incluindo homocedasticidade ou esfericidade, quando cabível)?',
        '4. Qual teste global é mais adequado, qual a hipótese nula e qual a interpretação do resultado?',
        '5. Quais comparações múltiplas são apropriadas? Explique a finalidade de Holm, Bonferroni, Tukey ou Dunn neste caso.'
    ]
    resps=[]
    for i,q in enumerate(perguntas):
        resps.append(st.text_area(q,key=f'resp_anova_{i}',height=90))
    rel='ATIVIDADE PRÁTICA — ANOVA E COMPARAÇÕES MÚLTIPLAS\n\n'+'\n\n'.join(f'{q}\n{r}' for q,r in zip(perguntas,resps))
    st.download_button('📥 Baixar minhas respostas (.txt)',rel.encode('utf-8-sig'),'respostas_atividade_anova.txt',mime='text/plain')
    st.info('A escolha do teste e a interpretação das respostas abertas devem ser discutidas ou avaliadas pelo professor; não há correção automática dessas respostas.')
