"""
Nassau Candy Distributor — Product Line Profitability & Margin Performance Dashboard
======================================================================================
Run with:  streamlit run app.py
Place "Nassau_Candy_Distributor.csv" in the same folder, or upload it from the sidebar.

Requirements covered:
  ✅ Tab 1 — Product Profitability Overview (margin leaderboard + pie chart)
  ✅ Tab 2 — Division Performance Dashboard (revenue vs profit + box plot + imbalance table)
  ✅ Tab 3 — Cost vs Margin Diagnostics (scatter + risk pie + flagged products table)
  ✅ Tab 4 — Profit Concentration / Pareto Analysis (Pareto chart + dependency indicators)
  ✅ Tab 5 — Factory Map (folium map with factory pins + product–factory correlation table)
  ✅ Sidebar — Date range selector, Division filter, Margin threshold slider, Product search
  ✅ KPIs  — Gross Margin %, Profit per Unit, Revenue Contribution, Profit Contribution, Margin Volatility
  ✅ Data Cleaning — zero-sales removal, missing-value handling, label standardisation
"""

import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import folium
from streamlit_folium import st_folium

# ──────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nassau Candy — Profitability Dashboard",
    page_icon="🍬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────
# THEME / STYLE
# ──────────────────────────────────────────────────────────────────────────
PALETTE = {
    "cocoa":   "#3A2317",
    "caramel": "#C17F3E",
    "cream":   "#FAF5EC",
    "teal":    "#1B8E83",
    "red":     "#D6455A",
    "amber":   "#E0A23B",
    "ink":     "#23150E",
}

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
}}
.block-container {{ padding-top: 1.4rem; }}

