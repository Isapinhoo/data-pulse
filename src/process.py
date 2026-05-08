"""
process.py — Processamento de Texto do DataPulse
=================================================
Transforma dados brutos em dados limpos e prontos para análise.

Etapas do pipeline:
  1. Limpeza básica (lowercase, pontuação, URLs)
  2. Tokenização (quebra o texto em palavras)
  3. Remoção de stopwords (palavras sem valor semântico)
  4. Normalização (stemming ou lematização)
  5. Persistência dos dados processados

Por que processar texto?
→ "AI", "A.I.", "artificial intelligence" → mesmo conceito
→ "running", "runs", "ran" → mesmo radical
→ Sem limpeza, a análise fica poluída com palavras irrelevantes
"""

import re
import string
import pandas as pd
import sqlite3
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    get_logger, get_db_connection, PROCESSED_DIR,
    today_str, save_raw_json
)

logger = get_logger("process")

# ──────────────────────────────────────────────
# SETUP DO NLTK (baixa recursos na primeira vez)
# ──────────────────────────────────────────────

import nltk

def setup_nltk() -> None:
    """
    Garante que os recursos do NLTK estejam baixados.
    Roda silenciosamente se já estiverem presentes.
    """
    resources = [
        ("tokenizers/punkt", "punkt"),
        ("tokenizers/punkt_tab", "punkt_tab"),
        ("corpora/stopwords", "stopwords"),
        ("corpora/wordnet", "wordnet"),
    ]
    for path, name in resources:
        try:
            nltk.data.find(path)
        except LookupError:
            logger.info(f"Baixando recurso NLTK: {name}...")
            nltk.download(name, quiet=True)

setup_nltk()

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer, WordNetLemmatizer

# Stemmer: reduz palavras ao radical (running → run)
stemmer = PorterStemmer()
# Lemmatizer: usa dicionário para forma canônica (better → good)
lemmatizer = WordNetLemmatizer()

# Stopwords em inglês + termos comuns sem valor analítico
STOPWORDS_EN = set(stopwords.words("english"))
CUSTOM_STOPWORDS = {
    "http", "https", "www", "com", "html", "org",
    "said", "say", "says", "also", "would", "could",
    "like", "just", "get", "got", "one", "new", "use",
    "make", "made", "year", "time", "day", "way",
    "people", "think", "know", "many", "much", "still"
}
ALL_STOPWORDS = STOPWORDS_EN | CUSTOM_STOPWORDS


# ──────────────────────────────────────────────
# FUNÇÕES DE LIMPEZA DE TEXTO
# ──────────────────────────────────────────────

def remove_urls(text: str) -> str:
    """Remove URLs do texto (http://..., https://...)."""
    return re.sub(r"https?://\S+|www\.\S+", "", text)


def remove_html_tags(text: str) -> str:
    """Remove tags HTML residuais (<p>, <br>, &amp;, etc.)."""
    text = re.sub(r"<[^>]+>", " ", text)                 # tags HTML
    text = re.sub(r"&\w+;", " ", text)                   # entidades HTML
    return text


def remove_special_characters(text: str) -> str:
    """Remove pontuação e caracteres especiais, mantendo espaços."""
    # Mantém letras, números e espaços
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    # Colapsa múltiplos espaços em um único
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_text(text: str) -> str:
    """
    Pipeline completo de limpeza de texto.

    Aplicado em sequência para garantir ordem correta:
    URL → HTML → lowercase → especiais → espaços

    Args:
        text: string bruta

    Returns:
        String limpa e normalizada.
    """
    if not text or not isinstance(text, str):
        return ""

    text = remove_urls(text)
    text = remove_html_tags(text)
    text = text.lower()                          # tudo minúsculo
    text = remove_special_characters(text)

    return text


def tokenize_and_filter(text: str, min_length: int = 3) -> list[str]:
    """
    Tokeniza o texto e filtra tokens irrelevantes.

    Args:
        text: texto já limpo
        min_length: tamanho mínimo de token (padrão: 3 caracteres)

    Returns:
        Lista de tokens significativos.
    """
    tokens = word_tokenize(text)

    filtered = [
        token for token in tokens
        if token not in ALL_STOPWORDS           # não é stopword
        and len(token) >= min_length            # tamanho mínimo
        and token.isalpha()                     # apenas letras (sem "123", "a1b")
    ]

    return filtered


def stem_tokens(tokens: list[str]) -> list[str]:
    """
    Aplica stemming: reduz palavras ao radical.
    Ex: "running", "runner", "runs" → "run"

    Vantagem: mais agressivo, cobre mais variações
    Desvantagem: pode distorcer palavras ("caring" → "car")
    """
    return [stemmer.stem(token) for token in tokens]


def lemmatize_tokens(tokens: list[str]) -> list[str]:
    """
    Aplica lematização: forma canônica da palavra.
    Ex: "better" → "good", "studies" → "study"

    Vantagem: preserva palavras legíveis
    Desvantagem: mais lento, requer POS tagging para máxima precisão
    """
    return [lemmatizer.lemmatize(token) for token in tokens]


