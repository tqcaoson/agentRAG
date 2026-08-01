# Habit Tracker Requirements

## FEAT-001: Create Habit
Users can create a habit with the following fields:
- habit name
- category
- target frequency
- start date
- optional note

Acceptance Criteria:
- User can create a new habit.
- Habit name is required.
- Category is optional.
- Target frequency must be daily or weekly.

## FEAT-002: Mark Habit As Done
Users can mark a habit as completed for a specific date.

Acceptance Criteria:
- User can mark today's habit as done.
- User can undo completion.
- System must avoid duplicate completion records for the same habit and date.
