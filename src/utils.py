"""
utils.py — Funções utilitárias do DataPulse
============================================
Centraliza logging, conexão com banco de dados SQLite,
e helpers reutilizáveis por todos os módulos do projeto.

Por que isso importa:
  - Evita repetição de código (DRY: Don't Repeat Yourself)
  - Facilita manutenção: mude aqui, reflete em tudo
  - Padrão de projetos reais em empresas de dados
"""

import sqlite3
import logging
import os
from datetime import datetime
from pathlib import Path

# ──────────────────────────────────────────────
# CAMINHOS BASE DO PROJETO
# ──────────────────────────────────────────────

# Path(__file__) é o caminho deste arquivo (utils.py)
# .parent sobe um nível → src/
# .parent novamente → data-pulse/ (raiz do projeto)
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DB_PATH = DATA_DIR / "datapulse.db"

# Garante que os diretórios existam ao importar o módulo
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────
# CONFIGURAÇÃO DE LOGGING
# ──────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """
    Retorna um logger configurado com formatação padronizada.

    Por que usar logging em vez de print()?
    → Logs têm timestamp, nível (INFO/WARNING/ERROR) e origem.
    → Em produção, você pode redirecionar logs para arquivos ou serviços.

    Args:
        name: nome do módulo (ex: "collect", "process")

    Returns:
        Logger configurado e pronto para uso.
    """
    logger = logging.getLogger(name)

    # Evita adicionar handlers duplicados se a função for chamada várias vezes
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Formato: [2024-01-15 14:32:01] INFO | collect | Mensagem aqui
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler para o console (terminal)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# ──────────────────────────────────────────────
# BANCO DE DADOS SQLite
# ──────────────────────────────────────────────

def get_db_connection() -> sqlite3.Connection:
    """
    Abre e retorna uma conexão com o banco SQLite.

    Por que SQLite?
    → Zero configuração, arquivo único, perfeito para portfólio.
    → Para escalar para produção, bastaria trocar por PostgreSQL.

    Returns:
        Conexão SQLite com row_factory configurada para retornar dicts.
    """
    conn = sqlite3.connect(DB_PATH)
    # row_factory permite acessar colunas pelo nome: row["titulo"]
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    """
    Cria as tabelas do banco caso ainda não existam.

    Tabelas:
      - articles: dados brutos coletados das APIs
      - trends: tendências calculadas ao longo do tempo
      - keywords: frequência de palavras por dia
    """
    logger = get_logger("utils")
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabela principal: artigos/posts coletados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source      TEXT NOT NULL,           -- "hackernews" ou "reddit"
            title       TEXT NOT NULL,
            text        TEXT,
            url         TEXT,
            score       INTEGER DEFAULT 0,       -- upvotes/pontos
            collected_at TEXT NOT NULL,          -- timestamp da coleta
            date        TEXT NOT NULL            -- data do post (YYYY-MM-DD)
        )
    """)

    # Tabela de tendências diárias
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trends (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword     TEXT NOT NULL,
            count       INTEGER NOT NULL,
            date        TEXT NOT NULL,           -- YYYY-MM-DD
            source      TEXT NOT NULL,
            UNIQUE(keyword, date, source)        -- evita duplicatas
        )
    """)

    # Tabela de clusters/tópicos detectados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cluster_id  INTEGER NOT NULL,
            keywords    TEXT NOT NULL,           -- JSON string com top keywords
            article_count INTEGER NOT NULL,
            date        TEXT NOT NULL,
            source      TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    logger.info(f"Banco de dados inicializado em: {DB_PATH}")


# ──────────────────────────────────────────────
# HELPERS GERAIS
# ──────────────────────────────────────────────

def today_str() -> str:
    """Retorna a data de hoje no formato YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


def now_str() -> str:
    """Retorna o timestamp atual no formato YYYY-MM-DD HH:MM:SS."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def save_raw_json(data: list, filename: str) -> Path:
    """
    Salva dados brutos como JSON no diretório data/raw/.

    Args:
        data: lista de dicionários a salvar
        filename: nome do arquivo (sem extensão)

    Returns:
        Path do arquivo salvo.
    """
    import json
    filepath = RAW_DIR / f"{filename}_{today_str()}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    get_logger("utils").info(f"Dados brutos salvos: {filepath.name} ({len(data)} registros)")
    return filepath


def load_raw_json(filename_pattern: str) -> list:
    """
    Carrega o arquivo JSON mais recente que corresponda ao padrão.

    Args:
        filename_pattern: prefixo do arquivo (ex: "hackernews")

    Returns:
        Lista de dicionários carregada do JSON.
    """
    import json
    files = sorted(RAW_DIR.glob(f"{filename_pattern}_*.json"), reverse=True)
    if not files:
        get_logger("utils").warning(f"Nenhum arquivo encontrado para padrão: {filename_pattern}")
        return []
    with open(files[0], "r", encoding="utf-8") as f:
        data = json.load(f)
    get_logger("utils").info(f"Carregado: {files[0].name} ({len(data)} registros)")
    return data
