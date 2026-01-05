"""
Work Backlogs Page
All open tasks appear here. Admin assigns/re-assigns them to sprints.
SprintsAssigned column tracks all sprint assignments for each task.
"""
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
from datetime import datetime
from modules.task_store import get_task_store
from modules.sprint_calendar import get_sprint_calendar
from components.auth import require_admin, display_user_info
from utils.grid_styles import apply_grid_styles, get_custom_css, STATUS_CELL_STYLE, DAYS_OPEN_CELL_STYLE, COLUMN_WIDTHS, COLUMN_DESCRIPTIONS, display_column_help
from utils.exporters import export_to_excel

st.set_page_config(
    page_title="Work Backlogs & Sprint Assignment",
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

st.title("📋 Work Backlogs & Sprint Assignment")

# Get task store and sprint calendar
task_store = get_task_store()
calendar = get_sprint_calendar()

# Get backlog tasks (all open tasks)
backlog_tasks = task_store.get_backlog_tasks()

# Get available sprints for assignment (only current and future)
all_sprints = calendar.get_all_sprints()
current_sprint = calendar.get_current_sprint()
current_sprint_num = current_sprint['SprintNumber'] if current_sprint else 1

# Filter to only current and future sprints for assignment
future_sprints = all_sprints[all_sprints['SprintNumber'] >= current_sprint_num].copy()

with st.expander("ℹ️ How to Use This Page", expanded=False):
    st.markdown("""
    All **open tasks** appear here. As admin, you can:
    - **Click checkbox** to select tasks for sprint assignment
    - Assign tasks to **current or future sprints**
    - Tasks can be assigned to multiple sprints over time
    - Track sprint assignment history in the **Sprints Assigned** column
    - Completed tasks are automatically moved to the **Completed Tasks** page
    """)

# Summary metrics by ticket type
if not backlog_tasks.empty and 'TicketType' in backlog_tasks.columns:
    # Count tasks by type
    task_counts = backlog_tasks['TicketType'].value_counts().to_dict()
    
    # Count unique tickets by type
    ticket_counts = {}
    if 'TicketNum' in backlog_tasks.columns:
        for ticket_type in ['SR', 'PR', 'IR', 'NC', 'AD']:
            ticket_counts[ticket_type] = backlog_tasks[backlog_tasks['TicketType'] == ticket_type]['TicketNum'].nunique()
        total_tickets = backlog_tasks['TicketNum'].nunique()
    else:
        ticket_counts = task_counts.copy()
        total_tickets = len(backlog_tasks)
    
    # Ticket type labels
    type_labels = {
        'SR': 'SR (Service Request)',
        'PR': 'PR (Problem)',
        'IR': 'IR (Incident Request)',
        'NC': 'NC (Non-classified IS Requests)',
        'AD': 'AD (Admin Request)'
    }
    
    # Row 1: Tickets by category
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Total Current Tickets", total_tickets)
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
        st.metric("Total Current Tasks", len(backlog_tasks))
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

st.divider()

if backlog_tasks.empty:
    st.info("📭 **No open tasks.** All tasks are completed.")
    st.caption("Upload a new iTrack extract to add tasks to the backlog.")
else:
    # Calculate DaysCreated from TicketCreatedDt
    if 'TicketCreatedDt' in backlog_tasks.columns:
        backlog_tasks['DaysCreated'] = (datetime.now() - pd.to_datetime(backlog_tasks['TicketCreatedDt'], errors='coerce')).dt.days
    
    # Use all backlog tasks (AgGrid has built-in filtering)
    display_tasks = backlog_tasks.copy()
    assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in backlog_tasks.columns else 'AssignedTo'
    
    # Calculate TaskCount for each ticket (e.g., "1/3", "2/3", "3/3")
    if 'TicketNum' in display_tasks.columns:
        # Count tasks per ticket
        ticket_counts = display_tasks.groupby('TicketNum').size().to_dict()
        
        # Sort by DaysCreated (oldest tickets first), then by TaskNum within ticket
        display_tasks = display_tasks.sort_values(
            by=['DaysCreated', 'TicketNum', 'TaskNum'],
            ascending=[False, True, True],
            na_position='last'
        ).reset_index(drop=True)
        
        # Add TaskCount column and track ticket groups for row banding
        task_counts = []
        ticket_group_ids = []
        current_group = 0
        prev_ticket = None
        task_counter = {}
        
        for idx, row in display_tasks.iterrows():
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
        
        display_tasks['TaskCount'] = task_counts
        display_tasks['_TicketGroup'] = ticket_group_ids
        display_tasks['_IsMultiTask'] = display_tasks['TicketNum'].map(lambda x: ticket_counts.get(x, 1) > 1)
    
    
    # Sprint assignment section
    st.markdown("### 📤 Assign Tasks to Sprint")
    
    # Sprint selector - only current and future sprints
    if not future_sprints.empty:
        # Build sprint options with date ranges
        sprint_display_options = []
        sprint_num_map = {}
        for _, row in future_sprints.iterrows():
            sprint_num = row['SprintNumber']
            start_dt = pd.to_datetime(row['SprintStartDt']).strftime('%m/%d/%Y')
            end_dt = pd.to_datetime(row['SprintEndDt']).strftime('%m/%d/%Y')
            display_text = f"Sprint {sprint_num}: {start_dt} - {end_dt}"
            sprint_display_options.append(display_text)
            sprint_num_map[display_text] = sprint_num
        
        # Sort by sprint number (descending)
        sprint_display_options = sorted(sprint_display_options, key=lambda x: sprint_num_map[x], reverse=True)
        
        # Find default index
        default_idx = 0
        if current_sprint:
            current_display = [k for k, v in sprint_num_map.items() if v == current_sprint['SprintNumber']]
            if current_display and current_display[0] in sprint_display_options:
                default_idx = sprint_display_options.index(current_display[0])
        
        selected_sprint_display = st.selectbox(
            "Target Sprint",
            sprint_display_options,
            index=default_idx,
            key="target_sprint_select"
        )
        target_sprint = sprint_num_map[selected_sprint_display]
    else:
        st.warning("No sprints available. Please set up sprint calendar first.")
        target_sprint = None
    
    st.divider()
    
    # Prepare display dataframe - same columns as Sprint Planning (plus SprintsAssigned for backlog)
    display_cols = [
        'UniqueTaskId', '_TicketGroup', '_IsMultiTask', 'SprintsAssigned',
        'TicketNum', 'TaskCount', 'TicketType', 'Section', 'CustomerName', 'TaskNum',
        'Status', 'AssignedTo', 'Subject', 'TicketCreatedDt', 'TaskCreatedDt',
        'DaysOpen', 'CustomerPriority', 'FinalPriority', 'GoalType', 'DependencyOn',
        'DependenciesLead', 'DependencySecured', 'Comments', 'HoursEstimated',
        'TaskHoursSpent', 'TicketHoursSpent'
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
    
    # Hidden columns
    gb.configure_column('UniqueTaskId', hide=True)
    gb.configure_column('_TicketGroup', hide=True)
    gb.configure_column('_IsMultiTask', hide=True)
    
    # Ticket/Task info columns (same as Sprint Planning)
    gb.configure_column('TicketNum', header_name='TicketNum', width=COLUMN_WIDTHS['TicketNum'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TicketNum', ''))
    gb.configure_column('TaskCount', header_name='Task#', width=COLUMN_WIDTHS['TaskCount'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TaskCount', ''))
    gb.configure_column('TicketType', header_name='TicketType', width=COLUMN_WIDTHS['TicketType'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TicketType', ''))
    gb.configure_column('Section', header_name='Section', width=COLUMN_WIDTHS['Section'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('Section', ''))
    gb.configure_column('CustomerName', header_name='CustomerName', width=COLUMN_WIDTHS['CustomerName'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('CustomerName', ''))
    gb.configure_column('TaskNum', header_name='TaskNum', width=COLUMN_WIDTHS['TaskNum'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TaskNum', ''))
    gb.configure_column('Status', header_name='Status', width=COLUMN_WIDTHS['Status'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('Status', ''), )
    gb.configure_column('AssignedTo', header_name='AssignedTo', width=COLUMN_WIDTHS['AssignedTo'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('AssignedTo', ''))
    gb.configure_column('Subject', header_name='Subject', width=COLUMN_WIDTHS['Subject'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('Subject', ''), tooltipField='Subject')
    gb.configure_column('TicketCreatedDt', header_name='TicketCreatedDt', width=COLUMN_WIDTHS['TicketCreatedDt'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TicketCreatedDt', ''))
    gb.configure_column('TaskCreatedDt', header_name='TaskCreatedDt', width=COLUMN_WIDTHS['TaskCreatedDt'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TaskCreatedDt', ''))
    
    # Metrics and planning fields (read-only in backlog, same as Sprint Planning)
    gb.configure_column('DaysOpen', header_name='DaysOpen', width=COLUMN_WIDTHS['DaysOpen'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('DaysOpen', ''), )
    gb.configure_column('CustomerPriority', header_name='CustomerPriority', width=COLUMN_WIDTHS['CustomerPriority'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('CustomerPriority', ''))
    gb.configure_column('FinalPriority', header_name='FinalPriority', width=COLUMN_WIDTHS['FinalPriority'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('FinalPriority', ''))
    gb.configure_column('GoalType', header_name='GoalType', width=COLUMN_WIDTHS['GoalType'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('GoalType', ''))
    gb.configure_column('DependencyOn', header_name='Dependency', width=COLUMN_WIDTHS['DependencyOn'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('DependencyOn', ''))
    gb.configure_column('DependenciesLead', header_name='DependencyLead(s)', width=COLUMN_WIDTHS['DependenciesLead'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('DependenciesLead', ''), tooltipField='DependenciesLead')
    gb.configure_column('DependencySecured', header_name='DependencySecured', width=COLUMN_WIDTHS['DependencySecured'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('DependencySecured', ''))
    gb.configure_column('Comments', header_name='Comments', width=COLUMN_WIDTHS['Comments'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('Comments', ''), tooltipField='Comments')
    gb.configure_column('HoursEstimated', header_name='HoursEstimated', width=COLUMN_WIDTHS['HoursEstimated'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('HoursEstimated', ''))
    gb.configure_column('TaskHoursSpent', header_name='TaskHoursSpent', width=COLUMN_WIDTHS['TaskHoursSpent'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TaskHoursSpent', ''))
    gb.configure_column('TicketHoursSpent', header_name='TicketHoursSpent', width=COLUMN_WIDTHS['TicketHoursSpent'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TicketHoursSpent', ''))
    
    # Show all rows (no pagination) - typically fewer than 200 open tasks
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
    
    
    # Column descriptions help
    display_column_help(title="❓ Column Descriptions")
    
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
    
    # Export section - exports current filtered view
    col_export1, col_export2 = st.columns([2, 6])
    
    with col_export1:
        # Export current filtered view
        export_df = grid_df.copy()
        # Remove internal columns from export
        export_cols = [c for c in export_df.columns if not c.startswith('_')]
        export_df = export_df[export_cols]
        
        excel_data = export_to_excel(export_df, sheet_name="Work Backlogs")
        filename = f"work_backlogs_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        
        st.download_button(
            label=f"📥 Export to Excel ({len(export_df)} tasks)",
            data=excel_data,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Export current filtered view to Excel"
        )
    
    with col_export2:
        st.caption("💡 Apply filters above to narrow down data before exporting.")
    
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
