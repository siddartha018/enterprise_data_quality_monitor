"""Project root package marker.

This file ensures imports like `enterprise_data_quality_monitor.*` work reliably
when running Streamlit or Python from different working directories.
"""

"""
Enterprise Data Quality Monitor package.

This package provides utilities to extract financial data, validate data quality,
detect anomalies, reconcile financials, compute data quality scores, and expose
results via a Streamlit monitoring dashboard.
"""

from .pipeline.data_pipeline import run_pipeline  # noqa: F401

