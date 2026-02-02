# Reports & Visualizations Master Plan

## Overview

This document outlines the implementation plan for 5 new report categories for the PIBIDS Sprint Dashboard. Each section details the data sources, calculations, UI components, and implementation approach.

---

## Data Sources Available

### Primary Tables

| Table | Key Columns | Description |
|-------|-------------|-------------|
| **tasks** | `task_num`, `ticket_num`, `task_status`, `assigned_to`, `section`, `task_created_dt`, `task_resolved_dt` | Individual work items |
| **tickets** | `ticket_num`, `ticket_status`, `ticket_type`, `section`, `customer_name`, `ticket_created_dt`, `ticket_resolved_dt` | Parent tickets (IR, SR, PR, NC) |
| **worklogs** | `record_id`, `task_num`, `owner`, `minutes_spent`, `log_date`, `sprint_number` | Time logged by team members |
| **sprint_calendar** | `sprint_number`, `sprint_name`, `sprint_start_dt`, `sprint_end_dt` | Sprint date windows |
| **offdays** | `username`, `sprint_number`, `off_date`, `reason` | Team member off days |
| **dashboard_task_annotations** | `task_num`, `sprints_assigned`, `hours_estimated`, `goal_type` | Dashboard-specific fields |

### Derived Data

| Field | Source | Calculation |
|-------|--------|-------------|
| **TicketType** | Parsed from `Subject` | IR, SR, PR, NC, AD |
| **Section** | `tickets.section` | Lab section (e.g., "Micro", "HLA") |
| **LoggedHours** | `worklogs.minutes_spent / 60` | Hours from worklog |
| **ExpectedHours** | `dashboard_task_annotations.hours_estimated` | Estimated hours per task |
| **AvailableHours** | `(sprint_days - off_days) * 8` | Per team member per sprint |

### Key Constants

- **Ticket Types**: IR (Incident), SR (Service), PR (Project), NC (Not Classified), AD (Admin)
- **Open Statuses**: Logged, Assigned, Accepted, Waiting
- **Closed Statuses**: Completed, Closed, Resolved, Done, Canceled

---

## Page Structure

### Proposed Navigation

```
📊 Reports & Analytics (New Page)
├── Tab 1: Tickets & Tasks Count
├── Tab 2: Tickets & Tasks Status  
├── Tab 3: Efforts by Lab Section
├── Tab 4: Effort Distribution by Team
└── Tab 5: Task Completion Rate
```

---

## Report 1: Tickets & Tasks Count

### Purpose
Display count of tickets and tasks per lab section, broken down by ticket type.

### Visualizations

| Chart | X-Axis | Y-Axis | Breakdown |
|-------|--------|--------|-----------|
| **1a. Tickets by Lab Section** | Lab Section | Count | Stacked by Ticket Type |
| **1b. Tasks by Lab Section** | Lab Section | Count | Stacked by Ticket Type |

### Filters (Global)

| Filter | Type | Options |
|--------|------|---------|
| **Ticket Status** | Multi-select | Assigned, Waiting, Closed, etc. |
| **Time Window** | Radio + Inputs | Sprint selector OR Date range (mutually exclusive) |
| **Assigned Team Member(s)** | Multi-select | List from `valid_team_members` config |

### Data Query Logic

```python
# Tickets by Section
SELECT 
    tk.section AS Section,
    tk.ticket_type AS TicketType,
    COUNT(DISTINCT tk.ticket_num) AS TicketCount
FROM tickets tk
JOIN tasks t ON t.ticket_num = tk.ticket_num
WHERE 
    -- Apply status filter
    t.task_status IN (:selected_statuses)
    -- Apply time window filter (sprint OR date range) - uses TASK CREATION DATE
    AND (t.task_created_dt BETWEEN :start_date AND :end_date)
    -- Apply assignee filter
    AND t.assigned_to IN (:selected_members)
    -- Exclude AD tickets by default
    AND tk.ticket_type != 'AD'
GROUP BY tk.section, tk.ticket_type

# Tasks by Section - similar but COUNT(t.task_num)
```

