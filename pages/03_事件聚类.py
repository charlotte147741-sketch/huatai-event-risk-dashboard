from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.theme import (
    apply_theme,
    style_fig,
    GRID,
    TEXT,
    MUTED,
    BLUE,
    CYAN,
    SKY,
)

# ============================================================
# 1. 页面设置
# ============================================================

st.set_page_config(
    page_title="事件聚类｜上市公司事件智能分析",
    page_icon="🧩",
    layout="wide",
)

apply_theme()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

# ============================================================
# 2. 阶段配置
# ============================================================

STAGE_ORDER = [
    "INITIAL",
    "SPREADING",
    "DEVELOPING",
    "CONFIRMED",
    "ESCALATED",
    "CLARIFIED",
    "REVERSED",
    "CLOSED",
]

STAGE_CN = {
    "INITIAL": "初始",
    "SPREADING": "传播",
    "DEVELOPING": "发展",
    "CONFIRMED": "确认",
    "ESCALATED": "升级",
    "CLARIFIED": "澄清",
    "REVERSED": "反转",
    "CLOSED": "结束",
}

STAGE_COLORS = {
    "INITIAL": "#4D9DE0",
    "SPREADING": "#38C9FF",
    "DEVELOPING": "#2F80FF",
    "CONFIRMED": "#2ED47A",
    "ESCALATED": "#FFB020",
    "CLARIFIED": "#7BC8FF",
    "REVERSED": "#FF5C7A",
    "CLOSED": "#597A98",
}

# ============================================================
# 3. 数据读取
# ============================================================

@st.cache_data
def load_cluster_data():
    cluster_df = pd.read_excel(
        DATA_DIR / "event_clusters.xlsx",
        sheet_name="事件簇",
    )

    member_df = pd.read_excel(
        DATA_DIR / "event_clusters.xlsx",
        sheet_name="成员映射",
    )

    stage_df = pd.read_excel(
        DATA_DIR / "event_stages.xlsx",
        sheet_name="演化阶段",
    )

    for col in ["cluster_start_time", "cluster_latest_time"]:
        if col in cluster_df.columns:
            cluster_df[col] = pd.to_datetime(
                cluster_df[col],
                errors="coerce",
            )

    if "article_publish_time" in member_df.columns:
        member_df["article_publish_time"] = pd.to_datetime(
            member_df["article_publish_time"],
            errors="coerce",
        )

    if "stage_time" in stage_df.columns:
        stage_df["stage_time"] = pd.to_datetime(
            stage_df["stage_time"],
            errors="coerce",
        )

    for col in ["article_count", "source_count", "cluster_confidence"]:
        if col in cluster_df.columns:
            cluster_df[col] = pd.to_numeric(
                cluster_df[col],
                errors="coerce",
            )

    if "similarity_score" in member_df.columns:
        member_df["similarity_score"] = pd.to_numeric(
            member_df["similarity_score"],
            errors="coerce",
        )

    if "stage_order" in stage_df.columns:
        stage_df["stage_order"] = pd.to_numeric(
            stage_df["stage_order"],
            errors="coerce",
        )

    return cluster_df, member_df, stage_df


cluster_df, member_df, stage_df = load_cluster_data()

# ============================================================
# 4. 数据增强
# ============================================================

def to_100(series):
    s = pd.to_numeric(series, errors="coerce")
    valid = s.dropna()

    if not valid.empty and valid.max() <= 1.5:
        s = s * 100

    return s


def to_bool(series):
    if series.dtype == bool:
        return series.fillna(False)

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


def safe_text(value):
    if pd.isna(value):
        return "—"

    text = str(value).strip()

    if not text or text.lower() == "nan":
        return "—"

    return text


cluster_df["cluster_confidence_100"] = to_100(
    cluster_df["cluster_confidence"]
)

if "is_key_turning_point" in stage_df.columns:
    stage_df["key_turning_bool"] = to_bool(
        stage_df["is_key_turning_point"]
    )
