from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.theme import (
    apply_theme,
    style_fig,
    MUTED,
    BLUE,
    CYAN,
    SKY,
    POSITIVE,
    NEGATIVE,
    NEUTRAL,
)

# ============================================================
# 1. 页面设置
# ============================================================

st.set_page_config(
    page_title="数据总览｜上市公司事件智能分析",
    page_icon="📊",
    layout="wide",
)

apply_theme()

# ============================================================
# 2. 数据路径
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

# ============================================================
# 3. 数据读取
# ============================================================

@st.cache_data
def load_data():
    extraction = pd.read_excel(
        DATA_DIR / "01_event_extraction.xlsx",
        sheet_name="事件实例",
    )

    clusters = pd.read_excel(
        DATA_DIR / "event_clusters.xlsx",
        sheet_name="事件簇",
    )

    members = pd.read_excel(
        DATA_DIR / "event_clusters.xlsx",
        sheet_name="成员映射",
    )

    extraction["article_publish_time"] = pd.to_datetime(
        extraction["article_publish_time"],
        errors="coerce",
    )

    return extraction, clusters, members


df, cluster_df, member_df = load_data()

# ============================================================
# 4. 标题
# ============================================================

st.title("📊 数据总览｜事件智能感知")

st.markdown(
    """
    <div class="section-subtitle">
    从全局视角观察金融事件类型、情绪方向、时间趋势、上市公司、
    行业与信息来源的整体分布。
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 5. 侧边栏筛选
# ============================================================

st.sidebar.markdown("## 🔎 数据总览筛选")
st.sidebar.caption("筛选条件会同步作用于本页面全部图表。")

filtered = df.copy()

valid_dates = filtered["article_publish_time"].dropna()

if not valid_dates.empty:
    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()

    date_range = st.sidebar.date_input(
        "发布时间",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start_date, end_date = date_range
        filtered = filtered[
            (filtered["article_publish_time"].dt.date >= start_date)
            & (filtered["article_publish_time"].dt.date <= end_date)
        ]

event_types = sorted(
    filtered["event_type"].dropna().astype(str).unique().tolist()
)

selected_types = st.sidebar.multiselect(
    "事件类型",
    event_types,
    placeholder="默认全部事件类型",
)

if selected_types:
    filtered = filtered[filtered["event_type"].isin(selected_types)]

emotion_order = ["正面", "中性", "负面"]
emotion_options = [
    x for x in emotion_order
    if x in filtered["event_emotion"].dropna().unique()
]

selected_emotions = st.sidebar.multiselect(
    "事件情绪",
    emotion_options,
    placeholder="默认全部情绪",
)

if selected_emotions:
    filtered = filtered[filtered["event_emotion"].isin(selected_emotions)]

industry_options = sorted(
    filtered["industry_name"].dropna().astype(str).unique().tolist()
)

selected_industries = st.sidebar.multiselect(
    "行业",
    industry_options,
    placeholder="默认全部行业",
)

if selected_industries:
    filtered = filtered[filtered["industry_name"].isin(selected_industries)]

st.sidebar.markdown("---")
st.sidebar.caption(f"当前筛选：{len(filtered):,} 条事件实例")

# ============================================================
# 6. 聚合事件数量
# ============================================================

filtered_ids = set(filtered["event_instance_id"].dropna().astype(str))

member_temp = member_df.copy()
member_temp["event_instance_id"] = member_temp["event_instance_id"].astype(str)

filtered_cluster_count = (
    member_temp[
        member_temp["event_instance_id"].isin(filtered_ids)
    ]["cluster_id"]
    .nunique()
)

# ============================================================
# 7. KPI
# ============================================================

company_count = filtered["secu_abbr"].dropna().nunique()
industry_count = filtered["industry_name"].dropna().nunique()
source_count = filtered["article_source"].dropna().nunique()

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("事件实例", f"{len(filtered):,}")
k2.metric("聚合事件", f"{filtered_cluster_count:,}")
k3.metric("上市公司", f"{company_count:,}")
k4.metric("覆盖行业", f"{industry_count:,}")
k5.metric("新闻来源", f"{source_count:,}")

st.markdown("---")

# ============================================================
# 8. 事件类型 + 情绪结构
# ============================================================

left, right = st.columns([1.35, 1])

with left:
    type_counts = (
        filtered["event_type"]
        .fillna("未分类")
        .value_counts()
        .reset_index()
    )
    type_counts.columns = ["事件类型", "事件实例数"]

    fig_type = px.bar(
        type_counts.sort_values("事件实例数", ascending=True),
        x="事件实例数",
        y="事件类型",
        orientation="h",
        text="事件实例数",
    )

    fig_type.update_traces(
        marker_color=BLUE,
        marker_line_color=CYAN,
        marker_line_width=0.6,
        textposition="outside",
        cliponaxis=False,
    )

    style_fig(fig_type, "事件类型分布", height=430, left_margin=180)
    fig_type.update_yaxes(automargin=True)

    st.plotly_chart(
        fig_type,
        use_container_width=True,
        theme=None,
        config={"displaylogo": False},
    )

with right:
    emotion_counts = (
        filtered["event_emotion"]
        .fillna("未知")
        .value_counts()
        .reset_index()
    )
    emotion_counts.columns = ["事件情绪", "事件实例数"]

    sentiment_colors = {
        "正面": POSITIVE,
        "中性": NEUTRAL,
        "负面": NEGATIVE,
        "未知": MUTED,
    }

    fig_emotion = px.pie(
        emotion_counts,
        names="事件情绪",
        values="事件实例数",
        hole=0.58,
        color="事件情绪",
        color_discrete_map=sentiment_colors,
    )

    fig_emotion.update_traces(
        textinfo="percent+label",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "事件实例：%{value}<br>"
            "占比：%{percent}"
            "<extra></extra>"
        ),
    )

    style_fig(fig_emotion, "事件情绪结构", height=430)

    st.plotly_chart(
        fig_emotion,
        use_container_width=True,
        theme=None,
        config={"displaylogo": False},
    )

# ============================================================
# 9. 时间趋势
# ============================================================

st.markdown("### 📈 事件时间趋势")

trend_data = filtered[filtered["article_publish_time"].notna()].copy()

if trend_data.empty:
    st.info("当前筛选条件下没有有效发布时间。")
else:
    trend_data["日期"] = trend_data["article_publish_time"].dt.date

    trend = (
        trend_data
        .groupby(["日期", "event_emotion"], dropna=False)
        .size()
        .reset_index(name="事件实例数")
    )

    trend["event_emotion"] = trend["event_emotion"].fillna("未知")

    fig_trend = px.line(
        trend,
        x="日期",
        y="事件实例数",
        color="event_emotion",
        markers=True,
        color_discrete_map={
            "正面": POSITIVE,
            "中性": NEUTRAL,
            "负面": NEGATIVE,
            "未知": MUTED,
        },
        labels={"event_emotion": "事件情绪"},
    )

    fig_trend.update_traces(
        line=dict(width=2.3),
        marker=dict(size=5),
    )

    style_fig(
        fig_trend,
        "事件实例随时间变化｜按情绪拆分",
        height=450,
    )

    fig_trend.update_layout(hovermode="x unified")

    st.plotly_chart(
        fig_trend,
        use_container_width=True,
        theme=None,
        config={"displaylogo": False},
    )

# ============================================================
# 10. 行业 × 事件类型热力图
# ============================================================

st.markdown("### 🔥 行业 × 事件类型态势")

heat_data = filtered[
    filtered["industry_name"].notna()
    & filtered["event_type"].notna()
].copy()

if heat_data.empty:
    st.info("当前筛选条件下没有可用于行业热力图的数据。")
else:
    heat_pivot = pd.pivot_table(
        heat_data,
        index="industry_name",
        columns="event_type",
        values="event_instance_id",
        aggfunc="count",
        fill_value=0,
    )

    heat_pivot = heat_pivot.loc[
        heat_pivot.sum(axis=1)
        .sort_values(ascending=True)
        .index
    ]

    fig_heat = go.Figure(
        data=go.Heatmap(
            z=heat_pivot.values,
            x=heat_pivot.columns,
            y=heat_pivot.index,
            colorscale=[
                [0.00, "#081522"],
                [0.20, "#102F50"],
                [0.45, "#145D8A"],
                [0.70, "#2F80FF"],
                [1.00, "#38C9FF"],
            ],
            colorbar=dict(
                title="事件实例数",
                tickfont=dict(color=MUTED),
            ),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "事件类型：%{x}<br>"
                "事件实例数：%{z}"
                "<extra></extra>"
            ),
        )
    )

    style_fig(
        fig_heat,
        "行业 × 事件类型热力图",
        height=max(560, 30 * len(heat_pivot)),
        left_margin=190,
        bottom_margin=105,
    )

    fig_heat.update_xaxes(
        automargin=True,
        tickangle=-20,
    )

    fig_heat.update_yaxes(
        automargin=True,
    )

    st.plotly_chart(
        fig_heat,
        use_container_width=True,
        theme=None,
        config={"displaylogo": False},
    )

# ============================================================
# 11. 公司 Top10 + 来源 Top10
# ============================================================

col_company, col_source = st.columns(2)

with col_company:
    company_counts = (
        filtered[filtered["secu_abbr"].notna()]
        .groupby("secu_abbr")["event_instance_id"]
        .nunique()
        .sort_values(ascending=False)
        .head(10)
        .sort_values()
        .reset_index(name="事件实例数")
    )

    if company_counts.empty:
        st.info("暂无上市公司数据。")
    else:
        fig_company = px.bar(
            company_counts,
            x="事件实例数",
            y="secu_abbr",
            orientation="h",
            text="事件实例数",
        )

        fig_company.update_traces(
            marker_color=CYAN,
            textposition="outside",
            cliponaxis=False,
        )

        style_fig(fig_company, "上市公司事件 Top10", height=470, left_margin=175)
        fig_company.update_yaxes(title="", automargin=True)

        st.plotly_chart(
            fig_company,
            use_container_width=True,
            theme=None,
            config={"displaylogo": False},
        )

with col_source:
    source_counts = (
        filtered[filtered["article_source"].notna()]
        .groupby("article_source")["event_instance_id"]
        .nunique()
        .sort_values(ascending=False)
        .head(10)
        .sort_values()
        .reset_index(name="事件实例数")
    )

    if source_counts.empty:
        st.info("暂无新闻来源数据。")
    else:
        fig_source = px.bar(
            source_counts,
            x="事件实例数",
            y="article_source",
            orientation="h",
            text="事件实例数",
        )

        fig_source.update_traces(
            marker_color=SKY,
            textposition="outside",
            cliponaxis=False,
        )

        style_fig(fig_source, "新闻来源 Top10", height=470, left_margin=180)
        fig_source.update_yaxes(title="", automargin=True)

        st.plotly_chart(
            fig_source,
            use_container_width=True,
            theme=None,
            config={"displaylogo": False},
        )

# ============================================================
# 12. 数据明细
# ============================================================

st.markdown("---")
st.markdown("### 📋 当前筛选事件明细")

detail_cols = [
    "article_publish_time",
    "article_source",
    "secu_abbr",
    "industry_name",
    "event_type",
    "event_emotion",
    "event_name",
]

detail_cols = [c for c in detail_cols if c in filtered.columns]

detail = (
    filtered[detail_cols]
    .sort_values(
        "article_publish_time",
        ascending=False,
        na_position="last",
    )
    .head(300)
)

detail = detail.rename(
    columns={
        "article_publish_time": "发布时间",
        "article_source": "来源",
        "secu_abbr": "上市公司",
        "industry_name": "行业",
        "event_type": "事件类型",
        "event_emotion": "情绪",
        "event_name": "事件名称",
    }
)

st.dataframe(
    detail,
    use_container_width=True,
    hide_index=True,
)
