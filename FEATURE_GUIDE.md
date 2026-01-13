# PBIDS Sprint Dashboard - Feature Guide

> **Document Purpose**: This comprehensive guide enables developers to rebuild the entire application from scratch without access to source code. It details all features, workflows, data structures, configurations, and UI components.

---

## 1. Application Overview

### 1.1 Purpose
The PBIDS Sprint Dashboard is a web-based application for managing sprint workflows, task assignments, and team capacity planning for the PBIDS (Pathology Business Intelligence and Decision Support) laboratory informatics team.

### 1.2 Technology Stack
- **Framework**: Streamlit (Python web framework)
- **Data Tables**: st-aggrid (AgGrid component for Streamlit)
- **Charts**: Plotly Express
- **Data Storage**: CSV files (local file system)
- **Configuration**: TOML files
- **Authentication**: Streamlit secrets-based authentication

### 1.3 Core Capabilities
- Import tasks from iTrack ticketing system
- Manage work backlogs and sprint assignments
- Plan sprint capacity with hours estimation
- Track worklog activity and team productivity
- Analyze completed tasks and sprint performance
- Export data to Excel/CSV

---

## 2. User Roles & Access Control

### 2.1 Administrator
- **Full access** to all features
- Upload and import tasks from iTrack
- Assign tasks to sprints
- Plan sprint capacity
- Configure sprint calendar and team settings
- View worklog activity reports
- Access Admin Config page

### 2.2 User (Team Member)
- View tasks assigned to their section
- Update task priorities (CustomerPriority, FinalPriority)
- Add comments to tasks
- View sprint progress and analytics
- **Cannot** access: Upload Tasks, Sprint Planning, Worklog Activity, Admin Config

### 2.3 Authentication Configuration
Authentication is managed via `.streamlit/secrets.toml`:
```toml
[passwords]
admin_username = "hashed_password"
user_username = "hashed_password"

[admin_users]
admins = ["admin_username1", "admin_username2"]
```

---

## 3. Data Architecture

### 3.1 Data Sources

#### Primary Data: Tasks (from iTrack)
- **Source File**: iTrack export (UTF-16 encoded, tab-delimited)
- **Storage**: `data/all_tasks.csv`
- **Relationship**: One ticket can have multiple tasks (1:N)

#### Secondary Data: Worklogs (from iTrack)
- **Source File**: iTrack worklog export (UTF-16 encoded, tab-delimited)
- **Storage**: `data/worklog_data.csv`
- **Relationship**: One task can have multiple worklog entries (1:N)
- **Join Key**: `TaskNum` links worklogs to tasks

#### Configuration Data
- **Sprint Calendar**: `data/sprint_calendar.csv`
- **Sections**: `.streamlit/sections.toml`
- **Team Members**: `.streamlit/itrack_mapping.toml`
- **Column Descriptions**: `.streamlit/column_descriptions.toml`

### 3.2 Task Data Schema

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| TaskNum | String | iTrack | Unique task identifier (e.g., "IR-12345") - **Primary Key** |
| TicketNum | Integer | iTrack | Parent ticket ID |
| TicketType | String | Derived | Type: IR, SR, PR, NC (extracted from Subject prefix) |
| Section | String | iTrack | Lab section/team |
| Status | String | iTrack | Task status (Logged, Assigned, Accepted, Waiting, Completed, Closed) |
| TicketStatus | String | iTrack | Ticket-level status from iTrack |
| AssignedTo | String | iTrack | Team member username |
| CustomerName | String | iTrack | Requester name |
| Subject | String | iTrack | Task description |
| TaskAssignedDt | DateTime | iTrack | Date task was assigned |
| TaskCreatedDt | DateTime | iTrack | Date task was created |
| TaskResolvedDt | DateTime | iTrack | Date task was resolved |
| TicketCreatedDt | DateTime | iTrack | Date ticket was created |
| TicketResolvedDt | DateTime | iTrack | Date ticket was resolved |
| DaysOpen | Integer | Calculated | Days since TaskAssignedDt |
| DaysCreated | Integer | Calculated | Days since TicketCreatedDt |
| CustomerPriority | Integer | Dashboard | Priority set by user (0-5) |
| FinalPriority | Integer | Dashboard | Final agreed priority (0-5) |
| HoursEstimated | Float | Dashboard | Effort estimate in hours |
| GoalType | String | Dashboard | "Mandatory" or "Stretch" |
| DependencyOn | String | Dashboard | Dependencies description |
| DependenciesLead | String | Dashboard | Dependency contact person |
| DependencySecured | String | Dashboard | Yes/Pending/No/NA |
| Comments | String | Dashboard | Free-text notes |
| SprintNumber | Integer | Assigned | Current sprint assignment |
| SprintsAssigned | String | Calculated | Comma-separated list of all sprints |
| OriginalSprintNumber | Integer | Calculated | First sprint where task appeared |
| UniqueTaskId | String | Calculated | Format: "TaskNum_SX" (X = original sprint) |
| TaskCount | String | Calculated | Position in ticket (e.g., "1/3") |
| TicketTotalTimeSpent | Float | iTrack | Total hours on ticket |
| TaskMinutesSpent | Float | iTrack | Minutes logged on task |

