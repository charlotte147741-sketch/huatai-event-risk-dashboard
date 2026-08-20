from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.theme import (
    apply_theme,
    style_fig,
    PANEL,
    GRID,
    TEXT,
    MUTED,
    BLUE,
    CYAN,
    SKY,
    POSITIVE,
    NEGATIVE,
    NEUTRAL,
    WARNING,
)

# ============================================================
# 1. 页面设置
# ============================================================

st.set_page_config(
    page_title="可信评估｜上市公司事件智能分析",
    page_icon="🛡️",
    layout="wide",
)

apply_theme()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

# ============================================================
# 2. 数据读取与字段标准化
# ============================================================

@st.cache_data
def load_credibility():
    df = pd.read_excel(
        DATA_DIR / "02_credibility.xlsx",
        sheet_name="可信评估",
    )

    if "article_publish_time" in df.columns:
        df["article_publish_time"] = pd.to_datetime(
            df["article_publish_time"],
            errors="coerce",
        )

    return df


df = load_credibility()


def to_bool_series(series):
    if series.dtype == bool:
        return series

    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map({
            "true": True,
            "false": False,
            "1": True,
            "0": False,
            "是": True,
            "否": False,
        })
        .fillna(False)
    )


def score_100(series):
    s = pd.to_numeric(series, errors="coerce")

    valid = s.dropna()

    if not valid.empty and valid.max() <= 1.5:
        s = s * 100

    return s


score_cols = [
    "credibility_score",
    "source_authority_score",
    "official_corrob_score",
    "multi_source_consistency_score",
    "propagation_score",
]

for col in score_cols:
    if col in df.columns:
        df[col + "_100"] = score_100(df[col])

if "official_flag" in df.columns:
    df["official_flag_bool"] = to_bool_series(df["official_flag"])
else:
    df["official_flag_bool"] = False

if "low_quality_flag" in df.columns:
    df["low_quality_flag_bool"] = to_bool_series(df["low_quality_flag"])
else:
    df["low_quality_flag_bool"] = False

# ============================================================
# 3. 页面标题
# ============================================================

st.title("🛡️ 可信评估｜多源证据与辨伪分析")

