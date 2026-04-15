"""
13_Analytics.py — Business Intelligence Dashboard
Satyam Tex Fabb CRM

Charts:
1. Monthly Sales Value (bar) — which months are peak
2. Top Products by Volume (bar) — what sells most
3. Top Customers by Value (bar) — who spends most
4. Customer × Product heatmap (table) — who orders what
5. Communication preference (pie) — email vs WhatsApp response rates from email_log
6. Category-wise sales breakdown (bar)
"""

from datetime import date

import pandas as pd
import streamlit as st

from utils.auth import require_login
from utils.supabase_db import fetch_table
from utils.ui import init_page

require_login()
init_page("Analytics")

st.title("📊 Business Intelligence")
st.caption("Live charts from your actual data. Generate any time.")

# ── Load data ────────────────────────────────────────────────────────────────
sales_raw = fetch_table("sales_records")
customers_raw = fetch_table("customers")
email_log_raw = fetch_table("email_log")
parts_raw = fetch_table("parts")

if not sales_raw:
    st.info("No sales data yet. Add sales records to see analytics.")
    st.stop()

# ── Build sales DataFrame ────────────────────────────────────────────────────
sales = pd.DataFrame(sales_raw)

# Normalise column names (Supabase returns snake_case)
sales.columns = [c.lower() for c in sales.columns]

def to_float(v):
    try:
        return float(str(v or "0").strip())
    except (TypeError, ValueError):
        return 0.0

def to_int(v):
    try:
        return int(float(str(v or "0").strip()))
    except (TypeError, ValueError):
        return 0

sales["total_sale_value"] = sales.get("total_sale_value", pd.Series(dtype=float)).apply(to_float)
sales["quantity_sold"] = sales.get("quantity_sold", pd.Series(dtype=int)).apply(to_int)

if "date" in sales.columns:
    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    sales = sales[sales["date"].notna()]
    sales["month"] = sales["date"].dt.to_period("M").astype(str)
    sales["month_dt"] = sales["date"].dt.to_period("M")

# ── Date range filter ────────────────────────────────────────────────────────
st.markdown("### 🗓️ Filter Period")
col1, col2 = st.columns(2)
min_date = sales["date"].min().date() if not sales.empty else date.today()
max_date = sales["date"].max().date() if not sales.empty else date.today()
with col1:
    start = st.date_input("From", value=min_date, key="analytics_start")
with col2:
    end = st.date_input("To", value=max_date, key="analytics_end")

mask = (sales["date"].dt.date >= start) & (sales["date"].dt.date <= end)
df = sales[mask].copy()

if df.empty:
    st.warning("No sales in the selected date range.")
    st.stop()

st.markdown("---")

# ── Summary KPIs ─────────────────────────────────────────────────────────────
total_revenue = df["total_sale_value"].sum()
total_units = df["quantity_sold"].sum()
unique_customers = df["party_name"].nunique() if "party_name" in df.columns else 0
unique_products = df["part_name"].nunique() if "part_name" in df.columns else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("💰 Total Revenue", f"Rs {total_revenue:,.0f}")
k2.metric("📦 Units Sold", f"{total_units:,}")
k3.metric("👥 Unique Customers", unique_customers)
k4.metric("🔩 Unique Products", unique_products)

st.markdown("---")

# ── Chart 1: Monthly Sales Value ─────────────────────────────────────────────
st.markdown("### 📅 Monthly Sales Revenue")
st.caption("Which months are your peak sales periods")

monthly = (
    df.groupby("month")["total_sale_value"]
    .sum()
    .reset_index()
    .sort_values("month")
)
monthly.columns = ["Month", "Revenue (Rs)"]

if not monthly.empty:
    st.bar_chart(monthly.set_index("Month")["Revenue (Rs)"])
    with st.expander("View monthly data table"):
        monthly["Revenue (Rs)"] = monthly["Revenue (Rs)"].apply(lambda x: f"Rs {x:,.2f}")
        st.dataframe(monthly, use_container_width=True, hide_index=True)

st.markdown("---")

# ── Chart 2: Top Products by Revenue ─────────────────────────────────────────
st.markdown("### 🔩 Top Products by Revenue")
st.caption("Which parts generate the most income")

col_left, col_right = st.columns(2)

with col_left:
    if "part_name" in df.columns:
        top_n = st.slider("Show top N products", min_value=5, max_value=30, value=10, key="top_products_n")
        top_products_rev = (
            df.groupby("part_name")["total_sale_value"]
            .sum()
            .sort_values(ascending=False)
            .head(top_n)
            .reset_index()
        )
        top_products_rev.columns = ["Part Name", "Revenue (Rs)"]
        st.bar_chart(top_products_rev.set_index("Part Name"))

with col_right:
    if "part_name" in df.columns:
        st.markdown("**By Units Sold**")
        top_products_qty = (
            df.groupby("part_name")["quantity_sold"]
            .sum()
            .sort_values(ascending=False)
            .head(top_n)
            .reset_index()
        )
        top_products_qty.columns = ["Part Name", "Units Sold"]
        st.bar_chart(top_products_qty.set_index("Part Name"))

st.markdown("---")

# ── Chart 3: Top Customers by Value ──────────────────────────────────────────
st.markdown("### 👥 Top Customers by Spend")
st.caption("Who spends the most with you")