### 3.3 Worklog Data Schema

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| RecordId | Integer | iTrack | Unique worklog entry ID |
| TaskNum | String | iTrack | Task identifier (join key) |
| Owner | String | iTrack | Team member who logged |
| MinutesSpent | Float | iTrack | Minutes logged in this entry |
| Description | String | iTrack | Worklog description |
| LogDate | DateTime | iTrack | Date of activity |
| SprintNumber | Integer | Calculated | Sprint based on LogDate |
| TicketType | String | Joined | From tasks table |
| Section | String | Joined | From tasks table |
| CustomerName | String | Joined | From tasks table |
| Subject | String | Joined | From tasks table |
| Status | String | Joined | From tasks table |
| AssignedTo | String | Joined | From tasks table |

### 3.4 Sprint Calendar Schema

| Column | Type | Description |
|--------|------|-------------|
| SprintNumber | Integer | Sequential sprint identifier |
| SprintName | String | Display name (e.g., "PIBIDS Sprint 5") |
| SprintStartDt | Date | Start date (Thursday) |
| SprintEndDt | Date | End date (Wednesday) |

---

## 4. Task Lifecycle

### 4.1 Task Import
Tasks are imported from iTrack extract files (CSV format) using the **Field Ownership Model**:

**Field Ownership:**
| Ownership | Fields | Import Behavior |
|-----------|--------|----------------|
| **iTrack-owned** | TaskNum, TicketNum, Status, TicketStatus, AssignedTo, Subject, Section, CustomerName, dates | Always updated from iTrack |
| **Dashboard-owned** | SprintsAssigned, CustomerPriority, FinalPriority, GoalType, HoursEstimated, Dependencies, Comments | Never overwritten by import |
| **Computed** | OriginalSprintNumber, TicketType, DaysOpen | Calculated during import |

**Import Behavior:**
- **TaskNum** is used as the unique identifier to match existing tasks
- **Existing tasks**: Only iTrack-owned fields are updated; dashboard annotations preserved
- **New tasks**: Initialized with default values for dashboard fields
- Tasks are automatically assigned an **Original Sprint Number** based on TaskAssignedDt
- **Open tasks** go to the Work Backlogs (no sprint assignment)
- **Completed/Closed tasks** are auto-assigned to their original sprint

**Import Report:**
After import, a detailed report shows:
- New tasks breakdown by status
- Task status changes (old → new transitions)
- Ticket status changes (old → new transitions)
- Field changes summary

### 4.2 Work Backlogs
All open tasks appear in the Work Backlogs regardless of sprint assignment. This serves as a central pool where administrators can:
- View all pending work
- Filter by days open, ticket age, section, status, and assignee
- Select tasks for sprint assignment

### 4.3 Sprint Assignment (v1.2)
Administrators assign tasks from the Work Backlogs to **current or future sprints only** (past sprints are not available for assignment). A task can be assigned to **multiple sprints** (e.g., if work spans across sprints). The assignment is tracked as a comma-separated list of sprint numbers in the `SprintsAssigned` field.

**Assignment Process:**
1. Select tasks using checkboxes in Work Backlogs
2. Choose target sprint from dropdown
3. Click "Assign to Sprint" button
4. Sprint number is added to SprintsAssigned (e.g., "1" → "1, 2")

### 4.3.1 Sprint Removal (v1.2)
Administrators can remove tasks from sprints via the Sprint Planning page:

1. Navigate to Sprint Planning for the target sprint
2. Change the SprintNumber dropdown to **blank** (empty)
3. Click "Save Changes"
4. The current sprint is removed from SprintsAssigned

**Important:** Removing from one sprint does NOT affect other sprint assignments.

