import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Executive E-Commerce BI Dashboard",
    page_icon="📊",
    layout="wide",
)


@st.cache_data
def load_data(path: str = "data/Ecommerce_Sales_Data_2024_2025.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Order Date"] = pd.to_datetime(
        df["Order Date"], format="%d-%m-%y", errors="coerce"
    )
    df = df.dropna(subset=["Order Date"]).copy()
    df["Year"] = df["Order Date"].dt.year
    df["Month"] = df["Order Date"].dt.to_period("M").astype(str)
    df["Profit Margin %"] = np.where(
        df["Sales"] > 0, (df["Profit"] / df["Sales"]) * 100, 0.0
    )
    return df


df = load_data()

st.title("📊 Executive E-Commerce BI Dashboard (2023–2025)")
st.caption(
    "Interactive sales & profitability overview across regions, categories, and payment modes."
)

# --- Sidebar Filters (3 Filters) ---
st.sidebar.header("🔎 Filters")

regions = sorted(df["Region"].dropna().unique().tolist())
selected_regions = st.sidebar.multiselect(
    "Region", options=regions, default=regions
)

categories = sorted(df["Category"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect(
    "Category", options=categories, default=categories
)

payment_modes = sorted(df["Payment Mode"].dropna().unique().tolist())
selected_payments = st.sidebar.multiselect(
    "Payment Mode", options=payment_modes, default=payment_modes
)

filtered_df = df[
    df["Region"].isin(selected_regions)
    & df["Category"].isin(selected_categories)
    & df["Payment Mode"].isin(selected_payments)
].copy()

# --- Empty-State Handling ---
if filtered_df.empty:
    st.warning(
        "⚠️ No records match the current filter selection. Please select at least one option in Region, Category, and Payment Mode."
    )
    st.stop()

# --- KPI Metric Cards (4 KPIs) ---
total_sales = filtered_df["Sales"].sum()
total_profit = filtered_df["Profit"].sum()
total_orders = filtered_df["Order ID"].nunique()
aov = total_sales / total_orders if total_orders > 0 else 0.0
profit_margin = (total_profit / total_sales * 100) if total_sales > 0 else 0.0

avg_order_sales = df["Sales"].mean()
avg_order_profit = df["Profit"].mean()
delta_aov = aov - avg_order_sales
delta_profit_per_order = (
    (total_profit / total_orders - avg_order_profit) if total_orders > 0 else 0.0
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Sales", f"${total_sales:,.0f}", delta=f"{profit_margin:.1f}% margin")
c2.metric(
    "Total Profit",
    f"${total_profit:,.0f}",
    delta=f"${delta_profit_per_order:,.0f} vs avg/order",
)
c3.metric("Total Orders", f"{total_orders:,}")
c4.metric(
    "Avg. Order Value", f"${aov:,.0f}", delta=f"${delta_aov:,.0f} vs dataset avg"
)

st.divider()

# --- Automated Insight Callout ---
monthly_sales = (
    filtered_df.groupby("Month", as_index=False)["Sales"]
    .sum()
    .sort_values("Month")
)
top_month_row = monthly_sales.loc[monthly_sales["Sales"].idxmax()]

category_perf = (
    filtered_df.groupby("Category", as_index=False)[["Sales", "Profit"]]
    .sum()
    .sort_values("Sales", ascending=False)
)
top_cat_row = category_perf.iloc[0]

high_disc = filtered_df[filtered_df["Discount"] >= 15]["Profit"].mean()
low_disc = filtered_df[filtered_df["Discount"] <= 5]["Profit"].mean()

discount_note = ""
if pd.notna(high_disc) and pd.notna(low_disc) and low_disc > 0:
    pct_diff = ((high_disc - low_disc) / low_disc) * 100
    discount_note = (
        f" Average profit per order at **15–20% discount** is **${high_disc:,.0f}** "
        f"vs. **${low_disc:,.0f}** at **0–5% discount** ({pct_diff:+.1f}%)."
    )

st.info(
    f"💡 **Automated Key Insight:** Top-performing category is **{top_cat_row['Category']}** "
    f"with **${top_cat_row['Sales']:,.0f}** in sales, while peak monthly revenue occurred in "
    f"**{top_month_row['Month']}** (**${top_month_row['Sales']:,.0f}**).{discount_note}"
)

# --- Visual 1: Monthly Trend ---
st.subheader("📈 Monthly Sales & Profit Trend")
monthly_agg = (
    filtered_df.groupby("Month", as_index=False)[["Sales", "Profit"]]
    .sum()
    .sort_values("Month")
)
monthly_melted = monthly_agg.melt(
    id_vars="Month",
    value_vars=["Sales", "Profit"],
    var_name="Metric",
    value_name="Amount",
)
fig_trend = px.line(
    monthly_melted,
    x="Month",
    y="Amount",
    color="Metric",
    markers=True,
    title="Monthly Revenue & Profit Over Time",
    labels={"Amount": "Amount ($)", "Month": "Month"},
)
fig_trend.update_layout(hovermode="x unified", xaxis_tickangle=-45)
st.plotly_chart(fig_trend, use_container_width=True)

# --- Visual 2 & Visual 3: Comparison + Relationship/Drilldown ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🏆 Category Comparison")
    metric_choice = st.radio(
        "Compare categories by:",
        options=["Sales", "Profit"],
        horizontal=True,
        key="cat_metric_choice",
    )
    cat_sorted = category_perf.sort_values(metric_choice, ascending=True)
    fig_comp = px.bar(
        cat_sorted,
        x=metric_choice,
        y="Category",
        orientation="h",
        title=f"Total {metric_choice} by Category",
        labels={metric_choice: f"Total {metric_choice} ($)", "Category": "Category"},
        color=metric_choice,
        color_continuous_scale="Blues",
    )
    fig_comp.update_layout(showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig_comp, use_container_width=True)

with col_right:
    st.subheader("🔎 Discount vs. Profit Relationship")
    sample_df = (
        filtered_df.sample(n=min(1500, len(filtered_df)), random_state=42)
        if len(filtered_df) > 1500
        else filtered_df
    )
    fig_rel = px.scatter(
        sample_df,
        x="Discount",
        y="Profit",
        color="Category",
        size="Quantity",
        hover_data=["Sub-Category", "Sales", "Region"],
        title="Order Profit vs. Discount Rate (Bubble Size = Quantity)",
        labels={"Discount": "Discount (%)", "Profit": "Profit ($)"},
    )
    st.plotly_chart(fig_rel, use_container_width=True)

# --- Drilldown Preview + Filtered CSV Download ---
st.divider()
st.subheader("📋 Filtered Records & Export")

csv_data = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Download Filtered Data (CSV)",
    data=csv_data,
    file_name="filtered_ecommerce_sales.csv",
    mime="text/csv",
)

display_cols = [
    "Order ID",
    "Order Date",
    "Region",
    "City",
    "Category",
    "Sub-Category",
    "Product Name",
    "Quantity",
    "Discount",
    "Sales",
    "Profit",
    "Payment Mode",
]
st.dataframe(
    filtered_df[display_cols].sort_values("Order Date", ascending=False),
    use_container_width=True,
    hide_index=True,
)