### Implementation Notes
- Use Plotly `px.bar` with `color='TicketType'` for stacked bars
- Chart type: Grouped or stacked bar chart (vertical)

---

## Report 2: Tickets & Tasks Status

### Purpose
Summarize ticket/task status activity (open vs completed) within a time window.

### Visualizations

| Chart | Type | Segments | Metric |
|-------|------|----------|--------|
| **Chart 1: Open Items** | Pie | Lab Section | Count of open items |
| **Chart 2: Completed Items** | Pie | Lab Section | Count of completed items |

### Filters (Global)

| Filter | Type | Options |
|--------|------|---------|
| **Lab Section** | Multi-select | List of valid sections |
| **Time Window** | Radio + Inputs | Sprint OR Date range (mutually exclusive) |
| **View Toggle** | Radio | Tickets only / Tasks only |

### Data Query Logic

```python
# Open Items (non-closed) - hardcoded open statuses
OPEN_STATUSES = ['Logged', 'Assigned', 'Accepted', 'Waiting']

# For Tickets toggle:
SELECT section, COUNT(DISTINCT ticket_num) 
WHERE ticket_status IN OPEN_STATUSES
  AND ticket_created_dt BETWEEN :start AND :end
GROUP BY section

# For Tasks toggle:
SELECT section, COUNT(task_num)
WHERE task_status IN OPEN_STATUSES
  AND task_created_dt BETWEEN :start AND :end
GROUP BY section

# Completed Items - items closed within time window
CLOSED_STATUSES = ['Completed', 'Closed', 'Resolved', 'Done']
WHERE task_resolved_dt BETWEEN :start AND :end
  AND task_status IN CLOSED_STATUSES
```

### Implementation Notes
- Use Plotly `px.pie` with hover showing count values
- Tooltip: Show count and percentage on hover
- Section filter affects visibility only; percentages still based on all sections

---

## Report 3: Efforts by Lab Section

### Purpose
Visualize PIBIDS effort distribution across lab sections by ticket type.

### Visualization

| Chart | X-Axis | Y-Axis | Stacking |
|-------|--------|--------|----------|
| **Stacked Bar** | Lab Section | Percentage (%) | Ticket Type |

### Filters

| Filter | Type | Options | Behavior |
|--------|------|---------|----------|
| **Hours Toggle** | Radio | Expected Hours / Logged Hours | Switches data source |
| **Time Window** | Radio | Sprint OR Date range | Mutually exclusive |
| **Lab Section** | Multi-select | Valid sections | Visibility only (denominator unchanged) |

### Data Query Logic

```python
# Logged Hours (from worklogs)
SELECT 
    tk.section AS Section,
    tk.ticket_type AS TicketType,
    SUM(w.minutes_spent) / 60.0 AS Hours
FROM worklogs w
JOIN tasks t ON t.task_num = w.task_num
JOIN tickets tk ON tk.ticket_num = t.ticket_num
WHERE w.log_date BETWEEN :start AND :end
GROUP BY tk.section, tk.ticket_type

# Expected Hours (from annotations)
SELECT 
    tk.section AS Section,
    tk.ticket_type AS TicketType,
    SUM(a.hours_estimated) AS Hours
FROM dashboard_task_annotations a
JOIN tasks t ON t.task_num = a.task_num
JOIN tickets tk ON tk.ticket_num = t.ticket_num
WHERE t.task_created_dt BETWEEN :start AND :end
GROUP BY tk.section, tk.ticket_type

# Calculate percentages
total_hours = df['Hours'].sum()
df['Percentage'] = (df['Hours'] / total_hours) * 100
```

### Implementation Notes
- **Critical**: Percentage denominator is TOTAL hours across ALL sections
- Section filter hides bars but doesn't change percentage calculation
- Tooltip: Show absolute hours AND ticket type breakdown

