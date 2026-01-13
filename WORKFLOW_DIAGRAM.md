# Sprint Dashboard Workflow Diagram

## Complete System Workflow

```mermaid
flowchart TB
    Start([Start Sprint Cycle]) --> ExportiTrack[Export Data from iTrack]
    
    ExportiTrack --> iTrackFile[(iTrack Extract CSV<br/>UTF-16 Tab-delimited)]
    
    iTrackFile --> Upload[Upload to<br/>New Sprint Page]
    
    Upload --> Validate{Validate<br/>CSV Format?}
    
    Validate -->|Invalid| Error1[Show Error Message]
    Error1 --> Upload
    
    Validate -->|Valid| Preview[Preview iTrack Data<br/>- Total tasks<br/>- Unique tickets<br/>- Assignees<br/>- Teams]
    
    Preview --> Configure[Configure New Sprint<br/>- Sprint number<br/>- Start date Thu<br/>- Duration 14 days]
    
    Configure --> Generate[Click Generate Sprint]
    
    Generate --> CheckCurrent{Current Sprint<br/>Exists?}
    
    CheckCurrent -->|Yes| Archive[Archive Current Sprint<br/>to Past Sprints<br/>ALL tasks included]
    CheckCurrent -->|No| AnalyzeCarryover
    
    Archive --> LoadPrevious[Load Previous Sprint<br/>with ALL tasks]
    
    LoadPrevious --> AnalyzeCarryover[Analyze Tasks]
    
    AnalyzeCarryover --> FilterCompleted{Task Status?}
    
    FilterCompleted -->|Completed/Closed| PastOnly[Add to Past Sprints Only<br/>Not carried over]
    FilterCompleted -->|In Progress/New| Carryover[Identify as Carryover<br/>Update from fresh iTrack]
    
    PastOnly --> PastSprintsDB
    
    Carryover --> UpdateCarryover[Update Carryover Tasks:<br/>- Fresh status<br/>- Fresh priority<br/>- Fresh assignee<br/>- Clear effort estimate]
    
    UpdateCarryover --> NewTasks[Identify New Tasks<br/>Created after previous<br/>sprint end date]
    
    NewTasks --> Escalate[Apply TAT Escalation<br/>- IR: 0.8 days → Priority 5<br/>- SR: 22 days → Priority 5]
    
    Escalate --> Combine[Combine Tasks:<br/>Carryover + New]
    
    Combine --> CreateSprint[Create New Current Sprint<br/>- Sprint metadata<br/>- Task list<br/>- Default priority 3]
    
    CreateSprint --> CurrentSprintDB[(Current Sprint CSV<br/>Active tasks only)]
    
    CurrentSprintDB --> PlanningPhase[Planning Phase<br/>Admin Reviews Sprint]
    
    PlanningPhase --> ViewDashboard{Which View?}
    
    ViewDashboard -->|Dashboard| ShowDashboard[📊 Dashboard<br/>Show ACTIVE tasks only<br/>- Stats<br/>- Charts<br/>- By team]
    
    ViewDashboard -->|Plan Sprint| ShowPlan[✏️ Plan Sprint<br/>Show ACTIVE tasks only<br/>Edit in grid:<br/>- Effort estimate<br/>- Dependencies<br/>- Comments]
    
    ViewDashboard -->|Section View| ShowSection[👥 Section View<br/>Show ACTIVE tasks only<br/>Filtered by team<br/>Read-only for users]
    
    ShowDashboard --> UpdateTasks
    ShowPlan --> UpdateTasks[Admin Updates Tasks<br/>Save changes]
    ShowSection --> WorkContinues
    
    UpdateTasks --> CurrentSprintDB
    
    UpdateTasks --> WorkContinues{Sprint<br/>Complete?}
    
    WorkContinues -->|No| ViewDashboard
    WorkContinues -->|Yes - 14 days| EndSprint[End of Sprint]
    
    EndSprint --> ReviewComplete[Admin Reviews:<br/>Mark tasks as completed<br/>in iTrack]
    
    ReviewComplete --> NextCycle[Ready for Next Sprint]
    
    NextCycle --> ExportiTrack
    
    CurrentSprintDB -.->|Archive at<br/>end of sprint| PastSprintsDB[(Past Sprints Archive<br/>ALL tasks<br/>Complete history)]
    
    PastSprintsDB --> Analytics[📈 Analytics<br/>Historical data<br/>All sprints]
    
    style iTrackFile fill:#e1f5ff
    style CurrentSprintDB fill:#fff4e1
    style PastSprintsDB fill:#f0f0f0
    style Archive fill:#ffe1e1
    style Carryover fill:#e1ffe1
    style PastOnly fill:#f0f0f0
    style ShowDashboard fill:#e1f5ff
    style ShowPlan fill:#ffe1f5
    style ShowSection fill:#f5e1ff
```

## Key Concepts

### 📥 Data Sources

