# PBIDS Sprint Dashboard - System Requirements Document

**Version:** 1.0  
**Date:** January 5, 2026  
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
- **Carryover**: Open tasks that automatically move to the next sprint
- **TAT (Turn-Around Time)**: Target completion timeframes by ticket type

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

## 4. Page Specifications

### 4.1 Home Page (app.py)

**Page Title:** "Sprint Dashboard (Prototype)"  
**Page Icon:** 📊

#### 4.1.1 Unauthenticated View
- Welcome message with application title
- Login form with:
  - **Username** field
  - **Password** field
  - **"🔐 Login"** button
- Help section explaining the application

#### 4.1.2 Authenticated View (Sidebar)
- **User Information Display:**
  - "👤 Logged in as: {display_name}"
  - "🔑 Role: {role}"
  - "📁 Section: {section}" (if applicable)
  - **"🚪 Logout"** button

- **Current Sprint Information:**
  - Sprint number and name
  - Date range (MM/DD - MM/DD/YYYY format)
  - Status indicator (🟢 Active, 🟡 Upcoming, etc.)

#### 4.1.3 Main Content (When Authenticated)
- Sprint overview with metrics:
  - **Total Tasks** count
  - **By Status** breakdown (Completed, In Progress, Pending)
  - **By Priority** breakdown
- Recent tasks table (last 10 open tasks)
- Navigation links to main pages

---

### 4.2 Dashboard Page

**Page Title:** "Dashboard (Prototype)"  
**Page Icon:** 📊  
**Access:** Authenticated users

#### 4.2.1 Header Section
- Title: "📊 Dashboard"
- Caption: "_Prototype — PBIDS Team_"
- User info display

#### 4.2.2 Task Overview Metrics (6 columns)
Row 1 - Ticket counts:
- **Total Current Tickets** - unique ticket count
- **SR** - Service Request count (help: "SR (Service Request)")
- **PR** - Problem count (help: "PR (Problem)")
- **IR** - Incident Request count (help: "IR (Incident Request)")
- **NC** - Non-classified count (help: "NC (Non-classified IS Requests)")
- **AD** - Admin Request count (help: "AD (Admin Request)")

Row 2 - Task counts (same categories)

#### 4.2.3 Sidebar Filters
- **Section** - multiselect, default "All"
- **Status** - multiselect, default "All"
- **Priority** - multiselect, default "All"
- **Assignee** - multiselect, default "All"

#### 4.2.4 Tabs
**Tab 1: "All Tasks"**
- Data table with all current sprint tasks
- Columns displayed in order (see Section 5.1 for column definitions)
- Export buttons: "📥 Export CSV", "📥 Export Excel"

**Tab 2: "At Risk"**
- Tasks at risk of missing TAT thresholds:
  - IR tasks where DaysOpen ≥ 0.6 days
  - SR tasks where DaysOpen ≥ 18 days
- Warning message: "⚠️ {count} tasks are at risk of missing TAT"

**Tab 3: "Capacity"**
- Team capacity breakdown by person
- Capacity thresholds:
  - 🟢 OK: Under 45 hours
  - 🟡 Warning: 45-52 hours
  - 🔴 Overload: Over 52 hours

---

### 4.3 Upload Tasks Page

**Page Title:** "Upload Tasks"  
**Page Icon:** 📤  
**Access:** Admin only

#### 4.3.1 Header
- Title: "📤 Upload Tasks"
- Caption: "_PBIDS Team_"

#### 4.3.2 Workflow Instructions (Expander: "📋 How Task Assignment Works")
```
### Simplified Workflow

1. **Upload iTrack extract** with all tasks
2. **Tasks automatically appear** in Work Backlogs
3. **Assign tasks to sprints** from Work Backlogs page
4. **Plan and estimate** in Sprint Planning page
5. **Repeat each sprint** - upload new extract to update

### Task Assignment Logic

- **New Tasks**: When uploaded, new tasks appear in Work Backlogs with no sprint assignment
- **Existing Tasks**: Task data (status, assignee, etc.) is updated from the new extract
- **Sprint Assignment**: Admins manually assign tasks to sprints from Work Backlogs page
- **Carryover**: Open tasks automatically carry over to future sprints until closed

### How Tasks Become "Carryover"

1. Task is assigned to Sprint N
2. Sprint N ends with task still open
3. Task automatically appears in Sprint N+1, N+2, etc.
4. Task shows "TaskOrigin: Carryover" in future sprints
5. "SprintsAssigned" column tracks: "10, 11, 12" (all sprints)
```

#### 4.3.3 Upload Section: iTrack Task Export
- **File uploader**: CSV files only
- **Preview**: Shows first 5 rows of uploaded data
- **"📤 Import Tasks"** button (primary)
- Success message: "✅ Imported {count} tasks ({new} new, {updated} updated)"

