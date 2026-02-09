"""
Sprint Overview Page
Quick overview for lab users to check all items in a Sprint
Shows tickets/tasks metrics, completion metrics, and full task list
"""
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from st_aggrid.shared import JsCode
from modules.task_store import get_task_store, CLOSED_STATUSES
from modules.section_filter import filter_by_section
from modules.sprint_calendar import get_sprint_calendar, format_sprint_display
from datetime import datetime
from components.auth import require_auth, display_user_info, get_user_role, get_user_section, is_admin, is_pbids_user
from utils.exporters import export_to_excel
from utils.grid_styles import apply_grid_styles, get_custom_css, COLUMN_WIDTHS, display_column_help, get_backlog_column_order, clean_subject_column

# Apply custom tooltip styles
apply_grid_styles()

st.title("Sprint Overview")
st.caption("_Quick overview of all items in a Sprint_")

# Require authentication
require_auth("Sprint Overview")

# Display user info
display_user_info()

# Get sprint calendar
calendar = get_sprint_calendar()
all_sprints = calendar.get_all_sprints()

if all_sprints.empty:
    st.warning("⚠️ No sprints defined in the calendar")
    st.stop()

# Get current sprint
current_sprint = calendar.get_current_sprint()
current_sprint_num = current_sprint['SprintNumber'] if current_sprint else None

# ===== FILTERS =====
st.markdown("### Filters")

col_sprint, col_section = st.columns(2)

# Sprint selection dropdown
with col_sprint:
    # Create sprint options with display format
    sprint_options = []
    sprint_map = {}  # Map display string to sprint number
    
    for _, row in all_sprints.iterrows():
        sprint_num = int(row['SprintNumber'])
        sprint_display = format_sprint_display(
            row['SprintName'], 
            row['SprintStartDt'], 
            row['SprintEndDt'], 
            sprint_num
        )
        # Mark current sprint
        if sprint_num == current_sprint_num:
            sprint_display = f"📍 {sprint_display} (Current)"
        sprint_options.append(sprint_display)
        sprint_map[sprint_display] = sprint_num
    
    # Default to current sprint
    default_idx = 0
    if current_sprint_num:
        for i, opt in enumerate(sprint_options):
            if sprint_map[opt] == current_sprint_num:
                default_idx = i
                break
    
    selected_sprint_display = st.selectbox(
        "Select Sprint",
        sprint_options,
        index=default_idx,
        help="Choose a sprint to view"
    )
    selected_sprint_num = sprint_map[selected_sprint_display]

# Get user's section for filtering
user_role = get_user_role()
user_section_raw = get_user_section()

# Parse user sections (may be comma-separated for multi-section users)
user_sections = []
if user_section_raw:
    user_sections = [s.strip() for s in user_section_raw.split(',') if s.strip()]

# Section filter
with col_section:
    # Load task store to get available sections
    task_store = get_task_store()
    sprint_df = task_store.get_sprint_tasks(selected_sprint_num)
    
    if sprint_df is not None and not sprint_df.empty:
        all_sections = sorted(sprint_df['Section'].dropna().unique().tolist())
    else:
        all_sections = []
    
    # Determine available sections based on user role
    if is_admin() or is_pbids_user():
        # Admin and PIBIDS Users can see all sections
        available_sections = ['All Sections'] + all_sections
        default_section_idx = 0
    else:
        # Section users can only see their assigned sections
        if user_sections:
            available_sections = ['All My Sections'] + [s for s in user_sections if s in all_sections]
        else:
            available_sections = ['All Sections']
        default_section_idx = 0
    
    selected_section = st.selectbox(
        "Filter by Section",
        available_sections,
        index=default_section_idx,
        help="Filter tasks by lab section"
    )

st.divider()

# ===== LOAD SPRINT DATA =====
if sprint_df is None or sprint_df.empty:
    st.warning(f"⚠️ No tasks found for Sprint {selected_sprint_num}")
    st.info("No tasks have been assigned to this sprint yet.")
    st.stop()

# Apply section filter
if selected_section not in ['All Sections', 'All My Sections']:
    sprint_df = filter_by_section(sprint_df, selected_section)
    display_sections = [selected_section]
elif selected_section == 'All My Sections' and user_sections:
    sprint_df = sprint_df[sprint_df['Section'].isin(user_sections)].copy()
    display_sections = user_sections
else:
    display_sections = all_sections

if sprint_df.empty:
    st.warning(f"⚠️ No tasks found for the selected section(s)")
    st.stop()

