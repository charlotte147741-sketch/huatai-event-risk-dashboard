import streamlit as st
import pandas as pd

from neo4j import GraphDatabase
from pyvis.network import Network

from pathlib import Path
import html


# ============================================================
# 1. 页面设置
# ============================================================

st.set_page_config(
    page_title="上市公司事件智能识别与风险追踪平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# >>> KG_READABLE_THEME >>>
st.markdown(
    """
    <style>
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        background: #F4F8FC !important;
        color: #16324F !important;
    }

    [data-testid="stHeader"] {
        background: #17304B !important;
    }

    [data-testid="stMain"] h1,
    [data-testid="stMain"] h2,
    [data-testid="stMain"] h3,
    [data-testid="stMain"] h4 {
        color: #123B63 !important;
    }

    [data-testid="stMain"] p,
    [data-testid="stMain"] label,
    [data-testid="stMain"] span,
    [data-testid="stMain"] small {
        color: #294C6B !important;
    }

    [data-testid="stSidebar"] {
        background: #07192E !important;
        border-right: 1px solid #214768 !important;
    }

    [data-testid="stSidebar"] * {
        color: #EAF6FF !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: #214768 !important;
    }

    [data-testid="stSidebar"] input {
        color: #16324F !important;
        background: #FFFFFF !important;
    }

    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #0B2847, #123B63) !important;
        border: 1px solid #214768 !important;
        border-radius: 14px !important;
        padding: 16px 18px !important;
    }

    [data-testid="stMetric"] *,
    [data-testid="stMetricLabel"],
    [data-testid="stMetricValue"] {
        color: #EAF6FF !important;
    }

    [data-testid="stMetricValue"] {
        color: #BFE9FF !important;
    }

    [data-testid="stMain"] [role="radiogroup"] label *,
    [data-testid="stMain"] [data-testid="stCheckbox"] label * {
        color: #294C6B !important;
    }

    iframe {
        background: #FFFFFF !important;
        border: 1px solid #D5E2EE !important;
        border-radius: 12px !important;
    }

    hr {
        border-color: #D5E2EE !important;
    }

    [data-testid="stMain"] [data-baseweb="select"] > div {
        background: #FFFFFF !important;
        color: #16324F !important;
    }

    [data-testid="stDataFrame"] {
        background: #FFFFFF !important;
        border: 1px solid #D5E2EE !important;
        border-radius: 10px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
# <<< KG_READABLE_THEME <<<




# ============================================================
# 2. 蓝色金融科技页面样式
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #F4F8FC;
    }

    .main-title {
        font-size: 30px;
        font-weight: 700;
        color: #123A63;
        margin-bottom: 4px;
    }

    .sub-title {
        font-size: 15px;
        color: #66809A;
        margin-bottom: 20px;
    }

    div[data-testid="stMetric"] {
        background-color: white;
        border: 1px solid #DCE8F3;
        border-radius: 14px;
        padding: 15px 17px;
        box-shadow: 0 2px 10px rgba(30, 80, 130, 0.05);
    }

    div[data-testid="stMetricLabel"] {
        color: #66809A;
    }

    div[data-testid="stMetricValue"] {
        color: #1769AA;
    }

    .graph-legend {
        background: white;
        border: 1px solid #DCE8F3;
        border-radius: 12px;
        padding: 10px 16px;
        margin-bottom: 12px;
        color: #425B72;
        font-size: 14px;
    }

    hr {
        border-color: #DCE8F3;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 3. Neo4j 连接
# ============================================================

@st.cache_resource
def get_driver():

    driver = GraphDatabase.driver(
        st.secrets["neo4j"]["uri"],
        auth=(
            st.secrets["neo4j"]["username"],
            st.secrets["neo4j"]["password"]
        )
    )

    driver.verify_connectivity()

    return driver


def run_query(query, parameters=None):

    driver = get_driver()

    records, summary, keys = driver.execute_query(
        query,
        parameters_=parameters or {},
        database_=st.secrets["neo4j"]["database"]
    )

    return pd.DataFrame(
        [record.data() for record in records]
    )


# ============================================================
# 4. 小工具
# ============================================================

def safe_int(value, default=0):

    try:
        if value is None:
            return default

        return int(float(value))

    except:
        return default


def safe_float(value, default=0.0):

    try:
        if value is None:
            return default

        return float(value)

    except:
        return default


def clean_text(value):

    if value is None:
        return ""

    return str(value).strip()


def short_text(value, length=16):

    value = clean_text(value)

    if len(value) <= length:
        return value

    return value[:length] + "…"


def esc(value):

    return html.escape(
        clean_text(value)
    )
# ============================================================
# 四种知识图谱视图配置
# ============================================================

VIEW_CONFIG = {

    "全局事件": {
        "title": "🌐 全局事件知识图谱",
        "description": "展示全部事件类型、聚合事件、上市公司、行业与新闻来源。",
        "event_color": "#2F80ED",
        "event_border": "#1D5FBF"
    },

    "正面事件": {
        "title": "🟢 正面事件 · 全局知识图谱",
        "description": "聚焦正面事件及其相关公司、行业和新闻来源。",
        "event_color": "#21A179",
        "event_border": "#157A5B"
    },

    "负面事件": {
        "title": "🔴 负面事件 · 全局知识图谱",
        "description": "聚焦负面事件及其相关公司、行业和新闻来源。",
        "event_color": "#E45756",
        "event_border": "#B83C3B"
    },

    "风险重点": {
        "title": "⚠️ 风险重点事件知识图谱",
        "description": "重点展示黄色预警及负面风险事件。",
        "event_color": "#F28C28",
        "event_border": "#C76712"
    }
}

# ============================================================
# 5. 获取“全局图谱”数据
# ============================================================

@st.cache_data(ttl=60)
def load_global_graph_data(
    view_mode,
    events_per_type=20,
    include_sources=True,
    sources_per_event=2
):

    # --------------------------------------------------------
    # 5.1 事件类型 → 事件
    #
    # 这里把所有事件类型一起取出来
    # 然后在 Python 中每个类型取前 N 个
    # --------------------------------------------------------

    event_df = run_query(
        """
        MATCH
            (t:EventType {view_layer:'global'})
            -[:`包含事件`]->
            (e:Event {kg_version:'v4'})

        WHERE
            $view_mode = '全局事件'

            OR (
                $view_mode = '正面事件'
                AND e.emotion = '正面'
            )

            OR (
                $view_mode = '负面事件'
                AND e.emotion = '负面'
            )

            OR (
                $view_mode = '风险重点'
                AND (
                    e.risk_level = '黄色'
                    OR e.emotion = '负面'
                )
            )

        RETURN
            t.name AS event_type,
            e.node_id AS event_id,
            e.display_name AS event_name,
            e.title AS event_title,
            e.emotion AS emotion,
            e.source_count AS source_count,
            e.event_credibility_score AS credibility,
            e.risk_score AS risk_score,
            e.risk_level AS risk_level,
            e.current_stage AS current_stage

        ORDER BY
            event_type,

            CASE
                WHEN $view_mode = '风险重点'
                THEN toFloat(coalesce(e.risk_score, 0))
                ELSE 0
            END DESC,

            CASE e.risk_level
                WHEN '黄色' THEN 2
                ELSE 1
            END DESC,

            toInteger(coalesce(e.source_count, 0)) DESC,

            toFloat(
                coalesce(
                    e.event_credibility_score,
                    0
                )
            ) DESC
        """,
        {
            "view_mode": view_mode
        }
    )


    if event_df.empty:

        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame()
        )


    # --------------------------------------------------------
    # 每个事件类型保留前 N 个
    # --------------------------------------------------------

    selected_df = (
        event_df
        .groupby(
            "event_type",
            group_keys=False
        )
        .head(events_per_type)
        .copy()
    )


    event_ids = (
        selected_df["event_id"]
        .dropna()
        .astype(str)
        .tolist()
    )


    # --------------------------------------------------------
    # 5.2 事件 → 公司 / 行业
    # --------------------------------------------------------

    entity_df = run_query(
        """
        MATCH
            (e:Event {kg_version:'v4'})

        WHERE
            e.node_id IN $event_ids


        OPTIONAL MATCH
            (e)
            -[:`涉及公司`]->
            (c:Company)


        OPTIONAL MATCH
            (e)
            -[:`涉及行业`]->
            (i:Industry)


        RETURN

            e.node_id AS event_id,

            c.node_id AS company_id,

            c.display_name AS company_name,

            c.trading_code AS trading_code,

            i.node_id AS industry_id,

            i.display_name AS industry_name
        """,

        {
            "event_ids": event_ids
        }
    )


    # --------------------------------------------------------
    # 5.3 新闻来源 → 聚合事件
    # --------------------------------------------------------

    if include_sources:

        source_df = run_query(
            """
            MATCH
                (src:Source {kg_version:'v4'})
                -[r:`报道事件`]->
                (e:Event {kg_version:'v4'})

            WHERE

                e.node_id IN $event_ids

                AND (

                    r.has_official = true

                    OR toInteger(
                        coalesce(
                            src.report_count,
                            0
                        )
                    ) >= 3

                    OR toInteger(
                        coalesce(
                            e.source_count,
                            0
                        )
                    ) >= 3
                )


            RETURN

                e.node_id AS event_id,

                src.node_id AS source_id,

                src.display_name AS source_name,

                src.name AS source_full_name,

                src.report_count AS report_count,

                src.avg_article_credibility
                    AS avg_credibility,

                r.has_official AS has_official


            ORDER BY

                event_id,

                r.has_official DESC,

                toInteger(
                    coalesce(
                        src.report_count,
                        0
                    )
                ) DESC
            """,

            {
                "event_ids": event_ids
            }
        )


        if not source_df.empty:

            source_df = (
                source_df
                .groupby(
                    "event_id",
                    group_keys=False
                )
                .head(sources_per_event)
                .copy()
            )

    else:

        source_df = pd.DataFrame()


    return (
        selected_df,
        entity_df,
        source_df
    )


# ============================================================
# 6. PyVis 全局知识图谱
# ============================================================

def build_global_network(
    event_df,
    entity_df,
    source_df,
    view_mode
):

    view_config = VIEW_CONFIG[view_mode]

    event_color = view_config["event_color"]

    event_border = view_config["event_border"]


    # --------------------------------------------------------
    # 创建交互网络
    # --------------------------------------------------------

    net = Network(

        height="760px",

        width="100%",

        directed=True,

        bgcolor="#FFFFFF",

        font_color="#16324F",

        neighborhood_highlight=True,

        cdn_resources="in_line"
    )


    added_nodes = set()
    added_edges = set()


    # ========================================================
    # 6.1 事件类型节点
    # ========================================================

    for event_type in (
        event_df["event_type"]
        .dropna()
        .unique()
    ):

        type_id = (
            "TYPE::" + str(event_type)
        )


        if type_id not in added_nodes:

            net.add_node(

                type_id,

                label=str(event_type),

                title=(
                    "<b>事件类型</b><br>"
                    + esc(event_type)
                ),

                color="#F3B63A",

                size=48,

                shape="dot",

                mass=8,

                borderWidth=3
            )

            added_nodes.add(type_id)


    # ========================================================
    # 6.2 聚合事件
    # ========================================================

    for _, row in event_df.iterrows():

        event_id = str(
            row["event_id"]
        )

        event_type = str(
            row["event_type"]
        )

        type_id = (
            "TYPE::" + event_type
        )


        # ----------------------------------------------------
        # Hover 内容
        # ----------------------------------------------------

        title = f"""
        <b>聚合事件</b><br>
        {esc(row.get("event_title"))}
        <hr>
        <b>事件类型：</b>{esc(event_type)}<br>
        <b>事件情绪：</b>{esc(row.get("emotion"))}<br>
        <b>可信度：</b>{safe_float(row.get("credibility")):.1f}<br>
        <b>来源数量：</b>{safe_int(row.get("source_count"))}<br>
        <b>当前阶段：</b>{esc(row.get("current_stage"))}<br>
        <b>风险等级：</b>{esc(row.get("risk_level"))}<br>
        <b>风险评分：</b>{safe_float(row.get("risk_score")):.1f}
        """


        if event_id not in added_nodes:

            net.add_node(

                event_id,

                label=short_text(
                    row.get("event_name")
                    or row.get("event_title"),
                    15
                ),

                title=title,

                color=event_color,

                borderColor=event_border,

                size=25,

                shape="dot",

                mass=3,

                borderWidth=2
            )

            added_nodes.add(
                event_id
            )


        edge_key = (
            type_id,
            event_id,
            "包含事件"
        )


        if edge_key not in added_edges:

            net.add_edge(

                type_id,

                event_id,

                label="包含事件",

                title="包含事件",

                color="#D69212",

                width=2
            )

            added_edges.add(
                edge_key
            )


    # ========================================================
    # 6.3 公司 / 行业
    # ========================================================

    if not entity_df.empty:

        for _, row in entity_df.iterrows():

            event_id = str(
                row["event_id"]
            )


            # ------------------------------------------------
            # 公司
            # ------------------------------------------------

            if pd.notna(
                row.get("company_id")
            ):

                company_id = str(
                    row["company_id"]
                )

                company_name = (
                    row.get("company_name")
                    or company_id
                )


                if company_id not in added_nodes:

                    net.add_node(

                        company_id,

                        label=short_text(
                            company_name,
                            10
                        ),

                        title=(
                            "<b>上市公司</b><br>"
                            + esc(company_name)
                            + "<br><b>证券代码：</b>"
                            + esc(
                                row.get(
                                    "trading_code"
                                )
                            )
                        ),

                        color="#45C2D3",

                        size=29,

                        shape="dot",

                        mass=2,

                        borderWidth=2
                    )

                    added_nodes.add(
                        company_id
                    )


                edge_key = (
                    event_id,
                    company_id,
                    "涉及公司"
                )


                if edge_key not in added_edges:

                    net.add_edge(

                        event_id,

                        company_id,

                        label="涉及公司",

                        title="涉及公司",

                        color="#2AA8B9",

                        width=1.7
                    )

                    added_edges.add(
                        edge_key
                    )


            # ------------------------------------------------
            # 行业
            # ------------------------------------------------

            if pd.notna(
                row.get("industry_id")
            ):

                industry_id = str(
                    row["industry_id"]
                )

                industry_name = (
                    row.get("industry_name")
                    or industry_id
                )


                if industry_id not in added_nodes:

                    net.add_node(

                        industry_id,

                        label=short_text(
                            industry_name,
                            9
                        ),

                        title=(
                            "<b>行业</b><br>"
                            + esc(industry_name)
                        ),

                        color="#7A6FF0",

                        size=24,

                        shape="dot",

                        mass=2,

                        borderWidth=2
                    )

                    added_nodes.add(
                        industry_id
                    )


                edge_key = (
                    event_id,
                    industry_id,
                    "涉及行业"
                )


                if edge_key not in added_edges:

                    net.add_edge(

                        event_id,

                        industry_id,

                        label="涉及行业",

                        title="涉及行业",

                        color="#6D5FDB",

                        width=1.6
                    )

                    added_edges.add(
                        edge_key
                    )


    # ========================================================
    # 6.4 新闻来源
    # ========================================================

    if not source_df.empty:

        for _, row in source_df.iterrows():

            event_id = str(
                row["event_id"]
            )

            source_id = str(
                row["source_id"]
            )

            source_name = (
                row.get("source_name")
                or row.get(
                    "source_full_name"
                )
                or source_id
            )


            source_title = f"""
            <b>新闻来源</b><br>
            {esc(row.get("source_full_name") or source_name)}
            <hr>
            <b>报道数量：</b>{safe_int(row.get("report_count"))}<br>
            <b>平均可信度：</b>{safe_float(row.get("avg_credibility")):.1f}<br>
            <b>含官方证据：</b>{
                '是'
                if row.get("has_official")
                else '否'
            }
            """


            if source_id not in added_nodes:

                net.add_node(

                    source_id,

                    label=short_text(
                        source_name,
                        9
                    ),

                    title=source_title,

                    color="#D95686",

                    size=18,

                    shape="dot",

                    mass=1,

                    borderWidth=2
                )

                added_nodes.add(
                    source_id
                )


            edge_key = (
                source_id,
                event_id,
                "报道事件"
            )


            if edge_key not in added_edges:

                net.add_edge(

                    source_id,

                    event_id,

                    label="报道事件",

                    title="报道事件",

                    color="#C74475",

                    width=1.0
                )

                added_edges.add(
                    edge_key
                )


    # ========================================================
    # 6.5 力导向布局
    #
    # 目标：
    # 黄色 EventType 成为几个大中心
    # 蓝色事件围绕事件类型
    # 公司 / 行业 / 来源位于外围
    # ========================================================

    net.set_options(
        """
        {
          "nodes": {

            "font": {
              "size": 12,
              "face": "Arial",
              "color": "#243B53"
            }
          },

          "edges": {

            "arrows": {
              "to": {
                "enabled": true,
                "scaleFactor": 0.45
              }
            },

            "font": {
              "size": 9,
              "align": "middle",
              "color": "#52677B",
              "background": "rgba(247,250,252,0.88)"
            },

            "smooth": {
              "enabled": true,
              "type": "dynamic"
            }
          },

          "interaction": {

            "hover": true,

            "tooltipDelay": 120,

            "hideEdgesOnDrag": true,

            "navigationButtons": true,

            "keyboard": true
          },

          "physics": {

            "enabled": true,

            "solver": "forceAtlas2Based",

            "forceAtlas2Based": {

              "gravitationalConstant": -55,

              "centralGravity": 0.008,

              "springLength": 145,

              "springConstant": 0.055,

              "damping": 0.46,

              "avoidOverlap": 0.65
            },

            "stabilization": {

              "enabled": true,

              "iterations": 350,

              "updateInterval": 25
            }
          }
        }
        """
    )


    return net


# ============================================================
# 7. 页面标题
# ============================================================

st.markdown(
    '<div class="main-title">'
    '面向上市公司的事件驱动智能识别、可信评估与脉络追踪'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">'
    '事件识别 · 可信评估 · 事件聚合 · 脉络追踪 · 风险预警'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# 8. 数据库连接检查
# ============================================================

try:

    get_driver()

except Exception as e:

    st.error(
        "Neo4j 数据库连接失败"
    )

    st.code(
        str(e)
    )

    st.stop()


# ============================================================
# 9. KPI
# ============================================================

kpi_df = run_query(
    """
    MATCH (e:Event {kg_version:'v4'})

    WITH count(e) AS events

    OPTIONAL MATCH
        (c:Company {kg_version:'v4'})

    WITH
        events,
        count(c) AS companies

    OPTIONAL MATCH
        (i:Industry {kg_version:'v4'})

    WITH
        events,
        companies,
        count(i) AS industries

    OPTIONAL MATCH
        (s:Source {kg_version:'v4'})

    WITH
        events,
        companies,
        industries,
        count(s) AS sources

    OPTIONAL MATCH
        (stg:Stage {kg_version:'v4'})

    RETURN
        events,
        companies,
        industries,
        sources,
        count(stg) AS stages
    """
)


if not kpi_df.empty:

    row = kpi_df.iloc[0]

    c1, c2, c3, c4, c5 = st.columns(
        5
    )

    c1.metric(
        "聚合事件",
        safe_int(row["events"])
    )

    c2.metric(
        "上市公司",
        safe_int(row["companies"])
    )

    c3.metric(
        "涉及行业",
        safe_int(row["industries"])
    )

    c4.metric(
        "新闻来源",
        safe_int(row["sources"])
    )

    c5.metric(
        "演化阶段",
        safe_int(row["stages"])
    )


st.markdown("---")


# ============================================================
# 10. 知识图谱分析视图切换
# ============================================================

st.markdown(
    "### 知识图谱分析视图"
)

view_mode = st.radio(
    "选择知识图谱模式",
    [
        "全局事件",
        "正面事件",
        "负面事件",
        "风险重点"
    ],
    horizontal=True,
    index=0,
    label_visibility="collapsed"
)

view_config = VIEW_CONFIG[
    view_mode
]

st.caption(
    view_config["description"]
)

st.markdown("---")


# ============================================================
# 10. 侧边栏：知识图谱控制
# ============================================================

with st.sidebar:

    st.title(
        "知识图谱控制台"
    )

    st.caption(
        "Event-Centric KG v4"
    )

    st.markdown("---")


    events_per_type = st.slider(

        "每种事件类型显示事件数",

        min_value=5,

        max_value=35,

        value=20,

        step=5
    )


    include_sources = st.checkbox(

        "显示新闻来源",

        value=True
    )


    sources_per_event = st.slider(

        "每个事件最多显示新闻来源",

        min_value=1,

        max_value=4,

        value=2,

        disabled=not include_sources
    )


    st.markdown("---")


    st.caption(
        "鼠标可拖动节点、滚轮缩放、悬停查看详细属性。"
    )


# ============================================================
# 11. 全局知识图谱
# ============================================================

st.subheader(
    view_config["title"]
)


st.markdown(
    """
    <div class="graph-legend">

    <b>图例：</b>

    🟡 事件类型　

    🔵 聚合事件　

    🟦 上市公司　

    🟣 行业　

    🩷 新闻来源

    </div>
    """,
    unsafe_allow_html=True
)


with st.spinner(
    "正在从 Neo4j 构建全局知识图谱..."
):

    event_df, entity_df, source_df = (
        load_global_graph_data(
            view_mode,
            events_per_type,
            include_sources,
            sources_per_event
        )
    )


    if event_df.empty:

        st.warning(
            "没有读取到 EventType → Event 数据。"
        )

        st.info(
            "请先确认你之前已经在 Neo4j 中运行过“建立全局视图层”的 01 代码。"
        )

    else:

        graph = build_global_network(
            event_df,
            entity_df,
            source_df,
            view_mode
        )


        # ----------------------------------------
        # 写成临时 HTML
        # ----------------------------------------

        graph_file = Path(
            "global_knowledge_graph.html"
        )


        graph.write_html(
            str(graph_file),

            notebook=False,

            open_browser=False
        )


        # ----------------------------------------
        # 当前 Streamlit 优先使用 st.iframe
        # 老版本则自动 fallback
        # ----------------------------------------

        if hasattr(st, "iframe"):

            st.iframe(

                graph_file,

                height=780
            )

        else:

            import streamlit.components.v1 as components

            graph_html = (
                graph_file
                .read_text(
                    encoding="utf-8"
                )
            )

            components.html(

                graph_html,

                height=780,

                scrolling=False
            )


# ============================================================
# 12. 当前图谱统计
# ============================================================

st.caption(
    f"""
    当前视图：
    {len(event_df):,} 个聚合事件 ·
    {entity_df['company_id'].nunique() if not entity_df.empty else 0:,} 家公司 ·
    {entity_df['industry_id'].nunique() if not entity_df.empty else 0:,} 个行业 ·
    {source_df['source_id'].nunique() if not source_df.empty else 0:,} 个新闻来源
    """
)
