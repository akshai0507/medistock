import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.express as px


# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="MediStock",
    page_icon="💊",
    layout="wide"
)

DATA_FILE = Path(__file__).parent / "medistock_cleaned_data.csv"


# ---------------- LOAD DATA ----------------
@st.cache_data
def load_data():
    data = pd.read_csv(DATA_FILE)

    data["date"] = pd.to_datetime(data["date"], errors="coerce")

    for col in ["medicine", "country", "category"]:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str).str.strip()

    for col in ["stock_level", "unit_price", "units_sold"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=["date", "medicine", "country"])
    data = data[data["medicine"] != ""]
    data = data[data["country"] != ""]

    return data


st.title("💊 MediStock")
st.write(
    "explore pharmacy sales trends."
)

try:
    df = load_data()
except FileNotFoundError:
    st.error(
        "Dataset not found. Upload medistock_cleaned_data.csv "
        "to the same GitHub repository as app.py."
    )
    st.stop()

if df.empty:
    st.error("The dataset contains no usable records.")
    st.stop()

countries = sorted(df["country"].unique())
medicines = sorted(df["medicine"].unique())

# ---------------- NAVIGATION ----------------
stock_tab, sales_tab = st.tabs(
    ["🔎 Medicine Stock Finder", "📊 Sales Dashboard"]
)


# =====================================================
# TAB 1: MEDICINE STOCK FINDER
# =====================================================
with stock_tab:
    st.header("Find a Medicine")

    st.write(
        "Choose a medicine and country to check the latest "
        "stock record available in the dataset."
    )

    col1, col2 = st.columns(2)

    with col1:
        selected_medicine = st.selectbox(
            "Choose medicine",
            medicines,
            key="stock_medicine"
        )

    with col2:
        selected_country = st.selectbox(
            "Choose country",
            countries,
            key="stock_country"
        )

    medicine_records = df[
        (df["medicine"] == selected_medicine)
        & (df["country"] == selected_country)
    ].copy()

    if medicine_records.empty:
        st.warning("No records found for this selection.")
    else:
        medicine_records = medicine_records.sort_values("date")
        latest = medicine_records.iloc[-1]

        st.subheader(f"Results for {selected_medicine}")

        c1, c2, c3 = st.columns(3)

        stock = latest.get("stock_level")
        price = latest.get("unit_price")

        c1.metric(
            "Recorded stock",
            f"{stock:,.0f}" if pd.notna(stock) else "Not available"
        )

        c2.metric(
            "Recorded unit price",
            f"{price:,.2f}" if pd.notna(price) else "Not available"
        )

        c3.metric(
            "Record date",
            latest["date"].strftime("%d %b %Y")
        )

        st.caption(
            "Stock and price are sample dataset values. "
            "Currency is unspecified, and live availability "
            "has not been verified."
        )

        st.subheader("Recent records")

        recent = medicine_records.sort_values(
            "date", ascending=False
        ).head(10)

        columns = [
            c for c in [
                "date", "medicine", "country", "category",
                "stock_level", "unit_price", "units_sold"
            ] if c in recent.columns
        ]

        st.dataframe(
            recent[columns],
            use_container_width=True,
            hide_index=True
        )



    