if "party_name" in df.columns:
    top_cust_n = st.slider("Show top N customers", min_value=5, max_value=20, value=10, key="top_cust_n")
    top_customers = (
        df.groupby("party_name")["total_sale_value"]
        .sum()
        .sort_values(ascending=False)
        .head(top_cust_n)
        .reset_index()
    )
    top_customers.columns = ["Customer", "Total Spend (Rs)"]

    c1, c2 = st.columns([2, 1])
    with c1:
        st.bar_chart(top_customers.set_index("Customer"))
    with c2:
        top_customers["Total Spend (Rs)"] = top_customers["Total Spend (Rs)"].apply(lambda x: f"Rs {x:,.2f}")
        st.dataframe(top_customers, use_container_width=True, hide_index=True)

st.markdown("---")

# ── Chart 4: Customer × Product Matrix ───────────────────────────────────────
st.markdown("### 🔥 Customer × Product Preference Matrix")
st.caption("Which customers buy which products — spot loyalty patterns and cross-sell opportunities")

if "party_name" in df.columns and "part_name" in df.columns:
    matrix_metric = st.radio(
        "Show by",
        options=["Revenue", "Units Sold"],
        horizontal=True,
        key="matrix_metric",
    )

    value_col = "total_sale_value" if matrix_metric == "Revenue" else "quantity_sold"

    # Limit to top customers and top products to keep it readable
    top_c = df.groupby("party_name")[value_col].sum().nlargest(15).index.tolist()
    top_p = df.groupby("part_name")[value_col].sum().nlargest(15).index.tolist()

    matrix_df = df[df["party_name"].isin(top_c) & df["part_name"].isin(top_p)]
    pivot = matrix_df.pivot_table(
        index="party_name",
        columns="part_name",
        values=value_col,
        aggfunc="sum",
        fill_value=0,
    )

    if not pivot.empty:
        st.caption(f"Showing top 15 customers × top 15 products. {'Revenue in Rs.' if matrix_metric == 'Revenue' else 'Units sold.'}")
        st.dataframe(
            pivot,
            use_container_width=True,
        )
        st.caption("🔴 Dark = high value. Empty cell = customer never bought that product → cross-sell opportunity.")
    else:
        st.info("Not enough data to build the matrix yet.")

st.markdown("---")

# ── Chart 5: Category-wise Sales ─────────────────────────────────────────────
st.markdown("### 📦 Sales by Category")
st.caption("Which product categories drive your business")

if "category" in df.columns:
    cat_sales = (
        df.groupby("category")["total_sale_value"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    cat_sales.columns = ["Category", "Revenue (Rs)"]
    cat_sales = cat_sales[cat_sales["Category"].str.strip().astype(bool)]

    if not cat_sales.empty:
        st.bar_chart(cat_sales.set_index("Category"))

st.markdown("---")

# ── Chart 6: Communication Preference ────────────────────────────────────────
st.markdown("### 📬 Communication Channel Analysis")
st.caption("Email vs WhatsApp — where are customers more responsive")

if email_log_raw:
    email_log = pd.DataFrame(email_log_raw)
    email_log.columns = [c.lower() for c in email_log.columns]

    if "email_type" in email_log.columns and "status" in email_log.columns:
        sent = email_log[email_log["status"].str.lower() == "sent"]
        email_count = len(sent[sent["email_type"].str.lower() != "whatsapp"]) if not sent.empty else len(sent)
        whatsapp_count = len(sent[sent["email_type"].str.lower() == "whatsapp"]) if "email_type" in sent.columns else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("📧 Emails Sent", email_count)
        c2.metric("📱 WhatsApp Sent", whatsapp_count)
        total_comm = email_count + whatsapp_count
        if total_comm > 0:
            c3.metric("📧 Email Share", f"{email_count/total_comm*100:.0f}%")

        # Breakdown by email type
        if "email_type" in email_log.columns:
            type_counts = (
                email_log[email_log["status"].str.lower() == "sent"]
                .groupby("email_type")
                .size()
                .reset_index()
            )
            type_counts.columns = ["Communication Type", "Count"]
            if not type_counts.empty:
                st.bar_chart(type_counts.set_index("Communication Type"))

        # Per-customer communication log
        if "recipient_name" in email_log.columns:
            st.markdown("**Per-customer communication history**")
            cust_comm = (
                email_log.groupby(["recipient_name", "email_type"])
                .size()
                .reset_index()
            )
            cust_comm.columns = ["Customer", "Channel", "Messages Sent"]
            st.dataframe(cust_comm, use_container_width=True, hide_index=True)
else:
    st.info("No communication logs yet. Send payment reminders or promotional emails to start tracking.")

st.markdown("---")

# ── Chart 7: Sales Trend — 30-day rolling ────────────────────────────────────
st.markdown("### 📈 Sales Trend (Daily)")
st.caption("Day-by-day revenue to spot busy and slow periods")

daily = (
    df.groupby(df["date"].dt.date)["total_sale_value"]
    .sum()
    .reset_index()
)
daily.columns = ["Date", "Daily Revenue (Rs)"]
daily = daily.sort_values("Date")

if not daily.empty:
    st.line_chart(daily.set_index("Date"))

st.markdown("---")
st.caption("All charts update live from your Supabase data. Use the date filter at the top to change the analysis period.")
