import streamlit as st

# ============================================================
# 统一深蓝金融科技主题
# ============================================================

BG = "#07192E"
PANEL = "#0B2847"
PANEL_2 = "#102F50"
GRID = "#214768"

TEXT = "#EAF6FF"
MUTED = "#8FB4D6"

BLUE = "#2F80FF"
CYAN = "#38C9FF"
SKY = "#7BC8FF"
ICE = "#BFE9FF"

POSITIVE = "#2ED47A"
NEGATIVE = "#FF5C7A"
NEUTRAL = "#8EA6C1"
WARNING = "#FFB020"

FONT = (
    "PingFang SC, Hiragino Sans GB, Heiti SC, "
    "Arial Unicode MS, Arial, sans-serif"
)


def apply_theme():
    st.markdown(
        f"""
        <style>

        html, body, [class*="css"] {{
            font-family: {FONT};
        }}

        .stApp {{
            background:
                radial-gradient(
                    circle at 15% 0%,
                    rgba(47,128,255,0.10),
                    transparent 30%
                ),
                {BG};
            color: {TEXT};
        }}

        [data-testid="stHeader"] {{
            background: rgba(7,25,46,0.93);
        }}

        [data-testid="stSidebar"] {{
            background: #081B31;
            border-right: 1px solid {GRID};
        }}

        [data-testid="stSidebar"] * {{
            color: {TEXT};
        }}

        h1, h2, h3 {{
            color: {TEXT};
        }}

        p, label {{
            color: {TEXT};
        }}

        div[data-testid="stMetric"] {{
            background: linear-gradient(
                145deg,
                {PANEL},
                {PANEL_2}
            );
            border: 1px solid {GRID};
            border-radius: 14px;
            padding: 16px 18px;
        }}

        div[data-testid="stMetricLabel"] {{
            color: {MUTED};
        }}

        div[data-testid="stMetricValue"] {{
            color: {CYAN};
        }}

        [data-testid="stDataFrame"] {{
            border: 1px solid {GRID};
            border-radius: 10px;
            overflow: hidden;
        }}

        .section-subtitle {{
            color: {MUTED};
            font-size: 14px;
            margin-top: -8px;
            margin-bottom: 14px;
        }}

        .blue-note {{
            background: rgba(47,128,255,0.08);
            border: 1px solid rgba(56,201,255,0.20);
            border-left: 4px solid {CYAN};
            padding: 10px 14px;
            border-radius: 8px;
            color: {MUTED};
            margin-bottom: 16px;
        }}

        hr {{
            border-color: {GRID};
        }}

        </style>
        """,
        unsafe_allow_html=True,
    )


def style_fig(fig, title=None, height=420, left_margin=110, right_margin=40, bottom_margin=50):
    fig.update_layout(
        title=dict(
            text=title or "",
            font=dict(
                size=17,
                color=TEXT
            ),
            x=0.02
        ),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family=FONT,
            color=TEXT
        ),
        margin=dict(
            l=left_margin,
            r=right_margin,
            t=65,
            b=bottom_margin
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=MUTED)
        ),
        hoverlabel=dict(
            bgcolor=PANEL_2,
            font_color=TEXT,
            bordercolor=GRID
        )
    )

    fig.update_xaxes(
        automargin=True,
        showgrid=False,
        linecolor=GRID,
        tickfont=dict(color=MUTED),
        title_font=dict(color=MUTED)
    )

    fig.update_yaxes(
        automargin=True,
        gridcolor=GRID,
        gridwidth=0.6,
        zeroline=False,
        linecolor=GRID,
        tickfont=dict(color=MUTED),
        title_font=dict(color=MUTED)
    )

    return fig