# ===== METRICS SECTION =====
st.markdown("### Sprint Metrics")

# Count tasks by type
if 'TicketType' in sprint_df.columns:
    task_counts = sprint_df['TicketType'].value_counts().to_dict()
    
    # Count unique tickets by type
    ticket_counts = {}
    if 'TicketNum' in sprint_df.columns:
        for ticket_type in ['SR', 'PR', 'IR', 'NC', 'AD']:
            ticket_counts[ticket_type] = sprint_df[sprint_df['TicketType'] == ticket_type]['TicketNum'].nunique()
        total_tickets = sprint_df['TicketNum'].nunique()
    else:
        ticket_counts = task_counts.copy()
        total_tickets = len(sprint_df)
    
    # Ticket type labels
    type_labels = {
        'SR': 'SR (Service Request)',
        'PR': 'PR (Project Request)',
        'IR': 'IR (Incident Request)',
        'NC': 'NC (Non-classified IS Requests)',
        'AD': 'AD (Admin Request)'
    }
    
    # Row 1: Tickets by category
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Total Sprint Tickets", total_tickets)
    with col2:
        st.metric("SR", ticket_counts.get('SR', 0), help=type_labels['SR'])
    with col3:
        st.metric("PR", ticket_counts.get('PR', 0), help=type_labels['PR'])
    with col4:
        st.metric("IR", ticket_counts.get('IR', 0), help=type_labels['IR'])
    with col5:
        st.metric("NC", ticket_counts.get('NC', 0), help=type_labels['NC'])
    with col6:
        st.metric("AD", ticket_counts.get('AD', 0), help=type_labels['AD'])
    
    # Row 2: Tasks by category
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Total Sprint Tasks", len(sprint_df))
    with col2:
        st.metric("SR", task_counts.get('SR', 0), help=type_labels['SR'])
    with col3:
        st.metric("PR", task_counts.get('PR', 0), help=type_labels['PR'])
    with col4:
        st.metric("IR", task_counts.get('IR', 0), help=type_labels['IR'])
    with col5:
        st.metric("NC", task_counts.get('NC', 0), help=type_labels['NC'])
    with col6:
        st.metric("AD", task_counts.get('AD', 0), help=type_labels['AD'])

st.caption(f"Showing {len(sprint_df)} tasks")

st.divider()

# ===== COMPLETION METRICS =====
st.markdown("### Completion Metrics")

# Determine task status
status_col = 'TaskStatus' if 'TaskStatus' in sprint_df.columns else 'Status'

# Categorize tasks by GoalType
if 'GoalType' not in sprint_df.columns:
    sprint_df['GoalType'] = ''

# Define status categories
completed_statuses = list(CLOSED_STATUSES)

# Calculate metrics for Mandatory and Stretch tasks (assigned to this sprint)
def get_completion_metrics(df, goal_type_filter):
    """Calculate completion metrics for a subset of tasks"""
    subset = df[df['GoalType'] == goal_type_filter]
    total = len(subset)
    
    if status_col in subset.columns:
        completed = len(subset[subset[status_col].isin(completed_statuses)])
        in_progress = total - completed
    else:
        in_progress = 0
        completed = 0
    
    return total, in_progress, completed

# Calculate metrics for Mandatory and Stretch
mandatory_total, mandatory_in_progress, mandatory_completed = get_completion_metrics(sprint_df, 'Mandatory')
stretch_total, stretch_in_progress, stretch_completed = get_completion_metrics(sprint_df, 'Stretch')

# Non-Assigned Tasks: tasks NOT assigned to this sprint but completed DURING the sprint dates
non_assigned_completed = 0

# Get sprint date range
sprint_info = calendar.get_sprint_by_number(selected_sprint_num)

