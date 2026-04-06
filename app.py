import streamlit as st
from datetime import datetime
from pawpal_system import (
    Owner, Pet, PetType, Task, Priority, TimeSlot, Recurrence,
    PawPalSystem, suggest_duration
)


st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")


# --- Session state initialization ---
def init_session():
    if "system" not in st.session_state:
        st.session_state.system = PawPalSystem()
    if "owner" not in st.session_state:
        st.session_state.owner = None
    if "pet" not in st.session_state:
        st.session_state.pet = None
    if "task_counter" not in st.session_state:
        st.session_state.task_counter = 0

init_session()


# ── Helper ────────────────────────────────────────────────────────────────────

PRIORITY_COLOR = {"high": "🔴", "medium": "🟡", "low": "🟢"}

def priority_badge(priority_value: str) -> str:
    return f"{PRIORITY_COLOR.get(priority_value, '')} {priority_value.upper()}"

def slot_progress(used: int, capacity: int) -> str:
    pct = int((used / capacity) * 100) if capacity > 0 else 0
    bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
    color = "green" if pct <= 80 else "orange" if pct <= 100 else "red"
    return f":{color}[{bar}] {used}/{capacity} min ({pct}%)"


# ── Header ────────────────────────────────────────────────────────────────────

st.title("🐾 PawPal+")
st.caption("A smart daily care planner for your pet — powered by priority scheduling.")
st.divider()


# ── Step 1: Owner + Pet Setup ─────────────────────────────────────────────────

st.subheader("Step 1: Owner & Pet Info")

col1, col2 = st.columns(2)
with col1:
    owner_name = st.text_input("Owner name", value="Jordan")
    st.markdown("**Available time per slot (minutes)**")
    morning_min   = st.number_input("Morning",   min_value=0, max_value=240, value=40)
    afternoon_min = st.number_input("Afternoon", min_value=0, max_value=240, value=40)
    evening_min   = st.number_input("Evening",   min_value=0, max_value=240, value=40)
with col2:
    pet_name = st.text_input("Pet name", value="Mochi")
    pet_type = st.selectbox("Species", [p.value for p in PetType])
    pet_age  = st.number_input("Pet age (years)", min_value=0, max_value=30, value=2)

if st.button("Save Owner & Pet", type="primary"):
    total = int(morning_min) + int(afternoon_min) + int(evening_min)
    owner = Owner(
        name=owner_name,
        available_minutes=total,
        time_per_slot={
            "morning":   int(morning_min),
            "afternoon": int(afternoon_min),
            "evening":   int(evening_min),
        },
    )
    pet = Pet(name=pet_name, pet_type=PetType(pet_type), age=int(pet_age), owner=owner)
    st.session_state.owner = owner
    st.session_state.pet   = pet

    system: PawPalSystem = st.session_state.system
    if system.get_pet(pet_name):
        system.remove_pet(pet_name)
    system.add_pet(pet)
    st.success(f"Saved! {owner.name}'s pet **{pet.name}** ({pet_type}, age {pet_age}) — {total} min/day available")

if st.session_state.pet:
    p = st.session_state.pet
    c1, c2, c3 = st.columns(3)
    c1.metric("Hunger",    f"{p.hunger_level}/10")
    c2.metric("Happiness", f"{p.happiness_level}/10")
    c3.metric("Energy",    f"{p.energy_level}/10")

st.divider()


# ── Step 2: Add Care Tasks ────────────────────────────────────────────────────

st.subheader("Step 2: Add Care Tasks")

if st.session_state.pet is None:
    st.warning("Complete Step 1 before adding tasks.")
else:
    pet: Pet = st.session_state.pet
    system: PawPalSystem = st.session_state.system

    col1, col2 = st.columns(2)
    with col1:
        task_desc = st.text_input("Task description", value="Morning walk")

        suggested = suggest_duration(pet.pet_type, task_desc)
        if suggested:
            st.caption(f"Suggested duration for a {pet.pet_type.value}: **{suggested} min**")
        duration = st.number_input(
            "Duration (minutes)",
            min_value=1, max_value=240,
            value=suggested if suggested else 20
        )
        priority = st.selectbox("Priority", [p.value for p in Priority], index=2)

    with col2:
        time_slot   = st.selectbox("Time slot", [s.value for s in TimeSlot])
        recurrence  = st.selectbox("Recurrence", [r.value for r in Recurrence])
        is_required = st.checkbox("Mark as required (must appear in schedule)")

        existing_ids = [t.task_id for t in system.get_pet_tasks(pet.name)]
        dep_input = st.text_input(
            "Depends on task IDs (comma-separated)",
            placeholder="e.g. t1, t2",
            help=f"Existing task IDs: {', '.join(existing_ids) if existing_ids else 'none yet'}"
        )

    if st.button("Add Task", type="primary"):
        st.session_state.task_counter += 1
        task_id = f"t{st.session_state.task_counter}"
        deps = [d.strip() for d in dep_input.split(",") if d.strip()]
        task = Task(
            task_id=task_id,
            description=task_desc,
            pet=pet,
            due_date=datetime.today(),
            duration_minutes=int(duration),
            priority=Priority(priority),
            time_slot=TimeSlot(time_slot),
            recurrence=Recurrence(recurrence),
            is_required=is_required,
            dependencies=deps,
        )
        system.add_task(task)
        st.success(f"Added **[{task_id}]** {task_desc} — {priority_badge(priority)}, {int(duration)} min, {time_slot}")

    # ── Task table ──
    pet_tasks = system.get_pet_tasks(pet.name)
    if pet_tasks:
        total_task_time = sum(t.duration_minutes for t in pet_tasks)
        total_available = pet.owner.available_minutes
        st.markdown(f"**{len(pet_tasks)} task(s) for {pet.name}** — total time: {total_task_time} min")

        # Pre-schedule conflict preview
        if total_task_time > total_available:
            st.warning(
                f"Total task time ({total_task_time} min) exceeds your available time "
                f"({total_available} min). Some tasks will be carried over or skipped."
            )

        # Render tasks as a styled table
        rows = []
        for t in pet_tasks:
            rows.append({
                "ID": t.task_id,
                "Description": t.description,
                "Priority": priority_badge(t.priority.value),
                "Duration": f"{t.duration_minutes} min",
                "Slot": t.time_slot.value,
                "Recurrence": t.recurrence.value,
                "Required": "Yes" if t.is_required else "",
                "Depends on": ", ".join(t.dependencies) if t.dependencies else "",
            })
        st.table(rows)

        col_r1, col_r2 = st.columns([1, 3])
        with col_r1:
            remove_id = st.text_input("Task ID to remove", placeholder="e.g. t1")
        with col_r2:
            st.write("")
            st.write("")
            if st.button("Remove Task"):
                system.remove_task(remove_id.strip())
                st.rerun()
    else:
        st.info("No tasks yet. Add one above.")

