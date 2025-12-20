# PBIDS Sprint Dashboard - Feature Guide

## Overview

The PBIDS Sprint Dashboard is a web-based application for managing sprint workflows, task assignments, and team capacity planning. It provides a centralized platform where administrators can import tasks from iTrack, assign them to sprints, and track progress, while team members can view their assignments and update task priorities.

---

## User Roles

### Administrator
- Upload and import tasks from iTrack
- Assign tasks to sprints
- Plan sprint capacity
- View all sections and team members
- Access all dashboard features

### User (Team Member)
- View tasks assigned to their section
- Update task priorities (CustomerPriority, FinalPriority)
- Add comments to tasks
- View sprint progress and analytics

---

## Task Lifecycle

### 1. Task Import
Tasks are imported from iTrack extract files (CSV format). When imported:
- Each task receives a unique identifier based on its Task Number and the sprint it was created in
- Tasks are automatically assigned an **Original Sprint Number** based on when the task was assigned (TaskAssignedDt)
- **Open tasks** go to the Work Backlogs (no sprint assignment)
- **Completed/Closed tasks** are auto-assigned to their original sprint

### 2. Work Backlogs
All open tasks appear in the Work Backlogs regardless of sprint assignment. This serves as a central pool where administrators can:
- View all pending work
- Filter by days open, ticket age, section, status, and assignee
- Select tasks for sprint assignment

### 3. Sprint Assignment
Administrators assign tasks from the Work Backlogs to specific sprints. A task can be assigned to **multiple sprints** (e.g., if work spans across sprints). The assignment is tracked as a comma-separated list of sprint numbers.

### 4. Sprint Planning
Once tasks are assigned to a sprint, the Sprint Planning page allows:
- Setting estimated hours for each task
- Assigning Goal Type (Mandatory or Stretch)
- Adding comments
- Monitoring capacity utilization per team member

### 5. Task Completion
When tasks are completed in iTrack and re-imported:
- Status updates automatically
- Completed tasks remain in their assigned sprints for historical tracking

---

## Dashboard Pages

### 1. 📊 Dashboard (Home)
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

---

### 2. 📤 Upload Tasks
**Admin only.** Used to import tasks from iTrack.

**Process:**
1. Upload an iTrack extract CSV file
2. System maps iTrack columns to dashboard schema
3. Preview imported data before confirming
4. Tasks are added to the system with proper sprint assignments

**Import behavior:**
- New tasks are added to the Work Backlogs
- Existing tasks are updated (Status, AssignedTo, Subject)
- Dashboard-only fields (CustomerPriority, FinalPriority, Comments) are preserved

---

### 3. 📋 Sprint View
View tasks assigned to a specific sprint.

**Features:**
- Select any sprint from dropdown
- View all tasks in that sprint with key details
- Filter by Section, Status, Ticket Type
- Color-coded status and priority indicators
- Days Open tracking with visual alerts for aging tasks

**Displayed columns:**
- Task #, Ticket #, Type, Section
- Status, Assignee, Subject
- Hours Estimated, Days Open

---

### 4. 👥 Section View
View and manage tasks by section (team).

**Features:**
- Filter by Section to see team workload
- Filter by Status, Priority range, Assignee
- **Editable fields** (for open tasks only):
  - CustomerPriority
  - Comments
- At-risk task highlighting
- Priority and status breakdown charts

**Priority Scale:**
- 5 = 🔴 Critical
- 4 = 🟠 High
- 3 = 🟡 Medium
- 2 = 🟢 Low
- 1 = ⚪ Minimal
- 0/None = ⚫ Not set

---

### 5. 📈 Analytics
Visual analytics and charts for sprint performance.

**Includes:**
- Task distribution by status
- Priority breakdown
- Section workload comparison
- Completion trends
- Ticket type distribution (IR, SR, PR)

---

### 6. 📚 Past Sprints
Historical view of completed sprints.

**Features:**
- Select any past sprint to review
- View completion metrics
- Search across all past sprints for specific tasks
- Export sprint data

---

### 7. ✏️ Sprint Planning
**Admin only.** The primary workspace for planning sprint capacity.

**Features:**

**Task Table (Editable):**
- View all tasks assigned to current/selected sprint
- Edit directly in the table:
  - **HoursEstimated**: Set effort estimate (hours)
  - **GoalType**: Mandatory or Stretch
  - **Comments**: Multi-line text editor (popup)
  - **CustomerPriority**: Set priority (0-5)
  - **FinalPriority**: Set final priority after review
- Changes auto-save when edited

**Capacity Planning:**
- **Mandatory capacity**: 48 hours per person per sprint
- **Stretch capacity**: 16 hours per person per sprint
- Real-time capacity utilization display per team member
- Warning indicators when capacity is exceeded

**Goal Types:**
- **Mandatory**: Core sprint commitment (counts toward 48hr limit)
- **Stretch**: Additional work if capacity allows (counts toward 16hr limit)

**Column Visibility:**
- Toggle which columns to display
- Customize view for planning workflow

---

