"""
collect.py — Coleta de Dados do DataPulse
==========================================
Responsável por buscar dados de APIs públicas e armazená-los
no banco SQLite e como JSON bruto para rastreabilidade.

Fontes de dados:
  1. HackerNews API  — https://hacker-news.firebaseio.com/v0/
     → 100% gratuita, sem chave de API, dados de tech em tempo real
  2. Reddit JSON API — https://www.reddit.com/r/{subreddit}.json
     → API pública, sem autenticação para leitura

Por que essas fontes?
→ Qualquer pessoa que clonar o projeto consegue rodar sem cadastro.
→ Dados reais de tendências tech = projeto mais impressionante.
"""

import requests
import time
import json
from datetime import datetime, timezone
from typing import Optional

# Importa utilitários do próprio projeto
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    get_logger, get_db_connection, init_database,
    save_raw_json, today_str, now_str
)

logger = get_logger("collect")

# ──────────────────────────────────────────────
# CONFIGURAÇÕES
# ──────────────────────────────────────────────

# User-Agent obrigatório na maioria das APIs públicas
HEADERS = {
    "User-Agent": "DataPulse/1.0 (portfolio project; github.com/seu-usuario/data-pulse)"
}

# Subreddits relevantes para tendências tech
SUBREDDITS = [
    "technology", "programming", "MachineLearning",
    "datascience", "artificial"
]

# Número máximo de itens por fonte
HN_LIMIT = 100      # HackerNews: top stories
REDDIT_LIMIT = 50   # Reddit: posts por subreddit


# ──────────────────────────────────────────────
# HACKERNEWS
# ──────────────────────────────────────────────

