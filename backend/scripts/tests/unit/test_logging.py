import structlog

from app.main import log


def test_structlog_configuration():
    """Verify that logging system can print structured context without errors."""
    logger = structlog.get_logger()
    logger.info("test.logging_system_active", integration=True)
    # Verifies logger runs without raising configuration or format exceptions
    assert log is not None
