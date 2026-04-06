import pytest
from datetime import datetime
from pawpal_system import (
    Owner, Pet, PetType, Task, Priority, TimeSlot, Recurrence,
    Scheduler, PawPalSystem, suggest_duration
)


# --- Fixtures ---

@pytest.fixture
def owner():
    return Owner(
        name="Alice",
        available_minutes=120,
        time_per_slot={"morning": 40, "afternoon": 40, "evening": 40},
    )


@pytest.fixture
def dog(owner):
    return Pet(name="Buddy", pet_type=PetType.DOG, age=3, owner=owner)


@pytest.fixture
def today():
    return datetime.today()


def make_task(task_id, desc, pet, today, duration, priority,
              slot=TimeSlot.ANY, recurrence=Recurrence.AS_NEEDED,
              is_required=False, deps=None):
    return Task(
        task_id=task_id,
        description=desc,
        pet=pet,
        due_date=today,
        duration_minutes=duration,
        priority=priority,
        time_slot=slot,
        recurrence=recurrence,
        is_required=is_required,
        dependencies=deps or [],
    )


# --- Task tests ---

def test_mark_complete_changes_task_status(dog, today):
    task = make_task("t1", "Feed the dog", dog, today, 15, Priority.HIGH)
    assert task.is_completed is False
    task.mark_complete()
    assert task.is_completed is True


def test_mark_incomplete_resets_task_status(dog, today):
    task = make_task("t1", "Feed the dog", dog, today, 15, Priority.HIGH)
    task.mark_complete()
    task.mark_incomplete()
    assert task.is_completed is False


def test_task_to_dict_contains_expected_keys(dog, today):
    task = make_task("t1", "Morning walk", dog, today, 30, Priority.MEDIUM)
    result = task.to_dict()
    assert result["task_id"] == "t1"
    assert result["description"] == "Morning walk"
    assert result["pet"] == "Buddy"
    assert result["duration_minutes"] == 30
    assert result["priority"] == "medium"
    assert "time_slot" in result
    assert "recurrence" in result
    assert "is_required" in result


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
    dog.feed()
    assert dog.hunger_level == 0

    dog.energy_level = 9
    dog.sleep()
    assert dog.energy_level == 10


# --- Owner slot time tests ---

def test_owner_set_available_time_distributes_evenly(owner):
    owner.set_available_time(120)
    assert owner.available_minutes == 120
    assert sum(owner.time_per_slot.values()) == 120


def test_owner_set_slot_time_updates_total(owner):
    owner.set_slot_time("morning", 60)
    assert owner.time_per_slot["morning"] == 60
    assert owner.available_minutes == sum(owner.time_per_slot.values())


def test_owner_set_slot_time_raises_for_unknown_slot(owner):
    with pytest.raises(ValueError):
        owner.set_slot_time("midnight", 30)


# --- Species duration suggestions ---

def test_suggest_duration_returns_hint_for_known_keyword():
    assert suggest_duration(PetType.DOG, "Morning walk") == 30


def test_suggest_duration_returns_none_for_unknown_keyword():
    assert suggest_duration(PetType.DOG, "Dentist appointment") is None


# --- Scheduler: knapsack ---

def test_knapsack_fits_within_capacity(dog, today):
    scheduler = Scheduler(available_minutes=60, time_per_slot={"morning": 60, "afternoon": 0, "evening": 0}, pet=dog)
    scheduler.add_task(make_task("t1", "Walk",     dog, today, 30, Priority.HIGH,   slot=TimeSlot.MORNING))
    scheduler.add_task(make_task("t2", "Grooming", dog, today, 20, Priority.MEDIUM, slot=TimeSlot.MORNING))
    scheduler.add_task(make_task("t3", "Training", dog, today, 25, Priority.LOW,    slot=TimeSlot.MORNING))
    plan = scheduler.generate_plan()
    total = sum(t.duration_minutes for t in plan["morning"])
    assert total <= 60


def test_knapsack_picks_better_combination_than_greedy(dog, today):
    # Greedy (high first) would pick t1 (weight 3, 35 min) and stop.
    # Knapsack should pick t2+t3 (weight 2+2=4, 30+10=40 min) — higher total weight.
    scheduler = Scheduler(available_minutes=40, time_per_slot={"morning": 40, "afternoon": 0, "evening": 0}, pet=dog)
    scheduler.add_task(make_task("t1", "Long high task",   dog, today, 35, Priority.HIGH,   slot=TimeSlot.MORNING))
    scheduler.add_task(make_task("t2", "Medium task A",    dog, today, 30, Priority.MEDIUM, slot=TimeSlot.MORNING))
    scheduler.add_task(make_task("t3", "Medium task B",    dog, today, 10, Priority.MEDIUM, slot=TimeSlot.MORNING))
    plan = scheduler.generate_plan()
    selected_ids = {t.task_id for t in plan["morning"]}
    assert "t2" in selected_ids
    assert "t3" in selected_ids
    assert "t1" not in selected_ids


def test_scheduler_skips_completed_tasks(dog, today):
    scheduler = Scheduler(available_minutes=120, time_per_slot={"morning": 120, "afternoon": 0, "evening": 0}, pet=dog)
    task = make_task("t1", "Walk", dog, today, 30, Priority.HIGH, slot=TimeSlot.MORNING)
    task.mark_complete()
    scheduler.add_task(task)
    plan = scheduler.generate_plan()
    assert len(plan["morning"]) == 0


