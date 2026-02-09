# User Access Levels

This document describes the access levels for different user types in the Sprint Dashboard application.

## User Roles Hierarchy

| Rank | Role | Description |
|------|------|-------------|
| 1 | **Admin** | Full system access, can manage users and configurations |
| 2 | **PIBIDS User** | Team Member with full edit access to sprint planning |
| 3 | **PIBIDS Viewer** | Team Member & PLM Leadership with view-only access to sprint planning (same visibility as PIBIDS User) |
| 4 | **Section Manager** | Can manage tasks within their assigned section(s) |
| 5 | **Section User** | View-only access to their assigned section(s) |

---

## Page Access Matrix

| Page | Admin | PIBIDS User | PIBIDS Viewer | Section Manager | Section User |
|------|:-----:|:-----------:|:-------------:|:---------------:|:------------:|
| **Dashboard** |
| Overview | ✅ View | ✅ View | ✅ View | ✅ View | ✅ View |
| **Lab Section View** |
| Sprint Overview | ✅ View | ✅ View | ✅ View | ✅ View (own sections) | ✅ View (own sections) |
| Sprint Prioritization | ✅ View/Edit | ✅ View/Edit | ✅ View | ✅ View/Edit (own sections) | ✅ View (own sections) |
| Sprint Feedback | ✅ View/Edit | ✅ View/Edit | ✅ View | ✅ View/Edit | ✅ View |
| **PIBIDS Sprint Planning** |
| Backlog Assign | ✅ View/Edit | ✅ View/Edit | ✅ View | ❌ No Access | ❌ No Access |
| Sprint Update | ✅ View/Edit | ✅ View/Edit | ✅ View | ❌ No Access | ❌ No Access |
| Worklog Activity | ✅ View | ✅ View | ✅ View | ❌ No Access | ❌ No Access |
| **Admin** |
| Admin Config | ✅ View/Edit | ❌ No Access | ❌ No Access | ❌ No Access | ❌ No Access |
| Data Source | ✅ View/Edit | ❌ No Access | ❌ No Access | ❌ No Access | ❌ No Access |
| Feature Requests | ✅ View/Edit | ❌ No Access | ❌ No Access | ❌ No Access | ❌ No Access |
| **Under Construction** |
| Reports & Analytics | ✅ View | ✅ View | ✅ View | ✅ View | ✅ View |

---

## Field-Level Edit Permissions

### Sprint Prioritization Page (Lab Section View)

| Field | Admin | PIBIDS User | PIBIDS Viewer | Section Manager | Section User |
|-------|:-----:|:-----------:|:-------------:|:---------------:|:------------:|
| CustomerPriority | ✅ Edit (all) | ✅ Edit (all) | ✅ View (all) | ✅ Edit (own section) | ✅ View (own section) |
| DependencyOn | ✅ Edit (all) | ✅ Edit (all) | ✅ View (all) | ✅ Edit (own section) | ✅ View (own section) |
| DependenciesLead | ✅ Edit (all) | ✅ Edit (all) | ✅ View (all) | ✅ Edit (own section) | ✅ View (own section) |
| Comments | ✅ Edit (all) | ✅ Edit (all) | ✅ View (all) | ✅ Edit (own section) | ✅ View (own section) |

### Backlog Assign Page (PIBIDS Sprint Planning)

| Field | Admin | PIBIDS User | PIBIDS Viewer | Section Manager | Section User |
|-------|:-----:|:-----------:|:-------------:|:---------------:|:------------:|
| SprintsAssigned | ✅ Edit | ✅ Edit | ✅ View | ❌ | ❌ |
| FinalPriority | ✅ Edit | ✅ Edit | ✅ View | ❌ | ❌ |
| GoalType | ✅ Edit | ✅ Edit | ✅ View | ❌ | ❌ |
| HoursEstimated | ✅ Edit | ✅ Edit | ✅ View | ❌ | ❌ |
| DependencySecured | ✅ Edit | ✅ Edit | ✅ View | ❌ | ❌ |
| Comments | ✅ Edit | ✅ Edit | ✅ View | ❌ | ❌ |

### Sprint Update Page (PIBIDS Sprint Planning)

| Field | Admin | PIBIDS User | PIBIDS Viewer | Section Manager | Section User |
|-------|:-----:|:-----------:|:-------------:|:---------------:|:------------:|
| GoalType | ✅ Edit | ✅ Edit | ✅ View | ❌ | ❌ |
| HoursEstimated | ✅ Edit | ✅ Edit | ✅ View | ❌ | ❌ |
| DependencySecured | ✅ Edit | ✅ Edit | ✅ View | ❌ | ❌ |
| Comments | ✅ Edit | ✅ Edit | ✅ View | ❌ | ❌ |
| NonCompletionReason | ✅ Edit | ✅ Edit | ✅ View | ❌ | ❌ |

---

## Section Filtering Rules

| Role | Section Visibility |
|------|-------------------|
| **Admin** | Can view/select all sections |
| **PIBIDS User** | Can view/select all sections |
| **PIBIDS Viewer** | Can view/select all sections |
| **Section Manager** | Limited to assigned section(s) only |
| **Section User** | Limited to assigned section(s) only |

**Note:** Section Managers and Section Users can be assigned to multiple sections (comma-separated in user configuration).

---

## Function Access Summary

| Function | Admin | PIBIDS User | PIBIDS Viewer | Section Manager | Section User |
|----------|:-----:|:-----------:|:-------------:|:---------------:|:------------:|
| View Dashboard | ✅ | ✅ | ✅ | ✅ | ✅ |
| View Sprint Data | ✅ All | ✅ All | ✅ All | ✅ Own Section | ✅ Own Section |
| Edit Customer Priority | ✅ All | ✅ All | ❌ | ✅ Own Section | ❌ |
| Assign Tasks to Sprints | ✅ | ✅ | ❌ | ❌ | ❌ |
| Set Final Priority | ✅ | ✅ | ❌ | ❌ | ❌ |
| Set Goal Type (Mandatory/Stretch) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Set Hours Estimated | ✅ | ✅ | ❌ | ❌ | ❌ |
| Sync Data from Snowflake | ✅ | ❌ | ❌ | ❌ | ❌ |
| Manage Users | ✅ | ❌ | ❌ | ❌ | ❌ |
| View Worklog Activity | ✅ | ✅ | ✅ | ❌ | ❌ |
| Export to Excel | ✅ | ✅ | ✅ | ✅ | ✅ |
| Submit Feedback | ✅ | ✅ | ❌ | ✅ | ❌ |

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Full access |
| ✅ View | View only |
| ✅ View/Edit | View and edit access |
| ✅ Edit | Can edit |
| ✅ All | Access to all sections |
| ✅ Own Section | Access limited to assigned section(s) |
| ❌ | No access |
| ❌ No Access | Page/function not available |
