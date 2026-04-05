from datetime import datetime
from pawpal_system import Owner, Pet, PetType, Task, Priority, PawPalSystem


if __name__ == "__main__":
    # Create owner
    owner = Owner(name="Alice", available_minutes=120)

    # Create pets
    dog = Pet(name="Buddy", pet_type=PetType.DOG, age=3, owner=owner)
    cat = Pet(name="Whiskers", pet_type=PetType.CAT, age=2, owner=owner)

    # Show initial pet status
    print("=== Initial Pet Status ===")
    print(dog.get_status())
    print(cat.get_status())

    # Simulate interactions
    print("\n=== Simulating Interactions ===")
    dog.feed()
    print(f"After feeding   -> {dog.get_status()}")
    dog.play()
    print(f"After playing   -> {dog.get_status()}")
    cat.sleep()
    print(f"After sleeping  -> {cat.get_status()}")

    # Set up the system
    system = PawPalSystem()
    system.add_pet(dog)
    system.add_pet(cat)

    # Create tasks
    today = datetime.today()
    system.add_task(Task("t1", "Morning walk",     dog, today, duration_minutes=30, priority=Priority.HIGH))
    system.add_task(Task("t2", "Afternoon playtime", dog, today, duration_minutes=45, priority=Priority.MEDIUM))
    system.add_task(Task("t3", "Evening grooming",  dog, today, duration_minutes=20, priority=Priority.LOW))
    system.add_task(Task("t4", "Feeding time",      cat, today, duration_minutes=15, priority=Priority.HIGH))
    system.add_task(Task("t5", "Litter box cleaning", cat, today, duration_minutes=10, priority=Priority.MEDIUM))

    # Build and display schedule for Buddy
    print("\n=== Buddy's Daily Schedule ===")
    scheduler = system.build_schedule("Buddy")
    print(scheduler.explain_plan())

    # Build and display schedule for Whiskers
    print("\n=== Whiskers's Daily Schedule ===")
    scheduler = system.build_schedule("Whiskers")
    print(scheduler.explain_plan())
