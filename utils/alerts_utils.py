from __future__ import annotations

from enterprise_data_quality_monitor.utils.logging_utils import get_logger


logger = get_logger(__name__)


def maybe_alert_on_low_score(
    score: float,
    threshold: float = 80.0,
) -> None:
    """Log a warning when the data quality score drops below threshold.

    This keeps the project lightweight and avoids external integrations.
    In a real deployment, this hook is where you'd plug in email/Slack/ops tools.
    """
    if score >= threshold:
        return

    subject = f"[Data Quality] Score below threshold: {score}"
    body = (
        f"Data quality score fell below threshold {threshold}.\n"
        f"Current score: {score}\n"
    )
    logger.warning("%s\n%s", subject, body)

