# DataPulse — radar de tendências tech

Pipeline de dados que coleta discussões públicas de tecnologia, processa o texto com NLP e identifica quais assuntos estão ganhando tração. Termina em um dashboard Streamlit.

## O problema

Acompanhar o que está em alta em tecnologia é trabalhoso: a discussão está espalhada entre HackerNews, Reddit, blogs e fóruns, e muda em poucos dias. A pergunta que o projeto responde é "o que a comunidade está discutindo hoje que não estava há três dias" — não "quais são as palavras mais comuns".

## Arquitetura

```
EXTRACT              TRANSFORM             LOAD
HackerNews API  -->  limpeza          -->  SQLite (artigos + trends)
Reddit JSON          tokenização           CSV processado
                     stopwords             JSON bruto
                     lematização
                     TF-IDF
                          |
                          v
                     ANALYTICS
                     frequência de palavras
                     tendência diária
                     clusters KMeans
                     taxa de crescimento
                     insights automáticos
                          |
                          v
                     DASHBOARD STREAMLIT
```

Cada módulo (`collect`, `process`, `analyze`) roda de forma independente, o que facilita testar e refazer só uma etapa.

## Coleta (`src/collect.py`)

Dois coletores, nenhum exige chave de API.

HackerNews, pela REST API pública do Firebase:

```
GET https://hacker-news.firebaseio.com/v0/topstories.json     # ids dos top 100
GET https://hacker-news.firebaseio.com/v0/item/{id}.json      # detalhe de cada post
```

Reddit, pelo endpoint JSON público:

```
GET https://www.reddit.com/r/{subreddit}/hot.json?limit=50
# subreddits: technology, programming, MachineLearning, datascience, artificial
```

Todo dado bruto é salvo em `data/raw/` como JSON com timestamp. Se a análise mudar, os dados originais continuam disponíveis para refazer.

## NLP (`src/process.py`)

O texto passa por sete etapas antes de ser analisado:

```
texto bruto
  remove_urls()          elimina "https://..."
  remove_html_tags()     elimina "<p>", "&amp;"
  .lower()               "AI" e "ai" viram o mesmo token
  remove_special_chars() mantém letras e números
  word_tokenize()        NLTK, quebra em palavras
  filtra stopwords       remove "the", "is", "was", "a"
  lemmatize()            WordNet: "running" -> "run"
tokens prontos
```

Lematização em vez de stemming: o stemming é mais agressivo e deforma palavras ("caring" vira "car"). A lematização usa o dicionário do WordNet e devolve formas legíveis, o que importa porque essas palavras aparecem no dashboard.

## Detecção de tendências (`src/analyze.py`)

Além de contar palavras, o sistema calcula a taxa de crescimento entre dois períodos:

```
crescimento = (freq_recente - freq_anterior) / freq_anterior * 100
```

Isso separa palavra popular (aparece muito, mas estável) de palavra em tendência (aparece mais do que antes). Numa execução de 08/05/2026: `agent` +2900%, `game` +4000% (lançamento do Switch 2), `model` -7% — dominante, mas sem crescimento.

## Clusterização com TF-IDF + KMeans

O clustering agrupa os artigos em temas sem nenhum rótulo manual.

No TF-IDF, palavra que aparece muito em poucos artigos ganha peso alto (é discriminativa) e palavra que aparece em todos ganha peso baixo. Cada artigo vira um vetor de 500 dimensões. O KMeans agrupa os vetores em N clusters (padrão 6) e, para cada um, as palavras de maior peso no centróide viram o rótulo.

Resultado de 08/05/2026:

| Cluster | Palavras-chave | Artigos |
|---|---|---|
| Model | model, data, problem, work, paper, claude | 308 (93%) |
| Agent | agent, workflow, cli, prompt, need, human | 9 (2,7%) |
| School | school, related, student, final, may, find | 6 (1,8%) |
| Coding | coding, agent, trust, show, field, across | 4 (1,2%) |
| Session | session, user, language, week, always | 2 (0,6%) |
| Math | math, transformer, find, model, graph, error | 1 (0,3%) |

A concentração em um cluster gigante mostra um limite do KMeans com k fixo: quando o corpus é homogêneo, ele não força separação real.

## Insights automáticos

A partir dos números, o sistema monta frases prontas para o dashboard:

```
'Agent' cresceu 2900% nos últimos dias
'Game' cresceu 4000% nos últimos dias
Palavra mais mencionada: 'Model', com 147 ocorrências
Tópico dominante: 'Model', com 308 artigos agrupados
'Post' caiu 40% nos últimos dias
```

## Stack

| Camada | Ferramenta | Versão |
|---|---|---|
| Linguagem | Python | 3.14 |
| Dados | Pandas, NumPy | — |
| NLP | NLTK | 3.9 |
| ML | scikit-learn | 1.8 |
| Dashboard | Streamlit | 1.57 |
| Gráficos | Plotly | 6.7 |
| Nuvem de palavras | wordcloud | 1.9 |
| Banco | SQLite | nativo |
| HTTP | requests | 2.33 |

SQLite e não PostgreSQL porque é análise local: zero setup para quem clonar. A troca é uma linha em `utils.py`.

## Estrutura

```
data-pulse/
├── data/
│   ├── raw/            JSONs brutos das APIs, com timestamp
│   ├── processed/      CSVs com tokens processados
│   └── datapulse.db    SQLite: artigos + trends
├── notebooks/          análises exploratórias
├── src/
│   ├── utils.py        logging, banco, helpers
│   ├── collect.py      HackerNews + Reddit
│   ├── process.py      limpeza, tokenização, lematização
│   └── analyze.py      frequência, trends, TF-IDF, KMeans
├── dashboard/
│   └── app.py          dashboard Streamlit
├── requirements.txt
└── .gitignore
```

## Como rodar

Requisitos: Python 3.10+ e Git.

```bash
git clone https://github.com/Isapinhoo/data-pulse.git
cd data-pulse

python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
# source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt

python src/collect.py            # ~350 artigos em ~2 min
python src/process.py            # tokeniza e lematiza
python src/analyze.py            # clusters e insights

streamlit run dashboard/app.py   # http://localhost:8501
```

Sem chaves de API: o projeto usa só endpoints públicos.

## Última execução

| Métrica | Valor |
|---|---|
| Artigos coletados | 350 |
| Fontes | 6 (HN + 5 subreddits) |
| Processados com sucesso | 349 / 350 |
| Tokens únicos após NLP | ~2.400 |
| Clusters | 6 |
| Tempo total do pipeline | ~3 min |

## Próximos passos

- [ ] Agendamento diário com APScheduler
- [ ] API REST com FastAPI (`GET /trends`, `GET /insights`)
- [ ] Análise de sentimento com VADER
- [ ] Deploy no Streamlit Cloud
- [ ] Testes com pytest
- [ ] Mais fontes: Dev.to e feeds RSS

## Licença

MIT.