if sprint_info:
    sprint_start = pd.to_datetime(sprint_info['SprintStartDt'])
    sprint_end = pd.to_datetime(sprint_info['SprintEndDt'])
    
    # Get all tasks from task store
    all_tasks_df = task_store.tasks_df.copy() if hasattr(task_store, 'tasks_df') else pd.DataFrame()
    
    if not all_tasks_df.empty:
        # Apply section filter to all tasks
        if selected_section not in ['All Sections', 'All My Sections']:
            all_tasks_df = filter_by_section(all_tasks_df, selected_section)
        elif selected_section == 'All My Sections' and user_sections:
            all_tasks_df = all_tasks_df[all_tasks_df['Section'].isin(user_sections)].copy()
        
        # Helper to check if task is NOT assigned to the selected sprint
        def not_in_sprint(sprints_str):
            if pd.isna(sprints_str) or str(sprints_str).strip() == '':
                return True
            try:
                sprint_list = [int(s.strip()) for s in str(sprints_str).split(',') if s.strip()]
                return selected_sprint_num not in sprint_list
            except:
                return True
        
        if 'SprintsAssigned' in all_tasks_df.columns and 'TaskResolvedDt' in all_tasks_df.columns:
            # Parse resolved date
            all_tasks_df['TaskResolvedDt'] = pd.to_datetime(all_tasks_df['TaskResolvedDt'], errors='coerce')
            
            # Tasks NOT assigned to the selected sprint
            non_assigned_tasks = all_tasks_df[all_tasks_df['SprintsAssigned'].apply(not_in_sprint)]
            
            # Count completed ones during sprint dates
            non_assigned_completed = len(non_assigned_tasks[
                (non_assigned_tasks['TaskResolvedDt'] >= sprint_start) &
                (non_assigned_tasks['TaskResolvedDt'] <= sprint_end)
            ])

# Create completion metrics table
def format_with_percent(count, total):
    """Format count with percentage"""
    if total == 0:
        return "0"
    pct = (count / total * 100)
    return f"{count} ({pct:.0f}%)"

completion_data = {
    'Task Type': ['Mandatory Tasks', 'Stretch Tasks', 'Non-Assigned Tasks'],
    'Total Assigned': [str(mandatory_total), str(stretch_total), 'NA'],
    'In Progress': [
        format_with_percent(mandatory_in_progress, mandatory_total) if mandatory_total > 0 else '0',
        format_with_percent(stretch_in_progress, stretch_total) if stretch_total > 0 else '0',
        'NA'
    ],
    'Completed': [
        format_with_percent(mandatory_completed, mandatory_total) if mandatory_total > 0 else '0',
        format_with_percent(stretch_completed, stretch_total) if stretch_total > 0 else '0',
        str(non_assigned_completed)
    ]
}

completion_df = pd.DataFrame(completion_data)

st.dataframe(
    completion_df,
    width='content',
    hide_index=True,
    column_config={
        'Task Type': st.column_config.TextColumn('Task Type', width=150),
        'Total Assigned': st.column_config.TextColumn('Total Assigned', width=120),
        'In Progress': st.column_config.TextColumn('In Progress', width=120),
        'Completed': st.column_config.TextColumn('Completed', width=120)
    }
)

st.divider()

# ===== TASK TABLE =====
st.markdown("### Sprint Tasks")
st.caption("💡 All tasks assigned to this sprint (including in progress and completed items)")

# Column descriptions help
display_column_help(title="❓ Column Descriptions")

# Add ticket grouping for row banding
filtered_df = sprint_df.copy()

if 'TicketNum' in filtered_df.columns:
    # Count tasks per ticket
    ticket_counts_for_grouping = filtered_df.groupby('TicketNum').size().to_dict()
    
    # Sort by TicketNum to group tasks from same ticket together
    filtered_df = filtered_df.sort_values(
        by=['TicketNum', 'TaskNum'],
        ascending=[True, True],
        na_position='last'
    ).reset_index(drop=True)
    
    # Add TaskCount column (ratio format: "1/3", "2/3", "3/3") and track ticket groups for row banding
    task_counts = []
    ticket_group_ids = []
    current_group = 0
    prev_ticket = None
    task_index_in_ticket = {}
    
    for idx, row in filtered_df.iterrows():
        ticket = row['TicketNum']
        if ticket != prev_ticket:
            current_group += 1
            prev_ticket = ticket
            task_index_in_ticket[ticket] = 0
        
        task_index_in_ticket[ticket] += 1
        total_tasks = ticket_counts_for_grouping.get(ticket, 1)
        task_counts.append(f"{task_index_in_ticket[ticket]}/{total_tasks}")
        ticket_group_ids.append(current_group)
    
    filtered_df['TaskCount'] = task_counts
    filtered_df['_TicketGroup'] = ticket_group_ids
    filtered_df['_IsMultiTask'] = filtered_df['TicketNum'].map(lambda x: ticket_counts_for_grouping.get(x, 1) > 1)

