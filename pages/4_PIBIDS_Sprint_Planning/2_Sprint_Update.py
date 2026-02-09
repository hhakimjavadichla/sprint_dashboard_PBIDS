"""
Sprint Planning Page
Editable interface for entering effort estimates, dependencies, and comments
Admin can update custom planning fields for sprint tasks
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
from modules.task_store import get_task_store, VALID_STATUSES
from modules.sprint_calendar import get_sprint_calendar, format_sprint_display
from modules.worklog_store import get_worklog_store
from modules.section_filter import exclude_forever_tickets, exclude_ad_tickets
from modules.capacity_validator import validate_capacity, get_capacity_dataframe
from components.auth import require_team_member_or_viewer, display_user_info, is_admin, is_pbids_user, is_pbids_viewer
from utils.grid_styles import apply_grid_styles, get_custom_css, STATUS_CELL_STYLE, PRIORITY_CELL_STYLE, DAYS_OPEN_CELL_STYLE, TASK_ORIGIN_CELL_STYLE, COLUMN_WIDTHS, get_column_width, COLUMN_DESCRIPTIONS, display_column_help, get_display_column_order, clean_subject_column
from utils.constants import VALID_SECTIONS
from utils.exporters import export_to_excel
from components.metrics_dashboard import display_ticket_task_metrics

# Apply custom tooltip styles
apply_grid_styles()

st.title("Sprint Update")
st.caption("_PIBIDS Team_")

# Require team member or viewer access (Admin, PIBIDS User, or PIBIDS Viewer)
require_team_member_or_viewer("Sprint Planning")
display_user_info()

# Check if user can edit (Admin and PIBIDS User can edit; PIBIDS Viewer is view-only)
can_edit_sprint = is_admin() or is_pbids_user()

# Instructions at the top
with st.expander("ℹ️ How to Use This Page", expanded=False):
    if can_edit_sprint:
        st.markdown("""
        ### Planning Workflow
        
        1. **Edit cells directly** in the table below (double-click to edit)
        2. **All fields are editable by Admin and PIBIDS Users**
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
        """)
    else:
        st.markdown("""
        ### View-Only Access
        
        You have **view-only access** to this page.
        - View sprint tasks and their current planning status
        - Only Admin and PIBIDS Users can edit sprint planning fields
        """)

# Load modules
task_store = get_task_store()
calendar = get_sprint_calendar()

# Check if we have tasks
all_tasks = task_store.get_all_tasks()
if all_tasks.empty:
    st.warning("📭 No tasks in the system yet.")
    st.info("Upload tasks first to plan sprints.")
    st.page_link("pages/7_Data_Source.py", label="Upload Tasks")
    st.stop()

# Get current sprint
current_sprint = calendar.get_current_sprint()
if not current_sprint:
    current_sprint = calendar.get_next_sprint()

# Sprint selector
all_sprints = calendar.get_all_sprints()
if all_sprints.empty:
    st.error("No sprints defined. Please update data/sprint_calendar.csv")
    st.stop()

current_sprint_num = current_sprint['SprintNumber'] if current_sprint else 1

# Option to show previous sprints
show_previous = st.checkbox("Show previous sprints", value=False, help="Enable to view and review past sprint data")

# Build sprint options
# Completed tasks are excluded from planning
# Note: These are TASK statuses, not ticket statuses
# Task statuses: Completed, Cancelled, Waiting, Accepted, Assigned, Logged
# Ticket statuses: Closed, Active, Resolved, Reopen, Waiting for Customer, Waiting for Resolution
COMPLETED_TASK_STATUSES = ['Completed', 'Cancelled']

sprint_options = []
default_idx = 0
for idx, row in all_sprints.iterrows():
    sprint_num = int(row['SprintNumber'])
    
    # Skip past sprints unless show_previous is enabled
    if not show_previous and sprint_num < current_sprint_num:
        continue
    
    label = format_sprint_display(row['SprintName'], row['SprintStartDt'], row['SprintEndDt'], sprint_num)
    
    # Count ALL tasks assigned to this sprint (including completed)
    sprint_tasks = task_store.get_sprint_tasks(sprint_num)
    task_count = len(sprint_tasks) if not sprint_tasks.empty else 0
    label += f" [{task_count} tasks]"
    
    sprint_options.append((sprint_num, label))
    if current_sprint and sprint_num == current_sprint['SprintNumber']:
        default_idx = len(sprint_options) - 1

if not sprint_options:
    st.error("No sprints available.")
    st.stop()

# Sprint selector
selected_label = st.selectbox(
    "Select Sprint to Plan",
    options=[opt[1] for opt in sprint_options],
    index=default_idx
)
selected_sprint_num = sprint_options[[opt[1] for opt in sprint_options].index(selected_label)][0]
selected_sprint = calendar.get_sprint_by_number(selected_sprint_num)

# Create sprint display name for section headings
selected_sprint_display = format_sprint_display(
    selected_sprint['SprintName'],
    selected_sprint['SprintStartDt'],
    selected_sprint['SprintEndDt'],
    selected_sprint_num
)

# Get ALL sprint tasks (including completed - policy: tasks stay in their assigned sprint)
sprint_tasks = task_store.get_sprint_tasks(selected_sprint_num)

if sprint_tasks.empty:
    st.info(f"📭 No tasks assigned to Sprint {selected_sprint_num}.")
    st.markdown("""    
    **To assign tasks:**
    1. Go to **Work Backlogs** page
    2. Select tasks you want to include in this sprint
    3. Assign them to Sprint {}
    """.format(selected_sprint_num))
    st.page_link("pages/4_PIBIDS_Sprint_Planning/2_Backlog_Assign.py", label="Go to Backlog Assign")
    st.stop()

# Filters
with st.sidebar:
    st.subheader("Filters")
    
    # Section filter
    sections = ['All'] + sorted(sprint_tasks['Section'].dropna().unique().tolist()) if 'Section' in sprint_tasks.columns else ['All']
    filter_section = st.multiselect("Section", sections, default=['All'])
    
    # Assignee filter
    assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in sprint_tasks.columns else 'AssignedTo'
    assignees = ['All'] + sorted(sprint_tasks[assignee_col].dropna().unique().tolist()) if assignee_col in sprint_tasks.columns else ['All']
    filter_assignee = st.multiselect("Assigned To", assignees, default=['All'])
    
    # Status filter
    statuses = ['All'] + sorted(sprint_tasks['TaskStatus'].dropna().unique().tolist()) if 'TaskStatus' in sprint_tasks.columns else ['All']
    filter_status = st.multiselect("Status", statuses, default=['All'])
    
    # Show only unestimated
    show_unestimated = st.checkbox("Show only tasks without estimates", value=False)
    
    # Forever ticket filter
    exclude_forever = st.checkbox(
        "Exclude Forever Tickets",
        value=False,
        help="Hide Standing Meetings and Miscellaneous Meetings tasks",
        key="exclude_forever_planning"
    )
    
    # AD ticket filter
    exclude_ad = st.checkbox(
        "Exclude AD Tickets",
        value=False,
        help="Hide Admin Request (AD) tickets",
        key="exclude_ad_planning"
    )

# Apply filters
filtered_tasks = sprint_tasks.copy()

if 'All' not in filter_section and filter_section:
    filtered_tasks = filtered_tasks[filtered_tasks['Section'].isin(filter_section)]

if 'All' not in filter_assignee and filter_assignee:
    filtered_tasks = filtered_tasks[filtered_tasks[assignee_col].isin(filter_assignee)]

if 'All' not in filter_status and filter_status:
    filtered_tasks = filtered_tasks[filtered_tasks['TaskStatus'].isin(filter_status)]

if show_unestimated:
    filtered_tasks = filtered_tasks[filtered_tasks['HoursEstimated'].isna()]

# Apply forever ticket filter
if exclude_forever:
    filtered_tasks = exclude_forever_tickets(filtered_tasks)

# Apply AD ticket filter
if exclude_ad:
    filtered_tasks = exclude_ad_tickets(filtered_tasks)

st.caption(f"Showing {len(filtered_tasks)} of {len(sprint_tasks)} tasks")

# Summary metrics by ticket type (reusable component) - use filtered data
display_ticket_task_metrics(filtered_tasks)

# Prepare editable dataframe
if not filtered_tasks.empty:
    # Get all available sprint numbers for dropdown (blank = remove from this sprint)
    all_sprint_numbers = [''] + sorted(all_sprints['SprintNumber'].unique().tolist())
    
    # Use all filtered tasks (AgGrid has built-in filtering)
    display_tasks = filtered_tasks.copy()
    assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in filtered_tasks.columns else 'AssignedTo'
    
    st.caption(f"Showing {len(display_tasks)} tasks")
    
    st.divider()
    
    # Define DependencySecured dropdown values
    DEPENDENCY_SECURED_VALUES = ['', 'Yes', 'Pending', 'No']
    
    # Define Dependency dropdown values
    DEPENDENCY_VALUES = ['', 'Yes', 'No']
    
    # Priority dropdown values: blank=not set yet, 0=No longer needed, 1=Lowest to 5=Highest
    # Use strings for all values to avoid ag-Grid type coercion issues
    PRIORITY_VALUES = ['', '0', '1', '2', '3', '4', '5']
    
    # Build edit dataframe with all required columns in specified order
    edit_df = display_tasks.copy()
    
    # Ensure all required columns exist
    required_cols = [
        'SprintNumber', 'SprintName', 'SprintStartDt', 'SprintEndDt',
        'DaysOpen', 'CustomerPriority', 'DependencyOn', 'DependenciesLead',
        'DependencySecured', 'Comments', 'HoursEstimated', 'TicketType',
        'Section', 'CustomerName', 'TicketNum', 'TaskNum', 'TaskStatus',
        'AssignedTo', 'Subject', 'TicketCreatedDt', 'TaskCreatedDt',
        'TaskMinutesSpent'
    ]
    
    for col in required_cols:
        if col not in edit_df.columns:
            edit_df[col] = None
    
    # TaskHoursSpent and TicketHoursSpent are calculated from worklog data
    # by task_store._calculate_hours_from_worklog() - do not overwrite here
    if 'TaskHoursSpent' not in edit_df.columns:
        edit_df['TaskHoursSpent'] = 0.0
    if 'TicketHoursSpent' not in edit_df.columns:
        edit_df['TicketHoursSpent'] = 0.0
    
    # Ensure FinalPriority column exists
    # Default is Null - admin must set it explicitly
    if 'FinalPriority' not in edit_df.columns:
        edit_df['FinalPriority'] = None
    
    # Convert priority columns to string for dropdown compatibility
    for priority_col in ['CustomerPriority', 'FinalPriority']:
        if priority_col in edit_df.columns:
            edit_df[priority_col] = edit_df[priority_col].apply(
                lambda x: '' if pd.isna(x) else str(int(x)) if isinstance(x, (int, float)) else str(x)
            )
    
    # TaskOrigin is always 'Assigned' since all sprint assignments are manual
    edit_df['TaskOrigin'] = 'Assigned'
    
    # Calculate TaskCount for each ticket (e.g., "1/3", "2/3", "3/3")
    if 'TicketNum' in edit_df.columns and 'DaysOpen' in edit_df.columns:
        # Count tasks per ticket
        ticket_counts = edit_df.groupby('TicketNum').size().to_dict()
        
        # Sort by DaysOpen (oldest tasks first), then by TaskNum within ticket
        edit_df = edit_df.sort_values(
            by=['DaysOpen', 'TicketNum', 'TaskNum'],
            ascending=[False, True, True],
            na_position='last'
        ).reset_index(drop=True)
        
        # Add TaskCount column and track ticket groups for row banding
        task_counts = []
        ticket_group_ids = []
        current_group = 0
        prev_ticket = None
        task_counter = {}
        
        for idx, row in edit_df.iterrows():
            ticket = row['TicketNum']
            total = ticket_counts.get(ticket, 1)
            
            # Track task number within ticket
            if ticket not in task_counter:
                task_counter[ticket] = 0
            task_counter[ticket] += 1
            task_counts.append(f"{task_counter[ticket]}/{total}")
            
            # Track ticket group for row banding
            if ticket != prev_ticket:
                current_group += 1
                prev_ticket = ticket
            ticket_group_ids.append(current_group)
        
        edit_df['TaskCount'] = task_counts
        edit_df['_TicketGroup'] = ticket_group_ids
        edit_df['_IsMultiTask'] = edit_df['TicketNum'].map(lambda x: ticket_counts.get(x, 1) > 1)
    
    # Use display name for AssignedTo if available
    if 'AssignedTo_Display' in edit_df.columns:
        edit_df['AssignedTo'] = edit_df['AssignedTo_Display']
    
    # Ensure GoalType column exists
    if 'GoalType' not in edit_df.columns:
        edit_df['GoalType'] = ''
    
    # Add CompletedThisSprint column (auto-calculated based on TaskStatus and TaskResolvedDt)
    sprint_start_dt = pd.to_datetime(selected_sprint['SprintStartDt'])
    sprint_end_dt = pd.to_datetime(selected_sprint['SprintEndDt'])
    
    def is_completed_this_sprint(row):
        """Check if task was completed within the sprint window."""
        task_status = str(row.get('TaskStatus', '')).strip()
        if task_status not in COMPLETED_TASK_STATUSES:
            return 'No'
        
        # Check if TaskResolvedDt is within sprint window
        resolved_dt = row.get('TaskResolvedDt')
        if pd.isna(resolved_dt):
            return 'No'
        
        try:
            resolved_dt = pd.to_datetime(resolved_dt)
            if sprint_start_dt <= resolved_dt <= sprint_end_dt:
                return 'Yes'
            else:
                return 'No'
        except:
            return 'No'
    
    edit_df['CompletedThisSprint'] = edit_df.apply(is_completed_this_sprint, axis=1)
    
    # Ensure NonCompletionReason column exists
    if 'NonCompletionReason' not in edit_df.columns:
        edit_df['NonCompletionReason'] = ''
    else:
        edit_df['NonCompletionReason'] = edit_df['NonCompletionReason'].fillna('')
    
    # Create combined Sprint column with formatted display
    edit_df['Sprint'] = edit_df.apply(
        lambda row: format_sprint_display(
            row.get('SprintName', ''),
            row.get('SprintStartDt'),
            row.get('SprintEndDt'),
            int(row['SprintNumber']) if pd.notna(row.get('SprintNumber')) else None
        ) if pd.notna(row.get('SprintNumber')) else '',
        axis=1
    )
    
    # Use standardized column order from config
    display_order = get_display_column_order('AssignedTo')
    
    # Add Sprint column (replace SprintName position or add after SprintNumber)
    if 'SprintName' in display_order:
        idx = display_order.index('SprintName')
        display_order.insert(idx, 'Sprint')
    elif 'SprintNumber' in display_order:
        idx = display_order.index('SprintNumber') + 1
        display_order.insert(idx, 'Sprint')
    else:
        display_order.insert(0, 'Sprint')
    
    # Add CompletedThisSprint and NonCompletionReason at the end
    display_order.extend(['CompletedThisSprint', 'NonCompletionReason'])
    
    available_cols = [col for col in display_order if col in edit_df.columns]
    edit_df = edit_df[available_cols].copy()
    
    # Clean subject column (remove LAB-XX: NNNNNN - prefix)
    edit_df = clean_subject_column(edit_df)
    
    # Define column view presets
    COLUMN_VIEWS = {
        'All Columns': None,  # None means show all columns
        'Hours & Capacity': ['TaskNum', 'Subject', 'AssignedTo', 'Section', 'GoalType', 
                             'HoursEstimated', 'TaskHoursSpent', 'TicketHoursSpent', 'CompletedThisSprint'],
        'Priority & Dependencies': ['TaskNum', 'Subject', 'AssignedTo', 'CustomerPriority', 'FinalPriority', 
                                    'DependencyOn', 'DependenciesLead', 'DependencySecured', 'Comments'],
        'Status Tracking': ['TaskNum', 'Subject', 'AssignedTo', 'TaskStatus', 'TaskOrigin', 
                           'DaysOpen', 'Sprint', 'CompletedThisSprint', 'NonCompletionReason']
    }
    
    # View selector
    selected_view = st.radio(
        "Column View: Select a preset to show only relevant columns for specific tasks",
        options=list(COLUMN_VIEWS.keys()),
        horizontal=True,
        key="sprint_update_view_selector"
    )
    
    # Get columns to show based on selected view
    view_columns = COLUMN_VIEWS[selected_view]
    
    # Helper function to check if column should be hidden
    def should_hide(col_name):
        if view_columns is None:  # All Columns view
            return False
        return col_name not in view_columns
    
    # Configure editable AgGrid
    gb = GridOptionsBuilder.from_dataframe(edit_df)
    gb.configure_default_column(resizable=True, sortable=True, filterable=True)
    
    # Hidden columns for tracking (always hidden)
    gb.configure_column('_TicketGroup', hide=True)
    gb.configure_column('_IsMultiTask', hide=True)
    
    # Editable prefix for column names (only show if user can edit)
    edit_prefix = '✏️ ' if can_edit_sprint else ''
    
    # Configure columns - editable columns marked with prefix
    # Sprint fields - combined into single column, keep SprintNumber editable but hidden
    gb.configure_column('SprintNumber', header_name='SprintNumber', width=COLUMN_WIDTHS['SprintNumber'], editable=can_edit_sprint,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('SprintNumber', ''),
                        cellEditor='agSelectCellEditor',
                        cellEditorParams={'values': all_sprint_numbers},
                        hide=True)
    gb.configure_column('Sprint', header_name='Selected Sprint', width=200, editable=False,
                        headerTooltip='Sprint assignment with dates', hide=should_hide('Sprint'))
    gb.configure_column('SprintName', hide=True)
    gb.configure_column('SprintStartDt', hide=True)
    gb.configure_column('SprintEndDt', hide=True)
    
    # Task Origin (New vs Carryover)
    gb.configure_column('TaskOrigin', header_name='TaskOrigin', width=COLUMN_WIDTHS['TaskOrigin'], editable=False,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TaskOrigin', ''), hide=should_hide('TaskOrigin'))
    
    # Sprints Assigned (read-only in Sprint Planning)
    gb.configure_column('SprintsAssigned', header_name='All Sprints Assigned', width=COLUMN_WIDTHS.get('SprintsAssigned', 130), editable=False,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('SprintsAssigned', ''), hide=should_hide('SprintsAssigned'))
    
    # Ticket/Task info - non-editable
    gb.configure_column('TicketNum', header_name='TicketNum', width=COLUMN_WIDTHS['TicketNum'], editable=False,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TicketNum', ''), hide=should_hide('TicketNum'))
    gb.configure_column('TaskCount', header_name='Task#', width=COLUMN_WIDTHS['TaskCount'], editable=False,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TaskCount', ''), hide=should_hide('TaskCount'))
    gb.configure_column('TicketType', header_name='TicketType', width=COLUMN_WIDTHS['TicketType'], editable=False,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TicketType', ''), hide=should_hide('TicketType'))
    gb.configure_column('Section', header_name='Section', width=COLUMN_WIDTHS['Section'], editable=False,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('Section', ''), hide=should_hide('Section'))
    gb.configure_column('CustomerName', header_name='CustomerName', width=COLUMN_WIDTHS['CustomerName'], editable=False,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('CustomerName', ''), hide=should_hide('CustomerName'))
    gb.configure_column('TaskNum', header_name='TaskNum', width=COLUMN_WIDTHS['TaskNum'], editable=False,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TaskNum', ''), hide=should_hide('TaskNum'))
    gb.configure_column('TaskStatus', header_name='TaskStatus', width=COLUMN_WIDTHS.get('TaskStatus', 100), editable=False,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TaskStatus', 'Task status from iTrack'), hide=should_hide('TaskStatus'))
    gb.configure_column('TicketStatus', header_name='TicketStatus', width=COLUMN_WIDTHS.get('TicketStatus', 100), editable=False,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TicketStatus', ''), hide=should_hide('TicketStatus'))
    gb.configure_column('AssignedTo', header_name='AssignedTo', width=COLUMN_WIDTHS['AssignedTo'], editable=False,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('AssignedTo', ''), hide=should_hide('AssignedTo'))
    gb.configure_column('Subject', header_name='Subject', width=COLUMN_WIDTHS.get('Subject', 200), editable=False,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('Subject', ''), tooltipField='Details', hide=should_hide('Subject'))
    gb.configure_column('Details', hide=True)  # Hidden - only used for Subject tooltip
    gb.configure_column('TicketCreatedDt', header_name='TicketCreatedDt', width=COLUMN_WIDTHS['TicketCreatedDt'], editable=False,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TicketCreatedDt', ''), hide=should_hide('TicketCreatedDt'))
    gb.configure_column('TaskCreatedDt', header_name='TaskCreatedDt', width=COLUMN_WIDTHS['TaskCreatedDt'], editable=False,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TaskCreatedDt', ''), hide=should_hide('TaskCreatedDt'))
    
    # Metrics and planning fields - editable ones marked with prefix
    gb.configure_column('DaysOpen', header_name='DaysOpen', width=COLUMN_WIDTHS['DaysOpen'], editable=False, 
                        headerTooltip=COLUMN_DESCRIPTIONS.get('DaysOpen', ''),
                        type=['numericColumn'], hide=should_hide('DaysOpen'))
    gb.configure_column('CustomerPriority', header_name=f'{edit_prefix}CustomerPriority', width=COLUMN_WIDTHS['CustomerPriority'], editable=can_edit_sprint,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('CustomerPriority', ''),
                        cellEditor='agSelectCellEditor',
                        cellEditorParams={'values': PRIORITY_VALUES}, hide=should_hide('CustomerPriority'))
    gb.configure_column('FinalPriority', header_name=f'{edit_prefix}FinalPriority', width=COLUMN_WIDTHS['FinalPriority'], editable=can_edit_sprint,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('FinalPriority', ''),
                        cellEditor='agSelectCellEditor',
                        cellEditorParams={'values': PRIORITY_VALUES}, hide=should_hide('FinalPriority'))
    gb.configure_column('GoalType', header_name=f'{edit_prefix}GoalType', width=COLUMN_WIDTHS['GoalType'], editable=can_edit_sprint,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('GoalType', ''),
                        cellEditor='agSelectCellEditor',
                        cellEditorParams={'values': ['', 'Mandatory', 'Stretch']}, hide=should_hide('GoalType'))
    gb.configure_column('DependencyOn', header_name=f'{edit_prefix}Dependency', width=COLUMN_WIDTHS['DependencyOn'], editable=can_edit_sprint,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('DependencyOn', ''),
                        cellEditor='agSelectCellEditor',
                        cellEditorParams={'values': DEPENDENCY_VALUES}, hide=should_hide('DependencyOn'))
    gb.configure_column('DependenciesLead', header_name=f'{edit_prefix}DependencyLead(s)', width=COLUMN_WIDTHS['DependenciesLead'], editable=can_edit_sprint,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('DependenciesLead', ''),
                        tooltipField='DependenciesLead',
                        cellEditor='agLargeTextCellEditor',
                        cellEditorPopup=True,
                        cellEditorParams={'maxLength': 1000, 'rows': 10, 'cols': 50}, hide=should_hide('DependenciesLead'))
    gb.configure_column('DependencySecured', header_name=f'{edit_prefix}DependencySecured', width=COLUMN_WIDTHS['DependencySecured'], editable=can_edit_sprint,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('DependencySecured', ''),
                        cellEditor='agSelectCellEditor',
                        cellEditorParams={'values': DEPENDENCY_SECURED_VALUES}, hide=should_hide('DependencySecured'))
    gb.configure_column('Comments', header_name=f'{edit_prefix}Comments', width=COLUMN_WIDTHS['Comments'], editable=can_edit_sprint,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('Comments', ''),
                        tooltipField='Comments',
                        cellEditor='agLargeTextCellEditor',
                        cellEditorPopup=True,
                        cellEditorParams={'maxLength': 1000, 'rows': 10, 'cols': 50}, hide=should_hide('Comments'))
    gb.configure_column('HoursEstimated', header_name=f'{edit_prefix}HoursEstimated', width=COLUMN_WIDTHS['HoursEstimated'], editable=can_edit_sprint,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('HoursEstimated', ''), type=['numericColumn'], hide=should_hide('HoursEstimated'))
    gb.configure_column('TaskHoursSpent', header_name='TaskHoursSpent', width=COLUMN_WIDTHS['TaskHoursSpent'], editable=False,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TaskHoursSpent', ''), type=['numericColumn'], hide=should_hide('TaskHoursSpent'))
    gb.configure_column('TicketHoursSpent', header_name='TicketHoursSpent', width=COLUMN_WIDTHS['TicketHoursSpent'], editable=False,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TicketHoursSpent', ''), type=['numericColumn'], hide=should_hide('TicketHoursSpent'))
    
    # Sprint Completion Tracking columns
    gb.configure_column('CompletedThisSprint', header_name='CompletedThisSprint', width=140, editable=False,
                        headerTooltip='Auto-calculated: Yes if task completed within sprint window', hide=should_hide('CompletedThisSprint'))
    gb.configure_column('NonCompletionReason', header_name=f'{edit_prefix}NonCompletionReason', width=200, editable=can_edit_sprint,
                        headerTooltip='Editable: Document why task was not completed in this sprint',
                        tooltipField='NonCompletionReason',
                        cellEditor='agLargeTextCellEditor',
                        cellEditorPopup=True,
                        cellEditorParams={'maxLength': 500, 'rows': 5, 'cols': 40}, hide=should_hide('NonCompletionReason'))
    
    gb.configure_pagination(enabled=False)
    gb.configure_selection(selection_mode='multiple', use_checkbox=False)
    
    # Row styling for multi-task ticket groups (alternating colors)
    row_style_jscode = JsCode("""
    function(params) {
        if (params.data._IsMultiTask) {
            if (params.data._TicketGroup % 2 === 0) {
                return { 'backgroundColor': '#e8f4e8' };  // Light green for even groups
            } else {
                return { 'backgroundColor': '#e8e8f4' };  // Light blue for odd groups
            }
        }
        return null;
    }
    """)
    
    grid_options = gb.build()
    grid_options['getRowStyle'] = row_style_jscode
    grid_options['enableBrowserTooltips'] = False  # Disable browser tooltips to avoid double tooltip
    
    if can_edit_sprint:
        st.caption("✏️ = Editable column (double-click to edit). Changes are saved when you click 'Save Changes' below.")
    else:
        st.caption("🔒 **View-only mode** - You do not have edit permissions for this page.")
    
    # Column descriptions help
    display_column_help(title="❓ Column Descriptions")
    
    # Display editable grid
    grid_response = AgGrid(
        edit_df,
        gridOptions=grid_options,
        height=600,
        theme='streamlit',
        update_mode=GridUpdateMode.VALUE_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        custom_css=get_custom_css()
    )
    
    # Get edited data
    edited_df = pd.DataFrame(grid_response['data'])
    
    # Save button - right below the table (only for users who can edit)
    if can_edit_sprint:
        col_save1, col_save2, col_save3 = st.columns([1, 2, 1])
        
        with col_save1:
            if st.button("💾 Save Changes", type="primary", use_container_width=True, key="save_btn_top"):
                editable_fields = ['CustomerPriority', 'FinalPriority', 'HoursEstimated', 
                                 'GoalType', 'DependencyOn', 'DependenciesLead', 'DependencySecured', 'Comments',
                                 'NonCompletionReason']
                sprint_changes = 0
                
                # Handle SprintNumber changes - modifies SprintsAssigned column
                # Blank/empty = "remove from THIS sprint only" (task may stay in other sprints)
                for _, row in edited_df.iterrows():
                    task_num = row.get('TaskNum')
                    if pd.isna(task_num):
                        continue
                    
                    if 'SprintNumber' in row.index:
                        new_sprint_num = row['SprintNumber']
                        new_sprint_str = str(new_sprint_num).strip() if pd.notna(new_sprint_num) else ''
                        
                        # Blank or 'nan' means remove from this sprint
                        if new_sprint_str == '' or new_sprint_str.lower() == 'nan':
                            success, msg = task_store.remove_task_from_sprint(str(task_num), selected_sprint_num)
                            if success:
                                sprint_changes += 1
                        else:
                            # Check if moving to different sprint
                            try:
                                new_sprint_int = int(float(new_sprint_str))  # Handle '1.0' format
                                if new_sprint_int != selected_sprint_num:
                                    task_store.remove_task_from_sprint(str(task_num), selected_sprint_num)
                                    task_store.assign_task_to_sprint(str(task_num), new_sprint_int)
                                    sprint_changes += 1
                            except (ValueError, TypeError):
                                pass  # Invalid value, skip
                
                # Build updates list for editable fields
                updates = []
                for _, row in edited_df.iterrows():
                    if pd.notna(row.get('TaskNum')):
                        update = {'TaskNum': row['TaskNum']}
                        for field in editable_fields:
                            if field in row.index:
                                update[field] = row[field]
                        updates.append(update)
                
                # Use centralized update method
                success, errors = task_store.update_tasks(updates)
                
                # If only sprint changes were made (no editable field changes), save manually
                if sprint_changes > 0 and success == 0:
                    task_store.save()
                
                if success > 0 or sprint_changes > 0:
                    msg = f"✅ Successfully saved {success} task(s)"
                    if sprint_changes > 0:
                        msg += f" ({sprint_changes} sprint assignment(s) changed)"
                    st.success(msg)
                    
                    # Recalculate capacity
                    updated_sprint = task_store.get_sprint_tasks(selected_sprint_num)
                    new_capacity = validate_capacity(updated_sprint)
                    
                    if new_capacity['overloaded']:
                        st.warning(f"⚠️ Capacity Alert: {len(new_capacity['overloaded'])} people now overloaded")
                    
                    st.rerun()
                elif errors:
                    st.error(f"❌ Errors: {', '.join(errors[:3])}")
        
        with col_save2:
            st.caption("Changes are only saved when you click 'Save Changes'")
        
        with col_save3:
            # Export button
            from utils.exporters import export_to_excel
            excel_data = export_to_excel(edited_df)
            st.download_button(
                "📥 Export",
                excel_data,
                f"sprint_{selected_sprint_num}_planning.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    else:
        # View-only: just show export button
        col1, col2 = st.columns([1, 3])
        with col1:
            from utils.exporters import export_to_excel
            excel_data = export_to_excel(edited_df)
            st.download_button(
                "📥 Export to Excel",
                excel_data,
                f"sprint_{selected_sprint_num}_planning.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    st.divider()
    
    # Export section - exports current filtered view
    col_export1, col_export2 = st.columns([2, 6])
    
    with col_export1:
        # Export current filtered view
        export_df = edited_df.copy()
        # Remove internal columns from export
        export_cols = [c for c in export_df.columns if not c.startswith('_')]
        export_df = export_df[export_cols]
        
        excel_data = export_to_excel(export_df, sheet_name="Sprint Planning")
        filename = f"sprint_planning_{selected_sprint_num}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        
        st.download_button(
            label=f"📥 Export to Excel ({len(export_df)} tasks)",
            data=excel_data,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Export current filtered view to Excel"
        )
    
    with col_export2:
        st.caption("💡 Apply filters in sidebar to narrow down data before exporting.")
    
    st.divider()
    
    # Task Completion Status Table by User
    st.markdown(f"### Task Completion Status by User in {selected_sprint_display}")
    
    # Get ALL sprint tasks (including completed) for completion tracking
    all_sprint_tasks = task_store.get_sprint_tasks(selected_sprint_num)
    
    if not all_sprint_tasks.empty:
        # Use display name if available
        assignee_col_status = 'AssignedTo_Display' if 'AssignedTo_Display' in all_sprint_tasks.columns else 'AssignedTo'
        
        # Get sprint date range for daily columns
        sprint_start = pd.to_datetime(selected_sprint['SprintStartDt']).date()
        sprint_end = pd.to_datetime(selected_sprint['SprintEndDt']).date()
        sprint_dates = pd.date_range(start=sprint_start, end=sprint_end).date.tolist()
        
        # Parse TaskResolvedDt for completion date tracking
        if 'TaskResolvedDt' in all_sprint_tasks.columns:
            all_sprint_tasks['_ResolvedDate'] = pd.to_datetime(all_sprint_tasks['TaskResolvedDt'], errors='coerce').dt.date
        else:
            all_sprint_tasks['_ResolvedDate'] = None
        
        # Calculate completion stats per user with daily breakdown
        completion_stats = []
        users = sorted(all_sprint_tasks[assignee_col_status].dropna().unique().tolist())
        
        total_completed = 0
        total_assigned = 0
        daily_totals = {d: 0 for d in sprint_dates}
        
        for user in users:
            user_tasks = all_sprint_tasks[all_sprint_tasks[assignee_col_status] == user]
            assigned = len(user_tasks)
            completed_tasks = user_tasks[user_tasks['TaskStatus'].isin(COMPLETED_TASK_STATUSES)]
            completed = len(completed_tasks)
            
            total_completed += completed
            total_assigned += assigned
            
            row_data = {
                'User': user,
                'Completion': f"{completed}/{assigned}",
                'Percent': (completed / assigned * 100) if assigned > 0 else 0
            }
            
            # Add daily completion counts
            for date in sprint_dates:
                day_count = len(completed_tasks[completed_tasks['_ResolvedDate'] == date])
                col_name = date.strftime('%m/%d')
                row_data[col_name] = day_count
                daily_totals[date] += day_count
            
            completion_stats.append(row_data)
        
        # Add total row
        total_row = {
            'User': 'TOTAL',
            'Completion': f"{total_completed}/{total_assigned}",
            'Percent': (total_completed / total_assigned * 100) if total_assigned > 0 else 0
        }
        for date in sprint_dates:
            col_name = date.strftime('%m/%d')
            total_row[col_name] = daily_totals[date]
        completion_stats.append(total_row)
        
        completion_df = pd.DataFrame(completion_stats)
        
        # Store percent values for styling
        percent_values = completion_df['Percent'].tolist()
        
        # Create display dataframe (exclude Percent column)
        date_cols = [d.strftime('%m/%d') for d in sprint_dates]
        display_cols = ['User', 'Completion'] + date_cols
        display_completion_df = completion_df[display_cols].copy()
        
        # Red gradient function - lighter (0%) to darker (100%)
        def get_red_gradient(percent):
            """Get red gradient color. 0% = light pink, 100% = dark red"""
            # RGB values: light pink (255, 235, 235) to dark red (139, 0, 0)
            r = int(255 - (percent / 100) * (255 - 139))
            g = int(235 - (percent / 100) * 235)
            b = int(235 - (percent / 100) * 235)
            return f'rgb({r}, {g}, {b})'
        
        def get_text_color(percent):
            """Get text color for readability - white for dark backgrounds"""
            return 'white' if percent >= 70 else 'black'
        
        # Color function for styling using index to look up values
        def style_completion_table(df):
            """Apply red gradient background to Completion column"""
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            
            for idx in df.index:
                percent = percent_values[idx]
                is_total = df.loc[idx, 'User'] == 'TOTAL'
                
                # Completion column - color by percent complete
                completion_bg = get_red_gradient(percent)
                completion_text = get_text_color(percent)
                styles.loc[idx, 'Completion'] = f'background-color: {completion_bg}; color: {completion_text}'
                
                # Bold for TOTAL row
                if is_total:
                    for col in df.columns:
                        styles.loc[idx, col] += '; font-weight: bold'
            
            return styles
        
        # Apply styling
        styled_df = display_completion_df.style.apply(style_completion_table, axis=None)
        
        # Display styled dataframe
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        st.caption("🔴 Red gradient: lighter = less complete → darker = more complete")
    else:
        st.info("No tasks assigned to this sprint yet.")
    
    st.divider()
    
    # Capacity Summary Section
    st.markdown(f"### Capacity Summary by Person in {selected_sprint_display}")
    st.caption("Shows estimated hours vs available hours from Team Availability (Admin Config)")
    
    # Calculate capacity from edited data (to show live updates)
    capacity_summary = task_store.get_capacity_summary(edited_df)
    
    # Load Team Availability from session state
    availability_key = f"team_availability_{selected_sprint_num}"
    team_availability = st.session_state.get(availability_key, pd.DataFrame())
    
    if not capacity_summary.empty:
        # Build availability lookup by team member name
        availability_lookup = {}
        if not team_availability.empty:
            for _, row in team_availability.iterrows():
                member_name = row.get('Team Member', '')
                total_hrs = row.get('Total Hrs Available', 80)
                mandatory_pct = row.get('Total Mandatory Hrs % Available', 70)
                stretch_pct = row.get('Total Stretch Hours %', 30)
                availability_lookup[member_name] = {
                    'mandatory_hrs': total_hrs * (mandatory_pct / 100),
                    'stretch_hrs': total_hrs * (stretch_pct / 100),
                    'total_hrs': total_hrs
                }
        
        # Create display DataFrame with ratios
        display_rows = []
        for _, row in capacity_summary.iterrows():
            member = row['AssignedTo']
            mandatory_est = row['MandatoryHours']
            stretch_est = row['StretchHours']
            
            # Get available hours from Team Availability (default: 48 mandatory, 16 stretch)
            avail = availability_lookup.get(member, {'mandatory_hrs': 48, 'stretch_hrs': 16, 'total_hrs': 80})
            
            # Calculate ratios
            mandatory_ratio = f"{mandatory_est:.0f}/{avail['mandatory_hrs']:.0f}"
            stretch_ratio = f"{stretch_est:.0f}/{avail['stretch_hrs']:.0f}"
            
            display_rows.append({
                'Team Member': member,
                'Mandatory Hours': mandatory_ratio,
                'Stretch Hours': stretch_ratio,
                'Mandatory_Est': mandatory_est,
                'Stretch_Est': stretch_est,
                'Mandatory_Avail': avail['mandatory_hrs'],
                'Stretch_Avail': avail['stretch_hrs']
            })
        
        display_capacity_df = pd.DataFrame(display_rows)
        
        # Heat map color function based on ratio (estimated/available) - single color gradient (blue)
        def get_ratio_color(estimated, available):
            """Get color based on ratio using blue gradient for density."""
            if available == 0:
                return 'background-color: rgb(245, 248, 255)'
            
            ratio = estimated / available
            # Clamp ratio between 0 and 1.5 for color calculation
            clamped_ratio = min(max(ratio, 0), 1.5)
            
            # Blue gradient: lighter blue (low) to darker blue (high)
            # Base color: light blue rgb(230, 240, 255) to dark blue rgb(30, 80, 180)
            intensity = clamped_ratio / 1.5  # Normalize to 0-1
            
            r = int(230 - intensity * 200)  # 230 -> 30
            g = int(240 - intensity * 160)  # 240 -> 80
            b = int(255 - intensity * 75)   # 255 -> 180
            
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            
            return f'background-color: rgb({r}, {g}, {b})'
        
        def get_ratio_text_color(estimated, available):
            """White text for high density cells."""
            if available == 0:
                return 'color: black'
            ratio = estimated / available
            return 'color: white' if ratio > 0.7 else 'color: black'
        
        # Store values for styling lookup
        capacity_values = {
            idx: {
                'mand_est': row['Mandatory_Est'],
                'mand_avail': row['Mandatory_Avail'],
                'stretch_est': row['Stretch_Est'],
                'stretch_avail': row['Stretch_Avail']
            }
            for idx, row in display_capacity_df.iterrows()
        }
        
        # Select only display columns
        display_cols_df = display_capacity_df[['Team Member', 'Mandatory Hours', 'Stretch Hours']].copy()
        
        # Style function for the table
        def style_capacity_table(df):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            
            for idx in df.index:
                vals = capacity_values.get(idx, {'mand_est': 0, 'mand_avail': 48, 'stretch_est': 0, 'stretch_avail': 16})
                
                # Mandatory Hours column
                mand_bg = get_ratio_color(vals['mand_est'], vals['mand_avail'])
                mand_text = get_ratio_text_color(vals['mand_est'], vals['mand_avail'])
                styles.loc[idx, 'Mandatory Hours'] = f'{mand_bg}; {mand_text}'
                
                # Stretch Hours column
                stretch_bg = get_ratio_color(vals['stretch_est'], vals['stretch_avail'])
                stretch_text = get_ratio_text_color(vals['stretch_est'], vals['stretch_avail'])
                styles.loc[idx, 'Stretch Hours'] = f'{stretch_bg}; {stretch_text}'
            
            return styles
        
        # Apply styling
        styled_capacity = display_cols_df.style.apply(style_capacity_table, axis=None)
        
        st.dataframe(styled_capacity, use_container_width=False, hide_index=True)
        st.caption("Format: Estimated / Available. Darker blue indicates higher capacity utilization.")
    else:
        st.info("No tasks with estimated hours yet.")
    
    # ========== BURN RATE TABLE ==========
    st.divider()
    st.markdown(f"### Burn Rate by Day in {selected_sprint_display}")
    st.caption("Shows % of total allocated time burned per team member by each day of the sprint")
    
    # Get worklog data for this sprint
    worklog_store = get_worklog_store()
    all_worklogs = worklog_store.get_worklogs_with_task_info()
    
    if not all_worklogs.empty and selected_sprint:
        # Get sprint date range
        sprint_start = pd.to_datetime(selected_sprint['SprintStartDt']).date()
        sprint_end = pd.to_datetime(selected_sprint['SprintEndDt']).date()
        all_sprint_dates = pd.date_range(start=sprint_start, end=sprint_end).date.tolist()
        
        # Filter worklogs to this sprint's date range
        all_worklogs['LogDate'] = pd.to_datetime(all_worklogs['LogDate'])
        sprint_worklogs = all_worklogs[
            (all_worklogs['LogDate'].dt.date >= sprint_start) &
            (all_worklogs['LogDate'].dt.date <= sprint_end)
        ].copy()
        
        if not sprint_worklogs.empty:
            # Create burn rate table
            sprint_worklogs['Date'] = sprint_worklogs['LogDate'].dt.date
            
            # Use Owner_Display if available (name-mapped), otherwise Owner
            owner_col = 'Owner_Display' if 'Owner_Display' in sprint_worklogs.columns else 'Owner'
            
            # Get unique team members from worklogs
            worklog_users = sorted(sprint_worklogs[owner_col].dropna().unique().tolist())
            
            # Get hours logged per user per day
            hours_by_day = sprint_worklogs.groupby([owner_col, 'Date'])['MinutesSpent'].sum().reset_index()
            hours_by_day['Hours'] = hours_by_day['MinutesSpent'] / 60
            
            # Create pivot table: users as rows, dates as columns
            hours_pivot = hours_by_day.pivot_table(
                index=owner_col,
                columns='Date',
                values='Hours',
                aggfunc='sum',
                fill_value=0
            )
            
            # Reindex columns to include all sprint dates
            hours_pivot = hours_pivot.reindex(columns=all_sprint_dates, fill_value=0)
            
            # Calculate cumulative hours per day
            hours_pivot = hours_pivot.cumsum(axis=1)
            
            # Get total allocated hours per team member from Team Availability (Admin Config)
            # Default to 80 hours if not configured
            availability_key = f"team_availability_{selected_sprint_num}"
            total_allocated = {}
            if availability_key in st.session_state:
                avail_df = st.session_state[availability_key]
                if 'Team Member' in avail_df.columns and 'Total Hrs Available' in avail_df.columns:
                    total_allocated = dict(zip(avail_df['Team Member'], avail_df['Total Hrs Available']))
            
            # Fallback: use 80 hours for any member not in availability config
            for member in hours_pivot.index:
                if member not in total_allocated:
                    total_allocated[member] = 80
            
            # Convert to burn rate percentage
            burn_rate_df = hours_pivot.copy()
            for member in burn_rate_df.index:
                allocated = total_allocated.get(member, 80)  # Default to 80 if not found
                if allocated > 0:
                    burn_rate_df.loc[member] = (burn_rate_df.loc[member] / allocated * 100).round(1)
                else:
                    burn_rate_df.loc[member] = 0
            
            # Track weekend columns (Saturday=5, Sunday=6)
            weekend_cols = set()
            for d in burn_rate_df.columns:
                if hasattr(d, 'weekday') and d.weekday() in (5, 6):
                    weekend_cols.add(d.strftime('%m/%d'))
            
            # Format column headers as MM/DD
            burn_rate_df.columns = [d.strftime('%m/%d') if hasattr(d, 'strftime') else str(d) for d in burn_rate_df.columns]
            
            # Get date columns before reset_index
            date_cols = list(burn_rate_df.columns)
            
            # Reset index to make Team Member a column
            burn_rate_df = burn_rate_df.reset_index()
            # Rename the index column (could be 'Owner' or 'Owner_Display') to 'Team Member'
            burn_rate_df = burn_rate_df.rename(columns={burn_rate_df.columns[0]: 'Team Member'})
            
            # Ensure date columns are numeric
            for col in date_cols:
                if col in burn_rate_df.columns:
                    burn_rate_df[col] = pd.to_numeric(burn_rate_df[col], errors='coerce').fillna(0)
            
            # Style function for burn rate heat map
            def style_burn_rate(df):
                styles = pd.DataFrame('', index=df.index, columns=df.columns)
                
                for col in df.columns:
                    if col == 'Team Member':
                        continue
                    
                    # Check if this is a weekend column
                    is_weekend = col in weekend_cols
                    
                    for idx in df.index:
                        if is_weekend:
                            # Weekend columns get gray background
                            styles.loc[idx, col] = 'background-color: #e0e0e0; color: #666666'
                        else:
                            try:
                                val = float(df.loc[idx, col])
                            except (ValueError, TypeError):
                                continue
                            if val >= 100:
                                # 100%+ = dark green (completed)
                                styles.loc[idx, col] = 'background-color: #28a745; color: white'
                            elif val >= 75:
                                # 75-99% = medium green
                                styles.loc[idx, col] = 'background-color: #5cb85c; color: white'
                            elif val >= 50:
                                # 50-74% = light green
                                styles.loc[idx, col] = 'background-color: #8fd19e'
                            elif val >= 25:
                                # 25-49% = yellow-green
                                styles.loc[idx, col] = 'background-color: #d4edda'
                            elif val > 0:
                                # 1-24% = very light
                                styles.loc[idx, col] = 'background-color: #f0fff0'
                            # 0% = no style (default white)
                
                return styles
            
            # Display styled burn rate table
            styled_burn = burn_rate_df.style.apply(style_burn_rate, axis=None).format(
                {col: '{:.1f}%' for col in date_cols if col in burn_rate_df.columns}
            )
            
            st.dataframe(styled_burn, use_container_width=False, hide_index=True)
            st.caption("📊 Shows cumulative % of allocated hours burned by each day. Green = on track, darker = more complete.")
        else:
            st.info("No worklog data available for this sprint period.")
    else:
        st.info("No worklog data available to calculate burn rate.")
    
else:
    st.info("No tasks match the current filters")