st.markdown(
    """
    <div class="section-subtitle">
    从信源权威、官方佐证、多源一致性与传播可信度四个维度，
    对新闻事件进行可信度量化，并识别待核验、低可信与低质量内容。
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 4. 侧边栏筛选
# ============================================================

st.sidebar.markdown("## 🔎 可信评估筛选")
st.sidebar.caption("筛选条件会同步作用于本页面全部图表。")

filtered = df.copy()

# 日期
if "article_publish_time" in filtered.columns:
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

# 可信等级
level_order = ["高可信", "中可信", "待核验", "低可信"]

level_options = [
    x for x in level_order
    if x in filtered["credibility_level"].dropna().unique()
]

selected_levels = st.sidebar.multiselect(
    "可信等级",
    level_options,
    placeholder="默认全部可信等级",
)

if selected_levels:
    filtered = filtered[
        filtered["credibility_level"].isin(selected_levels)
    ]

# 事件类型
event_type_options = sorted(
    filtered["event_type"].dropna().astype(str).unique().tolist()
)

selected_event_types = st.sidebar.multiselect(
    "事件类型",
    event_type_options,
    placeholder="默认全部事件类型",
)

if selected_event_types:
    filtered = filtered[
        filtered["event_type"].isin(selected_event_types)
    ]

# 情绪
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
    filtered = filtered[
        filtered["event_emotion"].isin(selected_emotions)
    ]

# 官方/非官方
official_filter = st.sidebar.radio(
    "信息属性",
    ["全部", "含官方信息", "非官方信息"],
    index=0,
)

if official_filter == "含官方信息":
    filtered = filtered[filtered["official_flag_bool"]]
elif official_filter == "非官方信息":
    filtered = filtered[~filtered["official_flag_bool"]]

# 最低来源样本数：用于来源排行榜
min_source_samples = st.sidebar.slider(
    "来源排行最低样本数",
    min_value=1,
    max_value=20,
    value=3,
    step=1,
)

st.sidebar.markdown("---")
st.sidebar.caption(f"当前筛选：{len(filtered):,} 条可信评估记录")

# ============================================================
# 5. KPI
# ============================================================

total = len(filtered)

level_counts = (
    filtered["credibility_level"]
    .value_counts()
    .to_dict()
)

avg_score = (
    filtered["credibility_score_100"].mean()
    if "credibility_score_100" in filtered.columns
    else np.nan
)

official_count = int(filtered["official_flag_bool"].sum())
low_quality_count = int(filtered["low_quality_flag_bool"].sum())

k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("评估记录", f"{total:,}")
k2.metric("高可信", f"{level_counts.get('高可信', 0):,}")
k3.metric("中可信", f"{level_counts.get('中可信', 0):,}")
k4.metric("待核验", f"{level_counts.get('待核验', 0):,}")
k5.metric("低可信", f"{level_counts.get('低可信', 0):,}")
k6.metric(
    "平均可信度",
    "-" if pd.isna(avg_score) else f"{avg_score:.1f}",
)

st.markdown(
    f"""
    <div class="blue-note">
    当前筛选中，官方信息记录 <b>{official_count:,}</b> 条，
    低质量内容标记 <b>{low_quality_count:,}</b> 条。
    可信等级与低质量识别是不同概念：低质量内容可能需要过滤或降权，
    可信等级则反映综合可信评估结果。
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 6. 可信等级分布 + 四维机制雷达
# ============================================================

left, right = st.columns([1.15, 1])

LEVEL_COLORS = {
    "高可信": CYAN,
    "中可信": BLUE,
    "待核验": SKY,
    "低可信": "#365A7A",
}

with left:
    level_df = (
        filtered["credibility_level"]
        .fillna("未知")
        .value_counts()
        .reindex(level_order + ["未知"])
        .dropna()
        .reset_index()
    )

    level_df.columns = ["可信等级", "记录数"]

    fig_level = px.bar(
        level_df.sort_values("记录数", ascending=True),
        x="记录数",
        y="可信等级",
        orientation="h",
        text="记录数",
        color="可信等级",
        color_discrete_map={
            **LEVEL_COLORS,
            "未知": MUTED,
        },
    )

    fig_level.update_traces(
        textposition="outside",
        cliponaxis=False,
    )

    style_fig(
        fig_level,
        "可信等级分布",
        height=440,
        left_margin=130,
    )

    fig_level.update_layout(showlegend=False)

    st.plotly_chart(
        fig_level,
        use_container_width=True,
        theme=None,
        config={"displaylogo": False},
    )

with right:
    mechanism_map = {
        "信源权威": "source_authority_score_100",
        "官方佐证": "official_corrob_score_100",
        "多源一致性": "multi_source_consistency_score_100",
        "传播可信度": "propagation_score_100",
    }

    radar_labels = []
    radar_values = []

    for label, col in mechanism_map.items():
        if col in filtered.columns:
            radar_labels.append(label)
            radar_values.append(
                float(filtered[col].mean())
                if filtered[col].notna().any()
                else 0.0
            )

    if radar_labels:
        radar_values_closed = radar_values + [radar_values[0]]
        radar_labels_closed = radar_labels + [radar_labels[0]]

        fig_radar = go.Figure()

        fig_radar.add_trace(
            go.Scatterpolar(
                r=radar_values_closed,
                theta=radar_labels_closed,
                fill="toself",
                fillcolor="rgba(56,201,255,0.18)",
                line=dict(
                    color=CYAN,
                    width=3,
                ),
                marker=dict(
                    color=CYAN,
                    size=7,
                ),
                name="平均得分",
                hovertemplate=(
                    "<b>%{theta}</b><br>"
                    "平均得分：%{r:.1f}"
                    "<extra></extra>"
                ),
            )
        )

        fig_radar.update_layout(
            title=dict(
                text="四维可信机制｜平均得分",
                font=dict(size=17, color=TEXT),
                x=0.02,
            ),
            height=440,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT),
            margin=dict(l=70, r=70, t=70, b=45),
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(
                    range=[0, 100],
                    gridcolor=GRID,
                    linecolor=GRID,
                    tickfont=dict(color=MUTED),
                ),
                angularaxis=dict(
                    gridcolor=GRID,
                    linecolor=GRID,
                    tickfont=dict(color=TEXT, size=13),
                ),
            ),
            showlegend=False,
        )

        st.plotly_chart(
            fig_radar,
            use_container_width=True,
            theme=None,
            config={"displaylogo": False},
        )
    else:
        st.info("当前数据中没有四维可信机制字段。")