if not filtered_df.empty:
    # Use display names if available
    sv_assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in filtered_df.columns else 'AssignedTo'
    
    # Use standardized column order from config
    display_order = get_backlog_column_order(sv_assignee_col)
    
    available_cols = [col for col in display_order if col in filtered_df.columns]
    display_df = filtered_df[available_cols].copy()
    
    # Clean subject column (remove LAB-XX: NNNNNN - prefix)
    display_df = clean_subject_column(display_df)
    
    # Define column view presets
    COLUMN_VIEWS = {
        'All Columns': None,
        'Status Tracking': ['TicketNum', 'TaskNum', 'Subject', sv_assignee_col, 'TaskStatus',
                            'GoalType', 'DaysOpen', 'TaskOrigin', 'SprintsAssigned'],
        'Priority & Dependencies': ['TicketNum', 'TaskNum', 'Subject', sv_assignee_col,
                                     'CustomerPriority', 'FinalPriority', 'GoalType',
                                     'DependencyOn', 'DependenciesLead', 'DependencySecured', 'Comments'],
        'Hours & Effort': ['TicketNum', 'TaskNum', 'Subject', sv_assignee_col, 'Section',
                           'GoalType', 'HoursEstimated', 'TaskHoursSpent', 'TicketHoursSpent'],
    }
    
    selected_view = st.radio(
        "Column View: Select a preset to show only relevant columns",
        options=list(COLUMN_VIEWS.keys()),
        horizontal=True,
        key="sprint_overview_view_selector"
    )
    
    view_columns = COLUMN_VIEWS[selected_view]
    
    def should_hide(col_name):
        if view_columns is None:
            return False
        return col_name not in view_columns
    
    # Configure AgGrid with built-in column filtering
    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_default_column(resizable=True, filterable=True, sortable=True)
    
    # Hidden columns
    gb.configure_column('_TicketGroup', hide=True)
    gb.configure_column('_IsMultiTask', hide=True)
    
    # Sprint columns (SprintNumber, SprintName, SprintStartDt, SprintEndDt hidden - redundant with sprint selector)
    gb.configure_column('SprintNumber', hide=True)
    gb.configure_column('SprintName', hide=True)
    gb.configure_column('SprintStartDt', hide=True)
    gb.configure_column('SprintEndDt', hide=True)
    gb.configure_column('TaskOrigin', header_name='TaskOrigin', width=COLUMN_WIDTHS.get('TaskOrigin', 90), hide=should_hide('TaskOrigin'))
    gb.configure_column('SprintsAssigned', header_name='SprintsAssigned', width=COLUMN_WIDTHS.get('SprintsAssigned', 130), hide=should_hide('SprintsAssigned'))
    
    # Ticket/Task columns
    gb.configure_column('TicketNum', header_name='TicketNum', width=COLUMN_WIDTHS['TicketNum'], hide=should_hide('TicketNum'))
    gb.configure_column('TaskCount', header_name='Task#', width=COLUMN_WIDTHS.get('TaskCount', 70), hide=should_hide('TaskCount'))
    gb.configure_column('TicketType', header_name='TicketType', width=COLUMN_WIDTHS['TicketType'], hide=should_hide('TicketType'))
    gb.configure_column('Section', header_name='Section', width=COLUMN_WIDTHS.get('Section', 100), hide=should_hide('Section'))
    gb.configure_column('CustomerName', header_name='CustomerName', width=COLUMN_WIDTHS.get('CustomerName', 120), hide=should_hide('CustomerName'))
    gb.configure_column('TaskNum', header_name='TaskNum', width=COLUMN_WIDTHS['TaskNum'], hide=should_hide('TaskNum'))
    gb.configure_column('TaskStatus', header_name='TaskStatus', width=COLUMN_WIDTHS.get('TaskStatus', 100), hide=should_hide('TaskStatus'))
    gb.configure_column('TicketStatus', header_name='TicketStatus', width=COLUMN_WIDTHS.get('TicketStatus', 100), hide=should_hide('TicketStatus'))
    gb.configure_column(sv_assignee_col, header_name='AssignedTo', width=COLUMN_WIDTHS['AssignedTo'], hide=should_hide(sv_assignee_col))
    gb.configure_column('Subject', header_name='Subject', width=COLUMN_WIDTHS.get('Subject', 200), 
                        tooltipField='Details', hide=should_hide('Subject'))
    gb.configure_column('Details', hide=True)  # Hidden - only used for Subject tooltip
    gb.configure_column('TicketCreatedDt', header_name='TicketCreatedDt', width=COLUMN_WIDTHS.get('TicketCreatedDt', 110), hide=should_hide('TicketCreatedDt'))
    gb.configure_column('TaskCreatedDt', header_name='TaskCreatedDt', width=COLUMN_WIDTHS.get('TaskCreatedDt', 110), hide=should_hide('TaskCreatedDt'))
    gb.configure_column('DaysOpen', header_name='DaysOpen', width=COLUMN_WIDTHS['DaysOpen'], hide=should_hide('DaysOpen'))
    
    # Priority and planning columns (read-only in this view)
    gb.configure_column('CustomerPriority', header_name='CustomerPriority', width=COLUMN_WIDTHS['CustomerPriority'], hide=should_hide('CustomerPriority'))
    gb.configure_column('FinalPriority', header_name='FinalPriority', width=COLUMN_WIDTHS.get('FinalPriority', 100), hide=should_hide('FinalPriority'))
    gb.configure_column('GoalType', header_name='GoalType', width=COLUMN_WIDTHS.get('GoalType', 90), hide=should_hide('GoalType'))
    gb.configure_column('DependencyOn', header_name='Dependency', width=COLUMN_WIDTHS.get('DependencyOn', 110), hide=should_hide('DependencyOn'))
    gb.configure_column('DependenciesLead', header_name='DependencyLead(s)', width=COLUMN_WIDTHS.get('DependenciesLead', 120),
                        tooltipField='DependenciesLead', hide=should_hide('DependenciesLead'))
    gb.configure_column('DependencySecured', header_name='DependencySecured', width=COLUMN_WIDTHS.get('DependencySecured', 130), hide=should_hide('DependencySecured'))
    gb.configure_column('Comments', header_name='Comments', width=COLUMN_WIDTHS['Comments'], tooltipField='Comments', hide=should_hide('Comments'))
    gb.configure_column('HoursEstimated', header_name='HoursEstimated', width=COLUMN_WIDTHS['HoursEstimated'], hide=should_hide('HoursEstimated'))
    gb.configure_column('TaskHoursSpent', header_name='TaskHoursSpent', width=COLUMN_WIDTHS.get('TaskHoursSpent', 110), hide=should_hide('TaskHoursSpent'))
    gb.configure_column('TicketHoursSpent', header_name='TicketHoursSpent', width=COLUMN_WIDTHS.get('TicketHoursSpent', 120), hide=should_hide('TicketHoursSpent'))
    gb.configure_pagination(enabled=False)
    
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
    grid_options['enableBrowserTooltips'] = False
    
    AgGrid(
        display_df,
        gridOptions=grid_options,
        height=600,
        theme='streamlit',
        update_mode=GridUpdateMode.NO_UPDATE,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False,
        custom_css=get_custom_css(),
        allow_unsafe_jscode=True
    )
    
    # Export section
    st.divider()
    
    col_export1, col_export2 = st.columns([2, 6])
    
    with col_export1:
        # Export current view
        export_df = display_df.copy()
        # Remove internal columns from export
        export_cols = [c for c in export_df.columns if not c.startswith('_')]
        export_df = export_df[export_cols]
        
        excel_data = export_to_excel(export_df, sheet_name="Sprint Overview")
        section_name = "_".join(display_sections).replace(' ', '_') if display_sections else "all"
        section_name = section_name[:50]  # Limit filename length
        filename = f"sprint_{selected_sprint_num}_overview_{section_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        
        st.download_button(
            label=f"📥 Export to Excel ({len(export_df)} tasks)",
            data=excel_data,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Export current view to Excel"
        )
    
    with col_export2:
        st.caption("💡 Use column filters in the table to narrow down data before exporting.")

else:
    st.info("No tasks match the current filters")

# Help section
with st.expander("About This View"):
    section_display = ", ".join(display_sections) if display_sections else "All Sections"
    
    st.markdown(f"""
    **Sprint Overview** provides a quick summary of all items in a selected sprint.
    
    **Current View:** Sprint {selected_sprint_num} · Sections: {section_display}
    
    **Metrics Explained:**
    - **Total Sprint Tickets/Tasks**: Count of unique tickets and tasks in the sprint
    - **By Type**: Breakdown by ticket type (SR, PR, IR, NC, AD)
    
    **Completion Metrics:**
    - **Mandatory Tasks**: Tasks marked as Mandatory goal type
    - **Stretch Tasks**: Tasks marked as Stretch goal type
    - **Non-Assigned Tasks**: Tasks without a goal type assignment
    
    **Task Table:**
    - Shows all tasks in the sprint (open, in progress, and completed)
    - Use column filters to narrow down the view
    - Multi-task tickets are color-coded for easy identification
    """)
