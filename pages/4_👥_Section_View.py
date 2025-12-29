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
from components.auth import require_auth, display_user_info, get_user_role, get_user_section
from utils.exporters import export_to_csv, export_to_excel
from utils.grid_styles import apply_grid_styles, get_custom_css, STATUS_CELL_STYLE, PRIORITY_CELL_STYLE, DAYS_OPEN_CELL_STYLE, COLUMN_WIDTHS, fullscreen_toggle, get_grid_height, display_column_help

st.set_page_config(
    page_title="Section View (Prototype)",
    page_icon="🧪",
    layout="wide"
)

# Apply custom tooltip styles
apply_grid_styles()

st.title("Section View")
st.caption("_Prototype — PBIDS Team_")

# Require authentication
require_auth("Section View")

# Display user info
display_user_info()

# Load data from task store
task_store = get_task_store()
sprint_df = task_store.get_current_sprint_tasks()

if sprint_df is None or sprint_df.empty:
    st.warning("⚠️ No active sprint found")
    st.info("No sprint data available. Please contact an administrator.")
    st.stop()

# Get user's section
user_role = get_user_role()
user_section = get_user_section()

# For admins, allow section selection
if user_role == 'Admin':
    st.info("👑 **Admin View**: Select a section to view or see all sections")
    
    sections = sorted(sprint_df['Section'].dropna().unique().tolist())
    selected_section = st.selectbox(
        "Select Section to View",
        ['All Sections'] + sections,
        help="Choose a section to view filtered data"
    )
    
    if selected_section != 'All Sections':
        user_section = selected_section
        sprint_df = filter_by_section(sprint_df, user_section)
else:
    # Section users can only see their own section
    if not user_section:
        st.error("⚠️ No section assigned to your account")
        st.info("Please contact an administrator to assign a section")
        st.stop()
    
    sprint_df = filter_by_section(sprint_df, user_section)
    st.info(f"👁️ Viewing tasks for: **{user_section}**")

st.divider()

# Section summary
if user_section:
    summary = get_section_summary(sprint_df, user_section)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total Tasks",
            summary['total_tasks'],
            help="All tasks assigned to this section"
        )
    
    with col2:
        st.metric(
            "Completed",
            summary['completed'],
            delta=f"{(summary['completed']/summary['total_tasks']*100):.0f}%" if summary['total_tasks'] > 0 else "0%",
            help="Tasks marked as completed"
        )
    
    with col3:
        st.metric(
            "In Progress",
            summary['in_progress'],
            help="Tasks currently being worked on"
        )
    
    with col4:
        st.metric(
            "At Risk",
            summary['at_risk'],
            delta="⚠️" if summary['at_risk'] > 0 else "✅",
            help="Tasks approaching or exceeding TAT"
        )
    
    with col5:
        st.metric(
            "Avg Days Open",
            f"{summary['avg_days_open']:.1f}",
            help="Average age of tasks in this section"
        )
    
    st.divider()
    
    # Team members
    if summary['team_members']:
        st.subheader("👥 Team Members")
        st.write(", ".join(summary['team_members']))
        st.divider()

# Use all tasks (AgGrid has built-in filtering)
filtered_df = sprint_df.copy()

st.caption(f"Showing {len(filtered_df)} tasks")

# Task table - Priority is editable for open tasks
st.markdown("### Tasks")
col_info, col_expand = st.columns([4, 1])
with col_info:
    st.caption("💡 You can edit **Priority** for open tasks. Double-click the Priority cell to change it.")
with col_expand:
    is_fullscreen = fullscreen_toggle("section_view")

# Column descriptions help
display_column_help(title="❓ Column Descriptions")

