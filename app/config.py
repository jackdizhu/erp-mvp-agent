import os

APPROVAL_CONFIG = {
    "ttl_seconds": int(os.getenv("APPROVAL_TTL", "300")),
    "max_pending": int(os.getenv("APPROVAL_MAX_PENDING", "10")),
}

HISTORY_WINDOW = {
    "default_n": int(os.getenv("HISTORY_WINDOW_N", "6")),
}

SSE_CONFIG = {
    "ping_interval": int(os.getenv("SSE_PING_INTERVAL", "15")),
    "timeout_seconds": int(os.getenv("SSE_TIMEOUT", "60")),
    "max_chunk_size": int(os.getenv("SSE_MAX_CHUNK", "500")),
}
