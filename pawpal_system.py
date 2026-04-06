from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime

# Logic layer: all classes, scheduling algorithms, and business rules for PawPal+.


class PetType(Enum):
    DOG = "dog"
    CAT = "cat"
    RABBIT = "rabbit"
    BIRD = "bird"


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    def weight(self) -> int:
        """Return a numeric weight for sorting; higher number means higher priority."""
        return {Priority.HIGH: 3, Priority.MEDIUM: 2, Priority.LOW: 1}[self]


class TimeSlot(Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    ANY = "any"


class Recurrence(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    AS_NEEDED = "as_needed"


# Default task durations (minutes) by species and keyword.
SPECIES_DURATION_DEFAULTS: Dict[PetType, Dict[str, int]] = {
    PetType.DOG:    {"walk": 30, "feeding": 10, "grooming": 20, "training": 15, "playtime": 20, "meds": 5},
    PetType.CAT:    {"feeding": 5, "grooming": 15, "litter": 10, "playtime": 10, "meds": 5},
    PetType.RABBIT: {"feeding": 10, "grooming": 15, "playtime": 20, "cage": 20, "meds": 5},
    PetType.BIRD:   {"feeding": 5, "cage": 15, "socialization": 10, "meds": 5},
}


def suggest_duration(pet_type: PetType, description: str) -> Optional[int]:
    """Return a suggested duration in minutes based on species and task description keyword match."""
    defaults = SPECIES_DURATION_DEFAULTS.get(pet_type, {})
    desc_lower = description.lower()
    for keyword, minutes in defaults.items():
        if keyword in desc_lower:
            return minutes
    return None


@dataclass
class Owner:
    name: str
    available_minutes: int  # total daily time — kept for backward compatibility
    time_per_slot: Dict[str, int] = field(
        default_factory=lambda: {"morning": 40, "afternoon": 40, "evening": 40}
    )
    preferences: dict = field(default_factory=dict)

    def set_available_time(self, minutes: int) -> None:
        """Set total available time and distribute evenly across the three slots."""
        if minutes < 0:
            raise ValueError("Available time cannot be negative.")
        self.available_minutes = minutes
        per_slot = minutes // 3
        self.time_per_slot = {
            "morning": per_slot,
            "afternoon": per_slot,
            "evening": minutes - 2 * per_slot,  # remainder goes to evening
        }

    def set_slot_time(self, slot: str, minutes: int) -> None:
        """Set available time for a specific slot and update the total."""
        if slot not in self.time_per_slot:
            raise ValueError(f"Unknown slot '{slot}'. Use morning, afternoon, or evening.")
        if minutes < 0:
            raise ValueError("Slot time cannot be negative.")
        self.time_per_slot[slot] = minutes
        self.available_minutes = sum(self.time_per_slot.values())

    def add_preference(self, key: str, value: str) -> None:
        """Store a scheduling preference as a key-value pair."""
        self.preferences[key] = value


@dataclass
class Pet:
    name: str
    pet_type: PetType
    age: int
    owner: Owner
    hunger_level: int = 5   # 0-10 scale
    happiness_level: int = 5
    energy_level: int = 5

    def _clamp(self, value: int) -> int:
        """Clamp a value to the valid 0-10 range."""
        return max(0, min(10, value))

    def feed(self) -> None:
        """Decrease hunger by 3 and increase happiness by 1, clamped to 0-10."""
        self.hunger_level = self._clamp(self.hunger_level - 3)
        self.happiness_level = self._clamp(self.happiness_level + 1)

    def play(self) -> None:
        """Increase happiness by 2 and decrease energy by 2, clamped to 0-10."""
        self.happiness_level = self._clamp(self.happiness_level + 2)
        self.energy_level = self._clamp(self.energy_level - 2)

    def sleep(self) -> None:
        """Restore energy by 4, clamped to a maximum of 10."""
        self.energy_level = self._clamp(self.energy_level + 4)

    def get_status(self) -> str:
        """Return a formatted one-line summary of the pet's current state."""
        return (
            f"{self.name} ({self.pet_type.value}, age {self.age}) | "
            f"Hunger: {self.hunger_level}/10 | "
            f"Happiness: {self.happiness_level}/10 | "
            f"Energy: {self.energy_level}/10"
        )


@dataclass
class Task:
    task_id: str
    description: str
    pet: Pet
    due_date: datetime
    duration_minutes: int
    priority: Priority
    is_completed: bool = False
    time_slot: TimeSlot = TimeSlot.ANY
    recurrence: Recurrence = Recurrence.AS_NEEDED
    dependencies: List[str] = field(default_factory=list)  # list of task_ids
    is_required: bool = False
    carry_over: bool = False

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.is_completed = True

    def mark_incomplete(self) -> None:
        """Mark this task as not completed."""
        self.is_completed = False

    def update_due_date(self, new_date: datetime) -> None:
        """Replace the task's due date with a new datetime."""
        self.due_date = new_date

    def to_dict(self) -> dict:
        """Serialize the task to a plain dictionary suitable for display or storage."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "pet": self.pet.name,
            "due_date": self.due_date.isoformat(),
            "duration_minutes": self.duration_minutes,
            "priority": self.priority.value,
            "time_slot": self.time_slot.value,
            "recurrence": self.recurrence.value,
            "is_required": self.is_required,
            "is_completed": self.is_completed,
            "carry_over": self.carry_over,
        }


@dataclass
class Scheduler:
    tasks: List[Task] = field(default_factory=list)
    available_minutes: int = 0
    time_per_slot: Dict[str, int] = field(
        default_factory=lambda: {"morning": 0, "afternoon": 0, "evening": 0}
    )
    pet: Optional[Pet] = None

    def add_task(self, task: Task) -> None:
        """Add a task to the scheduler's task list."""
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        """Remove a task from the scheduler by its task_id."""
        self.tasks = [t for t in self.tasks if t.task_id != task_id]

    def _state_adjusted_weight(self, task: Task) -> int:
        """
        Return priority weight boosted by pet state.
        Feeding tasks are boosted when hunger >= 8.
        Rest/sleep tasks are boosted when energy <= 2.
        """
        weight = task.priority.weight()
        if self.pet:
            if self.pet.hunger_level >= 8 and any(
                w in task.description.lower() for w in ["feed", "food", "meal"]
            ):
                weight += 2
            if self.pet.energy_level <= 2 and any(
                w in task.description.lower() for w in ["sleep", "rest", "nap"]
            ):
                weight += 2
        return weight

    def _knapsack(self, tasks: List[Task], capacity: int) -> List[Task]:
        """
        0/1 knapsack: select the combination of tasks that maximises total
        priority weight without exceeding the time capacity.
        Falls back to an empty list when capacity is 0 or no tasks are given.
        """
        n = len(tasks)
        if n == 0 or capacity <= 0:
            return []

        dp = [[0] * (capacity + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            task = tasks[i - 1]
            w = self._state_adjusted_weight(task)
            d = task.duration_minutes
            for c in range(capacity + 1):
                dp[i][c] = dp[i - 1][c]
                if d <= c:
                    dp[i][c] = max(dp[i][c], dp[i - 1][c - d] + w)

        # Backtrack to find which tasks were selected
        selected, c = [], capacity
        for i in range(n, 0, -1):
            if dp[i][c] != dp[i - 1][c]:
                selected.append(tasks[i - 1])
                c -= tasks[i - 1].duration_minutes
        return selected

    def _resolve_dependencies(self, plan: List[Task]) -> List[Task]:
        """
        Topological sort: ensure dependency tasks appear before the tasks
        that depend on them. Silently skips missing or circular dependencies.
        """
        task_map = {t.task_id: t for t in self.tasks}
        ordered, visited = [], set()

        def visit(task: Task) -> None:
            if task.task_id in visited:
                return
            visited.add(task.task_id)
            for dep_id in task.dependencies:
                dep = task_map.get(dep_id)
                if dep and dep in plan:
                    visit(dep)
            ordered.append(task)

        for task in plan:
            visit(task)
        return ordered

    def generate_plan(self) -> Dict[str, List[Task]]:
        """
        Build a daily plan organised by time slot.
        Each slot is filled using the 0/1 knapsack algorithm against that
        slot's time budget. Tasks marked ANY are distributed round-robin
        across slots. Dependencies are resolved with a topological sort.
        """
        incomplete = [t for t in self.tasks if not t.is_completed]

        # Bucket tasks into their target slot
        slot_buckets: Dict[str, List[Task]] = {
            "morning": [], "afternoon": [], "evening": []
        }
        any_tasks: List[Task] = []
        for task in incomplete:
            if task.time_slot == TimeSlot.ANY:
                any_tasks.append(task)
            else:
                slot_buckets[task.time_slot.value].append(task)

        # Distribute ANY tasks round-robin
        slot_keys = list(slot_buckets.keys())
        for i, task in enumerate(any_tasks):
            slot_buckets[slot_keys[i % len(slot_keys)]].append(task)

        plan: Dict[str, List[Task]] = {}
        for slot_name, bucket in slot_buckets.items():
            capacity = self.time_per_slot.get(slot_name, self.available_minutes // 3)
            selected = self._knapsack(bucket, capacity)
            plan[slot_name] = self._resolve_dependencies(selected)

        return plan

    def get_carry_over_tasks(self) -> List[Task]:
        """Return incomplete tasks that were not scheduled in any slot."""
        plan = self.generate_plan()
        scheduled_ids = {t.task_id for tasks in plan.values() for t in tasks}
        return [t for t in self.tasks if not t.is_completed and t.task_id not in scheduled_ids]

    def detect_conflicts(self) -> List[str]:
        """
        Return a list of warning strings for:
        - total duration exceeding available time
        - tasks with missing dependencies
        - required tasks that could not be scheduled
        """
        warnings = []

        total = sum(t.duration_minutes for t in self.tasks if not t.is_completed)
        if total > self.available_minutes:
            warnings.append(
                f"Total task time ({total} min) exceeds available time ({self.available_minutes} min)."
            )

        task_ids = {t.task_id for t in self.tasks}
        for task in self.tasks:
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    warnings.append(
                        f"'{task.description}' depends on unknown task id '{dep_id}'."
                    )

        plan = self.generate_plan()
        scheduled_ids = {t.task_id for tasks in plan.values() for t in tasks}
        for task in self.tasks:
            if task.is_required and not task.is_completed and task.task_id not in scheduled_ids:
                warnings.append(
                    f"Required task '{task.description}' could not be scheduled — consider reducing other task durations."
                )

        return warnings

    def explain_plan(self) -> str:
        """
        Return a human-readable explanation of the full day's plan including
        per-slot breakdowns, conflict warnings, and carry-over tasks.
        """
        plan = self.generate_plan()
        conflicts = self.detect_conflicts()
        carry_over = self.get_carry_over_tasks()
        pet_label = self.pet.name if self.pet else "pet"

        lines = [f"Daily plan for {pet_label}:\n"]

        if conflicts:
            lines.append("Conflicts / warnings:")
            for c in conflicts:
                lines.append(f"  ! {c}")
            lines.append("")

        total_scheduled = sum(len(tasks) for tasks in plan.values())
        if total_scheduled == 0:
            return "No tasks could be scheduled within the available time."

        for slot_name, tasks in plan.items():
            capacity = self.time_per_slot.get(slot_name, self.available_minutes // 3)
            used = sum(t.duration_minutes for t in tasks)
            lines.append(f"{slot_name.upper()} ({used}/{capacity} min):")
            if tasks:
                for task in tasks:
                    tags = f"[{task.priority.value.upper()}]"
                    if task.is_required:
                        tags += "[REQUIRED]"
                    if task.recurrence != Recurrence.AS_NEEDED:
                        tags += f"[{task.recurrence.value}]"
                    if task.carry_over:
                        tags += "[carry-over]"
                    lines.append(f"  ✔ {tags} {task.description} ({task.duration_minutes} min)")
            else:
                lines.append("  (no tasks scheduled)")
            lines.append("")

        if carry_over:
            lines.append("Carried over to tomorrow:")
            for task in carry_over:
                lines.append(f"  ↪ [{task.priority.value.upper()}] {task.description} ({task.duration_minutes} min)")

        return "\n".join(lines)


class PawPalSystem:
    def __init__(self) -> None:
        """Initialize the system with empty pet and task lists and no active scheduler."""
        self.pets: List[Pet] = []
        self.tasks: List[Task] = []
        self.scheduler: Optional[Scheduler] = None

    def add_pet(self, pet: Pet) -> None:
        """Register a new pet in the system."""
        self.pets.append(pet)

    def remove_pet(self, pet_name: str) -> None:
        """Remove a pet and all of its associated tasks from the system."""
        self.pets = [p for p in self.pets if p.name != pet_name]
        self.tasks = [t for t in self.tasks if t.pet.name != pet_name]

    def get_pet(self, pet_name: str) -> Optional[Pet]:
        """Return the Pet with the given name, or None if not found."""
        for pet in self.pets:
            if pet.name == pet_name:
                return pet
        return None

    def get_all_pets(self) -> List[Pet]:
        """Return a copy of the list of all registered pets."""
        return list(self.pets)

    def add_task(self, task: Task) -> None:
        """Add a care task to the system."""
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        """Remove a task from the system by its task_id."""
        self.tasks = [t for t in self.tasks if t.task_id != task_id]

    def get_all_tasks(self) -> List[Task]:
        """Return a copy of the list of all tasks across all pets."""
        return list(self.tasks)

    def get_pet_tasks(self, pet_name: str) -> List[Task]:
        """Return all tasks associated with the pet matching pet_name."""
        return [t for t in self.tasks if t.pet.name == pet_name]

    def build_schedule(self, pet_name: str) -> Scheduler:
        """
        Create and return a Scheduler for the named pet, pre-loaded with
        that pet's tasks, time_per_slot, and available_minutes from the owner.
        Raises ValueError if no pet with that name exists.
        """
        pet = self.get_pet(pet_name)
        if pet is None:
            raise ValueError(f"No pet found with name '{pet_name}'.")
        scheduler = Scheduler(
            tasks=self.get_pet_tasks(pet_name),
            available_minutes=pet.owner.available_minutes,
            time_per_slot=dict(pet.owner.time_per_slot),
            pet=pet,
        )
        self.scheduler = scheduler
        return scheduler

    def update_pet_status(self, pet_name: str, hunger: int, happiness: int, energy: int) -> None:
        """
        Directly set a pet's hunger, happiness, and energy levels (all clamped to 0-10).
        Raises ValueError if no pet with that name exists.
        """
        pet = self.get_pet(pet_name)
        if pet is None:
            raise ValueError(f"No pet found with name '{pet_name}'.")
        pet.hunger_level = max(0, min(10, hunger))
        pet.happiness_level = max(0, min(10, happiness))
        pet.energy_level = max(0, min(10, energy))