#### 4.3.4 Upload Section: iTrack Worklog Export
- **File uploader**: CSV files only  
- **Preview**: Shows first 5 rows
- **"📤 Import Worklogs"** button
- Success message: "✅ Imported {count} worklog entries"

#### 4.3.5 Current Data Status
- Task store status (total tasks, sprints with tasks)
- Worklog status (total entries, date range)

---

### 4.4 Sprint View Page

**Page Title:** "Sprint View (Prototype)"  
**Page Icon:** 🧪  
**Access:** All authenticated users

#### 4.4.1 Header
- Title: "Sprint View"
- Caption: "_Prototype — PBIDS Team_"

#### 4.4.2 Sprint Selector
- Dropdown: "Select Sprint"
- Format: "Sprint {N}: {SprintName} (MM/DD - MM/DD) [{count} tasks]"
- Status indicator: "Current", "Past", or "Upcoming"

#### 4.4.3 Sprint Info Bar
- Format: "**{SprintName}** — {StartDate} to {EndDate}"

#### 4.4.4 Summary Metrics (5 columns)
- **Total Tasks** - all tasks in sprint
- **Carryover** - tasks from previous sprints (help: "Open tasks from previous sprints")
- **Original** - tasks originally assigned to this sprint (help: "Tasks assigned to this sprint")
- **Open** - tasks not in closed status
- **Closed** - tasks in closed status

#### 4.4.5 Tabs

**Tab 1: "All Tasks"**
- Full task table (read-only)
- All columns visible
- Export buttons: "📥 Export CSV", "📥 Export Excel"

**Tab 2: "Update Status"** (Admin only)
- Message for non-admins: "⚠️ Admin access required to update tasks"
- For admins:
  - Instructions:
    ```
    **Close tasks to prevent carryover:**
    1. Use filters to find tasks
    2. Select one or more tasks from the table (use checkbox)
    3. Choose the new status and **Status Update Date**
    4. Click Update to apply changes
    
    > 💡 **Note:** Status Update Date cannot be before Task Assigned Date.
    ```
  - Task selection table with checkboxes
  - **New Status** dropdown (closed statuses only: Completed, Closed, Resolved, Cancelled)
  - **Status Update Date** date picker
  - **Impact Preview** showing which sprint the task will close in
  - **"💾 Update {N} Task(s)"** button (primary)

**Tab 3: "Distribution"**
- Tasks by Original Sprint (table)
- Tasks by Status (table with Open/Closed indicator)
- Tasks by Assignee (table with Total, Open, Closed counts)

---

### 4.5 Section View Page

**Page Title:** "Section View (Prototype)"  
**Page Icon:** 🧪  
**Access:** All authenticated users

#### 4.5.1 Header
- Title: "Section View"
- Caption: "_Prototype — PBIDS Team_"

#### 4.5.2 Role-Based Section Display

**For Admin/PBIDS User:**
- Info message: "👑 **{Role} View{Read-only note}**: Select a section to view or see all sections"
- Section dropdown: "Select Section to View" with "All Sections" option

**For Section Manager/Section User:**
- If no section assigned: Error "⚠️ No section assigned to your account"
- If section assigned: Info "👁️ **{Role}**: Viewing tasks for **{section(s)}**"

#### 4.5.3 Summary Metrics
Same format as Dashboard (6 columns × 2 rows for tickets and tasks by type)

#### 4.5.4 Task Table
- Title: "### Tasks"
- Caption: "💡 You can edit **Priority** for open tasks. Double-click the Priority cell to change it."
- Column descriptions help expander: "❓ Column Descriptions"

**Editable columns (for Section Manager/User, marked with ✏️):**
- CustomerPriority (dropdown: NotAssigned, 0, 1, 2, 3, 4, 5)
- Dependency (dropdown: '', 'Yes', 'No')
- DependencyLead(s) (text editor popup)
- Comments (text editor popup)

**For PBIDS Users:** All columns read-only with message "🔒 **Read-only view** - PBIDS Users cannot edit task data."

#### 4.5.5 Save and Export
- **"💾 Save Changes"** button (for users who can edit)
- Caption: "Editable fields: CustomerPriority, Dependency, DependencyLead(s), Comments. Only open tasks can be edited."
- Export button: "📥 Export to Excel ({count} tasks)"

#### 4.5.6 Breakdowns
- **📊 Status Breakdown** - count and percentage by status
- **🎯 Priority Breakdown** - count and percentage with labels:
  - 🔴 Critical (5)
  - 🟠 High (4)
  - 🟡 Medium (3)
  - 🟢 Low (2)
  - ⚪ Minimal (1)
  - ⚫ None (0)

