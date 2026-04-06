# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

**Three core user actions:**

1. **Add a pet and owner profile** — The user enters basic information about themselves (name, available time per day) and their pet (name, species, age). This gives the scheduler the context it needs to tailor the care plan.

2. **Add and manage care tasks** — The user creates tasks such as a morning walk, feeding, medication, or grooming. Each task has a title, estimated duration in minutes, and a priority level (low, medium, high). Users can add multiple tasks and edit or remove them as their pet's needs change.

3. **Generate and view today's daily schedule** — The user triggers the scheduler, which selects and orders tasks based on available time and priority. The app displays the resulting plan and explains why each task was included and when it is scheduled.

**Classes included and their responsibilities:**

- **Owner** — manages user information and available time per day (split across morning, afternoon, evening slots).
- **Pet** — holds the pet's profile and live state (hunger, happiness, energy) with methods to simulate feeding, playing, and sleeping.
- **Task** — represents one care item with duration, priority, time slot, recurrence, dependencies, and a required flag.
- **Scheduler** — the core engine. Selects and orders tasks using a 0/1 knapsack algorithm, resolves dependencies via topological sort, detects conflicts, and explains the final plan.
- **PawPalSystem** — the top-level registry that wires everything together. Manages all pets and tasks and creates a Scheduler on demand.

**b. Design changes**

Yes, the design changed significantly during implementation. Three key changes:

1. **`DailyPlan` was dropped** — The initial design had a separate `DailyPlan` class to hold the schedule output. During implementation, this responsibility was absorbed directly into `Scheduler.generate_plan()` and `explain_plan()`, which eliminated an unnecessary layer of indirection.

2. **`Owner` gained `time_per_slot`** — The original `Owner` only had a single `available_minutes` integer. To support slot-based scheduling (morning/afternoon/evening), a `time_per_slot` dictionary was added. This changed how `Scheduler` receives its time budget.

3. **`Task` grew considerably** — The initial `Task` had only `title`, `duration_minutes`, `priority`, and `completed`. The final version added `time_slot`, `recurrence`, `dependencies`, `is_required`, and `carry_over` to support a realistic scheduling model.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers three constraints:
- **Time** — each slot (morning, afternoon, evening) has its own time budget set by the owner.
- **Priority** — tasks are ranked HIGH / MEDIUM / LOW. Higher-priority tasks get a larger weight in the knapsack objective function.
- **Pet state** — if the pet's hunger reaches 8+/10, feeding tasks receive a +2 weight boost regardless of their assigned priority. The same boost applies to rest tasks when energy drops to 2/10 or below.

Time was treated as the hard constraint (tasks cannot exceed the slot budget), while priority and pet state determined which tasks get selected when there is competition for limited time.

**b. Tradeoffs**

The knapsack algorithm optimises for maximum total priority weight, not maximum number of tasks. This means a single HIGH-priority 30-minute task will always beat two LOW-priority 15-minute tasks of equal total duration, even though the same time is used either way.

This tradeoff is reasonable for a pet owner because missing a high-priority task (like medication) has a greater real-world cost than skipping two low-priority tasks (like enrichment play). The scheduler reflects that not all minutes of pet care are equally important.

---

## 3. AI Collaboration

**a. How you used AI**

AI tools (Claude Code) were used across all phases of the project:

- **Design brainstorming** — used AI to identify missing relationships in the initial skeleton file (`pawpal_system.py`). The AI spotted that `Task` linked to a pet by name string (fragile) and that `Scheduler` was missing entirely from the first draft.
- **Implementation** — AI wrote the first complete implementations of `Scheduler.generate_plan()` (greedy), then upgraded it to the knapsack algorithm when prompted.
- **Refactoring** — AI updated `Owner` to support `time_per_slot`, updated all downstream classes, and rewrote the test suite to match the new API.
- **Debugging** — AI diagnosed the pytest `ModuleNotFoundError` (wrong module name `pawpal` vs `pawpal_system`) and the broken `Task` constructor in the original test file.

The most effective prompts were specific and scoped: "review my skeleton file and identify missing relationships or bottlenecks" produced more useful output than general requests.

**b. Judgment and verification**

When the AI first suggested a greedy scheduler (sort by priority, add tasks in order until time runs out), the suggestion was accepted for the initial implementation but later evaluated more carefully. The greedy approach was found to fail in cases where two medium-priority tasks together fit in less time and produce more total value than one high-priority task. This was verified by writing the test `test_knapsack_picks_better_combination_than_greedy`, which confirmed the greedy approach would have failed and motivated the switch to the 0/1 knapsack.

The AI also suggested adding a `DailyPlan` class early in the design. After reviewing the responsibilities of that class, it was clear it duplicated what `Scheduler` already did. The suggestion was rejected and `Scheduler` was given the plan-output responsibility directly.

---

## 4. Testing and Verification

**a. What you tested**

- **Task state transitions** — `mark_complete` and `mark_incomplete` toggle `is_completed` correctly.
- **Pet state clamping** — `feed`, `play`, and `sleep` never push levels outside 0–10.
- **Knapsack correctness** — a specific test verifies the knapsack selects the better combination over greedy.
- **Pet state priority boost** — tests confirm that a hungry pet's feeding task wins over a competing task even when its base priority is lower.
- **Dependency ordering** — verifies that the topological sort places a dependency task before its dependent.
- **Carry-over detection** — tasks that don't fit are returned by `get_carry_over_tasks()`.
- **Conflict detection** — tests for time overruns, required tasks that can't be scheduled, and broken dependency references.
- **PawPalSystem integration** — add/remove pet (including cascade task deletion), `build_schedule` wiring, and error on unknown pet.

These tests were important because the scheduler's correctness cannot be inferred by running the UI alone — edge cases like the knapsack vs greedy difference and the hunger boost are invisible without direct unit tests.

**b. Confidence**

Confidence in the scheduler is high for the tested scenarios. Edge cases worth testing next:
- Circular dependencies (two tasks that each depend on the other) — currently handled gracefully by the topological sort's `visited` set, but not explicitly tested.
- Tasks with duration exactly equal to slot capacity.
- A pet whose hunger and energy are both critical simultaneously — verifying that both boosts apply and that the correct task wins.

---

## 5. Reflection

**a. What went well**

The scheduling engine turned out to be the strongest part of the project. The combination of the knapsack algorithm, pet-state-aware priority boosting, dependency resolution, and carry-over surfacing makes it meaningfully smarter than a simple sorted list. The conflict detection panel in the UI was also effective — it doesn't just warn, it tells the owner exactly what to do to fix the problem.

**b. What you would improve**

If given another iteration, the time-slot distribution for `ANY` tasks would be improved. Currently they are distributed round-robin, which is naive. A better approach would be to assign `ANY` tasks to whichever slot has the most remaining capacity, making better use of the owner's available time.

**c. Key takeaway**

The most important lesson was that AI tools are most useful when you, as the architect, already have a clear mental model of what you are building. When prompts were vague ("improve the scheduler"), the AI produced generic suggestions. When prompts were specific ("the greedy approach fails when two medium tasks fit better than one high task — implement 0/1 knapsack instead"), the AI produced exactly the right code. The lead architect's job is to know what question to ask, not to ask the AI to figure out the question too.
