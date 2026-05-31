import uuid
import time
import asyncio
import threading
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from queue import Queue


PENDING_REQUEST_TTL = 60


@dataclass
class Session:
    session_id: str
    client_id: str = "anonymous"
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    message_queue: Queue = field(default_factory=Queue)
    sse_connections: List[Any] = field(default_factory=list)
    pending_requests: Dict[str, float] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def touch(self):
        self.last_activity = time.time()

    def enqueue_message(self, message: dict):
        self.message_queue.put(message)

    def dequeue_message(self, timeout: float = 1.0) -> Optional[dict]:
        try:
            return self.message_queue.get(timeout=timeout)
        except Exception:
            return None

    def add_sse_connection(self, conn: Any):
        with self._lock:
            self.sse_connections.append(conn)

    def remove_sse_connection(self, conn: Any):
        with self._lock:
            if conn in self.sse_connections:
                self.sse_connections.remove(conn)

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.last_activity) > 3600

    def track_request(self, request_id: str) -> None:
        with self._lock:
            self.pending_requests[request_id] = time.time()

    def complete_request(self, request_id: str) -> None:
        with self._lock:
            self.pending_requests.pop(request_id, None)

    def cleanup_pending_requests(self) -> None:
        now = time.time()
        with self._lock:
            expired_ids = [
                rid for rid, ts in self.pending_requests.items()
                if (now - ts) > PENDING_REQUEST_TTL
            ]
            for rid in expired_ids:
                del self.pending_requests[rid]


class SessionManager:
    def __init__(self, session_ttl: int = 3600, max_sessions: int = 1000):
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.Lock()
        self._session_ttl = session_ttl
        self._max_sessions = max_sessions

    def create_session(self, client_id: str = "anonymous") -> Session:
        session_id = str(uuid.uuid4())
        session = Session(session_id=session_id, client_id=client_id)
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        with self._lock:
            session = self._sessions.get(session_id)
        if session and session.is_expired:
            self.remove_session(session_id)
            return None
        if session:
            session.touch()
        return session

    def remove_session(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session:
            for conn in session.sse_connections:
                try:
                    conn.close()
                except Exception:
                    pass
        return session is not None

    def validate_session(self, session_id: str) -> bool:
        return self.get_session(session_id) is not None

    def broadcast_notification(self, message: dict, session_id: Optional[str] = None):
        with self._lock:
            sessions = [self._sessions[sid]] if session_id and sid in self._sessions else list(self._sessions.values())
        for s in sessions:
            s.enqueue_message(message)

    def cleanup_expired(self):
        with self._lock:
            expired = [sid for sid, s in self._sessions.items() if s.is_expired]
            for sid in expired:
                session = self._sessions.pop(sid)
                for conn in session.sse_connections:
                    try:
                        conn.close()
                    except Exception:
                        pass
            for session in self._sessions.values():
                session.cleanup_pending_requests()


session_manager = SessionManager()
