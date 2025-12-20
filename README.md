# PBIDS Sprint Dashboard

**Version 0.3.0** — Developed by the PIBIDS Team

A sprint management dashboard for workflow tracking. Imports task data from iTrack, manages sprint assignments through Work Backlogs, tracks capacity with Goal Type planning, and provides TAT-based priority monitoring.

## Features

- **Work Backlogs** — Central hub for all open tasks; admin assigns tasks to sprints
- **Sprint Assignment Tracking** — `SprintsAssigned` column tracks all sprint assignments per task
- **Goal Type Planning** — Mandatory (60% capacity) vs Stretch (20% capacity) goals
- **Capacity Management** — Per-person limits: 48 hrs Mandatory, 16 hrs Stretch, 80 hrs Total
- **TAT Monitoring** — IR escalation at 0.8 days, SR at 22 days, at-risk warnings at 75%
- **Role-Based Access** — Admin (full control) and Section User (read-only)
- **Forever Ticket Exclusion** — Automatically excludes Standing Meetings and Miscellaneous Meetings
- **Team Member Filtering** — Filter tasks to show only configured team members
- **Color-Coded Tables** — Visual indicators for Status, Priority, Days Open, and Task Origin
- **Standardized Ticket Types** — Incident Request (IR), Service Request (SR), Project Request (PR), Not Classified (NC)

## Quick Start

### Prerequisites

- Python 3.10+
- Mamba environment: `streamlit_dash`

### Installation

1. **Activate your Mamba environment:**
```bash
mamba activate streamlit_dash
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure authentication:**
```bash
# Copy the template
cp .streamlit/secrets.toml.template .streamlit/secrets.toml

# Edit .streamlit/secrets.toml with your credentials
```

4. **Run the application:**
```bash
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`

### Default Login Credentials

**Admin User:**
- Username: `admin`
- Password: `admin123`

**Test Section User:**
- Username: `testuser`
- Password: `test123`

⚠️ **Change these credentials in `.streamlit/secrets.toml` for production use!**

## Project Structure

```
sprint_dashboard/
├── app.py                      # Main application entry point
├── requirements.txt            # Python dependencies
├── .streamlit/
│   ├── config.toml            # Streamlit configuration
│   └── secrets.toml           # Authentication credentials
├── pages/                     # Streamlit pages
│   ├── 1_📊_Dashboard.py      # Admin master dashboard
│   ├── 2_➕_New_Sprint.py     # Sprint generation
│   ├── 3_✏️_Plan_Sprint.py    # Effort estimation & planning
│   ├── 4_👥_Section_View.py   # Lab section filtered view
│   └── 5_📈_Analytics.py      # Charts and insights
├── modules/                   # Core business logic
│   ├── data_loader.py         # CSV import/export
│   ├── sprint_generator.py    # Sprint creation logic
│   ├── tat_calculator.py      # TAT escalation
│   ├── capacity_validator.py  # Workload validation
│   └── section_filter.py      # Section filtering
├── models/                    # Data models
│   ├── task.py               # Task model with validation
│   ├── sprint.py             # Sprint model
│   └── validation.py         # Data validation
├── utils/                     # Utility functions
│   ├── constants.py          # Configuration constants
│   ├── date_utils.py         # Date manipulation
│   ├── formatters.py         # Display formatting
│   └── exporters.py          # Export utilities
├── components/                # Reusable UI components
│   ├── auth.py               # Authentication
│   ├── metrics_dashboard.py  # Metrics widgets
│   ├── capacity_widget.py    # Capacity display
│   └── at_risk_widget.py     # At-risk tasks widget
└── data/                      # Data directory
    ├── current_sprint.csv     # Active sprint
    ├── past_sprints.csv       # Sprint archive
    └── itrack_extract.csv     # Latest iTrack import
```

## Core Concepts

### Task Assignment Model

The system uses a **Work Backlogs** model for task assignment:

| Concept | Description |
|---------|-------------|
| **OriginalSprintNumber** | Sprint when task was created (based on `TaskAssignedDt`) |
| **SprintsAssigned** | Comma-separated list of sprints task was assigned to (e.g., "4, 5") |
| **GoalType** | Mandatory or Stretch - affects capacity calculations |

### Task Status Flow

```
Open Tasks                    Completed Tasks
    │                              │
    ▼                              ▼
