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
from modules.section_filter import exclude_forever_tickets, exclude_ad_tickets
from components.auth import require_team_member, display_user_info, is_admin
from utils.grid_styles import apply_grid_styles, get_custom_css, STATUS_CELL_STYLE, DAYS_OPEN_CELL_STYLE, COLUMN_WIDTHS, COLUMN_DESCRIPTIONS, display_column_help, get_backlog_column_order, clean_subject_column
from utils.exporters import export_to_excel
from components.metrics_dashboard import display_ticket_task_metrics

# Apply custom styles
apply_grid_styles()

# Require team member access (Admin or PIBIDS User)
require_team_member("Backlog Assign")

# Display user info
display_user_info()

st.title("Backlog Assign")

# Check if user can edit (Admin only)
can_edit_backlog = is_admin()

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
    if can_edit_backlog:
        st.markdown("""
        All **open tasks** appear here. As admin, you can:
        - **Click checkbox** to select tasks for sprint assignment
        - Assign tasks to **current or future sprints**
        - Tasks can be assigned to multiple sprints over time
        - Track sprint assignment history in the **Sprints Assigned** column
        - Completed tasks are automatically moved to the **Completed Tasks** page
        """)
    else:
        st.markdown("""
        All **open tasks** appear here. You have **read-only access**.
        - View all backlog tasks and their current status
        - Track sprint assignment history in the **Sprints Assigned** column
        - Only Admins can assign tasks to sprints
        """)

# Forever ticket filter
col1, col2, col3, col4 = st.columns(4)
with col1:
    exclude_forever = st.checkbox(
        "Exclude Forever Tickets",
        value=False,
        help="Hide Standing Meetings and Miscellaneous Meetings tasks",
        key="exclude_forever_backlog"
    )
with col2:
    exclude_ad = st.checkbox(
        "Exclude AD Tickets",
        value=False,
        help="Hide Admin Request (AD) tickets",
        key="exclude_ad_backlog"
    )

# Apply filters for metrics display
metrics_tasks = backlog_tasks.copy()
if exclude_forever:
    metrics_tasks = exclude_forever_tickets(metrics_tasks)
if exclude_ad:
    metrics_tasks = exclude_ad_tickets(metrics_tasks)

