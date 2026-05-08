# 📡 DataPulse — Radar Inteligente de Tendências

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.34-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4-F7931E?style=flat&logo=scikit-learn&logoColor=white)
![NLTK](https://img.shields.io/badge/NLTK-3.8-154f3c?style=flat)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

> **Sistema de coleta, processamento e análise de tendências tecnológicas em tempo real**, com dashboard interativo e insights automáticos gerados por NLP + Machine Learning.

---

## 🎯 O Problema

Profissionais de tecnologia e negócios precisam saber **o que está em alta** no mundo tech, mas as informações estão espalhadas em dezenas de fontes: Reddit, HackerNews, blogs, fóruns. Acompanhar tudo manualmente é inviável.

## 💡 A Solução

O **DataPulse** automatiza esse processo:

1. **Coleta** dados de comunidades tech em tempo real (HackerNews, Reddit)
2. **Processa** os textos com técnicas de NLP (limpeza, tokenização, lematização)
3. **Analisa** frequências, calcula crescimento e agrupa tópicos com Machine Learning
4. **Exibe** tudo em um dashboard interativo com insights em linguagem natural

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────┐
│                    PIPELINE DATAPULSE                    │
├──────────────┬──────────────┬─────────────┬─────────────┤
│   COLETA     │ PROCESSAMENTO│   ANÁLISE   │ VISUALIZAÇÃO│
│              │              │             │             │
│ HackerNews ──┤              │  Word Freq  │             │
│   API        │  Limpeza     │  TF-IDF +   │  Streamlit  │
│              │  Stopwords   │  KMeans     │  Dashboard  │
│ Reddit ──────┤  Lemmatize   │  Tendências │  Plotly     │
│  JSON API    │  Normalização│  Insights   │  WordCloud  │
│              │              │  Automáticos│             │
└──────────────┴──────────────┴─────────────┴─────────────┘
                        │
                   SQLite DB
              (artigos + tendências)
```

**Fluxo de dados:**
```
APIs Públicas → collect.py → SQLite (raw)
                                ↓
                         process.py → tokens limpos
                                ↓
                          analyze.py → freq / clusters / insights
                                ↓
                        dashboard/app.py → UI interativa
```

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia | Finalidade |
|--------|-----------|------------|
| **Coleta** | `requests` | Chamadas HTTP às APIs |
| **Armazenamento** | `SQLite` | Banco de dados local, zero config |
| **Processamento** | `Pandas`, `NumPy` | Manipulação de dados |
| **NLP** | `NLTK` | Tokenização, stopwords, lematização |
| **ML** | `scikit-learn` | TF-IDF + KMeans clustering |
| **Visualização** | `Streamlit`, `Plotly` | Dashboard interativo |
| **Nuvem de palavras** | `wordcloud`, `Matplotlib` | Visualização de frequência |
| **Config** | `python-dotenv` | Variáveis de ambiente |

---

## 📁 Estrutura do Projeto

```
data-pulse/
│
├── data/
│   ├── raw/              # JSONs brutos das APIs (não versionados)
│   └── processed/        # CSVs com texto processado
│
├── notebooks/            # Análises exploratórias (Jupyter)
│
├── src/
│   ├── utils.py          # Logging, banco de dados, helpers
│   ├── collect.py        # Coleta de dados (HackerNews + Reddit)
│   ├── process.py        # Limpeza e processamento de texto
│   └── analyze.py        # Análise: freq, tendências, clusters, insights
│
├── dashboard/
│   └── app.py            # Dashboard Streamlit completo
│
├── requirements.txt      # Dependências do projeto
├── README.md             # Este arquivo
└── .gitignore
```

---

## 🚀 Como Rodar Localmente

### Pré-requisitos
- Python 3.10 ou superior
- pip atualizado

### Passo a Passo

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/data-pulse.git
cd data-pulse

# 2. Crie e ative o ambiente virtual
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Colete os dados (sem precisar de chave de API!)
python src/collect.py

# 5. Processe os dados coletados
python src/process.py

# 6. Execute as análises
python src/analyze.py

# 7. Inicie o dashboard
streamlit run dashboard/app.py
```

O dashboard abrirá automaticamente em `http://localhost:8501`

---

## 📸 Screenshots

> **[INSERIR AQUI]** Print da tela principal do dashboard mostrando as métricas rápidas e os insights automáticos.

> **[INSERIR AQUI]** Print da seção de Nuvem de Palavras e o ranking das top 10 palavras.

> **[INSERIR AQUI]** Print dos gráficos de tendência temporal e taxa de crescimento.

> **[INSERIR AQUI]** Print da seção de Clusters de Tópicos com o gráfico de pizza.

---

## 🔍 Detalhes Técnicos

### Pipeline de NLP
```
Texto bruto
  → remoção de URLs e HTML
  → lowercase
  → remoção de pontuação
  → tokenização (NLTK word_tokenize)
  → filtragem de stopwords (EN + custom)
  → lematização (WordNetLemmatizer)
  → tokens prontos para análise
```

### Algoritmo de Clustering
- **TF-IDF** transforma cada artigo em vetor numérico
  - Palavras que aparecem muito em POUCOS artigos têm peso alto
  - Palavras em TODOS os artigos têm peso baixo (descartadas)
- **KMeans** agrupa artigos com vetores similares
- Para cada cluster: extrai palavras com maior peso no centroide

### Detecção de Tendências
- Calcula frequência de palavras por dia
- Compara frequência recente vs. período anterior
- Taxa de crescimento: `(freq_recente - freq_anterior) / freq_anterior × 100%`

---

## ⚡ Diferenciais do Projeto

- ✅ **Zero dependência de chaves de API** — funciona para qualquer pessoa que clonar
- ✅ **Insights em linguagem natural** — transforma dados em frases acionáveis
- ✅ **Cache inteligente no Streamlit** — dashboard rápido mesmo com muito dado
- ✅ **Modularização clara** — cada arquivo tem uma responsabilidade única
- ✅ **Código comentado didaticamente** — explica o "porquê" de cada decisão
- ✅ **SQLite como banco real** — persistência entre execuções, fácil de inspecionar
- ✅ **Pronto para escalar** — substituir SQLite por PostgreSQL = 1 linha de código

---

## 🔭 Próximos Passos

- [ ] Adicionar API com FastAPI (`GET /trends`, `GET /insights`)
- [ ] Suporte a RSS feeds de blogs tech (TechCrunch, Wired)
- [ ] Agendamento automático com `schedule` ou cron
- [ ] Análise de sentimento com `transformers` (BERT)
- [ ] Deploy no Streamlit Cloud ou Railway
- [ ] Testes unitários com `pytest`

---

## 👩‍💻 Sobre

Projeto desenvolvido como parte de portfólio para vagas de Engenharia e Ciência de Dados.

**Habilidades demonstradas:**
- Engenharia de dados (pipeline ETL completo)
- Processamento de linguagem natural (NLP)
- Machine Learning não supervisionado (clustering)
- Desenvolvimento de dashboards interativos
- Boas práticas de código (modularização, logging, docstrings)

---

## 📄 Licença

MIT License — sinta-se à vontade para usar, modificar e distribuir.