# ============================================================
# 7. 可信度分布 + 官方/非官方对比
# ============================================================

c1, c2 = st.columns(2)

with c1:
    if "credibility_score_100" in filtered.columns:
        hist_df = filtered[
            filtered["credibility_score_100"].notna()
        ].copy()

        fig_hist = px.histogram(
            hist_df,
            x="credibility_score_100",
            nbins=20,
            color="credibility_level",
            color_discrete_map=LEVEL_COLORS,
            labels={
                "credibility_score_100": "可信度得分",
                "credibility_level": "可信等级",
            },
        )

        fig_hist.update_layout(
            barmode="overlay",
            bargap=0.08,
        )

        fig_hist.update_traces(opacity=0.82)

        style_fig(
            fig_hist,
            "可信度得分分布",
            height=430,
            left_margin=75,
        )

        st.plotly_chart(
            fig_hist,
            use_container_width=True,
            theme=None,
            config={"displaylogo": False},
        )

with c2:
    official_compare = filtered.copy()

    official_compare["信息属性"] = np.where(
        official_compare["official_flag_bool"],
        "官方信息",
        "非官方信息",
    )

    if (
        "credibility_score_100" in official_compare.columns
        and official_compare["credibility_score_100"].notna().any()
    ):
        fig_official = px.box(
            official_compare,
            x="信息属性",
            y="credibility_score_100",
            points="outliers",
            color="信息属性",
            color_discrete_map={
                "官方信息": CYAN,
                "非官方信息": BLUE,
            },
            labels={
                "credibility_score_100": "可信度得分",
            },
        )

        style_fig(
            fig_official,
            "官方信息 vs 非官方信息｜可信度对比",
            height=430,
            left_margin=85,
        )

        fig_official.update_layout(showlegend=False)

        st.plotly_chart(
            fig_official,
            use_container_width=True,
            theme=None,
            config={"displaylogo": False},
        )

# ============================================================
# 8. 信源权威与综合可信度关系（分档版）
# ============================================================

st.markdown("### 🔬 信源权威与综合可信度关系")

relation_data = filtered.copy()

required_cols = {
    "source_authority_score_100",
    "credibility_score_100",
    "credibility_level",
}