Work Backlogs ──────────────► Removed from Backlog
    │                         (auto-assigned to original sprint)
    │ Admin assigns
    ▼
Sprint View (can be assigned to multiple sprints)
```

### No Automatic Carryover

**Important:** Tasks do NOT automatically carry over to the next sprint. The admin must explicitly assign each task to each sprint from the Work Backlogs.

---

## Workflow

### 1. Import Tasks from iTrack

1. **Export iTrack Data** — Download latest ticket data as CSV
2. **Go to Upload Tasks page** — Upload the CSV file
3. **Review Task Distribution** — Preview shows open vs completed tasks
4. **Click Import** — Tasks are processed:
   - ✅ **Completed tasks** → Auto-assigned to their original sprint
   - 📋 **Open tasks** → Go to Work Backlogs (SprintsAssigned = empty)

### 2. Assign Tasks from Work Backlogs

1. **Go to Work Backlogs page** (Admin only)
2. **View all open tasks** — Filter by Section, Status, AssignedTo, Assignment status
3. **Select tasks** using checkboxes
4. **Choose target sprint** from dropdown
5. **Click Assign** — Sprint number is added to `SprintsAssigned` column
6. **Repeat as needed** — Same task can be assigned to multiple sprints over time

**Example:**
- Task T1 created in Sprint 4, open
- Admin assigns to Sprint 4 → SprintsAssigned = "4"
- Sprint 5, T1 still open → Admin assigns to Sprint 5 → SprintsAssigned = "4, 5"
- T1 now appears in both Sprint 4 and Sprint 5 views

### 3. Sprint Planning

1. **Go to Plan Sprint page** (Admin only)
2. **Select sprint** from dropdown
3. **For each task, set:**
   - **GoalType**: Mandatory or Stretch
   - **HoursEstimated**: Expected effort
   - **FinalPriority**: Override customer priority if needed
   - **Dependencies**: DependencyOn, DependenciesLead, DependencySecured
   - **Comments**: Admin notes
4. **Monitor Capacity Summary** — Shows per-person breakdown:
   - 🟢 Mandatory: ≤ 48 hrs (60% of 80 hrs)
   - 🟢 Stretch: ≤ 16 hrs (20% of 80 hrs)
   - 🔴 Over limit warnings
5. **Save Changes**

### 4. Sprint Monitoring

1. **Dashboard** — View all tasks, metrics, at-risk tasks
2. **Sprint View** — Detailed view of specific sprint
3. **Section View** — Filtered view for section users
4. **Update Status** — Mark tasks as completed with effective date

### 5. Sprint Completion

When a task is completed:
1. Update status to "Completed" in iTrack
2. Re-import iTrack data
3. Completed task is removed from Work Backlogs
4. Task remains visible in assigned sprints for historical tracking

## Configuration

### Sprint Settings
Edit `utils/constants.py`:
```python
SPRINT_DURATION_DAYS = 14        # Sprint length
MAX_CAPACITY_HOURS = 52          # Hours per person
TAT_IR_DAYS = 0.8               # IR escalation threshold
TAT_SR_DAYS = 22                # SR escalation threshold
```

### User Management
Edit `.streamlit/secrets.toml`:
```toml
[credentials]
username = "password"

[user_roles]
username = "Admin"  # or "Section User"

