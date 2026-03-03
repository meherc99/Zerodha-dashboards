import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_fetcher import fetch_all_holdings
import datetime

# Configure page UI settings
st.set_page_config(
    page_title="Zerodha Family Dashboard",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
.metric-box {
    background-color: #f0f2f6; 
    border-radius: 10px; 
    padding: 20px; 
    text-align: center;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
}
.metric-title {
    font-size: 1.2rem;
    color: #666;
    margin-bottom: 5px;
}
.metric-value {
    font-size: 2rem;
    font-weight: bold;
    color: #1f1f1f;
}
.positive { color: #008000; }
.negative { color: #d00000; }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# DATA FETCHING LAYER (CACHED FOR 12 HOURS)
# We set ttl=12*60*60 (43,200 seconds) to ensure it auto-refreshes 
# pulls seamlessly from Zerodha exactly twice a day (every 12 hrs).
# ----------------------------------------------------------------------
@st.cache_data(ttl=43200)
def load_data():
    # Calling the proxy function which attempts Kite connections 
    # or falls back to realistic family stub data.
    return fetch_all_holdings()

st.title("💸 Zerodha Family Portfolio Dashboard")
st.markdown("Automated **12-hour pull** setup for all Kite accounts (Stocks & Mutual Funds).")

with st.spinner("Fetching latest portfolio data..."):
    df = load_data()

if df is None or df.empty:
    st.warning("No data returned! Ensure your API keys are configured correctly.")
    st.stop()


# ----------------------------------------------------------------------
# OVERVIEW METRICS
# ----------------------------------------------------------------------
total_invested = df["Invested Amount"].sum()
total_current = df["Current Value"].sum()
overall_pnl = total_current - total_invested
overall_pnl_pct = (overall_pnl / total_invested) * 100 if total_invested > 0 else 0

pnl_color = "positive" if overall_pnl >= 0 else "negative"
pnl_sign = "+" if overall_pnl >= 0 else ""

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"<div class='metric-box'><div class='metric-title'>Total Invested</div><div class='metric-value'>₹ {total_invested:,.2f}</div></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='metric-box'><div class='metric-title'>Current Value</div><div class='metric-value'>₹ {total_current:,.2f}</div></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='metric-box'><div class='metric-title'>Overall P&L</div><div class='metric-value {pnl_color}'>{pnl_sign} ₹ {overall_pnl:,.2f}</div></div>", unsafe_allow_html=True)
with col4:
    st.markdown(f"<div class='metric-box'><div class='metric-title'>Overall Return</div><div class='metric-value {pnl_color}'>{pnl_sign} {overall_pnl_pct:,.2f}%</div></div>", unsafe_allow_html=True)

st.markdown("---")

# ----------------------------------------------------------------------
# FILTERING / SIDEBAR
# ----------------------------------------------------------------------
st.sidebar.header("Dashboard Filters")
accounts = st.sidebar.multiselect("Select Family Member", options=df["Account"].unique(), default=df["Account"].unique())
instrument_types = st.sidebar.multiselect("Instrument Type (EQ/MF)", options=df["Type"].unique(), default=df["Type"].unique())
# Optional: filter out stocks you don't care to analyze today
search_symbol = st.sidebar.text_input("Search Symbol")

# Apply filters
filtered_df = df[(df["Account"].isin(accounts)) & (df["Type"].isin(instrument_types))]
if search_symbol:
    filtered_df = filtered_df[filtered_df["Symbol"].str.contains(search_symbol.upper())]

st.subheader(f"Analyzing {len(filtered_df)} Holdings")

# ----------------------------------------------------------------------
# VISUALIZATIONS FOR INVESTMENT DECISIONS
# ----------------------------------------------------------------------
if not filtered_df.empty:
    viz_col1, viz_col2 = st.columns(2)

    with viz_col1:
        # 1. Accounts Distribution Pie Chart
        st.markdown("#### Portfolio Split by Account")
        acct_dist = filtered_df.groupby("Account")["Current Value"].sum().reset_index()
        fig_pie = px.pie(acct_dist, values='Current Value', names='Account', hole=0.4, 
                         color_discrete_sequence=px.colors.sequential.Teal)
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)

        # 3. Top Gainers & Losers (Bar Chart)
        st.markdown("#### Performance: Top 5 Gainers vs Losers (%)")
        perf_df = filtered_df.sort_values(by="Total P&L %", ascending=False)
        top_5_gain = perf_df.head(5)
        top_5_loss = perf_df.tail(5)
        combo_df = pd.concat([top_5_gain, top_5_loss])
        
        fig_bar = px.bar(combo_df, x="Symbol", y="Total P&L %", 
                         color="Total P&L %", color_continuous_scale=["red", "green"],
                         color_continuous_midpoint=0)
        fig_bar.update_layout(margin=dict(t=30, b=0, l=0, r=0), coloraxis_showscale=False)
        st.plotly_chart(fig_bar, use_container_width=True)


    with viz_col2:
        # 2. Treemap of holdings (Size representing market value, Color representing PnL %)
        st.markdown("#### Heatmap: Asset Valuation & % Change")
        fig_tree = px.treemap(filtered_df, path=[px.Constant("All Family"), 'Account', 'Symbol'], 
                              values='Current Value',
                              color='Total P&L %', hover_data=['Invested Amount', 'Total P&L'],
                              color_continuous_scale='RdYlGn',
                              color_continuous_midpoint=0)
        fig_tree.update_layout(margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig_tree, use_container_width=True)
        
        # 4. Sunburst type breakdown (EQ vs MF)
        st.markdown("#### Asset Class vs Accounts")
        fig_sun = px.sunburst(filtered_df, path=['Type', 'Account', 'Symbol'], values='Current Value')
        fig_sun.update_layout(margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig_sun, use_container_width=True)


    # ----------------------------------------------------------------------
    # DETAILED HOLDINGS TABLE
    # ----------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📋 Let's Review: Detailed Holdings")
    
    # We round floats for a cleaner table view
    display_df = filtered_df.copy()
    numeric_cols = ["Avg Buy Price", "Last Price", "Invested Amount", "Current Value", "Total P&L", "Total P&L %"]
    for col in numeric_cols:
         display_df[col] = display_df[col].apply(lambda x: round(x, 2))
         
    # Streamlit dataframe natively supports robust sorting and searching 
    st.dataframe(
        display_df.style.map(lambda val: 'color: green' if val > 0 else 'color: red', subset=['Total P&L', 'Total P&L %']),
        use_container_width=True,
        hide_index=True 
    )

else:
    st.info("No holdings match the current filters.")

# Notice at the bottom
st.caption("Data is pulled using Zerodha Kite API. Refresh rate is set to 12 hours caching. The actual 'Buy Date' assumes available chronological history via Kite, otherwise a placeholder serves as UI mock. For perfect trade dates, manual parsing of Tradebook CSVs is typically required by Zerodha if it exceeds API's standard response scope.")