---

## Report 4: Effort Distribution by PIBIDS Team

### Purpose
Show how each team member allocates their available hours by ticket type and lab section.

### Visualizations

| Chart | X-Axis | Y-Axis | Stacking |
|-------|--------|--------|----------|
| **4A: By Ticket Type** | Team Member | % of Available Hours | Ticket Type + Unaccounted |
| **4B: By Lab Section** | Team Member | % of Available Hours | Lab Section + Unaccounted |

### Filters

| Filter | Type | Options |
|--------|------|---------|
| **Effort Denominator** | Toggle | Total Worklog Entry / Total Allocated |
| **Time Window** | Radio | Sprint OR Date range (mutually exclusive) |
| **Team Member** | Multi-select | Valid team members |

### Data Query Logic

```python
# Step 1: Calculate Available Hours per Team Member
def get_available_hours(member, sprint_number):
    sprint = get_sprint_by_number(sprint_number)
    total_days = (sprint.end - sprint.start).days + 1
    weekdays = count_weekdays(sprint.start, sprint.end)  # ~10 days in 14-day sprint
    off_days = offdays_store.get_offday_count(member, sprint_number)
    available_days = weekdays - off_days
    return available_days * 8.0  # 8 hours per day

# Step 2: Get Logged Hours by Ticket Type
SELECT 
    w.owner AS TeamMember,
    tk.ticket_type AS TicketType,
    SUM(w.minutes_spent) / 60.0 AS LoggedHours
FROM worklogs w
JOIN tasks t ON t.task_num = w.task_num
JOIN tickets tk ON tk.ticket_num = t.ticket_num
WHERE w.log_date BETWEEN :start AND :end
GROUP BY w.owner, tk.ticket_type

# Step 3: Get Logged Hours by Section
SELECT 
    w.owner AS TeamMember,
    tk.section AS Section,
    SUM(w.minutes_spent) / 60.0 AS LoggedHours
FROM worklogs w
JOIN tasks t ON t.task_num = w.task_num
JOIN tickets tk ON tk.ticket_num = t.ticket_num
WHERE w.log_date BETWEEN :start AND :end
GROUP BY w.owner, tk.section

# Step 4: Calculate Unaccounted
unaccounted = available_hours - total_logged_hours
if unaccounted < 0:
    unaccounted = 0  # Over-logged case

# Step 5: Calculate Percentages
percentage = (logged_hours / available_hours) * 100
```

### Denominator Toggle Behavior

| Toggle Value | Denominator |
|--------------|-------------|
| **Total Allocated** | Available Hours (weekdays × 8 - off days × 8) |
| **Total Worklog Entry** | Sum of all logged hours for that member |

### Implementation Notes
- Unaccounted Hours = Available - Logged (show as separate category in stack)
- Each member's percentage is independent of other members
- Use `offdays_store` for off day calculation

---

## Report 5: Task Completion Rate by Sprint

### Purpose
Measure execution efficiency by tracking task completion within sprint windows.

### Visualizations

| Chart | X-Axis | Y-Axis | Metric |
|-------|--------|--------|--------|
| **5A: By Sprint** | Sprint | Completion Rate (%) | Tasks completed / Tasks committed × 100 |
| **5B: By Team Member** | Team Member | Completion Rate (%) | Same metric per person |

### Filters

| Filter | Type | Applies To |
|--------|------|------------|
| **Sprint Selector** | Multi-select | Both charts |
| **Date Range** | Date inputs | Alternative to sprint selector |
| **Team Member** | Multi-select | Chart 5B only |

### Data Query Logic

