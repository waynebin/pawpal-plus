from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
from datetime import datetime

# this will be the logic layer where all the classes and methods will be defined. This is where the main logic of the application will be implemented.

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


@dataclass
class Owner:
    name: str
    available_minutes: int  # total daily time available for pet care
    preferences: dict = field(default_factory=dict)

    def set_available_time(self, minutes: int) -> None:
        """Set the owner's daily available time in minutes. Raises ValueError if negative."""
        if minutes < 0:
            raise ValueError("Available time cannot be negative.")
        self.available_minutes = minutes

    def add_preference(self, key: str, value: str) -> None:
        """Store a scheduling preference as a key-value pair (e.g. 'morning_tasks': 'walk')."""
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
    pet: Pet                        # direct reference instead of pet_name string
    due_date: datetime
    duration_minutes: int           # required for scheduling
    priority: Priority              # required for scheduling
    is_completed: bool = False

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
            "is_completed": self.is_completed,
        }


@dataclass
class Scheduler:
    tasks: List[Task] = field(default_factory=list)
    available_minutes: int = 0
    pet: Optional[Pet] = None

    def add_task(self, task: Task) -> None:
        """Add a task to the scheduler's task list."""
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        """Remove a task from the scheduler by its task_id."""
        self.tasks = [t for t in self.tasks if t.task_id != task_id]

    def generate_plan(self) -> List[Task]:
        """
        Select and order incomplete tasks that fit within available_minutes.
        Tasks are sorted by priority (high first), then greedily added
        until the time budget is exhausted.
        Returns the list of scheduled tasks in priority order.
        """
        incomplete = [t for t in self.tasks if not t.is_completed]
        sorted_tasks = sorted(incomplete, key=lambda t: t.priority.weight(), reverse=True)

        plan = []
        time_used = 0
        for task in sorted_tasks:
            if time_used + task.duration_minutes <= self.available_minutes:
                plan.append(task)
                time_used += task.duration_minutes

        return plan

    def explain_plan(self) -> str:
        """
        Generate and return a human-readable explanation of today's plan.
        Shows scheduled tasks with their priority and duration, and lists
        any tasks that were skipped due to insufficient time.
        """
        plan = self.generate_plan()
        if not plan:
            return "No tasks could be scheduled within the available time."

        scheduled_ids = {t.task_id for t in plan}
        time_used = sum(t.duration_minutes for t in plan)
        lines = [f"Daily plan for {self.pet.name if self.pet else 'pet'} "
                 f"({time_used}/{self.available_minutes} minutes used):\n"]

        for task in plan:
            lines.append(f"  ✔ [{task.priority.value.upper()}] {task.description} ({task.duration_minutes} min)")

        skipped = [t for t in self.tasks if not t.is_completed and t.task_id not in scheduled_ids]
        if skipped:
            lines.append("\nSkipped (not enough time):")
            for task in skipped:
                lines.append(f"  ✘ [{task.priority.value.upper()}] {task.description} ({task.duration_minutes} min)")

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
        that pet's tasks and the owner's available_minutes.
        Raises ValueError if no pet with that name exists.
        """
        pet = self.get_pet(pet_name)
        if pet is None:
            raise ValueError(f"No pet found with name '{pet_name}'.")
        pet_tasks = self.get_pet_tasks(pet_name)
        scheduler = Scheduler(
            tasks=pet_tasks,
            available_minutes=pet.owner.available_minutes,
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