if required_cols.issubset(relation_data.columns):

    relation_data = relation_data[
        relation_data["source_authority_score_100"].notna()
        & relation_data["credibility_score_100"].notna()
        & relation_data["credibility_level"].notna()
    ].copy()

    if relation_data.empty:
        st.info("当前筛选条件下没有可用于信源权威关系分析的数据。")

    else:
        # ----------------------------------------------------
        # 将信源权威得分分档，避免原始散点过密
        # ----------------------------------------------------

        authority_bins = [0, 30, 40, 50, 60, 70, 80, 101]
        authority_labels = [
            "0–29",
            "30–39",
            "40–49",
            "50–59",
            "60–69",
            "70–79",
            "80–100",
        ]

        relation_data["信源权威分档"] = pd.cut(
            relation_data["source_authority_score_100"],
            bins=authority_bins,
            labels=authority_labels,
            right=False,
            include_lowest=True,
        )

        relation_data = relation_data[
            relation_data["信源权威分档"].notna()
        ].copy()

        rel_left, rel_right = st.columns([1.45, 1])

        # ----------------------------------------------------
        # 8.1 每个权威分档的可信等级结构（100%堆叠柱）
        # ----------------------------------------------------

        with rel_left:

            level_structure = (
                relation_data
                .groupby(
                    ["信源权威分档", "credibility_level"],
                    observed=False,
                )
                .size()
                .reset_index(name="记录数")
            )

            level_structure = level_structure[
                level_structure["记录数"] > 0
            ].copy()

            band_total = (
                level_structure
                .groupby("信源权威分档", observed=False)["记录数"]
                .transform("sum")
            )

            level_structure["占比"] = (
                level_structure["记录数"] / band_total * 100
            )

            fig_structure = px.bar(
                level_structure,
                x="信源权威分档",
                y="占比",
                color="credibility_level",
                barmode="stack",
                category_orders={
                    "信源权威分档": authority_labels,
                    "credibility_level": [
                        "低可信",
                        "待核验",
                        "中可信",
                        "高可信",
                    ],
                },
                color_discrete_map=LEVEL_COLORS,
                custom_data=["记录数"],
                labels={
                    "信源权威分档": "信源权威得分区间",
                    "credibility_level": "可信等级",
                    "占比": "占比（%）",
                },
            )

            fig_structure.update_traces(
                hovertemplate=(
                    "<b>权威得分：%{x}</b><br>"
                    "可信等级：%{fullData.name}<br>"
                    "记录数：%{customdata[0]}<br>"
                    "占比：%{y:.1f}%"
                    "<extra></extra>"
                )
            )

            style_fig(
                fig_structure,
                "信源权威分档 × 可信等级结构",
                height=470,
                left_margin=85,
                bottom_margin=75,
            )

            fig_structure.update_yaxes(
                range=[0, 100],
                title="可信等级占比（%）",
            )

            fig_structure.update_xaxes(
                title="信源权威得分区间",
            )

            st.plotly_chart(
                fig_structure,
                use_container_width=True,
                theme=None,
                config={"displaylogo": False},
            )

        # ----------------------------------------------------
        # 8.2 各权威分档的平均可信度趋势
        # ----------------------------------------------------

        with rel_right:

            authority_summary = (
                relation_data
                .groupby("信源权威分档", observed=False)
                .agg(
                    平均综合可信度=("credibility_score_100", "mean"),
                    样本数=("event_instance_id", "count"),
                )
                .reset_index()
            )

            authority_summary = authority_summary[
                authority_summary["样本数"] > 0
            ].copy()

            authority_summary["信源权威分档"] = (
                authority_summary["信源权威分档"].astype(str)
            )

            fig_trend = go.Figure()

            fig_trend.add_trace(
                go.Scatter(
                    x=authority_summary["信源权威分档"],
                    y=authority_summary["平均综合可信度"],
                    mode="lines+markers+text",
                    text=[
                        f"N={int(n)}"
                        for n in authority_summary["样本数"]
                    ],
                    textposition="top center",
                    line=dict(
                        color=CYAN,
                        width=3,
                    ),
                    marker=dict(
                        size=11,
                        color=BLUE,
                        line=dict(
                            color=CYAN,
                            width=2,
                        ),
                    ),
                    hovertemplate=(
                        "<b>权威得分：%{x}</b><br>"
                        "平均综合可信度：%{y:.1f}<br>"
                        "%{text}"
                        "<extra></extra>"
                    ),
                    name="平均综合可信度",
                )
            )

            style_fig(
                fig_trend,
                "权威分档平均综合可信度",
                height=470,
                left_margin=80,
                bottom_margin=75,
            )

            fig_trend.update_yaxes(
                range=[0, 100],
                title="平均综合可信度",
            )

            fig_trend.update_xaxes(
                title="信源权威得分区间",
            )

            fig_trend.update_layout(
                showlegend=False
            )

            st.plotly_chart(
                fig_trend,
                use_container_width=True,
                theme=None,
                config={"displaylogo": False},
            )

        st.caption(
            "为避免原始散点中大量样本重叠，本页将信源权威得分分档后展示。"
            "左图观察各权威区间内部的可信等级结构，右图观察平均综合可信度随信源权威变化的趋势。"
        )

else:
    st.info("当前数据中缺少信源权威或综合可信度字段。")

# ============================================================
# 9. 新闻来源平均可信度
# ============================================================

st.markdown("### 📰 新闻来源可信度分析")

source_stats = (
    filtered[
        filtered["article_source"].notna()
        & filtered["credibility_score_100"].notna()
    ]
    .groupby("article_source")
    .agg(
        样本数=("event_instance_id", "count"),
        平均可信度=("credibility_score_100", "mean"),
        官方记录数=("official_flag_bool", "sum"),
        低质量记录数=("low_quality_flag_bool", "sum"),
    )
    .reset_index()
)

source_stats = source_stats[
    source_stats["样本数"] >= min_source_samples
]

source_top = (
    source_stats
    .sort_values(
        ["平均可信度", "样本数"],
        ascending=[False, False],
    )
    .head(15)
    .sort_values("平均可信度")
)

if source_top.empty:
    st.info("当前筛选条件下，没有满足样本数要求的新闻来源。")
