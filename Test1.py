import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Store Traffic Dashboard", layout="wide")

# Hide Streamlit header/menu
hide_streamlit_style = """
<style>
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("📊 Store Traffic & Till Performance Dashboard")

# Upload CSV
uploaded_file = st.file_uploader("Upload rk.csv file", type=["csv"])

if uploaded_file is not None:

    df = pd.read_csv(uploaded_file)

    # -------------------------
    # CLEAN DATA
    # -------------------------
    cols_to_delete = list(range(0,10)) + list(range(18,22))
    df_cleaned = df.drop(df.columns[cols_to_delete], axis=1)

    new_names = ["Date","Till","Session","Rct","Customer","Total","Loyalty","Cashier"]
    df_cleaned.columns = new_names

    df_cleaned["Date"] = pd.to_datetime(df_cleaned["Date"], dayfirst=True, errors="coerce")
    df_cleaned["Total"] = df_cleaned["Total"].astype(str).str.replace(",", "").astype(float)

    df_cleaned = df_cleaned.dropna(subset=["Date"])

    # -------------------------
    # SIDEBAR FILTERS
    # -------------------------
    min_date = df_cleaned["Date"].min().date()
    max_date = df_cleaned["Date"].max().date()

    st.sidebar.header("Filters")

    start_date = st.sidebar.date_input("Start Date", min_date)
    end_date = st.sidebar.date_input("End Date", max_date)

    start_hour = st.sidebar.slider("Start Hour",0,23,0)
    end_hour = st.sidebar.slider("End Hour",0,23,23)

    # -------------------------
    # FILTER DATA
    # -------------------------
    df_filtered = df_cleaned[
        (df_cleaned["Date"].dt.date >= start_date) &
        (df_cleaned["Date"].dt.date <= end_date)
    ].copy()

    if df_filtered.empty:
        st.warning("No data for selected date range")
        st.stop()

    df_filtered["Day"] = df_filtered["Date"].dt.date

    daily_max_tills = df_filtered.groupby("Day")["Till"].nunique().reset_index(name="Max_Tills")

    df_time = df_filtered[
        (df_filtered["Date"].dt.hour >= start_hour) &
        (df_filtered["Date"].dt.hour <= end_hour)
    ]

    daily_metrics = df_time.groupby("Day").agg(
        Average_Till_Number=("Till","mean"),
        Active_Tills=("Till","nunique"),
        Daily_Rows_Count=("Till","size")
    ).reset_index()

    duration = max((end_hour-start_hour+1),1)

    daily_metrics["Customers_Per_Till"] = (
        daily_metrics["Daily_Rows_Count"] /
        (daily_metrics["Active_Tills"] * duration)
    )

    daily_plot_df = pd.merge(daily_max_tills,daily_metrics,on="Day",how="left")

    daily_plot_df["Day"] = pd.to_datetime(daily_plot_df["Day"])

    daily_plot_df["Waiting_Time"] = (daily_plot_df["Customers_Per_Till"] * 10) / 50

    daily_plot_df["Customers_Per_Till"] = daily_plot_df["Customers_Per_Till"].round(2)
    daily_plot_df["Waiting_Time"] = daily_plot_df["Waiting_Time"].round(2)

    # -------------------------
    # TILL PERFORMANCE PLOT
    # -------------------------
    fig, ax = plt.subplots(figsize=(14,6))

    sns.lineplot(data=daily_plot_df,x="Day",y="Max_Tills",label="Max Tills",ax=ax)
    sns.lineplot(data=daily_plot_df,x="Day",y="Average_Till_Number",label="Average Till",ax=ax)
    sns.lineplot(data=daily_plot_df,x="Day",y="Active_Tills",label="Active Tills",ax=ax)
    sns.lineplot(data=daily_plot_df,x="Day",y="Customers_Per_Till",label="Customers per Till",ax=ax)
    sns.lineplot(data=daily_plot_df,x="Day",y="Waiting_Time",
                 label="Waiting Time (min)",linestyle="--",marker="o",ax=ax)

    ax.set_title(f"Daily Till Metrics ({start_hour}:00 - {end_hour}:00)")
    plt.xticks(rotation=45)
    ax.grid(True)

    st.pyplot(fig)

    # -------------------------
    # TABLE
    # -------------------------
    st.subheader("Daily Till Metrics Table")

    st.dataframe(daily_plot_df,use_container_width=True)

    # =========================
    # LOYAL CUSTOMER ANALYSIS
    # =========================

    st.subheader("⭐ Loyal Customer Analysis")

    df_loyal = df_filtered[df_filtered["Loyalty"]=="þ"].copy()

    if df_loyal.empty:
        st.info("No loyal customer data in selected range.")
        st.stop()

    # Metrics per customer
    customer_metrics = df_loyal.groupby("Customer").agg(
        Total_Spending=("Total","sum"),
        Transaction_Count=("Rct","count")
    ).reset_index()

    customer_metrics["Basket_Value"] = (
        customer_metrics["Total_Spending"] /
        customer_metrics["Transaction_Count"]
    )

    # Top loyal customers
    top_loyal_metrics_filtered = customer_metrics.sort_values(
        "Total_Spending",ascending=False
    ).head(10)

    # Transactions by day
    df_loyal["Day_of_Week"] = df_loyal["Date"].dt.day_name()

    transactions_by_day = df_loyal.groupby("Day_of_Week").size().reset_index(name="Transaction_Count")

    # Order days
    day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']

    transactions_by_day["Day_of_Week"] = pd.Categorical(
        transactions_by_day["Day_of_Week"],
        categories=day_order,
        ordered=True
    )

    transactions_by_day = transactions_by_day.sort_values("Day_of_Week")

    # -------------------------
    # YOUR 2 PLOTS
    # -------------------------

    fig, axes = plt.subplots(2,1,figsize=(14,16))

    fig.suptitle("Selected Loyal Customer Analysis with Detailed Metrics",fontsize=20)

    # Plot 1
    sns.barplot(
        ax=axes[0],
        x="Total_Spending",
        y="Customer",
        data=top_loyal_metrics_filtered,
        palette="magma"
    )

    axes[0].set_title("Total Loyal Customers by Total Spending")

    for index,row in top_loyal_metrics_filtered.iterrows():

        text = (
            f"Total: {row['Total_Spending']:,.2f}\n"
            f"BV: {row['Basket_Value']:,.2f}\n"
            f"Freq: {row['Transaction_Count']}"
        )

        axes[0].text(row["Total_Spending"],index,text,va="center")

    axes[0].grid(True)

    # Plot 2
    sns.barplot(
        ax=axes[1],
        x="Transaction_Count",
        y="Day_of_Week",
        data=transactions_by_day,
        palette="cubehelix"
    )

    axes[1].set_title("Loyal Customer Shopping Patterns by Day")

    for index,row in transactions_by_day.iterrows():

        axes[1].text(row["Transaction_Count"],index,row["Transaction_Count"])

    axes[1].grid(True)

    plt.tight_layout()

    st.pyplot(fig)

else:

    st.info("Upload rk.csv to start analysis")
