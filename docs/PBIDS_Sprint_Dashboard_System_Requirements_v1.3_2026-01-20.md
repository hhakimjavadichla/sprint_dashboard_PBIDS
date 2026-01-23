# PBIDS Sprint Dashboard - System Requirements Document

**Version:** 1.3  
**Date:** January 20, 2026  
**Document Type:** Functional Requirements Specification  

---

## 1. Executive Summary

This document provides a comprehensive specification for the PBIDS Sprint Dashboard, a web-based sprint management system. The system enables teams to manage tasks through sprint cycles, track workload capacity, monitor Turn-Around Time (TAT) compliance, and facilitate team collaboration through role-based access.

The intended audience is a development team tasked with implementing a similar web application. This document describes **what** the system does (functional requirements), not how it is implemented.

---

## 2. System Overview

### 2.1 Application Purpose
The Sprint Dashboard manages task workflows across bi-weekly sprint cycles. It imports task data from an external ticketing system (iTrack), assigns tasks to sprints, tracks progress, monitors team capacity, and provides analytics.

### 2.2 Core Concepts

- **Sprint**: A two-week work cycle (14 days), typically Thursday-to-Wednesday
- **Task**: A unit of work derived from a ticket in the source system
- **Ticket**: A parent entity that may contain multiple tasks
- **Manual Sprint Assignment**: Tasks are explicitly assigned to sprints by admin (no automatic carryover)
- **TAT (Turn-Around Time)**: Target completion timeframes by ticket type
- **Field Ownership Model**: Defines which system (iTrack vs Dashboard) owns each field during imports
- **SprintsAssigned**: Comma-separated list tracking all sprint assignments for a task

### 2.3 Data Storage Options (v1.3)

The system supports two storage backends:

| Mode | Enable | Data Location |
|------|--------|---------------|
| **CSV** (default) | Default behavior | `data/*.csv` files |
| **SQLite** (optional) | `SPRINT_DASHBOARD_USE_SQLITE=true` | `data/sprint_dashboard.db` |

---

## 3. User Roles and Permissions

### 3.1 Role Definitions

| Role | Description |
|------|-------------|
| **Admin** | Full access to all features, can edit everything, manage users and configuration |
| **PBIDS User** | Read-only access, can view all sections but cannot edit any data |
| **Section Manager** | Can edit CustomerPriority, Dependency, DependencyLead(s), and Comments for tasks in their assigned section(s). Can submit sprint feedback. |
| **Section User** | Same permissions as Section Manager for their assigned section(s) |

### 3.2 Role-Based Access Matrix

| Feature/Page | Admin | PBIDS User | Section Manager | Section User |
|--------------|-------|------------|-----------------|--------------|
| Home/Dashboard | ✅ Full | ✅ View | ✅ View (own section) | ✅ View (own section) |
| Dashboard | ✅ Full | ✅ View | ✅ View (own section) | ✅ View (own section) |
| Upload Tasks | ✅ Full | ❌ No access | ❌ No access | ❌ No access |
| Sprint View | ✅ Full | ✅ View | ✅ View | ✅ View |
| Section View | ✅ Full (all sections) | ✅ View (all sections, read-only) | ✅ Edit (own section) | ✅ Edit (own section) |
| Analytics | ✅ Full | ✅ View | ✅ View (own section) | ✅ View (own section) |
| Completed Tasks | ✅ Full | ❌ No access | ❌ No access | ❌ No access |
| Sprint Planning | ✅ Full | ❌ No access | ❌ No access | ❌ No access |
| Work Backlogs & Sprint Assignment | ✅ Full | ❌ No access | ❌ No access | ❌ No access |
| Worklog Activity | ✅ Full | ❌ No access | ❌ No access | ❌ No access |
| Admin Config | ✅ Full | ❌ No access | ❌ No access | ❌ No access |
| Sprint Feedback | ✅ Full | ❌ No access | ✅ Submit/View | ❌ No access |

---

## 4. Editable Fields by Page

This section documents which fields can be edited on each page and by whom.

### 4.1 Work Backlogs Page (Admin Only)

| Field | Editor Type | Options/Format |
|-------|-------------|----------------|
| FinalPriority | Dropdown | 0, 1, 2, 3, 4, 5 |
| GoalType | Dropdown | '', 'Mandatory', 'Stretch' |
| DependencyOn | Dropdown | '', 'Yes', 'No' |
| DependenciesLead | Text popup | Free text (max 1000 chars) |
| DependencySecured | Dropdown | '', 'Yes', 'Pending', 'No' |
| Comments | Text popup | Free text (max 1000 chars) |