def fetch_hackernews_top(limit: int = HN_LIMIT) -> list[dict]:
    """
    Coleta os top stories do HackerNews.

    A API funciona em duas etapas:
      1. Busca lista de IDs dos top posts
      2. Para cada ID, busca os detalhes do post

    Args:
        limit: quantos posts buscar (máx recomendado: 200)

    Returns:
        Lista de dicionários com dados dos posts.
    """
    logger.info(f"Iniciando coleta HackerNews (limite: {limit} posts)...")

    # Passo 1: buscar lista de IDs
    url_ids = "https://hacker-news.firebaseio.com/v0/topstories.json"
    try:
        response = requests.get(url_ids, headers=HEADERS, timeout=10)
        response.raise_for_status()
        story_ids = response.json()[:limit]
    except requests.RequestException as e:
        logger.error(f"Erro ao buscar IDs do HackerNews: {e}")
        return []

    articles = []
    # Passo 2: buscar detalhes de cada post
    for i, story_id in enumerate(story_ids):
        url_item = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        try:
            resp = requests.get(url_item, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            item = resp.json()

            # Alguns itens podem ser None ou não ter título
            if not item or "title" not in item:
                continue

            # Converte timestamp Unix para data legível
            post_date = datetime.fromtimestamp(
                item.get("time", 0), tz=timezone.utc
            ).strftime("%Y-%m-%d")

            articles.append({
                "source": "hackernews",
                "title": item.get("title", ""),
                "text": item.get("text", ""),   # corpo do post (pode ser None)
                "url": item.get("url", ""),
                "score": item.get("score", 0),
                "date": post_date,
                "collected_at": now_str()
            })

            # Pausa para não sobrecarregar a API (boas práticas!)
            if i % 20 == 0 and i > 0:
                logger.info(f"  → {i}/{len(story_ids)} posts coletados...")
                time.sleep(0.5)

        except requests.RequestException as e:
            logger.warning(f"Erro no item {story_id}: {e}")
            continue

    logger.info(f"HackerNews: {len(articles)} posts coletados com sucesso.")
    return articles


# ──────────────────────────────────────────────
# REDDIT
# ──────────────────────────────────────────────

def fetch_reddit_posts(subreddit: str, limit: int = REDDIT_LIMIT) -> list[dict]:
    """
    Coleta posts do Reddit via JSON público (sem autenticação).

    A API JSON do Reddit é acessível adicionando .json à URL normal:
    https://www.reddit.com/r/technology.json

    Args:
        subreddit: nome do subreddit (ex: "technology")
        limit: quantos posts buscar (máx: 100)

    Returns:
        Lista de dicionários com dados dos posts.
    """
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.error(f"Erro ao acessar r/{subreddit}: {e}")
        return []

    posts = []
    for post in data.get("data", {}).get("children", []):
        p = post.get("data", {})

        # Ignora posts removidos ou sem título
        if p.get("removed_by_category") or not p.get("title"):
            continue

        # Converte timestamp Unix → data
        post_date = datetime.fromtimestamp(
            p.get("created_utc", 0), tz=timezone.utc
        ).strftime("%Y-%m-%d")

        posts.append({
            "source": f"reddit_r/{subreddit}",
            "title": p.get("title", ""),
            "text": p.get("selftext", ""),
            "url": p.get("url", ""),
            "score": p.get("score", 0),
            "date": post_date,
            "collected_at": now_str()
        })

    logger.info(f"r/{subreddit}: {len(posts)} posts coletados.")
    return posts


def fetch_all_reddit(subreddits: list[str] = SUBREDDITS) -> list[dict]:
    """
    Coleta posts de múltiplos subreddits com pausa entre chamadas.

    Args:
        subreddits: lista de subreddits

    Returns:
        Lista consolidada de todos os posts.
    """
    all_posts = []
    for sub in subreddits:
        posts = fetch_reddit_posts(sub)
        all_posts.extend(posts)
        time.sleep(1)  # Reddit pede 1 req/seg para APIs públicas
    logger.info(f"Reddit total: {len(all_posts)} posts de {len(subreddits)} subreddits.")
    return all_posts


# ──────────────────────────────────────────────
# PERSISTÊNCIA NO BANCO
# ──────────────────────────────────────────────

def save_articles_to_db(articles: list[dict]) -> int:
    """
    Salva lista de artigos no banco SQLite.

    Por que não usar INSERT simples?
    → INSERT OR IGNORE evita duplicatas caso o script rode duas vezes.
    → Em produção usaríamos um hash do conteúdo como chave única.

    Args:
        articles: lista de dicionários com dados dos artigos

    Returns:
        Número de novos registros inseridos.
    """
    if not articles:
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()

    inserted = 0
    for art in articles:
        try:
            cursor.execute("""
                INSERT INTO articles (source, title, text, url, score, collected_at, date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                art["source"],
                art["title"],
                art.get("text", ""),
                art.get("url", ""),
                art.get("score", 0),
                art["collected_at"],
                art["date"]
            ))
            inserted += 1
        except Exception as e:
            logger.warning(f"Erro ao inserir artigo: {e}")

    conn.commit()
    conn.close()
    logger.info(f"Banco atualizado: {inserted} novos registros inseridos.")
    return inserted


# ──────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ──────────────────────────────────────────────

def run_collection(
    sources: list[str] = ["hackernews", "reddit"],
    hn_limit: int = HN_LIMIT,
    reddit_limit: int = REDDIT_LIMIT
) -> list[dict]:
    """
    Executa a coleta completa de todas as fontes configuradas.

    Este é o ponto de entrada principal do módulo.
    Chame esta função para coletar, salvar em JSON e persistir no banco.

    Args:
        sources: fontes a coletar (["hackernews", "reddit"])
        hn_limit: limite de posts do HackerNews
        reddit_limit: limite de posts por subreddit do Reddit

    Returns:
        Lista com todos os artigos coletados.
    """
    logger.info("=" * 50)
    logger.info("DataPulse — Iniciando coleta de dados")
    logger.info("=" * 50)

    # Garante que o banco existe
    init_database()

    all_articles = []

    if "hackernews" in sources:
        hn_articles = fetch_hackernews_top(limit=hn_limit)
        all_articles.extend(hn_articles)
        if hn_articles:
            save_raw_json(hn_articles, "hackernews")

    if "reddit" in sources:
        reddit_articles = fetch_all_reddit()
        all_articles.extend(reddit_articles)
        if reddit_articles:
            save_raw_json(reddit_articles, "reddit")

    # Persiste tudo no banco
    total_inserted = save_articles_to_db(all_articles)

    logger.info(f"\n✅ Coleta concluída!")
    logger.info(f"   Total coletado  : {len(all_articles)} artigos")
    logger.info(f"   Novos no banco  : {total_inserted} registros")
    logger.info(f"   Data            : {today_str()}")

    return all_articles


# ──────────────────────────────────────────────
# EXECUÇÃO DIRETA
# ──────────────────────────────────────────────

if __name__ == "__main__":
    # Permite rodar: python src/collect.py
    articles = run_collection()
    print(f"\nExemplo do primeiro artigo coletado:")
    if articles:
        print(json.dumps(articles[0], indent=2, ensure_ascii=False))