#### 4.5.7 At-Risk Tasks Section
- Displayed if at-risk tasks exist
- Title: "### At-Risk Tasks"
- Warning: "⚠️ {count} tasks are at risk of missing TAT"
- Table with: TaskNum, Subject, DaysOpen, TicketType, Status, AssignedTo

#### 4.5.8 Help Section (Expander: "About This View")
```
{Viewing message based on user role}

This is a read-only view. Use column filters in the table to narrow results. 
Export buttons available for offline analysis.

**Priority Levels:** P5 Critical (red) · P4 High (yellow) · P3 and below (default)

**At-Risk Thresholds:** IR ≥ 0.6 days · SR ≥ 18 days
```

---

### 4.6 Analytics Page

**Page Title:** "Analytics"  
**Page Icon:** 📈  
**Access:** All authenticated users (section-filtered for non-admins)

#### 4.6.1 Header
- Title: "📈 Sprint Analytics"
- Section filter message for non-admins: "👁️ Viewing analytics for: **{section}**"

#### 4.6.2 Tabs

**Tab 1: "📊 Overview"**
- Key metrics (5 columns):
  - Total Tasks
  - Completed (with completion rate delta)
  - In Progress
  - Pending
  - Avg Days Open
- Charts:
  - Priority Breakdown (pie chart)
  - Type Breakdown (pie chart)
  - Section Breakdown (admin only)
  - Task Distribution by Assignee (bar chart, top 10)
  - Average Days Open by Ticket Type (bar chart)

**Tab 2: "⏰ TAT Analysis"**
- TAT Compliance metrics (4 columns):
  - Overall At Risk
  - TAT Exceeded (with warning indicator)
  - IR Compliance (percentage)
  - SR Compliance (percentage)
- IR section: Total, At Risk, Exceeded TAT, Compliance
- SR section: Total, At Risk, Exceeded TAT, Compliance
- TAT thresholds: IR = 0.8 days, SR = 22 days
- Task Age Distribution histogram with TAT threshold lines

**Tab 3: "👥 Team Performance"**
- Admin only full view
- Non-admin message: "Full team analytics available for administrators only"
- Capacity metrics:
  - Team Size
  - Team Capacity (hours)
  - Allocated Hours
  - Utilization percentage
- Capacity status counts: OK, Warning, Overload
- Individual Performance table

**Tab 4: "📋 Summary Report"**
- Text area with generated summary report
- Download button: "📥 Download Report"
- Key Statistics table

---

### 4.7 Completed Tasks Page

**Page Title:** "Completed Tasks"  
**Page Icon:** ✅  
**Access:** Admin only

#### 4.7.1 Header
- Title: "✅ Completed Tasks"
- Caption: "_Historical view of all completed tasks — PBIDS Team_"

#### 4.7.2 Summary Metrics (4 columns)
- ✅ Completed Tasks
- 🎫 Unique Tickets
- 📊 Sections
- ⏱️ Total Hours

#### 4.7.3 Tabs

**Tab 1: "📋 All Completed Tasks"**
- Filters (4 columns): Section, Ticket Type, Assignee, Completed In Sprint
- Task table with CompletedInSprint column
- Multi-task ticket grouping with alternating row colors
- Export buttons: "📥 Export Excel", "📥 Export CSV"

**Tab 2: "📊 By Sprint"**
- Sprint selector dropdown
- Sprint details: name, date range
- Metrics: Completed, IR Tasks, SR Tasks, Total Hours, Sections
- Charts: Tasks by Section, Tasks by Assignee
- Task Details table

**Tab 3: "📈 Trends & Analytics"**
- Requires at least 2 sprints with data
- Completion Volume Trend (bar chart)
- Task Type Distribution (line chart: IR vs SR)
- Effort Trend (bar chart: hours per sprint)
- Average Resolution Time (line chart)
- Sprint Completion Summary table

**Tab 4: "🔍 Search Tasks"**
- Search text input
- Multi-select filters: Sprint, Section, Assignee, Ticket Type, Customer
- Results table with export options

#### 4.7.4 Footer
- Note: "💡 **Note:** This page shows all completed tasks for historical analysis. Sprint Planning is for current and future sprints only."

---

### 4.8 Sprint Planning Page

**Page Title:** "Sprint Planning"  
**Page Icon:** ✏️  
**Access:** Admin only

#### 4.8.1 Header
- Title: "✏️ Sprint Planning"
- Caption: "_PBIDS Team_"

