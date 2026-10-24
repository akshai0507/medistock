
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="MediStock",
    page_icon="💊",
    layout="wide"
)

DATA_FILE = Path(__file__).parent / "medistock_cleaned_data.csv"

MONTH_NAMES = {
    1: "January", 2: "February", 3: "March",
    4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September",
    10: "October", 11: "November", 12: "December"
}


# ---------------- LOAD DATA ----------------
@st.cache_data
def load_data():
    data = pd.read_csv(DATA_FILE)

    required = [
        "date", "medicine", "country", "units_sold",
        "stock_level", "unit_price"
    ]
    missing = [col for col in required if col not in data.columns]

    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing)
        )

    data["date"] = pd.to_datetime(data["date"], errors="coerce")

    for col in ["medicine", "country", "category"]:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str).str.strip()

    for col in ["stock_level", "unit_price", "units_sold"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=["date", "medicine", "country"])
    data = data[
        (data["medicine"] != "") &
        (data["country"] != "")
    ].copy()

    return data


st.title("💊 MediStock")
st.write("Medicine stock search and interactive sales analytics.")

try:
    df = load_data()
except FileNotFoundError:
    st.error(
        "Dataset not found. Upload medistock_cleaned_data.csv "
        "to the same GitHub repository as app.py."
    )
    st.stop()
except ValueError as error:
    st.error(str(error))
    st.stop()

if df.empty:
    st.error("The dataset contains no usable records.")
    st.stop()

countries = sorted(df["country"].unique())
medicines = sorted(df["medicine"].unique())

stock_tab, sales_tab = st.tabs([
    "🔎 Medicine Stock Finder",
    "📊 Sales Dashboard"
])


# =====================================================
# TAB 1: MEDICINE STOCK FINDER
# =====================================================
with stock_tab:
    st.header("Find a Medicine")

    col1, col2 = st.columns(2)

    with col1:
        selected_medicine = st.selectbox(
            "Choose medicine",
            medicines,
            key="stock_medicine"
        )

    with col2:
        selected_stock_country = st.selectbox(
            "Choose country",
            countries,
            key="stock_country"
        )

    records = df[
        (df["medicine"] == selected_medicine) &
        (df["country"] == selected_stock_country)
    ].copy()

    if records.empty:
        st.warning("No records found.")
    else:
        records = records.sort_values("date")
        latest = records.iloc[-1]

        st.subheader(f"Results for {selected_medicine}")

        c1, c2, c3 = st.columns(3)

        stock = latest["stock_level"]
        price = latest["unit_price"]

        c1.metric(
            "Recorded stock",
            f"{stock:,.0f}" if pd.notna(stock) else "Not available"
        )
        c2.metric(
            "Recorded unit price",
            f"{price:,.2f}" if pd.notna(price) else "Not available"
        )
        c3.metric("Record date", latest["date"].strftime("%d %b %Y"))

        st.caption(
            "Sample dataset values only. Currency is unspecified; "
            "live pharmacy stock has not been verified."
        )

        st.subheader("Recent records")

        display_cols = [
            col for col in [
                "date", "medicine", "country", "category",
                "stock_level", "unit_price", "units_sold"
            ] if col in records.columns
        ]

        st.dataframe(
            records.sort_values("date", ascending=False)
            [display_cols].head(10),
            use_container_width=True,
            hide_index=True
        )


