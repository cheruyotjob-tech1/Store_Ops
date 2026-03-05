            # -----------------------------
            # Shopping Patterns by Day of Week
            # -----------------------------
            st.subheader("Loyal Customer Shopping Patterns by Day of the Week")

            df_loyalty['Day_of_Week'] = df_loyalty['Date'].dt.day_name()

            transactions_by_day = (
                df_loyalty.groupby('Day_of_Week')
                .size()
                .reset_index(name='Transaction_Count')
            )

            # Order days correctly
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

            plt.xticks(rotation=45, ha='right')
            ax_week.grid(axis='y', linestyle='--', alpha=0.7)

            plt.tight_layout()
            st.pyplot(fig_week)