```python
# Task Completion Rate Definition:
# Numerator: Tasks closed within the SAME sprint window they were assigned to
# Denominator: Total tasks assigned (committed) to the sprint

# Step 1: Get tasks committed to sprint
SELECT task_num, assigned_to
FROM task_sprint_assignments tsa
JOIN tasks t ON t.task_num = tsa.task_num
WHERE tsa.sprint_number = :sprint

# Step 2: Check which were completed within sprint window
SELECT t.task_num
FROM tasks t
JOIN sprint_calendar sc ON sc.sprint_number = :sprint
WHERE t.task_resolved_dt BETWEEN sc.sprint_start_dt AND sc.sprint_end_dt
  AND t.task_status IN ('Completed', 'Closed', 'Resolved', 'Done')

# Step 3: Calculate rate
completion_rate = (completed_in_sprint / committed_to_sprint) * 100

# For Chart 5B (by Team Member):
GROUP BY t.assigned_to
```

### Calculation Rules
- **Multi-sprint assignment**: A task can be assigned to multiple sprints (e.g., sprint 1,2 or 1,3)
- **Completion definition**: Any task completed within the sprint window counts as completed for that sprint
- **Numerator**: Tasks with status in Closed statuses AND `task_resolved_dt` within sprint window
- **Denominator**: Tasks assigned to the sprint (via `task_sprint_assignments`)
- **Consistency**: Same formula for sprint-level and person-level views
- **AD tickets**: Excluded by default

### Optional Enhancements (Nice-to-Have)
- Trend line overlay across sprints
- Tooltip: Show "X of Y tasks completed"
- Toggle: Include/exclude Mandatory vs Stretch tasks (filter by `goal_type`)
- Toggle: Include/exclude AD tickets

---

## Implementation Phases

### Phase 1: Page Structure & Filters
1. Create new page `pages/9_Reports_Analytics.py`
2. Implement 5 tabs with headers
3. Build shared filter components (sprint selector, date range, section filter)

### Phase 2: Report 1 - Tickets & Tasks Count
1. Implement data aggregation functions
2. Build bar charts with Plotly
3. Wire up filters

### Phase 3: Report 2 - Tickets & Tasks Status
1. Implement pie chart views
2. Add open/completed logic
3. Add toggle for Tickets vs Tasks

### Phase 4: Report 3 - Efforts by Lab Section
1. Implement hours aggregation (logged vs expected)
2. Build stacked percentage bar chart
3. Implement percentage calculation with fixed denominator

### Phase 5: Report 4 - Effort Distribution by Team
1. Implement available hours calculation (including off days)
2. Build dual stacked bar charts
3. Calculate unaccounted hours category

### Phase 6: Report 5 - Task Completion Rate
1. Implement completion rate calculation
2. Build sprint-level chart
3. Build team member-level chart
4. Add optional enhancements

---

## UI/UX Guidelines

### Chart Library
- **Primary**: Plotly Express (`plotly.express`)
- **Reason**: Interactive, supports hover/tooltips, responsive

### Filter Behavior
- Sprint and Date Range are **mutually exclusive** (radio toggle)
- Multi-select filters use `st.multiselect`
- Filters persist within session

### Tooltips
- All charts show relevant counts/values on hover
- Pie charts: count + percentage
- Bar charts: absolute value + breakdown

### Responsive Design
- Use `st.columns` for filter layout
- Charts use `use_container_width=True`

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `pages/9_Reports_Analytics.py` | **CREATE** | New main reports page |
| `modules/reports_store.py` | **CREATE** | Data aggregation functions for reports |
| `components/report_filters.py` | **CREATE** | Shared filter components |
| `utils/chart_helpers.py` | **CREATE** | Plotly chart helper functions |

---

## Design Decisions (Confirmed)

1. **Time Window filter**: Uses **task creation date** (`task_created_dt`)
2. **Report 3 denominator**: Section filter does NOT change percentage denominator - total hours across ALL sections is used
3. **Report 4 available hours**: 8 hours per working day
4. **Completion rate logic**: Any task completed within a sprint window counts. Tasks can be assigned to multiple sprints.
5. **AD tickets**: **Excluded by default** from all reports (can add toggle to include if needed)

---

*Document created: 2026-01-26*
