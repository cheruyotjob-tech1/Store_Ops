import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Quickmart | Analytics Dashboard", layout="wide", page_icon="📊")

# --- CUSTOM QUICKMART STYLING ---
st.markdown("""
    <style>
        .main { background-color: #f5f7f9; }
        .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #e61e25; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
        h1, h2, h3 { color: #1e3d33; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .reportview-container .main .block-container { padding-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

# --- HEADER SECTION ---
col_logo, col_text = st.columns([1, 4])
with col_logo:
    # Using the provided image URL or local path
    st.image("https://i.imgur.com/39hN3rW.png", width=180) # Replace with local path if necessary
with col_text:
    st.title("Store Traffic & Till Performance Analytics")
    st.markdown("_Empowering Quickmart Fresh & Easy Decisions with Real-Time Data_")

st.divider()

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("📂 Data Integration: Upload your 'rk.csv' file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # --- DATA CLEANING ---
    cols_to_delete = list(range(0, 10)) + list(range(18, 22))
    df_cleaned = df.drop(df.columns[cols_to_delete], axis=1)
    new_names = ["Date", "Till", "Session", "Rct", "Customer", "Total", "Loyalty", "Cashier"]
    df_cleaned.columns = new_names

    df_cleaned['Date'] = pd.to_datetime(df_cleaned['Date'], dayfirst=True, errors='coerce')
    df_cleaned['Total'] = df_cleaned['Total'].astype(str).str.replace(',', '').astype(float)
    df_cleaned = df_cleaned.dropna(subset=['Date'])

    # --- SIDEBAR FILTERS ---
    st.sidebar.image("https://i.imgur.com/39hN3rW.png", width=150)
    st.sidebar.header("Control Panel")
    
    min_date = df_cleaned['Date'].min().date()
    max_date = df_cleaned['Date'].max().date()

    start_date = st.sidebar.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input("End Date", max_date, min_value=min_date, max_value=max_date)
    
    st.sidebar.markdown("---")
    start_hour = st.sidebar.slider("Shift Start (Hour)", 0, 23, 7)
    end_hour = st.sidebar.slider("Shift End (Hour)", 0, 23, 21)

    # --- FILTER LOGIC ---
    df_filtered = df_cleaned[
        (df_cleaned['Date'].dt.date >= start_date) &
        (df_cleaned['Date'].dt.date <= end_date)
    ].copy()

    df_time = df_filtered[
        (df_filtered['Date'].dt.hour >= start_hour) &
        (df_filtered['Date'].dt.hour <= end_hour)
    ].copy()

    if df_time.empty:
        st.warning("⚠️ No data matches the current filters. Please adjust the dates or hours.")
    else:
        # --- TOP KPI BAR ---
        total_rev = df_time['Total'].sum()
        total_trans = len(df_time)
        avg_basket = total_rev / total_trans if total_trans > 0 else 0
        loyal_pct = (len(df_time[df_time['Loyalty'] == 'þ']) / total_trans) * 100 if total_trans > 0 else 0

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Revenue", f"KSh {total_rev:,.0f}")
        kpi2.metric("Transactions", f"{total_trans:,}")
        kpi3.metric("Avg Basket", f"KSh {avg_basket:,.0f}")
        kpi4.metric("Loyalty %", f"{loyal_pct:.1f}%")

        # --- TABBED NAVIGATION ---
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 Traffic Trends", 
            "👥 Cashier Analysis", 
            "🔍 Customer Search", 
            "💎 Loyalty Insights"
        ])

        # --- TAB 1: TRAFFIC TRENDS ---
        with tab1:
            st.subheader("Store Traffic & Waiting Time Trends")
            df_time['Day'] = df_time['Date'].dt.date
            daily_metrics = df_time.groupby('Day').agg(
                Active_Tills=('Till', 'nunique'),
                Count=('Till', 'size')
            ).reset_index()
            
            duration = max((end_hour - start_hour + 1), 1)
            daily_metrics['Cust_Per_Hour'] = daily_metrics['Count'] / (daily_metrics['Active_Tills'] * duration)
            daily_metrics['Waiting_Time'] = (daily_metrics['Cust_Per_Hour'] * 10) / 40

            fig1, ax1 = plt.subplots(figsize=(14, 5))
            sns.lineplot(data=daily_metrics, x='Day', y='Active_Tills', label='Active Tills', marker='o', color='#006a4e', ax=ax1)
            sns.lineplot(data=daily_metrics, x='Day', y='Waiting_Time', label='Wait Time (Min)', linestyle='--', color='#e61e25', ax=ax1)
            ax1.set_title("Operational Efficiency Overview", fontsize=12)
            plt.xticks(rotation=45)
            st.pyplot(fig1)
            
            with st.expander("View Daily Data Table"):
                st.dataframe(daily_metrics.style.highlight_max(axis=0), use_container_width=True)

        # --- TAB 2: CASHIER PERFORMANCE ---
        with tab2:
            st.subheader("Comprehensive Cashier Performance")
            cash_counts = df_time.groupby('Cashier').size().reset_index(name='Transactions').sort_values('Transactions', ascending=False)
            
            fig_h = max(6, len(cash_counts) * 0.4)
            fig2, ax2 = plt.subplots(figsize=(12, fig_h))
            sns.barplot(x='Transactions', y='Cashier', data=cash_counts, palette='Greens_r', ax=ax2)
            ax2.set_title("Total Transactions by Staff Member")
            st.pyplot(fig2)

        # --- TAB 3: CUSTOMER SEARCH ---
        with tab3:
            st.subheader("Individual Shopping Pattern Discovery")
            available_cust = sorted(df_time['Customer'].dropna().unique().tolist())
            selected_customer = st.selectbox("Search Customer Database", options=available_customers if 'available_customers' in locals() else available_cust)
            
            c_data = df_time[df_time['Customer'] == selected_customer]
            if not c_data.empty:
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.write(f"### Profile: {selected_customer}")
                    st.write(f"**Preferred Till:** {c_data['Till'].mode()[0]}")
                    st.write(f"**Top Cashier:** {c_data['Cashier'].mode()[0]}")
                    st.write(f"**Total Visits:** {len(c_data)}")
                with c2:
                    fig3, ax3 = plt.subplots(figsize=(10, 4))
                    c_daily = c_data.groupby(c_data['Date'].dt.date)['Total'].sum().reset_index()
                    sns.barplot(data=c_daily, x='Date', y='Total', color='#006a4e', ax=ax3)
                    plt.xticks(rotation=45)
                    st.pyplot(fig3)

        # --- TAB 4: LOYALTY INSIGHTS ---
        with tab4:
            st.subheader("Loyalty Program Impact")
            df_loyalty = df_filtered[df_filtered['Loyalty'].isin(['þ', 'o'])].copy()
            df_loyalty['Category'] = df_loyalty['Loyalty'].map({'þ': 'Loyal', 'o': 'Standard'})
            
            avg_data = df_loyalty.groupby('Category')['Total'].mean().reset_index()
            overall = df_loyalty['Total'].mean()
            avg_data = pd.concat([avg_data, pd.DataFrame({'Category':['Average'], 'Total':[overall]})])

            fig4, ax4 = plt.subplots(figsize=(10, 6))
            colors = ['#006a4e', '#808080', '#e61e25']
            sns.barplot(x='Category', y='Total', data=avg_data, palette=colors, ax=ax4)
            for i, v in enumerate(avg_data['Total']):
                ax4.text(i, v + 2, f"{v:.1f}", ha='center', fontweight='bold')
            st.pyplot(fig4)

else:
    # --- LANDING PAGE STATE ---
    st.info("👋 Welcome to the Quickmart Analytics Portal.")
    st.markdown("""
        ### Instructions to get started:
        1.  **Prepare Data:** Ensure you have your `rk.csv` file ready.
        2.  **Upload:** Use the uploader above to ingest your store data.
        3.  **Analyze:** Use the tabs to toggle between Traffic, Staff, and Customer insights.
        4.  **Filter:** Adjust the sidebar to focus on specific dates or peak hours.
    """)
    st.image("https://i.imgur.com/39hN3rW.png", alpha=0.1) # Watermark
