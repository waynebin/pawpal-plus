import pytest
from datetime import datetime
from pawpal_system import Owner, Pet, PetType, Task, Priority, Scheduler, PawPalSystem


# --- Fixtures ---

@pytest.fixture
def owner():
    return Owner(name="Alice", available_minutes=120)


@pytest.fixture
def dog(owner):
    return Pet(name="Buddy", pet_type=PetType.DOG, age=3, owner=owner)


@pytest.fixture
def today():
    return datetime.today()


# --- Task tests ---

def test_mark_complete_changes_task_status(dog, today):
    task = Task("t1", "Feed the dog", dog, today, duration_minutes=15, priority=Priority.HIGH)
    assert task.is_completed is False
    task.mark_complete()
    assert task.is_completed is True


def test_mark_incomplete_resets_task_status(dog, today):
    task = Task("t1", "Feed the dog", dog, today, duration_minutes=15, priority=Priority.HIGH)
    task.mark_complete()
    task.mark_incomplete()
    assert task.is_completed is False


def test_task_to_dict_contains_expected_keys(dog, today):
    task = Task("t1", "Morning walk", dog, today, duration_minutes=30, priority=Priority.MEDIUM)
    result = task.to_dict()
    assert result["task_id"] == "t1"
    assert result["description"] == "Morning walk"
    assert result["pet"] == "Buddy"
    assert result["duration_minutes"] == 30
    assert result["priority"] == "medium"


# --- Pet tests ---

def test_feed_reduces_hunger(dog):
    dog.hunger_level = 8
    dog.feed()
    assert dog.hunger_level == 5


def test_play_reduces_energy(dog):
    dog.energy_level = 6
    dog.play()
    assert dog.energy_level == 4


def test_sleep_restores_energy(dog):
    dog.energy_level = 3
    dog.sleep()
    assert dog.energy_level == 7


def test_pet_levels_do_not_exceed_bounds(dog):
    dog.hunger_level = 0
    dog.feed()  # would go to -3, should clamp to 0
    assert dog.hunger_level == 0

    dog.energy_level = 9
    dog.sleep()  # would go to 13, should clamp to 10
    assert dog.energy_level == 10


# --- Scheduler tests ---

def test_scheduler_generates_plan_within_time(dog, today):
    scheduler = Scheduler(available_minutes=60, pet=dog)
    scheduler.add_task(Task("t1", "Walk",     dog, today, duration_minutes=30, priority=Priority.HIGH))
    scheduler.add_task(Task("t2", "Grooming", dog, today, duration_minutes=20, priority=Priority.MEDIUM))
    scheduler.add_task(Task("t3", "Training", dog, today, duration_minutes=25, priority=Priority.LOW))

    plan = scheduler.generate_plan()
    total = sum(t.duration_minutes for t in plan)
    assert total <= 60


def test_scheduler_prioritizes_high_priority_tasks(dog, today):
    scheduler = Scheduler(available_minutes=30, pet=dog)
    scheduler.add_task(Task("t1", "Low task",  dog, today, duration_minutes=20, priority=Priority.LOW))
    scheduler.add_task(Task("t2", "High task", dog, today, duration_minutes=20, priority=Priority.HIGH))

    plan = scheduler.generate_plan()
    assert len(plan) == 1
    assert plan[0].task_id == "t2"


def test_scheduler_skips_completed_tasks(dog, today):
    scheduler = Scheduler(available_minutes=120, pet=dog)
    task = Task("t1", "Walk", dog, today, duration_minutes=30, priority=Priority.HIGH)
    task.mark_complete()
    scheduler.add_task(task)

    plan = scheduler.generate_plan()
    assert len(plan) == 0


def test_scheduler_remove_task(dog, today):
    scheduler = Scheduler(available_minutes=120, pet=dog)
    scheduler.add_task(Task("t1", "Walk", dog, today, duration_minutes=30, priority=Priority.HIGH))
    scheduler.remove_task("t1")
    assert len(scheduler.tasks) == 0


# --- PawPalSystem tests ---

def test_system_add_and_get_pet(dog):
    system = PawPalSystem()
    system.add_pet(dog)
    assert system.get_pet("Buddy") is dog


def test_system_remove_pet_also_removes_tasks(dog, today):
    system = PawPalSystem()
    system.add_pet(dog)
    system.add_task(Task("t1", "Walk", dog, today, duration_minutes=30, priority=Priority.HIGH))
    system.remove_pet("Buddy")
    assert system.get_pet("Buddy") is None
    assert len(system.get_all_tasks()) == 0


def test_system_build_schedule_uses_owner_time(dog, today):
    system = PawPalSystem()
    system.add_pet(dog)
    system.add_task(Task("t1", "Walk", dog, today, duration_minutes=30, priority=Priority.HIGH))
    scheduler = system.build_schedule("Buddy")
    assert scheduler.available_minutes == dog.owner.available_minutes


def test_system_build_schedule_raises_for_unknown_pet():
    system = PawPalSystem()
    with pytest.raises(ValueError):
        system.build_schedule("Ghost")