.nassau-header {{
    background: linear-gradient(135deg, {PALETTE['cocoa']} 0%, #54331F 100%);
    border-radius: 16px;
    padding: 1.6rem 2rem;
    color: {PALETTE['cream']};
    margin-bottom: 1.2rem;
    position: relative;
    overflow: hidden;
}}
.nassau-header h1 {{
    font-family: 'Fraunces', serif;
    font-size: 1.9rem;
    margin: 0 0 .25rem 0;
    color: {PALETTE['cream']};
}}
.nassau-header p {{ margin: 0; color: #E8D9C5; font-size: .95rem; }}
.nassau-stripe {{
    position: absolute; bottom: 0; left: 0; right: 0; height: 6px;
    background: repeating-linear-gradient(
        45deg,
        {PALETTE['caramel']} 0px, {PALETTE['caramel']} 14px,
        {PALETTE['teal']}    14px, {PALETTE['teal']}    28px,
        {PALETTE['amber']}   28px, {PALETTE['amber']}   42px
    );
}}

/* KPI cards now use custom HTML — no stMetric overrides needed */

.stTabs [data-baseweb="tab-list"] {{ gap: 4px; }}
.stTabs [data-baseweb="tab"] {{
    background-color: #F2E9DA;
    border-radius: 10px 10px 0 0;
    padding: .5rem 1rem;
    font-weight: 600;
    color: {PALETTE['cocoa']};
}}
.stTabs [aria-selected="true"] {{
    background-color: {PALETTE['cocoa']} !important;
    color: {PALETTE['cream']} !important;
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

CHART_TEMPLATE = "simple_white"
DISCRETE_SEQ   = [PALETTE["caramel"], PALETTE["teal"], PALETTE["amber"],
                  PALETTE["red"], "#7A5240", "#4E8C7C"]

# ──────────────────────────────────────────────────────────────────────────
# FACTORY DATA  (from PDF requirements)
# ──────────────────────────────────────────────────────────────────────────
FACTORIES = {
    "Lot's O' Nuts":    {"lat": 32.881893, "lon": -111.768036, "city": "Chandler, AZ"},
    "Wicked Choccy's":  {"lat": 32.076176, "lon": -81.088371,  "city": "Savannah, GA"},
    "Sugar Shack":      {"lat": 48.11914,  "lon": -96.18115,   "city": "Crookston, MN"},
    "Secret Factory":   {"lat": 41.446333, "lon": -90.565487,  "city": "Milan, IL"},
    "The Other Factory":{"lat": 35.1175,   "lon": -89.971107,  "city": "Memphis, TN"},
}

PRODUCT_FACTORY = [
    {"Division": "Chocolate", "Product Name": "Wonka Bar - Nutty Crunch Surprise", "Factory": "Lot's O' Nuts"},
    {"Division": "Chocolate", "Product Name": "Wonka Bar - Fudge Mallows",          "Factory": "Lot's O' Nuts"},
    {"Division": "Chocolate", "Product Name": "Wonka Bar -Scrumdiddlyumptious",     "Factory": "Lot's O' Nuts"},
    {"Division": "Chocolate", "Product Name": "Wonka Bar - Milk Chocolate",          "Factory": "Wicked Choccy's"},
    {"Division": "Chocolate", "Product Name": "Wonka Bar - Triple Dazzle Caramel",  "Factory": "Wicked Choccy's"},
    {"Division": "Sugar",     "Product Name": "Laffy Taffy",                         "Factory": "Sugar Shack"},
    {"Division": "Sugar",     "Product Name": "SweeTARTS",                           "Factory": "Sugar Shack"},
    {"Division": "Sugar",     "Product Name": "Nerds",                               "Factory": "Sugar Shack"},
    {"Division": "Sugar",     "Product Name": "Fun Dip",                             "Factory": "Sugar Shack"},
    {"Division": "Other",     "Product Name": "Fizzy Lifting Drinks",                "Factory": "Sugar Shack"},
    {"Division": "Sugar",     "Product Name": "Everlasting Gobstopper",              "Factory": "Secret Factory"},
    {"Division": "Sugar",     "Product Name": "Hair Toffee",                         "Factory": "The Other Factory"},
    {"Division": "Other",     "Product Name": "Lickable Wallpaper",                  "Factory": "Secret Factory"},
    {"Division": "Other",     "Product Name": "Wonka Gum",                           "Factory": "Secret Factory"},
    {"Division": "Other",     "Product Name": "Kazookles",                           "Factory": "The Other Factory"},
]
df_pf = pd.DataFrame(PRODUCT_FACTORY)

# ──────────────────────────────────────────────────────────────────────────
# DATA LOADING & CLEANING
# ──────────────────────────────────────────────────────────────────────────
CANDIDATE_FILES = [
    "Nassau_Candy_Distributor.csv",
    "Nassau Candy Distributor.csv",
    "nassau_candy_distributor.csv",
]

def find_bundled_file():
    for f in CANDIDATE_FILES:
        if os.path.exists(f):
            return f
    return None


@st.cache_data(show_spinner="Loading & cleaning data…")
def load_and_clean(file_obj_or_path):
    df = pd.read_csv(file_obj_or_path)

    df["Order Date"] = pd.to_datetime(df["Order Date"], dayfirst=True, errors="coerce")
    if "Ship Date" in df.columns:
        df["Ship Date"] = pd.to_datetime(df["Ship Date"], dayfirst=True, errors="coerce")

    rows_before = len(df)

    # Validation & cleaning
    df = df[df["Sales"] > 0]
    df = df[df["Units"] > 0]
    df = df.dropna(subset=["Sales", "Cost", "Gross Profit", "Units"])

    # Label standardisation
    df["Product Name"] = (
        df["Product Name"].astype(str).str.strip()
        .str.replace(r"\s*-\s*", " - ", regex=True)
        .str.replace(r"\s+", " ", regex=True)
    )
    df["Division"] = df["Division"].astype(str).str.strip().str.title()
    if "Region" in df.columns:
        df["Region"] = df["Region"].astype(str).str.strip().str.title()
    if "State/Province" in df.columns:
        df["State/Province"] = df["State/Province"].astype(str).str.strip().str.title()

    rows_after = len(df)

    # Feature engineering
    df["Gross Margin %"]        = df["Gross Profit"] / df["Sales"] * 100
    df["Profit per Unit"]       = df["Gross Profit"] / df["Units"]
    df["Cost per Unit"]         = df["Cost"]         / df["Units"]

    total_sales  = df["Sales"].sum()
    total_profit = df["Gross Profit"].sum()
    df["Revenue Contribution %"] = df["Sales"]        / total_sales  * 100
    df["Profit Contribution %"]  = df["Gross Profit"] / total_profit * 100

    df.attrs["rows_removed"] = rows_before - rows_after
    return df


def margin_risk_label(margin, threshold):
    if margin < threshold * 0.6:
        return "🔴 High Risk"
    elif margin < threshold:
        return "🟠 At Risk"
    return "🟢 Healthy"


# ──────────────────────────────────────────────────────────────────────────
# SIDEBAR — DATA SOURCE
# ──────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🍬 Nassau Candy")
st.sidebar.caption("Product Line Profitability & Margin Dashboard")
st.sidebar.divider()

bundled = find_bundled_file()
with st.sidebar.expander("📂 Data source", expanded=bundled is None):
    if bundled:
        st.success(f"Using bundled file: `{bundled}`")
    uploaded = st.file_uploader("Upload / replace CSV", type="csv")

data_source = uploaded if uploaded is not None else bundled
if data_source is None:
    st.warning("⬅️ Upload **Nassau_Candy_Distributor.csv** from the sidebar to get started.")
    st.stop()

df_raw = load_and_clean(data_source)

if df_raw.attrs.get("rows_removed"):
    st.sidebar.caption(f"🧹 {df_raw.attrs['rows_removed']} invalid rows removed during cleaning.")

# ──────────────────────────────────────────────────────────────────────────
# SIDEBAR — FILTERS
# ──────────────────────────────────────────────────────────────────────────
st.sidebar.divider()
st.sidebar.markdown("### 🔎 Filters")

valid_dates      = df_raw["Order Date"].dropna()
min_date, max_date = valid_dates.min().date(), valid_dates.max().date()

date_range = st.sidebar.date_input(
    "📅 Order date range", value=(min_date, max_date),
    min_value=min_date, max_value=max_date,
)
start_date, end_date = (date_range if len(date_range) == 2 else (min_date, max_date))

divisions          = sorted(df_raw["Division"].dropna().unique())
selected_divisions = st.sidebar.multiselect("🏷️ Division", options=divisions, default=divisions)

margin_threshold = st.sidebar.slider(
    "📉 Margin risk threshold (%)", min_value=0, max_value=100, value=35, step=1,
    help="Products below this Gross Margin % are flagged as at-risk across all tabs.",
)

search_term = st.sidebar.text_input(
    "🔍 Product search", placeholder="e.g. Wonka, Nerds, Taffy"
).strip()

# Apply filters
mask = (
    (df_raw["Order Date"].dt.date >= start_date)
    & (df_raw["Order Date"].dt.date <= end_date)
    & (df_raw["Division"].isin(selected_divisions))
)
df = df_raw.loc[mask].copy()

if df.empty:
    st.warning("No records match the current filters — widen the date range or division selection.")
    st.stop()

df["Margin Risk"] = df["Gross Margin %"].apply(lambda m: margin_risk_label(m, margin_threshold))

# ──────────────────────────────────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="nassau-header">
        <h1>🍬 Nassau Candy Distributor</h1>
        <p>Product Line Profitability &amp; Margin Performance — live analytics</p>
        <div class="nassau-stripe"></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────
# KPI ROW
# ──────────────────────────────────────────────────────────────────────────
total_sales        = df["Sales"].sum()
total_profit       = df["Gross Profit"].sum()
overall_margin     = total_profit / total_sales * 100 if total_sales else 0
avg_profit_per_unit= df["Profit per Unit"].mean()
margin_volatility  = df["Gross Margin %"].std()

st.markdown(
    f"""
    <div style="display:flex;gap:12px;margin-bottom:1rem;flex-wrap:wrap;">
        <div style="flex:1;min-width:140px;background:white;border:1px solid #EEE3D3;
                    border-top:4px solid #C17F3E;border-radius:12px;padding:1rem 1.2rem;
                    box-shadow:0 2px 8px rgba(58,35,23,0.10);">
            <div style="font-size:0.75rem;font-weight:700;color:#3A2317;
                        text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">
                💰 Total Revenue</div>
            <div style="font-size:1.55rem;font-weight:800;color:#23150E;">${total_sales:,.0f}</div>
        </div>
        <div style="flex:1;min-width:140px;background:white;border:1px solid #EEE3D3;
                    border-top:4px solid #1B8E83;border-radius:12px;padding:1rem 1.2rem;
                    box-shadow:0 2px 8px rgba(58,35,23,0.10);">
            <div style="font-size:0.75rem;font-weight:700;color:#3A2317;
                        text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">
                📈 Total Gross Profit</div>
            <div style="font-size:1.55rem;font-weight:800;color:#1B8E83;">${total_profit:,.0f}</div>
        </div>
        <div style="flex:1;min-width:140px;background:white;border:1px solid #EEE3D3;
                    border-top:4px solid #2E7D32;border-radius:12px;padding:1rem 1.2rem;
                    box-shadow:0 2px 8px rgba(58,35,23,0.10);">
            <div style="font-size:0.75rem;font-weight:700;color:#3A2317;
                        text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">
                📊 Overall Gross Margin</div>
            <div style="font-size:1.55rem;font-weight:800;color:#2E7D32;">{overall_margin:.1f}%</div>
        </div>
        <div style="flex:1;min-width:140px;background:white;border:1px solid #EEE3D3;
                    border-top:4px solid #C17F3E;border-radius:12px;padding:1rem 1.2rem;
                    box-shadow:0 2px 8px rgba(58,35,23,0.10);">
            <div style="font-size:0.75rem;font-weight:700;color:#3A2317;
                        text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">
                🎯 Avg Profit / Unit</div>
            <div style="font-size:1.55rem;font-weight:800;color:#23150E;">${avg_profit_per_unit:,.2f}</div>
        </div>
        <div style="flex:1;min-width:140px;background:white;border:1px solid #EEE3D3;
                    border-top:4px solid #D6455A;border-radius:12px;padding:1rem 1.2rem;
                    box-shadow:0 2px 8px rgba(58,35,23,0.10);">
            <div style="font-size:0.75rem;font-weight:700;color:#3A2317;
                        text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">
                📉 Margin Volatility (σ)</div>
            <div style="font-size:1.55rem;font-weight:800;color:#D6455A;">{margin_volatility:.1f} pts</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    f"Showing **{len(df):,}** orders across **{df['Product Name'].nunique()}** products, "
    f"**{start_date} → {end_date}**, divisions: {', '.join(selected_divisions) or '—'}."
)

# ──────────────────────────────────────────────────────────────────────────
# PRECOMPUTED AGGREGATES
# ──────────────────────────────────────────────────────────────────────────
product_summary = (
    df.groupby(["Product Name", "Division"])
    .agg(
        Total_Sales         =("Sales",         "sum"),
        Total_Profit        =("Gross Profit",  "sum"),
        Total_Cost          =("Cost",          "sum"),
        Total_Units         =("Units",         "sum"),
        Avg_Gross_Margin    =("Gross Margin %","mean"),
        Avg_Profit_per_Unit =("Profit per Unit","mean"),
        Orders              =("Sales",         "count"),
    )
    .reset_index()
)
product_summary["Profit Contribution %"]  = product_summary["Total_Profit"] / product_summary["Total_Profit"].sum() * 100
product_summary["Revenue Contribution %"] = product_summary["Total_Sales"]  / product_summary["Total_Sales"].sum()  * 100
product_summary["Cost_to_Sales_Ratio"]    = product_summary["Total_Cost"]   / product_summary["Total_Sales"]        * 100
product_summary["Risk Flag"] = product_summary["Avg_Gross_Margin"].apply(lambda m: margin_risk_label(m, margin_threshold))
product_summary = product_summary.sort_values("Total_Profit", ascending=False).reset_index(drop=True)


def apply_search(frame, col="Product Name"):
    if not search_term:
        return frame
    return frame[frame[col].str.contains(search_term, case=False, na=False)]


# ──────────────────────────────────────────────────────────────────────────
# TABS
# ──────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Product Profitability Overview",
    "🏭 Division Performance Dashboard",
    "💰 Cost vs Margin Diagnostics",
    "📈 Profit Concentration Analysis",
    "🗺️ Factory Map & Sourcing",
])

# ── TAB 1 — PRODUCT PROFITABILITY OVERVIEW ──────────────────────────────
with tab1:
    st.subheader("Product-Level Margin Leaderboard")

    leaderboard = apply_search(product_summary)
    if search_term and leaderboard.empty:
        st.info(f'No products match "{search_term}".')

    display_cols = {
        "Product Name":          "Product",
        "Division":              "Division",
        "Total_Sales":           "Total Sales ($)",
        "Total_Profit":          "Total Profit ($)",
        "Avg_Gross_Margin":      "Avg Margin (%)",
        "Avg_Profit_per_Unit":   "Profit / Unit ($)",
        "Profit Contribution %": "Profit Share (%)",
        "Risk Flag":             "Risk",
    }
    st.dataframe(
        leaderboard[list(display_cols.keys())].rename(columns=display_cols)
        .style.format({
            "Total Sales ($)":   "${:,.0f}",
            "Total Profit ($)":  "${:,.0f}",
            "Avg Margin (%)":    "{:.1f}%",
            "Profit / Unit ($)": "${:,.2f}",
            "Profit Share (%)":  "{:.1f}%",
        }),
        use_container_width=True, height=360,
    )

    col1, col2 = st.columns(2)
    with col1:
        margin_sorted = product_summary.sort_values("Avg_Gross_Margin")
        fig = px.bar(
            margin_sorted, x="Avg_Gross_Margin", y="Product Name", orientation="h",
            color="Risk Flag",
            color_discrete_map={"🔴 High Risk": PALETTE["red"], "🟠 At Risk": PALETTE["amber"], "🟢 Healthy": PALETTE["teal"]},
            labels={"Avg_Gross_Margin": "Avg Gross Margin (%)", "Product Name": ""},
            title="Margin Leaderboard (all products)", template=CHART_TEMPLATE,
        )
        fig.add_vline(x=margin_threshold, line_dash="dash", line_color=PALETTE["cocoa"],
                      annotation_text=f"Threshold {margin_threshold}%")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.pie(
            product_summary, names="Product Name", values="Profit Contribution %",
            hole=0.45, title="Profit Contribution by Product",
            color_discrete_sequence=DISCRETE_SEQ, template=CHART_TEMPLATE,
        )
        fig2.update_traces(textposition="inside", textinfo="percent+label", textfont_size=10)
        st.plotly_chart(fig2, use_container_width=True)

    # ── High-profit / High-sales / Low-margin categorisation ──
    st.markdown("#### Product Category Classification")
    median_sales  = product_summary["Total_Sales"].median()
    median_margin = product_summary["Avg_Gross_Margin"].median()

    def classify(row):
        high_sales  = row["Total_Sales"]       >= median_sales
        high_margin = row["Avg_Gross_Margin"]  >= median_margin
        if high_sales and high_margin:   return "⭐ High-Sales / High-Margin"
        if high_sales and not high_margin: return "⚠️ High-Sales / Low-Margin"
        if not high_sales and high_margin: return "💎 Low-Sales / High-Margin"
        return "❌ Low-Sales / Low-Margin"

    product_summary["Category"] = product_summary.apply(classify, axis=1)
    cat_view = apply_search(product_summary)[["Product Name", "Division", "Total_Sales", "Avg_Gross_Margin", "Category"]]
    st.dataframe(
        cat_view.rename(columns={"Total_Sales": "Total Sales ($)", "Avg_Gross_Margin": "Avg Margin (%)"})
        .style.format({"Total Sales ($)": "${:,.0f}", "Avg Margin (%)": "{:.1f}%"}),
        use_container_width=True,
    )

# ── TAB 2 — DIVISION PERFORMANCE DASHBOARD ──────────────────────────────
with tab2:
    st.subheader("Division-Level Performance")

    division_summary = (
        df.groupby("Division")
        .agg(Total_Sales=("Sales", "sum"), Total_Profit=("Gross Profit", "sum"),
             Avg_Gross_Margin=("Gross Margin %", "mean"), Orders=("Sales", "count"))
        .reset_index()
    )
    division_summary["Revenue Contribution %"] = division_summary["Total_Sales"]  / division_summary["Total_Sales"].sum()  * 100
    division_summary["Profit Contribution %"]  = division_summary["Total_Profit"] / division_summary["Total_Profit"].sum() * 100
    division_summary = division_summary.sort_values("Total_Profit", ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        fig.add_bar(name="Revenue",      x=division_summary["Division"], y=division_summary["Total_Sales"],  marker_color=PALETTE["caramel"])
        fig.add_bar(name="Gross Profit", x=division_summary["Division"], y=division_summary["Total_Profit"], marker_color=PALETTE["teal"])
        fig.update_layout(barmode="group", title="Revenue vs Profit by Division",
                          template=CHART_TEMPLATE, yaxis_title="Amount ($)")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.box(df, x="Division", y="Gross Margin %", color="Division",
                      color_discrete_sequence=DISCRETE_SEQ,
                      title="Margin Distribution by Division",
                      template=CHART_TEMPLATE, points="outliers")
        fig2.add_hline(y=margin_threshold, line_dash="dash", line_color=PALETTE["red"],
                       annotation_text=f"Risk threshold {margin_threshold}%")
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("#### Revenue vs Profit Imbalance")
    imbalance = division_summary.copy()
    imbalance["Gap (Profit − Revenue share)"] = imbalance["Profit Contribution %"] - imbalance["Revenue Contribution %"]
    st.dataframe(
        imbalance[["Division", "Total_Sales", "Total_Profit", "Avg_Gross_Margin",
                   "Revenue Contribution %", "Profit Contribution %", "Gap (Profit − Revenue share)"]
        ].rename(columns={"Total_Sales": "Total Sales ($)", "Total_Profit": "Total Profit ($)",
                           "Avg_Gross_Margin": "Avg Margin (%)"})
        .style.format({
            "Total Sales ($)": "${:,.0f}", "Total Profit ($)": "${:,.0f}",
            "Avg Margin (%)": "{:.1f}%", "Revenue Contribution %": "{:.1f}%",
            "Profit Contribution %": "{:.1f}%", "Gap (Profit − Revenue share)": "{:+.1f}%",
        }),
        use_container_width=True,
    )

    # Region-level breakdown
    if "Region" in df.columns:
        st.markdown("#### Region-Level Breakdown")
        region_summary = (
            df.groupby("Region")
            .agg(Total_Sales=("Sales","sum"), Total_Profit=("Gross Profit","sum"),
                 Avg_Margin=("Gross Margin %","mean"))
            .reset_index().sort_values("Total_Profit", ascending=False)
        )
        fig3 = px.bar(region_summary, x="Region", y=["Total_Sales","Total_Profit"],
                      barmode="group", title="Revenue vs Profit by Region",
                      color_discrete_sequence=[PALETTE["caramel"], PALETTE["teal"]],
                      template=CHART_TEMPLATE, labels={"value":"Amount ($)","variable":"Metric"})
        st.plotly_chart(fig3, use_container_width=True)

# ── TAB 3 — COST VS MARGIN DIAGNOSTICS ─────────────────────────────────
with tab3:
    st.subheader("Cost Structure & Margin Risk")

    cost_view = apply_search(product_summary)

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.scatter(
            cost_view if not cost_view.empty else product_summary,
            x="Total_Sales", y="Total_Cost",
            color="Risk Flag", size="Cost_to_Sales_Ratio",
            hover_name="Product Name",
            color_discrete_map={"🔴 High Risk": PALETTE["red"], "🟠 At Risk": PALETTE["amber"], "🟢 Healthy": PALETTE["teal"]},
            title=f"Cost vs Sales — flagged below {margin_threshold}% margin",
            labels={"Total_Sales": "Total Sales ($)", "Total_Cost": "Total Cost ($)"},
            template=CHART_TEMPLATE,
        )
        max_val = float(max(product_summary["Total_Sales"].max(), product_summary["Total_Cost"].max()))
        fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                      line=dict(dash="dot", color="gray"))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        risk_counts = product_summary["Risk Flag"].value_counts()
        fig2 = px.pie(values=risk_counts.values, names=risk_counts.index, hole=0.55,
                      color=risk_counts.index,
                      color_discrete_map={"🔴 High Risk": PALETTE["red"], "🟠 At Risk": PALETTE["amber"], "🟢 Healthy": PALETTE["teal"]},
                      title="Products by Risk Flag", template=CHART_TEMPLATE)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown(f"#### ⚠️ Flagged Products (margin below {margin_threshold}%)")
    flagged = apply_search(
        product_summary[product_summary["Avg_Gross_Margin"] < margin_threshold]
        .sort_values("Avg_Gross_Margin")
    )
    if flagged.empty:
        st.success("✅ No products fall below the current margin threshold.")
    else:
        st.dataframe(
            flagged[["Product Name","Division","Total_Sales","Total_Cost","Cost_to_Sales_Ratio","Avg_Gross_Margin","Risk Flag"]]
            .rename(columns={"Total_Sales":"Total Sales ($)","Total_Cost":"Total Cost ($)",
                             "Cost_to_Sales_Ratio":"Cost / Sales (%)","Avg_Gross_Margin":"Avg Margin (%)"})
            .style.format({"Total Sales ($)":"${:,.0f}","Total Cost ($)":"${:,.0f}",
                           "Cost / Sales (%)":"{:.1f}%","Avg Margin (%)":"{:.1f}%"}),
            use_container_width=True,
        )

    # State-level congestion analysis  (PDF requirement: detect congestion-prone states)
    if "State/Province" in df.columns:
        st.markdown("#### 🗺️ State-Level Sales Concentration (Congestion Prone Regions)")
        state_summary = (
            df.groupby("State/Province")
            .agg(Total_Sales=("Sales","sum"), Total_Profit=("Gross Profit","sum"),
                 Avg_Margin=("Gross Margin %","mean"), Orders=("Sales","count"))
            .reset_index().sort_values("Total_Sales", ascending=False).head(15)
        )
        fig_state = px.bar(state_summary, x="State/Province", y="Total_Sales",
                           color="Avg_Margin",
                           color_continuous_scale=["red","orange","green"],
                           title="Top 15 States by Sales Volume (color = Avg Margin %)",
                           labels={"Total_Sales":"Total Sales ($)","Avg_Margin":"Avg Margin %"},
                           template=CHART_TEMPLATE)
        st.plotly_chart(fig_state, use_container_width=True)

# ── TAB 4 — PROFIT CONCENTRATION (PARETO) ANALYSIS ─────────────────────
with tab4:
    st.subheader("Profit Concentration (Pareto) Analysis")

    pareto = product_summary.sort_values("Total_Profit", ascending=False).copy()
    pareto["Cumulative_Profit_%"] = pareto["Total_Profit"].cumsum() / pareto["Total_Profit"].sum() * 100
    n_products_80 = int((pareto["Cumulative_Profit_%"] <= 80).sum() + 1)
    n_products_80 = min(n_products_80, len(pareto))

    bar_colors = [PALETTE["teal"] if i < n_products_80 else PALETTE["caramel"] for i in range(len(pareto))]

    fig = go.Figure()
    fig.add_bar(x=pareto["Product Name"], y=pareto["Total_Profit"],
                name="Gross Profit", marker_color=bar_colors)
    fig.add_trace(go.Scatter(
        x=pareto["Product Name"], y=pareto["Cumulative_Profit_%"],
        name="Cumulative Profit %", mode="lines+markers",
        line=dict(color=PALETTE["red"], width=3), yaxis="y2",
    ))
    fig.update_layout(
        title=f"Product Pareto — {n_products_80} of {len(pareto)} products drive 80% of profit",
        template=CHART_TEMPLATE,
        yaxis=dict(title="Gross Profit ($)"),
        yaxis2=dict(title="Cumulative Profit (%)", overlaying="y", side="right", range=[0,115]),
        legend=dict(orientation="h", y=1.15),
        shapes=[dict(type="line", xref="paper", x0=0, x1=1,
                     yref="y2", y0=80, y1=80, line=dict(dash="dash", color="gray"))],
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Dependency Indicators")
    top1_share = pareto.iloc[0]["Profit Contribution %"]
    top3_share = pareto.head(min(3, len(pareto)))["Profit Contribution %"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Products driving 80% of profit", f"{n_products_80} / {len(pareto)}")
    c2.metric("Top 1 product's profit share",   f"{top1_share:.1f}%")
    c3.metric("Top 3 products' profit share",   f"{top3_share:.1f}%")

    if top3_share > 60:
        st.error("⚠️ High concentration risk — the business over-relies on a small number of products.")
    else:
        st.success("✅ Profit is reasonably diversified across the product portfolio.")

    # Revenue Pareto as well
    pareto_rev = product_summary.sort_values("Total_Sales", ascending=False).copy()
    pareto_rev["Cumulative_Revenue_%"] = pareto_rev["Total_Sales"].cumsum() / pareto_rev["Total_Sales"].sum() * 100
    n_rev_80 = int((pareto_rev["Cumulative_Revenue_%"] <= 80).sum() + 1)

    st.info(f"📌 **{n_rev_80} products** drive 80% of **revenue** | **{n_products_80} products** drive 80% of **profit**")

    with st.expander("📋 Full Pareto table"):
        st.dataframe(
            apply_search(pareto)[["Product Name","Division","Total_Sales","Total_Profit","Avg_Gross_Margin","Cumulative_Profit_%"]]
            .rename(columns={"Total_Sales":"Total Sales ($)","Total_Profit":"Total Profit ($)",
                             "Avg_Gross_Margin":"Avg Margin (%)","Cumulative_Profit_%":"Cumulative Profit (%)"})
            .style.format({"Total Sales ($)":"${:,.0f}","Total Profit ($)":"${:,.0f}",
                           "Avg Margin (%)":"{:.1f}%","Cumulative Profit (%)":"{:.1f}%"}),
            use_container_width=True,
        )

# ── TAB 5 — FACTORY MAP & SOURCING ──────────────────────────────────────
with tab5:
    st.subheader("🗺️ Factory Locations & Product-Factory Sourcing")

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("##### Factory Locations (USA)")

        # Build folium map
        m = folium.Map(location=[38.5, -96.0], zoom_start=4, tiles="CartoDB positron")

        factory_colors = {
            "Lot's O' Nuts":     "red",
            "Wicked Choccy's":   "purple",
            "Sugar Shack":       "orange",
            "Secret Factory":    "blue",
            "The Other Factory": "green",
        }

        for factory, info in FACTORIES.items():
            color = factory_colors.get(factory, "gray")
            products_here = df_pf[df_pf["Factory"] == factory]["Product Name"].tolist()
            product_html  = "<br>".join(f"• {p}" for p in products_here)
            popup_html = f"""
            <div style='font-family:Inter,sans-serif;min-width:200px'>
                <b style='font-size:14px'>{factory}</b><br>
                <span style='color:gray'>{info['city']}</span><br><br>
                <b>Products:</b><br>{product_html}
            </div>
            """
            folium.Marker(
                location=[info["lat"], info["lon"]],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=factory,
                icon=folium.Icon(color=color, icon="industry", prefix="fa"),
            ).add_to(m)

        st_folium(m, width=600, height=420)
        st.caption("📍 Click any pin to see which products are sourced from that factory.")

    with col2:
        st.markdown("##### Products & Factories Correlation")
        # Merge with profitability data
        pf_merged = df_pf.merge(
            product_summary[["Product Name","Avg_Gross_Margin","Total_Profit","Risk Flag"]],
            on="Product Name", how="left"
        )
        st.dataframe(
            pf_merged[["Division","Product Name","Factory","Avg_Gross_Margin","Risk Flag"]]
            .rename(columns={"Avg_Gross_Margin":"Avg Margin (%)"})
            .style.format({"Avg Margin (%)":"{:.1f}%"}),
            use_container_width=True, height=420,
        )

    # Factory profit summary
    st.markdown("##### Factory-Level Profitability Summary")
    factory_profit = (
        df_pf.merge(
            product_summary[["Product Name","Total_Sales","Total_Profit","Avg_Gross_Margin"]],
            on="Product Name", how="left"
        )
        .groupby("Factory")
        .agg(
            Products        =("Product Name", "count"),
            Total_Sales     =("Total_Sales",  "sum"),
            Total_Profit    =("Total_Profit", "sum"),
            Avg_Margin      =("Avg_Gross_Margin","mean"),
        )
        .reset_index()
        .sort_values("Total_Profit", ascending=False)
    )
    factory_profit["Profit Contribution %"] = factory_profit["Total_Profit"] / factory_profit["Total_Profit"].sum() * 100

    fig_fac = px.bar(
        factory_profit, x="Factory", y="Total_Profit",
        color="Avg_Margin",
        color_continuous_scale=["red","orange","green"],
        title="Gross Profit by Factory (color = Avg Margin %)",
        labels={"Total_Profit":"Total Profit ($)","Avg_Margin":"Avg Margin %"},
        template=CHART_TEMPLATE,
        text="Products",
    )
    st.plotly_chart(fig_fac, use_container_width=True)

    st.dataframe(
        factory_profit.rename(columns={
            "Total_Sales":"Total Sales ($)","Total_Profit":"Total Profit ($)",
            "Avg_Margin":"Avg Margin (%)","Products":"# Products",
        }).style.format({
            "Total Sales ($)":"${:,.0f}","Total Profit ($)":"${:,.0f}",
            "Avg Margin (%)":"{:.1f}%","Profit Contribution %":"{:.1f}%",
        }),
        use_container_width=True,
    )

# ──────────────────────────────────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Nassau Candy Distributor · Product Line Profitability & Margin Performance Dashboard · "
    "Built with Streamlit + Plotly + Folium"
)