1. **iTrack Extract (Input)**
   - Fresh export from iTrack system
   - UTF-16 tab-delimited format
   - Contains all active tickets/tasks
   - Updated status, priority, assignees

2. **Current Sprint (Working File)**
   - Only ONE active sprint at a time
   - **Filtered view:** Shows ACTIVE tasks only (no completed)
   - **Actual file:** Contains all tasks
   - Used for planning and daily work
   - Updated by admins with estimates/dependencies

3. **Past Sprints (Archive)**
   - Historical record of ALL sprints
   - Contains EVERY task (completed + incomplete)
   - Includes all annotations (effort, dependencies, comments)
   - Used for analytics and reporting

### 🔄 Sprint Generation Logic

```mermaid
flowchart LR
    A[Previous Sprint<br/>20 tasks] --> B{Analyze Status}
    B -->|12 Completed| C[Past Sprints Archive]
    B -->|8 In Progress| D[Carry Over to New Sprint]
    E[iTrack Extract<br/>New tasks] -->|15 new tasks| F[Add to New Sprint]
    D --> G[New Sprint<br/>23 tasks total]
    F --> G
    
    style C fill:#f0f0f0
    style G fill:#e1ffe1
```

**Math:**
- Previous Sprint: 20 tasks (12 completed, 8 incomplete)
- Archive: +20 tasks (ALL preserved)
- New Sprint: 8 carryover + 15 new = 23 tasks

### 👁️ View Filtering

| View | Shows | Purpose |
|------|-------|---------|
| **Dashboard** | Active tasks only | Monitor progress |
| **Plan Sprint** | Active tasks only | Add estimates |
| **Section View** | Active tasks only | Team's work |
| **Analytics** | Active tasks | Current metrics |
| **Past Sprints** | ALL tasks | Historical analysis |

### ⏱️ TAT Escalation Rules

```mermaid
flowchart LR
    Task[Task Created] --> CheckType{Task Type}
    CheckType -->|IR| CheckIR{Days Open<br/>> 0.8?}
    CheckType -->|SR| CheckSR{Days Open<br/>> 22?}
    CheckType -->|PR/NC| NoPriority[Keep Priority<br/>as-is]
    
    CheckIR -->|Yes| Escalate1[Set Priority = 5<br/>URGENT]
    CheckIR -->|No| NoPriority
    
    CheckSR -->|Yes| Escalate1
    CheckSR -->|No| NoPriority
    
    style Escalate1 fill:#ffe1e1
```

**Ticket Type Labels:**
- **Incident Request (IR)** - Urgent issues
- **Service Request (SR)** - Standard requests
- **Project Request (PR)** - Project work
- **Not Classified (NC)** - Uncategorized

### 🚧 Forever Ticket Exclusion

The following tickets are automatically excluded from all metrics:
- Tasks with subject containing "Standing Meeting"
- Tasks with subject containing "Miscellaneous Meetings"

These are recurring tasks that would skew metrics if included.

### 👥 Team Member Filtering

Tasks are filtered to only show those assigned to configured team members.
Configure in `.streamlit/itrack_mapping.toml` under `[team_members]` section.

### 📊 Sprint Workflow Timeline

```mermaid
gantt
    title 14-Day Sprint Cycle
    dateFormat YYYY-MM-DD
    section Sprint N
    Archive Previous Sprint           :done, a1, 2025-12-05, 1d
    Generate New Sprint               :done, a2, 2025-12-05, 1d
    section Planning
    Admin Adds Estimates              :active, b1, 2025-12-05, 3d
    Team Reviews Tasks                :active, b2, 2025-12-06, 2d
    section Execution
    Development Work (14 days)        :c1, 2025-12-05, 14d
    Admin Updates Progress            :c2, 2025-12-08, 11d
    section Completion
    Mark Tasks Complete in iTrack     :d1, 2025-12-18, 1d
    Export for Next Sprint            :d2, 2025-12-19, 1d
    section Sprint N+1
    Start New Sprint                  :milestone, 2025-12-19, 0d
```

## User Roles & Actions

### 👨‍💼 Admin (Project Admin)
- ✅ Generate new sprints
- ✅ Upload iTrack extracts
- ✅ Add effort estimates
- ✅ Set dependencies
- ✅ Update priorities
- ✅ View all sections
- ✅ Archive sprints

### 👨‍🔬 Section User (Lab Team Member)
- ✅ View their section's tasks only
- ✅ See effort estimates
- ✅ Read-only access
- ❌ Cannot edit
- ❌ Cannot generate sprints

## Data Flow Summary

```
iTrack System
    ↓ [Export]
iTrack Extract CSV (UTF-16)
    ↓ [Upload]
Sprint Dashboard
    ↓ [Validate & Map Columns]
Normalized Data
    ↓ [Generate Sprint]
    ↓
    ├─→ Archive Old Sprint → Past Sprints (ALL tasks)
    ↓
    ├─→ Identify Carryover (Incomplete tasks)
    ├─→ Identify New Tasks (From iTrack)
    ├─→ Apply TAT Escalation
    ↓
Current Sprint (Active tasks view)
    ↓ [Planning]
Admin Adds Estimates/Dependencies
    ↓ [During Sprint]
Team Works on Tasks
    ↓ [End Sprint]
Tasks Completed in iTrack
    ↓ [Next Cycle]
Export Fresh iTrack Data
```