if not filtered_df.empty:
    # Use display names if available
    sv_assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in filtered_df.columns else 'AssignedTo'
    
    # Priority dropdown values: 0=No longer needed, 1=Lowest to 5=Highest, NotAssigned
    PRIORITY_VALUES = ['NotAssigned', 0, 1, 2, 3, 4, 5]
    
    # Select columns to display (include UniqueTaskId for tracking)
    display_cols = [
        'UniqueTaskId',
        'TaskNum',
        'TicketNum',
        'TicketType',
        'Subject',
        'Status',
        sv_assignee_col,
        'DaysOpen',
        'HoursEstimated',
        'Comments'
    ]
    
    available_cols = [col for col in display_cols if col in filtered_df.columns]
    display_df = filtered_df[available_cols].copy()
    
    # Mark which rows are editable (open tasks only)
    display_df['_is_open'] = ~display_df['Status'].isin(CLOSED_STATUSES)
    
    # Configure AgGrid
    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_default_column(resizable=True, filterable=True, sortable=True)
    gb.configure_column('UniqueTaskId', hide=True)
    gb.configure_column('_is_open', hide=True)
    gb.configure_column('TaskNum', header_name='TaskNum', width=COLUMN_WIDTHS['TaskNum'])
    gb.configure_column('TicketNum', header_name='TicketNum', width=COLUMN_WIDTHS['TicketNum'])
    gb.configure_column('TicketType', header_name='TicketType', width=COLUMN_WIDTHS['TicketType'])
    gb.configure_column('Subject', header_name='Subject', width=COLUMN_WIDTHS['Subject'], tooltipField='Subject')
    gb.configure_column('Status', header_name='Status', width=COLUMN_WIDTHS['Status'])
    gb.configure_column(sv_assignee_col, header_name='AssignedTo', width=COLUMN_WIDTHS['AssignedTo'])
    # Priority is editable ONLY for open tasks (not completed/closed)
    priority_editable = JsCode("""
        function(params) {
            return params.data._is_open === true;
        }
    """)
    gb.configure_column('CustomerPriority', header_name='CustomerPriority', width=COLUMN_WIDTHS['CustomerPriority'], 
                        editable=priority_editable,
                        cellStyle=PRIORITY_CELL_STYLE,
                        cellEditor='agSelectCellEditor',
                        cellEditorParams={'values': PRIORITY_VALUES})
    gb.configure_column('DaysOpen', header_name='DaysOpen', width=COLUMN_WIDTHS['DaysOpen'])
    gb.configure_column('HoursEstimated', header_name='HoursEstimated', width=COLUMN_WIDTHS['HoursEstimated'])
    gb.configure_column('Comments', header_name='Comments', width=COLUMN_WIDTHS['Comments'], tooltipField='Comments')
    gb.configure_pagination(enabled=False)
    
    grid_options = gb.build()
    
    grid_response = AgGrid(
        display_df,
        gridOptions=grid_options,
        height=get_grid_height(is_fullscreen, 600),
        theme='streamlit',
        update_mode=GridUpdateMode.VALUE_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False,
        enable_enterprise_modules=False,
        custom_css=get_custom_css(),
        allow_unsafe_jscode=True
    )
    
    # Get edited data
    edited_df = pd.DataFrame(grid_response['data'])
    
    # Save button for priority changes
    st.divider()
    
    col_save, col_info = st.columns([1, 3])
    
    with col_save:
        if st.button("💾 Save Priority Changes", type="primary", use_container_width=True):
            success_count = 0
            fail_count = 0
            
            for idx, row in edited_df.iterrows():
                unique_id = row.get('UniqueTaskId')
                if pd.isna(unique_id):
                    continue
                
                # Only save if task is open
                if not row.get('_is_open', True):
                    continue
                
                # Get priority value
                priority_val = row.get('CustomerPriority')
                if pd.notna(priority_val):
                    try:
                        mask = task_store.tasks_df['UniqueTaskId'] == unique_id
                        if mask.any():
                            task_store.tasks_df.loc[mask, 'CustomerPriority'] = int(priority_val)
                            success_count += 1
                    except Exception as e:
                        fail_count += 1
            
            if success_count > 0:
                if task_store.save():
                    st.success(f"✅ Updated priority for {success_count} task(s)")
                    st.rerun()
                else:
                    st.error("❌ Failed to save changes")
            elif fail_count > 0:
                st.warning(f"⚠️ Failed to update {fail_count} task(s)")
            else:
                st.info("No changes to save")
    
    with col_info:
        st.caption("Priority: 0=Not needed, 1=Lowest, 5=Highest. Only open tasks can be edited.")
    
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
        section_name = user_section.replace(' ', '_') if user_section else "all"
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
    st.markdown(f"""
    {'Viewing all sections (Admin mode)' if user_role == 'Admin' and not user_section else f'Viewing tasks for **{user_section}**'}
    
    This is a read-only view. Use column filters in the table to narrow results. Export buttons available for offline analysis.
    
    **Priority Levels:** P5 Critical (red) · P4 High (yellow) · P3 and below (default)
    
    **At-Risk Thresholds:** IR ≥ 0.6 days · SR ≥ 18 days
    """)