| Before | Action (in Sprint 1) | After |
|--------|---------------------|-------|
| SprintsAssigned: "1" | Set SprintNumber blank | SprintsAssigned: "" (backlog) |
| SprintsAssigned: "1, 2" | Set SprintNumber blank | SprintsAssigned: "2" |

### 4.4 Sprint Planning
The Sprint Planning page shows **only current and future sprints**. By default, a sprint has **no tasks** until the admin explicitly assigns them from Work Backlogs.

Once tasks are assigned to a sprint, the Sprint Planning page allows:
- Setting estimated hours for each task
- Assigning Goal Type (Mandatory or Stretch)
- Adding comments
- Monitoring capacity utilization per team member

### 4.5 Task Completion
When tasks are completed in iTrack and re-imported:
- Status updates automatically
- Completed tasks are moved to the **Completed Tasks** page for historical analysis
- Completed tasks are no longer subject to sprint planning

---

## 5. Dashboard Pages

### 5.1 📊 Dashboard (Home)
**File**: `pages/1_📊_Dashboard.py`

The main overview page showing:
- **Current Sprint** metrics and progress
- **Task counts** by status (Open, In Progress, Completed, Canceled)
- **Section breakdown** with task distribution
- **Quick stats**: Priority 5 tasks, IR count, SR count
- **Capacity summary** (Admin only): Hours allocated vs. available per team member

**Filters available:**
- Section
- Status
- Assignee

**UI Components:**
- Metric cards using `st.metric()`
- AgGrid table with task list
- Expandable table toggle

---

### 5.2 📤 Upload Tasks
**File**: `pages/2_📤_Upload_Tasks.py`  
**Access**: Admin only

Used to import tasks and worklogs from iTrack.

**Two Import Types:**
1. **Task Import**: Main iTrack task export
2. **Worklog Import**: iTrack worklog/activity export

**Process:**
1. Upload an iTrack extract CSV file (UTF-16 encoded, tab-delimited)
2. System maps iTrack columns to dashboard schema
3. Preview imported data before confirming
4. Tasks are added to the system with proper sprint assignments

**Import behavior (Field Ownership Model):**
- **TaskNum** is the unique identifier for matching tasks
- **Existing tasks**: Only iTrack-owned fields updated (Status, TicketStatus, AssignedTo, Subject, dates)
- **Dashboard-owned fields preserved**: SprintsAssigned, CustomerPriority, FinalPriority, GoalType, HoursEstimated, Dependencies, Comments
- **New tasks**: Added to Work Backlogs with default dashboard values
- Worklogs are appended (duplicates detected by RecordId)

**Import Report displays:**
- New tasks by status (with open/closed indicators)
- Task status changes (aggregated and individual)
- Ticket status changes (aggregated and individual)
- Field changes summary

**Column Mapping** (iTrack → Dashboard):
- `Task ID` → `TaskNum`
- `Ticket ID` → `TicketNum`
- `Task_Status` → `Status`
- `Ticket_Status` → `TicketStatus`
- `Task_Owner` → `AssignedTo`
- `Ticket_Subject` → `Subject`
- `Section` → `Section`
- `Profilefullname` → `CustomerName`

---

### 5.3 📋 Sprint View
**File**: `pages/3_📋_Sprint_View.py`

View tasks assigned to a specific sprint.

**Features:**
- Select any sprint from dropdown
- View all tasks in that sprint with key details
- Filter by Section, Status, Ticket Type
- Days Open tracking with visual alerts for aging tasks
- **Expandable table** toggle for fullscreen view

**Tabs:**
1. **All Tasks**: Complete task list for selected sprint
2. **By Section**: Tasks grouped by section

**Displayed columns:**
- Task #, Ticket #, Type, Section
- Status, TicketStatus, Assignee, Subject
- Hours Estimated, Days Open

**Table Features:**
- Sortable columns
- Column tooltips with descriptions
- Pagination disabled (shows all rows)

---

### 5.4 👥 Section View
**File**: `pages/4_👥_Section_View.py`

View and manage tasks by section (team).

**Features:**
- Filter by Section to see team workload
- Filter by Status, Priority range, Assignee
- **Editable fields** (for open tasks only):
  - CustomerPriority
  - Comments
- At-risk task highlighting
- Priority and status breakdown charts
- **Expandable table** toggle

**Priority Scale:**
| Value | Label | Color |
|-------|-------|-------|
| 5 | Critical | 🔴 Red |
| 4 | High | 🟠 Orange |
| 3 | Medium | 🟡 Yellow |
| 2 | Low | 🟢 Green |
| 1 | Minimal | ⚪ White |
| 0/None | Not set | ⚫ Gray |