**Sprint Assignment:** Select tasks via checkbox, choose target sprint, click "Assign" button.

### 4.2 Section View Page (Admin, Section Manager, Section User)

| Field | Editor Type | Options/Format |
|-------|-------------|----------------|
| CustomerPriority | Dropdown | 0, 1, 2, 3, 4, 5 |
| DependencyOn | Dropdown | '', 'Yes', 'No' |
| DependenciesLead | Text popup | Free text |
| Comments | Text popup | Free text |

**Note:** Only open tasks can be edited. PBIDS Users have read-only access.

### 4.3 Sprint Planning Page (Admin Only)

| Field | Editor Type | Options/Format |
|-------|-------------|----------------|
| SprintNumber | Dropdown | All sprint numbers + blank (to remove from sprint) |
| CustomerPriority | Dropdown | 0, 1, 2, 3, 4, 5 |
| FinalPriority | Dropdown | 0, 1, 2, 3, 4, 5 |
| GoalType | Dropdown | '', 'Mandatory', 'Stretch' |
| DependencyOn | Dropdown | '', 'Yes', 'No' |
| DependenciesLead | Text popup | Free text |
| DependencySecured | Dropdown | '', 'Yes', 'Pending', 'No' |
| Comments | Text popup | Free text |
| HoursEstimated | Numeric | Decimal hours |

**Sprint Removal:** Set SprintNumber to blank to remove task from current sprint.

---

## 5. Sprint Assignment Logic (v1.3 - Manual Assignment Only)

### 5.1 No Automatic Carryover

**Important:** Tasks do **NOT** automatically carry over to the next sprint. The admin must explicitly assign each task to each sprint from the Work Backlogs. This provides full control over sprint scope and prevents unwanted task accumulation.

### 5.2 SprintsAssigned Field

The `SprintsAssigned` field is a comma-separated list that tracks all sprint assignments for a task.

**Examples:**
- `"1"` - Task assigned to Sprint 1 only
- `"1, 2"` - Task assigned to both Sprint 1 and Sprint 2
- `""` (empty) - Task in backlog, not assigned to any sprint

### 5.3 Assigning Tasks to Sprints

**Location:** Work Backlogs & Sprint Assignment page

**Process:**
1. Admin selects tasks using checkboxes in the grid
2. Admin selects target sprint from dropdown
3. Admin clicks "Assign {N} Task(s) to Sprint {X}" button
4. System adds sprint number to SprintsAssigned field
5. Task appears in Sprint Planning for that sprint

**Behavior:**
- If task already assigned to that sprint: Skipped with message
- SprintsAssigned updates: `"1"` → `"1, 2"` (adds Sprint 2)
- Task can be assigned to multiple sprints

### 5.4 Removing Tasks from Sprints

**Location:** Sprint Planning page

**Process:**
1. Admin views Sprint Planning for Sprint X
2. Admin changes SprintNumber dropdown to blank (empty)
3. Admin clicks "Save Changes"
4. System removes Sprint X from SprintsAssigned field

**Behavior:**
- Only removes the CURRENT sprint from SprintsAssigned
- Task remains in other assigned sprints
- If task was only in Sprint X: SprintsAssigned becomes empty (true backlog)

**Example:**
| Before | Action | After |
|--------|--------|-------|
| SprintsAssigned: "1" | Remove from Sprint 1 | SprintsAssigned: "" (backlog) |
| SprintsAssigned: "1, 2" | Remove from Sprint 1 | SprintsAssigned: "2" |
| SprintsAssigned: "1, 2, 3" | Remove from Sprint 2 | SprintsAssigned: "1, 3" |

### 5.5 Task Origin

When viewing a sprint, each task has a `TaskOrigin`:

| TaskOrigin | Description | Color |
|------------|-------------|-------|
| **Assigned** | Task manually assigned to this sprint by admin | 🔵 Blue |

**Note:** Since there is no automatic carryover, all tasks in a sprint are explicitly "Assigned" by the admin.

---

## 6. SQLite Database Support (v1.3)

### 6.1 Overview

The system supports an optional SQLite database backend for improved data integrity, performance, and concurrent access.

### 6.2 Enabling SQLite Mode

Set the following environment variables before running the application:

