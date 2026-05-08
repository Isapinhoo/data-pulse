"""
analyze.py — Motor de Análise do DataPulse
==========================================
Transforma texto processado em insights acionáveis:
  1. Frequência de palavras (quais termos dominam)
  2. Detecção de tendências (crescimento ao longo do tempo)
  3. Clusterização de tópicos (TF-IDF + KMeans)
  4. Insights automáticos ("X cresceu Y% nos últimos dias")

Por que cada técnica?
→ Frequência: visão rápida dos termos mais relevantes
→ Tendências: detecta o que está CRESCENDO, não apenas o que é popular
→ Clustering: agrupa temas similares sem precisar de labels manuais
→ Insights em linguagem natural: torna análise acessível a não-técnicos
"""

import pandas as pd
import numpy as np
import json
from collections import Counter
from typing import Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    get_logger, get_db_connection, init_database,
    today_str, PROCESSED_DIR
)
from process import run_processing, load_articles_from_db, process_dataframe

# Scikit-learn: ferramentas de ML/NLP
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

logger = get_logger("analyze")


# ──────────────────────────────────────────────
# 1. FREQUÊNCIA DE PALAVRAS
# ──────────────────────────────────────────────

def compute_word_frequency(
    df: pd.DataFrame,
    top_n: int = 50,
    date: Optional[str] = None,
    source: Optional[str] = None
) -> pd.DataFrame:
    """
    Calcula as palavras mais frequentes no corpus.

    Args:
        df: DataFrame com coluna 'tokens'
        top_n: quantas palavras retornar
        date: filtro de data
        source: filtro de fonte

    Returns:
        DataFrame com colunas [word, count, rank].
    """
    if df.empty or "tokens" not in df.columns:
        return pd.DataFrame(columns=["word", "count", "rank"])

    # Aplica filtros
    if date:
        df = df[df["date"] == date]
    if source:
        df = df[df["source"].str.contains(source, case=False, na=False)]

    # Achata todas as listas de tokens em um único iterável
    all_tokens = []
    for token_list in df["tokens"]:
        if isinstance(token_list, list):
            all_tokens.extend(token_list)
        elif isinstance(token_list, str):
            # Se foi carregado do CSV (formato "tok1|tok2|...")
            all_tokens.extend(token_list.split("|"))

    if not all_tokens:
        return pd.DataFrame(columns=["word", "count", "rank"])

    counter = Counter(all_tokens)
    top_words = counter.most_common(top_n)

    df_freq = pd.DataFrame(top_words, columns=["word", "count"])
    df_freq["rank"] = range(1, len(df_freq) + 1)

    logger.info(f"Top {top_n} palavras calculadas. Mais frequente: '{df_freq.iloc[0]['word']}' ({df_freq.iloc[0]['count']}x)")
    return df_freq


# ──────────────────────────────────────────────
# 2. DETECÇÃO DE TENDÊNCIAS AO LONGO DO TEMPO
# ──────────────────────────────────────────────

def compute_daily_trends(df: pd.DataFrame, top_keywords: int = 20) -> pd.DataFrame:
    """
    Calcula a frequência diária das palavras mais relevantes.

    Detectar tendências = observar como a frequência de uma palavra
    muda ao longo dos dias. Uma palavra com +50% nos últimos 3 dias
    provavelmente está em alta.

    Args:
        df: DataFrame processado com colunas 'tokens' e 'date'
        top_keywords: quantas palavras monitorar

    Returns:
        DataFrame pivô: linhas = datas, colunas = palavras.
    """
    if df.empty:
        return pd.DataFrame()

    # Passo 1: identifica as top palavras globais para monitorar
    freq = compute_word_frequency(df, top_n=top_keywords)
    if freq.empty:
        return pd.DataFrame()

    keywords_to_track = freq["word"].tolist()

    # Passo 2: conta cada palavra por dia
    daily_counts = []

    for date, group in df.groupby("date"):
        all_tokens = []
        for token_list in group["tokens"]:
            if isinstance(token_list, list):
                all_tokens.extend(token_list)
            elif isinstance(token_list, str):
                all_tokens.extend(token_list.split("|"))

        day_counter = Counter(all_tokens)

        row = {"date": date}
        for keyword in keywords_to_track:
            row[keyword] = day_counter.get(keyword, 0)

        daily_counts.append(row)

    if not daily_counts:
        return pd.DataFrame()

    df_trends = pd.DataFrame(daily_counts).sort_values("date")
    df_trends = df_trends.set_index("date")

    logger.info(f"Tendências calculadas para {len(df_trends)} dias e {len(keywords_to_track)} palavras.")
    return df_trends


