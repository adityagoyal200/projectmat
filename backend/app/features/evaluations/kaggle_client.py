import logging

logger = logging.getLogger(__name__)


async def fetch_kaggle_metrics(username: str) -> dict:
    """
    Fetch Kaggle metrics for a given username.
    Currently a stub that returns an empty dictionary.
    """
    logger.info(f"Stubbing Kaggle metrics fetch for {username}")
    return {}