```bash
# Enable SQLite mode
export SPRINT_DASHBOARD_USE_SQLITE=true

# Optional: Custom database path (default: data/sprint_dashboard.db)
export SPRINT_DASHBOARD_DB_PATH=/path/to/custom.db

# Run the application
streamlit run app.py
```

### 6.3 SQLite Schema (Normalized)

| Table | Description |
|-------|-------------|
| `tickets` | Parent ticket information (ticket_num, status, dates, subject, customer, section) |
| `tasks` | Individual task records (task_num, ticket_num FK, status, assigned_to, dates) |
| `dashboard_task_annotations` | Dashboard-owned fields (sprints_assigned, priority, goal_type, comments) |
| `task_sprint_assignments` | Sprint assignment join table (task_num, sprint_number) |
| `worklogs` | Worklog entries (record_id, task_num, owner, minutes, log_date) |
| `users` | User accounts (username, password, role, section, active) |
| `offdays` | Off day configurations (sprint_number, team_member, off_date) |
| `feedback` | Sprint feedback (sprint_number, section, satisfaction, comments) |
| `sprint_calendar` | Sprint definitions (sprint_number, name, start_date, end_date) |
| `app_metadata` | Schema version tracking |

### 6.4 Compatibility View

A SQL view `task_flat_view` maintains compatibility with the existing UI by joining the normalized tables into a flat structure matching the CSV format.

### 6.5 Migration from CSV to SQLite

```bash
# Activate environment
mamba activate itrack_sprint_dashboard

# Run migration (preserves existing CSV files)
python -m modules.sqlite_migration --data-dir data/

# Run migration with overwrite (replaces existing SQLite DB)
python -m modules.sqlite_migration --data-dir data/ --overwrite
```

**Migration includes:**
- All tasks with annotations
- Sprint assignments
- Worklogs
- Users
- Off days
- Feedback
- Sprint calendar

### 6.6 Data Import with SQLite

When SQLite mode is enabled:
- iTrack task imports save directly to SQLite
- Worklog imports save directly to SQLite
- All UI operations use SQLite for persistence
- CSV files are not modified

---

## 7. Page Specifications

### 7.1 Home Page (app.py)

**Page Title:** "Sprint Dashboard (Prototype)"  
**Page Icon:** 📊

#### 7.1.1 Unauthenticated View
- Welcome message with application title
- Login form with:
  - **Username** field
  - **Password** field
  - **"🔐 Login"** button
- Help section explaining the application

#### 7.1.2 Authenticated View (Sidebar)
- **User Information Display:**
  - "👤 Logged in as: {display_name}"
  - "🔑 Role: {role}"
  - "📁 Section: {section}" (if applicable)
  - **"🚪 Logout"** button

- **Current Sprint Information:**
  - Sprint number and name
  - Date range (MM/DD - MM/DD/YYYY format)
  - Status indicator (🟢 Active, 🟡 Upcoming, etc.)

#### 7.1.3 Main Content (When Authenticated)
- Sprint overview with metrics:
  - **Total Tasks** count
  - **By Status** breakdown (Completed, In Progress, Pending)
  - **By Priority** breakdown
- Recent tasks table (last 10 open tasks)
- Navigation links to main pages

---

### 7.2 Dashboard Page

**Page Title:** "Dashboard (Prototype)"  
**Page Icon:** 📊  
**Access:** Authenticated users

#### 7.2.1 Header Section
- Title: "📊 Dashboard"
- Caption: "_Prototype — PBIDS Team_"
- User info display

#### 7.2.2 Task Overview Metrics (6 columns)
Row 1 - Ticket counts:
- **Total Current Tickets** - unique ticket count
- **SR** - Service Request count
- **PR** - Problem count
- **IR** - Incident Request count
- **NC** - Non-classified count
- **AD** - Admin Request count

Row 2 - Task counts (same categories)

#### 7.2.3 Sidebar Filters
- **Section** - multiselect, default "All"
- **Status** - multiselect, default "All"
- **Priority** - multiselect, default "All"
- **Assignee** - multiselect, default "All"

#### 7.2.4 Tabs
**Tab 1: "All Tasks"**
- Data table with all current sprint tasks
- Export buttons: "📥 Export CSV", "📥 Export Excel"

**Tab 2: "At Risk"**
- Tasks at risk of missing TAT thresholds
- Warning message: "⚠️ {count} tasks are at risk of missing TAT"

**Tab 3: "Capacity"**
- Team capacity breakdown by person
- Color-coded status indicators