## Critical Rules

1. ✅ **Only ONE current sprint** at a time
2. ✅ **Current sprint shows ACTIVE tasks only** (completed filtered out)
3. ✅ **Archive includes ALL tasks** (completed + incomplete)
4. ✅ **Only incomplete tasks carry over** to next sprint
5. ✅ **TAT escalation** applied to overdue tasks
6. ✅ **Sprint duration is always 14 days** (Thu → Wed)
7. ✅ **Capacity limit is 52 hours** per team member per sprint
8. ✅ **Fresh iTrack data** used to update carryover tasks
9. ✅ **Forever tickets excluded** from all metrics (Standing/Miscellaneous Meetings)
10. ✅ **Team member filtering** - only configured members shown
11. ✅ **Field Ownership Model** - iTrack fields updated, dashboard fields preserved
12. ✅ **TaskNum as unique key** - used to match existing tasks during import
13. ✅ **SprintsAssigned tracks all sprints** - comma-separated list (v1.2)
14. ✅ **Sprint removal only affects current sprint** - other assignments preserved (v1.2)

## Status Workflow (iTrack)

```
Logged → Assigned → Accepted → Waiting → Completed/Closed
  🔵       🟡        🔵        🟠         🟢
```

| Status | Color | Meaning |
|--------|-------|--------|
| Logged | 🔵 Blue | New, unassigned |
| Assigned | 🟡 Yellow | Assigned, awaiting acceptance |
| Accepted | 🔵 Cyan | Actively working |
| Waiting | 🟠 Amber | On hold |
| Completed/Closed | 🟢 Green | Finished |
| Canceled | ⚪ Gray | Excluded |

## Field Ownership Model (v1.1)

Defines which system owns each field during imports:

```mermaid
flowchart LR
    subgraph iTrack["iTrack-Owned Fields"]
        A1[TaskNum]
        A2[Status]
        A3[TicketStatus]
        A4[AssignedTo]
        A5[Subject]
        A6[Dates]
    end
    
    subgraph Dashboard["Dashboard-Owned Fields"]
        B1[SprintsAssigned]
        B2[GoalType]
        B3[Priority]
        B4[Comments]
        B5[HoursEstimated]
    end
    
    Import[iTrack Import] -->|✅ Updates| iTrack
    Import -->|🚫 Preserves| Dashboard
    
    style iTrack fill:#e1f5ff
    style Dashboard fill:#fff4e1
```

| Ownership | Fields | Import Behavior |
|-----------|--------|----------------|
| **iTrack-owned** | TaskNum, TicketNum, Status, TicketStatus, AssignedTo, Subject, CustomerName, dates | Always updated |
| **Dashboard-owned** | SprintsAssigned, CustomerPriority, FinalPriority, GoalType, HoursEstimated, Comments | Never overwritten |
| **Computed** | OriginalSprintNumber, TicketType, DaysOpen | Calculated |

## Sprint Assignment & Removal (v1.2)

```mermaid
flowchart TB
    subgraph Assignment ["Assign to Sprint (Work Backlogs)"]
        A1[Select tasks with checkboxes] --> A2[Choose target sprint]
        A2 --> A3[Click Assign button]
        A3 --> A4[Sprint added to SprintsAssigned]
    end
    
    subgraph Removal ["Remove from Sprint (Sprint Planning)"]
        R1[View Sprint Planning for Sprint X] --> R2[Set SprintNumber to blank]
        R2 --> R3[Click Save Changes]
        R3 --> R4[Sprint X removed from SprintsAssigned]
    end
    
    subgraph Examples ["SprintsAssigned Examples"]
        E1["Task in '1' only"] -->|Remove from Sprint 1| E2["Becomes '' (backlog)"]
        E3["Task in '1, 2'"] -->|Remove from Sprint 1| E4["Becomes '2'"]
        E5["Task in '1, 2, 3'"] -->|Remove from Sprint 2| E6["Becomes '1, 3'"]
    end
    
    style Assignment fill:#e1ffe1
    style Removal fill:#ffe1e1
    style Examples fill:#f0f0f0
```

### Editable Fields by Page (v1.2)

| Page | Editable Fields | Save Method |
|------|-----------------|-------------|
| **Work Backlogs** | FinalPriority, GoalType, DependencyOn, DependenciesLead, DependencySecured, Comments | Save Changes button |
| **Section View** | CustomerPriority, DependencyOn, DependenciesLead, Comments | Save Changes button |
| **Sprint Planning** | All above + SprintNumber (blank=remove), HoursEstimated | Save Changes button |

---

**Version 1.2** — Updated January 13, 2026
