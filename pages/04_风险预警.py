from pathlib import Path
import html
import re

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
    WARNING,
    NEGATIVE,
)

# ============================================================
# 1. 页面设置
# ============================================================

st.set_page_config(
    page_title="风险预警｜上市公司事件智能分析",
    page_icon="⚠️",
    layout="wide",
)

apply_theme()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

# ============================================================
# 2. 阶段中文
# ============================================================

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

RISK_COLORS = {
    "黄色": "#FFB020",
    "关注": "#38C9FF",
}

# ============================================================
# 3. 页面专属样式
# ============================================================

st.markdown(
    """
    <style>
    .risk-card {
        background: linear-gradient(145deg, rgba(11,40,71,.96), rgba(16,47,80,.96));
        border: 1px solid rgba(56,201,255,.16);
        border-radius: 14px;
        padding: 16px 18px;
        margin-bottom: 12px;
        box-shadow: 0 8px 24px rgba(0,0,0,.12);
    }
    .risk-card-yellow {
        border-left: 4px solid #FFB020;
    }
    .risk-card-watch {
        border-left: 4px solid #38C9FF;
    }
    .risk-card-title {
        color: #EAF6FF;
        font-size: 15px;
        font-weight: 700;
        line-height: 1.5;
        margin-bottom: 8px;
    }
    .risk-card-meta {
        color: #8FB4D6;
        font-size: 12px;
        margin-bottom: 9px;
    }
    .risk-card-reason {
        color: #CFE7F8;
        font-size: 13px;
        line-height: 1.7;
        margin-bottom: 7px;
    }
    .risk-card-action {
        color: #9DDCFF;
        font-size: 12px;
        line-height: 1.65;
    }
    .risk-pill {
        display: inline-block;
        border-radius: 999px;
        padding: 3px 8px;
        margin-right: 7px;
        font-size: 11px;
        font-weight: 700;
    }
    .risk-pill-yellow {
        color: #FFCC64;
        background: rgba(255,176,32,.12);
        border: 1px solid rgba(255,176,32,.25);
    }
    .risk-pill-watch {
        color: #7DDEFF;
        background: rgba(56,201,255,.10);
        border: 1px solid rgba(56,201,255,.22);
    }
    .dossier-box {
        background: rgba(47,128,255,.07);
        border: 1px solid rgba(56,201,255,.17);
        border-left: 4px solid #38C9FF;
        border-radius: 10px;
        padding: 13px 15px;
        color: #CFE7F8;
        line-height: 1.8;
        margin: 8px 0 14px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 4. 数据读取
# ============================================================

@st.cache_data
def load_risk_data():
    risk_df = pd.read_excel(
        DATA_DIR / "risk_alerts.xlsx",
        sheet_name="风险预警",
    )

    stage_df = pd.read_excel(
        DATA_DIR / "event_stages.xlsx",
        sheet_name="演化阶段",
    )

    for col in ["first_seen_time", "latest_time"]:
        if col in risk_df.columns:
            risk_df[col] = pd.to_datetime(
                risk_df[col],
                errors="coerce",
            )

    if "stage_time" in stage_df.columns:
        stage_df["stage_time"] = pd.to_datetime(
            stage_df["stage_time"],
            errors="coerce",
        )

    for col in [
        "risk_score",
        "severity_score",
        "credibility_factor",
        "spread_factor",
        "freshness_factor",
        "cluster_confidence",
        "article_count",
        "source_count",
    ]:
        if col in risk_df.columns:
            risk_df[col] = pd.to_numeric(
                risk_df[col],
                errors="coerce",
            )

    if "stage_order" in stage_df.columns:
        stage_df["stage_order"] = pd.to_numeric(
            stage_df["stage_order"],
            errors="coerce",
        )

    return risk_df, stage_df


risk_df, stage_df = load_risk_data()

# ============================================================
# 5. 工具函数
# ============================================================

def to_100(series):
    s = pd.to_numeric(series, errors="coerce")
    valid = s.dropna()

    if not valid.empty and valid.max() <= 1.5:
        s = s * 100

    return s


def safe_text(value):
    if pd.isna(value):
        return "—"

    text = str(value).strip()

    if not text or text.lower() == "nan":
        return "—"

    return text


def split_multi(value):
    if pd.isna(value):
        return []

    text = str(value).strip()

    if not text or text.lower() == "nan":
        return []

    parts = re.split(r"[、,，;；|/]+", text)

    return [
        p.strip()
        for p in parts
        if p.strip()
    ]


def parse_sources(value):
    return split_multi(value)


def factor_100(value):
    if pd.isna(value):
        return np.nan

    v = float(value)

    if abs(v) <= 1.5:
        return v * 100

    return v


# 标准化几个展示字段
risk_df["cluster_confidence_100"] = to_100(
    risk_df["cluster_confidence"]
)

for col in [
    "severity_score",
    "credibility_factor",
    "spread_factor",
    "freshness_factor",
]:
    risk_df[col + "_100"] = risk_df[col].map(factor_100)

risk_df["current_stage_cn"] = (
    risk_df["current_stage"]
    .map(STAGE_CN)
    .fillna(risk_df["current_stage"])
)

# 公司展开表：用于企业工作台
company_rows = []

for _, row in risk_df.iterrows():
    companies = split_multi(row.get("main_secu_abbrs"))

    for company in companies:
        company_rows.append({
            "company": company,
            "cluster_id": row.get("cluster_id"),
            "risk_score": row.get("risk_score"),
            "risk_level": row.get("risk_level"),
            "event_title": row.get("event_title"),
            "event_type": row.get("event_type"),
            "event_emotion": row.get("event_emotion"),
            "latest_time": row.get("latest_time"),
        })

company_event_df = pd.DataFrame(company_rows)

# ============================================================
# 6. 标题
# ============================================================

st.title("⚠️ 风险预警｜事件驱动智能预警")

st.markdown(
    """
    <div class="section-subtitle">
    从“风险优先级 → 风险驱动因素 → 企业关联事件 → 单事件风险档案”
    四个层次解释为什么预警、应该优先关注什么，以及预警之后该做什么。
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 7. 侧边栏筛选
# ============================================================

st.sidebar.markdown("## 🔎 风险预警筛选")
st.sidebar.caption("筛选条件会同步作用于本页面核心分析。")

filtered = risk_df.copy()

risk_level_options = [
    x for x in ["黄色", "关注"]
    if x in filtered["risk_level"].dropna().unique()
]

selected_levels = st.sidebar.multiselect(
    "风险等级",
    risk_level_options,
    placeholder="默认全部风险等级",
)

if selected_levels:
    filtered = filtered[
        filtered["risk_level"].isin(selected_levels)
    ]

event_type_options = sorted(
    filtered["event_type"]
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
        filtered["event_type"].isin(selected_types)
    ]

emotion_options = [
    x for x in ["正面", "中性", "负面"]
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

stage_options = sorted(
    filtered["current_stage"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

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

if not filtered.empty:
    min_score = float(
        np.floor(filtered["risk_score"].min())
    )
    max_score = float(
        np.ceil(filtered["risk_score"].max())
    )

    score_threshold = st.sidebar.slider(
        "最低风险分",
        min_value=min_score,
        max_value=max_score,
        value=min_score,
        step=1.0,
    )

    filtered = filtered[
        filtered["risk_score"] >= score_threshold
    ]

st.sidebar.markdown("---")
st.sidebar.caption(f"当前筛选：{len(filtered):,} 条预警")

# ============================================================
# 8. KPI
# ============================================================

total_alerts = len(filtered)
yellow_count = int(
    (filtered["risk_level"] == "黄色").sum()
)
watch_count = int(
    (filtered["risk_level"] == "关注").sum()
)
negative_count = int(
    (filtered["event_emotion"] == "负面").sum()
)
avg_risk = (
    filtered["risk_score"].mean()
    if not filtered.empty
    else np.nan
)

company_set = set()

for value in filtered["main_secu_abbrs"].dropna():
    company_set.update(split_multi(value))

k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("预警事件", f"{total_alerts:,}")
k2.metric("黄色预警", f"{yellow_count:,}")
k3.metric("关注事件", f"{watch_count:,}")
k4.metric("负面事件", f"{negative_count:,}")
k5.metric("涉及公司", f"{len(company_set):,}")
k6.metric(
    "平均风险分",
    "-" if pd.isna(avg_risk) else f"{avg_risk:.1f}",
)

st.markdown(
    """
    <div class="blue-note">
    本页严格使用现有风险字段，不额外创造“红色 / 橙色 / 高中低”风险等级。
    当前数据中的正式预警等级为“关注”和“黄色”。
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 9. 核心图1：风险优先级矩阵
# ============================================================

st.markdown("### 🎯 风险优先级矩阵")

priority_df = filtered[
    filtered["risk_score"].notna()
    & filtered["cluster_confidence_100"].notna()
].copy()

if priority_df.empty:
    st.info("当前筛选条件下没有可用于风险优先级矩阵的数据。")
else:
    priority_df["来源数展示"] = (
        priority_df["source_count"]
        .fillna(1)
        .clip(lower=1)
    )

    fig_priority = px.scatter(
        priority_df,
        x="cluster_confidence_100",
        y="risk_score",
        size="来源数展示",
        color="risk_level",
        color_discrete_map=RISK_COLORS,
        hover_name="event_title",
        hover_data={
            "event_type": True,
            "event_emotion": True,
            "main_secu_abbrs": True,
            "risk_score": ":.1f",
            "cluster_confidence_100": ":.1f",
            "source_count": True,
            "article_count": True,
            "来源数展示": False,
        },
        labels={
            "cluster_confidence_100": "事件簇置信度",
            "risk_score": "风险分",
            "risk_level": "风险等级",
            "event_type": "事件类型",
            "event_emotion": "事件情绪",
            "main_secu_abbrs": "主要公司",
            "source_count": "来源数",
            "article_count": "文章数",
        },
        size_max=28,
    )

    risk_median = float(priority_df["risk_score"].median())
    conf_median = float(
        priority_df["cluster_confidence_100"].median()
    )

    fig_priority.add_hline(
        y=risk_median,
        line_dash="dot",
        line_color="#597A98",
        annotation_text="风险中位数",
        annotation_font_color=MUTED,
    )

    fig_priority.add_vline(
        x=conf_median,
        line_dash="dot",
        line_color="#597A98",
        annotation_text="置信度中位数",
        annotation_font_color=MUTED,
    )

    style_fig(
        fig_priority,
        "风险分 × 事件簇置信度｜气泡大小表示来源数",
        height=520,
        left_margin=90,
        bottom_margin=75,
    )

    fig_priority.update_layout(
        legend_title_text="风险等级",
    )

    st.plotly_chart(
        fig_priority,
        use_container_width=True,
        theme=None,
        config={"displaylogo": False},
    )

    st.caption(
        "优先关注右上区域：风险分较高，同时事件聚类置信度较高，"
        "意味着事件本身较明确且预警优先级更高。"
    )

# ============================================================
# 10. 核心图2：风险驱动因素
# ============================================================

st.markdown("### 🧬 风险驱动因素")

factor_cols = {
    "严重程度": "severity_score_100",
    "可信因子": "credibility_factor_100",
    "传播因子": "spread_factor_100",
    "新鲜度因子": "freshness_factor_100",
}

factor_rows = []

for label, col in factor_cols.items():
    if col in filtered.columns:
        factor_rows.append({
            "风险因子": label,
            "平均得分": filtered[col].mean(),
        })

factor_summary = pd.DataFrame(factor_rows)

left_factor, right_factor = st.columns([1, 1.45])

with left_factor:
    if factor_summary.empty:
        st.info("当前数据中没有风险因子字段。")
    else:
        fig_factor = px.bar(
            factor_summary.sort_values(
                "平均得分",
                ascending=True,
            ),
            x="平均得分",
            y="风险因子",
            orientation="h",
            text=factor_summary.sort_values(
                "平均得分",
                ascending=True,
            )["平均得分"].round(1),
        )

        fig_factor.update_traces(
            marker_color=CYAN,
            textposition="outside",
            cliponaxis=False,
        )

        style_fig(
            fig_factor,
            "当前筛选预警｜平均风险因子",
            height=430,
            left_margin=130,
            right_margin=65,
        )

        fig_factor.update_xaxes(
            range=[0, 100],
            title="因子得分",
        )

        fig_factor.update_yaxes(
            title="",
        )

        st.plotly_chart(
            fig_factor,
            use_container_width=True,
            theme=None,
            config={"displaylogo": False},
        )

with right_factor:
    # --------------------------------------------------------
    # Top8 高风险事件风险因子热力图
    # 用热力图替代原来的 Top12 分组柱状图，避免事件标题挤在 X 轴
    # --------------------------------------------------------

    top_factor_events = (
        filtered
        .sort_values(
            "risk_score",
            ascending=False,
        )
        .head(8)
        .copy()
    )

    if top_factor_events.empty:
        st.info("当前筛选条件下没有风险事件。")
    else:
        heat_rows = []

        for _, row in top_factor_events.iterrows():
            full_title = safe_text(
                row.get("event_title")
            )

            # 左侧只显示短标题，完整标题放在悬停提示中
            short_title = full_title

            if len(short_title) > 16:
                short_title = short_title[:16] + "…"

            heat_rows.append({
                "事件": short_title,
                "完整标题": full_title,
                "风险分": row.get("risk_score"),
                "严重程度": row.get("severity_score_100"),
                "可信因子": row.get("credibility_factor_100"),
                "传播因子": row.get("spread_factor_100"),
                "新鲜度因子": row.get("freshness_factor_100"),
            })

        factor_heat_df = pd.DataFrame(heat_rows)

        factor_names = [
            "严重程度",
            "可信因子",
            "传播因子",
            "新鲜度因子",
        ]

        z = factor_heat_df[factor_names].astype(float).values

        # 每个单元格的悬停信息都带完整事件标题与风险分
        customdata = []

        for _, row in factor_heat_df.iterrows():
            customdata.append(
                [
                    [
                        row["完整标题"],
                        row["风险分"],
                    ]
                    for _ in factor_names
                ]
            )

        customdata = np.array(
            customdata,
            dtype=object,
        )

        fig_factor_events = go.Figure(
            data=go.Heatmap(
                z=z,
                x=factor_names,
                y=factor_heat_df["事件"],
                text=np.round(z, 1),
                texttemplate="%{text}",
                zmin=0,
                zmax=100,
                colorscale=[
                    [0.00, "#081522"],
                    [0.25, "#123B63"],
                    [0.55, "#2F80FF"],
                    [0.78, "#38C9FF"],
                    [1.00, "#FFB020"],
                ],
                colorbar=dict(
                    title="因子得分",
                    tickfont=dict(
                        color=MUTED
                    ),
                ),
                customdata=customdata,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "风险分：%{customdata[1]:.1f}<br>"
                    "%{x}：%{z:.1f}"
                    "<extra></extra>"
                ),
            )
        )

        style_fig(
            fig_factor_events,
            "重点风险事件 Top8｜风险因子画像",
            height=470,
            left_margin=240,
            right_margin=80,
            bottom_margin=70,
        )

        fig_factor_events.update_xaxes(
            title="",
            side="top",
            automargin=True,
        )

        fig_factor_events.update_yaxes(
            title="",
            autorange="reversed",
            automargin=True,
        )

        st.plotly_chart(
            fig_factor_events,
            use_container_width=True,
            theme=None,
            config={
                "displaylogo": False
            },
        )

        st.caption(
            "每一行代表一个重点风险事件，每一列代表一个风险因子。"
            "颜色越亮、数值越高，说明该因子对该事件的风险贡献越突出；"
            "鼠标悬停可查看完整事件标题和风险分。"
        )

# ============================================================
# 11. 企业风险工作台
# ============================================================

st.markdown("### 🏢 企业风险工作台")

available_companies = sorted(company_set)

if not available_companies:
    st.info("当前筛选条件下没有可识别的上市公司。")
else:
    selected_company = st.selectbox(
        "搜索 / 选择上市公司",
        available_companies,
    )

    company_cluster_ids = set(
        company_event_df[
            company_event_df["company"] == selected_company
        ]["cluster_id"]
        .dropna()
        .astype(str)
    )

    company_risks = filtered[
        filtered["cluster_id"]
        .astype(str)
        .isin(company_cluster_ids)
    ].copy()

    if company_risks.empty:
        st.info("当前筛选条件下，该公司暂无风险事件。")
    else:
        ck1, ck2, ck3, ck4, ck5 = st.columns(5)

        ck1.metric(
            "关联预警",
            f"{len(company_risks):,}",
        )

        ck2.metric(
            "黄色预警",
            f"{int((company_risks['risk_level'] == '黄色').sum()):,}",
        )

        ck3.metric(
            "平均风险分",
            f"{company_risks['risk_score'].mean():.1f}",
        )

        ck4.metric(
            "最高风险分",
            f"{company_risks['risk_score'].max():.1f}",
        )

        company_industries = set()

        for value in company_risks["main_industry_names"].dropna():
            company_industries.update(split_multi(value))

        ck5.metric(
            "关联行业",
            f"{len(company_industries):,}",
        )

        company_table = (
            company_risks[
                [
                    "event_title",
                    "risk_level",
                    "risk_score",
                    "event_type",
                    "event_emotion",
                    "current_stage_cn",
                    "source_count",
                    "latest_time",
                ]
            ]
            .sort_values(
                "risk_score",
                ascending=False,
            )
            .rename(
                columns={
                    "event_title": "事件标题",
                    "risk_level": "风险等级",
                    "risk_score": "风险分",
                    "event_type": "事件类型",
                    "event_emotion": "情绪",
                    "current_stage_cn": "当前阶段",
                    "source_count": "来源数",
                    "latest_time": "最近时间",
                }
            )
        )

        st.dataframe(
            company_table,
            use_container_width=True,
            hide_index=True,
            height=min(
                420,
                75 + 38 * len(company_table),
            ),
        )

# ============================================================
# 12. 最新 / 重点预警卡片
# ============================================================

st.markdown("### 📡 最新重点预警")

card_df = (
    filtered
    .sort_values(
        ["risk_level", "risk_score", "latest_time"],
        ascending=[False, False, False],
    )
    .head(8)
    .copy()
)

if card_df.empty:
    st.info("当前筛选条件下没有风险预警。")
else:
    for _, row in card_df.iterrows():
        level = safe_text(row.get("risk_level"))
        css_class = (
            "risk-card-yellow"
            if level == "黄色"
            else "risk-card-watch"
        )
        pill_class = (
            "risk-pill-yellow"
            if level == "黄色"
            else "risk-pill-watch"
        )

        title = html.escape(
            safe_text(row.get("event_title"))
        )
        reason = html.escape(
            safe_text(row.get("trigger_reason"))
        )
        action = html.escape(
            safe_text(row.get("recommended_action"))
        )
        event_type = html.escape(
            safe_text(row.get("event_type"))
        )
        company = html.escape(
            safe_text(row.get("main_secu_abbrs"))
        )
        latest = safe_text(
            row.get("latest_time")
        )
        risk_score = row.get("risk_score")

        risk_text = (
            f"{risk_score:.1f}"
            if pd.notna(risk_score)
            else "—"
        )

        st.markdown(
            f"""
            <div class="risk-card {css_class}">
                <div class="risk-card-title">{title}</div>
                <div class="risk-card-meta">
                    <span class="risk-pill {pill_class}">{html.escape(level)}</span>
                    风险分 {risk_text}
                    &nbsp; · &nbsp; {event_type}
                    &nbsp; · &nbsp; {company}
                    &nbsp; · &nbsp; {html.escape(latest)}
                </div>
                <div class="risk-card-reason">
                    <b>触发原因：</b>{reason}
                </div>
                <div class="risk-card-action">
                    <b>建议动作：</b>{action}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ============================================================
# 13. 单事件风险档案
# ============================================================

st.markdown("---")
st.markdown("### 🔎 单事件风险档案")

selector_df = filtered[
    ["cluster_id", "event_title", "risk_score"]
].copy()

selector_df = selector_df.sort_values(
    "risk_score",
    ascending=False,
)

selector_df["选择项"] = (
    selector_df["cluster_id"].astype(str)
    + "｜"
    + selector_df["event_title"].fillna("未命名事件").astype(str)
)

selected_label = st.selectbox(
    "选择一个风险事件",
    selector_df["选择项"].tolist(),
)

selected_cluster_id = (
    selected_label.split("｜", 1)[0]
    if selected_label
    else None
)

if selected_cluster_id:
    detail = filtered[
        filtered["cluster_id"].astype(str)
        == str(selected_cluster_id)
    ].copy()

    if not detail.empty:
        row = detail.iloc[0]

        d1, d2, d3, d4, d5, d6 = st.columns(6)

        d1.metric(
            "风险等级",
            safe_text(row.get("risk_level")),
        )
        d2.metric(
            "风险分",
            (
                f"{row['risk_score']:.1f}"
                if pd.notna(row["risk_score"])
                else "-"
            ),
        )
        d3.metric(
            "簇置信度",
            (
                f"{row['cluster_confidence_100']:.1f}"
                if pd.notna(row["cluster_confidence_100"])
                else "-"
            ),
        )
        d4.metric(
            "来源数",
            (
                int(row["source_count"])
                if pd.notna(row["source_count"])
                else 0
            ),
        )
        d5.metric(
            "文章数",
            (
                int(row["article_count"])
                if pd.notna(row["article_count"])
                else 0
            ),
        )
        d6.metric(
            "当前阶段",
            safe_text(row.get("current_stage_cn")),
        )

        st.markdown(
            f"#### {safe_text(row.get('event_title'))}"
        )

        st.markdown(
            f"""
            <div class="dossier-box">
            {html.escape(safe_text(row.get("event_summary")))}
            </div>
            """,
            unsafe_allow_html=True,
        )

        meta_left, meta_right = st.columns(2)

        with meta_left:
            st.write(
                "**主要公司：**",
                safe_text(row.get("main_secu_abbrs")),
            )
            st.write(
                "**主要行业：**",
                safe_text(row.get("main_industry_names")),
            )
            st.write(
                "**事件类型：**",
                safe_text(row.get("event_type")),
            )
            st.write(
                "**事件情绪：**",
                safe_text(row.get("event_emotion")),
            )

        with meta_right:
            st.write(
                "**首次发现：**",
                safe_text(row.get("first_seen_time")),
            )
            st.write(
                "**最近更新：**",
                safe_text(row.get("latest_time")),
            )
            st.write(
                "**证据来源：**",
                safe_text(row.get("evidence_sources")),
            )

        # ----------------------------------------------------
        # 13.1 单事件风险因子雷达
        # ----------------------------------------------------

        st.markdown("#### 🧬 风险形成机制")

        radar_labels = [
            "严重程度",
            "可信因子",
            "传播因子",
            "新鲜度因子",
        ]

        radar_values = [
            row.get("severity_score_100"),
            row.get("credibility_factor_100"),
            row.get("spread_factor_100"),
            row.get("freshness_factor_100"),
        ]

        radar_values = [
            0 if pd.isna(v) else float(v)
            for v in radar_values
        ]

        radar_labels_closed = radar_labels + [radar_labels[0]]
        radar_values_closed = radar_values + [radar_values[0]]

        fig_radar = go.Figure()

        fig_radar.add_trace(
            go.Scatterpolar(
                r=radar_values_closed,
                theta=radar_labels_closed,
                fill="toself",
                fillcolor="rgba(56,201,255,0.16)",
                line=dict(
                    color=CYAN,
                    width=3,
                ),
                marker=dict(
                    color=CYAN,
                    size=7,
                ),
                hovertemplate=(
                    "<b>%{theta}</b><br>"
                    "得分：%{r:.1f}"
                    "<extra></extra>"
                ),
            )
        )

        fig_radar.update_layout(
            height=430,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT),
            margin=dict(
                l=80,
                r=80,
                t=35,
                b=45,
            ),
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
                    tickfont=dict(
                        color=TEXT,
                        size=13,
                    ),
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

        # ----------------------------------------------------
        # 13.2 触发原因 + 建议动作
        # ----------------------------------------------------

        reason_col, action_col = st.columns(2)

        with reason_col:
            st.markdown("#### 🚨 触发原因")
            st.markdown(
                f"""
                <div class="dossier-box">
                {html.escape(safe_text(row.get("trigger_reason")))}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with action_col:
            st.markdown("#### ✅ 建议动作")
            st.markdown(
                f"""
                <div class="dossier-box">
                {html.escape(safe_text(row.get("recommended_action")))}
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ----------------------------------------------------
        # 13.3 事件演化时间线
        # ----------------------------------------------------

        st.markdown("#### 🕒 事件演化时间线")

        selected_stages = stage_df[
            stage_df["cluster_id"].astype(str)
            == str(selected_cluster_id)
        ].copy()

        selected_stages = selected_stages.sort_values(
            ["stage_order", "stage_time"],
            na_position="last",
        )

        if selected_stages.empty:
            st.info("该风险事件暂无演化阶段记录。")
        else:
            fig_timeline = go.Figure()

            fig_timeline.add_trace(
                go.Scatter(
                    x=selected_stages["stage_time"],
                    y=[1] * len(selected_stages),
                    mode="lines",
                    line=dict(
                        color=GRID,
                        width=3,
                    ),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

            for stage_type in selected_stages["stage_type"].dropna().unique():
                sub = selected_stages[
                    selected_stages["stage_type"] == stage_type
                ]

                fig_timeline.add_trace(
                    go.Scatter(
                        x=sub["stage_time"],
                        y=[1] * len(sub),
                        mode="markers+text",
                        marker=dict(
                            size=18,
                            color=STAGE_COLORS.get(
                                stage_type,
                                SKY,
                            ),
                            line=dict(
                                color="#EAF6FF",
                                width=1.2,
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
                            ],
                            axis=-1,
                        ),
                        hovertemplate=(
                            "<b>%{customdata[0]}</b><br>"
                            "%{x}<br>"
                            "%{customdata[1]}"
                            "<extra></extra>"
                        ),
                    )
                )

            fig_timeline.update_layout(
                height=390,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=TEXT),
                margin=dict(
                    l=40,
                    r=40,
                    t=55,
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
