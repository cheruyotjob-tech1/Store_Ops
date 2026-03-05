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
        else:
            daily_metrics = pd.DataFrame()

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
        ax.grid(True, which='major', linestyle='-', alpha=0.7, color='gray')
        st.pyplot(fig)

        st.subheader("Daily Till Metrics Table")
        st.dataframe(daily_plot_df.style.format({
            'Max_Tills': '{:.0f}', 'Average_Till_Number': '{:.1f}', 
            'Active_Tills': '{:.0f}', 'Customers_Per_Till': '{:.2f}', 'Waiting_Time': '{:.2f}'
        }), use_container_width=True)

        # -----------------------------
        # Cashier Performance Metrics
        # -----------------------------
        st.divider()
        st.subheader("👨‍🍳 Cashier Performance Metrics")

        if not df_time.empty:
            cashier_transaction_counts = df_time.groupby('Cashier').size().reset_index(name='Transaction_Count')
            cashier_loyalty_counts = df_time.groupby(['Cashier', 'Loyalty']).size().reset_index(name='Loyalty_Transaction_Count')
            cashier_unique_tills = df_time.groupby('Cashier')['Till'].nunique().reset_index(name='Unique_Tills_Count')

            fig_cash, axes_cash = plt.subplots(1, 3, figsize=(24, 8))
            top_10_cashiers = cashier_transaction_counts.sort_values(by='Transaction_Count', ascending=False).head(10)
            top_10_names = top_10_cashiers['Cashier'].tolist()

            sns.barplot(x='Cashier', y='Transaction_Count', data=top_10_cashiers, ax=axes_cash[0], palette='viridis')
            axes_cash[0].set_title('Top 10 Cashiers by Transactions')
            axes_cash[0].tick_params(axis='x', rotation=45)

            loyalty_filtered = cashier_loyalty_counts[cashier_loyalty_counts['Cashier'].isin(top_10_names)].copy()
            loyalty_filtered['Loyalty'] = pd.Categorical(loyalty_filtered['Loyalty'], categories=['o', 'þ'])
            sns.barplot(x='Cashier', y='Loyalty_Transaction_Count', hue='Loyalty', data=loyalty_filtered, ax=axes_cash[1], palette={'o': 'skyblue', 'þ': 'salmon'})
            axes_cash[1].set_title('Loyalty Breakdown')
            axes_cash[1].tick_params(axis='x', rotation=45)

            unique_tills_filtered = cashier_unique_tills[cashier_unique_tills['Cashier'].isin(top_10_names)].sort_values(by='Unique_Tills_Count', ascending=False)
            sns.barplot(x='Cashier', y='Unique_Tills_Count', data=unique_tills_filtered, ax=axes_cash[2], palette='mako')
            axes_cash[2].set_title('Unique Tills Used')
            axes_cash[2].tick_params(axis='x', rotation=45)

            plt.tight_layout()
            st.pyplot(fig_cash)

        # -----------------------------
        # NEW: Top Customer Analysis
        # -----------------------------
        st.divider()
        st.subheader("🏆 Top Customer Spending & Frequency")

        if not df_time.empty:
            # Grouping by Customer to find high-value individuals
            customer_analysis = df_time.groupby('Customer').agg(
                Total_Spend=('Total', 'sum'),
                Visit_Frequency=('Rct', 'count')
            ).reset_index()
            
            customer_analysis['Avg_Basket_Value'] = (customer_analysis['Total_Spend'] / customer_analysis['Visit_Frequency']).round(2)
            
            # Filtering out generic names
            customer_analysis = customer_analysis[~customer_analysis['Customer'].isin(['<Customer Name>', 'CASH'])]

            fig_cust, axes_cust = plt.subplots(1, 3, figsize=(24, 8))
            fig_cust.suptitle('Customer Analysis (Filtered Period)', fontsize=20)

            # Top 10 by Total Spend
            top_spend = customer_analysis.sort_values('Total_Spend', ascending=False).head(10)
            sns.barplot(x='Customer', y='Total_Spend', data=top_spend, ax=axes_cust[0], palette='crest')
            axes_cust[0].set_title('Top 10 Customers by Total Spend')
            axes_cust[0].tick_params(axis='x', rotation=45)

            # Top 10 by Visit Frequency
            top_freq = customer_analysis.sort_values('Visit_Frequency', ascending=False).head(10)
            sns.barplot(x='Customer', y='Visit_Frequency', data=top_freq, ax=axes_cust[1], palette='flare')
            axes_cust[1].set_title('Top 10 Customers by Visit Frequency')
            axes_cust[1].tick_params(axis='x', rotation=45)

            # Top 10 by Average Basket Value
            top_basket = customer_analysis.sort_values('Avg_Basket_Value', ascending=False).head(10)
            sns.barplot(x='Customer', y='Avg_Basket_Value', data=top_basket, ax=axes_cust[2], palette='magma')
            axes_cust[2].set_title('Top 10 Customers by Avg Basket Value')
            axes_cust[2].tick_params(axis='x', rotation=45)

            plt.tight_layout(rect=[0, 0.03, 1, 0.95])
            st.pyplot(fig_cust)

        # -----------------------------
        # Loyalty Analysis
        # -----------------------------
        st.divider()
        st.subheader("Loyalty Customer Insights")
        df_loyalty = df_filtered[df_filtered['Loyalty'].isin(['þ', 'o'])].copy()

        if not df_loyalty.empty:
            df_loyalty['Loyalty_Category'] = df_loyalty['Loyalty'].map({'þ': 'Loyal', 'o': 'Non-Loyal'})
            col1, col2 = st.columns(2)

            with col1:
                avg_spending = df_loyalty.groupby('Loyalty_Category')['Total'].mean().reset_index()
                fig_bar, ax_bar = plt.subplots(figsize=(8, 5))
                sns.barplot(x='Loyalty_Category', y='Total', data=avg_spending, palette='viridis', ax=ax_bar)
                ax_bar.set_title('Avg Spend by Loyalty')
                st.pyplot(fig_bar)

            with col2:
                df_loyalty['Day_L'] = pd.to_datetime(df_loyalty['Date'].dt.date)
                daily_counts = df_loyalty.groupby(['Day_L', 'Loyalty_Category']).size().reset_index(name='Count')
                fig_daily, ax_daily = plt.subplots(figsize=(8, 5))
                sns.barplot(data=daily_counts, x='Day_L', y='Count', hue='Loyalty_Category', ax=ax_daily)
                plt.xticks(rotation=45)
                st.pyplot(fig_daily)
else:
    st.info("Please upload your rk.csv file to begin.")
