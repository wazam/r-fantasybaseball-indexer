import logging

from app.db import init_db

logger = logging.getLogger(__name__)

# run with: pipenv run python -m app.init
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s %(message)s")
    logger.info("Initializing database.")
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
