# Sprint Dashboard - Revision Log

## Recent Requests and Implementation Responses

---

### 1. Feature Request: Calculate Hours Spent from Worklog
**Date:** Jan 23, 2026  
**Type:** Feature Request

**Request:**  
TaskHoursSpent and TicketHoursSpent columns should be calculated from the worklog table entries instead of Snowflake. In Backlog Assign page, show total hours spent. In Sprint Update page, show only hours spent during that sprint.

**Response:**  
Updated hours calculation. Backlog Assign now shows total hours from all worklogs. Sprint Update shows hours logged during the selected sprint only. TicketHoursSpent is the sum of all task hours for that ticket.

---

### 2. Revision: Show Completed Tasks in Sprint Tables
**Date:** Jan 23, 2026  
**Type:** Policy Revision

**Request:**  
Tasks assigned to a sprint should always be visible in that sprint, even after completion. Currently, completed tasks are hidden from Sprint Update page.

**Response:**  
Sprint Update page now shows all tasks assigned to the sprint, including completed ones. Task count in sprint dropdown includes all tasks.

---

### 3. Feature Request: Sprint Completion Tracking Table
**Date:** Jan 23, 2026  
**Type:** Feature Request

**Request:**  
Add a new table in Sprint Update page showing: Sprint Number, Task ID, Subject, Completed This Sprint (Yes/No based on status and resolved date within sprint window), and an editable Non-Completion Reason field.

**Response:**  
Added Sprint Completion Tracking section at bottom of Sprint Update page. Table shows completion status per task with editable reason field. Includes summary metrics showing completion rate.

---

### 4. Layout: Move Task Completion Status Section
**Date:** Jan 23, 2026  
**Type:** Layout Change

**Request:**  
Move the "Task Completion Status by User" section to below the main task table in Sprint Update page.

**Response:**  
Moved section to appear after the Burn Rate chart at the bottom of the page.

---

### 5. Feature Request: Toggle Previous Sprints Visibility
**Date:** Jan 23, 2026  
**Type:** Feature Request

**Request:**  
Add option to view previous sprints in Sprint Update page. Currently only current and future sprints are shown.

**Response:**  
Added "Show Previous Sprints" checkbox at top of Sprint Update page. When checked, past sprints appear in the dropdown.

---

### 6. Revision: Consolidate Subject Column
**Date:** Jan 23, 2026  
**Type:** Revision

**Request:**  
Revert back to a single Subject column. The split into TaskSubject and TicketSubject caused confusion.

**Response:**  
All tables now use a single Subject column throughout the application.

---

### 7. Bug Fix: Data Loading Error
**Date:** Jan 23, 2026  
**Type:** Bug Fix

**Request:**  
Fix error when loading task data from Snowflake - Subject column not being recognized.

**Response:**  
Fixed column name mapping. Data loads correctly now.

---

### 8. Feature Request: Add Task Count per Ticket
**Date:** Jan 23, 2026  
**Type:** Feature Request

**Request:**  
Add a TaskCount column to identify tickets with multiple tasks.

**Response:**  
Added TaskCount column showing how many tasks belong to each ticket.

---

### 9. Revision: Non-Completion Reason Field
**Date:** Jan 23, 2026  
**Type:** Revision

**Request:**  
Add Non-Completion Reason field to existing task annotations rather than creating a new table.

**Response:**  
Added NonCompletionReason as an editable field in the task data. Field persists with other task annotations.

---

### 10. Layout: Update Column Display Order
**Date:** Jan 23, 2026  
**Type:** Layout Change

**Request:**  
Update column order in all tables to use the consolidated Subject column.

**Response:**  
Updated column display order across all pages to show single Subject column consistently.

---

## Summary

| # | Type | Description | Status |
|---|------|-------------|--------|
| 1 | Feature | Worklog-based hours calculation | ✅ Complete |
| 2 | Revision | Show completed tasks in sprint tables | ✅ Complete |
| 3 | Feature | Sprint Completion Tracking table | ✅ Complete |
| 4 | Layout | Move Task Completion Status section | ✅ Complete |
| 5 | Feature | Toggle previous sprints visibility | ✅ Complete |
| 6 | Revision | Consolidate Subject column | ✅ Complete |
| 7 | Bug Fix | Data loading error | ✅ Complete |
| 8 | Feature | Task count per ticket | ✅ Complete |
| 9 | Revision | Non-Completion Reason field | ✅ Complete |
| 10 | Layout | Update column display order | ✅ Complete |