# =====================================================
# TAB 2: POWER BI-STYLE SALES DASHBOARD
# =====================================================
with sales_tab:
    st.header("📊 MediStock Sales Analytics")
    st.caption("Filter the dashboard by country, year, and month.")

    sales = df.dropna(subset=["date", "units_sold"]).copy()
    sales["year"] = sales["date"].dt.year.astype(int)
    sales["month"] = sales["date"].dt.month.astype(int)

    # Revenue is an estimate; the currency is not supplied.
    sales["revenue_estimate"] = (
        sales["units_sold"] * sales["unit_price"].fillna(0)
    )

    # ---------------- FILTERS ----------------
    st.sidebar.header("Dashboard Filters")

    country_options = ["All countries"] + sorted(
        sales["country"].unique().tolist()
    )

    selected_country = st.sidebar.selectbox(
        "Select country",
        country_options,
        key="dashboard_country"
    )

    years = sorted(sales["year"].unique().tolist(), reverse=True)

    selected_year = st.sidebar.selectbox(
        "Select year", years, key="dashboard_year"
    )

    available_months = sorted(
        sales.loc[sales["year"] == selected_year, "month"]
        .unique().tolist()
    )

    selected_month = st.sidebar.selectbox(
        "Select month",
        available_months,
        format_func=lambda month: MONTH_NAMES[month],
        key="dashboard_month"
    )

    # ---------------- CONSISTENT FILTERING ----------------
    filtered_year = sales[sales["year"] == selected_year].copy()

    if selected_country != "All countries":
        filtered_year = filtered_year[
            filtered_year["country"] == selected_country
        ]

    filtered_month = filtered_year[
        filtered_year["month"] == selected_month
    ].copy()

    if filtered_month.empty:
        st.warning("No sales data is available for these filters.")
        st.stop()

    # ---------------- KPI CARDS ----------------
    medicine_sales = (
        filtered_month.groupby("medicine", as_index=False)
        .agg(units_sold=("units_sold", "sum"))
        .sort_values("units_sold", ascending=False)
    )

    total_units = filtered_month["units_sold"].sum()
    estimated_revenue = filtered_month["revenue_estimate"].sum()
    medicine_count = filtered_month["medicine"].nunique()

    top_medicine = medicine_sales.iloc[0]["medicine"]
    top_units = medicine_sales.iloc[0]["units_sold"]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Units Sold", f"{total_units:,.0f}")
    k2.metric("Estimated Sales Value", f"{estimated_revenue:,.2f}")
    k3.metric("Medicines Recorded", f"{medicine_count:,}")
    k4.metric("Top-Selling Medicine", str(top_medicine))

    country_label = (
        selected_country
        if selected_country != "All countries"
        else "All countries"
    )

    st.caption(
        f"Country: {country_label} | "
        f"Period: {MONTH_NAMES[selected_month]} {selected_year} | "
        f"Top medicine units: {top_units:,.0f}"
    )

    st.divider()

    # ---------------- MONTHLY TREND ----------------
    st.subheader("📈 Monthly Sales Trend")

    monthly_trend = (
        filtered_year.groupby("month", as_index=False)
        .agg(
            units_sold=("units_sold", "sum"),
            sales_value=("revenue_estimate", "sum")
        )
    )

    monthly_trend["Month"] = monthly_trend["month"].map(MONTH_NAMES)
    monthly_trend["Month"] = pd.Categorical(
        monthly_trend["Month"],
        categories=list(MONTH_NAMES.values()),
        ordered=True
    )
    monthly_trend = monthly_trend.sort_values("Month")

    fig_trend = px.line(
        monthly_trend,
        x="Month",
        y="units_sold",
        markers=True,
        title=f"Monthly Units Sold — {selected_year}",
        labels={"Month": "Month", "units_sold": "Units Sold"},
        template="plotly_white"
    )
    fig_trend.update_layout(height=380)
    st.plotly_chart(fig_trend, use_container_width=True)

    # ---------------- TOP MEDICINES ----------------
    left, right = st.columns(2)

    with left:
        st.subheader("🏆 Top 10 Medicines")

        top10 = medicine_sales.head(10).sort_values("units_sold")

        fig_top = px.bar(
            top10,
            x="units_sold",
            y="medicine",
            orientation="h",
            text="units_sold",
            title=f"Best Sellers — {MONTH_NAMES[selected_month]}",
            labels={"units_sold": "Units Sold", "medicine": "Medicine"},
            template="plotly_white"
        )
        fig_top.update_traces(texttemplate="%{text:,.0f}")
        fig_top.update_layout(height=430, yaxis_title="")
        st.plotly_chart(fig_top, use_container_width=True)

    # ---------------- CATEGORY ANALYSIS ----------------
    with right:
        st.subheader("🍩 Sales by Category")

        if "category" in filtered_month.columns:
            category_data = (
                filtered_month.groupby("category", as_index=False)
                .agg(units_sold=("units_sold", "sum"))
            )
            category_data = category_data[
                category_data["category"].str.strip() != ""
            ].sort_values("units_sold", ascending=False)

            if not category_data.empty:
                fig_category = px.pie(
                    category_data,
                    names="category",
                    values="units_sold",
                    hole=0.55,
                    title="Share of Units Sold",
                    template="plotly_white"
                )
                fig_category.update_layout(height=430)
                st.plotly_chart(
                    fig_category, use_container_width=True
                )
            else:
                st.info("No category data is available.")
        else:
            st.info("The dataset has no category column.")

    # ---------------- COUNTRY COMPARISON ----------------
    st.divider()

    if selected_country == "All countries":
        st.subheader("🌍 Country Sales Comparison")

        country_data = (
            filtered_month.groupby("country", as_index=False)
            .agg(units_sold=("units_sold", "sum"))
            .sort_values("units_sold", ascending=True)
            .tail(10)
        )

        fig_country = px.bar(
            country_data,
            x="units_sold",
            y="country",
            orientation="h",
            text="units_sold",
            title=(
                f"Top Countries — {MONTH_NAMES[selected_month]} "
                f"{selected_year}"
            ),
            labels={"units_sold": "Units Sold", "country": "Country"},
            template="plotly_white"
        )
        fig_country.update_layout(height=420)
        st.plotly_chart(fig_country, use_container_width=True)

    else:
        st.subheader(f"📦 {selected_country}: Monthly Medicine Sales")

        country_medicines = (
            filtered_month.groupby("medicine", as_index=False)
            .agg(units_sold=("units_sold", "sum"))
            .sort_values("units_sold", ascending=False)
            .head(10)
            .sort_values("units_sold", ascending=True)
        )

        fig_country = px.bar(
            country_medicines,
            x="units_sold",
            y="medicine",
            orientation="h",
            text="units_sold",
            title=(
                f"Top Medicines in {selected_country} — "
                f"{MONTH_NAMES[selected_month]} {selected_year}"
            ),
            labels={"units_sold": "Units Sold", "medicine": "Medicine"},
            template="plotly_white"
        )
        fig_country.update_layout(height=420)
        st.plotly_chart(fig_country, use_container_width=True)

    # ---------------- SALES DETAILS & DOWNLOAD ----------------
    st.subheader("📋 Monthly Sales Details")

    detail = medicine_sales.copy()
    detail.columns = ["Medicine", "Units Sold"]

    st.dataframe(detail, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇️ Download Monthly Sales Report",
        data=detail.to_csv(index=False).encode("utf-8"),
        file_name=(
            f"medistock_sales_{selected_year}_"
            f"{selected_month:02d}.csv"
        ),
        mime="text/csv"
    )

    st.caption(
        "MediStock prototype | Sales are based on the supplied dataset. "
        "Stock is not connected to live pharmacies."
    )

