# 📡 DataPulse — Radar Inteligente de Tendências Tech

<div align="center">

![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.57-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![scikit--learn](https://img.shields.io/badge/scikit--learn-1.8-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)
![NLTK](https://img.shields.io/badge/NLTK-3.9-154f3c?style=for-the-badge)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.x-150458?style=for-the-badge&logo=pandas&logoColor=white)

**Sistema end-to-end de coleta, processamento e análise de tendências tecnológicas em tempo real.**
Pipeline completo: APIs públicas → NLP → Machine Learning → Dashboard interativo.

[▶ Ver Demo](#-preview-do-dashboard) • [⚙ Como Rodar](#-como-rodar-localmente) • [🏗 Arquitetura](#-arquitetura-do-sistema)

</div>

---

## 🎯 Motivação e Problema

Acompanhar o que está em alta no mundo da tecnologia é cada vez mais difícil. As discussões relevantes estão fragmentadas em dezenas de plataformas — HackerNews, Reddit, blogs, fóruns — e mudam rapidamente.

**A pergunta que esse projeto responde:**
> *"Quais tópicos estão ganhando tração agora? O que a comunidade tech está discutindo hoje que não estava há 3 dias?"*

O DataPulse automatiza esse monitoramento com um pipeline de dados completo, desde a coleta até a geração de insights em linguagem natural.

---

## 🖥️ Preview do Dashboard

### 📊 Visão Geral & Insights Automáticos
> Métricas em tempo real + frases de insight geradas automaticamente pelo sistema.

<!-- TODO: subir o print em docs/images/01_overview.png e descomentar
![Dashboard Overview](docs/images/01_overview.png)
-->

### ☁️ Nuvem de Palavras & Ranking Top 10
> Visualização imediata do vocabulário dominante no corpus do dia.

<!-- TODO: subir o print em docs/images/02_wordcloud.png e descomentar
![Word Cloud](docs/images/02_wordcloud.png)
-->

### 📈 Taxa de Crescimento & Frequência Global
> Detecta quais palavras estão crescendo — não apenas quais são populares.

<!-- TODO: subir o print em docs/images/03_trends.png e descomentar
![Trends](docs/images/03_trends.png)
-->

### 🗂️ Clusters de Tópicos Identificados por ML
> KMeans agrupa artigos em tópicos sem nenhum label manual.

<!-- TODO: subir o print em docs/images/04_topics.png e descomentar
![Topics](docs/images/04_topics.png)
-->

### 🔍 Explorador de Artigos Brutos
> Todos os dados coletados acessíveis com links clicáveis direto para a fonte.

<!-- TODO: subir o print em docs/images/05_rawdata.png e descomentar
![Raw Data](docs/images/05_rawdata.png)
-->

---

## 🏗️ Arquitetura do Sistema

O projeto segue uma arquitetura de **pipeline ETL modular**, onde cada camada tem uma responsabilidade única e bem definida:

```
┌──────────────────────────────────────────────────────────────────┐
│                         DATAPULSE PIPELINE                        │
│                                                                    │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────────────┐ │
│  │   EXTRACT   │    │  TRANSFORM   │    │        LOAD           │ │
│  │             │    │              │    │                       │ │
│  │ HackerNews  │───▶│  Limpeza     │───▶│  SQLite               │ │
│  │ API (JSON)  │    │  Tokenização │    │  (artigos + trends)   │ │
│  │             │    │  Stopwords   │    │                       │ │
│  │ Reddit      │───▶│  Lemmatize   │───▶│  CSV processado       │ │
│  │ Public JSON │    │  TF-IDF      │    │  JSON bruto           │ │
│  └─────────────┘    └──────────────┘    └───────────────────────┘ │
│                              │                                     │
│                              ▼                                     │
│                   ┌──────────────────┐                            │
│                   │    ANALYTICS     │                            │
│                   │                  │                            │
│                   │  Word Frequency  │                            │
│                   │  Daily Trends    │                            │
│                   │  KMeans Clusters │                            │
│                   │  Growth Rate     │                            │
│                   │  Auto Insights   │                            │
│                   └────────┬─────────┘                            │
│                            │                                      │
│                            ▼                                      │
│                   ┌──────────────────┐                            │
│                   │   STREAMLIT UI   │                            │
│                   │  Dashboard + API │                            │
│                   └──────────────────┘                            │
└──────────────────────────────────────────────────────────────────┘
```

**Princípio de design:** cada módulo (`collect`, `process`, `analyze`) pode ser executado de forma independente, facilitando testes, manutenção e futura escalabilidade.

---

## 🔬 Detalhes Técnicos

### 1. Coleta de Dados (`src/collect.py`)

Dois coletores independentes, ambos **sem necessidade de chaves de API**:

**HackerNews** — usa a [Firebase REST API](https://hacker-news.firebaseio.com/v0/) pública:
```python
# Passo 1: busca lista de IDs dos top 100 posts
GET https://hacker-news.firebaseio.com/v0/topstories.json

# Passo 2: busca detalhes de cada post
GET https://hacker-news.firebaseio.com/v0/item/{id}.json
```

**Reddit** — usa o endpoint JSON público (sem autenticação):
```python
GET https://www.reddit.com/r/{subreddit}/hot.json?limit=50
# Subreddits: technology, programming, MachineLearning, datascience, artificial
```

Todos os dados brutos são salvos em `data/raw/` como JSON com timestamp, garantindo **rastreabilidade completa** — se algo mudar na análise, os dados originais ainda estão disponíveis.

---

### 2. Pipeline de NLP (`src/process.py`)

O texto passa por 7 etapas de transformação antes de ser analisado:

```
Texto bruto
    ↓ remove_urls()            → elimina "https://..."
    ↓ remove_html_tags()       → elimina "<p>", "&amp;", etc.
    ↓ .lower()                 → "AI" e "ai" viram o mesmo token
    ↓ remove_special_chars()   → mantém só letras e números
    ↓ word_tokenize() [NLTK]   → quebra em palavras individuais
    ↓ filtra stopwords         → remove "the", "is", "was", "a"...
    ↓ lemmatize() [WordNet]    → "running"→"run", "models"→"model"
    ↓
  tokens prontos para análise
```

**Por que lematização e não stemming?**
O stemming é mais agressivo e pode deformar palavras (`"caring"→"car"`). A lematização usa um dicionário real (WordNet) e produz formas canônicas legíveis — importante para o dashboard exibir palavras compreensíveis.

---

### 3. Detecção de Tendências (`src/analyze.py`)

A detecção de tendências vai além de contar palavras. O sistema calcula a **taxa de crescimento** comparando dois períodos:

```
crescimento = (frequência_recente - frequência_anterior) / frequência_anterior × 100%
```

Isso distingue entre:
- Uma palavra **popular** (aparece muito, mas estável)
- Uma palavra em **tendência** (aparece mais do que antes — sinal de buzz)

**Exemplo real do sistema em 08/05/2026:**
- `"agent"` → +2900% (IA agêntica explodindo nas discussões)
- `"game"` → +4000% (lançamento do Nintendo Switch 2 gerando buzz)
- `"model"` → -7% (estável, word dominante mas sem crescimento)

---

### 4. Clusterização de Tópicos com TF-IDF + KMeans

O clustering identifica **grupos temáticos** sem nenhum label manual:

**TF-IDF (Term Frequency × Inverse Document Frequency)**
- Palavras que aparecem muito em **poucos** artigos → peso alto (discriminativas)
- Palavras que aparecem em **todos** os artigos → peso baixo (genéricas)
- Resultado: cada artigo vira um vetor de 500 dimensões

**KMeans**
- Agrupa vetores similares em N clusters (padrão: 6)
- Para cada cluster, extrai as palavras com maior peso no centróide

**Resultado real (08/05/2026):**
| Cluster | Palavras-chave | Artigos |
|---------|---------------|---------|
| Tópico 4 — Model | model, data, problem, work, paper, claude | 308 (93%) |
| Tópico 5 — Agent | agent, workflow, cli, prompt, need, human | 9 (2.7%) |
| Tópico 6 — School | school, related, student, final, may, find | 6 (1.8%) |
| Tópico 2 — Coding | coding, agent, trust, show, field, across | 4 (1.2%) |
| Tópico 1 — Session | session, user, language, week, always | 2 (0.6%) |
| Tópico 3 — Math | math, transformer, find, model, graph, error | 1 (0.3%) |

---

### 5. Insights Automáticos em Linguagem Natural

O sistema gera frases interpretáveis automaticamente, tornando a análise acessível a qualquer pessoa:

```python
# Exemplo de saída gerada pelo sistema:
"🚀 'Agent' cresceu 2900% nos últimos dias"
"🚀 'Game' cresceu 4000% nos últimos dias"
"🔥 Palavra mais mencionada: 'Model' com 147 ocorrências"
"📊 Tópico dominante: 'Model' com 308 artigos agrupados"
"📉 'Post' caiu 40% nos últimos dias"
```

---

## 🛠️ Stack Tecnológica

| Categoria | Tecnologia | Versão | Justificativa |
|-----------|-----------|--------|---------------|
| **Linguagem** | Python | 3.14 | Ecossistema de dados mais completo |
| **Dados** | Pandas + NumPy | latest | Padrão da indústria para ETL |
| **NLP** | NLTK | 3.9 | Tokenização e lematização robustas |
| **ML** | scikit-learn | 1.8 | TF-IDF vetorizado + KMeans |
| **Dashboard** | Streamlit | 1.57 | Prototipagem rápida de UIs de dados |
| **Gráficos** | Plotly | 6.7 | Visualizações interativas |
| **Wordcloud** | wordcloud | 1.9 | Visualização de frequência |
| **Banco** | SQLite | built-in | Zero configuração, portátil |
| **HTTP** | requests | 2.33 | Coleta das APIs públicas |

> **Por SQLite e não PostgreSQL?**
> Para um projeto de portfólio e análise local, SQLite elimina fricção de setup. A troca para PostgreSQL seria uma mudança de 1 linha em `utils.py` — a arquitetura foi desenhada para isso.

---

## 📁 Estrutura do Projeto

```
data-pulse/
│
├── 📂 data/
│   ├── raw/                  # JSONs brutos das APIs (com timestamp)
│   │   ├── hackernews_2026-05-08.json
│   │   └── reddit_2026-05-08.json
│   ├── processed/            # CSVs com tokens processados
│   │   └── processed_2026-05-08.csv
│   └── datapulse.db          # Banco SQLite (artigos + trends)
│
├── 📂 docs/
│   └── images/               # Screenshots do dashboard
│
├── 📂 notebooks/             # Análises exploratórias (Jupyter)
│
├── 📂 src/                   # Módulos do pipeline
│   ├── utils.py              # Logging, DB, helpers reutilizáveis
│   ├── collect.py            # Coleta: HackerNews + Reddit APIs
│   ├── process.py            # NLP: limpeza + tokenização + lemmatize
│   └── analyze.py            # ML: freq + trends + TF-IDF + KMeans
│
├── 📂 dashboard/
│   └── app.py                # Dashboard Streamlit (600+ linhas)
│
├── requirements.txt          # Dependências do projeto
├── GUIA_COMPLETO.md          # Guia passo a passo detalhado
├── README.md
└── .gitignore
```

---

## 🚀 Como Rodar Localmente

### Pré-requisitos
- Python 3.10+
- Git

### Setup completo

```bash
# 1. Clone o repositório
git clone https://github.com/Isapinhoo/data-pulse.git
cd data-pulse

# 2. Ambiente virtual
python -m venv venv
venv\Scripts\Activate.ps1      # Windows PowerShell
# source venv/bin/activate     # macOS / Linux

# 3. Dependências
pip install -r requirements.txt

# 4. Rode o pipeline completo
python src/collect.py    # coleta ~350 artigos em ~2 min
python src/process.py    # NLP: tokeniza e lematiza
python src/analyze.py    # ML: clusters e insights

# 5. Dashboard
streamlit run dashboard/app.py
# Acesse: http://localhost:8501
```

> **Sem chaves de API.** O projeto usa exclusivamente endpoints públicos do HackerNews e Reddit — qualquer pessoa pode clonar e rodar imediatamente.

---

## 📊 Resultados da Última Execução

| Métrica | Valor |
|---------|-------|
| Artigos coletados | 350 |
| Fontes monitoradas | 6 (HN + 5 subreddits) |
| Artigos processados com sucesso | 349 / 350 (99.7%) |
| Tokens únicos após NLP | ~2.400 |
| Clusters identificados | 6 |
| Insights gerados automaticamente | 8 |
| Tempo total do pipeline | ~3 minutos |

---

## ⚡ Diferenciais Técnicos

- **Arquitetura modular real** — cada módulo tem uma responsabilidade única; fácil de testar e manter
- **Rastreabilidade de dados** — dados brutos sempre preservados em JSON com timestamp
- **Dois tipos de análise complementares** — frequência absoluta (o que é popular) + taxa de crescimento (o que está ganhando tração)
- **NLP explicável** — escolha de lemmatização sobre stemming por legibilidade
- **Cache inteligente no Streamlit** — `@st.cache_data(ttl=300)` evita queries repetidas ao banco
- **Logging profissional** — todos os módulos usam `logging` com timestamp e nível, não `print()`

---

## 🔭 Roadmap

- [x] Pipeline ETL completo (collect → process → analyze)
- [x] Dashboard interativo com Streamlit
- [x] Clustering de tópicos com TF-IDF + KMeans
- [x] Insights automáticos em linguagem natural
- [ ] Agendamento automático diário (APScheduler)
- [ ] API REST com FastAPI (`GET /trends`, `GET /insights`)
- [ ] Análise de sentimento com VADER
- [ ] Deploy no Streamlit Cloud
- [ ] Testes unitários com pytest (cobertura > 80%)
- [ ] Suporte a mais fontes: Dev.to, RSS feeds

---

## 👩‍💻 Sobre o Projeto

Desenvolvido como projeto de portfólio focado em demonstrar habilidades práticas de **Engenharia e Ciência de Dados**.

**Competências demonstradas:**
- Pipeline ETL completo do zero
- Processamento de linguagem natural (NLP)
- Machine Learning não supervisionado (clustering)
- Modelagem de banco de dados relacional
- Desenvolvimento de dashboards interativos
- Boas práticas: modularização, logging, docstrings, separação de responsabilidades

---

## 📄 Licença

MIT License — use, modifique e distribua livremente.
