# 📡 DataPulse — Guia Completo Passo a Passo

> Este guia te leva do zero até o dashboard rodando, com explicações de tudo que está acontecendo.

---

## 📋 Índice

1. [O que você vai construir](#1-o-que-você-vai-construir)
2. [Pré-requisitos](#2-pré-requisitos)
3. [Configurando o ambiente](#3-configurando-o-ambiente)
4. [Entendendo a estrutura do projeto](#4-entendendo-a-estrutura-do-projeto)
5. [Passo 1 — Coletar dados](#5-passo-1--coletar-dados)
6. [Passo 2 — Processar os dados](#6-passo-2--processar-os-dados)
7. [Passo 3 — Analisar tendências](#7-passo-3--analisar-tendências)
8. [Passo 4 — Abrir o dashboard](#8-passo-4--abrir-o-dashboard)
9. [Entendendo cada arquivo](#9-entendendo-cada-arquivo)
10. [Erros comuns e como resolver](#10-erros-comuns-e-como-resolver)
11. [Como colocar no GitHub](#11-como-colocar-no-github)

---

## 1. O que você vai construir

O **DataPulse** é um sistema que:

- 🔍 **Coleta** posts e artigos do HackerNews e Reddit automaticamente
- 🧹 **Limpa** e processa os textos removendo palavras sem valor
- 📊 **Analisa** quais palavras estão crescendo, agrupa tópicos com Machine Learning
- 💡 **Gera insights** automáticos como *"'AI' cresceu 87% nos últimos dias"*
- 🖥️ **Exibe tudo** num dashboard interativo bonito

**Por que isso impressiona recrutadores?**
Porque mostra que você sabe fazer o ciclo completo de dados:
coleta → banco de dados → NLP → ML → visualização

---

## 2. Pré-requisitos

Antes de qualquer coisa, você precisa ter instalado:

### ✅ Python 3.10 ou superior

**Como verificar se já tem:**
Abra o terminal do VS Code (`Ctrl + '`) e digite:
```
python --version
```
Se aparecer `Python 3.10.x` ou maior, está ok.

**Se não tiver**, baixe em: https://www.python.org/downloads/
> ⚠️ Na instalação, marque a opção **"Add Python to PATH"** — isso é obrigatório!

---

### ✅ VS Code (você já tem)

Extensões recomendadas para instalar no VS Code:
- **Python** (da Microsoft) — essencial
- **Pylance** — autocompletar inteligente
- **Rainbow CSV** — visualizar arquivos CSV coloridos

Para instalar: `Ctrl + Shift + X` → pesquisa o nome → clica em Install

---

### ✅ Git (para subir no GitHub depois)

**Como verificar:**
```
git --version
```

**Se não tiver**, baixe em: https://git-scm.com/downloads

---

## 3. Configurando o Ambiente

### Passo 3.1 — Abrir a pasta certa no VS Code

No VS Code:
1. Aperta `Ctrl + K`, depois `Ctrl + O`
2. Navega até: `Documentos\Claude\Projects\dados\data-pulse`
3. Clica em **Selecionar Pasta**

Você deve ver no Explorer do lado esquerdo:
```
data-pulse/
├── dashboard/
├── data/
├── notebooks/
├── src/
├── .gitignore
├── README.md
└── requirements.txt
```

---

### Passo 3.2 — Abrir o Terminal integrado

Atalho: `Ctrl + '` (acento grave, a tecla do til no teclado BR)

O terminal vai abrir na parte de baixo do VS Code.

**Confirma que você está na pasta certa:**
```bash
pwd
```
Deve mostrar algo como:
`C:\Users\isapi\OneDrive\Documentos\Claude\Projects\dados\data-pulse`

Se não estiver, navega com:
```bash
cd "C:\Users\isapi\OneDrive\Documentos\Claude\Projects\dados\data-pulse"
```

---

### Passo 3.3 — Criar o Ambiente Virtual

> **O que é um ambiente virtual?**
> É uma "caixa separada" para as bibliotecas do seu projeto. Assim, você não mistura as dependências de projetos diferentes. É uma boa prática profissional obrigatória.

```bash
python -m venv venv
```

Isso cria uma pasta `venv/` dentro do projeto. Pode demorar alguns segundos.

---

### Passo 3.4 — Ativar o Ambiente Virtual

**No Windows (PowerShell):**
```bash
venv\Scripts\Activate.ps1
```

**Se aparecer erro de permissão no PowerShell:**
```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\Activate.ps1
```

**No Windows (CMD):**
```bash
venv\Scripts\activate.bat
```

**No macOS/Linux:**
```bash
source venv/bin/activate
```

✅ **Como saber que funcionou:** o terminal vai mostrar `(venv)` no início da linha:
```
(venv) C:\Users\isapi\...\data-pulse>
```

> ⚠️ **Lembre-se:** toda vez que abrir o projeto, você precisa ativar o ambiente virtual. O VS Code às vezes faz isso automaticamente — ele vai perguntar se quer usar o interpretador `venv/Scripts/python.exe`. Clique em **Sim**.

---

### Passo 3.5 — Instalar as Dependências

Com o ambiente virtual ativado, rode:

```bash
pip install -r requirements.txt
```

> **O que isso faz?** Lê o arquivo `requirements.txt` e instala todas as bibliotecas listadas nele.

Vai aparecer muito texto rolando — isso é normal! As principais instalações são:
- `pandas` e `numpy` — manipulação de dados
- `nltk` — processamento de linguagem natural
- `scikit-learn` — machine learning (TF-IDF + KMeans)
- `streamlit` — o dashboard
- `plotly` — gráficos interativos
- `wordcloud` — nuvem de palavras
- `requests` — chamadas HTTP para as APIs

Pode demorar **2 a 5 minutos** dependendo da sua internet.

**Confirma que instalou certo:**
```bash
pip list
```
Deve aparecer uma lista com todas as bibliotecas.

---

## 4. Entendendo a Estrutura do Projeto

Antes de rodar, é importante entender o que cada coisa faz:

```
data-pulse/
│
├── src/                    ← O "cérebro" do projeto
│   ├── utils.py            ← Funções compartilhadas (logging, banco de dados)
│   ├── collect.py          ← COLETA dados das APIs
│   ├── process.py          ← LIMPA e processa os textos
│   └── analyze.py          ← ANALISA tendências e gera insights
│
├── dashboard/
│   └── app.py              ← Interface visual (Streamlit)
│
├── data/
│   ├── raw/                ← JSONs brutos salvos das APIs
│   └── processed/          ← CSVs com dados já processados
│
├── notebooks/              ← Análises exploratórias (Jupyter)
│
├── requirements.txt        ← Lista de bibliotecas necessárias
├── README.md               ← Documentação do projeto (para GitHub)
└── .gitignore              ← O que NÃO enviar para o GitHub
```

**Fluxo de dados:**
```
Internet (APIs) → collect.py → banco SQLite → process.py → analyze.py → dashboard
```

Cada módulo faz UMA coisa bem feita. Isso se chama **separação de responsabilidades** — princípio fundamental de engenharia de software.

---

## 5. Passo 1 — Coletar Dados

Este é o primeiro passo real do projeto. Vamos buscar artigos reais da internet.

```bash
python src/collect.py
```

**O que acontece internamente:**

1. O script conecta ao **HackerNews API** e pega os 100 posts mais populares
2. Conecta ao **Reddit** (r/technology, r/programming, r/MachineLearning, r/datascience, r/artificial) e pega os posts em alta
3. Salva os dados brutos como JSON em `data/raw/`
4. Insere tudo no banco de dados SQLite em `data/datapulse.db`

**O que você vai ver no terminal:**
```
[2024-01-15 14:32:01] INFO | collect | Iniciando coleta HackerNews (limite: 100 posts)...
[2024-01-15 14:32:05] INFO | collect | HackerNews: 98 posts coletados com sucesso.
[2024-01-15 14:32:05] INFO | collect | r/technology: 48 posts coletados.
[2024-01-15 14:32:07] INFO | collect | r/programming: 50 posts coletados.
...
[2024-01-15 14:32:15] INFO | collect | ✅ Coleta concluída!
[2024-01-15 14:32:15] INFO | collect |    Total coletado  : 347 artigos
[2024-01-15 14:32:15] INFO | collect |    Novos no banco  : 347 registros
```

**Pode demorar de 30 segundos a 2 minutos** dependendo da internet.

> 💡 **Dica:** Você pode rodar esse script várias vezes em dias diferentes para acumular dados. Quanto mais dados, melhor a análise de tendências!

---

## 6. Passo 2 — Processar os Dados

Agora vamos limpar os textos coletados:

```bash
python src/process.py
```

**O que acontece:**

1. Carrega os artigos do banco de dados
2. Para cada artigo, o texto passa por várias etapas de limpeza:
   - Remove URLs (`https://...`)
   - Remove tags HTML (`<p>`, `<br>`, etc.)
   - Converte tudo para minúsculas
   - Remove pontuação e caracteres especiais
3. **Tokenização**: quebra o texto em palavras individuais
4. **Remoção de stopwords**: elimina palavras sem valor ("the", "a", "is", "and"...)
5. **Lematização**: converte palavras para a forma canônica ("running" → "run", "better" → "good")
6. Salva o resultado como CSV em `data/processed/`

**O que você vai ver:**
```
[INFO] | process | Carregados 347 artigos do banco.
[INFO] | process | Processando 347 artigos...
[INFO] | process | Processamento concluído: 341/347 artigos válidos.
[INFO] | process | Dados processados salvos: processed_2024-01-15.csv
```

> 💡 **Por que isso é importante?** Sem limpeza, "AI", "A.I.", "ai" e "artificial intelligence" seriam palavras diferentes. Após o processamento, viram tokens comparáveis.

---

## 7. Passo 3 — Analisar Tendências

Este é o passo mais interessante — onde o Machine Learning entra:

```bash
python src/analyze.py
```

**O que acontece:**

**Etapa 1 — Frequência de palavras**
Conta quais palavras aparecem mais no corpus inteiro.
Ex: "ai: 234, model: 189, data: 156..."

**Etapa 2 — Tendências diárias**
Cria uma tabela: linhas = dias, colunas = palavras.
Permite ver como cada palavra evolui ao longo do tempo.

**Etapa 3 — Clusterização com TF-IDF + KMeans**
- **TF-IDF**: transforma cada artigo num vetor de números
  (palavras raras naquele artigo têm peso ALTO, palavras comuns têm peso BAIXO)
- **KMeans**: agrupa artigos com vetores parecidos em 6 clusters
- Para cada cluster, extrai as palavras mais representativas

**Etapa 4 — Insights automáticos**
Compara a frequência recente com a anterior e gera frases:
- "🚀 'llm' cresceu 143% nos últimos dias"
- "🔥 Palavra mais mencionada: 'AI' com 234 ocorrências"

**O que você vai ver:**
```
[INFO] | analyze | [1/4] Calculando frequência de palavras...
[INFO] | analyze | Top 50 palavras calculadas. Mais frequente: 'ai' (234x)
[INFO] | analyze | [2/4] Detectando tendências ao longo do tempo...
[INFO] | analyze | Tendências calculadas para 3 dias e 20 palavras.
[INFO] | analyze | [3/4] Clusterizando tópicos com TF-IDF + KMeans...
[INFO] | analyze | Clusterização concluída: 6 tópicos identificados.
  Cluster 0: ai, model, llm, gpt, language (89 artigos)
  Cluster 1: security, breach, vulnerability, attack (45 artigos)
  ...
[INFO] | analyze | [4/4] Gerando insights automáticos...
[INFO] | analyze | 8 insights gerados automaticamente.

🔍 TOP 10 PALAVRAS:
 word  count  rank
   ai    234     1
model    189     2
 data    156     3
...

💡 INSIGHTS AUTOMÁTICOS:
  🚀 'Llm' cresceu 143% nos últimos dias
  🔥 Palavra mais mencionada: 'Ai' com 234 ocorrências
  📊 Tópico dominante: 'Ai' com 89 artigos agrupados
```

---

## 8. Passo 4 — Abrir o Dashboard

Agora o momento mais visual do projeto:

```bash
streamlit run dashboard/app.py
```

**O que acontece:**
- O Streamlit inicia um servidor local
- O seu navegador abre automaticamente em `http://localhost:8501`
- Você vê o dashboard completo com todos os dados analisados

**O que você verá no dashboard:**

| Seção | O que mostra |
|-------|-------------|
| 📊 Visão Geral | 4 métricas: total de artigos, artigos hoje, dias monitorados, fontes ativas |
| 💡 Insights | Frases automáticas sobre crescimento e tendências |
| ☁️ Nuvem de Palavras | Palavras mais frequentes em tamanhos diferentes |
| 🏆 Top 10 Ranking | Tabela com as palavras e suas frequências |
| 📈 Tendências | Gráfico de linhas: evolução de palavras ao longo dos dias |
| 📉 Crescimento | Gráfico de barras: quem cresceu e quem caiu |
| 🗂️ Tópicos | Pizza + tabela com os 6 clusters identificados |
| 🔍 Dados Brutos | Tabela com todos os artigos coletados |

**Controles da sidebar (barra lateral esquerda):**
- **Fonte de dados**: filtra por HackerNews ou Reddit
- **Período**: quantos dias analisar (1 a 30)
- **Top N palavras**: quantas palavras exibir
- **Número de tópicos**: quantos clusters criar
- **Botão "Coletar Dados Agora"**: executa nova coleta sem sair do dashboard

**Para parar o dashboard:** volta no terminal e aperta `Ctrl + C`

---

## 9. Entendendo Cada Arquivo

### `src/utils.py` — A Base
```
Responsabilidade: funções que todos os outros módulos usam

Contém:
- get_logger()       → cria logs com timestamp e nível (INFO/WARNING/ERROR)
- get_db_connection() → abre conexão com o banco SQLite
- init_database()    → cria as tabelas se não existirem
- save_raw_json()    → salva dados brutos em JSON
- today_str()        → retorna data de hoje formatada
```

Por que existe? → Evita repetir código. Se precisar mudar o banco de dados, muda só aqui.

---

### `src/collect.py` — O Coletor
```
Responsabilidade: buscar dados reais da internet

Funções principais:
- fetch_hackernews_top(limit)  → busca top N posts do HN
- fetch_reddit_posts(sub)     → busca posts de um subreddit
- fetch_all_reddit()          → busca de múltiplos subreddits
- save_articles_to_db()       → salva no banco SQLite
- run_collection()            → orquestra tudo (ponto de entrada)
```

Fontes usadas:
- HackerNews: `https://hacker-news.firebaseio.com/v0/topstories.json`
- Reddit: `https://www.reddit.com/r/{subreddit}/hot.json`

Por que essas fontes? → Totalmente públicas, sem precisar de cadastro ou chave de API.

---

### `src/process.py` — O Processador de Texto
```
Responsabilidade: transformar texto bruto em tokens limpos

Pipeline de limpeza:
1. remove_urls()              → elimina https://...
2. remove_html_tags()         → elimina <p>, &amp;, etc.
3. text.lower()               → tudo minúsculo
4. remove_special_characters() → só letras e números
5. word_tokenize()            → quebra em palavras
6. filtra stopwords           → remove "the", "is", "and"...
7. lemmatize_tokens()         → "running" → "run"
```

---

### `src/analyze.py` — O Motor de Análise
```
Responsabilidade: extrair inteligência dos dados processados

Funções principais:
- compute_word_frequency()    → Counter de tokens
- compute_daily_trends()      → tabela de frequência por dia
- cluster_topics()            → TF-IDF + KMeans
- compute_growth_rate()       → % de crescimento por palavra
- generate_insights()         → frases em linguagem natural
- run_analysis()              → orquestra tudo
```

---

### `dashboard/app.py` — A Interface Visual
```
Responsabilidade: mostrar tudo visualmente

Seções:
- render_sidebar()         → filtros e controles laterais
- render_wordcloud()       → nuvem de palavras
- render_bar_chart()       → barras de frequência
- render_trend_lines()     → evolução temporal
- render_cluster_chart()   → pizza de clusters
- render_growth_chart()    → crescimento/queda
- main()                   → monta o layout completo
```

---

## 10. Erros Comuns e Como Resolver

### ❌ `ModuleNotFoundError: No module named 'streamlit'`
**Causa:** ambiente virtual não está ativado, ou dependências não foram instaladas.
```bash
# Ativa o ambiente virtual
venv\Scripts\Activate.ps1   # Windows
source venv/bin/activate    # macOS/Linux

# Reinstala as dependências
pip install -r requirements.txt
```

---

### ❌ `sqlite3.OperationalError: no such table: articles`
**Causa:** você pulou o passo de coleta.
```bash
# Roda a coleta primeiro
python src/collect.py
```

---

### ❌ `Error: no such file or directory` ao rodar o dashboard
**Causa:** você não está na pasta correta.
```bash
# Navega para a pasta do projeto
cd "C:\Users\isapi\OneDrive\Documentos\Claude\Projects\dados\data-pulse"

# Agora rode
streamlit run dashboard/app.py
```

---

### ❌ `LookupError: Resource 'stopwords' not found`
**Causa:** recursos do NLTK não foram baixados (raro, o código faz isso automaticamente).
```python
# Abra o Python no terminal e rode:
python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt'); nltk.download('wordnet')"
```

---

### ❌ `ConnectionError` ou `Timeout` durante a coleta
**Causa:** problema de internet ou API temporariamente fora.
- Verifique sua conexão
- Tente novamente após alguns minutos
- A API do Reddit especialmente pode ter rate limit (limite de chamadas)

---

### ❌ Dashboard abre mas mostra aviso "Nenhum dado encontrado"
**Causa:** coleta não foi feita ou falhou.
```bash
# Na barra lateral do dashboard, clique em "Coletar Dados Agora"
# OU rode no terminal:
python src/collect.py
python src/process.py
```

---

## 11. Como Colocar no GitHub

Colocar no GitHub é essencial para portfólio. Recrutadores **vão** verificar.

### Passo 11.1 — Crie uma conta no GitHub
Acesse: https://github.com e crie sua conta se não tiver.

### Passo 11.2 — Crie um repositório novo
1. Clique no **+** no canto superior direito → **New repository**
2. Nome: `data-pulse`
3. Descrição: `📡 Sistema de radar de tendências tech com NLP e Machine Learning`
4. Deixe como **Public** (recrutadores precisam ver)
5. **NÃO** marque "Add a README" (já temos um)
6. Clique em **Create repository**

### Passo 11.3 — Configure o Git localmente
```bash
# Dentro da pasta data-pulse, rode:
git init
git add .
git commit -m "feat: projeto inicial DataPulse com pipeline completo"

# Substitua SEU-USUARIO pelo seu usuário do GitHub
git remote add origin https://github.com/SEU-USUARIO/data-pulse.git
git branch -M main
git push -u origin main
```

### Passo 11.4 — Adicione screenshots ao README
Depois de rodar o dashboard:
1. Tire prints das seções mais bonitas
2. Salve em uma pasta `docs/images/` no projeto
3. Edite o `README.md` e substitua os `[INSERIR AQUI]` pelos prints

### Dicas para o README impressionar:
- Adicione os badges (já estão no README criado)
- Inclua um GIF do dashboard funcionando (use o LICEcap para gravar)
- Descreva o projeto na primeira pessoa: *"Desenvolvi um sistema que..."*

---

## 🎯 Resumo dos Comandos — Cola Rápida

```bash
# 1. Navegar para o projeto
cd "C:\Users\isapi\OneDrive\Documentos\Claude\Projects\dados\data-pulse"

# 2. Ativar ambiente virtual
venv\Scripts\Activate.ps1

# 3. Instalar dependências (só na primeira vez)
pip install -r requirements.txt

# 4. Coletar dados
python src/collect.py

# 5. Processar dados
python src/process.py

# 6. Analisar tendências
python src/analyze.py

# 7. Abrir o dashboard
streamlit run dashboard/app.py
```

---

*Guia criado para o projeto DataPulse — Radar Inteligente de Tendências*
*Parte do portfólio de Engenharia e Ciência de Dados*
