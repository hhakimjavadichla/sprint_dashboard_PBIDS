"""
Work Backlogs Page
All open tasks appear here. Admin assigns/re-assigns them to sprints.
SprintsAssigned column tracks all sprint assignments for each task.
"""
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from modules.task_store import get_task_store
from modules.sprint_calendar import get_sprint_calendar
from components.auth import require_admin, display_user_info
from utils.grid_styles import apply_grid_styles, get_custom_css, STATUS_CELL_STYLE, DAYS_OPEN_CELL_STYLE

st.set_page_config(
    page_title="Work Backlogs",
    page_icon="📋",
    layout="wide"
)

# Apply custom styles
apply_grid_styles()

# Require admin access
if not require_admin():
    st.stop()

# Display user info
display_user_info()

st.title("📋 Work Backlogs")
st.markdown("""
All **open tasks** appear here. As admin, you can:
- Assign tasks to sprints (tasks can be assigned to multiple sprints over time)
- Track sprint assignment history in the **Sprints Assigned** column
- Completed tasks are automatically removed from this view
""")

# Get task store and sprint calendar
task_store = get_task_store()
calendar = get_sprint_calendar()

# Get backlog tasks (all open tasks)
backlog_tasks = task_store.get_backlog_tasks()

# Get available sprints for assignment
all_sprints = calendar.get_all_sprints()
current_sprint = calendar.get_current_sprint()

# Display backlog stats
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📋 Open Tasks", len(backlog_tasks) if not backlog_tasks.empty else 0)
with col2:
    if current_sprint:
        st.metric("🎯 Current Sprint", f"Sprint {current_sprint['SprintNumber']}")
    else:
        st.metric("🎯 Current Sprint", "None")
with col3:
    # Count unassigned tasks (no sprints assigned yet)
    if not backlog_tasks.empty and 'SprintsAssigned' in backlog_tasks.columns:
        unassigned = len(backlog_tasks[backlog_tasks['SprintsAssigned'].fillna('') == ''])
        st.metric("⏳ Unassigned", unassigned)
    else:
        st.metric("⏳ Unassigned", 0)
with col4:
    if not backlog_tasks.empty and 'Section' in backlog_tasks.columns:
        sections = backlog_tasks['Section'].nunique()
        st.metric("📊 Sections", sections)
    else:
        st.metric("📊 Sections", 0)

st.divider()

if backlog_tasks.empty:
    st.info("📭 **No open tasks.** All tasks are completed.")
    st.caption("Upload a new iTrack extract to add tasks to the backlog.")