else:
    stage_df["key_turning_bool"] = False

# 不同阶段数量
stage_type_count = (
    stage_df.dropna(subset=["stage_type"])
    .groupby("cluster_id")["stage_type"]
    .nunique()
    .rename("stage_type_count")
)

# 是否存在关键转折
key_turning = (
    stage_df.groupby("cluster_id")["key_turning_bool"]
    .max()
    .rename("has_key_turning")
)

cluster_df = cluster_df.merge(
    stage_type_count,
    on="cluster_id",
    how="left",
)

cluster_df = cluster_df.merge(
    key_turning,
    on="cluster_id",
    how="left",
)

cluster_df["stage_type_count"] = (
    cluster_df["stage_type_count"]
    .fillna(0)
    .astype(int)
)

cluster_df["has_key_turning"] = (
    cluster_df["has_key_turning"]
    .fillna(False)
    .astype(bool)
)

cluster_df["current_stage_cn"] = (
    cluster_df["current_stage"]
    .map(STAGE_CN)
    .fillna(cluster_df["current_stage"])
)

# ============================================================
# 5. 页面标题
# ============================================================

st.title("🧩 事件聚类｜同源事件聚合与脉络追踪")

st.markdown(
    """
    <div class="section-subtitle">
    本页只保留对比赛展示最有价值的聚类可视化：
    聚类规模结构、当前演化状态、聚类质量、不同事件类型的阶段差异，
    以及单事件簇的完整演化脉络。
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 6. 侧边栏筛选
# ============================================================

st.sidebar.markdown("## 🔎 事件聚类筛选")
st.sidebar.caption("筛选条件会同步作用于本页面全部图表。")

filtered = cluster_df.copy()

event_type_options = sorted(
    filtered["cluster_event_type"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

selected_types = st.sidebar.multiselect(
    "事件类型",
    event_type_options,
    placeholder="默认全部事件类型",
)

if selected_types:
    filtered = filtered[
        filtered["cluster_event_type"].isin(selected_types)
    ]

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

stage_options = [
    s for s in STAGE_ORDER
    if s in filtered["current_stage"].dropna().unique()
]

selected_stages = st.sidebar.multiselect(
    "当前阶段",
    stage_options,
    format_func=lambda x: STAGE_CN.get(x, x),
    placeholder="默认全部阶段",
)

if selected_stages:
    filtered = filtered[
        filtered["current_stage"].isin(selected_stages)
    ]

st.sidebar.markdown("---")
st.sidebar.caption(f"当前筛选：{len(filtered):,} 个事件簇")

# ============================================================
# 7. KPI
# ============================================================

cluster_count = len(filtered)
multi_article_count = int(
    (filtered["article_count"].fillna(0) > 1).sum()
)
multi_source_count = int(
    (filtered["source_count"].fillna(0) > 1).sum()
)
multi_stage_count = int(
    (filtered["stage_type_count"] > 1).sum()
)
avg_confidence = (
    filtered["cluster_confidence_100"].mean()
    if not filtered.empty
    else np.nan
)

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("事件簇", f"{cluster_count:,}")
k2.metric("多新闻聚合", f"{multi_article_count:,}")
k3.metric("多来源交叉", f"{multi_source_count:,}")
k4.metric("多阶段演化", f"{multi_stage_count:,}")
k5.metric(
    "平均聚类置信度",
    "-" if pd.isna(avg_confidence) else f"{avg_confidence:.1f}",
)

# ============================================================
# 8. 保留图1：事件类型｜聚类数量
# ============================================================

st.markdown("### 📊 事件类型｜聚类数量")

type_counts = (
    filtered["cluster_event_type"]
    .fillna("未分类")
    .value_counts()
    .reset_index()
)

type_counts.columns = ["事件类型", "事件簇数"]

fig_type = px.bar(
    type_counts.sort_values("事件簇数"),
    x="事件簇数",
    y="事件类型",
    orientation="h",
    text="事件簇数",
)

fig_type.update_traces(
    marker_color=BLUE,
    marker_line_color=CYAN,
    marker_line_width=0.6,
    textposition="outside",
    cliponaxis=False,
)

style_fig(
    fig_type,
    "事件类型｜聚类数量",
    height=470,
    left_margin=190,
    right_margin=70,
)

fig_type.update_yaxes(
    title="",
    automargin=True,
)

st.plotly_chart(
    fig_type,
    use_container_width=True,
    theme=None,
    config={"displaylogo": False},
)

# ============================================================
# 9. 保留图2：当前阶段分布 + 聚类置信度
# ============================================================

st.markdown("### 🧭 当前阶段与聚类置信度")

left_stage, right_conf = st.columns(2)

with left_stage:
    stage_counts = (
        filtered["current_stage"]
        .dropna()
        .value_counts()
        .reindex(
            [s for s in STAGE_ORDER if s in filtered["current_stage"].dropna().unique()]
        )
        .dropna()
        .reset_index()
    )

    stage_counts.columns = ["阶段", "事件簇数"]
    stage_counts["阶段中文"] = (
        stage_counts["阶段"]
        .map(STAGE_CN)
        .fillna(stage_counts["阶段"])
    )

    fig_stage = px.bar(
        stage_counts,
        x="阶段中文",
        y="事件簇数",
        text="事件簇数",
        color="阶段",
        color_discrete_map=STAGE_COLORS,
    )

    fig_stage.update_traces(
        textposition="outside",
        cliponaxis=False,
    )

    style_fig(
        fig_stage,
        "事件簇当前阶段分布",
        height=460,
        left_margin=80,
        bottom_margin=70,
    )

    fig_stage.update_layout(showlegend=False)
    fig_stage.update_xaxes(title="当前阶段")

    st.plotly_chart(
        fig_stage,
        use_container_width=True,
        theme=None,
        config={"displaylogo": False},
    )

with right_conf:
    confidence_data = filtered[
        filtered["cluster_confidence_100"].notna()
    ].copy()

    fig_conf = px.histogram(
        confidence_data,
        x="cluster_confidence_100",
        nbins=18,
        labels={
            "cluster_confidence_100": "聚类置信度",
        },
    )

    fig_conf.update_traces(
        marker_color=SKY,
        marker_line_color=CYAN,
        marker_line_width=0.5,
    )

    style_fig(
        fig_conf,
        "聚类置信度分布",
        height=460,
        left_margin=80,
    )

    fig_conf.update_xaxes(
        range=[0, 100],
        title="聚类置信度",
    )

    fig_conf.update_yaxes(
        title="事件簇数",
    )

    st.plotly_chart(
        fig_conf,
        use_container_width=True,
        theme=None,
        config={"displaylogo": False},
    )

# ============================================================
# 10. 保留图3：聚类有效性矩阵
# ============================================================

st.markdown("### 🎯 聚类有效性矩阵")

quality_rows = []

for event_type, sub in filtered.groupby(
    "cluster_event_type",
    dropna=False,
):
    quality_rows.append({
        "事件类型": (
            event_type if pd.notna(event_type) else "未分类"
        ),
        "多新闻聚合率": (
            (sub["article_count"].fillna(0) > 1).mean() * 100
        ),
        "多来源交叉率": (
            (sub["source_count"].fillna(0) > 1).mean() * 100
        ),
        "多阶段演化率": (
            (sub["stage_type_count"] > 1).mean() * 100
        ),
        "关键转折覆盖率": (
            sub["has_key_turning"].mean() * 100
        ),
        "平均聚类置信度": (
            sub["cluster_confidence_100"].mean()
        ),
    })

quality_df = pd.DataFrame(quality_rows)

if quality_df.empty:
    st.info("当前筛选条件下没有可用于聚类有效性分析的数据。")
else:
    metric_order = [
        "多新闻聚合率",
        "多来源交叉率",
        "多阶段演化率",
        "关键转折覆盖率",
        "平均聚类置信度",
    ]

    quality_matrix = (
        quality_df
        .set_index("事件类型")[metric_order]
        .round(1)
        .sort_values(
            "多来源交叉率",
            ascending=True,
        )
    )

    fig_quality = go.Figure(
        data=go.Heatmap(
            z=quality_matrix.values,
            x=quality_matrix.columns,
            y=quality_matrix.index,
            text=np.round(quality_matrix.values, 1),
            texttemplate="%{text}",
            zmin=0,
            zmax=100,
            colorscale=[
                [0.00, "#081522"],
                [0.30, "#123B63"],
                [0.60, "#2F80FF"],
                [1.00, "#38C9FF"],
            ],
            colorbar=dict(
                title="得分 / 比例",
                tickfont=dict(color=MUTED),
            ),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "%{x}：%{z:.1f}"
                "<extra></extra>"
            ),
        )
    )

    style_fig(
        fig_quality,
        "不同事件类型的聚类增益与质量",
        height=max(480, 58 * len(quality_matrix)),
        left_margin=190,
        bottom_margin=100,
    )

    fig_quality.update_xaxes(
        tickangle=-15,
        automargin=True,
    )

    fig_quality.update_yaxes(
        automargin=True,
    )

    st.plotly_chart(
        fig_quality,
        use_container_width=True,
        theme=None,
        config={"displaylogo": False},
    )

    st.caption(
        "该矩阵不只看“聚了多少个事件”，而是比较各事件类型在多新闻聚合、"
        "多来源交叉、阶段演化、关键转折覆盖和聚类置信度上的实际表现。"
    )

# ============================================================
# 11. 保留图4：事件类型 × 当前演化阶段
# ============================================================

st.markdown("### 🧭 事件类型 × 当前演化阶段")

stage_status = filtered[
    filtered["cluster_event_type"].notna()
    & filtered["current_stage"].notna()
].copy()

if stage_status.empty:
    st.info("当前筛选条件下没有阶段数据。")
else:
    stage_ct = pd.crosstab(
        stage_status["cluster_event_type"],
        stage_status["current_stage"],
        normalize="index",
    ) * 100

    stage_ct = stage_ct.reindex(
        columns=[
            s for s in STAGE_ORDER
            if s in stage_ct.columns
        ],
        fill_value=0,
    )

    stage_ct.columns = [
        STAGE_CN.get(x, x)
        for x in stage_ct.columns
    ]

    stage_ct = stage_ct.loc[
        stage_ct.sum(axis=1)
        .sort_values(ascending=True)
        .index
    ]

    fig_stage_heat = go.Figure(
        data=go.Heatmap(
            z=stage_ct.values,
            x=stage_ct.columns,
            y=stage_ct.index,
            text=np.round(stage_ct.values, 1),
            texttemplate="%{text}%",
            colorscale=[
                [0.00, "#081522"],
                [0.25, "#123B63"],
                [0.60, "#2F80FF"],
                [1.00, "#38C9FF"],
            ],
            colorbar=dict(
                title="类型内占比",
                ticksuffix="%",
                tickfont=dict(color=MUTED),
            ),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "当前阶段：%{x}<br>"
                "类型内占比：%{z:.1f}%"
                "<extra></extra>"
            ),
        )
    )

    style_fig(
        fig_stage_heat,
        "不同事件类型当前处于什么阶段",
        height=max(480, 58 * len(stage_ct)),
        left_margin=190,
        bottom_margin=75,
    )

    st.plotly_chart(
        fig_stage_heat,
        use_container_width=True,
        theme=None,
        config={"displaylogo": False},
    )

# ============================================================
# 12. 保留图5：单事件簇脉络钻取
# ============================================================

st.markdown("---")
st.markdown("### 🔎 单事件簇脉络钻取")

selector_df = filtered[
    ["cluster_id", "cluster_title"]
].copy()

selector_df["选择项"] = (
    selector_df["cluster_id"].astype(str)
    + "｜"
    + selector_df["cluster_title"]
    .fillna("未命名事件")
    .astype(str)
)

selected_label = st.selectbox(
    "选择一个事件簇",
    selector_df["选择项"].tolist(),
)

selected_cluster_id = (
    selected_label.split("｜", 1)[0]
    if selected_label
    else None
)

if selected_cluster_id:
    selected_cluster = cluster_df[
        cluster_df["cluster_id"].astype(str)
        == str(selected_cluster_id)
    ].copy()

    if not selected_cluster.empty:
        row = selected_cluster.iloc[0]

        d1, d2, d3, d4, d5 = st.columns(5)

        d1.metric(
            "文章数",
            int(row["article_count"])
            if pd.notna(row["article_count"])
            else 0,
        )

        d2.metric(
            "来源数",
            int(row["source_count"])
            if pd.notna(row["source_count"])
            else 0,
        )

        d3.metric(
            "聚类置信度",
            (
                f"{row['cluster_confidence_100']:.1f}"
                if pd.notna(row["cluster_confidence_100"])
                else "-"
            ),
        )

        d4.metric(
            "当前阶段",
            safe_text(row.get("current_stage_cn")),
        )

        d5.metric(
            "事件情绪",
            safe_text(row.get("event_emotion")),
        )

        st.markdown(
            f"#### {safe_text(row.get('cluster_title'))}"
        )

        if pd.notna(row.get("cluster_summary")):
            st.markdown(
                f"""
                <div class="blue-note">
                {safe_text(row.get('cluster_summary'))}
                </div>
                """,
                unsafe_allow_html=True,
            )

        meta_left, meta_right = st.columns(2)

        with meta_left:
            st.write(
                "**事件类型：**",
                safe_text(row.get("cluster_event_type")),
            )
            st.write(
                "**主要公司：**",
                safe_text(row.get("main_secu_abbrs")),
            )
            st.write(
                "**主要行业：**",
                safe_text(row.get("main_industry_names")),
            )

        with meta_right:
            st.write(
                "**开始时间：**",
                safe_text(row.get("cluster_start_time")),
            )
            st.write(
                "**最近时间：**",
                safe_text(row.get("cluster_latest_time")),
            )
            st.write(
                "**证据来源：**",
                safe_text(row.get("evidence_sources")),
            )

        selected_stages_df = stage_df[
            stage_df["cluster_id"].astype(str)
            == str(selected_cluster_id)
        ].copy()

        selected_stages_df = selected_stages_df.sort_values(
            ["stage_order", "stage_time"],
            na_position="last",
        )

        st.markdown("#### 🕒 事件演化时间线")

        if selected_stages_df.empty:
            st.info("该事件簇暂无演化阶段记录。")
        else:
            fig_timeline = go.Figure()

            fig_timeline.add_trace(
                go.Scatter(
                    x=selected_stages_df["stage_time"],
                    y=[1] * len(selected_stages_df),
                    mode="lines",
                    line=dict(
                        color=GRID,
                        width=3,
                    ),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

            for stage_type in selected_stages_df["stage_type"].dropna().unique():
                sub = selected_stages_df[
                    selected_stages_df["stage_type"] == stage_type
                ]

                fig_timeline.add_trace(
                    go.Scatter(
                        x=sub["stage_time"],
                        y=[1] * len(sub),
                        mode="markers+text",
                        marker=dict(
                            size=[
                                24 if bool(v) else 17
                                for v in sub["key_turning_bool"]
                            ],
                            color=STAGE_COLORS.get(
                                stage_type,
                                MUTED,
                            ),
                            line=dict(
                                color="#EAF6FF",
                                width=1.3,
                            ),
                        ),
                        text=[
                            f"{int(o)}. {STAGE_CN.get(t, t)}"
                            for o, t in zip(
                                sub["stage_order"],
                                sub["stage_type"],
                            )
                        ],
                        textposition="top center",
                        name=STAGE_CN.get(
                            stage_type,
                            stage_type,
                        ),
                        customdata=np.stack(
                            [
                                sub["stage_title"]
                                .fillna("")
                                .astype(str),
                                sub["stage_summary"]
                                .fillna("")
                                .astype(str),
                                sub["key_turning_bool"]
                                .astype(str),
                            ],
                            axis=-1,
                        ),
                        hovertemplate=(
                            "<b>%{customdata[0]}</b><br>"
                            "%{x}<br>"
                            "%{customdata[1]}<br>"
                            "关键转折：%{customdata[2]}"
                            "<extra></extra>"
                        ),
                    )
                )

            fig_timeline.update_layout(
                title=dict(
                    text="事件演化阶段｜关键转折点节点更大",
                    font=dict(
                        color=TEXT,
                        size=17,
                    ),
                    x=0.02,
                ),
                height=390,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=TEXT),
                margin=dict(
                    l=40,
                    r=40,
                    t=85,
                    b=65,
                ),
                yaxis=dict(
                    visible=False,
                    range=[0.8, 1.3],
                ),
                xaxis=dict(
                    title="时间",
                    gridcolor=GRID,
                    tickfont=dict(color=MUTED),
                    titlefont=dict(color=MUTED),
                ),
                legend=dict(
                    orientation="h",
                    y=-0.20,
                    x=0,
                    font=dict(color=MUTED),
                ),
                hoverlabel=dict(
                    bgcolor="#102F50",
                    font_color=TEXT,
                    bordercolor=GRID,
                ),
            )

            st.plotly_chart(
                fig_timeline,
                use_container_width=True,
                theme=None,
                config={"displaylogo": False},
            )

            stage_table = selected_stages_df[
                [
                    "stage_order",
                    "stage_time",
                    "stage_type",
                    "stage_title",
                    "stage_summary",
                    "key_turning_bool",
                ]
            ].copy()

            stage_table["stage_type"] = (
                stage_table["stage_type"]
                .map(STAGE_CN)
                .fillna(stage_table["stage_type"])
            )

            stage_table["key_turning_bool"] = (
                stage_table["key_turning_bool"]
                .map({True: "是", False: "否"})
            )

            stage_table = stage_table.rename(
                columns={
                    "stage_order": "阶段序号",
                    "stage_time": "阶段时间",
                    "stage_type": "阶段类型",
                    "stage_title": "阶段标题",
                    "stage_summary": "阶段摘要",
                    "key_turning_bool": "关键转折点",
                }
            )

            st.dataframe(
                stage_table,
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("#### 📰 簇内新闻成员")

        selected_members = member_df[
            member_df["cluster_id"].astype(str)
            == str(selected_cluster_id)
        ].copy()

        selected_members = selected_members.sort_values(
            "article_publish_time",
            ascending=True,
            na_position="last",
        )

        member_cols = [
            "event_instance_id",
            "article_publish_time",
            "article_source",
            "article_title",
            "similarity_score",
        ]

        member_cols = [
            c for c in member_cols
            if c in selected_members.columns
        ]

        member_table = selected_members[
            member_cols
        ].rename(
            columns={
                "event_instance_id": "事件实例ID",
                "article_publish_time": "发布时间",
                "article_source": "新闻来源",
                "article_title": "新闻标题",
                "similarity_score": "相似度",
            }
        )

        if "相似度" in member_table.columns:
            member_table["相似度"] = (
                member_table["相似度"].round(4)
            )

        st.dataframe(
            member_table,
            use_container_width=True,
            hide_index=True,
            height=420,
        )
