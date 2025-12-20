"""
Sprint View Page
View tasks for any sprint - current sprint shows carryover from all previous sprints
Admin can update task status with date to control task positioning
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from modules.task_store import get_task_store, CLOSED_STATUSES
from modules.sprint_calendar import get_sprint_calendar
from components.auth import require_admin, display_user_info, is_admin
from utils.exporters import export_to_csv, export_to_excel
from utils.grid_styles import apply_grid_styles, get_custom_css, STATUS_CELL_STYLE, PRIORITY_CELL_STYLE, DAYS_OPEN_CELL_STYLE

st.set_page_config(
    page_title="Sprint View (Prototype)",
    page_icon="🧪",
    layout="wide"
)

# Apply custom tooltip styles
apply_grid_styles()

st.title("Sprint View")
st.caption("_Prototype — PBIDS Team_")

# Display user info
display_user_info()

# Load modules
task_store = get_task_store()
calendar = get_sprint_calendar()

# Check if we have tasks
all_tasks = task_store.get_all_tasks()
if all_tasks.empty:
    st.warning("📭 No tasks in the system yet.")
    st.info("Upload tasks first to view sprints.")
    st.page_link("pages/2_📤_Upload_Tasks.py", label="📤 Upload Tasks", icon="📤")
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

# Build sprint options
sprint_options = []
default_idx = 0
for idx, row in all_sprints.iterrows():
    sprint_num = int(row['SprintNumber'])
    label = f"Sprint {sprint_num}: {row['SprintName']} ({row['SprintStartDt'].strftime('%m/%d')} - {row['SprintEndDt'].strftime('%m/%d')})"
    
    # Check if sprint has tasks
    sprint_tasks = task_store.get_sprint_tasks(sprint_num)
    task_count = len(sprint_tasks) if not sprint_tasks.empty else 0
    label += f" [{task_count} tasks]"
    
    sprint_options.append((sprint_num, label))
    if current_sprint and sprint_num == current_sprint['SprintNumber']:
        default_idx = len(sprint_options) - 1

col1, col2 = st.columns([3, 1])

with col1:
    selected_label = st.selectbox(
        "Select Sprint",
        options=[opt[1] for opt in sprint_options],
        index=default_idx
    )

selected_sprint_num = sprint_options[[opt[1] for opt in sprint_options].index(selected_label)][0]
selected_sprint = calendar.get_sprint_by_number(selected_sprint_num)

with col2:
    is_current = current_sprint and selected_sprint_num == current_sprint['SprintNumber']
    if is_current:
        st.success("Current")
    elif selected_sprint['SprintEndDt'] < datetime.now():
        st.caption("Past")
    else:
        st.caption("Upcoming")

# Sprint info bar
st.markdown(f"**{selected_sprint['SprintName']}** — {selected_sprint['SprintStartDt'].strftime('%b %d')} to {selected_sprint['SprintEndDt'].strftime('%b %d, %Y')}")

st.divider()

# Get sprint tasks
sprint_tasks = task_store.get_sprint_tasks(selected_sprint_num)

if sprint_tasks.empty:
    st.info(f"No tasks in Sprint {selected_sprint_num}.")
    st.stop()

# Summary metrics
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Tasks", len(sprint_tasks))

with col2:
    carryover_count = int(sprint_tasks['IsCarryover'].sum()) if 'IsCarryover' in sprint_tasks.columns else 0
    st.metric("Carryover", carryover_count, help="Open tasks from previous sprints")

with col3:
    original_count = len(sprint_tasks) - carryover_count
    st.metric("Original", original_count, help="Tasks assigned to this sprint")

with col4:
    open_count = len(sprint_tasks[~sprint_tasks['Status'].isin(CLOSED_STATUSES)]) if 'Status' in sprint_tasks.columns else len(sprint_tasks)
    st.metric("Open", open_count)

with col5:
    closed_count = len(sprint_tasks) - open_count
    st.metric("Closed", closed_count)

st.divider()

# Tabs
tab1, tab2, tab3 = st.tabs(["All Tasks", "Update Status", "Distribution"])

with tab1:
    # Filters in sidebar
    with st.sidebar:
        st.markdown("**Filters**")
        
        # Status filter
        all_statuses = sprint_tasks['Status'].unique().tolist() if 'Status' in sprint_tasks.columns else []
        status_filter = st.multiselect("Status", options=all_statuses, default=all_statuses)
        
        # Carryover filter
        show_option = st.radio(
            "Show Tasks",
            options=['All', 'Original Only', 'Carryover Only'],
        )
        
        # Assignee filter - use display names
        tab1_assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in sprint_tasks.columns else 'AssignedTo'
        if tab1_assignee_col in sprint_tasks.columns:
            all_assignees = sorted(sprint_tasks[tab1_assignee_col].dropna().unique().tolist())
            assignee_filter = st.multiselect("Assignee", options=all_assignees, default=all_assignees)
        else:
            assignee_filter = []
    
    # Apply filters
    filtered_df = sprint_tasks.copy()
    
    if status_filter:
        filtered_df = filtered_df[filtered_df['Status'].isin(status_filter)]
    
    if show_option == 'Original Only' and 'IsCarryover' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['IsCarryover'] == False]
    elif show_option == 'Carryover Only' and 'IsCarryover' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['IsCarryover'] == True]
    
    if assignee_filter and tab1_assignee_col in filtered_df.columns:
        filtered_df = filtered_df[filtered_df[tab1_assignee_col].isin(assignee_filter)]
    
    st.caption(f"Showing {len(filtered_df)} of {len(sprint_tasks)} tasks")
    
    # Display columns - use display name for assignee
    display_cols = [
        'UniqueTaskId', 'TaskNum', 'Status', tab1_assignee_col, 'Subject',
        'OriginalSprintNumber', 'IsCarryover', 'TaskAssignedDt', 'StatusUpdateDt',
        'TicketType'
    ]
    display_cols = [c for c in display_cols if c in filtered_df.columns]
    
    # Configure grid
    gb = GridOptionsBuilder.from_dataframe(filtered_df[display_cols])
    gb.configure_default_column(resizable=True, filterable=True, sortable=True)
    gb.configure_column('Subject', header_name='Subject', width=180, tooltipField='Subject')
    gb.configure_column('UniqueTaskId', header_name='UniqueTaskId', width=120)
    gb.configure_column('TaskNum', header_name='TaskNum', width=100)
    gb.configure_column('IsCarryover', header_name='IsCarryover', width=100)
    gb.configure_column(tab1_assignee_col, header_name='AssignedTo', width=120)
    gb.configure_column('Status', header_name='Status', width=100, cellStyle=STATUS_CELL_STYLE)
    gb.configure_column('TicketType', header_name='TicketType', width=80)
    gb.configure_column('OriginalSprintNumber', header_name='OriginalSprintNumber', width=140)
    gb.configure_column('TaskAssignedDt', header_name='TaskAssignedDt', width=115)
    gb.configure_column('StatusUpdateDt', header_name='StatusUpdateDt', width=115)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=100)
    
    grid_options = gb.build()
    
    AgGrid(
        filtered_df[display_cols],
        gridOptions=grid_options,
        height=600,
        theme='streamlit',
        fit_columns_on_grid_load=False,
        enable_enterprise_modules=False,
        custom_css=get_custom_css(),
        allow_unsafe_jscode=True
    )
    
    # Export
    col1, col2 = st.columns(2)
    with col1:
        csv_data = export_to_csv(filtered_df)
        st.download_button(
            "📥 Export CSV",
            csv_data,
            f"sprint_{selected_sprint_num}_tasks.csv",
            "text/csv"
        )
    with col2:
        excel_data = export_to_excel(filtered_df)
        st.download_button(
            "📥 Export Excel",
            excel_data,
            f"sprint_{selected_sprint_num}_tasks.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

with tab2:
    st.subheader("✏️ Update Task Status")
    
    # Admin only
    if not is_admin():
        st.warning("⚠️ Admin access required to update tasks")
        st.info("Please log in as admin to update task status.")
    else:
        st.markdown("""
        **Close tasks to prevent carryover:**
        1. Use filters to find tasks
        2. Select one or more tasks from the table (use checkbox)
        3. Choose the new status and **Status Update Date**
        4. Click Update to apply changes
        
        > 💡 **Note:** Status Update Date cannot be before Task Assigned Date. For multiple tasks, the earliest Task Assigned Date will be used as minimum.
        """)
        
        # Only show open tasks for updating
        open_tasks = sprint_tasks[~sprint_tasks['Status'].isin(CLOSED_STATUSES)].copy()
        
        if open_tasks.empty:
            st.success("✅ All tasks in this sprint are already closed.")
        else:
            st.info(f"📝 {len(open_tasks)} open tasks available for status update")
            
            # --- Filtering Section ---
            st.markdown("#### 🔍 Filter Tasks")
            filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
            
            with filter_col1:
                sections = ['All'] + sorted(open_tasks['Section'].dropna().unique().tolist()) if 'Section' in open_tasks.columns else ['All']
                filter_section = st.selectbox("Section", sections, key="update_filter_section")
            
            with filter_col2:
                # Use display names for assignee filter
                assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in open_tasks.columns else 'AssignedTo'
                assignees = ['All'] + sorted(open_tasks[assignee_col].dropna().unique().tolist()) if assignee_col in open_tasks.columns else ['All']
                filter_assignee = st.selectbox("Assigned To", assignees, key="update_filter_assignee")
            
            with filter_col3:
                statuses = ['All'] + sorted(open_tasks['Status'].dropna().unique().tolist()) if 'Status' in open_tasks.columns else ['All']
                filter_status = st.selectbox("Status", statuses, key="update_filter_status")
            
            with filter_col4:
                types = ['All'] + sorted(open_tasks['TicketType'].dropna().unique().tolist()) if 'TicketType' in open_tasks.columns else ['All']
                filter_type = st.selectbox("Ticket Type", types, key="update_filter_type")
            
            search_text = st.text_input("🔎 Search (Task ID, Subject, Ticket#)", placeholder="Type to search...", key="update_search")
            
            # Apply filters
            filtered_tasks = open_tasks.copy()
            
            if filter_section != 'All' and 'Section' in filtered_tasks.columns:
                filtered_tasks = filtered_tasks[filtered_tasks['Section'] == filter_section]
            if filter_assignee != 'All' and assignee_col in filtered_tasks.columns:
                filtered_tasks = filtered_tasks[filtered_tasks[assignee_col] == filter_assignee]
            if filter_status != 'All' and 'Status' in filtered_tasks.columns:
                filtered_tasks = filtered_tasks[filtered_tasks['Status'] == filter_status]
            if filter_type != 'All' and 'TicketType' in filtered_tasks.columns:
                filtered_tasks = filtered_tasks[filtered_tasks['TicketType'] == filter_type]
            
            if search_text:
                search_lower = search_text.lower()
                mask = (
                    filtered_tasks['TaskNum'].astype(str).str.lower().str.contains(search_lower, na=False) |
                    filtered_tasks['Subject'].astype(str).str.lower().str.contains(search_lower, na=False) |
                    filtered_tasks['TicketNum'].astype(str).str.lower().str.contains(search_lower, na=False) |
                    filtered_tasks['UniqueTaskId'].astype(str).str.lower().str.contains(search_lower, na=False)
                )
                filtered_tasks = filtered_tasks[mask]
            
            st.caption(f"Showing {len(filtered_tasks)} of {len(open_tasks)} open tasks")
            
            if filtered_tasks.empty:
                st.warning("No tasks match the current filters. Try adjusting your filters.")
            else:
                # Prepare display dataframe with better formatting
                display_df = filtered_tasks.copy()
                
                # Create Sprint ID column: S10-TaskNum
                display_df['SprintTaskId'] = display_df.apply(
                    lambda r: f"S{int(r['OriginalSprintNumber'])}-{r['TaskNum']}", axis=1
                )
                
                # Format TaskAssignedDt for display
                if 'TaskAssignedDt' in display_df.columns:
                    display_df['AssignedDate'] = pd.to_datetime(display_df['TaskAssignedDt'], errors='coerce').dt.strftime('%Y-%m-%d')
                else:
                    display_df['AssignedDate'] = 'N/A'
                
                # Use display name column if available
                assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in display_df.columns else 'AssignedTo'
                
                # Columns to display in grid
                grid_cols = ['SprintTaskId', 'Status', assignee_col, 'Section', 'TicketType', 
                            'AssignedDate', 'DaysOpen', 'Subject', 'UniqueTaskId']
                available_grid_cols = [c for c in grid_cols if c in display_df.columns]
                grid_df = display_df[available_grid_cols].copy()
                
                # Configure AgGrid with row selection
                gb = GridOptionsBuilder.from_dataframe(grid_df)
                gb.configure_default_column(filterable=True, sortable=True, resizable=True)
                gb.configure_selection(
                    selection_mode='multiple',
                    use_checkbox=True,
                    header_checkbox=True
                )
                gb.configure_column('SprintTaskId', header_name='SprintTaskId', width=120, pinned='left')
                gb.configure_column('Status', header_name='Status', width=100, cellStyle=STATUS_CELL_STYLE)
                gb.configure_column(assignee_col, header_name='AssignedTo', width=120)
                gb.configure_column('Section', header_name='Section', width=100)
                gb.configure_column('TicketType', header_name='TicketType', width=80)
                gb.configure_column('AssignedDate', header_name='AssignedDate', width=110)
                gb.configure_column('DaysOpen', header_name='DaysOpen', width=90, cellStyle=DAYS_OPEN_CELL_STYLE)
                gb.configure_column('Subject', header_name='Subject', width=180, tooltipField='Subject')
                gb.configure_column('UniqueTaskId', hide=True)  # Hidden but needed for reference
                
                grid_options = gb.build()
                
                st.markdown("#### 📋 Select Tasks to Update")
                st.caption("Click checkbox to select tasks. Use header checkbox to select all.")
                
                grid_response = AgGrid(
                    grid_df,
                    gridOptions=grid_options,
                    height=350,
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
                
                st.markdown("---")
                
                if selected_df.empty or len(selected_df) == 0:
                    st.info("👆 Select one or more tasks from the table above to update their status.")
                else:
                    num_selected = len(selected_df)
                    st.success(f"✅ **{num_selected} task(s) selected**")
                    
                    # Show selected tasks summary
                    with st.expander(f"📋 View Selected Tasks ({num_selected})", expanded=False):
                        for idx, row in selected_df.iterrows():
                            st.write(f"• **{row.get('SprintTaskId', 'N/A')}** | {row.get('Status', 'N/A')} | {row.get('AssignedTo', 'N/A')} | {str(row.get('Subject', ''))[:50]}")
                    
                    # Get earliest task assigned date from selected tasks
                    selected_unique_ids = selected_df['UniqueTaskId'].tolist()
                    selected_full_data = filtered_tasks[filtered_tasks['UniqueTaskId'].isin(selected_unique_ids)]
                    
                    min_dates = []
                    for _, row in selected_full_data.iterrows():
                        task_assigned = row.get('TaskAssignedDt')
                        if pd.notna(task_assigned):
                            if isinstance(task_assigned, str):
                                task_assigned = pd.to_datetime(task_assigned)
                            min_dates.append(task_assigned.date() if hasattr(task_assigned, 'date') else task_assigned)
                    
                    # Use earliest date as minimum, or default
                    if min_dates:
                        earliest_date = min(min_dates)
                    else:
                        earliest_date = date(2025, 1, 1)
                    
                    st.markdown("#### ✏️ Update Status")
                    
                    form_col1, form_col2 = st.columns(2)
                    
                    with form_col1:
                        new_status = st.selectbox(
                            "New Status",
                            options=CLOSED_STATUSES,
                            help="Select the closing status for selected task(s)",
                            key="bulk_new_status"
                        )
                    
                    with form_col2:
                        status_update_date = st.date_input(
                            "Status Update Date",
                            value=date.today(),
                            min_value=earliest_date,
                            help=f"Minimum date: {earliest_date} (earliest Task Assigned Date among selected)",
                            key="bulk_status_date"
                        )
                    
                    # Show impact preview
                    update_dt = datetime.combine(status_update_date, datetime.min.time())
                    close_sprint = calendar.get_sprint_for_date(update_dt)
                    
                    st.markdown("---")
                    st.markdown("**📍 Impact Preview:**")
                    
                    if close_sprint:
                        if close_sprint['SprintNumber'] == selected_sprint_num:
                            st.success(f"✅ Task(s) will close in **this sprint** (Sprint {close_sprint['SprintNumber']})")
                            st.caption("Tasks will remain visible in this sprint but won't carry over to next sprint")
                        elif close_sprint['SprintNumber'] < selected_sprint_num:
                            st.warning(f"⬅️ Task(s) will move **back** to **Sprint {close_sprint['SprintNumber']}** ({close_sprint['SprintName']})")
                            st.caption(f"Tasks will be removed from Sprint {selected_sprint_num} and all sprints after Sprint {close_sprint['SprintNumber']}")
                        else:
                            st.info(f"➡️ Task(s) will close in **Sprint {close_sprint['SprintNumber']}** ({close_sprint['SprintName']})")
                    else:
                        st.warning("⚠️ Selected date is outside defined sprint windows")
                    
                    # Check for tasks where update date is before their assigned date
                    invalid_tasks = []
                    valid_tasks = []
                    for _, row in selected_full_data.iterrows():
                        task_assigned = row.get('TaskAssignedDt')
                        if pd.notna(task_assigned):
                            if isinstance(task_assigned, str):
                                task_assigned = pd.to_datetime(task_assigned)
                            task_date = task_assigned.date() if hasattr(task_assigned, 'date') else task_assigned
                            if status_update_date < task_date:
                                invalid_tasks.append({
                                    'id': row['UniqueTaskId'],
                                    'task': row['TaskNum'],
                                    'assigned': task_date
                                })
                            else:
                                valid_tasks.append(row['UniqueTaskId'])
                        else:
                            valid_tasks.append(row['UniqueTaskId'])
                    
                    if invalid_tasks:
                        st.warning(f"⚠️ {len(invalid_tasks)} task(s) have Task Assigned Date after the selected Status Update Date:")
                        for t in invalid_tasks:
                            st.caption(f"  • Task {t['task']}: Assigned {t['assigned']}")
                        st.info(f"These tasks will be skipped. {len(valid_tasks)} task(s) will be updated.")
                    
                    # Update button
                    if st.button(f"💾 Update {len(valid_tasks)} Task(s)", type="primary", use_container_width=True, disabled=len(valid_tasks) == 0):
                        success_count = 0
                        fail_count = 0
                        
                        for task_id in valid_tasks:
                            success = task_store.update_task_status(
                                task_id,
                                new_status,
                                update_dt
                            )
                            if success:
                                success_count += 1
                            else:
                                fail_count += 1
                        
                        if success_count > 0:
                            st.success(f"✅ Successfully updated {success_count} task(s) to '{new_status}'")
                        if fail_count > 0:
                            st.error(f"❌ Failed to update {fail_count} task(s)")
                        
                        if success_count > 0:
                            st.rerun()

with tab3:
    st.subheader("📊 Task Distribution")
    
    # By original sprint
    if 'OriginalSprintNumber' in sprint_tasks.columns:
        st.markdown("**Tasks by Original Sprint:**")
        
        orig_counts = sprint_tasks.groupby('OriginalSprintNumber').size().reset_index(name='Count')
        orig_counts['Sprint'] = orig_counts['OriginalSprintNumber'].apply(lambda x: f"Sprint {int(x)}")
        orig_counts['Type'] = orig_counts['OriginalSprintNumber'].apply(
            lambda x: 'Original' if x == selected_sprint_num else 'Carryover'
        )
        
        st.dataframe(
            orig_counts[['Sprint', 'Count', 'Type']],
            use_container_width=True,
            hide_index=True
        )
    
    # By status
    if 'Status' in sprint_tasks.columns:
        st.markdown("**Tasks by Status:**")
        
        status_counts = sprint_tasks['Status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        status_counts['Type'] = status_counts['Status'].apply(
            lambda x: '🔴 Closed' if x in CLOSED_STATUSES else '🟢 Open'
        )
        
        st.dataframe(
            status_counts,
            use_container_width=True,
            hide_index=True
        )
    
    # By assignee
    if 'AssignedTo' in sprint_tasks.columns:
        st.markdown("**Tasks by Assignee:**")
        
        assignee_counts = sprint_tasks.groupby('AssignedTo').agg({
            'UniqueTaskId': 'count',
            'Status': lambda x: sum(x.isin(CLOSED_STATUSES))
        }).reset_index()
        assignee_counts.columns = ['Assignee', 'Total', 'Closed']
        assignee_counts['Open'] = assignee_counts['Total'] - assignee_counts['Closed']
        
        st.dataframe(
            assignee_counts[['Assignee', 'Total', 'Open', 'Closed']],
            use_container_width=True,
            hide_index=True
        )