---

### 5.5 📈 Analytics
**File**: `pages/5_📈_Analytics.py`

Visual analytics and charts for sprint performance.

**Includes:**
- Task distribution by status (pie chart)
- Priority breakdown (bar chart)
- Section workload comparison
- Completion trends over time
- Ticket type distribution (IR, SR, PR, NC)

**Chart Library**: Plotly Express

---

### 5.6 ✅ Completed Tasks
**File**: `pages/6_✅_Completed_Tasks.py`

Historical view of all completed tasks.

**Features:**
- View all completed tasks with their completion sprint
- Filter by sprint, section, assignee, ticket type
- **Task grouping**: Multi-task tickets are grouped together with alternating row colors
- Search across all completed tasks
- Trends and analytics for completion patterns
- Export completed tasks data to Excel/CSV

**Tabs:**
1. **By Sprint**: Tasks grouped by completion sprint
2. **All Tasks**: Complete list with filters
3. **Trends**: Completion analytics over time

**Note:** Completed tasks are for historical analysis only and are not available in Sprint Planning.

---

### 5.7 ✏️ Sprint Planning
**File**: `pages/7_✏️_Sprint_Planning.py`  
**Access**: Admin only

The primary workspace for planning sprint capacity.

**Important:** This page shows **only current and future sprints**. Past sprints are not available for planning.

**Features:**

**Task Table (Editable AgGrid):**
- View tasks assigned to current/selected sprint (empty by default until tasks are assigned)
- **No tasks appear by default** - admin must assign tasks from Work Backlogs first
- Columns include: Status, TicketStatus, AssignedTo, Subject, etc.
- Edit directly in the table:
  - **SprintNumber**: Dropdown (blank + all sprint numbers) - **blank = remove from this sprint (v1.2)**
  - **HoursEstimated**: Numeric input (hours)
  - **GoalType**: Dropdown (None, Mandatory, Stretch)
  - **Comments**: Multi-line text editor (popup on click)
  - **CustomerPriority**: Dropdown (0-5)
  - **FinalPriority**: Dropdown (0-5)
  - **DependencyOn**: Dropdown (Yes, No, blank)
  - **DependenciesLead**: Text input
  - **DependencySecured**: Dropdown (Yes, Pending, No, blank)
- Click "Save Changes" button to persist edits
- **Expandable table** toggle for fullscreen editing

**Sprint Removal (v1.2):**
- Set SprintNumber to blank to remove task from current sprint
- Only removes from THIS sprint - task stays in other assigned sprints
- If task was only in this sprint, it returns to backlog

**Capacity Summary Panel:**
- Shows each team member with their allocated hours
- **Mandatory capacity**: 48 hours per person per sprint (configurable)
- **Stretch capacity**: 16 hours per person per sprint (configurable)
- Color-coded bars: Green (under), Yellow (warning), Red (over)
- Real-time updates as HoursEstimated changes

**Goal Types:**
- **Mandatory**: Core sprint commitment (counts toward mandatory limit)
- **Stretch**: Additional work if capacity allows (counts toward stretch limit)

**Column Visibility Toggle:**
- Show/hide columns dynamically
- Customize view for planning workflow

**Columns displayed:**
- SprintNumber, TaskOrigin, TicketNum, TaskCount
- TicketType, Section, CustomerName, TaskNum
- Status, TicketStatus, AssignedTo, Subject
- TicketCreatedDt, TaskCreatedDt, DaysOpen
- CustomerPriority, FinalPriority, GoalType
- DependencyOn, DependenciesLead, DependencySecured
- Comments, HoursEstimated, TaskHoursSpent, TicketHoursSpent
- SprintsAssigned

---

### 5.8 📋 Work Backlogs
**File**: `pages/8_📋_Work_Backlogs.py`  
**Access**: Admin only

Central pool of all open tasks awaiting sprint assignment.

**Summary Cards (Top):**
Metric cards showing open items by ticket type:
- **SR**: Service Requests count
- **PR**: Problem Requests count
- **IR**: Incident Requests count
- **NC**: Not Categorized count
- **AD**: Administrative count

**Filters:**
- **Section**: Filter by team (dropdown)
- **Status**: Filter by task status (dropdown)
- **Assignee**: Filter by team member (dropdown)
- **DaysOpen (Task) More Than**: Numeric input (days)
- **Days Created (Ticket) More Than**: Numeric input (days)