#### 4.8.2 Instructions (Expander: "ℹ️ How to Use This Page")
```
### Planning Workflow

1. **Edit cells directly** in the table below (double-click to edit)
2. **All fields are editable by admin**
3. **Click "Save Changes"** button to persist your edits
4. **Monitor capacity** - warnings appear if anyone exceeds 52 hours

### Field Types
- **Dropdown fields:** SprintNumber, CustomerPriority (0-5), DependencySecured, Status, TicketType, Section
- **Numeric fields:** DaysOpen, HoursEstimated, HoursSpent
- **Free text fields:** All other fields

### Pre-populated Fields (from iTrack or calculated)
- **DaysOpen** - Days since ticket creation (calculated)
- **HoursSpent** - From iTrack worklog (TaskMinutesSpent / 60)
- **TicketType, Section, CustomerName, Status, AssignedTo, Subject** - From iTrack upload
- **TicketNum, TaskNum, TicketCreatedDt, TaskCreatedDt** - From iTrack upload

### Tips
- Changing SprintNumber moves the task to that sprint on save
- Use filters to focus on specific sections or assignees
- Capacity validation happens automatically
```

#### 4.8.3 Sprint Selector
- Only current and future sprints shown
- Format: "Sprint {N}: {SprintName} (MM/DD - MM/DD) [{count} tasks]"
- Task counts exclude completed tasks

#### 4.8.4 Sidebar Filters
- Section (multiselect)
- Assigned To (multiselect)
- Status (multiselect)
- Checkbox: "Show only tasks without estimates"

#### 4.8.5 Summary Metrics
Same format as Dashboard (tickets and tasks by type)

#### 4.8.6 Editable Task Table
Caption: "✏️ = Editable column (double-click to edit). Changes are saved when you click 'Save Changes' below."

**Editable columns (marked with ✏️):**
- SprintNumber (dropdown of all sprint numbers)
- CustomerPriority (dropdown: NotAssigned, 0-5)
- FinalPriority (dropdown: NotAssigned, 0-5)
- GoalType (dropdown: '', 'Mandatory', 'Stretch')
- Dependency (dropdown: '', 'Yes', 'No')
- DependencyLead(s) (text popup editor)
- DependencySecured (dropdown: '', 'Yes', 'Pending', 'No')
- Comments (text popup editor)
- HoursEstimated (numeric)

**Read-only columns:**
- SprintName, SprintStartDt, SprintEndDt
- TaskOrigin (New/Carryover with color coding)
- SprintsAssigned
- TicketNum, TaskCount, TicketType, Section, CustomerName, TaskNum
- Status, AssignedTo, Subject
- TicketCreatedDt, TaskCreatedDt
- DaysOpen, TaskHoursSpent, TicketHoursSpent

#### 4.8.7 Capacity Summary Section
- Title: "### 📊 Capacity Summary by Person"
- Caption: "**Limits:** Mandatory ≤ 48 hrs (60%), Stretch ≤ 16 hrs (20%), Total = 80 hrs"
- Per-person breakdown:
  - ⚪ None: hours
  - 🟢/🔴 Mandatory: hours / limit
  - 🟢/🔴 Stretch: hours / limit
  - 🟢/🔴 Total: hours / limit

#### 4.8.8 Save and Export
- **"💾 Save Changes"** button (primary)
- Caption: "Changes are only saved when you click 'Save Changes'"
- **"📥 Export"** button