else:
    fig_source = px.bar(
        source_top,
        x="平均可信度",
        y="article_source",
        orientation="h",
        text=source_top["平均可信度"].round(1),
        hover_data={
            "样本数": True,
            "官方记录数": True,
            "低质量记录数": True,
        },
    )

    fig_source.update_traces(
        marker_color=CYAN,
        textposition="outside",
        cliponaxis=False,
    )

    style_fig(
        fig_source,
        f"新闻来源平均可信度 Top15｜最低样本数 ≥ {min_source_samples}",
        height=520,
        left_margin=200,
        right_margin=70,
    )

    fig_source.update_yaxes(title="", automargin=True)

    st.plotly_chart(
        fig_source,
        use_container_width=True,
        theme=None,
        config={"displaylogo": False},
    )

# ============================================================
# 10. 低质量内容诊断
# ============================================================

st.markdown("### ⚠️ 低质量内容诊断")

low_quality = filtered[
    filtered["low_quality_flag_bool"]
].copy()

# ------------------------------------------------------------
# 10.1 KPI
# ------------------------------------------------------------

lq1, lq2, lq3, lq4 = st.columns(4)

low_quality_rate = (
    len(low_quality) / len(filtered) * 100
    if len(filtered)
    else 0
)

low_quality_sources = (
    low_quality["article_source"].dropna().nunique()
    if "article_source" in low_quality.columns
    else 0
)

low_quality_companies = (
    low_quality["secu_abbr"].dropna().nunique()
    if "secu_abbr" in low_quality.columns
    else 0
)

lq1.metric("低质量记录", f"{len(low_quality):,}")
lq2.metric("低质量占比", f"{low_quality_rate:.1f}%")
lq3.metric("涉及来源", f"{low_quality_sources:,}")
lq4.metric("涉及公司", f"{low_quality_companies:,}")

if low_quality.empty:
    st.info("当前筛选条件下没有低质量标记内容。")