---

### 7.3 Upload Tasks Page

**Page Title:** "Upload Tasks"  
**Page Icon:** 📤  
**Access:** Admin only

#### 7.3.1 Workflow Instructions
```
### Simplified Workflow

1. **Upload iTrack extract** with all tasks
2. **Tasks automatically appear** in Work Backlogs
3. **Assign tasks to sprints** from Work Backlogs page
4. **Plan and estimate** in Sprint Planning page
5. **Repeat each sprint** - upload new extract to update

### Manual Sprint Assignment (v1.3)

- **No automatic carryover** - tasks do NOT move to next sprint automatically
- Admin must explicitly assign tasks to each sprint from Work Backlogs
- This provides full control over sprint scope

### Field Ownership Model

- **iTrack-owned fields**: Always updated from imports (Status, TicketStatus, AssignedTo, Subject, dates)
- **Dashboard-owned fields**: Never overwritten by imports (SprintsAssigned, GoalType, Priority, Comments)
- **Computed fields**: Calculated during import (OriginalSprintNumber, TicketType, DaysOpen)
```

#### 7.3.2 Import Report
After import, displays:
- Summary metrics: Total Processed, New, Updated, Unchanged
- New tasks by status
- Task status changes
- Ticket status changes
- Field changes summary

---

### 7.4 Work Backlogs & Sprint Assignment Page

**Page Title:** "Work Backlogs & Sprint Assignment"  
**Page Icon:** 📋  
**Access:** Admin only

#### 7.4.1 Instructions
```
All **open tasks** appear here. As admin, you can:
- **Click checkbox** to select tasks for sprint assignment
- Assign tasks to **current or future sprints**
- Tasks can be assigned to multiple sprints over time
- Track sprint assignment history in the **Sprints Assigned** column
- Completed tasks are automatically moved to the **Completed Tasks** page
- **Edit fields** (FinalPriority, GoalType, Dependencies, Comments) directly in the table

**Note:** Tasks do NOT automatically carry over. You must manually assign tasks to each sprint.
```

#### 7.4.2 Sprint Assignment Section
- **Target Sprint** dropdown (current and future sprints only)
- Task selection checkboxes
- "📤 Assign {N} Task(s) to Sprint {SprintNum}" button

---

### 7.5 Sprint Planning Page

**Page Title:** "Sprint Planning"  
**Page Icon:** ✏️  
**Access:** Admin only

#### 7.5.1 Instructions
```
### Planning Workflow

1. **Edit cells directly** in the table below
2. **All fields are editable by admin**
3. **Click "Save Changes"** button to persist your edits
4. **Monitor capacity** - warnings appear if anyone exceeds limits

### Sprint Assignment

- **Change SprintNumber to blank**: Removes task from THIS sprint only
- **Change SprintNumber to different sprint**: Moves task to that sprint
- Tasks can be in multiple sprints - SprintsAssigned tracks all

### No Automatic Carryover (v1.3)

Tasks do NOT automatically move to the next sprint. If a task is not completed:
1. Go to Work Backlogs
2. Select the task
3. Assign it to the new sprint
```

#### 7.5.2 Capacity Summary
- Per-person breakdown:
  - Mandatory: ≤ 48 hrs (60%)
  - Stretch: ≤ 16 hrs (20%)
  - Total: 80 hrs (100%)
- Color-coded indicators: 🟢 OK, 🔴 Over limit

---

## 8. Data Model

### 8.1 Task Fields