else:
    # Filter controls
    st.markdown("### 🔍 Filter Backlog")
    
    # Row 1: Standard filters
    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns(5)
    
    with filter_col1:
        sections = ['All'] + sorted(backlog_tasks['Section'].dropna().unique().tolist())
        section_filter = st.selectbox("Section", sections, key="backlog_section_filter")
    
    with filter_col2:
        statuses = ['All'] + sorted(backlog_tasks['Status'].dropna().unique().tolist())
        status_filter = st.selectbox("Status", statuses, key="backlog_status_filter")
    
    with filter_col3:
        ticket_types = ['All'] + sorted(backlog_tasks['TicketType'].dropna().unique().tolist())
        type_filter = st.selectbox("TicketType", ticket_types, key="backlog_type_filter")
    
    with filter_col4:
        assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in backlog_tasks.columns else 'AssignedTo'
        assignees = ['All'] + sorted(backlog_tasks[assignee_col].dropna().unique().tolist())
        assignee_filter = st.selectbox("AssignedTo", assignees, key="backlog_assignee_filter")
    
    with filter_col5:
        # Filter by assignment status
        assignment_options = ['All', 'Unassigned', 'Assigned']
        assignment_filter = st.selectbox("Assignment", assignment_options, key="backlog_assignment_filter")
    
    # Row 2: Numeric filters
    filter_col6, filter_col7 = st.columns(2)
    
    # Calculate DaysCreated from TicketCreatedDt
    if 'TicketCreatedDt' in backlog_tasks.columns:
        from datetime import datetime
        backlog_tasks['DaysCreated'] = (datetime.now() - pd.to_datetime(backlog_tasks['TicketCreatedDt'], errors='coerce')).dt.days
    
    with filter_col6:
        # DaysOpen filter - dropdown with "more than" values
        days_options = ['All', 0, 1, 3, 5, 7, 14, 21, 30, 60, 90]
        days_open_min = st.selectbox("DaysOpen (Task) More Than", days_options, key="backlog_days_open_filter")
    
    with filter_col7:
        # DaysCreated filter - dropdown with "more than" values
        days_created_min = st.selectbox("DaysCreated (Ticket) More Than", days_options, key="backlog_days_created_filter")
    
    # Row 3: Column visibility
    all_columns = ['SprintsAssigned', 'TicketNum', 'TicketType', 'Section', 'TaskNum', 'Status', 
                   'AssignedTo', 'CustomerName', 'Subject', 'DaysOpen', 'DaysCreated', 'TicketCreatedDt', 'TaskCreatedDt']
    default_visible = ['SprintsAssigned', 'TicketNum', 'TicketType', 'Section', 'TaskNum', 'Status', 
                       'AssignedTo', 'CustomerName', 'Subject', 'DaysOpen', 'DaysCreated', 'TicketCreatedDt', 'TaskCreatedDt']
    visible_columns = st.multiselect("Visible Columns", all_columns, default=default_visible, key="backlog_visible_cols")
    
    # Apply filters
    display_tasks = backlog_tasks.copy()
    
    if section_filter != 'All':
        display_tasks = display_tasks[display_tasks['Section'] == section_filter]
    if status_filter != 'All':
        display_tasks = display_tasks[display_tasks['Status'] == status_filter]
    if type_filter != 'All':
        display_tasks = display_tasks[display_tasks['TicketType'] == type_filter]
    if assignee_filter != 'All':
        display_tasks = display_tasks[display_tasks[assignee_col] == assignee_filter]
    if assignment_filter == 'Unassigned':
        display_tasks = display_tasks[display_tasks['SprintsAssigned'].fillna('') == '']
    elif assignment_filter == 'Assigned':
        display_tasks = display_tasks[display_tasks['SprintsAssigned'].fillna('') != '']
    
    # Apply DaysOpen filter (more than selected value)
    if days_open_min != 'All' and 'DaysOpen' in display_tasks.columns:
        display_tasks = display_tasks[display_tasks['DaysOpen'].fillna(0) > days_open_min]
    
    # Apply DaysCreated filter (more than selected value)
    if days_created_min != 'All' and 'DaysCreated' in display_tasks.columns:
        display_tasks = display_tasks[display_tasks['DaysCreated'].fillna(0) > days_created_min]
    
    st.caption(f"Showing {len(display_tasks)} of {len(backlog_tasks)} open tasks")
    
    st.divider()
    
    # Sprint assignment section
    st.markdown("### 📤 Assign Tasks to Sprint")
    
    # Sprint selector
    if not all_sprints.empty:
        sprint_options = sorted(all_sprints['SprintNumber'].unique().tolist(), reverse=True)
        
        assign_col1, assign_col2 = st.columns([1, 3])
        with assign_col1:
            target_sprint = st.selectbox(
                "Target Sprint",
                sprint_options,
                index=0 if current_sprint is None else sprint_options.index(current_sprint['SprintNumber']) if current_sprint['SprintNumber'] in sprint_options else 0,
                key="target_sprint_select"
            )
        with assign_col2:
            sprint_info = calendar.get_sprint_by_number(target_sprint)
            if sprint_info:
                st.info(f"📅 Sprint {target_sprint}: {sprint_info['SprintStartDt'].strftime('%m/%d/%Y')} - {sprint_info['SprintEndDt'].strftime('%m/%d/%Y')}")
    else:
        st.warning("No sprints available. Please set up sprint calendar first.")
        target_sprint = None
    
    st.divider()
    
    # Prepare display dataframe
    display_cols = [
        'UniqueTaskId', 'SprintsAssigned', 'OriginalSprintNumber', 'TicketNum', 'TicketType', 'Section', 'TaskNum',
        'Status', 'AssignedTo', 'CustomerName', 'Subject', 'DaysOpen', 'DaysCreated',
        'TicketCreatedDt', 'TaskCreatedDt'
    ]
    
    # Use display name if available
    if 'AssignedTo_Display' in display_tasks.columns:
        display_tasks['AssignedTo'] = display_tasks['AssignedTo_Display']
    
    available_cols = [col for col in display_cols if col in display_tasks.columns]
    grid_df = display_tasks[available_cols].copy()
    
    # Configure AgGrid with row selection
    gb = GridOptionsBuilder.from_dataframe(grid_df)
    gb.configure_default_column(resizable=True, filterable=True, sortable=True)
    
    # Configure checkbox selection on first visible column
    gb.configure_selection(
        selection_mode='multiple',
        use_checkbox=True,
        header_checkbox=True,
        pre_selected_rows=[]
    )
    
    # Configure first column with checkbox
    gb.configure_column(
        'SprintsAssigned', 
        header_name='Sprints Assigned', 
        width=130,
        checkboxSelection=True,
        headerCheckboxSelection=True
    )
    
    gb.configure_column('UniqueTaskId', hide=True)
    gb.configure_column('OriginalSprintNumber', header_name='Created Sprint', width=110, hide=True)
    gb.configure_column('TicketNum', header_name='TicketNum', width=100, hide='TicketNum' not in visible_columns)
    gb.configure_column('TicketType', header_name='TicketType', width=80, hide='TicketType' not in visible_columns)
    gb.configure_column('Section', header_name='Section', width=100, hide='Section' not in visible_columns)
    gb.configure_column('TaskNum', header_name='TaskNum', width=90, hide='TaskNum' not in visible_columns)
    gb.configure_column('Status', header_name='Status', width=90, cellStyle=STATUS_CELL_STYLE, hide='Status' not in visible_columns)
    gb.configure_column('AssignedTo', header_name='AssignedTo', width=120, hide='AssignedTo' not in visible_columns)
    gb.configure_column('CustomerName', header_name='CustomerName', width=120, hide='CustomerName' not in visible_columns)
    gb.configure_column('Subject', header_name='Subject', width=250, tooltipField='Subject', hide='Subject' not in visible_columns)
    gb.configure_column('DaysOpen', header_name='DaysOpen', width=90, cellStyle=DAYS_OPEN_CELL_STYLE, hide='DaysOpen' not in visible_columns)
    gb.configure_column('DaysCreated', header_name='DaysCreated', width=100, hide='DaysCreated' not in visible_columns)
    gb.configure_column('TicketCreatedDt', header_name='TicketCreatedDt', width=115, hide='TicketCreatedDt' not in visible_columns)
    gb.configure_column('TaskCreatedDt', header_name='TaskCreatedDt', width=110, hide='TaskCreatedDt' not in visible_columns)
    
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=50)
    
    grid_options = gb.build()
    
    st.markdown("### 📋 Select Tasks to Assign")
    st.caption("Click checkbox to select tasks. Tasks can be assigned to multiple sprints over time.")
    
    grid_response = AgGrid(
        grid_df,
        gridOptions=grid_options,
        height=500,
        theme='streamlit',
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        custom_css=get_custom_css()
    )
    
    selected_rows = grid_response['selected_rows']
    
    # Convert to DataFrame if it's a list
    if isinstance(selected_rows, list):
        selected_df = pd.DataFrame(selected_rows) if selected_rows else pd.DataFrame()
    else:
        selected_df = selected_rows if selected_rows is not None else pd.DataFrame()
    
    st.divider()
    
    # Assignment action
    if selected_df.empty or len(selected_df) == 0:
        st.info("👆 Select one or more tasks from the table above to assign to a sprint.")
    else:
        num_selected = len(selected_df)
        st.success(f"✅ **{num_selected} task(s) selected**")
        
        # Show selected tasks summary
        with st.expander(f"📋 View Selected Tasks ({num_selected})", expanded=False):
            for idx, row in selected_df.iterrows():
                st.write(f"• **{row.get('TaskNum', 'N/A')}** | {row.get('Status', 'N/A')} | {row.get('AssignedTo', 'N/A')} | {str(row.get('Subject', ''))[:50]}...")
        
        # Assign button
        if target_sprint is not None:
            if st.button(f"📤 Assign {num_selected} Task(s) to Sprint {target_sprint}", type="primary"):
                # Get UniqueTaskIds from selected rows
                task_ids = selected_df['UniqueTaskId'].tolist()
                
                # Assign tasks (returns assigned_count, skipped_count, errors)
                assigned, skipped, errors = task_store.assign_tasks_to_sprint(task_ids, target_sprint)
                
                if assigned > 0:
                    st.success(f"✅ Added Sprint {target_sprint} to {assigned} task(s)")
                    if skipped > 0:
                        st.warning(f"⚠️ {skipped} task(s) skipped:")
                        with st.expander("View details"):
                            for err in errors:
                                st.write(f"• {err}")
                    st.balloons()
                    st.rerun()
                elif skipped > 0:
                    st.error(f"❌ All {skipped} task(s) were skipped:")
                    for err in errors:
                        st.write(f"• {err}")
                else:
                    st.error("❌ Failed to assign tasks. Please try again.")
        else:
            st.warning("Please select a target sprint to assign tasks.")

# Footer
st.divider()
st.caption("💡 **Tip:** Open tasks stay in the backlog until completed. Assign them to sprints as needed - the Sprints Assigned column tracks all assignments.")
