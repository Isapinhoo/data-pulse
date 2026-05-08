"""
app.py — Dashboard Streamlit do DataPulse
==========================================
Interface visual completa do sistema de radar de tendências.

Seções do dashboard:
  1. 🏠 Visão Geral — métricas rápidas e insights do dia
  2. 📈 Tendências — evolução temporal das palavras-chave
  3. ☁️  Nuvem de Palavras — visualização rápida do vocabulário
  4. 🗂️  Tópicos — clusters de assuntos identificados
  5. 🔄 Coletar Dados — executa o pipeline completo

Como rodar:
  streamlit run dashboard/app.py
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório src ao PATH para importar os módulos
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3

# ──────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA (deve vir antes de tudo)
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="DataPulse — Radar de Tendências",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado para deixar o dashboard mais profissional
st.markdown("""
<style>
    /* Fonte e cores gerais */
    .stApp { background-color: #0e1117; }

    /* Cards de métricas */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #1a1f2e, #252b3b);
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 16px;
    }

    /* Título principal */
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #00d4ff, #7b61ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.2rem;
    }

    .subtitle {
        text-align: center;
        color: #8892a4;
        font-size: 1rem;
        margin-bottom: 2rem;
    }

    /* Cards de insights */
    .insight-card {
        background: linear-gradient(135deg, #1a1f2e, #252b3b);
        border-left: 4px solid #00d4ff;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 10px;
        font-size: 0.95rem;
    }

    .insight-card.growth { border-left-color: #00c853; }
    .insight-card.decline { border-left-color: #ff5252; }
    .insight-card.cluster { border-left-color: #7b61ff; }

    /* Badge de fonte */
    .source-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 4px;
    }
    .hn-badge { background: #ff6600; color: white; }
    .reddit-badge { background: #ff4500; color: white; }

    /* Seção */
    .section-header {
        border-bottom: 2px solid #2d3748;
        padding-bottom: 8px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# IMPORTAÇÕES DOS MÓDULOS DO PROJETO
# ──────────────────────────────────────────────

@st.cache_resource
def load_modules():
    """
    Importa módulos pesados apenas uma vez (cache do Streamlit).
    O @st.cache_resource evita recarregar a cada interação do usuário.
    """
    try:
        from utils import get_db_connection, init_database, DB_PATH
        from collect import run_collection
        from process import load_articles_from_db, process_dataframe
        from analyze import (
            compute_word_frequency, compute_daily_trends,
            cluster_topics, compute_growth_rate, generate_insights
        )
        return {
            "get_db": get_db_connection,
            "init_db": init_database,
            "db_path": DB_PATH,
            "run_collection": run_collection,
            "load_articles": load_articles_from_db,
            "process_df": process_dataframe,
            "word_freq": compute_word_frequency,
            "daily_trends": compute_daily_trends,
            "cluster": cluster_topics,
            "growth": compute_growth_rate,
            "insights": generate_insights,
        }
    except Exception as e:
        st.error(f"Erro ao carregar módulos: {e}")
        return None


# ──────────────────────────────────────────────
# FUNÇÕES DE CARREGAMENTO DE DADOS (com cache)
# ──────────────────────────────────────────────

@st.cache_data(ttl=300)  # cache de 5 minutos
def get_articles_df(source_filter=None, days=7):
    """Carrega artigos do banco com cache para evitar queries repetidas."""
    mods = load_modules()
    if not mods:
        return pd.DataFrame()

    date_limit = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    conn = mods["get_db"]()
    query = "SELECT * FROM articles WHERE date >= ?"
    params = [date_limit]

    if source_filter and source_filter != "Todas":
        query += " AND source LIKE ?"
        params.append(f"%{source_filter.lower()}%")

    try:
        df = pd.read_sql_query(query, conn, params=params)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()

    return df


@st.cache_data(ttl=300)
def get_processed_df(source_filter=None, days=7):
    """Carrega e processa artigos (com cache)."""
    mods = load_modules()
    if not mods:
        return pd.DataFrame()

    df_raw = get_articles_df(source_filter, days)
    if df_raw.empty:
        return pd.DataFrame()

    return mods["process_df"](df_raw)


@st.cache_data(ttl=300)
def get_db_stats():
    """Retorna estatísticas gerais do banco de dados."""
    mods = load_modules()
    if not mods:
        return {}

    conn = mods["get_db"]()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM articles")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT date) FROM articles")
        days = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM articles WHERE date = date('now')")
        today_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT source) FROM articles")
        sources = cursor.fetchone()[0]

        cursor.execute("SELECT MAX(collected_at) FROM articles")
        last_update = cursor.fetchone()[0] or "Nunca"

    except Exception:
        total, days, today_count, sources, last_update = 0, 0, 0, 0, "Nunca"
    finally:
        conn.close()

    return {
        "total": total,
        "days": days,
        "today": today_count,
        "sources": sources,
        "last_update": last_update
    }


# ──────────────────────────────────────────────
# COMPONENTES VISUAIS
# ──────────────────────────────────────────────

def render_wordcloud(df_freq: pd.DataFrame):
    """
    Renderiza nuvem de palavras usando matplotlib + wordcloud.
    Exibe dentro do Streamlit via st.pyplot().
    """
    if df_freq.empty:
        st.info("Sem dados para gerar nuvem de palavras.")
        return

    try:
        from wordcloud import WordCloud
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use("Agg")  # backend sem janela (necessário no Streamlit)

        word_dict = dict(zip(df_freq["word"], df_freq["count"]))

        wc = WordCloud(
            width=900,
            height=450,
            background_color="#0e1117",
            colormap="cool",
            max_words=60,
            max_font_size=120,
            min_font_size=14,
            prefer_horizontal=0.8,
        ).generate_from_frequencies(word_dict)

        fig, ax = plt.subplots(figsize=(12, 5))
        fig.patch.set_facecolor("#0e1117")
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        plt.tight_layout(pad=0)

        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    except ImportError:
        # Fallback: exibe como gráfico de barras horizontal se wordcloud não estiver instalado
        st.warning("Instale 'wordcloud' para a nuvem de palavras. Exibindo gráfico de barras.")
        render_bar_chart(df_freq.head(20))


def render_bar_chart(df_freq: pd.DataFrame, title: str = "Top Palavras"):
    """Gráfico de barras horizontal das palavras mais frequentes."""
    if df_freq.empty:
        return

    fig = px.bar(
        df_freq.head(20).sort_values("count"),
        x="count",
        y="word",
        orientation="h",
        title=title,
        color="count",
        color_continuous_scale="viridis",
        labels={"count": "Frequência", "word": "Palavra"}
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
        showlegend=False,
        coloraxis_showscale=False,
        height=500,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)


def render_trend_lines(df_trends: pd.DataFrame, selected_words: list[str]):
    """Gráfico de linhas mostrando evolução temporal das palavras selecionadas."""
    if df_trends.empty or not selected_words:
        st.info("Selecione palavras para visualizar tendências.")
        return

    # Filtra apenas as colunas selecionadas
    cols_available = [w for w in selected_words if w in df_trends.columns]
    if not cols_available:
        st.warning("Palavras selecionadas não encontradas nas tendências.")
        return

    df_plot = df_trends[cols_available].reset_index()
    df_melted = df_plot.melt(id_vars="date", var_name="Palavra", value_name="Frequência")

    fig = px.line(
        df_melted,
        x="date",
        y="Frequência",
        color="Palavra",
        title="Evolução de Tendências ao Longo do Tempo",
        markers=True,
        line_shape="spline"
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
        height=400,
        xaxis=dict(gridcolor="#2d3748"),
        yaxis=dict(gridcolor="#2d3748"),
        margin=dict(l=10, r=10, t=40, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)


def render_cluster_chart(df_clusters: pd.DataFrame):
    """Gráfico de pizza mostrando distribuição de tópicos."""
    if df_clusters.empty:
        st.info("Execute a análise para visualizar os clusters.")
        return

    fig = px.pie(
        df_clusters,
        values="article_count",
        names="label",
        title="Distribuição de Tópicos",
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.Plasma
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
        height=400,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)


def render_growth_chart(df_growth: pd.DataFrame):
    """Gráfico de barras mostrando crescimento/queda de palavras."""
    if df_growth.empty:
        st.info("Dados insuficientes para calcular crescimento.")
        return

    df_plot = df_growth.head(15).copy()
    df_plot["color"] = df_plot["growth_pct"].apply(
        lambda x: "#00c853" if x >= 0 else "#ff5252"
    )

    fig = go.Figure(go.Bar(
        x=df_plot["growth_pct"],
        y=df_plot["keyword"],
        orientation="h",
        marker_color=df_plot["color"],
        text=df_plot["growth_pct"].apply(lambda x: f"{x:+.0f}%"),
        textposition="outside"
    ))
    fig.update_layout(
        title="Taxa de Crescimento por Palavra (últimos dias)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#e0e0e0",
        height=400,
        xaxis=dict(title="Crescimento (%)", gridcolor="#2d3748", zeroline=True, zerolinecolor="#555"),
        yaxis=dict(title=""),
        margin=dict(l=10, r=60, t=40, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────

def render_sidebar():
    """Renderiza a barra lateral com filtros e controles."""
    with st.sidebar:
        st.markdown("## 📡 DataPulse")
        st.markdown("*Radar Inteligente de Tendências*")
        st.divider()

        st.markdown("### ⚙️ Filtros")

        source = st.selectbox(
            "Fonte de dados",
            ["Todas", "HackerNews", "Reddit"],
            index=0
        )

        days = st.slider(
            "Período (dias)",
            min_value=1, max_value=30, value=7,
            help="Quantos dias de dados analisar"
        )

        top_n = st.slider(
            "Top N palavras",
            min_value=10, max_value=100, value=30,
            help="Quantas palavras exibir nas análises"
        )

        n_clusters = st.slider(
            "Número de tópicos",
            min_value=2, max_value=10, value=6,
            help="Quantos clusters de tópicos identificar"
        )

        st.divider()
        st.markdown("### 🔄 Atualizar Dados")

        if st.button("▶ Coletar Dados Agora", use_container_width=True, type="primary"):
            return source, days, top_n, n_clusters, True

        st.divider()
        st.markdown("### 📌 Sobre")
        st.markdown("""
        **DataPulse** monitora tendências em tempo real em comunidades tech.

        Fontes:
        - 🟠 HackerNews (top stories)
        - 🔴 Reddit (r/technology, r/programming, etc.)

        Pipeline:
        `Coleta → Processamento → Análise → Visualização`
        """)

    return source, days, top_n, n_clusters, False


# ──────────────────────────────────────────────
# LAYOUT PRINCIPAL
# ──────────────────────────────────────────────

def main():
    """Função principal do dashboard."""
    # Garante que o banco existe
    mods = load_modules()
    if mods:
        mods["init_db"]()

    # Sidebar e controles
    source_filter, days, top_n, n_clusters, run_collect = render_sidebar()

    # Título principal
    st.markdown('<h1 class="main-title">📡 DataPulse</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Radar Inteligente de Tendências Tech</p>', unsafe_allow_html=True)

    # ── Execução de coleta (se botão pressionado) ──
    if run_collect:
        with st.status("🔄 Coletando dados...", expanded=True) as status:
            st.write("Conectando ao HackerNews...")
            st.write("Conectando ao Reddit...")
            try:
                articles = mods["run_collection"]()
                st.write(f"✅ {len(articles)} artigos coletados!")
                status.update(label="Coleta concluída!", state="complete")
                # Limpa cache para forçar reload dos dados
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                status.update(label=f"Erro: {e}", state="error")

    # ── Carrega dados ──
    stats = get_db_stats()
    df_raw = get_articles_df(source_filter if source_filter != "Todas" else None, days)
    df_processed = get_processed_df(source_filter if source_filter != "Todas" else None, days)

    # ══════════════════════════════════════════
    # SEÇÃO 1: MÉTRICAS RÁPIDAS
    # ══════════════════════════════════════════
    st.markdown("### 📊 Visão Geral")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de Artigos", f"{stats.get('total', 0):,}", help="Total no banco de dados")
    with col2:
        st.metric("Artigos Hoje", f"{stats.get('today', 0):,}", help="Coletados hoje")
    with col3:
        st.metric("Dias Monitorados", f"{stats.get('days', 0)}", help="Dias com dados")
    with col4:
        st.metric("Fontes Ativas", f"{stats.get('sources', 0)}", help="Fontes conectadas")

    if df_raw.empty:
        st.warning("⚠️ Nenhum dado encontrado. Clique em **Coletar Dados Agora** na barra lateral para começar!")
        st.stop()

    # ── Processa e analisa ──
    if df_processed.empty:
        st.error("Erro no processamento dos dados.")
        st.stop()

    with st.spinner("Analisando tendências..."):
        df_freq = mods["word_freq"](df_processed, top_n=top_n)
        df_trends = mods["daily_trends"](df_processed)
        df_clusters = mods["cluster"](df_processed, n_clusters=n_clusters)
        df_growth = mods["growth"](df_trends) if not df_trends.empty else pd.DataFrame()
        insights = mods["insights"](df_growth, df_freq, df_clusters)

    # ══════════════════════════════════════════
    # SEÇÃO 2: INSIGHTS AUTOMÁTICOS
    # ══════════════════════════════════════════
    if insights:
        st.markdown("### 💡 Insights Automáticos")
        cols = st.columns(min(len(insights), 3))
        for i, insight in enumerate(insights[:6]):
            with cols[i % 3]:
                css_class = insight.get("type", "")
                st.markdown(
                    f'<div class="insight-card {css_class}">'
                    f'{insight["emoji"]} {insight["message"]}'
                    f'</div>',
                    unsafe_allow_html=True
                )

    st.divider()

    # ══════════════════════════════════════════
    # SEÇÃO 3: NUVEM DE PALAVRAS + TOP RANKING
    # ══════════════════════════════════════════
    st.markdown("### ☁️ Nuvem de Palavras & Ranking")

    col_wc, col_bar = st.columns([2, 1])
    with col_wc:
        render_wordcloud(df_freq)
    with col_bar:
        st.markdown("**🏆 Top 10 Palavras**")
        if not df_freq.empty:
            df_top10 = df_freq.head(10)[["rank", "word", "count"]].copy()
            df_top10.columns = ["#", "Palavra", "Menções"]
            df_top10["Palavra"] = df_top10["Palavra"].str.title()
            st.dataframe(
                df_top10,
                use_container_width=True,
                hide_index=True,
                height=350
            )

    st.divider()

    # ══════════════════════════════════════════
    # SEÇÃO 4: TENDÊNCIAS TEMPORAIS
    # ══════════════════════════════════════════
    st.markdown("### 📈 Evolução de Tendências")

    if not df_trends.empty and len(df_trends) > 1:
        # Seletor de palavras para acompanhar
        available_words = list(df_trends.columns)[:20]
        default_words = available_words[:5]

        selected = st.multiselect(
            "Escolha palavras para acompanhar:",
            options=available_words,
            default=default_words
        )
        render_trend_lines(df_trends, selected)

        # Gráfico de crescimento lado a lado
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            render_growth_chart(df_growth)
        with col_g2:
            render_bar_chart(df_freq.head(15), "Frequência Global")
    else:
        st.info("Colete dados de múltiplos dias para visualizar tendências temporais.")
        render_bar_chart(df_freq.head(20), "Top Palavras do Período")

    st.divider()

    # ══════════════════════════════════════════
    # SEÇÃO 5: CLUSTERS DE TÓPICOS
    # ══════════════════════════════════════════
    st.markdown("### 🗂️ Tópicos Identificados")

    if not df_clusters.empty:
        col_pie, col_table = st.columns([1, 1])
        with col_pie:
            render_cluster_chart(df_clusters)
        with col_table:
            st.markdown("**Detalhes dos Clusters**")
            df_show = df_clusters[["label", "keywords_str", "article_count"]].copy()
            df_show.columns = ["Tópico", "Palavras-chave", "Artigos"]
            st.dataframe(df_show, use_container_width=True, hide_index=True)
    else:
        st.info("Dados insuficientes para clusterização. Colete mais dados e tente novamente.")

    st.divider()

    # ══════════════════════════════════════════
    # SEÇÃO 6: DADOS BRUTOS
    # ══════════════════════════════════════════
    with st.expander("🔍 Explorar Artigos Brutos"):
        st.dataframe(
            df_raw[["source", "title", "score", "date", "url"]].head(50),
            use_container_width=True,
            hide_index=True,
            column_config={
                "url": st.column_config.LinkColumn("Link"),
                "score": st.column_config.NumberColumn("⭐ Score"),
                "source": st.column_config.TextColumn("Fonte"),
            }
        )

    # Footer
    st.markdown("---")
    st.markdown(
        '<p style="text-align:center; color:#555; font-size:0.8rem;">'
        f'DataPulse v1.0 • Última atualização: {stats.get("last_update", "N/A")} • '
        'Desenvolvido com Python + Streamlit'
        '</p>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