# Summary metrics by ticket type (reusable component) - use filtered data
display_ticket_task_metrics(metrics_tasks)

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
    
    # Apply forever ticket filter
    if exclude_forever:
        display_tasks = exclude_forever_tickets(display_tasks)
    
    # Apply AD ticket filter
    if exclude_ad:
        display_tasks = exclude_ad_tickets(display_tasks)
    
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
    st.markdown("### Assign Tasks to Sprint")
    
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
    
    # Placeholder for assignment UI - will be populated after grid selection
    assignment_container = st.container()
    
    st.divider()
    
    # Use standardized column order from config
    # Use display name if available
    if 'AssignedTo_Display' in display_tasks.columns:
        display_tasks['AssignedTo'] = display_tasks['AssignedTo_Display']
    
    display_cols = get_backlog_column_order('AssignedTo')
    available_cols = [col for col in display_cols if col in display_tasks.columns]
    grid_df = display_tasks[available_cols].copy()
    
    # Clean subject column (remove LAB-XX: NNNNNN - prefix)
    grid_df = clean_subject_column(grid_df)
    
    # Convert dependency columns from float to string (required for dropdown editors)
    for col in ['DependencyOn', 'DependenciesLead', 'DependencySecured', 'Comments']:
        if col in grid_df.columns:
            grid_df[col] = grid_df[col].fillna('').astype(str)
            # Clean up 'nan' strings
            grid_df[col] = grid_df[col].replace('nan', '')
    
    # Convert priority columns to string for dropdown compatibility
    for priority_col in ['CustomerPriority', 'FinalPriority']:
        if priority_col in grid_df.columns:
            grid_df[priority_col] = grid_df[priority_col].apply(
                lambda x: '' if pd.isna(x) else str(int(x)) if isinstance(x, (int, float)) else str(x)
            )
    
    # Define dropdown values for editable columns
    # Use strings for all values to avoid ag-Grid type coercion issues
    PRIORITY_VALUES = ['', '0', '1', '2', '3', '4', '5']
    DEPENDENCY_VALUES = ['', 'Yes', 'No']
    DEPENDENCY_SECURED_VALUES = ['', 'Yes', 'Pending', 'No']
    GOAL_TYPE_VALUES = ['', 'Mandatory', 'Stretch']
    
    # Define column view presets for Backlog Assign
    COLUMN_VIEWS = {
        'All Columns': None,  # None means show all columns
        'Quick Assign': ['SprintsAssigned', 'TaskNum', 'Subject', 'AssignedTo', 'Section', 
                         'TicketType', 'DaysOpen', 'FinalPriority'],
        'Priority Review': ['SprintsAssigned', 'TaskNum', 'Subject', 'AssignedTo', 
                           'CustomerPriority', 'FinalPriority', 'GoalType', 'DaysOpen'],
        'Dependencies': ['SprintsAssigned', 'TaskNum', 'Subject', 'AssignedTo', 
                        'DependencyOn', 'DependenciesLead', 'DependencySecured', 'Comments']
    }
    
    # View selector
    selected_view = st.radio(
        "Column View: Select a preset to show only relevant columns for specific tasks",
        options=list(COLUMN_VIEWS.keys()),
        horizontal=True,
        key="backlog_assign_view_selector"
    )
    
    # Get columns to show based on selected view
    view_columns = COLUMN_VIEWS[selected_view]
    
    # Helper function to check if column should be hidden
    def should_hide(col_name):
        if view_columns is None:  # All Columns view
            return False
        return col_name not in view_columns
    
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
    
    # Configure first column with checkbox (SprintsAssigned is always visible for assignment)
    gb.configure_column(
        'SprintsAssigned', 
        header_name='Sprints Assigned', 
        width=130,
        checkboxSelection=True,
        headerCheckboxSelection=True,
        hide=should_hide('SprintsAssigned')
    )
    
    # Hidden columns (always hidden)
    gb.configure_column('_TicketGroup', hide=True)
    gb.configure_column('_IsMultiTask', hide=True)
    
    # Ticket/Task info columns (same as Sprint Planning)
    gb.configure_column('TicketNum', header_name='TicketNum', width=COLUMN_WIDTHS['TicketNum'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TicketNum', ''), hide=should_hide('TicketNum'))
    gb.configure_column('TaskCount', header_name='Task#', width=COLUMN_WIDTHS['TaskCount'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TaskCount', ''), hide=should_hide('TaskCount'))
    gb.configure_column('TicketType', header_name='TicketType', width=COLUMN_WIDTHS['TicketType'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TicketType', ''), hide=should_hide('TicketType'))
    gb.configure_column('Section', header_name='Section', width=COLUMN_WIDTHS['Section'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('Section', ''), hide=should_hide('Section'))
    gb.configure_column('CustomerName', header_name='CustomerName', width=COLUMN_WIDTHS['CustomerName'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('CustomerName', ''), hide=should_hide('CustomerName'))
    gb.configure_column('TaskNum', header_name='TaskNum', width=COLUMN_WIDTHS['TaskNum'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TaskNum', ''), hide=should_hide('TaskNum'))
    gb.configure_column('TaskStatus', header_name='TaskStatus', width=COLUMN_WIDTHS.get('TaskStatus', 100),
                        headerTooltip=COLUMN_DESCRIPTIONS.get('Status', ''), hide=should_hide('TaskStatus'))
    gb.configure_column('TicketStatus', header_name='TicketStatus', width=COLUMN_WIDTHS.get('TicketStatus', 100),
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TicketStatus', ''), hide=should_hide('TicketStatus'))
    gb.configure_column('AssignedTo', header_name='AssignedTo', width=COLUMN_WIDTHS['AssignedTo'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('AssignedTo', ''), hide=should_hide('AssignedTo'))
    gb.configure_column('Subject', header_name='Subject', width=COLUMN_WIDTHS.get('Subject', 200),
                        headerTooltip=COLUMN_DESCRIPTIONS.get('Subject', ''), tooltipField='Subject', hide=should_hide('Subject'))
    gb.configure_column('TicketCreatedDt', header_name='TicketCreatedDt', width=COLUMN_WIDTHS['TicketCreatedDt'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TicketCreatedDt', ''), hide=should_hide('TicketCreatedDt'))
    gb.configure_column('TaskCreatedDt', header_name='TaskCreatedDt', width=COLUMN_WIDTHS['TaskCreatedDt'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TaskCreatedDt', ''), hide=should_hide('TaskCreatedDt'))
    
    # Metrics and planning fields
    gb.configure_column('DaysOpen', header_name='DaysOpen', width=COLUMN_WIDTHS['DaysOpen'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('DaysOpen', ''), hide=should_hide('DaysOpen'))
    gb.configure_column('CustomerPriority', header_name='CustomerPriority', width=COLUMN_WIDTHS['CustomerPriority'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('CustomerPriority', ''), hide=should_hide('CustomerPriority'))
    gb.configure_column('FinalPriority', header_name='✏️ FinalPriority', width=COLUMN_WIDTHS['FinalPriority'], editable=True,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('FinalPriority', ''),
                        cellEditor='agSelectCellEditor',
                        cellEditorParams={'values': PRIORITY_VALUES}, hide=should_hide('FinalPriority'))
    gb.configure_column('GoalType', header_name='✏️ GoalType', width=COLUMN_WIDTHS['GoalType'], editable=True,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('GoalType', ''),
                        cellEditor='agSelectCellEditor',
                        cellEditorParams={'values': GOAL_TYPE_VALUES}, hide=should_hide('GoalType'))
    gb.configure_column('DependencyOn', header_name='✏️ Dependency', width=COLUMN_WIDTHS['DependencyOn'], editable=True,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('DependencyOn', ''),
                        cellEditor='agSelectCellEditor',
                        cellEditorParams={'values': DEPENDENCY_VALUES}, hide=should_hide('DependencyOn'))
    gb.configure_column('DependenciesLead', header_name='✏️ DependencyLead(s)', width=COLUMN_WIDTHS['DependenciesLead'], editable=True,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('DependenciesLead', ''), tooltipField='DependenciesLead',
                        cellEditor='agLargeTextCellEditor',
                        cellEditorPopup=True,
                        cellEditorParams={'maxLength': 1000, 'rows': 5, 'cols': 40}, hide=should_hide('DependenciesLead'))
    gb.configure_column('DependencySecured', header_name='✏️ DependencySecured', width=COLUMN_WIDTHS['DependencySecured'], editable=True,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('DependencySecured', ''),
                        cellEditor='agSelectCellEditor',
                        cellEditorParams={'values': DEPENDENCY_SECURED_VALUES}, hide=should_hide('DependencySecured'))
    gb.configure_column('Comments', header_name='✏️ Comments', width=COLUMN_WIDTHS['Comments'], editable=True,
                        headerTooltip=COLUMN_DESCRIPTIONS.get('Comments', ''), tooltipField='Comments',
                        cellEditor='agLargeTextCellEditor',
                        cellEditorPopup=True,
                        cellEditorParams={'maxLength': 2000, 'rows': 5, 'cols': 50}, hide=should_hide('Comments'))
    gb.configure_column('HoursEstimated', header_name='HoursEstimated', width=COLUMN_WIDTHS['HoursEstimated'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('HoursEstimated', ''), hide=should_hide('HoursEstimated'))
    gb.configure_column('TaskHoursSpent', header_name='TaskHoursSpent', width=COLUMN_WIDTHS['TaskHoursSpent'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TaskHoursSpent', ''), hide=should_hide('TaskHoursSpent'))
    gb.configure_column('TicketHoursSpent', header_name='TicketHoursSpent', width=COLUMN_WIDTHS['TicketHoursSpent'],
                        headerTooltip=COLUMN_DESCRIPTIONS.get('TicketHoursSpent', ''), hide=should_hide('TicketHoursSpent'))
    
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
    grid_options['enableBrowserTooltips'] = False  # Disable browser tooltips to avoid double tooltip
    
    st.caption("✏️ = Editable column (double-click to edit). Click 'Save Changes' below when done.")
    
    # Column descriptions help
    display_column_help(title="❓ Column Descriptions")
    
    grid_response = AgGrid(
        grid_df,
        gridOptions=grid_options,
        height=500,
        theme='streamlit',
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        custom_css=get_custom_css()
    )
    
    # Get edited data from grid
    edited_df = pd.DataFrame(grid_response['data'])
    
    selected_rows = grid_response['selected_rows']
    
    # Convert to DataFrame if it's a list
    if isinstance(selected_rows, list):
        selected_df = pd.DataFrame(selected_rows) if selected_rows else pd.DataFrame()
    else:
        selected_df = selected_rows if selected_rows is not None else pd.DataFrame()
    
    # Populate assignment UI in the container above the table (Admin only)
    with assignment_container:
        if not can_edit_backlog:
            st.info("🔒 **Read-only mode.** Only Admins can assign tasks to sprints.")
        elif selected_df.empty or len(selected_df) == 0:
            st.info("👆 Select tasks from the table below to assign to the target sprint.")
        else:
            num_selected = len(selected_df)
            st.success(f"✅ **{num_selected} task(s) selected**")
            
            # Show selected tasks summary
            with st.expander(f"📋 View Selected Tasks ({num_selected})", expanded=False):
                for idx, row in selected_df.iterrows():
                    st.write(f"• **{row.get('TaskNum', 'N/A')}** | {row.get('TaskStatus', 'N/A')} | {row.get('AssignedTo', 'N/A')} | {str(row.get('Subject', ''))[:50]}...")
            
            # Assign button
            if target_sprint is not None:
                if st.button(f"📤 Assign {num_selected} Task(s) to Sprint {target_sprint}", type="primary", key="assign_btn"):
                    # Get TaskNums from selected rows
                    task_nums = [str(t) for t in selected_df['TaskNum'].tolist()]
                    
                    # Assign tasks (returns assigned_count, skipped_count, errors)
                    assigned, skipped, errors = task_store.assign_tasks_to_sprint(task_nums, target_sprint)
                    
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
    
    # Save Changes button for editable fields (Admin only)
    if can_edit_backlog:
        st.markdown("#### Save Edits")
        col_save1, col_save2 = st.columns([2, 6])
        
        with col_save1:
            if st.button("💾 Save Changes", type="primary", help="Save all edits to FinalPriority, GoalType, Dependencies, and Comments"):
                editable_fields = ['FinalPriority', 'GoalType', 'DependencyOn', 'DependenciesLead', 'DependencySecured', 'Comments']
                
                if 'TaskNum' not in edited_df.columns:
                    st.error("❌ TaskNum column not found in grid data.")
                else:
                    # Build updates list from edited grid data
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
                    
                    if success > 0:
                        st.toast(f"✅ Updated {success} task(s)", icon="✅")
                        st.rerun()
                    elif errors:
                        st.error(f"❌ Errors: {', '.join(errors[:3])}")
                    else:
                        st.info("No changes to save")
        
        with col_save2:
            st.caption("💡 Edit cells by double-clicking, then click 'Save Changes' to persist your edits.")
    
    st.divider()
    
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

# Footer
st.divider()
st.caption("💡 **Tip:** Open tasks stay in the backlog until completed. Assign them to sprints as needed - the Sprints Assigned column tracks all assignments.")
