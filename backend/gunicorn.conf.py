"""Gunicorn config for AIERP production deployment.

Run with:
    gunicorn -c gunicorn.conf.py app.main:app

Or override workers via env:
    WEB_CONCURRENCY=8 gunicorn -c gunicorn.conf.py app.main:app

Worker class: uvicorn.workers.UvicornWorker (ASGI, supports WebSocket).
"""
from __future__ import annotations

import multiprocessing
import os


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# Bind
host = os.getenv("WEB_HOST", "0.0.0.0")
port = _env_int("WEB_PORT", 8080)
bind = f"{host}:{port}"

# Worker processes
# Rule of thumb: 2 * CPU + 1 (capped by available memory)
cpu_count = multiprocessing.cpu_count()
_default_workers = min(2 * cpu_count + 1, 8)
workers = _env_int("WEB_CONCURRENCY", _default_workers)

# Worker class — async ASGI worker for FastAPI
worker_class = "uvicorn.workers.UvicornWorker"

# Threads per worker (FastAPI is async, so 1 is fine; 2-4 if sync deps creep in)
threads = _env_int("WEB_THREADS", 1)

# Worker lifecycle
timeout = _env_int("WEB_TIMEOUT", 60)
graceful_timeout = _env_int("WEB_GRACEFUL_TIMEOUT", 30)
keepalive = _env_int("WEB_KEEPALIVE", 5)

# Restart workers periodically to avoid memory leaks
max_requests = _env_int("WEB_MAX_REQUESTS", 10000)
max_requests_jitter = _env_int("WEB_MAX_REQUESTS_JITTER", 1000)

# Logging
accesslog = os.getenv("WEB_ACCESSLOG", "-")
errorlog = os.getenv("WEB_ERRORLOG", "-")
loglevel = os.getenv("WEB_LOGLEVEL", "info")
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s '
    '"%(f)s" "%(a)s" %(L)s'
)

# Process naming
proc_name = "aierp-web"

# Preload app for memory savings with multiple workers (no per-worker copy of code)
preload_app = True


# Lifecycle hooks
def on_starting(server) -> None:
    server.log.info(
        "AIERP gunicorn starting: workers=%d threads=%d worker_class=%s bind=%s",
        workers, threads, worker_class, bind,
    )


def post_fork(server, worker) -> None:
    server.log.info("AIERP worker %d spawned (pid=%d)", worker.age, worker.pid)


def worker_int(worker) -> None:
    worker.log.info("AIERP worker %d received SIGINT/SIGQUIT", worker.pid)


def worker_abort(worker) -> None:
    worker.log.warning("AIERP worker %d timed out and is being aborted", worker.pid)
