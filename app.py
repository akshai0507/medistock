
import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="MediStock",
    page_icon="💊",
    layout="wide"
)

st.title("💊 MediStock")
st.subheader("Find medicines using recorded pharmacy data")
st.write(
    "Search the dataset to view recorded stock levels and prices. "
    "These are sample data values, not confirmed live pharmacy inventory."
)

DATA_FILE = Path(__file__).parent / "medistock_cleaned_data.csv"

@st.cache_data
def load_data():
    data = pd.read_csv(DATA_FILE)
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["medicine"] = data["medicine"].fillna("").astype(str)
    data["country"] = data["country"].fillna("").astype(str)
    return data

try:
    df = load_data()
except FileNotFoundError:
    st.error(
        "Dataset not found. Upload medistock_cleaned_data.csv "
        "to the same GitHub repository as app.py."
    )
    st.stop()

# Search controls
st.header("Search medicines")

col1, col2 = st.columns(2)

with col1:
    medicine_query = st.text_input(
        "Medicine name",
        placeholder="Example: Amlodipine"
    )

with col2:
    countries = sorted(
        [c for c in df["country"].dropna().unique() if c]
    )
    selected_country = st.selectbox(
        "Country",
        ["All countries"] + countries
    )

if medicine_query.strip():
    results = df[
        df["medicine"].str.contains(
            medicine_query.strip(),
            case=False,
            regex=False,
            na=False
        )
    ].copy()

    if selected_country != "All countries":
        results = results[
            results["country"] == selected_country
        ]

    if results.empty:
        st.warning("No matching medicine found in this dataset.")
    else:
        results = results.sort_values("date", ascending=False)

        st.success(f"Found {len(results):,} matching records.")

        latest = results.iloc[0]

        a, b, c = st.columns(3)
        a.metric("Recorded stock", f"{latest['stock_level']:,.0f}")
        b.metric("Recorded unit price", f"{latest['unit_price']:,.2f}")
        c.metric(
            "Record date",
            latest["date"].strftime("%Y-%m-%d")
            if pd.notna(latest["date"]) else "Unknown"
        )

        st.caption(
            "These values come from the most recent matching dataset "
            "record. Currency and stock freshness have not been verified."
        )

        display_columns = [
            "date", "medicine", "country", "category",
            "stock_level", "unit_price", "units_sold",
            "expiry_days_remaining"
        ]

        st.subheader("Matching records")
        st.dataframe(
            results[display_columns].head(100),
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("Enter a medicine name to begin searching.")

st.divider()
st.caption(
    "MediStock prototype | Sample dataset | "
    "Availability must be confirmed with the pharmacy."
)
