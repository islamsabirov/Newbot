import logging
import structlog
from app.core.config import settings

def setup_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(level))

logger = structlog.get_logger()
