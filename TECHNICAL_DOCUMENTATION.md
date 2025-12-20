# PBIDS Sprint Dashboard — Technical Documentation

**Version:** 0.3.0  
**Last Updated:** December 19, 2024  
**Author:** PIBIDS Team

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Project Structure](#3-project-structure)
4. [Configuration Files](#4-configuration-files)
5. [Core Modules](#5-core-modules)
6. [Pages (UI)](#6-pages-ui)
7. [Components](#7-components)
8. [Utilities](#8-utilities)
9. [Models](#9-models)
10. [Data Flow](#10-data-flow)
11. [Authentication System](#11-authentication-system)
12. [Business Logic](#12-business-logic)
13. [Sprint Assignment Logic](#13-sprint-assignment-logic)
14. [Capacity Planning](#14-capacity-planning)
15. [Troubleshooting Guide](#15-troubleshooting-guide)
16. [Upgrade Guide](#16-upgrade-guide)

---

## 1. System Overview

### Purpose
The PBIDS Sprint Dashboard is a Streamlit-based web application for managing sprint workflows. It imports task data from iTrack, manages task assignments through Work Backlogs, tracks capacity with Goal Type planning, and provides role-based views for different users.

### Key Features
- **Work Backlogs**: Central hub for all open tasks; admin assigns tasks to sprints
- **SprintsAssigned Tracking**: Tasks can be assigned to multiple sprints; history tracked in comma-separated list
- **Goal Type Planning**: Mandatory (60% capacity) vs Stretch (20% capacity) goals
- **Capacity Management**: Per-person limits: 48 hrs Mandatory, 16 hrs Stretch, 80 hrs Total
- **No Automatic Carryover**: Admin must explicitly assign tasks to each sprint
- **TAT Monitoring**: Automatic priority escalation for IR (0.8 days) and SR (22 days)
- **Role-Based Access**: Admin (full access) and Section User (read-only filtered view)
- **Name Mapping**: Convert iTrack account names to display names
- **Forever Ticket Exclusion**: Automatically excludes standing meetings and miscellaneous meetings
- **Team Member Filtering**: Filter tasks by configured team members only
- **Color-Coded Tables**: Status, Priority, Days Open, TaskOrigin columns are color-coded

### Technology Stack
| Component | Technology |
|-----------|------------|
| Web Framework | Streamlit 1.29+ |
| Data Processing | Pandas 2.1+ |
| Visualization | Plotly 5.18+ |
| Interactive Tables | streamlit-aggrid 0.3.4 |
| Data Validation | Pydantic 2.5+ |
| Config Format | TOML |

---

## 2. Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         STREAMLIT UI                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ Home    │ │Dashboard│ │ Upload  │ │ Sprint  │ │ Section │   │
│  │ (app)   │ │         │ │ Tasks   │ │ View    │ │ View    │   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘   │
│       │           │           │           │           │         │
│  ┌────┴───────────┴───────────┴───────────┴───────────┴────┐   │
│  │                     COMPONENTS                            │   │
│  │  auth.py │ metrics_dashboard.py │ at_risk_widget.py      │   │
│  └────────────────────────┬─────────────────────────────────┘   │
└───────────────────────────┼─────────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────────┐
│                     BUSINESS LOGIC                               │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐       │
│  │   TaskStore    │ │ SprintCalendar │ │   DataLoader   │       │
│  │  (Singleton)   │ │  (Singleton)   │ │                │       │
│  └───────┬────────┘ └───────┬────────┘ └───────┬────────┘       │
│          │                  │                  │                 │
│  ┌───────┴──────────────────┴──────────────────┴───────┐        │
│  │              section_filter.py                       │        │
│  │              tat_calculator.py                       │        │
│  │              capacity_validator.py                   │        │
│  └──────────────────────────────────────────────────────┘        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────┐
│                         DATA LAYER                               │
│  ┌────────────────────┐  ┌────────────────────┐                 │
│  │  data/all_tasks.csv │  │ data/sprint_       │                 │
│  │  (Task Store)       │  │ calendar.csv       │                 │
│  └────────────────────┘  └────────────────────┘                 │
│  ┌────────────────────────────────────────────┐                 │
│  │  .streamlit/itrack_mapping.toml (Config)   │                 │
│  └────────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

### Design Patterns

1. **Singleton Pattern**: `TaskStore` and `SprintCalendar` use singleton pattern for global state
2. **Configuration-Driven**: All mappings and settings are in TOML config files
3. **Separation of Concerns**: UI (pages) → Components → Modules → Data
4. **Defensive Loading**: Graceful handling of missing files and invalid data

---

## 3. Project Structure

```
sprint_dashboard/
├── app.py                      # Main entry point, home page
├── requirements.txt            # Python dependencies
├── README.md                   # User documentation
├── WORKFLOW_DIAGRAM.md         # Visual workflow guide
├── TECHNICAL_DOCUMENTATION.md  # This file
│
├── .streamlit/                 # Streamlit configuration
│   ├── config.toml            # Streamlit settings (theme, etc.)
│   ├── secrets.toml           # Authentication credentials (gitignored)
│   ├── secrets.toml.template  # Template for secrets
│   ├── itrack_mapping.toml    # Column mapping & business config
│   └── sections.toml          # Valid lab sections list
│
├── pages/                      # Streamlit pages (auto-discovered)
│   ├── 1_📊_Dashboard.py      # Admin dashboard with filters
│   ├── 2_📤_Upload_Tasks.py   # iTrack CSV import
│   ├── 3_📋_Sprint_View.py    # Sprint details & task updates
│   ├── 4_👥_Section_View.py   # Section-filtered read-only view
│   ├── 5_📈_Analytics.py      # Charts and visualizations
│   └── 6_📚_Past_Sprints.py   # Historical sprint archive
│
├── modules/                    # Core business logic
│   ├── __init__.py
│   ├── task_store.py          # Central task management (CRITICAL)
│   ├── sprint_calendar.py     # Sprint window management
│   ├── data_loader.py         # CSV import/export with mapping
│   ├── section_filter.py      # Section-based filtering
│   ├── sprint_generator.py    # Sprint creation logic
│   ├── tat_calculator.py      # TAT escalation logic
│   └── capacity_validator.py  # Workload validation
│
├── components/                 # Reusable UI components
│   ├── __init__.py
│   ├── auth.py                # Authentication system
│   ├── metrics_dashboard.py   # Metric display widgets
│   ├── at_risk_widget.py      # At-risk tasks display
│   └── capacity_widget.py     # Capacity visualization
│
├── utils/                      # Utility functions
│   ├── __init__.py
│   ├── constants.py           # Configuration constants (from TOML)
│   ├── date_utils.py          # Date manipulation helpers
│   ├── formatters.py          # Display formatting
│   ├── exporters.py           # CSV/Excel export utilities
│   ├── grid_styles.py         # AgGrid styling (CSS)
│   └── name_mapper.py         # Account → Display name mapping
│
├── models/                     # Data models and validation
│   ├── __init__.py
│   ├── task.py                # Task data model
│   ├── sprint.py              # Sprint data model
│   └── validation.py          # Data validation functions
│
├── data/                       # Data files (gitignored CSVs)
│   ├── .gitkeep               # Keeps directory in git
│   ├── all_tasks.csv          # Central task store
│   ├── sprint_calendar.csv    # Sprint date definitions
│   └── itrack_*.csv           # Uploaded iTrack files
│
├── documents/                  # Business documentation
│   └── Sprint_Logics.docx     # Business requirements
│
└── tables/                     # Reference data
    └── *.csv                   # Lookup tables
```

---

## 4. Configuration Files

### 4.1 `.streamlit/itrack_mapping.toml`

This is the **primary configuration file** that controls:

#### File Format Section
```toml
[file_format]
encoding = "utf-16"          # iTrack exports in UTF-16
delimiter = "\t"             # Tab-delimited
```

**Troubleshooting**: If import fails with encoding errors, verify the iTrack export format matches these settings.

#### Sprint Schedule Section
```toml
[sprint_schedule]
duration_days = 14           # 2-week sprints
start_weekday = 3            # Thursday (0=Monday)
end_weekday = 2              # Wednesday
cycle_name = "Thursday-to-Wednesday"
calendar_file = "sprint_calendar.csv"
auto_detect_sprint = true    # Auto-assign by TaskAssignedDt
```

#### Capacity Settings
```toml
[sprint_capacity]
max_hours = 52               # Max hours per person per sprint
warning_hours = 45           # Warning threshold
capacity_percentage = 65     # % of 80 hours available
```

#### TAT Thresholds
```toml
[tat_thresholds]
ir_days = 0.8                # IR escalates at 0.8 days
sr_days = 22                 # SR escalates at 22 days
warning_percent = 75         # At-risk warning at 75%
```

#### Column Mapping (iTrack → Internal)
```toml
[column_mapping]
"Ticket ID" = "Parent ID"
"Task ID" = "Task"
"Task_Status" = "Status"
"Task_Owner" = "Assignee"
"Ticket_Subject" = "Subject"
"Section" = "Team"
"Task_Assigned_DateTime" = "Task Assigned Date"
# ... more mappings
```

**How Column Mapping Works:**
1. iTrack exports have specific column names (left side)
2. These are mapped to internal names (right side)
3. Internal names are then mapped to sprint schema names

#### Sprint Schema Mapping (Internal → Sprint)
```toml
[sprint_schema_mapping]
"Task" = "TaskNum"
"Parent ID" = "TicketNum"
"Status" = "Status"
"Assignee" = "AssignedTo"
"Team" = "Section"
"Task Assigned Date" = "TaskAssignedDt"
# ... more mappings
```

#### Name Mapping (Account → Display)
```toml
[name_mapping]
hhakimjavadi = "Hesam Hakimjavadi"
mjimeno = "Jimeno Marilou"
# Add team members here
```

**To Add a New Team Member:**
1. Find their iTrack account name (username)
2. Add line: `accountname = "Display Name"`
3. Restart the app (no code changes needed)

### 4.2 `.streamlit/secrets.toml`

Authentication credentials (DO NOT COMMIT):

```toml
[credentials]
admin = "admin123"
testuser = "test123"
# Add users: username = "password"

[user_roles]
admin = "Admin"
testuser = "Section User"
# Options: "Admin" or "Section User"

[user_sections]
testuser = "CoreLab"
# Only needed for Section Users
```

### 4.3 `.streamlit/sections.toml`

Valid lab sections:

```toml
[sections]
valid_sections = [
    "LSC - Laboratory Service Center",
    "Micro - Microbiology",
    "CoreLab - Chemistry",
    "PIBIDS",
    # ... more sections
]

default_section = "PIBIDS"
```

### 4.4 Team Members Configuration

In `.streamlit/itrack_mapping.toml`, configure valid team members:

```toml
[team_members]
# List of valid team member usernames (from iTrack AssignedTo field)
# Tasks assigned to users NOT in this list will be filtered out
valid_members = [
    "Skinta, John",
    "Jimeno, Marilou",
    "Kusumo, Marietta",
    # ... more team members
]
```

This filters out tasks assigned to non-team members from all dashboards and metrics.

### 4.4 `data/sprint_calendar.csv`

Sprint definitions:

```csv
SprintNumber,SprintName,SprintStartDt,SprintEndDt
1,Sprint 1,2024-11-07,2024-11-20
2,Sprint 2,2024-11-21,2024-12-04
3,Sprint 3,2024-12-05,2024-12-18
```

**To Add a New Sprint:**
1. Add row to `sprint_calendar.csv`
2. Ensure dates don't overlap with existing sprints
3. Dates must be in `YYYY-MM-DD` format

---

## 5. Core Modules

### 5.1 `modules/task_store.py` — **CRITICAL**

The central task management system. All tasks are stored in a single CSV file.

#### Key Concepts

**UniqueTaskId**: Each task gets a unique ID: `{TaskNum}_S{OriginalSprintNumber}`
- Example: `TSK-1234_S3` = Task TSK-1234, originally assigned to Sprint 3

**SprintsAssigned**: Comma-separated list of sprints task was assigned to
- Example: `"4, 5"` = Task assigned to Sprint 4, then Sprint 5
- Empty string = Unassigned (in Work Backlogs only)

**GoalType**: Capacity planning category
- `Mandatory` = Core work (60% of capacity)
- `Stretch` = Additional work (20% of capacity)

**OriginalSprintNumber**: The sprint the task was first assigned to (based on TaskAssignedDt)

**StatusUpdateDt**: Controls when a task "closes" for carryover purposes

#### Class: `TaskStore`

```python
class TaskStore:
    def __init__(self, store_path: str = None)
    
    def _load_store(self) -> pd.DataFrame
    def save(self) -> bool
    
    # Import & Retrieval
    def import_tasks(self, itrack_df, mapped_df) -> Dict
    def get_sprint_tasks(self, sprint_number: int) -> pd.DataFrame
    def get_current_sprint_tasks(self) -> pd.DataFrame
    def get_backlog_tasks(self) -> pd.DataFrame  # All open tasks
    def get_all_tasks(self) -> pd.DataFrame
    def get_task_history(self, task_num: str) -> pd.DataFrame
    
    # Assignment
    def assign_task_to_sprint(self, unique_task_id, sprint_number) -> Tuple[bool, str]
    def assign_tasks_to_sprint(self, unique_task_ids, sprint_number) -> Tuple[int, int, List[str]]
    
    # Status & Capacity
    def update_task_status(self, unique_task_id, new_status, status_update_dt) -> bool
    def get_capacity_summary(self, sprint_tasks) -> pd.DataFrame
    
    # Internal helpers
    def _sprint_in_list(self, sprints_assigned, sprint_number) -> bool
    def _add_sprint_to_list(self, current_sprints, sprint_number) -> str
    def _calculate_days_open(self, df) -> pd.DataFrame
```

#### Sprint Task Logic (`get_sprint_tasks`)

A task appears in Sprint N if:
- Sprint N is in the `SprintsAssigned` list

**No automatic carryover.** Admin must explicitly assign each task to each sprint.

```python
def get_sprint_tasks(self, sprint_number: int) -> pd.DataFrame:
    # Check if sprint_number is in SprintsAssigned list
    mask = self.tasks_df['SprintsAssigned'].apply(
        lambda x: self._sprint_in_list(x, sprint_number)
    )
    result = self.tasks_df[mask].copy()
    
    # Determine TaskOrigin
    result['TaskOrigin'] = result.apply(
        lambda row: 'New' if row['OriginalSprintNumber'] == sprint_number else 'Assigned',
        axis=1
    )
    return result
```

#### Backlog Logic (`get_backlog_tasks`)

All **open tasks** appear in Work Backlogs:
- Status NOT in `CLOSED_STATUSES`
- Regardless of `SprintsAssigned` value

```python
def get_backlog_tasks(self) -> pd.DataFrame:
    return self.tasks_df[~self.tasks_df['Status'].isin(CLOSED_STATUSES)].copy()
```

```python
CLOSED_STATUSES = [
    'Completed', 'Closed', 'Resolved', 'Done', 
    'Canceled', 'Excluded from Carryover'
]

# Valid statuses (iTrack workflow)
VALID_STATUSES = [
    'Logged',       # New task, not yet assigned
    'Assigned',     # Assigned to someone but not yet accepted
    'Accepted',     # Accepted by assignee, actively working
    'Waiting',      # On hold/waiting for external input
    'Completed',    # Work finished
    'Closed',       # Ticket closed
    'Resolved',     # Issue resolved
    'Done',         # Alternative completion status
    'Canceled',     # Task canceled
    'Excluded from Carryover'  # Manual exclusion
]
```

#### Forever Ticket Exclusion

"Forever tickets" are recurring tasks that should be excluded from metrics:
- Tasks with subject containing "Standing Meeting"
- Tasks with subject containing "Miscellaneous Meetings"

These are automatically filtered out by `exclude_forever_tickets()` in `section_filter.py`.

#### Team Member Filtering

Tasks are filtered to only show those assigned to configured team members.
See `filter_by_team_members()` in `section_filter.py`.

#### Singleton Access

```python
from modules.task_store import get_task_store

task_store = get_task_store()  # Returns singleton instance
```

### 5.2 `modules/sprint_calendar.py`

Manages sprint date windows defined in CSV.

#### Class: `SprintCalendar`

```python
class SprintCalendar:
    def get_all_sprints(self) -> pd.DataFrame
    def get_sprint_by_number(self, sprint_number: int) -> Optional[Dict]
    def get_sprint_for_date(self, date: datetime) -> Optional[Dict]
    def get_current_sprint(self) -> Optional[Dict]
    def get_next_sprint(self) -> Optional[Dict]
    def add_sprint(self, sprint_number, sprint_name, start_date, end_date) -> bool
    def assign_tasks_to_sprint(self, df, date_column) -> pd.DataFrame
```

#### Sprint Info Dict Structure

```python
{
    'SprintNumber': 3,
    'SprintName': 'Sprint 3',
    'SprintStartDt': datetime(2024, 12, 5),
    'SprintEndDt': datetime(2024, 12, 18)
}
```

### 5.3 `modules/data_loader.py`

Handles CSV import/export with column mapping.

#### Class: `DataLoader`

```python
class DataLoader:
    def __init__(self, data_dir, config_path)
    
    def load_itrack_extract(self, file_path=None, uploaded_file=None) 
        -> Tuple[pd.DataFrame, bool, list]
    
    def map_itrack_to_sprint(self, itrack_df) -> pd.DataFrame
    
    def load_current_sprint(self, include_completed=False) -> Optional[pd.DataFrame]
    def load_past_sprints(self) -> Optional[pd.DataFrame]
    def save_current_sprint(self, df) -> bool
    def save_past_sprints(self, df) -> bool
    def archive_current_sprint(self) -> bool
```

#### Column Mapping Flow

```
iTrack Export CSV
    │
    ▼ [column_mapping] from config
Internal Column Names
    │
    ▼ [sprint_schema_mapping] from config
Sprint Schema Names
    │
    ▼
Final DataFrame
```

### 5.4 `modules/section_filter.py`

Section-based filtering utilities.

```python
def filter_by_section(df, section) -> pd.DataFrame
def get_available_sections(df) -> List[str]
def get_section_summary(df, section) -> dict
def get_all_section_summaries(df) -> List[dict]
def apply_section_filters(df, sections, status, priority_range, assigned_to) -> pd.DataFrame
```

---

## 6. Pages (UI)

### 6.1 `app.py` — Home Page

- Entry point, displays login form
- Shows sprint overview after login
- Quick action links based on role

**Session State Variables:**
```python
st.session_state.authenticated  # bool
st.session_state.username       # str
st.session_state.user_role      # "Admin" or "Section User"
st.session_state.user_section   # str (for Section Users)
```

### 6.2 `pages/1_📊_Dashboard.py`

Admin dashboard with full visibility.

**Features:**
- Sprint metrics display
- Filterable task table (AgGrid)
- At-Risk and Capacity tabs
- Export functionality

**Access:** All authenticated users

### 6.3 `pages/2_📤_Upload_Tasks.py`

iTrack CSV import page.

**Workflow:**
1. Upload iTrack CSV file
2. Validate format and columns
3. Preview task distribution by sprint
4. Import to task store

**Access:** Admin only

### 6.4 `pages/3_📋_Sprint_View.py`

Detailed sprint view with task management.

**Tabs:**
- **All Tasks**: Full task list with filters
- **Update Status**: Change task status with effective date
- **Distribution**: Charts and breakdowns

**Access:** All authenticated users (edit requires Admin)

### 6.5 `pages/4_👥_Section_View.py`

Section-filtered read-only view.

**Features:**
- Auto-filters to user's section
- Read-only task display
- At-risk task highlighting
- Export for offline use

**Access:** All authenticated users

### 6.6 `pages/5_📈_Analytics.py`

Charts and visualizations.

**Charts:**
- Priority distribution
- Status breakdown
- Section workload
- Time-based trends

**Access:** All authenticated users

### 6.7 `pages/6_📚_Past_Sprints.py`

Historical sprint archive.

**Features:**
- Browse past sprints
- Compare sprint metrics
- Search across sprints
- Export historical data

**Access:** Admin only

---

## 7. Components

### 7.1 `components/auth.py`

Authentication system.

```python
def check_authentication() -> bool
def get_user_role() -> Optional[str]
def get_user_section() -> Optional[str]
def is_admin() -> bool
def login(username, password) -> Tuple[bool, str]
def logout()
def require_auth(page_name)      # Stops page if not authenticated
def require_admin(page_name)     # Stops page if not admin
def display_user_info()          # Sidebar user info widget
def display_login_form()         # Login form widget
```

### 7.2 `components/metrics_dashboard.py`

Metric display widgets.

```python
def display_metric_row(metrics: list)
def display_sprint_overview(sprint_df)
def display_priority_breakdown(sprint_df)
def display_type_breakdown(sprint_df)
def display_status_breakdown(sprint_df)
def display_section_breakdown(sprint_df)
```

### 7.3 `components/at_risk_widget.py`

At-risk task display.

```python
def display_at_risk_widget(sprint_df)
def get_at_risk_tasks(df) -> pd.DataFrame
```

### 7.4 `components/capacity_widget.py`

Capacity tracking display.

```python
def display_capacity_summary(sprint_df)
def get_capacity_by_person(df) -> pd.DataFrame
```

---

## 8. Utilities

### 8.1 `utils/constants.py`

Configuration constants loaded from TOML.

```python
# Sprint
SPRINT_DURATION_DAYS = 14
SPRINT_START_WEEKDAY = 3  # Thursday

# Capacity
MAX_CAPACITY_HOURS = 52
WARNING_CAPACITY_HOURS = 45

# TAT
TAT_IR_DAYS = 0.8
TAT_SR_DAYS = 22
TAT_WARNING_THRESHOLD = 0.75

# Statuses
STATUS_EXCLUDED = ['Completed', 'Canceled', 'Closed', ...]

# File Paths
CURRENT_SPRINT_FILE = "data/current_sprint.csv"
PAST_SPRINTS_FILE = "data/past_sprints.csv"
```

### 8.2 `utils/name_mapper.py`

Account name to display name mapping.

```python
@lru_cache(maxsize=1)
def load_name_mapping() -> Dict[str, str]

def get_display_name(account_name) -> str
def apply_name_mapping(df, column='AssignedTo') -> pd.DataFrame
def get_all_mapped_names() -> Dict[str, str]
def clear_name_cache()  # Call after config changes
```

**Usage:**
```python
from utils.name_mapper import apply_name_mapping

df = apply_name_mapping(df, 'AssignedTo')
# Creates 'AssignedTo_Display' column with mapped names
```

### 8.3 `utils/date_utils.py`

Date manipulation helpers.

```python
def parse_date_flexible(date_str) -> Optional[datetime]
def get_days_remaining_in_sprint(sprint_end) -> int
def calculate_days_open(assigned_date) -> float
def is_business_day(date) -> bool
```

### 8.4 `utils/exporters.py`

Export utilities.

```python
def export_to_csv(df, filename) -> bytes
def export_to_excel(df, filename) -> bytes
def create_download_button(df, filename, label)
```

### 8.5 `utils/grid_styles.py`

AgGrid styling.

```python
def apply_grid_styles()  # Call once per page
def get_custom_css() -> dict  # For AgGrid custom_css parameter
```

---

## 9. Models

### 9.1 `models/validation.py`

Data validation functions.

```python
def validate_itrack_csv(df) -> Tuple[bool, List[str]]
def validate_sprint_csv(df) -> Tuple[bool, List[str]]
def validate_task_data(task_dict) -> Tuple[bool, List[str]]
def get_data_quality_report(df) -> Dict
```

### 9.2 `models/task.py` and `models/sprint.py`

Pydantic data models for type validation.

---

## 10. Data Flow

### 10.1 Import Flow

```
iTrack Export (UTF-16, Tab)
    │
    ▼
DataLoader.load_itrack_extract()
    │ - Apply [column_mapping]
    │ - Validate required columns
    │ - Apply default values
    │ - Parse dates
    ▼
DataLoader.map_itrack_to_sprint()
    │ - Apply [sprint_schema_mapping]
    │ - Extract TicketType from Subject
    │ - Initialize planning columns
    ▼
TaskStore.import_tasks()
    │ - Assign OriginalSprintNumber by TaskAssignedDt
    │ - Create UniqueTaskId
    │ - Merge with existing tasks
    ▼
TaskStore.save()
    │
    ▼
data/all_tasks.csv
```

### 10.2 Sprint View Flow

```
User requests Sprint N
    │
    ▼
TaskStore.get_sprint_tasks(N)
    │
    ├─► Original Tasks: OriginalSprintNumber == N
    │
    ├─► Carryover Tasks: 
    │   OriginalSprintNumber < N
    │   AND (Status not closed OR StatusUpdateDt > SprintEndDt)
    │
    ▼
Combine + Mark IsCarryover
    │
    ▼
apply_name_mapping()
    │
    ▼
Calculate DaysOpen
    │
    ▼
Return DataFrame with sprint metadata
```

### 10.3 Status Update Flow

```
Admin selects task
    │
    ▼
Enter new status + StatusUpdateDt
    │
    ▼
TaskStore.update_task_status()
    │ - Validate StatusUpdateDt >= TaskAssignedDt
    │ - Update Status + StatusUpdateDt
    ▼
TaskStore.save()
    │
    ▼
Task now appears/disappears from sprints
based on StatusUpdateDt vs SprintEndDt
```

---

## 11. Authentication System

### Login Flow

```
User enters credentials
    │
    ▼
auth.login(username, password)
    │ - Read st.secrets['credentials']
    │ - Verify password
    │ - Get role from st.secrets['user_roles']
    │ - Get section from st.secrets['user_sections']
    ▼
Set session state:
    st.session_state.authenticated = True
    st.session_state.username = username
    st.session_state.user_role = role
    st.session_state.user_section = section
```

### Access Control

| Role | Dashboard | Upload | Sprint View | Section View | Analytics | Past Sprints |
|------|-----------|--------|-------------|--------------|-----------|--------------|
| Admin | ✅ Full | ✅ | ✅ Edit | ✅ All | ✅ | ✅ |
| Section User | ✅ Read | ❌ | ✅ Read | ✅ Own Section | ✅ | ❌ |

---

## 12. Business Logic

### 12.1 TAT Escalation

| Ticket Type | Escalation Threshold | At-Risk Warning (75%) |
|-------------|---------------------|----------------------|
| IR (Incident) | 0.8 days | 0.6 days |
| SR (Service Request) | 22 days | 18 days |
| PR (Project) | No auto-escalation | N/A |

When `DaysOpen >= threshold`, task should be escalated to Priority 5.

### 12.2 Closed Statuses

Tasks with these statuses are considered closed:
```python
CLOSED_STATUSES = [
    'Completed', 'Closed', 'Resolved', 'Done', 
    'Canceled', 'Excluded from Carryover'
]
```

---

## 13. Sprint Assignment Logic

### 13.1 Overview

The system uses a **Work Backlogs** model instead of automatic carryover:

```
iTrack Import
    │
    ├── Completed Tasks → Auto-assign to OriginalSprintNumber
    │                     (SprintsAssigned = "N")
    │
    └── Open Tasks → Work Backlogs
                     (SprintsAssigned = "")
                           │
                           │ Admin assigns
                           ▼
                     Sprint View
                     (SprintsAssigned = "4" or "4, 5", etc.)
```

### 13.2 Import Logic

When importing tasks from iTrack:

```python
def import_tasks(self, itrack_df, mapped_df) -> Dict:
    for idx, row in mapped_df.iterrows():
        # Determine OriginalSprintNumber from TaskAssignedDt
        original_sprint = calendar.get_sprint_for_date(row['TaskAssignedDt'])
        mapped_df.at[idx, 'OriginalSprintNumber'] = original_sprint['SprintNumber']
        
        # Apply assignment rules
        if row['Status'] in CLOSED_STATUSES:
            # Completed: auto-assign to original sprint
            mapped_df.at[idx, 'SprintsAssigned'] = str(original_sprint['SprintNumber'])
        else:
            # Open: go to backlog (no sprints assigned)
            mapped_df.at[idx, 'SprintsAssigned'] = ''
        
        # Set default GoalType
        mapped_df.at[idx, 'GoalType'] = 'Mandatory'
```

### 13.3 Assignment Logic

When admin assigns task to sprint:

```python
def assign_task_to_sprint(self, unique_task_id: str, sprint_number: int) -> Tuple[bool, str]:
    # Validation: Cannot assign to sprint older than creation
    if sprint_number < original_sprint_number:
        return False, "Cannot assign to sprint older than creation sprint"
    
    # Check if already assigned
    if self._sprint_in_list(current_sprints, sprint_number):
        return False, "Task already assigned to this sprint"
    
    # Add sprint to list (append, don't replace)
    new_sprints = self._add_sprint_to_list(current_sprints, sprint_number)
    # "4" → "4, 5" (if adding sprint 5)
    
    self.tasks_df.loc[mask, 'SprintsAssigned'] = new_sprints
```

### 13.4 Task Origin

When viewing a sprint, each task has a `TaskOrigin`:

| TaskOrigin | Condition | Color |
|------------|-----------|-------|
| **New** | `OriginalSprintNumber == SprintNumber` | 🟢 Green |
| **Assigned** | `OriginalSprintNumber != SprintNumber` | 🔵 Blue |

### 13.5 Example Workflow

1. **Sprint 4**: Task T1 created, open
   - `OriginalSprintNumber = 4`
   - `SprintsAssigned = ""` (in backlog)

2. **Admin assigns T1 to Sprint 4**
   - `SprintsAssigned = "4"`
   - T1 appears in Sprint 4 view with `TaskOrigin = "New"`

3. **Sprint 5**: T1 still open
   - T1 still in backlog (open tasks always appear)
   - `SprintsAssigned = "4"` (shows previous assignment)

4. **Admin assigns T1 to Sprint 5**
   - `SprintsAssigned = "4, 5"`
   - T1 appears in Sprint 4 (TaskOrigin="New") AND Sprint 5 (TaskOrigin="Assigned")

5. **T1 completed**
   - Removed from backlog (closed status)
   - Still visible in Sprint 4 and Sprint 5 for historical tracking

---

## 14. Capacity Planning

### 14.1 Goal Types

| Goal Type | Capacity Limit | % of 80 hrs | Description |
|-----------|----------------|-------------|-------------|
| **Mandatory** | 48 hours | 60% | Core work that must be completed |
| **Stretch** | 16 hours | 20% | Additional work if time permits |
| **Total** | 80 hours | 100% | Maximum available hours |

```python
GOAL_TYPES = ['Mandatory', 'Stretch']
DEFAULT_GOAL_TYPE = 'Mandatory'

CAPACITY_LIMITS = {
    'Mandatory': 48,  # 60% of 80 hours
    'Stretch': 16,    # 20% of 80 hours
    'Total': 80       # Total available hours
}
```

### 14.2 Capacity Summary

The `get_capacity_summary()` method returns per-person breakdown:

```python
def get_capacity_summary(self, sprint_tasks: pd.DataFrame) -> pd.DataFrame:
    summary_data = []
    for assignee in sprint_tasks['AssignedTo'].unique():
        assignee_tasks = sprint_tasks[sprint_tasks['AssignedTo'] == assignee]
        
        mandatory_hours = assignee_tasks[
            assignee_tasks['GoalType'] == 'Mandatory'
        ]['HoursEstimated'].sum()
        
        stretch_hours = assignee_tasks[
            assignee_tasks['GoalType'] == 'Stretch'
        ]['HoursEstimated'].sum()
        
        summary_data.append({
            'AssignedTo': assignee,
            'MandatoryHours': mandatory_hours,
            'StretchHours': stretch_hours,
            'TotalHours': mandatory_hours + stretch_hours,
            'MandatoryOver': mandatory_hours > 48,
            'StretchOver': stretch_hours > 16,
            'TotalOver': (mandatory_hours + stretch_hours) > 80
        })
    return pd.DataFrame(summary_data)
```

### 14.3 UI Display

In Plan Sprint page, capacity summary shows:
- 🟢 Within limit (green)
- 🔴 Over limit (red)

```
📊 Capacity Summary by Person
Limits: Mandatory ≤ 48 hrs (60%), Stretch ≤ 16 hrs (20%), Total = 80 hrs

John Smith
  🟢 Mandatory: 40.0 / 48 hrs
  🟢 Stretch: 8.0 / 16 hrs
  🟢 Total: 48.0 / 80 hrs

Jane Doe
  🔴 Mandatory: 52.0 / 48 hrs  ← Over limit!
  🟢 Stretch: 4.0 / 16 hrs
  🟢 Total: 56.0 / 80 hrs
```

---

## 15. Troubleshooting Guide

### Import Errors

**"Missing required columns"**
- Check iTrack export format matches `[file_format]` in config
- Verify column names match `[column_mapping]` keys

**"Encoding error"**
- iTrack exports use UTF-16 with tab delimiter
- Save as UTF-16 LE if re-exporting

**"Tasks not appearing in sprint"**
- Check `TaskAssignedDt` falls within sprint window in `sprint_calendar.csv`
- Verify sprint calendar has no gaps

### Authentication Issues

**"Invalid credentials"**
- Check `.streamlit/secrets.toml` exists
- Verify username/password match exactly (case-sensitive)

**"Missing secrets.toml"**
- Copy `secrets.toml.template` to `secrets.toml`
- Add your credentials

### Data Issues

**Tasks not carrying over**
- Check task status is not in `CLOSED_STATUSES`
- Verify `StatusUpdateDt` if set

**Wrong sprint assignment**
- Check `TaskAssignedDt` value
- Verify sprint windows in `sprint_calendar.csv`

### Performance Issues

**Slow loading**
- Clear `__pycache__` directories
- Reduce number of tasks loaded at once
- Use pagination in AgGrid

---

## 14. Upgrade Guide

### Adding New iTrack Columns

1. Add mapping to `[column_mapping]` in `itrack_mapping.toml`:
   ```toml
   "New iTrack Column" = "internal_name"
   ```

2. If needed in sprint schema, add to `[sprint_schema_mapping]`:
   ```toml
   "internal_name" = "SprintColumnName"
   ```

3. Add to `[sprint_columns].column_order` if it should appear in exports

### Adding New Users

1. Edit `.streamlit/secrets.toml`:
   ```toml
   [credentials]
   newuser = "password123"
   
   [user_roles]
   newuser = "Admin"  # or "Section User"
   
   [user_sections]
   newuser = "CoreLab"  # Only for Section Users
   ```

### Adding New Sprints

1. Edit `data/sprint_calendar.csv`:
   ```csv
   4,Sprint 4,2024-12-19,2025-01-01
   ```

2. Ensure no date overlap with existing sprints

### Adding New Team Members (Name Mapping)

1. Edit `[name_mapping]` in `itrack_mapping.toml`:
   ```toml
   newaccount = "New Person Name"
   ```

2. Restart application (or call `clear_name_cache()`)

### Modifying Closed Statuses

1. Edit `CLOSED_STATUSES` list in `modules/task_store.py`
2. Also update `STATUS_EXCLUDED` in `utils/constants.py`

### Changing TAT Thresholds

1. Edit `[tat_thresholds]` in `itrack_mapping.toml`:
   ```toml
   ir_days = 1.0   # New IR threshold
   sr_days = 20    # New SR threshold
   ```

---

## Appendix A: Complete Column Schema

| Column | Type | Description |
|--------|------|-------------|
| **Identity** | | |
| UniqueTaskId | str | `{TaskNum}_S{OriginalSprintNumber}` |
| TaskNum | str | Unique task ID from iTrack |
| TicketNum | str | Parent ticket number |
| **Sprint Assignment** | | |
| OriginalSprintNumber | int | Sprint when task was created (from TaskAssignedDt) |
| SprintsAssigned | str | Comma-separated list of assigned sprints (e.g., "4, 5") |
| TaskOrigin | str | "New" or "Assigned" (calculated dynamically) |
| **Task Info** | | |
| TicketType | str | IR/SR/PR/NC |
| Section | str | Lab section |
| Status | str | Task status (Logged/Assigned/Accepted/Waiting/Completed/etc.) |
| AssignedTo | str | Account name |
| AssignedTo_Display | str | Display name (added dynamically) |
| CustomerName | str | Customer requesting |
| Subject | str | Task description |
| **Dates** | | |
| TaskAssignedDt | datetime | Task assignment date |
| TaskCreatedDt | datetime | Task creation date |
| TaskResolvedDt | datetime | Task resolution date |
| TicketCreatedDt | datetime | Ticket creation date |
| TicketResolvedDt | datetime | Ticket resolution date |
| StatusUpdateDt | datetime | When status was changed |
| **Metrics** | | |
| CustomerPriority | int | Priority 0-5 |
| FinalPriority | int | Admin-set priority override |
| DaysOpen | float | Days since assigned (calculated) |
| **Planning** | | |
| GoalType | str | "Mandatory" or "Stretch" |
| HoursEstimated | float | Planned hours |
| DependencyOn | str | Task dependencies |
| DependenciesLead | str | Lead for dependencies |
| DependencySecured | str | Yes/No/Partial |
| Comments | str | Admin notes |

---

## Appendix B: Key File Locations

| File | Purpose |
|------|---------|
| `data/all_tasks.csv` | Central task store |
| `data/sprint_calendar.csv` | Sprint definitions |
| `.streamlit/itrack_mapping.toml` | Column mapping & config |
| `.streamlit/secrets.toml` | Authentication |
| `.streamlit/sections.toml` | Valid sections |

---

*End of Technical Documentation*
