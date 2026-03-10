from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal, Optional

import plotly.express as px
import streamlit as st

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from enterprise_data_quality_monitor.config.snowflake_config import SnowflakeConfig
from enterprise_data_quality_monitor.pipeline.data_pipeline import run_pipeline
from enterprise_data_quality_monitor.warehouse.snowflake_client import fetch_dataframe


st.set_page_config(
    page_title="Enterprise Data Quality Monitor",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def _run_cached_pipeline(
    source: Literal["csv", "snowflake"],
    csv_path: Optional[str],
    snowflake_table: Optional[str],
    snowflake_summary_table: Optional[str],
) -> dict:
    if source == "csv":
        return run_pipeline(source="csv", csv_path=csv_path)

    config = SnowflakeConfig.from_env()
    return run_pipeline(
        source="snowflake",
        snowflake_config=config,
        snowflake_table=snowflake_table,
        snowflake_summary_table=snowflake_summary_table,
    )


def main() -> None:
    st.title("Enterprise Data Quality Monitor")
    st.markdown(
        "Monitor financial data quality, anomalies, and reconciliation results "
        "across your data warehouse."
    )

    with st.sidebar:
        st.header("Configuration")
        source = st.selectbox("Data Source", options=["csv", "snowflake"], index=0)

        csv_path: Optional[str] = None
        snowflake_table: Optional[str] = None
        snowflake_summary_table: Optional[str] = None

        if source == "csv":
            csv_path = st.text_input(
                "Transactions CSV path",
                value="data/financial_transactions.csv",
            )
            st.caption(
                "Tip: You can point this to Kaggle `Customer_Transactions.csv` too; "
                "the app will auto-adapt it into the required schema."
            )
        else:
            snowflake_table = st.text_input(
                "Snowflake transactions table (e.g., DB.SCHEMA.TRANSACTIONS)",
            )
            snowflake_summary_table = st.text_input(
                "Snowflake revenue summary table (optional)",
            )

        run_button = st.button("Run Pipeline")

    if not run_button:
        st.info("Configure parameters in the sidebar and click **Run Pipeline**.")
        return

    with st.spinner("Running data quality pipeline..."):
        results = _run_cached_pipeline(
            source=source,
            csv_path=csv_path,
            snowflake_table=snowflake_table,
            snowflake_summary_table=snowflake_summary_table,
        )

    dq_score = results["data_quality_score"]
    validation = results["validation"]
    analytics = results["analytics"]
    anomalies = results["anomalies"]
    reconciliation = results["reconciliation"]

    # KPI row
    kpi_cols = st.columns(5)
    kpi_cols[0].metric("Data Quality Score", dq_score["score"])
    kpi_cols[1].metric(
        "Missing Values (%)",
        dq_score["components"]["missing_percentage"],
    )
    kpi_cols[2].metric(
        "Duplicates (%)",
        dq_score["components"]["duplicate_percentage"],
    )
    kpi_cols[3].metric(
        "Anomalies",
        dq_score["components"]["anomaly_count"],
    )
    kpi_cols[4].metric(
        "Total Revenue / Spend",
        f"{analytics['total_revenue']:.2f}",
    )

    st.markdown("---")

    col_left, col_right = st.columns(2)

    # Left: data quality breakdown
    with col_left:
        st.subheader("Data Quality Breakdown")

        st.markdown("**Missing Values by Column**")
        missing_per_col = validation["missing"]["per_column_missing"]
        if missing_per_col:
            mv_df = (
                __import__("pandas")
                .DataFrame(
                    {
                        "column": list(missing_per_col.keys()),
                        "missing_percentage": list(missing_per_col.values()),
                    }
                )
                .sort_values("missing_percentage", ascending=False)
            )
            st.dataframe(mv_df, use_container_width=True)
        else:
            st.write("No missing value information available.")

        st.markdown("**Duplicate Rows**")
        st.write(
            f"Duplicate rows: {validation['duplicates']['duplicate_count']} "
            f"({validation['duplicates']['duplicate_percentage']:.2f}%)"
        )
        dup_df = validation["duplicates"]["duplicates"]
        if hasattr(dup_df, "head") and not dup_df.empty:
            st.dataframe(dup_df.head(10), use_container_width=True)
        else:
            st.write("No duplicate rows detected.")

    # Right: anomalies & reconciliation
    with col_right:
        st.subheader("Anomalies & Reconciliation")

        st.markdown("**Anomaly Alerts**")
        anomalies_df = anomalies["anomalies"]
        if hasattr(anomalies_df, "head") and not anomalies_df.empty:
            st.warning(f"{anomalies['anomaly_count']} anomalous transactions detected.")
            st.dataframe(anomalies_df.head(10), use_container_width=True)
        else:
            st.write("No anomalies detected.")

        st.markdown("**Revenue Reconciliation**")
        if reconciliation["has_reported_data"]:
            diff_flag = (
                "Within tolerance"
                if reconciliation["within_tolerance"]
                else "Outside tolerance"
            )
            st.write(
                f"Calculated revenue: {reconciliation['calculated_revenue']:.2f}  \n"
                f"Reported revenue: {reconciliation['reported_revenue']:.2f}  \n"
                f"Absolute difference: {reconciliation['absolute_difference']:.2f}  \n"
                f"Percentage difference: {reconciliation['percentage_difference']:.2f}%  \n"
                f"Status: **{diff_flag}**"
            )
        else:
            st.info("No reported revenue data available for reconciliation.")

    st.markdown("---")

    st.subheader("Revenue Analytics")
    daily_df = analytics["daily_revenue"]
    daily_forecast_df = analytics.get("daily_forecast")
    if not daily_df.empty:
        if daily_forecast_df is not None and not daily_forecast_df.empty:
            # Combine history and forecast for a single chart.
            hist = daily_df.copy()
            hist["kind"] = "actual"
            fc = daily_forecast_df.copy()
            fc.rename(columns={"forecast_total_revenue": "total_revenue"}, inplace=True)
            fc["kind"] = "forecast"
            combined = pd.concat([hist, fc], ignore_index=True)
            fig_daily = px.line(
                combined,
                x="date",
                y="total_revenue",
                color="kind",
                title="Daily Revenue (Actual vs Forecast)",
            )
        else:
            fig_daily = px.line(
                daily_df,
                x="date",
                y="total_revenue",
                title="Daily Revenue",
            )
        st.plotly_chart(fig_daily, use_container_width=True)

    region_df = analytics["revenue_by_region"]
    if not region_df.empty:
        fig_region = px.bar(
            region_df,
            x="region",
            y="total_revenue",
            title="Revenue by Region",
        )
        st.plotly_chart(fig_region, use_container_width=True)

    top_customers_df = analytics["top_customers"]
    if not top_customers_df.empty:
        fig_customers = px.bar(
            top_customers_df,
            x="customer_id",
            y="total_revenue",
            title="Top Customers by Revenue",
        )
        st.plotly_chart(fig_customers, use_container_width=True)

    # Snowflake-only: show latest automated metrics & feedback summary when available.
    if source == "snowflake":
        st.markdown("---")
        st.subheader("Automated Metrics & Feedback (Snowflake)")

        try:
            config = SnowflakeConfig.from_env()

            metrics_df = fetch_dataframe(
                config,
                """
                SELECT *
                FROM FINANCE_DB.PUBLIC.DATA_QUALITY_METRICS
                ORDER BY CREATED_AT DESC
                LIMIT 1
                """,
            )
            if not metrics_df.empty:
                row = metrics_df.iloc[0]
                m1, m2, m3 = st.columns(3)
                m1.metric(
                    "Total Customers (metrics table)",
                    int(row.get("total_customers", row.get("TOTAL_CUSTOMERS", 0))),
                )
                m2.metric(
                    "Avg Spend (metrics table)",
                    f"{float(row.get('avg_spend', row.get('AVG_SPEND', 0.0))):.2f}",
                )
                m3.metric(
                    "Missing Feedback (metrics table)",
                    int(row.get("missing_feedback", row.get("MISSING_FEEDBACK", 0))),
                )
            else:
                st.info(
                    "No rows in DATA_QUALITY_METRICS yet. "
                    "Run the REFRESH_DATA_QUALITY_METRICS procedure or wait for the task."
                )
        except Exception as exc:  # pragma: no cover - external dependency
            st.warning(f"Could not load automated metrics from Snowflake: {exc}")

        try:
            feedback_df = fetch_dataframe(
                config,
                """
                SELECT *
                FROM FINANCE_DB.PUBLIC.CUSTOMER_FEEDBACK_SUMMARY
                ORDER BY churn_rate DESC
                """,
            )
            if not feedback_df.empty:
                st.markdown("**Feedback & Churn by Country (Snowflake)**")
                st.dataframe(feedback_df, use_container_width=True)
        except Exception as exc:  # pragma: no cover - external dependency
            st.warning(f"Could not load feedback summary from Snowflake: {exc}")


if __name__ == "__main__":
    main()

