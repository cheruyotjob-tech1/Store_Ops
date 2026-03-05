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
    df_cleaned['Total'] = df_cleaned['Total'].astype(str).str.replace(',', '').astype(float)

    df_cleaned = df_cleaned.dropna(subset=['Date'])

    # -----------------------------
    # Sidebar Filters
    # -----------------------------
    min_date = df_cleaned['Date'].min().date()
    max_date = df_cleaned['Date'].max().date()

    st.sidebar.header("Filters")

    start_date = st.sidebar.date_input(
        "Start Date",
        min_date,
        min_value=min_date,
        max_value=max_date
    )

    end_date = st.sidebar.date_input(
        "End Date",
        max_date,
        min_value=min_date,
        max_value=max_date
    )

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

        # Waiting time estimation
        daily_plot_df['Waiting_Time'] = (daily_plot_df['Customers_Per_Till'] * 10) / 50

        daily_plot_df['Customers_Per_Till'] = daily_plot_df['Customers_Per_Till'].round(2)
        daily_plot_df['Waiting_Time'] = daily_plot_df['Waiting_Time'].round(2)

        # -----------------------------
        # Main Plot
        # -----------------------------
        fig, ax = plt.subplots(figsize=(14, 6))

        sns.lineplot(data=daily_plot_df, x='Day', y='Max_Tills', label='Max Tills', ax=ax)
        sns.lineplot(data=daily_plot_df, x='Day', y='Average_Till_Number', label='Average Till', ax=ax)
        sns.lineplot(data=daily_plot_df, x='Day', y='Active_Tills', label='Active Tills (Filtered Hours)', ax=ax)
        sns.lineplot(data=daily_plot_df, x='Day', y='Customers_Per_Till', label='Customers per Till per Hour', ax=ax)

        sns.lineplot(
            data=daily_plot_df,
            x='Day',
            y='Waiting_Time',
            label='Est. Waiting Time (min)',
            linestyle='--',
            linewidth=2.5,
            marker='o',
            ax=ax
        )

        ax.set_title(f"Daily Till Metrics ({start_hour}:00 - {end_hour}:00)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Metric Value")

        plt.xticks(rotation=45)

        ax.grid(True, which='major', linestyle='-', linewidth=1, alpha=0.7)
        ax.grid(True, which='minor', linestyle=':', linewidth=0.5, alpha=0.4)

        ax.minorticks_on()
        ax.set_axisbelow(True)

        plt.tight_layout()

        st.pyplot(fig)

        # -----------------------------
        # Data Table
        # -----------------------------
        st.subheader("Daily Till Metrics Table")

        styled_df = daily_plot_df.style.format({
            'Max_Tills': '{:.0f}',
            'Average_Till_Number': '{:.1f}',
            'Active_Tills': '{:.0f}',
            'Customers_Per_Till': '{:.2f}',
            'Waiting_Time': '{:.2f}'
        })

        st.dataframe(styled_df, use_container_width=True)

        # -----------------------------
        # Loyalty Analysis
        # -----------------------------
        st.subheader("Loyalty Customer Insights")

        df_loyalty = df_filtered[df_filtered['Loyalty'].isin(['þ', 'o'])].copy()

        if df_loyalty.empty:

            st.info("No loyalty data in the selected date range.")

        else:

            df_loyalty['Loyalty_Category'] = df_loyalty['Loyalty'].map({
                'þ': 'Loyal',
                'o': 'Non-Loyal'
            })

            avg_spending_loyal = df_loyalty[df_loyalty['Loyalty_Category'] == 'Loyal']['Total'].mean()
            avg_spending_non_loyal = df_loyalty[df_loyalty['Loyalty_Category'] == 'Non-Loyal']['Total'].mean()
            overall_avg_spending = df_loyalty['Total'].mean()

            plot_data = pd.DataFrame({
                'Category': ['Loyal Customers', 'Non-Loyal Customers', 'Overall Average'],
                'Average_Spending': [
                    avg_spending_loyal,
                    avg_spending_non_loyal,
                    overall_avg_spending
                ]
            })

            df_loyalty['Day'] = df_loyalty['Date'].dt.date

            daily_customer_counts = df_loyalty.groupby(
                ['Day', 'Loyalty_Category']
            ).size().reset_index(name='Transaction_Count')

            daily_customer_counts['Day'] = pd.to_datetime(daily_customer_counts['Day'])

            col1, col2 = st.columns(2)

            # -----------------------------
            # Average Spending Plot
            # -----------------------------
            with col1:

                fig_bar, ax_bar = plt.subplots(figsize=(8, 5))

                sns.barplot(
                    x='Category',
                    y='Average_Spending',
                    data=plot_data,
                    palette='viridis',
                    ax=ax_bar
                )

                ax_bar.set_title('Average Spending by Loyalty Category')
                ax_bar.set_xlabel('Customer Category')
                ax_bar.set_ylabel('Average Spending (KSh)')

                for i, v in enumerate(plot_data['Average_Spending']):
                    ax_bar.text(i, v + 1, f"{v:.2f}", ha='center')

                plt.tight_layout()

                st.pyplot(fig_bar)

            # -----------------------------
            # Daily Transactions Plot
            # -----------------------------
            with col2:

                fig_daily, ax_daily = plt.subplots(figsize=(8, 5))

                sns.barplot(
                    data=daily_customer_counts,
                    x='Day',
                    y='Transaction_Count',
                    hue='Loyalty_Category',
                    ax=ax_daily
                )

                ax_daily.set_title('Daily Transactions by Loyalty Category')
                ax_daily.set_xlabel('Date')
                ax_daily.set_ylabel('Transactions')

                plt.xticks(rotation=45)

                plt.tight_layout()

                st.pyplot(fig_daily)

            # -----------------------------
            # Day of Week Shopping Pattern
            # -----------------------------
            st.subheader("Loyal Customer Shopping Patterns by Day of the Week")

            df_loyalty['Day_of_Week'] = df_loyalty['Date'].dt.day_name()

            transactions_by_day = df_loyalty.groupby(
                'Day_of_Week'
            ).size().reset_index(name='Transaction_Count')

            days_order = [
                'Monday','Tuesday','Wednesday',
                'Thursday','Friday','Saturday','Sunday'
            ]

            transactions_by_day['Day_of_Week'] = pd.Categorical(
                transactions_by_day['Day_of_Week'],
                categories=days_order,
                ordered=True
            )

            transactions_by_day = transactions_by_day.sort_values('Day_of_Week')

            fig_week, ax_week = plt.subplots(figsize=(12, 6))

            sns.barplot(
                x='Day_of_Week',
                y='Transaction_Count',
                data=transactions_by_day,
                palette='viridis',
                hue='Day_of_Week',
                legend=False,
                ax=ax_week
            )

            ax_week.set_title('Loyal Customer Shopping Patterns by Day of the Week')
            ax_week.set_xlabel('Day of the Week')
            ax_week.set_ylabel('Number of Transactions')

            plt.xticks(rotation=45)

            ax_week.grid(axis='y', linestyle='--', alpha=0.7)

            plt.tight_layout()

            st.pyplot(fig_week)

else:

    st.info("Please upload your rk.csv file to begin.")
