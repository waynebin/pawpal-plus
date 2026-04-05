# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

**Three core user actions:**

1. **Add a pet and owner profile** — The user enters basic information about themselves (name, available time per day) and their pet (name, species, age). This gives the scheduler the context it needs to tailor the care plan.

2. **Add and manage care tasks** — The user creates tasks such as a morning walk, feeding, medication, or grooming. Each task has a title, estimated duration in minutes, and a priority level (low, medium, high). Users can add multiple tasks and edit or remove them as their pet's needs change.

3. **Generate and view today's daily schedule** — The user triggers the scheduler, which selects and orders tasks based on available time and priority. The app displays the resulting plan and explains why each task was included and when it is scheduled.

**Building blocks (objects):**

- **Owner**
  - Attributes: `name` (str), `available_minutes` (int), `preferences` (dict)
  - Methods: `set_available_time(minutes)`, `add_preference(key, value)`

- **Pet**
  - Attributes: `name` (str), `species` (str), `age` (int), `owner` (Owner)
  - Methods: `get_info() -> dict`

- **Task**
  - Attributes: `title` (str), `duration_minutes` (int), `priority` (str), `completed` (bool)
  - Methods: `mark_complete()`, `to_dict() -> dict`

- **Scheduler**
  - Attributes: `tasks` (list[Task]), `available_minutes` (int)
  - Methods: `add_task(task)`, `remove_task(title)`, `generate_plan() -> list[Task]`, `explain_plan() -> str`

- **DailyPlan**
  - Attributes: `scheduled_tasks` (list[Task]), `total_duration` (int), `explanation` (str)
  - Methods: `display() -> str`, `is_feasible() -> bool`

- What classes did you include, and what responsibilities did you assign to each?
the `Owner` class manages user information and preferences, while the `Pet` class holds details about the pet. The `Task` class represents individual care tasks with their attributes and methods to manage completion status. The `Scheduler` class is responsible for managing tasks and generating a daily plan based on constraints. Finally, the `DailyPlan` class encapsulates the scheduled tasks and provides methods to display the plan and check its feasibility.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