| Field Name | Description | Source | Editable By |
|------------|-------------|--------|-------------|
| UniqueTaskId | Unique identifier for each task | System-generated | None |
| SprintNumber | Sprint the task is assigned to | System/Admin | Admin (Sprint Planning) |
| SprintName | Name of the sprint | System | None |
| SprintStartDt | Sprint start date | System | None |
| SprintEndDt | Sprint end date | System | None |
| OriginalSprintNumber | First sprint the task was assigned to | System | None |
| TaskOrigin | "Assigned" (all tasks are manually assigned) | Calculated | None |
| SprintsAssigned | Comma-separated list of all sprints | System | None |
| TicketNum | Parent ticket number | iTrack | None |
| TaskNum | Task number (**Primary Key** for imports) | iTrack | None |
| TaskCount | Position in ticket (e.g., "1/3") | Calculated | None |
| TicketType | SR, PR, IR, NC, or AD | iTrack | None |
| Section | Lab section/team | iTrack | None |
| CustomerName | Customer name | iTrack | None |
| Status | Task status | iTrack | Admin (Sprint View) |
| TicketStatus | Ticket-level status | iTrack | None |
| AssignedTo | Person assigned | iTrack | None |
| Subject | Task subject/title | iTrack | None |
| TicketCreatedDt | Ticket creation date | iTrack | None |
| TaskCreatedDt | Task creation date | iTrack | None |
| TaskAssignedDt | Date task was assigned to sprint | System | None |
| DaysOpen | Days since ticket creation | Calculated | None |
| CustomerPriority | Customer-assigned priority (0-5) | Manual | Admin, Section Manager/User |
| FinalPriority | Final priority (0-5) | Manual | Admin |
| GoalType | "", "Mandatory", or "Stretch" | Manual | Admin |
| DependencyOn | "Yes", "No", or "" | Manual | Admin, Section Manager/User |
| DependenciesLead | Dependency lead contact(s) | Manual | Admin, Section Manager/User |
| DependencySecured | "Yes", "Pending", "No", or "" | Manual | Admin |
| Comments | Free-text comments | Manual | Admin, Section Manager/User |
| HoursEstimated | Estimated hours | Manual | Admin |
| TaskHoursSpent | Hours spent on task | iTrack worklog | None |
| TicketHoursSpent | Total hours on ticket | iTrack worklog | None |

### 8.2 Field Ownership Model

| Ownership | Fields | Import Behavior |
|-----------|--------|-----------------|
| **iTrack-owned** | TaskNum, TicketNum, Status, TicketStatus, AssignedTo, Subject, Section, CustomerName, dates | Always updated from iTrack |
| **Dashboard-owned** | SprintsAssigned, CustomerPriority, FinalPriority, GoalType, HoursEstimated, DependencyOn, DependenciesLead, DependencySecured, Comments, StatusUpdateDt | Never overwritten by import |
| **Computed** | OriginalSprintNumber, TicketType, DaysOpen, UniqueTaskId, TaskCount | Calculated during import |

---

## 9. Workflows

### 9.1 Task Import Workflow

1. Admin exports tasks from iTrack (CSV format)
2. Admin navigates to Upload Tasks page
3. Admin uploads CSV file
4. System validates CSV structure
5. System imports tasks using **Field Ownership Model**:
   - **New tasks**: Added to task store with default dashboard values
   - **Existing tasks** (matched by TaskNum): Only iTrack-owned fields updated
   - **Dashboard annotations preserved**: SprintsAssigned, Priority, GoalType, Comments untouched
6. System displays **Detailed Import Report**
7. Tasks appear in Work Backlogs page

### 9.2 Sprint Assignment Workflow (Manual - v1.3)

1. Admin navigates to Work Backlogs & Sprint Assignment page
2. Admin views all open tasks
3. Admin selects tasks using checkboxes
4. Admin selects target sprint from dropdown
5. Admin clicks "Assign to Sprint" button
6. System adds sprint number to **SprintsAssigned** field
7. Tasks appear in Sprint Planning for that sprint

**Important:** There is NO automatic carryover. Admin must repeat this process for each sprint.

### 9.3 Sprint Removal Workflow

1. Admin navigates to Sprint Planning page for Sprint X
2. Admin locates task to remove from sprint
3. Admin changes SprintNumber dropdown to **blank** (empty)
4. Admin clicks "Save Changes"
5. System removes Sprint X from SprintsAssigned field
6. **Only Sprint X is removed** - task remains in other assigned sprints

### 9.4 Sprint Planning Workflow

1. Admin navigates to Sprint Planning page
2. Admin selects sprint to plan
3. Admin edits planning fields:
   - HoursEstimated for capacity planning
   - GoalType (Mandatory/Stretch) for capacity limits
   - Priority fields
   - Dependencies
   - Comments
   - **SprintNumber** (blank to remove, or different number to move)
4. Admin monitors capacity summary
5. Admin clicks Save Changes

### 9.5 Worklog Import Workflow

1. Admin exports worklogs from iTrack (CSV format)
2. Admin navigates to Upload Tasks page, Worklog section
3. Admin uploads worklog CSV file
4. System imports worklogs using **Date-Based Merge Strategy**:
   - **For dates in upload**: All existing records for those dates are replaced
   - **For dates NOT in upload**: Existing records are preserved
5. System displays import statistics
6. Worklogs available in Worklog Activity page

---

## 10. Configuration

