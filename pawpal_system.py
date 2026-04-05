from dataclasses import dataclass
from typing import List
from enum import Enum
from datetime import datetime

# this will be the logic layer where all the classes and methods will be defined. This is where the main logic of the application will be implemented.  
class PetType(Enum):
    DOG = "dog"
    CAT = "cat"
    RABBIT = "rabbit"
    BIRD = "bird"

@dataclass
class Pet:
    name: str
    pet_type: PetType
    age: int
    hunger_level: int
    happiness_level: int
    energy_level: int
    
    def feed(self) -> None:
        pass
    
    def play(self) -> None:
        pass
    
    def sleep(self) -> None:
        pass
    
    def get_status(self) -> str:
        pass

@dataclass
class Task:
    task_id: str
    description: str
    pet_name: str
    due_date: datetime
    is_completed: bool
    
    def mark_complete(self) -> None:
        pass
    
    def mark_incomplete(self) -> None:
        pass
    
    def update_due_date(self, new_date: datetime) -> None:
        pass

class PawPalSystem:
    def __init__(self) -> None:
        pass
    
    def add_pet(self, pet: Pet) -> None:
        pass
    
    def remove_pet(self, pet_name: str) -> None:
        pass
    
    def get_pet(self, pet_name: str) -> Pet:
        pass
    
    def add_task(self, task: Task) -> None:
        pass
    
    def remove_task(self, task_id: str) -> None:
        pass
    
    def get_all_tasks(self) -> List[Task]:
        pass
    
    def get_pet_tasks(self, pet_name: str) -> List[Task]:
        pass
    
    def update_pet_status(self, pet_name: str) -> None:
        pass
    
    def get_all_pets(self) -> List[Pet]:
        pass