# --- Scheduler: pet state-aware priority ---

def test_hungry_pet_boosts_feeding_task(dog, today):
    dog.hunger_level = 9
    scheduler = Scheduler(available_minutes=30, time_per_slot={"morning": 30, "afternoon": 0, "evening": 0}, pet=dog)
    # Feed task has LOW priority but should be boosted by hunger
    scheduler.add_task(make_task("t1", "Feed Buddy",  dog, today, 10, Priority.LOW,  slot=TimeSlot.MORNING))
    scheduler.add_task(make_task("t2", "High task",   dog, today, 25, Priority.HIGH, slot=TimeSlot.MORNING))
    plan = scheduler.generate_plan()
    selected_ids = {t.task_id for t in plan["morning"]}
    # Both fit (10+25=35 > 30), so only one can be chosen — feed should win after boost
    assert "t1" in selected_ids


def test_tired_pet_boosts_rest_task(dog, today):
    dog.energy_level = 1
    scheduler = Scheduler(available_minutes=20, time_per_slot={"morning": 0, "afternoon": 0, "evening": 20}, pet=dog)
    scheduler.add_task(make_task("t1", "Rest time",  dog, today, 15, Priority.LOW,    slot=TimeSlot.EVENING))
    scheduler.add_task(make_task("t2", "Playtime",   dog, today, 20, Priority.MEDIUM, slot=TimeSlot.EVENING))
    plan = scheduler.generate_plan()
    selected_ids = {t.task_id for t in plan["evening"]}
    assert "t1" in selected_ids


# --- Scheduler: dependencies ---

def test_dependency_task_comes_first(dog, today):
    scheduler = Scheduler(available_minutes=60, time_per_slot={"morning": 60, "afternoon": 0, "evening": 0}, pet=dog)
    scheduler.add_task(make_task("t1", "Bath",    dog, today, 20, Priority.MEDIUM, slot=TimeSlot.MORNING))
    scheduler.add_task(make_task("t2", "Groom",   dog, today, 15, Priority.HIGH,   slot=TimeSlot.MORNING, deps=["t1"]))
    plan = scheduler.generate_plan()
    ids = [t.task_id for t in plan["morning"]]
    assert ids.index("t1") < ids.index("t2")


# --- Scheduler: carry-over and conflicts ---

def test_carry_over_returns_unscheduled_tasks(dog, today):
    scheduler = Scheduler(available_minutes=20, time_per_slot={"morning": 20, "afternoon": 0, "evening": 0}, pet=dog)
    scheduler.add_task(make_task("t1", "Walk",     dog, today, 15, Priority.HIGH,   slot=TimeSlot.MORNING))
    scheduler.add_task(make_task("t2", "Training", dog, today, 30, Priority.MEDIUM, slot=TimeSlot.MORNING))
    carry = scheduler.get_carry_over_tasks()
    assert any(t.task_id == "t2" for t in carry)


def test_detect_conflicts_over_time(dog, today):
    scheduler = Scheduler(available_minutes=30, time_per_slot={"morning": 10, "afternoon": 10, "evening": 10}, pet=dog)
    scheduler.add_task(make_task("t1", "Walk",     dog, today, 20, Priority.HIGH,   slot=TimeSlot.MORNING))
    scheduler.add_task(make_task("t2", "Training", dog, today, 20, Priority.MEDIUM, slot=TimeSlot.MORNING))
    warnings = scheduler.detect_conflicts()
    assert any("exceeds" in w for w in warnings)


def test_detect_conflicts_required_task_not_scheduled(dog, today):
    scheduler = Scheduler(available_minutes=10, time_per_slot={"morning": 10, "afternoon": 0, "evening": 0}, pet=dog)
    scheduler.add_task(make_task("t1", "Meds", dog, today, 60, Priority.HIGH, slot=TimeSlot.MORNING, is_required=True))
    warnings = scheduler.detect_conflicts()
    assert any("Required" in w for w in warnings)


def test_detect_conflicts_missing_dependency(dog, today):
    scheduler = Scheduler(available_minutes=60, time_per_slot={"morning": 60, "afternoon": 0, "evening": 0}, pet=dog)
    scheduler.add_task(make_task("t2", "Groom", dog, today, 15, Priority.HIGH, slot=TimeSlot.MORNING, deps=["t_missing"]))
    warnings = scheduler.detect_conflicts()
    assert any("unknown task" in w for w in warnings)


# --- PawPalSystem tests ---

def test_system_add_and_get_pet(dog):
    system = PawPalSystem()
    system.add_pet(dog)
    assert system.get_pet("Buddy") is dog


def test_system_remove_pet_also_removes_tasks(dog, today):
    system = PawPalSystem()
    system.add_pet(dog)
    system.add_task(make_task("t1", "Walk", dog, today, 30, Priority.HIGH))
    system.remove_pet("Buddy")
    assert system.get_pet("Buddy") is None
    assert len(system.get_all_tasks()) == 0


def test_system_build_schedule_passes_slot_times(dog):
    system = PawPalSystem()
    system.add_pet(dog)
    scheduler = system.build_schedule("Buddy")
    assert scheduler.time_per_slot == dog.owner.time_per_slot


def test_system_build_schedule_raises_for_unknown_pet():
    system = PawPalSystem()
    with pytest.raises(ValueError):
        system.build_schedule("Ghost")