**Column Visibility Toggle:**
- Show/hide columns dynamically

**Sprint Assignment:**
- Select tasks using checkbox column in table
- Choose target sprint from dropdown (**only current and future sprints**)
- Click "Assign to Sprint" button
- Sprint is added to SprintsAssigned column (e.g., "1" → "1, 2")
- Tasks remain visible in backlogs but now have sprint assignment
- Past sprints are not available for assignment

**Editable Fields (v1.2):**
- **FinalPriority**: Dropdown (0-5)
- **GoalType**: Dropdown (Mandatory, Stretch, blank)
- **DependencyOn**: Dropdown (Yes, No, blank)
- **DependenciesLead**: Text popup editor
- **DependencySecured**: Dropdown (Yes, Pending, No, blank)
- **Comments**: Text popup editor
- Click "Save Changes" button to persist edits

**Table Features:**
- AgGrid with sortable/filterable columns
- Column header tooltips with descriptions
- Editable columns marked with ✏️ prefix
- **Expandable table** toggle

**Columns displayed:**
- SprintsAssigned (with checkbox for selection)
- TicketNum, TaskCount, TicketType, Section
- TaskNum, Status, TicketStatus, AssignedTo, CustomerName
- Subject, DaysOpen
- TicketCreatedDt, TaskCreatedDt
- CustomerPriority, ✏️ FinalPriority, ✏️ GoalType
- ✏️ DependencyOn, ✏️ DependenciesLead, ✏️ DependencySecured
- ✏️ Comments, HoursEstimated

---

### 5.9 📊 Worklog Activity
**File**: `pages/9_📊_Worklog_Activity.py`  
**Access**: Admin only

Activity tracking report based on iTrack worklog data.

**Data Source:**
- Separate iTrack export file (Worklog table)
- Imported via the Upload Tasks page
- Each entry represents a team member's activity log for a task
- **Joined with tasks table** to get TicketType, Section, etc.

**Header Metrics:**
- Total Logs (count of worklog entries)
- Total Hours (sum of minutes / 60)
- Unique Users
- Current Sprint indicator

**Report Tabs:**

#### Tab 1: 📅 Daily Activity
**Filters:**
- **Sprint**: Select sprint (dropdown)
- **Ticket Type**: Filter by IR, SR, PR, NC, etc. (dropdown)
- **Section**: Filter by lab section (dropdown)

**Three Pivot Tables:**

1. **Work Log Entry Frequency by User & Date**
   - Rows: Team members
   - Columns: Dates (MM/DD format)
   - Values: Count of worklog entries
   - Color gradient: Blues
   - Shows all sprint dates (not just dates with activity)
   - Weekend columns highlighted with light purple background

2. **Work Logged Hours by User & Date**
   - Rows: Team members
   - Columns: Dates (MM/DD format)
   - Values: Hours (converted from minutes, 1 decimal)
   - Color gradient: Greens
   - Weekend columns highlighted

3. **Tasks Worked by User & Date**
   - Rows: Team members
   - Columns: Dates (MM/DD format)
   - Values: Count of unique tasks (not log entries)
   - Color gradient: Oranges
   - Weekend columns highlighted

**Export:** Excel download button

#### Tab 2: 👤 By User
- Select individual team member from dropdown
- Summary metrics: Total logs, hours, days active, tasks worked
- Activity timeline chart (dual Y-axis: logs + hours)
- Recent activity detail table

#### Tab 3: 📈 Sprint Summary
- Total activity metrics per sprint (bar chart)
- Log volume and hours comparison
- User activity breakdown per sprint (stacked bar)

#### Tab 4: 📋 Raw Data
- All imported worklog entries in table
- Filters: User, Sprint, "Only entries with minutes logged"
- Export to Excel/CSV

---

### 5.10 ⚙️ Admin Config
**File**: `pages/10_⚙️_Admin_Config.py`  
**Access**: Admin only

System configuration page for administrators.

**Features:**
- **Sprint Calendar Management**: Add/edit sprints
- **Team Member Management**: Add/remove valid team members
- **Section Configuration**: Manage valid sections
- **Capacity Settings**: Configure hours per person per sprint
- **Name Mapping**: Map usernames to display names

---

## 6. Key Concepts

### 6.1 Sprint Calendar
- **File**: `data/sprint_calendar.csv`
- **Schedule**: Two-week sprints (14 days)
- **Cycle**: Thursday to Wednesday
- Sprints are numbered sequentially
- Current sprint is auto-detected from system date

