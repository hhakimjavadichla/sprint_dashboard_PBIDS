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
from utils.grid_styles import apply_grid_styles, get_custom_css, STATUS_CELL_STYLE, PRIORITY_CELL_STYLE, DAYS_OPEN_CELL_STYLE, TASK_ORIGIN_CELL_STYLE, COLUMN_WIDTHS, display_column_help, get_display_column_order, clean_subject_column

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
    # Use all tasks (AgGrid has built-in filtering)
    tab1_assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in sprint_tasks.columns else 'AssignedTo'
    filtered_df = sprint_tasks.copy()
    
    st.caption(f"Showing {len(filtered_df)} tasks")
    
    # Use standardized column order from config
    display_order = get_display_column_order(tab1_assignee_col)
    
    available_cols = [col for col in display_order if col in filtered_df.columns]
    display_df = filtered_df[available_cols].copy()
    
    # Clean subject column (remove LAB-XX: NNNNNN - prefix)
    display_df = clean_subject_column(display_df)
    
    # Configure grid
    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_default_column(resizable=True, filterable=True, sortable=True)
    
    # Hidden columns
    gb.configure_column('_TicketGroup', hide=True)
    gb.configure_column('_IsMultiTask', hide=True)
    
    # Sprint columns
    gb.configure_column('SprintNumber', header_name='SprintNumber', width=COLUMN_WIDTHS.get('SprintNumber', 100))
    gb.configure_column('SprintName', header_name='SprintName', width=COLUMN_WIDTHS.get('SprintName', 120))
    gb.configure_column('SprintStartDt', header_name='SprintStartDt', width=COLUMN_WIDTHS.get('SprintStartDt', 100))
    gb.configure_column('SprintEndDt', header_name='SprintEndDt', width=COLUMN_WIDTHS.get('SprintEndDt', 100))
    gb.configure_column('TaskOrigin', header_name='TaskOrigin', width=COLUMN_WIDTHS.get('TaskOrigin', 90))
    gb.configure_column('SprintsAssigned', header_name='SprintsAssigned', width=COLUMN_WIDTHS.get('SprintsAssigned', 130))
    
    # Ticket/Task columns
    gb.configure_column('TicketNum', header_name='TicketNum', width=COLUMN_WIDTHS['TicketNum'])
    gb.configure_column('TaskCount', header_name='Task#', width=COLUMN_WIDTHS.get('TaskCount', 70))
    gb.configure_column('TicketType', header_name='TicketType', width=COLUMN_WIDTHS['TicketType'])
    gb.configure_column('Section', header_name='Section', width=COLUMN_WIDTHS.get('Section', 100))
    gb.configure_column('CustomerName', header_name='CustomerName', width=COLUMN_WIDTHS.get('CustomerName', 120))
    gb.configure_column('TaskNum', header_name='TaskNum', width=COLUMN_WIDTHS['TaskNum'])
    gb.configure_column('Status', header_name='Status', width=COLUMN_WIDTHS['Status'])
    gb.configure_column('TicketStatus', header_name='TicketStatus', width=COLUMN_WIDTHS.get('TicketStatus', 100))
    gb.configure_column(tab1_assignee_col, header_name='AssignedTo', width=COLUMN_WIDTHS['AssignedTo'])
    gb.configure_column('Subject', header_name='Subject', width=COLUMN_WIDTHS['Subject'], tooltipField='Subject')
    gb.configure_column('TicketCreatedDt', header_name='TicketCreatedDt', width=COLUMN_WIDTHS.get('TicketCreatedDt', 110))
    gb.configure_column('TaskCreatedDt', header_name='TaskCreatedDt', width=COLUMN_WIDTHS.get('TaskCreatedDt', 110))
    gb.configure_column('DaysOpen', header_name='DaysOpen', width=COLUMN_WIDTHS['DaysOpen'])
    gb.configure_column('CustomerPriority', header_name='CustomerPriority', width=COLUMN_WIDTHS['CustomerPriority'])
    gb.configure_column('FinalPriority', header_name='FinalPriority', width=COLUMN_WIDTHS.get('FinalPriority', 100))
    gb.configure_column('GoalType', header_name='GoalType', width=COLUMN_WIDTHS.get('GoalType', 90))
    gb.configure_column('DependencyOn', header_name='Dependency', width=COLUMN_WIDTHS.get('DependencyOn', 110))
    gb.configure_column('DependenciesLead', header_name='DependencyLead(s)', width=COLUMN_WIDTHS.get('DependenciesLead', 120))
    gb.configure_column('DependencySecured', header_name='DependencySecured', width=COLUMN_WIDTHS.get('DependencySecured', 130))
    gb.configure_column('Comments', header_name='Comments', width=COLUMN_WIDTHS['Comments'], tooltipField='Comments')
    gb.configure_column('HoursEstimated', header_name='HoursEstimated', width=COLUMN_WIDTHS['HoursEstimated'])
    gb.configure_column('TaskHoursSpent', header_name='TaskHoursSpent', width=COLUMN_WIDTHS.get('TaskHoursSpent', 110))
    gb.configure_column('TicketHoursSpent', header_name='TicketHoursSpent', width=COLUMN_WIDTHS.get('TicketHoursSpent', 120))
    gb.configure_pagination(enabled=False)
    
    grid_options = gb.build()
    grid_options['enableBrowserTooltips'] = False  # Disable browser tooltips to avoid double tooltip
    
    AgGrid(
        display_df,
        gridOptions=grid_options,
        height=600,
        theme='streamlit',
        fit_columns_on_grid_load=False,
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
            
            # Use all open tasks (AgGrid has built-in filtering)
            filtered_tasks = open_tasks.copy()
            assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in open_tasks.columns else 'AssignedTo'
            
            st.caption(f"Showing {len(filtered_tasks)} open tasks")
            
            if not filtered_tasks.empty:
                # Prepare display dataframe with better formatting
                display_df = filtered_tasks.copy()
                
                # Create Sprint ID column: S{SprintNumber}-TaskNum
                display_df['SprintTaskId'] = display_df.apply(
                    lambda r: f"S{selected_sprint_num}-{r['TaskNum']}", axis=1
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
                            'AssignedDate', 'DaysOpen', 'Subject', 'TaskNum']
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
                gb.configure_column('SprintTaskId', header_name='SprintTaskId', width=COLUMN_WIDTHS.get('SprintTaskId', 120), pinned='left')
                gb.configure_column('Status', header_name='Status', width=COLUMN_WIDTHS['Status'])
                gb.configure_column(assignee_col, header_name='AssignedTo', width=COLUMN_WIDTHS['AssignedTo'])
                gb.configure_column('Section', header_name='Section', width=COLUMN_WIDTHS['Section'])
                gb.configure_column('TicketType', header_name='TicketType', width=COLUMN_WIDTHS['TicketType'])
                gb.configure_column('AssignedDate', header_name='AssignedDate', width=COLUMN_WIDTHS.get('AssignedDate', 115))
                gb.configure_column('DaysOpen', header_name='DaysOpen', width=COLUMN_WIDTHS['DaysOpen'])
                gb.configure_column('Subject', header_name='Subject', width=COLUMN_WIDTHS['Subject'], tooltipField='Subject')
                gb.configure_column('TaskNum', hide=True)  # Hidden but needed for reference
                
                grid_options = gb.build()
                grid_options['enableBrowserTooltips'] = False  # Disable browser tooltips to avoid double tooltip
                
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
                    selected_task_nums = [str(t) for t in selected_df['TaskNum'].tolist()]
                    selected_full_data = filtered_tasks[filtered_tasks['TaskNum'].astype(str).isin(selected_task_nums)]
                    
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
                        task_num = str(row['TaskNum'])
                        if pd.notna(task_assigned):
                            if isinstance(task_assigned, str):
                                task_assigned = pd.to_datetime(task_assigned)
                            task_date = task_assigned.date() if hasattr(task_assigned, 'date') else task_assigned
                            if status_update_date < task_date:
                                invalid_tasks.append({
                                    'id': task_num,
                                    'task': task_num,
                                    'assigned': task_date
                                })
                            else:
                                valid_tasks.append(task_num)
                        else:
                            valid_tasks.append(task_num)
                    
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
            'TaskNum': 'count',
            'Status': lambda x: sum(x.isin(CLOSED_STATUSES))
        }).reset_index()
        assignee_counts.columns = ['Assignee', 'Total', 'Closed']
        assignee_counts['Open'] = assignee_counts['Total'] - assignee_counts['Closed']
        
        st.dataframe(
            assignee_counts[['Assignee', 'Total', 'Open', 'Closed']],
            use_container_width=True,
            hide_index=True
        )