### 8. 📋 Work Backlogs
Central pool of all open tasks awaiting sprint assignment.

**Features:**

**Filters:**
- **Section**: Filter by team
- **Status**: Filter by task status
- **Assignee**: Filter by team member
- **DaysOpen (Task) More Than**: Show tasks open longer than X days
- **Days Created (Ticket) More Than**: Show tickets created more than X days ago

**Column Visibility:**
- Customize which columns to display
- Toggle date columns, days counters, etc.

**Sprint Assignment:**
- Select tasks using checkboxes
- Choose target sprint from dropdown
- Click "Assign to Sprint" button
- Tasks remain in backlogs (visible) but now have sprint assignment

**Displayed Information:**
- Task #, Ticket #, Type, Section
- Status, Assignee, Customer Name
- Subject, Days Open, Days Created
- Created dates (Task and Ticket)

---

## Key Concepts

### Sprint Calendar
Sprints are defined in a calendar configuration with:
- Sprint Number
- Sprint Name
- Start Date
- End Date

Tasks are assigned to sprints based on these date ranges.

### Task Types
- **IR (Incident Request)**: Urgent issues requiring immediate attention
- **SR (Service Request)**: Standard service requests
- **PR (Problem Request)**: Problem tickets

### Task Status
- **Open**: Not started
- **In Progress**: Work ongoing
- **Completed**: Work finished
- **Canceled**: Task canceled
- **Closed**: Task closed

### Forever Tickets
Certain recurring tasks (identified by subject keywords like "Forever Ticket") are handled specially:
- Excluded from TAT (Turn Around Time) calculations
- Not flagged as at-risk regardless of age

### At-Risk Tasks
Tasks are flagged as at-risk based on:
- **IR tasks**: At risk if open > 60% of TAT threshold
- **SR tasks**: At risk if open > 18 days

### Dashboard-Only Fields
These fields are NOT imported from iTrack but managed within the dashboard:
- **CustomerPriority**: Priority set by user/admin (0-5 scale)
- **FinalPriority**: Final agreed priority after review
- **Comments**: Notes and comments added by team
- **HoursEstimated**: Effort estimate for capacity planning
- **GoalType**: Mandatory or Stretch classification
- **SprintsAssigned**: Which sprints the task is assigned to

---

## Workflows

### Workflow 1: Weekly Task Import (Admin)
1. Export tasks from iTrack as CSV
2. Go to **Upload Tasks** page
3. Upload the CSV file
4. Review the mapping and preview
5. Confirm import
6. New tasks appear in Work Backlogs

### Workflow 2: Sprint Planning (Admin)
1. Go to **Work Backlogs**
2. Filter to find relevant tasks
3. Select tasks for the upcoming sprint
4. Assign to sprint using the dropdown and button
5. Go to **Sprint Planning**
6. Set HoursEstimated for each task
7. Set GoalType (Mandatory/Stretch)
8. Monitor capacity utilization
9. Adjust assignments if over capacity

### Workflow 3: Priority Update (User/Admin)
1. Go to **Section View**
2. Filter to your section
3. Click on CustomerPriority cell for any open task
4. Select new priority from dropdown
5. Changes save automatically

### Workflow 4: Adding Comments
1. Go to **Sprint Planning** or **Section View**
2. Click on Comments cell
3. Multi-line editor popup appears
4. Enter comments
5. Click away to save

### Workflow 5: Reviewing Sprint Progress
1. Go to **Dashboard** for overview
2. Go to **Sprint View** for detailed task list
3. Go to **Analytics** for charts and trends
4. Go to **Section View** for team-specific breakdown

### Workflow 6: Historical Review
1. Go to **Past Sprints**
2. Select completed sprint from dropdown
3. View metrics and task details
4. Use search to find specific tasks across sprints

---

## Data Persistence

- All task data is stored locally in CSV format
- Changes made in the dashboard are saved immediately
- Task assignments, priorities, comments persist across sessions
- Importing new data updates existing tasks without losing dashboard-only fields

---

## Access Control

- **Admin users**: Full access to all features including upload, assignment, and planning
- **Regular users**: Can view dashboards, update priorities and comments on their section's tasks
- Authentication is managed through Streamlit's built-in authentication

---

## Tips for Effective Use

1. **Import regularly**: Keep task data fresh by importing from iTrack weekly
2. **Plan capacity carefully**: Use the 48hr Mandatory / 16hr Stretch limits as guides
3. **Set priorities early**: CustomerPriority helps with sprint planning decisions
4. **Use comments**: Document blockers, dependencies, or special notes
5. **Monitor at-risk tasks**: Address aging tasks before they escalate
6. **Review past sprints**: Learn from completion rates and adjust future planning

---

## Summary

The PBIDS Sprint Dashboard provides a complete workflow for:
- ✅ Importing tasks from iTrack
- ✅ Managing work backlogs
- ✅ Assigning tasks to sprints
- ✅ Planning sprint capacity
- ✅ Tracking priorities and progress
- ✅ Analyzing team performance
- ✅ Reviewing historical data

All in a single, easy-to-use web interface accessible by both administrators and team members.
