import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ----------------------------------------
# Page Config
# ----------------------------------------
st.set_page_config(page_title="Store Traffic Dashboard", layout="wide")

st.title("📊 Store Traffic & Till Performance Dashboard")

# ----------------------------------------
# Cache Data Loading
# ----------------------------------------
@st.cache_data
def load_and_clean_data(uploaded_file):
    df = pd.read_csv(uploaded_file)

    # Drop unwanted columns (based on your structure)
    cols_to_delete = list(range(0, 10)) + list(range(18, 22))
    df_cleaned = df.drop(df.columns[cols_to_delete], axis=1)

    # Rename columns
    new_names = ["Date", "Till", "Session", "Rct", "Customer", "Total", "Loyalty", "Cashier"]
    df_cleaned.columns = new_names

    # Convert types
    df_cleaned['Date'] = pd.to_datetime(df_cleaned['Date'], dayfirst=True, errors='coerce')
    df_cleaned['Total'] = df_cleaned['Total'].astype(str).str.replace(',', '').astype(float)

    df_cleaned = df_cleaned.dropna(subset=['Date'])

    return df_cleaned


# ----------------------------------------
# File Upload
# ----------------------------------------
uploaded_file = st.file_uploader("Upload rk.csv file", type=["csv"])

if uploaded_file is not None:

    df_cleaned = load_and_clean_data(uploaded_file)

    # ----------------------------------------
    # Sidebar Filters
    # ----------------------------------------
    min_date = df_cleaned['Date'].min().date()
    max_date = df_cleaned['Date'].max().date()

    st.sidebar.header("Filters")

    date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    hour_range = st.sidebar.slider(
        "Select Hour Range",
        0, 23, (0, 23)
    )

    start_date, end_date = date_range
    start_hour, end_hour = hour_range

    # ----------------------------------------
    # Filter Data
    # ----------------------------------------
    df_filtered = df_cleaned[
        (df_cleaned['Date'].dt.date >= start_date) &
        (df_cleaned['Date'].dt.date <= end_date)
    ].copy()

    df_filtered = df_filtered[
        (df_filtered['Date'].dt.hour >= start_hour) &
        (df_filtered['Date'].dt.hour <= end_hour)
    ]

    if df_filtered.empty:
        st.warning("No data available for selected filters.")
    else:
        df_filtered['Day'] = df_filtered['Date'].dt.date

        # ----------------------------------------
        # Daily Metrics
        # ----------------------------------------
        daily_metrics = df_filtered.groupby('Day').agg(
            Max_Tills=('Till', 'nunique'),
            Average_Till_Number=('Till', 'mean'),
            Total_Transactions=('Till', 'size')
        ).reset_index()

        duration = max((end_hour - start_hour + 1), 1)

        daily_metrics['Customers_Per_Till_Per_Hour'] = (
            daily_metrics['Total_Transactions'] /
            (daily_metrics['Max_Tills'] * duration)
        )

        # ----------------------------------------
        # KPI CARDS
        # ----------------------------------------
        col1, col2, col3 = st.columns(3)

        col1.metric("Max Tills (Peak Day)", daily_metrics['Max_Tills'].max())
        col2.metric("Average Tills Used", round(daily_metrics['Max_Tills'].mean(), 2))
        col3.metric("Avg Customers/Till/Hour",
                    round(daily_metrics['Customers_Per_Till_Per_Hour'].mean(), 2))

        st.divider()

        # ----------------------------------------
        # ENHANCED PLOT
        # ----------------------------------------
        fig, ax = plt.subplots(figsize=(14, 6))

        sns.lineplot(
            data=daily_metrics,
            x='Day',
            y='Max_Tills',
            marker='o',
            linewidth=2,
            label='Max Tills',
            ax=ax
        )

        sns.lineplot(
            data=daily_metrics,
            x='Day',
            y='Customers_Per_Till_Per_Hour',
            marker='o',
            linewidth=2,
            label='Customers per Till per Hour',
            ax=ax
        )

        # Add labels to every point
        for i in range(len(daily_metrics)):
            ax.text(
                daily_metrics['Day'].iloc[i],
                daily_metrics['Max_Tills'].iloc[i],
                round(daily_metrics['Max_Tills'].iloc[i], 2),
                fontsize=8,
                ha='right'
            )

            ax.text(
                daily_metrics['Day'].iloc[i],
                daily_metrics['Customers_Per_Till_Per_Hour'].iloc[i],
                round(daily_metrics['Customers_Per_Till_Per_Hour'].iloc[i], 2),
                fontsize=8,
                ha='left'
            )

        ax.set_title(
            f"Till Performance ({start_hour}:00 - {end_hour}:00)",
            fontsize=14,
            fontweight='bold'
        )

        ax.set_xlabel("Date", fontsize=12)
        ax.set_ylabel("Value", fontsize=12)

        plt.xticks(rotation=45)

        # Strong grid
        ax.grid(True, which='both', linestyle='--', linewidth=0.7, alpha=0.7)

        ax.legend()
        plt.tight_layout()

        st.pyplot(fig)

        # ----------------------------------------
        # Data Table
        # ----------------------------------------
        st.subheader("📋 Daily Metrics Table")
        st.dataframe(daily_metrics, use_container_width=True)

else:
    st.info("Upload your rk.csv file to begin analysis.")
