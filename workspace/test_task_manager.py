import pytest
from task_manager import TaskManager, Task


def test_add_task_returns_correct_title():
    task_manager = TaskManager()
    task = task_manager.add_task("title for newly created task")
    assert task.title == "title for newly created task"

def test_add_task_return_correct_title_id():
    task_manager = TaskManager()
    task = task_manager.add_task("title for newly created task")
    assert task.task_id == 1

def test_add_task_return_corrrect_completed_field():
    task_manager = TaskManager()
    task = task_manager.add_task("title for newly created task")
    assert not task.completed

def test_complete_task_gets_completed_successfully():
    task_manager = TaskManager()
    task = task_manager.add_task("title for newly created task")
    task_manager.complete_task(1)
    assert task.completed

def test_complete_task_task_id_doesnt_exist():
    with pytest.raises(ValueError):
        task_manager = TaskManager()
        task_manager.complete_task(2)

def test_delete_task_removes_task():
    task_manager = TaskManager()
    task_manager.add_task("title for newly created task")
    task_manager.delete_task(1)
    assert len(task_manager.tasks) == 0

def test_delete_task_id_doesnt_exist():
    with pytest.raises(ValueError):
        task_manager = TaskManager()
        task_manager.delete_task(2)

def test_get_all_tasks_returns_task_list():
    task_manager = TaskManager()
    task_manager.add_task("title for newly created task")
    task_list = task_manager.get_all_tasks()
    assert len(task_list) == 1
    assert isinstance(task_list[0], Task)
    assert task_list[0].title == "title for newly created task"

def test_get_pending_tasks_returns_pending_tasks_only():
    task_manager = TaskManager()
    task_manager.add_task("title for newly created task 1")
    task_manager.add_task("title for newly created task 2")
    task_manager.add_task("title for newly created task 3")
    task_manager.complete_task(1)
    task_manager.complete_task(2)
    task_list = task_manager.get_pending_tasks()
    assert len(task_list) == 1
    assert isinstance(task_list[0], Task)
    assert task_list[0].title == "title for newly created task 3"