### 6.2 Task Types (TicketType)
Derived from the Subject/Summary field prefix:
| Type | Full Name | Description |
|------|-----------|-------------|
| IR | Incident Request | Urgent issues requiring immediate attention |
| SR | Service Request | Standard service requests |
| PR | Problem Request | Problem tickets for root cause analysis |
| NC | Not Categorized | Lab incidents, other items |
| AD | Administrative | Administrative tasks |

### 6.3 Task Status Workflow
iTrack workflow progression:
```
Logged → Assigned → Accepted → Waiting → Completed/Closed
```

| Status | Description |
|--------|-------------|
| Logged | Initial state, not yet assigned |
| Assigned | Assigned to team member |
| Accepted | Team member accepted the task |
| Waiting | Blocked, waiting on external input |
| Completed | Work finished |
| Closed | Task closed |
| Canceled | Task canceled |

### 6.4 Forever Tickets
Certain recurring tasks (identified by subject keywords like "Forever Ticket") are handled specially:
- Excluded from TAT (Turn Around Time) calculations
- Not flagged as at-risk regardless of age
- Typically used for ongoing maintenance or monitoring tasks

### 6.5 At-Risk Task Calculation
Tasks are flagged as at-risk based on Turn Around Time (TAT) thresholds:
- **IR tasks**: At risk if open > 60% of TAT threshold (default: 0.8 days)
- **SR tasks**: At risk if open > 18 days
- Warning indicators appear at 75% of TAT threshold

### 6.6 Dashboard-Only Fields
These fields are NOT imported from iTrack but managed within the dashboard:
| Field | Type | Description |
|-------|------|-------------|
| CustomerPriority | Integer (0-5) | Priority set by user/admin |
| FinalPriority | Integer (0-5) | Final agreed priority after review |
| Comments | Text | Notes and comments added by team |
| HoursEstimated | Float | Effort estimate for capacity planning |
| GoalType | String | "Mandatory" or "Stretch" |
| SprintsAssigned | String | Comma-separated list of assigned sprints |
| DependencyOn | Text | Dependencies description |
| DependenciesLead | Text | Dependency contact person |
| DependencySecured | String | Yes/Pending/No/NA |

### 6.7 Capacity Planning Rules
- **Mandatory capacity**: 48 hours per person per sprint (configurable)
- **Stretch capacity**: 16 hours per person per sprint (configurable)
- **Total available**: ~52 hours (65% of 80-hour sprint)
- Warning threshold at 87% of max

### 6.8 Multi-Task Tickets
- One ticket can have multiple tasks (1:N relationship)
- Tasks are grouped by TicketNum in displays
- TaskCount shows position (e.g., "1/3" = first of 3 tasks)
- Alternating row colors for visual grouping in tables

---

## 7. Configuration Files

### 7.1 `.streamlit/itrack_mapping.toml`
Main configuration file containing:

**File Format Settings:**
```toml
[file_format]
encoding = "utf-16"
delimiter = "\t"
```

**Sprint Schedule:**
```toml
[sprint_schedule]
duration_days = 14
start_weekday = 3  # Thursday
end_weekday = 2    # Wednesday
```

**Capacity Settings:**
```toml
[sprint_capacity]
max_hours = 52
warning_hours = 45
capacity_percentage = 65
```

**TAT Thresholds:**
```toml
[tat_thresholds]
ir_days = 0.8
sr_days = 22
warning_percent = 75
```

**Column Mapping** (iTrack → Internal):
```toml
[column_mapping]
"Ticket ID" = "Parent ID"
"Task ID" = "Task"
"Task_Status" = "Status"
"Task_Owner" = "Assignee"
# ... etc.
```

**Team Members:**
```toml
[team_members]
valid_team_members = ["username1", "username2", ...]
```

**Name Mapping:**
```toml
[name_mapping]
username1 = "Display Name 1"
username2 = "Display Name 2"
```

### 7.2 `.streamlit/sections.toml`
Valid lab sections for task assignment:
```toml
[sections]
valid_sections = [
    "LSC - Laboratory Service Center",
    "Micro - Microbiology",
    "CoreLab - Coagulation",
    # ... etc.
]
default_section = "PIBIDS"
```

### 7.3 `.streamlit/column_descriptions.toml`
Column header tooltips for AgGrid tables:
```toml
[descriptions]
TaskNum = "Task number within the ticket"
Status = "Current status of the task"
DaysOpen = "Number of days since task was assigned"
# ... etc.
```

