"""
This is a deliberately buggy version used by the eval harness.
"""
from dataclasses import dataclass


@dataclass
class Task:
    task_id: int
    title: str
    completed: bool = False

class TaskManager:
    def __init__(self):
        self.counter = 1
        self.tasks = dict()

    def add_task(self, title: str) -> Task:
        task = Task(self.counter, title)
        self.tasks[self.counter] = task
        self.counter += 1
        return task
    
    def complete_task(self, task_id: int) -> None:
        if task_id not in self.tasks:
            raise ValueError(f'Task with task id: {task_id} is not found')
        self.tasks[task_id].completed = True

    def delete_task(self, task_id: int) -> None:
        if task_id not in self.tasks:
            raise ValueError(f'Task with task id: {task_id} is not found')
        del self.tasks[task_id]

    def get_all_tasks(self) -> list[Task]:
        return list(self.tasks.values())
    
    def get_pending_tasks(self) -> list[Task]:
        return list(self.tasks.values())