### 10.1 Sprint Schedule Configuration

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| duration_days | 14 | Sprint length in days |
| start_weekday | 3 | Start day (0=Monday, 3=Thursday) |
| end_weekday | 2 | End day (0=Monday, 2=Wednesday) |

### 10.2 Capacity Configuration

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| max_hours | 52 | Maximum capacity per person |
| warning_hours | 45 | Warning threshold |

### 10.3 Capacity Limits by Goal Type

| Goal Type | Hours Limit | Percentage |
|-----------|-------------|------------|
| Mandatory | 48 hours | 60% |
| Stretch | 16 hours | 20% |
| Total | 80 hours | 100% |

### 10.4 TAT Thresholds

| Ticket Type | At-Risk Threshold | Exceeded Threshold |
|-------------|-------------------|-------------------|
| IR (Incident) | 0.6 days | 0.8 days |
| SR (Service) | 18 days | 22 days |

### 10.5 Environment Variables (v1.3)

| Variable | Default | Description |
|----------|---------|-------------|
| `SPRINT_DASHBOARD_USE_SQLITE` | `false` | Enable SQLite backend |
| `SPRINT_DASHBOARD_DB_PATH` | `data/sprint_dashboard.db` | SQLite database path |

---

## 11. Validation Rules

### 11.1 User Management

- Username must be unique
- Cannot delete users (only deactivate)
- Cannot deactivate last active Admin
- Section Manager and Section User roles require at least one section assigned

### 11.2 Sprint Calendar

- Sprint numbers must be unique
- End date must be after start date
- Sprints cannot be deleted (historical data integrity)

### 11.3 Task Status Updates

- Status update date cannot be before task assigned date
- Only closed statuses can be selected for closing tasks

### 11.4 Sprint Assignment (v1.3)

- Tasks can be assigned to multiple sprints
- Removing from one sprint doesn't affect other sprint assignments
- SprintsAssigned field maintains comma-separated history
- **No automatic carryover** - all assignments are manual

### 11.5 Task Import

- TaskNum is the unique identifier for matching tasks
- iTrack-owned fields are always updated from imports
- Dashboard-owned fields are never overwritten by imports

---

## 12. Glossary

| Term | Definition |
|------|------------|
| **Backlog** | Collection of all open tasks not yet assigned to a sprint |
| **Capacity** | Available working hours for a team member (default 80 hours/sprint) |
| **Dashboard-owned field** | Field managed by the dashboard, never overwritten by iTrack imports |
| **Field Ownership Model** | System defining which fields are updated during imports vs preserved |
| **GoalType** | Classification of task importance: Mandatory (must complete) or Stretch (if time permits) |
| **iTrack** | Source ticketing system from which task data is imported |
| **iTrack-owned field** | Field sourced from iTrack, always updated during imports |
| **Manual Sprint Assignment** | Tasks are explicitly assigned to sprints by admin (no automatic carryover) |
| **Off Day** | Day when a team member is unavailable (vacation, sick leave, etc.) |
| **Sprint** | Two-week work cycle (14 days) |
| **SprintsAssigned** | Comma-separated list tracking all sprint assignments for a task |
| **SQLite Mode** | Optional database backend for improved data integrity |
| **TAT** | Turn-Around Time - target completion timeframe for a ticket type |
| **Ticket** | Parent work item that may contain multiple tasks |
| **TicketStatus** | Status of the parent ticket from iTrack |
| **Task** | Individual unit of work, child of a ticket |
| **TaskNum** | Unique task identifier, used as primary key for import matching |
| **Worklog** | Time tracking entry recording work performed |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-05 | PBIDS Team | Initial document |
| 1.1 | 2026-01-07 | PBIDS Team | Added Field Ownership Model, TicketStatus field, Comprehensive Import Report, TaskNum as primary key, Date-based merge for worklog imports |
| 1.2 | 2026-01-13 | PBIDS Team | Added Editable Fields by Page section, Sprint Assignment/Removal logic documentation, SprintsAssigned field behavior, Centralized editable fields configuration, Work Backlogs editable fields, Sprint Planning sprint removal via blank SprintNumber |
| 1.3 | 2026-01-20 | PBIDS Team | **Manual Sprint Assignment** - removed automatic carryover, all sprint assignments are now explicit by admin. **SQLite Database Support** - added optional SQLite backend with normalized schema, migration tool, and environment variable configuration. Simplified TaskOrigin to "Assigned" only. |

---

*End of Document*