else:
    # --------------------------------------------------------
    # 10.2 低质量内容按事件类型分布
    # --------------------------------------------------------

    left_lq, right_lq = st.columns(2)

    with left_lq:
        event_lq = (
            low_quality["event_type"]
            .fillna("未分类")
            .value_counts()
            .reset_index()
        )

        event_lq.columns = ["事件类型", "低质量记录数"]

        fig_lq_event = px.bar(
            event_lq.sort_values("低质量记录数"),
            x="低质量记录数",
            y="事件类型",
            orientation="h",
            text="低质量记录数",
        )

        fig_lq_event.update_traces(
            marker_color=WARNING,
            textposition="outside",
            cliponaxis=False,
        )

        style_fig(
            fig_lq_event,
            "低质量内容｜事件类型分布",
            height=430,
            left_margin=180,
            right_margin=60,
        )

        fig_lq_event.update_yaxes(
            title="",
            automargin=True,
        )

        st.plotly_chart(
            fig_lq_event,
            use_container_width=True,
            theme=None,
            config={"displaylogo": False},
        )

    # --------------------------------------------------------
    # 10.3 低质量内容来源 Top10
    # --------------------------------------------------------

    with right_lq:
        source_lq = (
            low_quality[
                low_quality["article_source"].notna()
            ]
            .groupby("article_source")["event_instance_id"]
            .count()
            .sort_values(ascending=False)
            .head(10)
            .sort_values()
            .reset_index(name="低质量记录数")
        )

        if source_lq.empty:
            st.info("暂无可统计的低质量新闻来源。")
        else:
            fig_lq_source = px.bar(
                source_lq,
                x="低质量记录数",
                y="article_source",
                orientation="h",
                text="低质量记录数",
            )

            fig_lq_source.update_traces(
                marker_color="#F59E5B",
                textposition="outside",
                cliponaxis=False,
            )

            style_fig(
                fig_lq_source,
                "低质量内容｜新闻来源 Top10",
                height=430,
                left_margin=190,
                right_margin=60,
            )

            fig_lq_source.update_yaxes(
                title="",
                automargin=True,
            )

            st.plotly_chart(
                fig_lq_source,
                use_container_width=True,
                theme=None,
                config={"displaylogo": False},
            )

    # --------------------------------------------------------
    # 10.4 证据类型 × 可信等级
    # --------------------------------------------------------

    if (
        "evidence_type" in filtered.columns
        and filtered["evidence_type"].notna().any()
    ):
        evidence_df = filtered[
            filtered["evidence_type"].notna()
            & filtered["credibility_level"].notna()
        ].copy()

        evidence_df["evidence_type"] = (
            evidence_df["evidence_type"]
            .astype(str)
            .str.strip()
        )

        evidence_df = evidence_df[
            evidence_df["evidence_type"] != ""
        ]

        if not evidence_df.empty:
            evidence_ct = (
                evidence_df
                .groupby(["evidence_type", "credibility_level"])
                .size()
                .reset_index(name="记录数")
            )

            evidence_total = (
                evidence_ct
                .groupby("evidence_type")["记录数"]
                .transform("sum")
            )

            evidence_ct["占比"] = (
                evidence_ct["记录数"]
                / evidence_total
                * 100
            )

            fig_evidence = px.bar(
                evidence_ct,
                x="evidence_type",
                y="占比",
                color="credibility_level",
                barmode="stack",
                color_discrete_map=LEVEL_COLORS,
                custom_data=["记录数"],
                labels={
                    "evidence_type": "证据类型",
                    "credibility_level": "可信等级",
                    "占比": "占比（%）",
                },
            )

            fig_evidence.update_traces(
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "可信等级：%{fullData.name}<br>"
                    "记录数：%{customdata[0]}<br>"
                    "占比：%{y:.1f}%"
                    "<extra></extra>"
                )
            )

            style_fig(
                fig_evidence,
                "证据类型 × 可信等级结构",
                height=460,
                left_margin=85,
                bottom_margin=90,
            )

            fig_evidence.update_yaxes(range=[0, 100])

            fig_evidence.update_xaxes(
                automargin=True,
                tickangle=-15,
            )

            st.plotly_chart(
                fig_evidence,
                use_container_width=True,
                theme=None,
                config={"displaylogo": False},
            )

    # --------------------------------------------------------
    # 10.5 low_quality_reason 只做解释，不强行画 Top10
    # --------------------------------------------------------

    if (
        "low_quality_reason" in low_quality.columns
        and low_quality["low_quality_reason"].notna().any()
    ):
        reason_summary = (
            low_quality["low_quality_reason"]
            .dropna()
            .astype(str)
            .str.strip()
        )

        reason_summary = reason_summary[
            reason_summary != ""
        ]

        unique_reasons = reason_summary.nunique()

        st.caption(
            f"低质量原因字段共有 {unique_reasons} 种原始文本。"
            "若该字段是统一模板说明，则不将其绘制成分类 Top10，"
            "避免产生“看似有分类、实际只是同一句模板”的误导。"
        )

# ============================================================
# 11. 待核验 / 低可信重点明细
# ============================================================

st.markdown("---")
st.markdown("### 📋 待核验 / 低可信证据明细")

focus = filtered[
    filtered["credibility_level"].isin(
        ["待核验", "低可信"]
    )
].copy()

focus_cols = [
    "article_publish_time",
    "article_source",
    "secu_abbr",
    "event_type",
    "event_emotion",
    "article_title",
    "credibility_score_100",
    "credibility_level",
    "evidence_type",
    "evidence_text",
    "credibility_reason",
    "low_quality_flag_bool",
    "low_quality_reason",
]

focus_cols = [
    c for c in focus_cols
    if c in focus.columns
]

if focus.empty:
    st.info("当前筛选条件下没有待核验或低可信记录。")
else:
    focus = focus[focus_cols].copy()

    if "credibility_score_100" in focus.columns:
        focus = focus.sort_values(
            "credibility_score_100",
            ascending=True,
            na_position="last",
        )

    focus = focus.head(300)

    focus = focus.rename(
        columns={
            "article_publish_time": "发布时间",
            "article_source": "新闻来源",
            "secu_abbr": "上市公司",
            "event_type": "事件类型",
            "event_emotion": "情绪",
            "article_title": "新闻标题",
            "credibility_score_100": "可信度",
            "credibility_level": "可信等级",
            "evidence_type": "证据类型",
            "evidence_text": "证据内容",
            "credibility_reason": "可信评估理由",
            "low_quality_flag_bool": "低质量标记",
            "low_quality_reason": "低质量原因",
        }
    )

    st.dataframe(
        focus,
        use_container_width=True,
        hide_index=True,
        height=520,
    )
