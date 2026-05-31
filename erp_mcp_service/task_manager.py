import uuid
import time
import threading
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class TaskState:
    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    ttl: int = 60000
    _cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)

    @property
    def is_expired(self) -> bool:
        elapsed_ms = (time.time() - self.created_at) * 1000
        return elapsed_ms > self.ttl

    @property
    def is_canceled(self) -> bool:
        return self._cancel_event.is_set()


class TaskManager:
    def __init__(self):
        self._tasks: Dict[str, TaskState] = {}
        self._lock = threading.Lock()

    def create_task(self, ttl: int = 60000) -> TaskState:
        task_id = str(uuid.uuid4())
        task = TaskState(
            task_id=task_id,
            status="working",
            ttl=ttl,
        )
        with self._lock:
            self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[TaskState]:
        with self._lock:
            task = self._tasks.get(task_id)
        if task and task.is_expired:
            self._remove_task(task_id)
            return None
        return task

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self.get_task(task_id)
        if not task:
            return None
        result = {
            "taskId": task.task_id,
            "status": task.status,
        }
        if task.progress:
            result["progress"] = task.progress
        return result

    def update_progress(self, task_id: str, progress: Dict[str, Any]) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status != "working":
                return False
            task.progress = progress
        return True

    def complete_task(self, task_id: str, result: Any) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status != "working":
                return False
            task.status = "completed"
            task.result = result
        return True

    def fail_task(self, task_id: str, error: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status != "working":
                return False
            task.status = "failed"
            task.error = error
        return True

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status != "working":
                return False
            task.status = "canceled"
            task._cancel_event.set()
        return True

    def list_tasks(self) -> List[Dict[str, Any]]:
        self._cleanup_expired()
        with self._lock:
            return [
                {
                    "taskId": t.task_id,
                    "status": t.status,
                    "progress": t.progress,
                }
                for t in self._tasks.values()
            ]

    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self.get_task(task_id)
        if not task:
            return None
        if task.status == "completed":
            return {
                "taskId": task.task_id,
                "status": "completed",
                "result": task.result,
            }
        if task.status == "failed":
            return {
                "taskId": task.task_id,
                "status": "failed",
                "error": task.error,
            }
        return {
            "taskId": task.task_id,
            "status": task.status,
        }

    def _remove_task(self, task_id: str) -> None:
        with self._lock:
            self._tasks.pop(task_id, None)

    def _cleanup_expired(self) -> None:
        with self._lock:
            expired = [
                tid for tid, t in self._tasks.items() if t.is_expired
            ]
            for tid in expired:
                del self._tasks[tid]


task_manager = TaskManager()
