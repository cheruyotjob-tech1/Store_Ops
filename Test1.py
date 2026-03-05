# app.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime

# ────────────────────────────────────────────────
# Page config
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="Loyal Customer Dashboard",
    page_icon="🛒",
    layout="wide"
)

st.title("Loyal Customer Analysis Dashboard")
st.markdown("This dashboard shows insights from POS receipt data (Jan–Mar 2026)")

# ────────────────────────────────────────────────
# 1. File uploader (so you can upload pp.csv or similar)
# ────────────────────────────────────────────────
uploaded_file = st.file_uploader("Upload your POS data CSV (pp.csv format)", type=["csv"])

if uploaded_file is not None:
    # ────────────────────────────────────────────────
    # 2. Load and clean data (mirroring your notebook)
    # ────────────────────────────────────────────────
    with st.spinner("Loading and cleaning data..."):
        df = pd.read_csv(uploaded_file)

        # Drop useless header-like rows & reset index
        df = df[df['Date Time'].str.contains(r'\d{2}/\d{2}/\d{4}', na=False, regex=True)].copy()
        df.reset_index(drop=True, inplace=True)

        # Select only the meaningful columns (based on your cleaning steps)
        keep_cols = [
            'Date Time', 'Till', 'Session', 'Rct',
            'Customer', 'Total', 'Loyalty', 'Cashier'
        ]
        # Adjust if column names are slightly different after read_csv
        available_cols = [c for c in keep_cols if c in df.columns]
        df_clean = df[available_cols].copy()

        # Rename for consistency
        df_clean = df_clean.rename(columns={
            'Date Time': 'Date',
            'Rct': 'Receipt',
        })

        # Convert Date → datetime
        df_clean['Date'] = pd.to_datetime(df_clean['Date'], format='%d/%m/%Y %H:%M', errors='coerce')

        # Clean Total column (remove commas, convert to float)
        df_clean['Total'] = df_clean['Total'].astype(str).str.replace(',', '').astype(float)

        # Filter only rows that look like real transactions
        df_clean = df_clean[df_clean['Total'] > 0].copy()

        # Add useful derived columns
        df_clean['Date_only']     = df_clean['Date'].dt.date
        df_clean['Day_of_Week']   = df_clean['Date'].dt.day_name()
        df_clean['Month']         = df_clean['Date'].dt.month
        df_clean['Year']          = df_clean['Date'].dt.year
        df_clean['Hour']          = df_clean['Date'].dt.hour

    st.success(f"Loaded {len(df_clean):,} valid transactions!")

    # ────────────────────────────────────────────────
    # 3. Identify Loyal Customers
    #    (simple definition: appeared ≥ 5 times OR spent ≥ some threshold)
    # ────────────────────────────────────────────────
    MIN_TRANSACTIONS = 5
    MIN_SPEND        = 10000  # KES – adjust as needed

    loyal_customers = (
        df_clean.groupby('Customer')
        .agg(
            Transaction_Count=('Receipt', 'nunique'),
            Total_Spending=('Total', 'sum'),
            First_Date=('Date', 'min'),
            Last_Date=('Date', 'max'),
            Avg_Basket_Value=('Total', 'mean')
        )
        .reset_index()
    )

    # Filter loyal
    loyal_customers = loyal_customers[
        (loyal_customers['Transaction_Count'] >= MIN_TRANSACTIONS) |
        (loyal_customers['Total_Spending'] >= MIN_SPEND)
    ].sort_values('Total_Spending', ascending=False)

    st.subheader("Loyal Customers Overview")
    st.dataframe(
        loyal_customers.style.format({
            'Total_Spending':    '{:,.0f}',
            'Avg_Basket_Value':  '{:,.0f}',
            'First_Date':        '{:%Y-%m-%d}',
            'Last_Date':         '{:%Y-%m-%d}'
        }),
        use_container_width=True
    )

    # ────────────────────────────────────────────────
    # 4. Prepare data for your requested plots
    # ────────────────────────────────────────────────
    top_loyal_metrics_filtered = loyal_customers.head(15).copy()   # top 15 spenders

    # Daily pattern (all loyal customers' transactions)
    transactions_by_day = (
        df_clean[df_clean['Customer'].isin(loyal_customers['Customer'])]
        .groupby('Day_of_Week')
        .agg(Transaction_Count=('Receipt', 'nunique'))
        .reset_index()
    )

    day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    transactions_by_day['Day_of_Week'] = pd.Categorical(
        transactions_by_day['Day_of_Week'], categories=day_order, ordered=True
    )
    transactions_by_day = transactions_by_day.sort_values('Day_of_Week')

    # ────────────────────────────────────────────────
    # 5. Your requested visualization – two subplots
    # ────────────────────────────────────────────────
    st.subheader("Selected Loyal Customer Analysis with Detailed Metrics")

    fig, axes = plt.subplots(2, 1, figsize=(14, 16), sharex=False)
    fig.suptitle('Selected Loyal Customer Analysis with Detailed Metrics', fontsize=20, y=1.02)

    # Plot 1: Total Spending (horizontal bar)
    if not top_loyal_metrics_filtered.empty:
        sns.barplot(
            ax=axes[0],
            x='Total_Spending',
            y='Customer',
            data=top_loyal_metrics_filtered,
            palette='magma',
            hue='Customer',
            legend=False
        )
        axes[0].set_title('Total Loyal Customers by Total Spending', fontsize=14)
        axes[0].set_xlabel('Total Spending (KES)')
        axes[0].set_ylabel('Customer')
        axes[0].grid(axis='x', linestyle='--', alpha=0.7)

        for index, row in top_loyal_metrics_filtered.iterrows():
            text = (
                f"Total: {row['Total_Spending']:,.0f}\n"
                f"BV: {row['Avg_Basket_Value']:,.0f}\n"
                f"Freq: {row['Transaction_Count']:,}"
            )
            axes[0].text(
                row['Total_Spending'], index,
                text, color='black', ha='left', va='center', fontsize=9
            )
    else:
        axes[0].text(0.5, 0.5, 'No loyal customer data', ha='center', va='center', fontsize=14, color='red')
        axes[0].axis('off')

    # Plot 2: Transactions by Day of Week
    if not transactions_by_day.empty:
        sns.barplot(
            ax=axes[1],
            x='Transaction_Count',
            y='Day_of_Week',
            data=transactions_by_day,
            palette='cubehelix',
            hue='Day_of_Week',
            legend=False
        )
        axes[1].set_title('Loyal Customer Shopping Patterns by Day of the Week', fontsize=14)
        axes[1].set_xlabel('Number of Transactions')
        axes[1].set_ylabel('Day of the Week')
        axes[1].grid(axis='x', linestyle='--', alpha=0.7)

        for index, row in transactions_by_day.iterrows():
            axes[1].text(
                row['Transaction_Count'], index,
                f"{row['Transaction_Count']:,}",
                color='black', ha='left', va='center', fontsize=10
            )
    else:
        axes[1].text(0.5, 0.5, 'No daily pattern data', ha='center', va='center', fontsize=14, color='red')
        axes[1].axis('off')

    plt.tight_layout(rect=[0, 0.03, 1, 0.98])
    st.pyplot(fig)

else:
    st.info("Please upload your POS CSV file (pp.csv or similar format) to start the analysis.")

st.markdown("---")
st.caption(f"Dashboard last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S EAT')}")