# =====================================================
# POWER BI-STYLE SALES DASHBOARD
# =====================================================
with sales_tab:
    st.header("📊 MediStock | Sales Analytics")
    st.caption("Interactive sales reporting and medicine performance")

    sales = df.dropna(subset=["date", "units_sold"]).copy()

    sales["year"] = sales["date"].dt.year
    sales["month"] = sales["date"].dt.month
    sales["revenue_estimate"] = (
        sales["units_sold"] * sales["unit_price"].fillna(0)
    )

    month_names = {
        1: "January", 2: "February", 3: "March",
        4: "April", 5: "May", 6: "June",
        7: "July", 8: "August", 9: "September",
        10: "October", 11: "November", 12: "December"
    }

    # ---------------- SIDEBAR FILTERS ----------------
    st.sidebar.header("Dashboard Filters")

    country_options = ["All countries"] + sorted(
        sales["country"].dropna().unique().tolist()
    )

    selected_country = st.sidebar.selectbox(
        "Select country", country_options
    )

    years = sorted(
        sales["year"].dropna().unique().astype(int).tolist(),
        reverse=True
    )

    selected_year = st.sidebar.selectbox("Select year", years)

    months = sorted(
        sales.loc[sales["year"] == selected_year, "month"]
        .dropna().unique().astype(int).tolist()
    )

    selected_month = st.sidebar.selectbox(
        "Select month",
        months,
        format_func=lambda x: month_names[x]
    )

    # ---------------- FILTER DATA ----------------
    year_data = sales[sales["year"] == selected_year].copy()

    if selected_country != "All countries":
        year_data = year_data[
            year_data["country"] == selected_country
        ]

    month_data = year_data[
        year_data["month"] == selected_month
    ].copy()

    if month_data.empty:
        st.warning("No sales data is available for these filters.")
        st.stop()

    # ---------------- KPI CARDS ----------------
    total_units = month_data["units_sold"].sum()
    estimated_revenue = month_data["revenue_estimate"].sum()
    medicine_count = month_data["medicine"].nunique()

    medicine_sales = (
        month_data.groupby("medicine", as_index=False)
        ["units_sold"].sum()
        .sort_values("units_sold", ascending=False)
    )

    top_medicine = medicine_sales.iloc[0]["medicine"]
    top_units = medicine_sales.iloc[0]["units_sold"]

    k1, k2, k3, k4 = st.columns(4)

    k1.metric("Total Units Sold", f"{total_units:,.0f}")
    k2.metric("Estimated Sales Value", f"{estimated_revenue:,.2f}")
    k3.metric("Medicines Sold", f"{medicine_count:,}")
    k4.metric("Top Medicine", str(top_medicine))

    st.caption(
        f"Reporting period: {month_names[selected_month]} "
        f"{selected_year} | Top medicine units: {top_units:,.0f}. "
        "Sales value is units sold × unit price; currency is unspecified."
    )

    st.divider()

    # ---------------- MONTHLY SALES TREND ----------------
    st.subheader("📈 Monthly Sales Trend")

    if year_data.empty:
        st.info("No records available for this year.")
    else:
        monthly_trend = (
            year_data.groupby("month", as_index=False)
            .agg(
                units_sold=("units_sold", "sum"),
                sales_value=("revenue_estimate", "sum")
            )
        )

        monthly_trend["Month"] = monthly_trend["month"].map(month_names)

        fig_trend = px.line(
            monthly_trend,
            x="Month",
            y="units_sold",
            markers=True,
            title=f"Monthly Units Sold — {selected_year}",
            labels={
                "Month": "Month",
                "units_sold": "Units Sold"
            },
            template="plotly_white"
        )

        fig_trend.update_traces(line=dict(width=3))
        fig_trend.update_layout(
            height=380,
            xaxis_title="Month",
            yaxis_title="Units Sold"
        )

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
            title="Best-Selling Medicines",
            labels={
                "units_sold": "Units Sold",
                "medicine": "Medicine"
            },
            template="plotly_white"
        )

        fig_top.update_traces(texttemplate="%{text:,.0f}")
        fig_top.update_layout(height=420, yaxis_title="")
        st.plotly_chart(fig_top, use_container_width=True)

    # ---------------- CATEGORY SHARE ----------------
    with right:
        st.subheader("🍩 Sales by Category")

        if "category" in month_data.columns:
            category_data = (
                month_data.groupby("category", as_index=False)
                ["units_sold"].sum()
                .sort_values("units_sold", ascending=False)
            )

            category_data = category_data[
                category_data["category"].astype(str).str.strip() != ""
            ]

            if not category_data.empty:
                fig_category = px.pie(
                    category_data,
                    names="category",
                    values="units_sold",
                    hole=0.55,
                    title="Share of Units Sold",
                    template="plotly_white"
                )

                fig_category.update_layout(height=420)
                st.plotly_chart(
                    fig_category, use_container_width=True
                )
            else:
                st.info("No category data available.")
        else:
            st.info("The dataset has no category column.")

    
# ---------------- COUNTRY SALES COMPARISON ----------------
st.divider()
st.subheader("🌍 Country Sales Comparison")

# Use the selected year and month
country_data = sales[
    (sales["year"] == selected_year) &
    (sales["month"] == selected_month)
].copy()

# If a specific country is selected, filter to that country
if selected_country != "All countries":
    country_data = country_data[
        country_data["country"] == selected_country
    ]

if country_data.empty:
    st.warning("No sales data for the selected country and month.")
else:
    country_summary = (
        country_data.groupby("country", as_index=False)
        .agg(units_sold=("units_sold", "sum"))
        .sort_values("units_sold", ascending=False)
    )

    fig_country = px.bar(
        country_summary,
        x="country",
        y="units_sold",
        color="country",
        title=(
            f"Sales by Country — {month_names[selected_month]} "
            f"{selected_year}"
        ),
        labels={
            "country": "Country",
            "units_sold": "Units Sold"
        },
        template="plotly_white"
    )

    fig_country.update_layout(
        height=400,
        showlegend=False
    )

    st.plotly_chart(fig_country, use_container_width=True)


    # ---------------- DETAIL TABLE ----------------
    st.subheader("📋 Monthly Sales Details")

    detail = medicine_sales.copy()
    detail.columns = ["Medicine", "Units Sold"]

    st.dataframe(
        detail,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "⬇️ Download Sales Report",
        data=detail.to_csv(index=False).encode("utf-8"),
        file_name=f"medistock_sales_{selected_year}_{selected_month:02d}.csv",
        mime="text/csv"
    )