st.divider()


# ── Step 3: Generate Daily Schedule ──────────────────────────────────────────

st.subheader("Step 3: Generate Daily Schedule")

if st.session_state.pet is None:
    st.warning("Complete Step 1 before generating a schedule.")
else:
    if st.button("Generate Schedule", type="primary"):
        system: PawPalSystem = st.session_state.system
        try:
            scheduler = system.build_schedule(st.session_state.pet.name)
            conflicts  = scheduler.detect_conflicts()
            plan       = scheduler.generate_plan()
            carry_over = scheduler.get_carry_over_tasks()
            total_scheduled = sum(len(tasks) for tasks in plan.values())

            # ── Conflict panel ──────────────────────────────────────────────
            if conflicts:
                st.error("**Scheduling conflicts detected — review before proceeding:**")
                for i, msg in enumerate(conflicts, 1):
                    if "exceeds" in msg:
                        st.warning(f"**#{i} Time overrun:** {msg}  \n"
                                   "_Tip: reduce task durations or increase available time in Step 1._")
                    elif "Required" in msg:
                        st.error(f"**#{i} Required task skipped:** {msg}  \n"
                                 "_Tip: shorten other tasks or free up the relevant time slot._")
                    elif "unknown task" in msg:
                        st.warning(f"**#{i} Broken dependency:** {msg}  \n"
                                   "_Tip: check the task IDs entered in the 'Depends on' field._")
                    else:
                        st.warning(f"**#{i}** {msg}")
                st.divider()

            # ── No tasks fit ────────────────────────────────────────────────
            if total_scheduled == 0:
                st.warning(
                    "No tasks could fit within the available time slots.  \n"
                    "Try shortening task durations or increasing the time per slot in Step 1."
                )
            else:
                scheduled_total = sum(t.duration_minutes for tasks in plan.values() for t in tasks)
                st.success(
                    f"Schedule built for **{st.session_state.pet.name}** — "
                    f"{total_scheduled} task(s), {scheduled_total} min planned today."
                )

                # ── Per-slot panels ─────────────────────────────────────────
                for slot_name, tasks in plan.items():
                    capacity = scheduler.time_per_slot.get(slot_name, 0)
                    used = sum(t.duration_minutes for t in tasks)

                    with st.expander(
                        f"{'🌅' if slot_name=='morning' else '☀️' if slot_name=='afternoon' else '🌙'} "
                        f"**{slot_name.upper()}** — {slot_progress(used, capacity)}",
                        expanded=True,
                    ):
                        if tasks:
                            for task in tasks:
                                badges = [priority_badge(task.priority.value)]
                                if task.is_required:
                                    badges.append("🔒 REQUIRED")
                                if task.recurrence.value != "as_needed":
                                    badges.append(f"🔁 {task.recurrence.value}")
                                if task.carry_over:
                                    badges.append("↪ carry-over")
                                if task.dependencies:
                                    badges.append(f"🔗 after {', '.join(task.dependencies)}")

                                st.markdown(
                                    f"✅ **{task.description}** ({task.duration_minutes} min)  \n"
                                    f"{'  '.join(badges)}"
                                )
                        else:
                            st.caption("No tasks scheduled in this slot.")

                # ── Carry-over panel ────────────────────────────────────────
                if carry_over:
                    with st.expander(f"↪ **Carried over to tomorrow** ({len(carry_over)} task(s))", expanded=False):
                        st.info(
                            "These tasks didn't fit today's schedule. They are listed here "
                            "so you can reschedule or adjust tomorrow's time budget."
                        )
                        for task in carry_over:
                            st.markdown(
                                f"- {priority_badge(task.priority.value)} **{task.description}** "
                                f"({task.duration_minutes} min)"
                                + (" 🔒" if task.is_required else "")
                            )

                # ── Full text explanation ───────────────────────────────────
                with st.expander("📋 Full scheduler explanation", expanded=False):
                    st.code(scheduler.explain_plan(), language=None)

        except ValueError as e:
            st.error(str(e))
