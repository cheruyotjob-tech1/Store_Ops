import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Store Traffic Dashboard", layout="wide")
# Hide Streamlit header/menu
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""

st.title("📊 Store Traffic & Till Analytics")

# -----------------------------
# Upload CSV
# -----------------------------
uploaded_file = st.file_uploader("Upload rk.csv file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # -----------------------------
    # Clean Data (Same Logic as Yours)
    # -----------------------------
    cols_to_delete = list(range(0, 10)) + list(range(18, 22))
    df_cleaned = df.drop(df.columns[cols_to_delete], axis=1)

    new_names = ["Date", "Till", "Session", "Rct", "Customer", "Total", "Loyalty", "Cashier"]
    df_cleaned.columns = new_names

    df_cleaned['Date'] = pd.to_datetime(df_cleaned['Date'], dayfirst=True, errors='coerce')
    df_cleaned['Total'] = df_cleaned['Total'].astype(str).str.replace(',', '').astype(float)

    df_cleaned = df_cleaned.dropna(subset=['Date'])

    # -----------------------------
    # Sidebar Filters
    # -----------------------------
    min_date = df_cleaned['Date'].min().date()
    max_date = df_cleaned['Date'].max().date()

    st.sidebar.header("Filters")

    start_date = st.sidebar.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input("End Date", max_date, min_value=min_date, max_value=max_date)

    start_hour = st.sidebar.slider("Start Hour", 0, 23, 0)
    end_hour = st.sidebar.slider("End Hour", 0, 23, 23)

    # -----------------------------
    # Filter Data
    # -----------------------------
    df_filtered = df_cleaned[
        (df_cleaned['Date'].dt.date >= start_date) &
        (df_cleaned['Date'].dt.date <= end_date)
    ].copy()

    if df_filtered.empty:
        st.warning("No data for selected date range")
    else:
        df_filtered['Day'] = df_filtered['Date'].dt.date

        daily_max_tills = df_filtered.groupby('Day')['Till'].nunique().reset_index(name='Max_Tills')

        df_time = df_filtered[
            (df_filtered['Date'].dt.hour >= start_hour) &
            (df_filtered['Date'].dt.hour <= end_hour)
        ].copy()

        if not df_time.empty:
            daily_metrics = df_time.groupby('Day').agg(
                Average_Till_Number=('Till', 'mean'),
                Active_Tills=('Till', 'nunique'),
                Daily_Rows_Count=('Till', 'size')
            ).reset_index()

            duration = max((end_hour - start_hour + 1), 1)

            daily_metrics['Customers_Per_Till'] = (
                daily_metrics['Daily_Rows_Count'] /
                (daily_metrics['Active_Tills'] * duration)
            )
        else:
            daily_metrics = pd.DataFrame()

        daily_plot_df = pd.merge(daily_max_tills, daily_metrics, on='Day', how='left')
        daily_plot_df['Day'] = pd.to_datetime(daily_plot_df['Day'])

        # -----------------------------
        # Plot
        # -----------------------------
        fig, ax = plt.subplots(figsize=(14, 6))

        sns.lineplot(data=daily_plot_df, x='Day', y='Max_Tills', label='Max Tills', ax=ax)
        sns.lineplot(data=daily_plot_df, x='Day', y='Average_Till_Number', label='Average Till', ax=ax)
        sns.lineplot(data=daily_plot_df, x='Day', y='Active_Tills', label='Active Tills (Filtered Hours)', ax=ax)
        sns.lineplot(data=daily_plot_df, x='Day', y='Customers_Per_Till', label='Customers per Till per Hour', ax=ax)

        ax.set_title(f"Daily Till Metrics ({start_hour}:00 - {end_hour}:00)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Metric Value")
        plt.xticks(rotation=45)
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()

        st.pyplot(fig)

        # -----------------------------
        # Show Data
        # -----------------------------
        st.subheader("Daily Metrics Table")
        st.dataframe(daily_plot_df, use_container_width=True)

else:
    st.info("Please upload your rk.csv file to begin.")