def process_text_full(text: str, method: str = "lemmatize") -> list[str]:
    """
    Pipeline completo: limpa → tokeniza → normaliza.

    Args:
        text: texto bruto
        method: "stem" ou "lemmatize"

    Returns:
        Lista de tokens processados.
    """
    cleaned = clean_text(text)
    tokens = tokenize_and_filter(cleaned)

    if method == "stem":
        return stem_tokens(tokens)
    else:
        return lemmatize_tokens(tokens)


# ──────────────────────────────────────────────
# PROCESSAMENTO EM LOTE (DataFrame)
# ──────────────────────────────────────────────

def load_articles_from_db(
    source: Optional[str] = None,
    date: Optional[str] = None,
    limit: int = 1000
) -> pd.DataFrame:
    """
    Carrega artigos do banco SQLite para um DataFrame Pandas.

    Args:
        source: filtra por fonte (ex: "hackernews")
        date: filtra por data (YYYY-MM-DD)
        limit: máximo de registros

    Returns:
        DataFrame com os artigos.
    """
    conn = get_db_connection()

    query = "SELECT * FROM articles WHERE 1=1"
    params = []

    if source:
        query += " AND source LIKE ?"
        params.append(f"%{source}%")
    if date:
        query += " AND date = ?"
        params.append(date)

    query += f" ORDER BY score DESC LIMIT {limit}"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    logger.info(f"Carregados {len(df)} artigos do banco.")
    return df


def process_dataframe(df: pd.DataFrame, method: str = "lemmatize") -> pd.DataFrame:
    """
    Aplica o pipeline de processamento a um DataFrame inteiro.

    Adiciona colunas:
      - clean_title: título limpo
      - tokens: lista de tokens processados
      - tokens_str: tokens como string (para nuvem de palavras)

    Args:
        df: DataFrame com coluna 'title' (e opcionalmente 'text')
        method: método de normalização

    Returns:
        DataFrame enriquecido com colunas de processamento.
    """
    if df.empty:
        logger.warning("DataFrame vazio recebido para processamento.")
        return df

    logger.info(f"Processando {len(df)} artigos...")

    # Combina título + texto para análise mais rica
    # fillna("") evita erros com valores None/NaN
    df = df.copy()
    df["combined_text"] = df["title"].fillna("") + " " + df["text"].fillna("")

    # Aplica limpeza e tokenização
    df["clean_title"] = df["title"].fillna("").apply(clean_text)
    df["tokens"] = df["combined_text"].apply(
        lambda t: process_text_full(t, method=method)
    )
    df["tokens_str"] = df["tokens"].apply(lambda t: " ".join(t))
    df["token_count"] = df["tokens"].apply(len)

    # Remove linhas onde não sobrou nenhum token útil
    df_clean = df[df["token_count"] > 0].copy()

    logger.info(f"Processamento concluído: {len(df_clean)}/{len(df)} artigos válidos.")
    return df_clean


def save_processed_data(df: pd.DataFrame, filename: str = "processed") -> Path:
    """
    Salva DataFrame processado como CSV em data/processed/.

    Args:
        df: DataFrame processado
        filename: nome base do arquivo

    Returns:
        Path do arquivo salvo.
    """
    filepath = PROCESSED_DIR / f"{filename}_{today_str()}.csv"

    # Converte lista de tokens para string antes de salvar (CSV não suporta listas)
    df_save = df.copy()
    if "tokens" in df_save.columns:
        df_save["tokens"] = df_save["tokens"].apply(
            lambda t: "|".join(t) if isinstance(t, list) else t
        )

    df_save.to_csv(filepath, index=False, encoding="utf-8")
    logger.info(f"Dados processados salvos: {filepath.name}")
    return filepath


# ──────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ──────────────────────────────────────────────

def run_processing(
    source: Optional[str] = None,
    date: Optional[str] = None,
    method: str = "lemmatize"
) -> pd.DataFrame:
    """
    Executa o pipeline completo de processamento.

    Args:
        source: filtro de fonte (None = todas)
        date: filtro de data (None = todas)
        method: "lemmatize" ou "stem"

    Returns:
        DataFrame processado e pronto para análise.
    """
    logger.info("=" * 50)
    logger.info("DataPulse — Iniciando processamento de texto")
    logger.info("=" * 50)

    df_raw = load_articles_from_db(source=source, date=date)

    if df_raw.empty:
        logger.error("Nenhum dado encontrado. Execute collect.py primeiro.")
        return pd.DataFrame()

    df_processed = process_dataframe(df_raw, method=method)
    save_processed_data(df_processed)

    logger.info(f"\n✅ Processamento concluído!")
    logger.info(f"   Artigos processados: {len(df_processed)}")
    logger.info(f"   Método de normalização: {method}")

    return df_processed


if __name__ == "__main__":
    df = run_processing()
    if not df.empty:
        print("\n📋 Exemplo de artigo processado:")
        row = df.iloc[0]
        print(f"  Título original : {row['title']}")
        print(f"  Título limpo    : {row['clean_title']}")
        print(f"  Tokens          : {row['tokens'][:10]}...")
        print(f"  Qtd tokens      : {row['token_count']}")
