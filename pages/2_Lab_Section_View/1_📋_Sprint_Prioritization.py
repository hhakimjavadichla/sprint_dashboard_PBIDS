"""
Section View Page
Filtered view for lab section users
Section users can update priority for open tasks in their section
"""
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from st_aggrid.shared import JsCode
from modules.task_store import get_task_store, CLOSED_STATUSES
from modules.section_filter import filter_by_section, get_section_summary
from modules.sprint_calendar import get_sprint_calendar
from datetime import datetime
from components.auth import require_auth, display_user_info, get_user_role, get_user_section, is_admin, is_pbids_user, can_edit_section
from utils.exporters import export_to_csv, export_to_excel
from utils.grid_styles import apply_grid_styles, get_custom_css, STATUS_CELL_STYLE, PRIORITY_CELL_STYLE, DAYS_OPEN_CELL_STYLE, COLUMN_WIDTHS, display_column_help, get_backlog_column_order, clean_subject_column

# Apply custom tooltip styles
apply_grid_styles()

st.title("📋 Sprint Prioritization")
st.caption("_Prototype — PBIDS Team_")

# Require authentication
require_auth("Section View")

# Display user info
display_user_info()

# Load data from task store - get ALL open tasks (not just sprint-assigned)
# This allows section users to set CustomerPriority before admin assigns to a sprint
task_store = get_task_store()
sprint_df = task_store.get_backlog_tasks()

if sprint_df is None or sprint_df.empty:
    st.warning("⚠️ No open tasks found")
    st.info("No open tasks available. Please contact an administrator.")
    st.stop()

# Get user's section
user_role = get_user_role()
user_section_raw = get_user_section()

# Parse user sections (may be comma-separated for multi-section users)
user_sections = []
if user_section_raw:
    user_sections = [s.strip() for s in user_section_raw.split(',') if s.strip()]

# For admins and PBIDS Users, allow section selection (view all sections)
if is_admin() or is_pbids_user():
    role_label = "Admin" if is_admin() else "PBIDS User"
    edit_note = "" if is_admin() else " (Read-only)"
    st.info(f"👑 **{role_label} View{edit_note}**: Select a section to view or see all sections")
    
    sections = sorted(sprint_df['Section'].dropna().unique().tolist())
    selected_section = st.selectbox(
        "Select Section to View",
        ['All Sections'] + sections,
        help="Choose a section to view filtered data"
    )
    
    if selected_section != 'All Sections':
        sprint_df = filter_by_section(sprint_df, selected_section)
        display_sections = [selected_section]
    else:
        display_sections = sections
else:
    # Section Managers and Section Users can only see their assigned sections
    if not user_sections:
        st.error("⚠️ No section assigned to your account")
        st.info("Please contact an administrator to assign a section")
        st.stop()
    
    # Filter to include all user's sections
    if 'Section' in sprint_df.columns:
        sprint_df = sprint_df[sprint_df['Section'].isin(user_sections)].copy()
    
    display_sections = user_sections
    role_label = "Section Manager" if user_role == 'Section Manager' else "Section User"
    st.info(f"👁️ **{role_label}**: Viewing tasks for **{', '.join(user_sections)}**")

st.divider()

# Summary metrics by ticket type - same format as Work Backlogs
if not sprint_df.empty and 'TicketType' in sprint_df.columns:
    # Count tasks by type
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
        st.metric("Total Current Tasks", len(sprint_df))
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

# Use all tasks (AgGrid has built-in filtering)
filtered_df = sprint_df.copy()

# Add ticket grouping for row banding (color-coded by ticket)
if 'TicketNum' in filtered_df.columns:
    # Count tasks per ticket
    ticket_counts_for_grouping = filtered_df.groupby('TicketNum').size().to_dict()
    
    # Sort by TicketNum to group tasks from same ticket together
    filtered_df = filtered_df.sort_values(
        by=['TicketNum', 'TaskNum'],
        ascending=[True, True],
        na_position='last'
    ).reset_index(drop=True)
    
    # Track ticket groups for row banding
    ticket_group_ids = []
    current_group = 0
    prev_ticket = None
    
    for idx, row in filtered_df.iterrows():
        ticket = row['TicketNum']
        if ticket != prev_ticket:
            current_group += 1
            prev_ticket = ticket
        ticket_group_ids.append(current_group)
    
    filtered_df['_TicketGroup'] = ticket_group_ids
    filtered_df['_IsMultiTask'] = filtered_df['TicketNum'].map(lambda x: ticket_counts_for_grouping.get(x, 1) > 1)

