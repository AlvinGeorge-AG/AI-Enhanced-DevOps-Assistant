import threading

# Shared across the FastAPI event loop and APScheduler's background thread.
# asyncio.Lock is loop-bound; threading.Lock is the correct primitive here.
_mutation_lock = threading.Lock()


class mutation_guard:
    """Context manager that serializes CRON health checks and Alertmanager webhooks."""

    def __enter__(self):
        _mutation_lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _mutation_lock.release()
        return False
