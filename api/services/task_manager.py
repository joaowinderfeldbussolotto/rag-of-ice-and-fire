import uuid
from datetime import datetime
from typing import Dict, Optional
from api.models.schemas import TaskStatus, TaskResult, RAGResponse

class TaskManager:
    """Simple in-memory task manager for async operations"""
    
    def __init__(self):
        self.tasks: Dict[str, TaskResult] = {}
    
    def create_task(self) -> str:
        """Create a new task and return its ID"""
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = TaskResult(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        return task_id
    
    def update_task_status(self, task_id: str, status: TaskStatus):
        """Update task status"""
        if task_id in self.tasks:
            self.tasks[task_id].status = status
    
    def complete_task(self, task_id: str, result: RAGResponse):
        """Mark task as completed with result"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.COMPLETED
            self.tasks[task_id].result = result
            self.tasks[task_id].completed_at = datetime.now().isoformat()
    
    def fail_task(self, task_id: str, error: str):
        """Mark task as failed with error"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.FAILED
            self.tasks[task_id].result = RAGResponse(
                success=False,
                method="unknown",
                error=error
            )
            self.tasks[task_id].completed_at = datetime.now().isoformat()
    
    def get_task(self, task_id: str) -> Optional[TaskResult]:
        """Get task by ID"""
        return self.tasks.get(task_id)

# Global task manager instance
task_manager = TaskManager()