### 7.4 `.streamlit/secrets.toml`
Authentication credentials (not in version control):
```toml
[passwords]
admin_user = "hashed_password"

[admin_users]
admins = ["admin_user1", "admin_user2"]
```

---

## 8. Workflows

### 8.1 Weekly Task Import (Admin)
1. Export tasks from iTrack as CSV (UTF-16, tab-delimited)
2. Go to **Upload Tasks** page
3. Select "Task Import" option
4. Upload the CSV file
5. Review column mapping and preview data
6. Confirm import
7. New tasks appear in Work Backlogs
8. Existing tasks are updated (preserving dashboard fields)

### 8.2 Worklog Import (Admin)
1. Export worklogs from iTrack as CSV
2. Go to **Upload Tasks** page
3. Upload the worklog CSV file
4. System uses **Date-Based Merge Strategy**:
   - For dates in upload: All existing records replaced
   - For dates NOT in upload: Existing records preserved
5. Review import statistics (Total, Valid, Dates, Replaced, Preserved)
6. View activity in **Worklog Activity** page

**Benefits:** Supports incremental updates (e.g., weekly exports) while preserving historical data

### 8.3 Sprint Planning (Admin)
1. Go to **Work Backlogs**
2. Filter to find relevant tasks (by section, days open, etc.)
3. Select tasks using checkboxes
4. Choose target sprint from dropdown
5. Click "Assign to Sprint" button
6. Go to **Sprint Planning** page
7. Select the sprint
8. Set HoursEstimated for each task
9. Set GoalType (Mandatory/Stretch)
10. Monitor capacity utilization panel
11. Adjust assignments if over capacity

### 8.4 Priority Update (User/Admin)
1. Go to **Section View** or **Sprint Planning**
2. Filter to your section
3. Click on CustomerPriority cell for any open task
4. Select new priority from dropdown (0-5)
5. Changes save automatically
6. Repeat for FinalPriority if needed

### 8.5 Adding Comments
1. Go to **Sprint Planning** or **Section View**
2. Click on Comments cell
3. Multi-line editor popup appears
4. Enter comments (include date prefix recommended)
5. Click away to save

### 8.6 Reviewing Sprint Progress
1. Go to **Dashboard** for overview metrics
2. Go to **Sprint View** for detailed task list
3. Go to **Analytics** for charts and trends
4. Go to **Section View** for team-specific breakdown
5. Go to **Worklog Activity** to see team activity

### 8.7 Reviewing Worklog Activity
1. Go to **Worklog Activity** page
2. Select sprint from dropdown
3. Optionally filter by Ticket Type or Section
4. View three pivot tables:
   - Work Log Entry Frequency (how often people log)
   - Work Logged Hours (time spent per day)
   - Tasks Worked (unique tasks per day)
5. Weekend columns are highlighted
6. Export data if needed

### 8.8 Historical Review
1. Go to **Completed Tasks** page
2. Select completed sprint from dropdown
3. View task details and completion metrics
4. Use search to find specific tasks across sprints
5. Export data for reporting

---

## 9. UI Components & Styling

### 9.1 AgGrid Tables
All data tables use st-aggrid with these features:
- **Sortable columns**: Click header to sort
- **Column tooltips**: Hover over header for description
- **Editable cells**: Click to edit (where allowed)
- **Checkbox selection**: For bulk operations
- **Pagination disabled**: Shows all rows by default
- **Expandable toggle**: Fullscreen view option