#### 4.8.9 Capacity Breakdown
- Color-coded table:
  - OVERLOAD: red background (#ffe6e6)
  - WARNING: yellow background (#fff3cd)
  - OK: green background (#d4edda)

---

### 4.9 Work Backlogs & Sprint Assignment Page

**Page Title:** "Work Backlogs & Sprint Assignment"  
**Page Icon:** 📋  
**Access:** Admin only

#### 4.9.1 Header
- Title: "📋 Work Backlogs & Sprint Assignment"

#### 4.9.2 Instructions (Expander: "ℹ️ How to Use This Page")
```
All **open tasks** appear here. As admin, you can:
- **Click checkbox** to select tasks for sprint assignment
- Assign tasks to **current or future sprints**
- Tasks can be assigned to multiple sprints over time
- Track sprint assignment history in the **Sprints Assigned** column
- Completed tasks are automatically moved to the **Completed Tasks** page
```

#### 4.9.3 Summary Metrics
Same format as Dashboard (tickets and tasks by type)

#### 4.9.4 Sprint Assignment Section
- Title: "### 📤 Assign Tasks to Sprint"
- **Target Sprint** dropdown (current and future sprints only)
- Format: "Sprint {N}: MM/DD/YYYY - MM/DD/YYYY"

#### 4.9.5 Task Selection Table
- Checkbox column for selection (header checkbox for select all)
- First column: "Sprints Assigned" (tracks all sprint assignments)
- All task columns (read-only in this view)
- Multi-task ticket grouping with alternating row colors

#### 4.9.6 Export
- Button: "📥 Export to Excel ({count} tasks)"

#### 4.9.7 Assignment Action
- When no tasks selected: "👆 Select one or more tasks from the table above to assign to a sprint."
- When tasks selected:
  - Success message: "✅ **{N} task(s) selected**"
  - Expander: "📋 View Selected Tasks ({N})"
  - Button: "📤 Assign {N} Task(s) to Sprint {SprintNum}" (primary)
  - Success: "✅ Added Sprint {N} to {count} task(s)"

#### 4.9.8 Footer
- Tip: "💡 **Tip:** Open tasks stay in the backlog until completed. Assign them to sprints as needed - the Sprints Assigned column tracks all assignments."

---

### 4.10 Worklog Activity Page

**Page Title:** "Worklog Activity"  
**Page Icon:** 📊  
**Access:** Admin only

#### 4.10.1 Header
- Title: "📊 Worklog Activity Report"
- Caption: "_Team member activity tracking based on iTrack worklog data — PBIDS Team_"

#### 4.10.2 Summary Metrics (4 columns)
- 📝 Total Log Entries
- ⏱️ Total Hours Logged
- 👥 Team Members
- 🎯 Current Sprint

#### 4.10.3 Tabs

**Tab 1: "📅 Daily Activity"**
- Title: "Daily Activity by User"
- Caption: "Shows log frequency and minutes spent per user per day"

- **Date Range Mode:** Radio buttons "Sprint" or "Custom Range"
- **Filters (4 columns):**
  - Sprint selector (when Sprint mode)
  - Start/End date pickers (when Custom Range mode)
  - Ticket Type (multiselect, default "All")
  - Section (multiselect, default "All")

- **Color Legend:** "🟪 Weekend | 🟥 Off Day (configured in Admin Config)"

- **Three pivot tables:**
  1. Log Frequency by Date (count of log entries per user per day)
  2. Hours Logged by Date (hours per user per day)
  3. Unique Tasks by Date (distinct task count per user per day)

- **Off Day Highlighting:**
  - Weekends: light purple background (#f8f5fc)
  - Configured off days: light red background (#ffe6e6)

**Tab 2: "👤 By User"**
- User activity summary
- Total hours, entries, days active per user

**Tab 3: "📈 Sprint Summary"**
- Sprint-level worklog totals
- Hours by sprint comparison

**Tab 4: "📋 Raw Data"**
- Full worklog data table
- Export options

---

### 4.11 Admin Configuration Page

**Page Title:** "Admin Configuration"  
**Page Icon:** ⚙️  
**Access:** Admin only

#### 4.11.1 Header
- Title: "⚙️ Admin Configuration"
- Caption: "_Configure sprint calendar and user accounts — PBIDS Team_"

#### 4.11.2 Tabs

**Tab 1: "📅 Sprint Calendar"**

*Current Sprints Section:*
- Title: "### Current Sprints"
- Table columns: Sprint #, Sprint Name, Start Date, End Date

*Add New Sprint Section:*
- Title: "### ➕ Add New Sprint"
- Fields:
  - Sprint Number (auto-suggested as max + 1)
  - Sprint Name (default: "Sprint {N}")
  - Start Date (auto-suggested as day after last sprint)
  - End Date (auto-suggested as 14 days from start)
- Button: "➕ Add Sprint" (primary)

**Tab 2: "👥 User Management"**

*Current Users Section:*
- Title: "### Current Users"
- Table columns: Username, Display Name, Role, Section, Active
- "Active" shown as checkbox column

*Add/Edit User Section:*
- Title: "### ➕ Add New User" or "### ✏️ Edit User"
- User selector dropdown (for edit mode)
- Fields:
  - Username (disabled in edit mode)
  - Password
  - Display Name
  - Role (dropdown): Admin, PBIDS User, Section Manager, Section User
  - Sections (multiselect) - Required for Section Manager and Section User roles
  - Active (checkbox)
- Button: "➕ Add User" or "💾 Save Changes"
- Caption: "Users can be activated or deactivated but not deleted"

*Activate/Deactivate Section:*
- User selector
- Current status display
- Toggle button: "🟢 Activate User" or "🔴 Deactivate User"
- Validation: Cannot deactivate last active admin

**Tab 3: "🧑‍💼 Team Members"**

*Team Members Configuration Section:*
- Title: "### Team Members Configuration"
- Info: "Manage the list of valid team members for task assignment mapping."

*Current Team Members Table:*
- Columns: Email (from iTrack), Display Name, Active
- Active column shows ✅ or ❌

*Add New Team Member Section:*
- Title: "### ➕ Add New Team Member"
- Fields:
  - Email (iTrack identifier)
  - Display Name
- Button: "➕ Add Team Member"

*Activate/Deactivate Team Member Section:*
- Team member selector (shows all members)
- Current status display
- Toggle button: "🟢 Activate" or "🔴 Deactivate"
- Caption: "Team members can be activated or deactivated but not deleted"

**Tab 4: "🏖️ Off Days"**

*Off Days Configuration Section:*
- Title: "### 🏖️ Off Days Configuration"
- Caption: "Configure days when team members are unavailable during a sprint. This affects capacity calculations and is highlighted in Worklog Activity reports."

*Sprint Selector:*
- Dropdown to select sprint for configuration

*Checkbox Grid Table:*
- Rows: Active team members
- Columns: Sprint weekdays (excludes weekends)
- Checkboxes: ☑️ = working day, ☐ = off day
- Default: All weekdays checked (working)
- Changes auto-save when checkbox is toggled

*Off Days Summary Section:*
- Title: "### Off Days Summary"
- Shows list of configured off days for the selected sprint
- Format: "• {Team Member}: {Date}"

---

### 4.12 Sprint Feedback Page

**Page Title:** "Sprint Feedback (Prototype)"  
**Page Icon:** 💬  
**Access:** Section Managers and Admins only

#### 4.12.1 Header
- Title: "💬 Sprint Feedback"
- Caption: "_Prototype — PBIDS Team_"

#### 4.12.2 Access Control
- Non-Section Managers see: "⚠️ This page is only accessible to Section Managers"
- Info: "Section Managers can submit feedback for recently completed sprints."

#### 4.12.3 Tabs

**Tab 1: "📝 Submit Feedback"**
- Title: "Submit Feedback for Sprint {N}" (where N = current sprint - 1)
- Sprint info display: "**{SprintName}** ({StartDate} - {EndDate})"

*For each section the user manages:*
- Section header: "#### Feedback for Section: **{Section}**"

*If feedback already submitted:*
- Success: "✅ Feedback already submitted for {Section}"
- Expander to view submitted feedback

*If feedback not yet submitted - Form:*
```
**a. Overall satisfaction of this sprint?**
[Slider: 1-5, label "Rate from 1 (Very Unsatisfied) to 5 (Very Satisfied)"]

**b. What went well?**
[Text area, placeholder: "Share positive outcomes, achievements, and successes..."]

**c. What did not go well?**
[Text area, placeholder: "Share challenges, blockers, or areas that need improvement..."]

[📤 Submit Feedback] (primary button)
```

**Tab 2: "📋 View Previous Feedback"**
- Title: "📋 Your Previous Feedback"
- Grouped by sprint (most recent first)
- Each feedback shows: Section, Satisfaction score, submission date, comments

#### 4.12.4 Help Section (Expander: "ℹ️ About Sprint Feedback")
```
### How Sprint Feedback Works

- **Who can submit:** Section Managers only
- **When to submit:** Feedback can only be submitted for the **most recently completed sprint**
- **One submission per section:** Each Section Manager can submit one feedback per section they manage

### Feedback Questions
1. **Overall Satisfaction (1-5):** Rate your overall satisfaction with the sprint
2. **What went well:** Share positive outcomes and achievements
3. **What did not go well:** Share challenges and areas for improvement

### Viewing History
You can view your previously submitted feedback in the "View Previous Feedback" tab, 
but you cannot edit past submissions.
```

---

## 5. Data Model

### 5.1 Task Fields

| Field Name | Description | Source | Editable By |
|------------|-------------|--------|-------------|
| UniqueTaskId | Unique identifier for each task | System-generated | None |
| SprintNumber | Sprint the task is assigned to | System/Admin | Admin (Sprint Planning) |
| SprintName | Name of the sprint | System | None |
| SprintStartDt | Sprint start date | System | None |
| SprintEndDt | Sprint end date | System | None |
| OriginalSprintNumber | First sprint the task was assigned to | System | None |
| TaskOrigin | "New" or "Carryover" | Calculated | None |
| SprintsAssigned | Comma-separated list of all sprints | System | None |
| TicketNum | Parent ticket number | iTrack | None |
| TaskNum | Task number | iTrack | None |
| TaskCount | Position in ticket (e.g., "1/3") | Calculated | None |
| TicketType | SR, PR, IR, NC, or AD | iTrack | None |
| Section | Lab section/team | iTrack | None |
| CustomerName | Customer name | iTrack | None |
| Status | Task status | iTrack | Admin (Sprint View) |
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

### 5.2 Priority Values

| Value | Label | Color |
|-------|-------|-------|
| 5 | 🔴 Critical | Red |
| 4 | 🟠 High | Orange/Yellow |
| 3 | 🟡 Medium | Yellow |
| 2 | 🟢 Low | Green |
| 1 | ⚪ Minimal | White/Gray |
| 0 | ⚫ None/No longer needed | Black/Gray |
| NotAssigned | Not Assigned | Default |

### 5.3 Status Values

**Open Statuses:** Tasks remain in backlog and carry over
- Pending
- Accepted
- In Progress
- (any status not in closed list)

**Closed Statuses:** Tasks are completed and don't carry over
- Completed
- Closed
- Resolved
- Cancelled
- Canceled
- Done
- Excluded from Carryover

### 5.4 Ticket Types

| Code | Full Name |
|------|-----------|
| SR | Service Request |
| PR | Problem |
| IR | Incident Request |
| NC | Non-classified IS Requests |
| AD | Admin Request |

### 5.5 User Data Model

| Field | Description |
|-------|-------------|
| Username | Login username (unique) |
| Password | Login password |
| Role | Admin, PBIDS User, Section Manager, Section User |
| Section | Comma-separated list of assigned sections |
| DisplayName | Display name shown in UI |
| Active | Boolean - whether user can log in |

### 5.6 Sprint Calendar Data Model

| Field | Description |
|-------|-------------|
| SprintNumber | Unique sprint identifier (integer) |
| SprintName | Display name (e.g., "Sprint 10") |
| SprintStartDt | Start date |
| SprintEndDt | End date |

### 5.7 Feedback Data Model

| Field | Description |
|-------|-------------|
| SprintNumber | Sprint being reviewed |
| Section | Section providing feedback |
| SubmittedBy | Username of submitter |
| OverallSatisfaction | Rating 1-5 |
| WhatWentWell | Free text |
| WhatDidNotGoWell | Free text |
| SubmittedAt | Timestamp |

### 5.8 Off Days Data Model

| Field | Description |
|-------|-------------|
| SprintNumber | Sprint the off day applies to |
| TeamMember | Team member email/identifier |
| OffDate | Date the team member is off |

### 5.9 Worklog Data Model

| Field | Description |
|-------|-------------|
| TaskNum | Related task number |
| Owner | Person who logged the work |
| LogDate | Date of the worklog entry |
| MinutesSpent | Minutes logged |
| SprintNumber | Sprint containing the log date |

---

## 6. Workflows

### 6.1 Task Import Workflow

1. Admin exports tasks from iTrack (CSV format)
2. Admin navigates to Upload Tasks page
3. Admin uploads CSV file
4. System validates CSV structure
5. System imports tasks:
   - New tasks are added to task store
   - Existing tasks are updated with new data
   - Tasks appear in Work Backlogs page
6. Success message shows counts

### 6.2 Sprint Assignment Workflow

1. Admin navigates to Work Backlogs & Sprint Assignment page
2. Admin views all open tasks
3. Admin selects tasks using checkboxes
4. Admin selects target sprint from dropdown
5. Admin clicks "Assign to Sprint" button
6. System adds sprint number to SprintsAssigned field
7. Tasks appear in Sprint Planning for that sprint

### 6.3 Sprint Planning Workflow

1. Admin navigates to Sprint Planning page
2. Admin selects sprint to plan
3. Admin edits planning fields:
   - HoursEstimated for capacity planning
   - GoalType (Mandatory/Stretch) for capacity limits
   - Priority fields
   - Dependencies
   - Comments
4. Admin monitors capacity summary
5. Admin clicks Save Changes
6. System validates and saves all changes

### 6.4 Task Status Update Workflow

1. Admin navigates to Sprint View page
2. Admin selects sprint and goes to "Update Status" tab
3. Admin selects tasks to close
4. Admin selects new status and update date
5. System shows impact preview (which sprint task will close in)
6. Admin clicks Update button
7. Tasks are marked as closed and won't carry over

### 6.5 Carryover Workflow (Automatic)

1. Sprint ends with open tasks
2. When viewing next sprint, system automatically includes:
   - All tasks originally assigned to new sprint (TaskOrigin: New)
   - All open tasks from previous sprints (TaskOrigin: Carryover)
3. SprintsAssigned field tracks history (e.g., "10, 11, 12")

### 6.6 Off Days Configuration Workflow

1. Admin navigates to Admin Config > Off Days tab
2. Admin selects sprint to configure
3. System displays checkbox grid:
   - Rows: Active team members
   - Columns: Sprint weekdays
4. Admin unchecks days when team members are unavailable
5. Changes save automatically
6. Off days appear highlighted in Worklog Activity reports

### 6.7 Sprint Feedback Workflow

1. Sprint N ends, Sprint N+1 begins
2. Section Manager navigates to Sprint Feedback page
3. System shows feedback form for Sprint N-1 (just completed)
4. Section Manager completes form for each section they manage:
   - Overall Satisfaction (1-5)
   - What went well
   - What did not go well
5. Section Manager submits feedback
6. Feedback is stored (one submission per section per sprint)

---

## 7. Configuration

### 7.1 Sprint Schedule Configuration

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| duration_days | 14 | Sprint length in days |
| start_weekday | 3 | Start day (0=Monday, 3=Thursday) |
| end_weekday | 2 | End day (0=Monday, 2=Wednesday) |
| cycle_name | "Thursday-to-Wednesday" | Display name for cycle |

### 7.2 Capacity Configuration

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| max_hours | 52 | Maximum capacity per person |
| warning_hours | 45 | Warning threshold |
| capacity_percentage | 65 | Target utilization % |

### 7.3 TAT Thresholds

| Ticket Type | At-Risk Threshold | Exceeded Threshold |
|-------------|-------------------|-------------------|
| IR (Incident) | 0.6 days | 0.8 days |
| SR (Service) | 18 days | 22 days |

### 7.4 Capacity Limits by Goal Type

| Goal Type | Hours Limit | Percentage |
|-----------|-------------|------------|
| Mandatory | 48 hours | 60% |
| Stretch | 16 hours | 20% |
| Total | 80 hours | 100% |

---

## 8. Table Display Conventions

### 8.1 Row Styling

- **Multi-task tickets:** Alternating background colors for ticket groups
  - Even groups: Light green (#e8f4e8)
  - Odd groups: Light blue (#e8e8f4)

### 8.2 Cell Styling

- **Priority cells:** Color-coded by value
- **DaysOpen cells:** Color-coded by TAT risk
- **TaskOrigin cells:** Color-coded (New vs Carryover)

### 8.3 Worklog Activity Highlighting

- **Weekends:** Light purple background (#f8f5fc)
- **Off Days:** Light red background (#ffe6e6)

### 8.4 Capacity Table Styling

- **OK:** Green background (#d4edda)
- **Warning:** Yellow background (#fff3cd)
- **Overload:** Red background (#ffe6e6)

---

## 9. Export Functionality

All data tables support export with the following options:

| Format | Button Label | File Extension |
|--------|--------------|----------------|
| Excel | "📥 Export Excel" or "📥 Export to Excel" | .xlsx |
| CSV | "📥 Export CSV" | .csv |

Export files are named with context and timestamp:
- `sprint_planning_{sprint}_{timestamp}.xlsx`
- `work_backlogs_{timestamp}.xlsx`
- `section_view_{section}_{timestamp}.xlsx`
- `completed_tasks.xlsx`
- `sprint_{N}_tasks.csv`

---

## 10. Validation Rules

### 10.1 User Management

- Username must be unique
- Cannot delete users (only deactivate)
- Cannot deactivate last active Admin
- Section Manager and Section User roles require at least one section assigned

### 10.2 Sprint Calendar

- Sprint numbers must be unique
- End date must be after start date
- Sprints cannot be deleted (historical data integrity)

### 10.3 Task Status Updates

- Status update date cannot be before task assigned date
- Only closed statuses can be selected for closing tasks

### 10.4 Sprint Feedback

- Only Section Managers can submit feedback
- One submission per section per sprint
- At least one comment required (what went well OR what did not go well)

---

## 11. Navigation Structure

```
Home (app.py)
├── 📊 Dashboard
├── 📤 Upload Tasks (Admin)
├── 🧪 Sprint View
├── 👥 Section View
├── 📈 Analytics
├── ✅ Completed Tasks (Admin)
├── ✏️ Sprint Planning (Admin)
├── 📋 Work Backlogs & Sprint Assignment (Admin)
├── 📊 Worklog Activity (Admin)
├── ⚙️ Admin Config (Admin)
│   ├── 📅 Sprint Calendar
│   ├── 👥 User Management
│   ├── 🧑‍💼 Team Members
│   └── 🏖️ Off Days
└── 💬 Sprint Feedback (Section Manager)
```

---

## 12. Glossary

| Term | Definition |
|------|------------|
| **Backlog** | Collection of all open tasks not yet completed |
| **Carryover** | Task that wasn't completed in its original sprint and moves to the next sprint |
| **Capacity** | Available working hours for a team member (default 52 hours/sprint) |
| **GoalType** | Classification of task importance: Mandatory (must complete) or Stretch (if time permits) |
| **iTrack** | Source ticketing system from which task data is imported |
| **Off Day** | Day when a team member is unavailable (vacation, sick leave, etc.) |
| **Sprint** | Two-week work cycle (14 days) |
| **TAT** | Turn-Around Time - target completion timeframe for a ticket type |
| **Ticket** | Parent work item that may contain multiple tasks |
| **Task** | Individual unit of work, child of a ticket |
| **Worklog** | Time tracking entry recording work performed |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-05 | PBIDS Team | Initial document |

---

*End of Document*