[user_sections]
username = "Core Lab"  # Only for Section Users
```

## Data Schema

### iTrack Extract (Input)
Required columns:
- `Task`: Unique task ID
- `Parent ID`: Ticket number
- `Status`: Task status
- `Subject`: Description
- `Created On`: Creation date

Optional columns:
- `Priority`: Customer priority (0-5)
- `Team`: Lab section
- `Assignee`: Person assigned
- `Created Inc` / `Created SR`: Ticket dates
- `Customer Inc.` / `Customer SR`: Customer names

### Sprint CSV (Output)
Key columns:
- `SprintNumber`, `SprintName`, `SprintStartDt`, `SprintEndDt`
- `TaskNum`, `TicketNum`, `TicketType`, `Section`
- `Status`, `AssignedTo`, `CustomerName`, `Subject`
- `CustomerPriority`, `DaysOpen`
- `TicketCreatedDt`, `TaskCreatedDt`
- `HoursEstimated`
- `DependencyOn`, `DependenciesLead`, `DependencySecured`
- `Comments`

## Business Rules

### Sprint Assignment Rules

1. **Completed tasks** are auto-assigned to their `OriginalSprintNumber`
2. **Open tasks** go to Work Backlogs with `SprintsAssigned` = empty
3. Admin assigns tasks to sprints from backlog
4. **Validation**: Cannot assign task to sprint older than its `OriginalSprintNumber`
5. Tasks can be assigned to multiple sprints (tracked in `SprintsAssigned`)

### Task Origin

When viewing a sprint, each task has a `TaskOrigin`:

| TaskOrigin | Description | Color |
|------------|-------------|-------|
| **New** | Task created in this sprint (`OriginalSprintNumber` = current sprint) | 🟢 Green |
| **Assigned** | Task assigned from backlog (`OriginalSprintNumber` ≠ current sprint) | 🔵 Blue |

### Goal Type & Capacity

| Goal Type | Capacity Limit | % of 80 hrs |
|-----------|----------------|-------------|
| **Mandatory** | 48 hours | 60% |
| **Stretch** | 16 hours | 20% |
| **Total** | 80 hours | 100% |

Capacity Summary shows per-person breakdown with color indicators:
- 🟢 Within limit
- 🔴 Over limit

### TAT Escalation

| Ticket Type | Escalation Threshold | At-Risk Warning (75%) |
|-------------|---------------------|----------------------|
| IR (Incident) | 0.8 days | 0.6 days |
| SR (Service Request) | 22 days | 18 days |
| PR (Project) | Manual only | N/A |

### Closed Statuses

Tasks with these statuses are considered closed:
- Completed, Closed, Resolved, Done, Canceled, Excluded from Carryover

## Troubleshooting

### Application Won't Start
```bash
# Check Python version
python --version  # Should be 3.10+

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check for port conflicts
# Kill existing Streamlit processes
pkill -f streamlit
```

### Authentication Issues
```bash
# Verify secrets file exists
ls -la .streamlit/secrets.toml

# Check file format (must be valid TOML)
cat .streamlit/secrets.toml
```

### Data File Errors
- Ensure `data/` directory exists
- Check CSV file encoding (should be UTF-8)
- Verify column names match expected schema

### Import Errors
```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -name "*.pyc" -delete

# Reinstall specific package
pip install streamlit==1.29.0 --force-reinstall
```

## Development

### Running Tests
```bash
pytest tests/ -v
```

### Code Style
```bash
# Format code
black .

# Lint
flake8 .
```

## License

Internal use only — PBIDS Team

## Version

**v0.3.0** — December 19, 2024

### What's New in v0.3.0
- **Work Backlogs** — Replaced Pre-Sprint Queue; all open tasks appear here
- **SprintsAssigned Column** — Tracks all sprint assignments per task (comma-separated)
- **No Automatic Carryover** — Admin must explicitly assign tasks to each sprint
- **Goal Type** — Mandatory vs Stretch goals with capacity limits
- **Capacity Summary** — Per-person breakdown: Mandatory (48 hrs), Stretch (16 hrs), Total (80 hrs)
- **Assignment Validation** — Cannot assign task to sprint older than creation sprint

### Previous Versions

**v0.2.0** — December 15, 2024
- Forever ticket exclusion (Standing Meetings, Miscellaneous Meetings)
- Team member filtering via configuration
- Editable Status and Section in Plan Sprint page
- Color-coded Status, Priority, and Days Open columns
- Standardized ticket type labels (IR, SR, PR, NC)

**v0.1.0** — Initial release

---

Built with Streamlit