### 9.2 Color Coding
**Priority Colors** (for cells):
| Value | Color |
|-------|-------|
| 5 | Red (#ff6b6b) |
| 4 | Orange (#ffa500) |
| 3 | Yellow (#ffeb3b) |
| 2 | Green (#69db7c) |
| 1 | Light gray |
| 0 | Gray |

**Worklog Heatmaps:**
- Log frequency: Blues gradient
- Hours logged: Greens gradient
- Tasks worked: Oranges gradient
- Weekend columns: Light purple (#f8f5fc)

### 9.3 Metric Cards
Summary statistics displayed using `st.metric()`:
- Current Sprint indicator
- Task counts by type/status
- Capacity utilization

### 9.4 Charts
All charts use Plotly Express:
- Bar charts for comparisons
- Pie charts for distributions
- Line charts for trends
- Dual-axis charts for activity tracking

---

## 10. Data Persistence

### 10.1 Storage Format
- All task data stored in CSV format
- Location: `data/` directory
- Files:
  - `all_tasks.csv` - Main task data
  - `worklog_data.csv` - Worklog entries
  - `sprint_calendar.csv` - Sprint definitions

### 10.2 Save Behavior
- Changes save immediately on cell edit
- Task assignments persist across sessions
- Dashboard-only fields preserved during import
- Import updates existing tasks (by TaskNum) without losing dashboard fields

### 10.3 Backup Considerations
- CSV files should be backed up regularly
- Configuration files in `.streamlit/` should be version controlled
- Secrets file should NOT be in version control

---

## 11. Module Architecture

### 11.1 Core Modules (`modules/`)
| Module | Purpose |
|--------|---------|
| `task_store.py` | Task data management (CRUD operations) |
| `worklog_store.py` | Worklog data management, joins with tasks |
| `sprint_calendar.py` | Sprint date calculations and lookups |
| `sprint_generator.py` | Auto-generate sprint data for export |
| `capacity_validator.py` | Capacity planning calculations |
| `section_filter.py` | Team member and section filtering |
| `tat_calculator.py` | Turn Around Time calculations |
| `data_loader.py` | iTrack file import and column mapping |
| `user_store.py` | User authentication and roles |

### 11.2 Utility Modules (`utils/`)
| Module | Purpose |
|--------|---------|
| `grid_styles.py` | AgGrid styling, color coding, fullscreen toggle |
| `name_mapper.py` | Username to display name mapping |
| `exporters.py` | Excel/CSV export functions |
| `formatters.py` | Date and number formatting |
| `date_utils.py` | Date calculations and parsing |
| `constants.py` | Application constants |

### 11.3 Components (`components/`)
| Component | Purpose |
|-----------|---------|
| `auth.py` | Authentication decorators and user info display |

---

## 12. Summary

The PBIDS Sprint Dashboard provides a complete workflow for:
- ✅ Importing tasks from iTrack
- ✅ Importing worklogs for activity tracking
- ✅ Managing work backlogs
- ✅ Assigning tasks to sprints
- ✅ Planning sprint capacity
- ✅ Tracking priorities and progress
- ✅ Monitoring team activity via worklogs
- ✅ Analyzing team performance
- ✅ Reviewing historical data
- ✅ Exporting data to Excel/CSV

All in a single, easy-to-use web interface accessible by both administrators and team members.

---

## Appendix A: File Structure

```
sprint_dashboard_PBIDS/
├── app.py                          # Main Streamlit app entry point
├── requirements.txt                # Python dependencies
├── .streamlit/
│   ├── config.toml                 # Streamlit configuration
│   ├── secrets.toml                # Authentication (not in git)
│   ├── itrack_mapping.toml         # Column mapping & settings
│   ├── sections.toml               # Valid sections list
│   └── column_descriptions.toml    # Column tooltip descriptions
├── data/
│   ├── all_tasks.csv               # Main task data
│   ├── worklog_data.csv            # Worklog entries
│   └── sprint_calendar.csv         # Sprint definitions
├── pages/
│   ├── 1_📊_Dashboard.py
│   ├── 2_📤_Upload_Tasks.py
│   ├── 3_📋_Sprint_View.py
│   ├── 4_👥_Section_View.py
│   ├── 5_📈_Analytics.py
│   ├── 6_✅_Completed_Tasks.py
│   ├── 7_✏️_Sprint_Planning.py
│   ├── 8_📋_Work_Backlogs.py
│   ├── 9_📊_Worklog_Activity.py
│   └── 10_⚙️_Admin_Config.py
├── modules/
│   ├── task_store.py
│   ├── worklog_store.py
│   ├── sprint_calendar.py
│   ├── sprint_generator.py
│   ├── capacity_validator.py
│   ├── section_filter.py
│   ├── tat_calculator.py
│   ├── data_loader.py
│   └── user_store.py
├── utils/
│   ├── grid_styles.py
│   ├── name_mapper.py
│   ├── exporters.py
│   ├── formatters.py
│   ├── date_utils.py
│   └── constants.py
├── components/
│   └── auth.py
└── documents/
    └── task_readme.csv             # Column documentation
```

---

## Appendix B: Dependencies

Key Python packages (from `requirements.txt`):
- `streamlit` - Web framework
- `streamlit-aggrid` - AgGrid table component
- `pandas` - Data manipulation
- `plotly` - Interactive charts
- `openpyxl` - Excel export
- `toml` - Configuration file parsing

---

*Document last updated: January 2026*
