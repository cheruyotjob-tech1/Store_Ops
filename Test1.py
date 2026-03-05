import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Store Traffic Dashboard", layout="wide")

# Hide Streamlit header/menu
hide_streamlit_style = """
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("📊 Store Traffic & Till Performance Dashboard")

# -----------------------------
# Upload CSV
# -----------------------------
uploaded_file = st.file_uploader("Upload rk.csv file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # -----------------------------
    # Clean Data
    # -----------------------------
    cols_to_delete = list(range(0, 10)) + list(range(18, 22))
    df_cleaned = df.drop(df.columns[cols_to_delete], axis=1)
    new_names = ["Date", "Till", "Session", "Rct", "Customer", "Total", "Loyalty", "Cashier"]
    df_cleaned.columns = new_names

    df_cleaned['Date'] = pd.to_datetime(df_cleaned['Date'], dayfirst=True, errors='coerce')
    # Clean 'Total' globally first to ensure consistency
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
    # Filter Data (main)
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
            
            daily_plot_df = pd.merge(daily_max_tills, daily_metrics, on='Day', how='left')
            daily_plot_df['Day'] = pd.to_datetime(daily_plot_df['Day'])

            # Calculate Waiting Time
            daily_plot_df['Waiting_Time'] = (daily_plot_df['Customers_Per_Till'] * 10) / 40
            daily_plot_df['Customers_Per_Till'] = daily_plot_df['Customers_Per_Till'].round(2)
            daily_plot_df['Waiting_Time'] = daily_plot_df['Waiting_Time'].round(2)

            # -----------------------------
            # Main Plot: Daily Till Metrics
            # -----------------------------
            fig, ax = plt.subplots(figsize=(14, 6))
            sns.lineplot(data=daily_plot_df, x='Day', y='Max_Tills', label='Max Tills', ax=ax)
            sns.lineplot(data=daily_plot_df, x='Day', y='Average_Till_Number', label='Average Till', ax=ax)
            sns.lineplot(data=daily_plot_df, x='Day', y='Active_Tills', label='Active Tills (Filtered Hours)', ax=ax)
            sns.lineplot(data=daily_plot_df, x='Day', y='Customers_Per_Till', label='Customers per Till per Hour', ax=ax)
            sns.lineplot(data=daily_plot_df, x='Day', y='Waiting_Time', label='Est. Waiting Time (min)', linestyle='--', linewidth=2.5, marker='o', ax=ax)

            ax.set_title(f"Daily Till Metrics ({start_hour}:00 - {end_hour}:00)")
            plt.xticks(rotation=45)
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)

            # Table
            st.subheader("Daily Till Metrics Table")
            st.dataframe(daily_plot_df.style.format({'Max_Tills': '{:.0f}', 'Average_Till_Number': '{:.1f}', 'Active_Tills': '{:.0f}', 'Customers_Per_Till': '{:.2f}', 'Waiting_Time': '{:.2f}'}), use_container_width=True)

            # -----------------------------
            # NEW: Top Loyal Customers Analysis (Filtered)
            # -----------------------------
            st.divider()
            st.subheader("🏆 Top Loyal Customers Shopping Patterns")
            
            # Using the filtered time dataframe to respect date/hour sliders
            loyal_customers_df = df_time[df_time['Loyalty'] == 'þ'].copy()
            
            if not loyal_customers_df.empty:
                customer_summary = loyal_customers_df.groupby('Customer').agg(
                    Value=('Total', 'sum'),
                    Frequency=('Rct', 'count')
                ).reset_index()
                customer_summary['Basket Value'] = customer_summary['Value'] / customer_summary['Frequency']

                # Filter out placeholder/generic names if necessary
                customer_summary_filtered = customer_summary[customer_summary['Customer'] != '<Customer Name>']

                fig_loyal, axes = plt.subplots(1, 3, figsize=(24, 7))
                
                # Plot 1: Top 10 by Value
                top_value = customer_summary_filtered.sort_values(by='Value', ascending=False).head(10)
                sns.barplot(x='Customer', y='Value', data=top_value, ax=axes[0], palette='viridis')
                axes[0].set_title('Top 10 Customers by Value')
                axes[0].tick_params(axis='x', rotation=45)

                # Plot 2: Top 10 by Frequency
                top_freq = customer_summary_filtered.sort_values(by='Frequency', ascending=False).head(10)
                sns.barplot(x='Customer', y='Frequency', data=top_freq, ax=axes[1], palette='magma')
                axes[1].set_title('Top 10 Customers by Frequency')
                axes[1].tick_params(axis='x', rotation=45)

                # Plot 3: Top 10 by Basket Value
                top_basket = customer_summary_filtered.sort_values(by='Basket Value', ascending=False).head(10)
                sns.barplot(x='Customer', y='Basket Value', data=top_basket, ax=axes[2], palette='cividis')
                axes[2].set_title('Top 10 Customers by Basket Value')
                axes[2].tick_params(axis='x', rotation=45)

                plt.tight_layout()
                st.pyplot(fig_loyal)
            else:
                st.info("No loyal customers (þ) found for the selected time period.")

            # -----------------------------
            # Existing Loyalty Category Insights
            # -----------------------------
            st.subheader("Loyalty Customer Insights (Broad)")
            df_loyalty = df_filtered[df_filtered['Loyalty'].isin(['þ', 'o'])].copy()
            if not df_loyalty.empty:
                df_loyalty['Loyalty_Category'] = df_loyalty['Loyalty'].map({'þ': 'Loyal', 'o': 'Non-Loyal'})
                col1, col2 = st.columns(2)
                # ... [Existing Loyalty plots code continues here] ...
                with col1:
                    avg_data = df_loyalty.groupby('Loyalty_Category')['Total'].mean().reset_index()
                    fig_bar, ax_bar = plt.subplots()
                    sns.barplot(x='Loyalty_Category', y='Total', data=avg_data, palette='viridis', ax=ax_bar)
                    st.pyplot(fig_bar)
                with col2:
                    df_loyalty['Day'] = pd.to_datetime(df_loyalty['Date'].dt.date)
                    counts = df_loyalty.groupby(['Day', 'Loyalty_Category']).size().reset_index(name='Count')
                    fig_daily, ax_daily = plt.subplots()
                    sns.barplot(data=counts, x='Day', y='Count', hue='Loyalty_Category', ax=ax_daily)
                    plt.xticks(rotation=45)
                    st.pyplot(fig_daily)

else:
    st.info("Please upload your rk.csv file to begin.")
