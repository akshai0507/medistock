import streamlit as st
import pandas as pd
from pathlib import Path

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
# TAB 2: SALES DASHBOARD
# =====================================================
with sales_tab:
    st.header("📊 Medicine Sales Dashboard")

    st.write(
        "Find the best-selling medicines for a selected "
        "country and month."
    )

    dated_data = df.dropna(subset=["date"]).copy()

    if dated_data.empty:
        st.warning("No valid dates are available for sales analysis.")
    else:
        dated_data["year"] = dated_data["date"].dt.year
        dated_data["month"] = dated_data["date"].dt.month

        available_years = sorted(
            dated_data["year"].unique().tolist(),
            reverse=True
        )

        month_names = {
            1: "January", 2: "February", 3: "March",
            4: "April", 5: "May", 6: "June",
            7: "July", 8: "August", 9: "September",
            10: "October", 11: "November", 12: "December"
        }

        filter1, filter2, filter3 = st.columns(3)

        with filter1:
            dashboard_country = st.selectbox(
                "Country",
                ["All countries"] + countries,
                key="sales_country"
            )

        with filter2:
            selected_year = st.selectbox(
                "Year",
                available_years,
                key="sales_year"
            )

        months_available = sorted(
            dated_data.loc[
                dated_data["year"] == selected_year, "month"
            ].unique().tolist()
        )

        with filter3:
            selected_month = st.selectbox(
                "Month",
                months_available,
                format_func=lambda m: month_names[int(m)],
                key="sales_month"
            )

        # Filter records for the selected month and year
        monthly = dated_data[
            (dated_data["year"] == selected_year)
            & (dated_data["month"] == selected_month)
        ].copy()

        if dashboard_country != "All countries":
            monthly = monthly[
                monthly["country"] == dashboard_country
            ]

        monthly = monthly.dropna(subset=["units_sold"])

        if monthly.empty:
            st.warning("No sales records for these filters.")
        else:
            # Aggregate units sold by medicine
            sales_summary = (
                monthly.groupby("medicine", as_index=False)
                .agg(
                    total_units_sold=("units_sold", "sum"),
                    average_recorded_stock=("stock_level", "mean"),
                    average_unit_price=("unit_price", "mean")
                )
                .sort_values("total_units_sold", ascending=False)
            )

            sales_summary["total_units_sold"] = (
                sales_summary["total_units_sold"].round(0)
            )

            # Dashboard metrics
            total_units = monthly["units_sold"].sum()
            number_of_medicines = monthly["medicine"].nunique()
            best_seller = sales_summary.iloc[0]

            m1, m2, m3 = st.columns(3)

            m1.metric(
                "Total units sold",
                f"{total_units:,.0f}"
            )

            m2.metric(
                "Medicines recorded",
                f"{number_of_medicines:,}"
            )

            m3.metric(
                "Highest-selling medicine",
                str(best_seller["medicine"])
            )

            st.success(
                f"Best seller for {month_names[int(selected_month)]} "
                f"{selected_year}: **{best_seller['medicine']}** "
                f"with **{best_seller['total_units_sold']:,.0f} "
                f"recorded units sold**."
            )

            # Top 10 chart
            st.subheader("🏆 Top 10 Best-Selling Medicines")

            top10 = sales_summary.head(10).set_index("medicine")

            st.bar_chart(
                top10[["total_units_sold"]],
                horizontal=True
            )

            # Detailed ranking
            st.subheader("Medicine Sales Ranking")

            ranking = sales_summary.copy()
            ranking.insert(
                0, "Rank", range(1, len(ranking) + 1)
            )

            st.dataframe(
                ranking,
                use_container_width=True,
                hide_index=True
            )

            # Download report
            csv_data = sales_summary.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="⬇️ Download monthly sales report",
                data=csv_data,
                file_name=(
                    f"medistock_sales_{selected_year}_"
                    f"{int(selected_month):02d}.csv"
                ),
                mime="text/csv"
            )

            st.caption(
                "Sales rankings use the sum of units_sold in the "
                "selected month. They describe the supplied dataset, "
                "not verified sales from a specific pharmacy."
            )

st.divider()
st.caption(
    "MediStock Prototype | Dataset-based results | "
    "Live pharmacy inventory is not connected yet."
)

  
