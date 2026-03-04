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

# ────────────────────────────────────────────────
# Upload CSV
# ────────────────────────────────────────────────
uploaded_file = st.file_uploader("Upload rk.csv file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # ────────────────────────────────────────────────
    # Clean Data
    # ────────────────────────────────────────────────
    cols_to_delete = list(range(0, 10)) + list(range(18, 22))
    df_cleaned = df.drop(df.columns[cols_to_delete], axis=1)
    new_names = ["Date", "Till", "Session", "Rct", "Customer", "Total", "Loyalty", "Cashier"]
    df_cleaned.columns = new_names

    df_cleaned['Date'] = pd.to_datetime(df_cleaned['Date'], dayfirst=True, errors='coerce')
    df_cleaned['Total'] = df_cleaned['Total'].astype(str).str.replace(',', '').astype(float)
    df_cleaned = df_cleaned.dropna(subset=['Date'])

    # ────────────────────────────────────────────────
    # Sidebar Filters
    # ────────────────────────────────────────────────
    min_date = df_cleaned['Date'].min().date()
    max_date = df_cleaned['Date'].max().date()

    st.sidebar.header("Filters")
    start_date = st.sidebar.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
    end_date   = st.sidebar.date_input("End Date",   max_date, min_value=min_date, max_value=max_date)
    start_hour = st.sidebar.slider("Start Hour", 0, 23, 0)
    end_hour   = st.sidebar.slider("End Hour",   0, 23, 23)

    # ────────────────────────────────────────────────
    # Filter Data
    # ────────────────────────────────────────────────
    df_filtered = df_cleaned[
        (df_cleaned['Date'].dt.date >= start_date) &
        (df_cleaned['Date'].dt.date <= end_date) &
        (df_cleaned['Date'].dt.hour >= start_hour) &
        (df_cleaned['Date'].dt.hour <= end_hour)
    ].copy()

    if df_filtered.empty:
        st.warning("No data available for the selected date & hour range.")
    else:
        df_filtered['Day'] = df_filtered['Date'].dt.date

        # Max tills per day (always available)
        daily_max_tills = df_filtered.groupby('Day')['Till'].nunique().reset_index(name='Max_Tills')

        # ────────────────────────────────────────────────
        # Hourly-filtered metrics
        # ────────────────────────────────────────────────
        if not df_filtered.empty:
            daily_metrics = df_filtered.groupby('Day').agg(
                Average_Till_Number=('Till', 'mean'),
                Active_Tills=('Till', 'nunique'),
                Daily_Rows_Count=('Till', 'size')
            ).reset_index()

            duration = max((end_hour - start_hour + 1), 1)
            daily_metrics['Customers_Per_Till'] = (
                daily_metrics['Daily_Rows_Count'] /
                (daily_metrics['Active_Tills'] * duration)
            ).round(2)

            # Safe merge
            daily_plot_df = pd.merge(
                daily_max_tills,
                daily_metrics,
                on='Day',
                how='left'
            )
            daily_plot_df['Day'] = pd.to_datetime(daily_plot_df['Day'])
            daily_plot_df['Waiting_Time'] = (daily_plot_df['Customers_Per_Till'].fillna(0) * 10 / 50).round(2)

        else:
            # Fallback when hour filter removes everything
            daily_plot_df = daily_max_tills.copy()
            daily_plot_df['Day'] = pd.to_datetime(daily_plot_df['Day'])
            for col in ['Average_Till_Number', 'Active_Tills', 'Customers_Per_Till', 'Waiting_Time']:
                daily_plot_df[col] = 0.0
            st.info("No transactions in selected hour range — showing only maximum tills per day.")

        # ────────────────────────────────────────────────
        # Main Plot: Daily Till Metrics
        # ────────────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(14, 6))
        sns.lineplot(data=daily_plot_df, x='Day', y='Max_Tills',          label='Max Tills', ax=ax)
        sns.lineplot(data=daily_plot_df, x='Day', y='Average_Till_Number', label='Avg Till', ax=ax)
        sns.lineplot(data=daily_plot_df, x='Day', y='Active_Tills',       label='Active Tills', ax=ax)
        sns.lineplot(data=daily_plot_df, x='Day', y='Customers_Per_Till', label='Cust / Till / Hour', ax=ax)
        sns.lineplot(data=daily_plot_df, x='Day', y='Waiting_Time',
                     label='Est. Wait (min)', linestyle='--', linewidth=2.5, marker='o', ax=ax)

        ax.set_title(f"Daily Till Metrics ({start_hour:02d}:00 – {end_hour:02d}:00)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Value")
        ax.grid(True, which='major', linestyle='-', alpha=0.6)
        ax.grid(True, which='minor', linestyle=':', alpha=0.3)
        ax.minorticks_on()
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)

        # ────────────────────────────────────────────────
        # Loyalty Analysis
        # ────────────────────────────────────────────────
        st.subheader("Loyalty Customer Insights")
        df_loyalty = df_filtered[df_filtered['Loyalty'].isin(['þ', 'o'])].copy()

        if df_loyalty.empty:
            st.info("No loyalty data (þ or o) in selected period.")
        else:
            df_loyalty['Loyalty_Category'] = df_loyalty['Loyalty'].map({'þ': 'Loyal', 'o': 'Non-Loyal'})

            avg_loyal     = df_loyalty[df_loyalty['Loyalty_Category'] == 'Loyal']['Total'].mean()
            avg_non_loyal = df_loyalty[df_loyalty['Loyalty_Category'] == 'Non-Loyal']['Total'].mean()
            avg_overall   = df_loyalty['Total'].mean()

            plot_data = pd.DataFrame({
                'Category': ['Loyal', 'Non-Loyal', 'Overall'],
                'Average_Spending': [avg_loyal, avg_non_loyal, avg_overall]
            })

            # ── Loyalty spending bar ──
            col1, col2 = st.columns(2)

            with col1:
                fig1, ax1 = plt.subplots(figsize=(7, 5))
                sns.barplot(
                    data=plot_data,
                    x='Category',
                    y='Average_Spending',
                    hue='Category',
                    palette='viridis',
                    legend=False,
                    ax=ax1
                )
                ax1.set_title('Average Spending by Loyalty Category')
                for i, v in enumerate(plot_data['Average_Spending']):
                    ax1.text(i, v + max(1, v*0.02), f"{v:.2f}", ha='center')
                st.pyplot(fig1)

            # ── Daily loyalty transactions ──
            with col2:
                daily_loyal = df_loyalty.groupby([df_loyalty['Date'].dt.date, 'Loyalty_Category']).size()\
                                        .reset_index(name='Count')
                daily_loyal['Date'] = pd.to_datetime(daily_loyal['Date'])

                fig2, ax2 = plt.subplots(figsize=(7, 5))
                sns.barplot(data=daily_loyal, x='Date', y='Count', hue='Loyalty_Category', ax=ax2)
                ax2.set_title('Daily Transactions by Loyalty')
                plt.xticks(rotation=45)
                st.pyplot(fig2)

            # ── Top 10 loyal customers ──
            st.subheader("Top 10 Loyal Customers by Total Spending")
            loyal_only = df_loyalty[df_loyalty['Loyalty_Category'] == 'Loyal']
            top_cust = loyal_only.groupby('Customer')['Total'].sum()\
                                 .reset_index(name='Total_Spending')\
                                 .sort_values('Total_Spending', ascending=False)\
                                 .head(10)

            if not top_cust.empty:
                fig_top, ax_top = plt.subplots(figsize=(10, 7))
                sns.barplot(
                    data=top_cust,
                    x='Total_Spending',
                    y='Customer',
                    hue='Customer',
                    palette='magma',
                    legend=False,
                    ax=ax_top
                )
                ax_top.set_title("Top 10 Loyal Customers – Total Spending")
                ax_top.grid(axis='x', linestyle='--', alpha=0.5)
                for i, row in top_cust.iterrows():
                    ax_top.text(row['Total_Spending'] * 1.01, i, f"{row['Total_Spending']:,.0f}", va='center')
                plt.tight_layout()
                st.pyplot(fig_top)

            # ── Day of week pattern for loyal ──
            st.subheader("Loyal Customer Shopping Patterns by Day of Week")
            loyal_only['Day_of_Week'] = loyal_only['Date'].dt.day_name()
            trans_by_day = loyal_only.groupby('Day_of_Week').size().reset_index(name='Transaction_Count')

            day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
            trans_by_day['Day_of_Week'] = pd.Categorical(trans_by_day['Day_of_Week'], categories=day_order, ordered=True)
            trans_by_day = trans_by_day.sort_values('Day_of_Week')

            if not trans_by_day.empty:
                fig_day, ax_day = plt.subplots(figsize=(10, 6))
                sns.barplot(
                    data=trans_by_day,
                    x='Transaction_Count',
                    y='Day_of_Week',
                    hue='Day_of_Week',
                    palette='cubehelix',
                    legend=False,
                    ax=ax_day
                )
                ax_day.set_title("Loyal Customers – Transactions per Day of Week")
                ax_day.grid(axis='x', linestyle='--', alpha=0.5)
                for i, row in trans_by_day.iterrows():
                    ax_day.text(row['Transaction_Count'] + 0.4, i, f"{int(row['Transaction_Count'])}", va='center')
                plt.tight_layout()
                st.pyplot(fig_day)

            # ── Till frequency ──
            st.subheader("Transaction Frequency by Till Number")
            till_freq = df_filtered['Till'].value_counts().reset_index()
            till_freq.columns = ['Till', 'Frequency']
            till_freq = till_freq.sort_values('Till')

            fig_till, ax_till = plt.subplots(figsize=(10, 6))
            sns.barplot(
                data=till_freq,
                x='Till',
                y='Frequency',
                hue='Till',
                palette='viridis',
                legend=False,
                ax=ax_till
            )
            ax_till.set_title("Transactions per Till")
            ax_till.grid(axis='y', linestyle='--', alpha=0.5)
            plt.tight_layout()
            st.pyplot(fig_till)

else:
    st.info("Please upload your rk.csv file to begin.")