def save_trends_to_db(df_trends: pd.DataFrame, source: str = "all") -> None:
    """
    Persiste as tendências diárias no banco SQLite.

    Args:
        df_trends: DataFrame pivô de tendências
        source: identificador da fonte
    """
    if df_trends.empty:
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    for date, row in df_trends.iterrows():
        for keyword, count in row.items():
            if count > 0:
                cursor.execute("""
                    INSERT OR REPLACE INTO trends (keyword, count, date, source)
                    VALUES (?, ?, ?, ?)
                """, (keyword, int(count), date, source))

    conn.commit()
    conn.close()
    logger.info("Tendências salvas no banco de dados.")


# ──────────────────────────────────────────────
# 3. CLUSTERIZAÇÃO DE TÓPICOS (TF-IDF + KMeans)
# ──────────────────────────────────────────────

def cluster_topics(
    df: pd.DataFrame,
    n_clusters: int = 6,
    top_words_per_cluster: int = 8
) -> pd.DataFrame:
    """
    Agrupa artigos em tópicos usando TF-IDF + KMeans.

    Como funciona:
      1. TF-IDF transforma cada artigo em um vetor numérico
         (palavras importantes para AQUELE artigo vs. o corpus todo)
      2. KMeans agrupa artigos com vetores similares
      3. Para cada cluster, extraímos as palavras mais representativas

    Por que TF-IDF e não apenas contagem?
    → "technology" aparece em quase tudo → baixo TF-IDF (não discrimina)
    → "kubernetes" aparece em poucos → alto TF-IDF (muito discriminativo)

    Args:
        df: DataFrame com coluna 'tokens_str'
        n_clusters: número de grupos a criar
        top_words_per_cluster: palavras representativas por cluster

    Returns:
        DataFrame com clusters e suas palavras-chave.
    """
    if df.empty or "tokens_str" not in df.columns:
        logger.warning("Dados insuficientes para clusterização.")
        return pd.DataFrame()

    # Filtra documentos vazios
    df_valid = df[df["tokens_str"].str.strip() != ""].copy()
    if len(df_valid) < n_clusters:
        logger.warning(f"Poucos documentos ({len(df_valid)}) para {n_clusters} clusters.")
        n_clusters = max(2, len(df_valid) // 3)

    logger.info(f"Clusterizando {len(df_valid)} artigos em {n_clusters} tópicos...")

    # TF-IDF: transforma textos em matriz numérica
    # max_features: considera apenas as 500 palavras mais relevantes
    # min_df=2: ignora palavras que aparecem em menos de 2 documentos
    vectorizer = TfidfVectorizer(
        max_features=500,
        min_df=2,
        max_df=0.85,         # ignora palavras em >85% dos docs (muito genéricas)
        ngram_range=(1, 2),  # considera bigramas também: "machine learning"
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(df_valid["tokens_str"])
    except ValueError as e:
        logger.error(f"Erro no TF-IDF: {e}")
        return pd.DataFrame()

    # KMeans: agrupa por similaridade no espaço TF-IDF
    # n_init=10: tenta 10 inicializações diferentes (evita mínimos locais)
    kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    df_valid = df_valid.copy()
    df_valid["cluster"] = kmeans.fit_predict(tfidf_matrix)

    # Extrai palavras mais representativas de cada cluster
    feature_names = vectorizer.get_feature_names_out()
    cluster_info = []

    for cluster_id in range(n_clusters):
        # Centro do cluster no espaço TF-IDF
        center = kmeans.cluster_centers_[cluster_id]
        # Índices das palavras com maior peso no centro
        top_indices = center.argsort()[::-1][:top_words_per_cluster]
        top_words = [feature_names[i] for i in top_indices]

        cluster_size = (df_valid["cluster"] == cluster_id).sum()

        cluster_info.append({
            "cluster_id": cluster_id,
            "keywords": top_words,
            "keywords_str": ", ".join(top_words),
            "article_count": int(cluster_size),
            "label": f"Tópico {cluster_id + 1}: {top_words[0].title()}"
        })

    df_clusters = pd.DataFrame(cluster_info).sort_values("article_count", ascending=False)

    # Adiciona coluna de cluster ao DataFrame original
    df["cluster"] = df_valid["cluster"].reindex(df.index, fill_value=-1)

    logger.info(f"Clusterização concluída: {n_clusters} tópicos identificados.")
    for _, row in df_clusters.iterrows():
        logger.info(f"  Cluster {row['cluster_id']}: {row['keywords_str']} ({row['article_count']} artigos)")

    return df_clusters


# ──────────────────────────────────────────────
# 4. INSIGHTS AUTOMÁTICOS
# ──────────────────────────────────────────────

def compute_growth_rate(
    df_trends: pd.DataFrame,
    days_back: int = 3
) -> pd.DataFrame:
    """
    Calcula a taxa de crescimento de cada palavra nos últimos N dias.

    Fórmula: crescimento = (freq_recente - freq_anterior) / freq_anterior * 100

    Args:
        df_trends: DataFrame pivô com tendências diárias
        days_back: janela de comparação em dias

    Returns:
        DataFrame com [keyword, growth_pct, recent_count, previous_count].
    """
    if df_trends.empty or len(df_trends) < 2:
        return pd.DataFrame()

    # Divide o DataFrame em período recente e período anterior
    mid = max(1, len(df_trends) - days_back)
    recent = df_trends.iloc[mid:]
    previous = df_trends.iloc[:mid]

    recent_sum = recent.sum()
    previous_sum = previous.sum()

    growth_data = []
    for keyword in df_trends.columns:
        prev = previous_sum.get(keyword, 0)
        rec = recent_sum.get(keyword, 0)

        if prev > 0:
            growth_pct = ((rec - prev) / prev) * 100
        elif rec > 0:
            growth_pct = 100.0  # surgiu do nada
        else:
            growth_pct = 0.0

        growth_data.append({
            "keyword": keyword,
            "growth_pct": round(growth_pct, 1),
            "recent_count": int(rec),
            "previous_count": int(prev)
        })

    df_growth = pd.DataFrame(growth_data)
    df_growth = df_growth.sort_values("growth_pct", ascending=False)

    return df_growth


def generate_insights(
    df_growth: pd.DataFrame,
    df_freq: pd.DataFrame,
    df_clusters: pd.DataFrame
) -> list[dict]:
    """
    Gera frases de insight em linguagem natural.

    Exemplos de saída:
      - "🚀 'AI' cresceu 87% nos últimos 3 dias"
      - "📉 'blockchain' caiu 42% nos últimos 3 dias"
      - "🔥 Tópico mais quente: 'machine learning' com 234 menções"
      - "📊 6 clusters identificados, maior grupo: 'AI' (89 artigos)"

    Args:
        df_growth: DataFrame de crescimento de palavras
        df_freq: DataFrame de frequência global
        df_clusters: DataFrame de clusters

    Returns:
        Lista de dicionários com {type, message, value}.
    """
    insights = []

    # Insights de crescimento (top 5 crescendo)
    if not df_growth.empty:
        top_growing = df_growth[df_growth["growth_pct"] > 0].head(5)
        for _, row in top_growing.iterrows():
            insights.append({
                "type": "growth",
                "emoji": "🚀",
                "message": f"'{row['keyword'].title()}' cresceu {row['growth_pct']:.0f}% nos últimos dias",
                "value": row["growth_pct"],
                "keyword": row["keyword"]
            })

        # Top 3 em queda
        top_falling = df_growth[df_growth["growth_pct"] < -20].head(3)
        for _, row in top_falling.iterrows():
            insights.append({
                "type": "decline",
                "emoji": "📉",
                "message": f"'{row['keyword'].title()}' caiu {abs(row['growth_pct']):.0f}% nos últimos dias",
                "value": row["growth_pct"],
                "keyword": row["keyword"]
            })

    # Insight de palavra mais mencionada
    if not df_freq.empty:
        top_word = df_freq.iloc[0]
        insights.append({
            "type": "top_keyword",
            "emoji": "🔥",
            "message": f"Palavra mais mencionada: '{top_word['word'].title()}' com {top_word['count']} ocorrências",
            "value": int(top_word["count"]),
            "keyword": top_word["word"]
        })

    # Insight de clusters
    if not df_clusters.empty:
        top_cluster = df_clusters.iloc[0]
        insights.append({
            "type": "cluster",
            "emoji": "📊",
            "message": f"Tópico dominante: '{top_cluster['keywords'][0].title()}' "
                       f"com {top_cluster['article_count']} artigos agrupados",
            "value": int(top_cluster["article_count"]),
            "keyword": top_cluster["keywords"][0]
        })

    logger.info(f"{len(insights)} insights gerados automaticamente.")
    return insights


# ──────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ──────────────────────────────────────────────

def run_analysis(df: Optional[pd.DataFrame] = None) -> dict:
    """
    Executa o pipeline completo de análise.

    Args:
        df: DataFrame processado (se None, busca do banco)

    Returns:
        Dicionário com todos os resultados da análise:
        {freq, trends, growth, clusters, insights}
    """
    logger.info("=" * 50)
    logger.info("DataPulse — Iniciando análise de tendências")
    logger.info("=" * 50)

    # Carrega e processa dados se necessário
    if df is None:
        df_raw = load_articles_from_db()
        if df_raw.empty:
            logger.error("Sem dados. Execute collect.py primeiro.")
            return {}
        df = process_dataframe(df_raw)

    if df.empty:
        logger.error("Nenhum dado processado disponível.")
        return {}

    # 1. Frequência de palavras
    logger.info("\n[1/4] Calculando frequência de palavras...")
    df_freq = compute_word_frequency(df, top_n=50)

    # 2. Tendências diárias
    logger.info("\n[2/4] Detectando tendências ao longo do tempo...")
    df_trends = compute_daily_trends(df, top_keywords=20)
    if not df_trends.empty:
        save_trends_to_db(df_trends)

    # 3. Clusterização
    logger.info("\n[3/4] Clusterizando tópicos com TF-IDF + KMeans...")
    df_clusters = cluster_topics(df, n_clusters=6)

    # 4. Taxa de crescimento e insights
    logger.info("\n[4/4] Gerando insights automáticos...")
    df_growth = compute_growth_rate(df_trends) if not df_trends.empty else pd.DataFrame()
    insights = generate_insights(df_growth, df_freq, df_clusters)

    results = {
        "freq": df_freq,
        "trends": df_trends,
        "growth": df_growth,
        "clusters": df_clusters,
        "insights": insights,
        "df_processed": df
    }

    logger.info(f"\n✅ Análise concluída!")
    logger.info(f"   Palavras analisadas  : {len(df_freq)}")
    logger.info(f"   Dias monitorados     : {len(df_trends)}")
    logger.info(f"   Clusters identificados: {len(df_clusters)}")
    logger.info(f"   Insights gerados     : {len(insights)}")

    return results


if __name__ == "__main__":
    results = run_analysis()
    if results:
        print("\n🔍 TOP 10 PALAVRAS:")
        print(results["freq"].head(10).to_string(index=False))

        print("\n💡 INSIGHTS AUTOMÁTICOS:")
        for insight in results["insights"]:
            print(f"  {insight['emoji']} {insight['message']}")

        print("\n🗂️  CLUSTERS DE TÓPICOS:")
        if not results["clusters"].empty:
            for _, row in results["clusters"].iterrows():
                print(f"  Tópico {row['cluster_id']}: {row['keywords_str']} ({row['article_count']} artigos)")