st.caption(f"Showing {len(filtered_df)} tasks")

# Task table - Priority is editable for open tasks
st.markdown("### Tasks")
st.caption("💡 You can edit **Priority** for open tasks. Double-click the Priority cell to change it.")

# Column descriptions help
display_column_help(title="❓ Column Descriptions")

# Current Sprint info
calendar = get_sprint_calendar()
current_sprint = calendar.get_current_sprint()
if current_sprint:
    start_dt = pd.to_datetime(current_sprint['SprintStartDt'])
    end_dt = pd.to_datetime(current_sprint['SprintEndDt'])
    st.info(f"📅 **Current Sprint:** {current_sprint['SprintName']} (Sprint {current_sprint['SprintNumber']}) — {start_dt.strftime('%b %d')} to {end_dt.strftime('%b %d, %Y')}")

if not filtered_df.empty:
    # Use display names if available
    sv_assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in filtered_df.columns else 'AssignedTo'
    
    # Priority dropdown values: blank=not set yet, 0=No longer needed, 1=Lowest to 5=Highest
    PRIORITY_VALUES = ['', 0, 1, 2, 3, 4, 5]
    
    # Use standardized column order from config (backlog order - no sprint detail columns)
    display_order = get_backlog_column_order(sv_assignee_col)
    
    available_cols = [col for col in display_order if col in filtered_df.columns]
    display_df = filtered_df[available_cols].copy()
    
    # Clean subject column (remove LAB-XX: NNNNNN - prefix)
    display_df = clean_subject_column(display_df)
    
    # Mark which rows are editable (open tasks only)
    display_df['_is_open'] = ~display_df['Status'].isin(CLOSED_STATUSES)
    
    # Configure AgGrid with built-in column filtering (click column header menu)
    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_default_column(resizable=True, filterable=True, sortable=True)
    
    # Hidden columns
    gb.configure_column('_TicketGroup', hide=True)
    gb.configure_column('_IsMultiTask', hide=True)
    gb.configure_column('_is_open', hide=True)
    
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
    gb.configure_column(sv_assignee_col, header_name='AssignedTo', width=COLUMN_WIDTHS['AssignedTo'])
    gb.configure_column('Subject', header_name='Subject', width=COLUMN_WIDTHS['Subject'], 
                        tooltipField='Subject')
    gb.configure_column('TicketCreatedDt', header_name='TicketCreatedDt', width=COLUMN_WIDTHS.get('TicketCreatedDt', 110))
    gb.configure_column('TaskCreatedDt', header_name='TaskCreatedDt', width=COLUMN_WIDTHS.get('TaskCreatedDt', 110))
    gb.configure_column('DaysOpen', header_name='DaysOpen', width=COLUMN_WIDTHS['DaysOpen'])
    
    # Priority is editable ONLY for open tasks AND only for users who can edit (not PBIDS Users)
    user_can_edit = can_edit_section()
    if user_can_edit:
        priority_editable = JsCode("""
            function(params) {
                return params.data._is_open === true;
            }
        """)
        gb.configure_column('CustomerPriority', header_name='✏️ CustomerPriority', width=COLUMN_WIDTHS['CustomerPriority'], 
                            editable=priority_editable,
                            cellEditor='agSelectCellEditor',
                            cellEditorParams={'values': PRIORITY_VALUES})
    else:
        # Read-only for PBIDS Users
        gb.configure_column('CustomerPriority', header_name='CustomerPriority', width=COLUMN_WIDTHS['CustomerPriority'])
    gb.configure_column('FinalPriority', header_name='FinalPriority', width=COLUMN_WIDTHS.get('FinalPriority', 100))
    gb.configure_column('GoalType', header_name='GoalType', width=COLUMN_WIDTHS.get('GoalType', 90))
    
    # Dependency, DependencyLead(s), Comments are editable for Section Manager/User
    if user_can_edit:
        # Dependency dropdown values
        DEPENDENCY_VALUES = ['', 'Yes', 'No']
        gb.configure_column('DependencyOn', header_name='✏️ Dependency', width=COLUMN_WIDTHS.get('DependencyOn', 110),
                            editable=priority_editable,
                            cellEditor='agSelectCellEditor',
                            cellEditorParams={'values': DEPENDENCY_VALUES})
        gb.configure_column('DependenciesLead', header_name='✏️ DependencyLead(s)', width=COLUMN_WIDTHS.get('DependenciesLead', 120),
                            editable=priority_editable,
                            tooltipField='DependenciesLead',
                            cellEditor='agLargeTextCellEditor',
                            cellEditorPopup=True,
                            cellEditorParams={'maxLength': 1000, 'rows': 5, 'cols': 40})
        gb.configure_column('Comments', header_name='✏️ Comments', width=COLUMN_WIDTHS['Comments'],
                            editable=priority_editable,
                            tooltipField='Comments',
                            cellEditor='agLargeTextCellEditor',
                            cellEditorPopup=True,
                            cellEditorParams={'maxLength': 2000, 'rows': 5, 'cols': 50})
    else:
        # Read-only for PBIDS Users
        gb.configure_column('DependencyOn', header_name='Dependency', width=COLUMN_WIDTHS.get('DependencyOn', 110))
        gb.configure_column('DependenciesLead', header_name='DependencyLead(s)', width=COLUMN_WIDTHS.get('DependenciesLead', 120),
                            tooltipField='DependenciesLead')
        gb.configure_column('Comments', header_name='Comments', width=COLUMN_WIDTHS['Comments'], tooltipField='Comments')
    gb.configure_column('DependencySecured', header_name='DependencySecured', width=COLUMN_WIDTHS.get('DependencySecured', 130))
    gb.configure_column('HoursEstimated', header_name='HoursEstimated', width=COLUMN_WIDTHS['HoursEstimated'])
    gb.configure_column('TaskHoursSpent', header_name='TaskHoursSpent', width=COLUMN_WIDTHS.get('TaskHoursSpent', 110))
    gb.configure_column('TicketHoursSpent', header_name='TicketHoursSpent', width=COLUMN_WIDTHS.get('TicketHoursSpent', 120))
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
    
    grid_response = AgGrid(
        display_df,
        gridOptions=grid_options,
        height=600,
        theme='streamlit',
        update_mode=GridUpdateMode.VALUE_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False,
        custom_css=get_custom_css(),
        allow_unsafe_jscode=True
    )
    
    # Get edited data
    edited_df = pd.DataFrame(grid_response['data'])
    
    # Save button for priority changes (only for users who can edit)
    st.divider()
    
    if user_can_edit:
        col_save, col_info = st.columns([1, 3])
        
        with col_save:
            if st.button("💾 Save Changes", type="primary", use_container_width=True):
                editable_fields = ['CustomerPriority', 'DependencyOn', 'DependenciesLead', 'Comments']
                
                # Build updates list from edited grid data (only open tasks)
                updates = []
                for _, row in edited_df.iterrows():
                    if pd.notna(row.get('TaskNum')) and row.get('_is_open', True):
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
        
        with col_info:
            st.caption("Editable fields: CustomerPriority, Dependency, DependencyLead(s), Comments. Only open tasks can be edited.")
    else:
        st.caption("🔒 **Read-only view** - PBIDS Users cannot edit task data.")
    
    # Export section - exports current filtered view
    col_export1, col_export2 = st.columns([2, 6])
    
    with col_export1:
        # Export current filtered view
        export_df = edited_df.copy()
        # Remove internal columns from export
        export_cols = [c for c in export_df.columns if not c.startswith('_')]
        export_df = export_df[export_cols]
        
        from datetime import datetime
        excel_data = export_to_excel(export_df, sheet_name="Section View")
        # Use display_sections for filename (defined earlier based on admin selection or user sections)
        section_name = "_".join(display_sections).replace(' ', '_') if display_sections else "all"
        section_name = section_name[:50]  # Limit filename length
        filename = f"section_view_{section_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        
        st.download_button(
            label=f"📥 Export to Excel ({len(export_df)} tasks)",
            data=excel_data,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Export current filtered view to Excel"
        )
    
    with col_export2:
        st.caption("💡 Apply filters above to narrow down data before exporting.")

