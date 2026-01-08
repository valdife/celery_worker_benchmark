import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if gevent pool is being used and apply monkey patching
# This must happen before importing any modules that use blocking I/O (like requests)
CELERY_POOL_TYPE = os.getenv("CELERY_POOL_TYPE", "prefork")
if CELERY_POOL_TYPE == "gevent":
    from gevent import monkey
    # Patch all standard library modules to be gevent-compatible
    # This makes blocking I/Odoc operations (like requests.get) cooperative
    logger.info("Applying gevent monkey patching for gevent worker pool")
    monkey.patch_all()
    logger.info("Gevent monkey patching completed - blocking I/O is now cooperative")

from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "benchmark",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=300,
)

import tasks

