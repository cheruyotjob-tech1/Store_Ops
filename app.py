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
        ax.grid(True, which='major', linestyle='-', linewidth=1.0, alpha=0.7, color='gray')
        st.pyplot(fig)


        # -----------------------------
        # NEW: Specific Customer Pattern Search (Streamlit Version)
        # -----------------------------
        st.divider()
        st.subheader("🔍 Individual Customer Pattern Search")
        
        # Get unique customers from the filtered dataset
        available_customers = sorted(df_time['Customer'].dropna().unique().tolist())
        
        if available_customers:
            selected_customer = st.selectbox("Select or Type Customer Name", options=available_customers)
            
            cust_pattern = df_time[df_time['Customer'] == selected_customer].copy()
            
            if not cust_pattern.empty:
                c_col1, c_col2, c_col3 = st.columns(3)
                with c_col1:
                    st.metric("Total Transactions", len(cust_pattern))
                with c_col2:
                    st.metric("Total Spend", f"{cust_pattern['Total'].sum():,.2f}")
                with c_col3:
                    st.metric("Avg Basket", f"{cust_pattern['Total'].mean():,.2f}")
                
                # Visualizing customer's shopping dates
                fig_cust_search, ax_cust_search = plt.subplots(figsize=(12, 4))
                cust_daily = cust_pattern.groupby(cust_pattern['Date'].dt.date)['Total'].sum().reset_index()
                sns.barplot(data=cust_daily, x='Date', y='Total', palette='viridis', ax=ax_cust_search)
                plt.xticks(rotation=45)
                ax_cust_search.set_title(f"Spending Timeline for {selected_customer}")
                st.pyplot(fig_cust_search)
                
                # Show favorite Till and favorite Cashier
                fav_till = cust_pattern['Till'].mode()[0]
                fav_cashier = cust_pattern['Cashier'].mode()[0]
                st.write(f"💡 **Insights:** Typically shops at **Till {fav_till}** and served by **{fav_cashier}**.")
            else:
                st.info("No data found for this specific customer in the filtered time.")
        else:
            st.info("No customers found for the selected date/hour range.")

        # -----------------------------
        # Cashier Performance Metrics
        # -----------------------------
        st.divider()
        st.subheader("Cashier Performance Analysis")

        if not df_time.empty:
            cash_counts = df_time.groupby('Cashier').size().reset_index(name='Transaction_Count').sort_values('Transaction_Count', ascending=False)
            loyalty_counts = df_time.groupby(['Cashier', 'Loyalty']).size().reset_index(name='Loyalty_Transaction_Count')
            unique_tills = df_time.groupby('Cashier')['Till'].nunique().reset_index(name='Unique_Tills_Count')

            fig_height = max(8, len(cash_counts) * 0.4)
            fig_cash, axes_cash = plt.subplots(1, 3, figsize=(24, fig_height))
            sns.barplot(x='Transaction_Count', y='Cashier', data=cash_counts, ax=axes_cash[0], palette='viridis')
            axes_cash[0].set_title('Transactions per Cashier')

            loyalty_f = loyalty_counts.copy()
            loyalty_f['Loyalty'] = pd.Categorical(loyalty_f['Loyalty'], categories=['o', 'þ'])
            order = cash_counts['Cashier'].tolist()
            sns.barplot(x='Loyalty_Transaction_Count', y='Cashier', hue='Loyalty', data=loyalty_f, ax=axes_cash[1], palette={'o': 'salmon', 'þ': 'skyblue'}, order=order)
            axes_cash[1].set_title('Loyalty Breakdown')
            axes_cash[1].legend(title='Loyalty Type')

            tills_f = unique_tills.sort_values('Unique_Tills_Count', ascending=False)
            sns.barplot(x='Unique_Tills_Count', y='Cashier', data=tills_f, ax=axes_cash[2], palette='mako', order=order)
            axes_cash[2].set_title('Unique Tills Used')

            plt.tight_layout()
            st.pyplot(fig_cash)

        # -----------------------------
        # Top Customer Analysis
        # -----------------------------
        st.divider()
        st.subheader("🏆 Top Customer Ranking")
        if not df_time.empty:
            cust_df = df_time[~df_time['Customer'].isin(['<Customer Name>', 'CASH'])].groupby('Customer').agg(
                Total_Spend=('Total', 'sum'),
                Frequency=('Rct', 'count')
            ).reset_index()
            cust_df['Avg_Basket'] = (cust_df['Total_Spend'] / cust_df['Frequency']).round(2)
            fig_cust, axes_cust = plt.subplots(1, 3, figsize=(24, 8))
            top_s = cust_df.sort_values('Total_Spend', ascending=False).head(10)
            sns.barplot(x='Customer', y='Total_Spend', data=top_s, ax=axes_cust[0], palette='crest')
            axes_cust[0].set_title('Top 10 by Total Spend')
            axes_cust[0].tick_params(axis='x', rotation=45)
            top_f = cust_df.sort_values('Frequency', ascending=False).head(10)
            sns.barplot(x='Customer', y='Frequency', data=top_f, ax=axes_cust[1], palette='flare')
            axes_cust[1].set_title('Top 10 by Frequency')
            axes_cust[1].tick_params(axis='x', rotation=45)
            top_b = cust_df.sort_values('Avg_Basket', ascending=False).head(10)
            sns.barplot(x='Customer', y='Avg_Basket', data=top_b, ax=axes_cust[2], palette='magma')
            axes_cust[2].set_title('Top 10 by Avg Basket')
            axes_cust[2].tick_params(axis='x', rotation=45)
            plt.tight_layout()
            st.pyplot(fig_cust)

        # -----------------------------
        # Loyalty Customer Insights
        # -----------------------------
        st.divider()
        st.subheader("💎 Loyalty Customer Insights")
        df_loyalty = df_filtered[df_filtered['Loyalty'].isin(['þ', 'o'])].copy()
        if not df_loyalty.empty:
            df_loyalty['Loyalty_Category'] = df_loyalty['Loyalty'].map({'þ': 'Loyal', 'o': 'Non-Loyal'})
            avg_loyal = df_loyalty[df_loyalty['Loyalty_Category'] == 'Loyal']['Total'].mean()
            avg_non = df_loyalty[df_loyalty['Loyalty_Category'] == 'Non-Loyal']['Total'].mean()
            overall_avg = df_loyalty['Total'].mean()
            l_plot_data = pd.DataFrame({
                'Category': ['Loyal Customers', 'Non-Loyal Customers', 'Overall Average'],
                'Average_Spending': [avg_loyal, avg_non, overall_avg]
            })
            col1, col2 = st.columns(2)
            with col1:
                fig_l_bar, ax_l_bar = plt.subplots(figsize=(8, 6))
                sns.barplot(x='Category', y='Average_Spending', data=l_plot_data, palette='viridis', ax=ax_l_bar)
                ax_l_bar.set_title('Average Spending by Loyalty Category', fontsize=14)
                for i, v in enumerate(l_plot_data['Average_Spending']):
                    ax_l_bar.text(i, v + (v * 0.02), f"{v:.2f}", ha='center', fontweight='bold')
                st.pyplot(fig_l_bar)
            with col2:
                df_loyalty['Day_Plot'] = pd.to_datetime(df_loyalty['Date'].dt.date)
                daily_counts = df_loyalty.groupby(['Day_Plot', 'Loyalty_Category']).size().reset_index(name='Count')
                fig_l_daily, ax_l_daily = plt.subplots(figsize=(8, 6))
                sns.barplot(data=daily_counts, x='Day_Plot', y='Count', hue='Loyalty_Category', ax=ax_l_daily)
                plt.xticks(rotation=45)
                st.pyplot(fig_l_daily)
else:
    st.info("Please upload your rk.csv file to begin.")