else:
    st.info("No tasks match the current filters")

# Task breakdown
st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Status Breakdown")
    status_counts = filtered_df['Status'].value_counts()
    
    for status, count in status_counts.items():
        percentage = (count / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
        st.write(f"**{status}**: {count} ({percentage:.0f}%)")

with col2:
    st.subheader("🎯 Priority Breakdown")
    priority_counts = filtered_df['CustomerPriority'].dropna().value_counts().sort_index(ascending=False)
    
    priority_labels = {
        5: '🔴 Critical',
        4: '🟠 High',
        3: '🟡 Medium',
        2: '🟢 Low',
        1: '⚪ Minimal',
        0: '⚫ None'
    }
    
    for priority, count in priority_counts.items():
        percentage = (count / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
        label = priority_labels.get(priority, f'P{priority}')
        st.write(f"**{label}**: {count} ({percentage:.0f}%)")

# At-risk tasks highlight
at_risk_df = filtered_df[
    ((filtered_df['TicketType'] == 'IR') & (filtered_df['DaysOpen'] >= 0.6)) |
    ((filtered_df['TicketType'] == 'SR') & (filtered_df['DaysOpen'] >= 18))
]
if len(at_risk_df) > 0:
    st.divider()
    st.markdown("### At-Risk Tasks")
    st.warning(f"⚠️ {len(at_risk_df)} tasks are at risk of missing TAT")
    
    # Use display names if available
    ar_assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in at_risk_df.columns else 'AssignedTo'
    ar_cols = ['TaskNum', 'Subject', 'DaysOpen', 'TicketType', 'Status', ar_assignee_col]
    ar_cols = [c for c in ar_cols if c in at_risk_df.columns]
    at_risk_display = at_risk_df[ar_cols].copy()
    
    gb_ar = GridOptionsBuilder.from_dataframe(at_risk_display)
    gb_ar.configure_default_column(resizable=True, sortable=True)
    gb_ar.configure_column('Subject', width=180, tooltipField='Subject')
    gb_ar.configure_column(ar_assignee_col, header_name='Assignee', width=120)
    grid_options_ar = gb_ar.build()
    
    AgGrid(
        at_risk_display,
        gridOptions=grid_options_ar,
        height=250,
        theme='streamlit',
        fit_columns_on_grid_load=False,
        custom_css=get_custom_css()
    )

# Help section
with st.expander("About This View"):
    section_display = ", ".join(display_sections) if display_sections else "All Sections"
    viewing_msg = "Viewing all sections (Admin mode)" if user_role == 'Admin' and len(display_sections) > 1 else f"Viewing tasks for **{section_display}**"
    
    if is_pbids_user():
        edit_msg = "This is a read-only view."
    elif is_admin() or user_role in ['Section Manager', 'Section User']:
        edit_msg = "You can edit **CustomerPriority**, **Dependency**, **DependencyLead(s)**, and **Comments** for open tasks."
    else:
        edit_msg = "This is a read-only view."
    
    st.markdown(f"""
    {viewing_msg}
    
    **This page shows all open tasks** (not just sprint-assigned tasks). Section users can set CustomerPriority, and admins can then decide which sprint to assign each task to.
    
    {edit_msg} Use column filters in the table to narrow results. Export buttons available for offline analysis.
    
    **SprintsAssigned Column:** Shows which sprints a task has been assigned to. Empty means not yet assigned to any sprint.
    
    **Priority Levels:** P5 Critical (red) · P4 High (yellow) · P3 and below (default)
    
    **At-Risk Thresholds:** IR ≥ 0.6 days · SR ≥ 18 days
    """)
