"""
Dashboard Page
Full view of ALL tasks with comprehensive filtering options.
Shows all tasks (open or closed, with or without sprint assignment).
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from modules.task_store import get_task_store, CLOSED_STATUSES
from modules.section_filter import exclude_forever_tickets, exclude_ad_tickets
from modules.sprint_calendar import get_sprint_calendar
from components.auth import require_auth, display_user_info, get_user_role, get_user_section
from components.metrics_dashboard import display_ticket_task_metrics
from components.at_risk_widget import display_at_risk_widget
from components.capacity_widget import display_capacity_summary
from utils.exporters import export_to_csv, export_to_excel
from utils.grid_styles import apply_grid_styles, get_custom_css, STATUS_CELL_STYLE, PRIORITY_CELL_STYLE, DAYS_OPEN_CELL_STYLE, get_backlog_column_order, COLUMN_WIDTHS, clean_subject_column

# Apply custom tooltip styles
apply_grid_styles()

st.title("Overview")
st.caption("_All Tasks Overview — PIBIDS Team_")

# Require authentication
require_auth("Dashboard")

# Display user info in sidebar
display_user_info()

# Load data from task store
task_store = get_task_store()
calendar = get_sprint_calendar()

# Get ALL tasks (not just current sprint)
all_tasks = task_store.get_all_tasks()

if all_tasks is None or all_tasks.empty:
    st.warning("⚠️ No tasks in the system")
    st.info("Upload tasks to view the dashboard")
    if get_user_role() == 'Admin':
        st.page_link("pages/7_Data_Source.py", label="Upload Tasks")
    st.stop()

# Get sprint calendar for filters
all_sprints = calendar.get_all_sprints()
current_sprint = calendar.get_current_sprint()

# Filter for section users (non-admins only see their section)
user_role = get_user_role()
if user_role != 'Admin':
    user_section = get_user_section()
    if user_section:
        # Handle comma-separated sections
        if ',' in str(user_section):
            user_sections = [s.strip() for s in user_section.split(',')]
            all_tasks = all_tasks[all_tasks['Section'].isin(user_sections)]
        else:
            all_tasks = all_tasks[all_tasks['Section'] == user_section]
        st.info(f"👁️ Viewing tasks for: **{user_section}**")

# ============================================================================
# FILTERS - At the top of the page
# ============================================================================
st.markdown("### Filters")

# Row 1: Sprint and Date filters
col1, col2, col3, col4 = st.columns(4)

with col1:
    # Sprint filter mode
    filter_mode = st.radio(
        "Filter by",
        ["All Tasks", "Sprint", "Custom Date Range"],
        horizontal=True,
        help="Choose how to filter tasks"
    )

with col2:
    if filter_mode == "Sprint":
        # Build sprint options
        sprint_options = ["All Sprints"]
        if not all_sprints.empty:
            for _, row in all_sprints.iterrows():
                sprint_num = int(row['SprintNumber'])
                label = f"Sprint {sprint_num}: {row['SprintName']}"
                sprint_options.append(label)
        
        selected_sprint_label = st.selectbox(
            "Select Sprint",
            sprint_options,
            index=0
        )
    else:
        selected_sprint_label = None
        st.empty()

with col3:
    if filter_mode == "Custom Date Range":
        # Get min/max dates from tasks
        min_date = pd.to_datetime(all_tasks['TaskCreatedDt'], errors='coerce').min()
        max_date = datetime.now()
        
        if pd.isna(min_date):
            min_date = datetime.now() - timedelta(days=365)
        
        start_date = st.date_input(
            "Start Date",
            value=min_date.date() if hasattr(min_date, 'date') else min_date,
            help="Filter tasks created on or after this date"
        )
    else:
        start_date = None
        st.empty()

with col4:
    if filter_mode == "Custom Date Range":
        end_date = st.date_input(
            "End Date",
            value=datetime.now().date(),
            help="Filter tasks created on or before this date"
        )
    else:
        end_date = None
        st.empty()

# Row 2: Section, Ticket Type, Status filters
col1, col2, col3, col4 = st.columns(4)

with col1:
    # Section filter (multi-select)
    available_sections = sorted(all_tasks['Section'].dropna().unique().tolist()) if 'Section' in all_tasks.columns else []
    selected_sections = st.multiselect(
        "Section",
        available_sections,
        default=[],
        help="Filter by lab section (leave empty for all)"
    )

with col2:
    # Ticket Type filter
    ticket_types = ['SR', 'PR', 'IR', 'NC', 'AD']
    available_types = [t for t in ticket_types if t in all_tasks['TicketType'].unique()] if 'TicketType' in all_tasks.columns else []
    selected_types = st.multiselect(
        "Ticket Type",
        available_types,
        default=[],
        help="Filter by ticket type (leave empty for all)"
    )

with col3:
    # Status filter
    available_statuses = sorted(all_tasks['TaskStatus'].dropna().unique().tolist()) if 'TaskStatus' in all_tasks.columns else []
    selected_statuses = st.multiselect(
        "Status",
        available_statuses,
        default=[],
        help="Filter by task status (leave empty for all)"
    )

with col4:
    # Assignee filter
    assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in all_tasks.columns else 'AssignedTo'
    available_assignees = sorted(all_tasks[assignee_col].dropna().unique().tolist()) if assignee_col in all_tasks.columns else []
    selected_assignees = st.multiselect(
        "Assigned To",
        available_assignees,
        default=[],
        help="Filter by assignee (leave empty for all)"
    )

# Row 3: Additional options
col1, col2, col3, col4 = st.columns(4)
with col1:
    exclude_forever = st.checkbox(
        "Exclude Forever Tickets",
        value=False,
        help="Hide Standing Meetings and Miscellaneous Meetings tasks"
    )
with col2:
    exclude_ad = st.checkbox(
        "Exclude AD Tickets",
        value=False,
        help="Hide Admin Request (AD) tickets"
    )

st.divider()

# ============================================================================
# APPLY FILTERS
# ============================================================================
filtered_df = all_tasks.copy()

# Apply sprint/date filter
if filter_mode == "Sprint" and selected_sprint_label and selected_sprint_label != "All Sprints":
    # Extract sprint number from label
    sprint_num = int(selected_sprint_label.split(":")[0].replace("Sprint ", ""))
    # Filter by SprintsAssigned containing this sprint number
    if 'SprintsAssigned' in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df['SprintsAssigned'].apply(
                lambda x: str(sprint_num) in str(x).split(', ') if pd.notna(x) and x != '' else False
            )
        ]
    elif 'SprintNumber' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['SprintNumber'] == sprint_num]

elif filter_mode == "Custom Date Range" and start_date and end_date:
    # Filter by TaskCreatedDt
    if 'TaskCreatedDt' in filtered_df.columns:
        filtered_df['_task_date'] = pd.to_datetime(filtered_df['TaskCreatedDt'], errors='coerce').dt.date
        filtered_df = filtered_df[
            (filtered_df['_task_date'] >= start_date) & 
            (filtered_df['_task_date'] <= end_date)
        ]
        filtered_df = filtered_df.drop(columns=['_task_date'])

# Apply section filter
if selected_sections:
    filtered_df = filtered_df[filtered_df['Section'].isin(selected_sections)]

# Apply ticket type filter
if selected_types:
    filtered_df = filtered_df[filtered_df['TicketType'].isin(selected_types)]

# Apply status filter
if selected_statuses:
    filtered_df = filtered_df[filtered_df['TaskStatus'].isin(selected_statuses)]

# Apply assignee filter
if selected_assignees:
    filtered_df = filtered_df[filtered_df[assignee_col].isin(selected_assignees)]

# Apply forever tickets filter
if exclude_forever:
    filtered_df = exclude_forever_tickets(filtered_df)

# Apply AD tickets filter
if exclude_ad:
    filtered_df = exclude_ad_tickets(filtered_df)

# ============================================================================
# METRICS
# ============================================================================
# Pass exclude_forever flag to metrics - if user excluded them, don't double-exclude
display_ticket_task_metrics(filtered_df, exclude_forever_internally=not exclude_forever)

st.divider()

# ============================================================================
# TASK TABLE
# ============================================================================
filter_notes = []
if exclude_forever:
    filter_notes.append("forever tickets excluded")
if exclude_ad:
    filter_notes.append("AD tickets excluded")

if filter_notes:
    st.caption(f"📋 Showing **{len(filtered_df)}** tasks ({', '.join(filter_notes)})")
else:
    st.caption(f"📋 Showing **{len(filtered_df)}** tasks (of **{len(all_tasks)}** total)")

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["📋 All Tasks", "⚠️ At Risk", "📊 Capacity"])

with tab1:
    if not filtered_df.empty:
        # Prepare display dataframe with ticket grouping for color-coding
        display_df = filtered_df.copy()
        
        # Add ticket grouping for row banding (color-coded by ticket)
        if 'TicketNum' in display_df.columns:
            # Count tasks per ticket
            ticket_counts = display_df.groupby('TicketNum').size().to_dict()
            
            # Sort by TicketNum to group tasks from same ticket together
            display_df = display_df.sort_values(
                by=['TicketNum', 'TaskNum'],
                ascending=[True, True],
                na_position='last'
            ).reset_index(drop=True)
            
            # Track ticket groups for row banding
            ticket_group_ids = []
            current_group = 0
            prev_ticket = None
            
            for idx, row in display_df.iterrows():
                ticket = row['TicketNum']
                if ticket != prev_ticket:
                    current_group += 1
                    prev_ticket = ticket
                ticket_group_ids.append(current_group)
            
            display_df['_TicketGroup'] = ticket_group_ids
            display_df['_IsMultiTask'] = display_df['TicketNum'].map(lambda x: ticket_counts.get(x, 1) > 1)
        
        # Use standardized column order from config (backlog order - no sprint detail columns)
        display_cols = get_backlog_column_order(assignee_col)
        
        available_cols = [col for col in display_cols if col in display_df.columns]
        grid_df = display_df[available_cols].copy()
        
        # Clean subject column (remove LAB-XX: NNNNNN - prefix)
        grid_df = clean_subject_column(grid_df)
        
        # Show task count in table
        st.caption(f"Table contains **{len(grid_df)}** tasks")
        
        # Configure AgGrid
        gb = GridOptionsBuilder.from_dataframe(grid_df)
        gb.configure_default_column(resizable=True, filterable=True, sortable=True)
        
        # Hidden columns for row styling
        if '_TicketGroup' in grid_df.columns:
            gb.configure_column('_TicketGroup', hide=True)
        if '_IsMultiTask' in grid_df.columns:
            gb.configure_column('_IsMultiTask', hide=True)
        
        gb.configure_column('TaskNum', header_name='Task #', width=100)
        gb.configure_column('TicketNum', header_name='Ticket #', width=100)
        gb.configure_column('TicketType', header_name='Type', width=60)
        gb.configure_column('Subject', width=200, tooltipField='Subject')
        gb.configure_column('TaskStatus', width=100)
        if 'TicketStatus' in available_cols:
            gb.configure_column('TicketStatus', header_name='Ticket Status', width=100)
        gb.configure_column(assignee_col, header_name='Assignee', width=120)
        gb.configure_column('DaysOpen', header_name='Days Open', width=80)
        gb.configure_column('Section', width=80)
        if 'SprintsAssigned' in available_cols:
            gb.configure_column('SprintsAssigned', header_name='Sprints', width=100)
        gb.configure_column('HoursEstimated', header_name='Est. Hours', width=90)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=500)
        
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
        
        AgGrid(
            grid_df,
            gridOptions=grid_options,
            height=600,
            theme='streamlit',
            fit_columns_on_grid_load=False,
            enable_enterprise_modules=False,
            custom_css=get_custom_css(),
            allow_unsafe_jscode=True
        )
        
        # Export options
        col1, col2, col3 = st.columns([1, 1, 4])
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with col1:
            csv_data = export_to_csv(filtered_df)
            st.download_button(
                "📥 Export CSV",
                csv_data,
                f"dashboard_tasks_{timestamp}.csv",
                "text/csv"
            )
        
        with col2:
            excel_data = export_to_excel(filtered_df)
            st.download_button(
                "📥 Export Excel",
                excel_data,
                f"dashboard_tasks_{timestamp}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("No tasks match the current filters")

with tab2:
    display_at_risk_widget(filtered_df, detailed=True)

with tab3:
    if user_role == 'Admin':
        display_capacity_summary(filtered_df, detailed=True)
    else:
        st.info("Capacity view is available for administrators only")

# Quick stats at bottom
st.divider()

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    open_count = len(filtered_df[~filtered_df['TaskStatus'].isin(CLOSED_STATUSES)])
    st.metric("Open Tasks", open_count)

with col2:
    closed_count = len(filtered_df[filtered_df['TaskStatus'].isin(CLOSED_STATUSES)])
    st.metric("Closed Tasks", closed_count)

with col3:
    priority_5 = len(filtered_df[filtered_df['CustomerPriority'] == 5])
    st.metric("Priority 5 (Critical)", priority_5)

with col4:
    ir_count = len(filtered_df[filtered_df['TicketType'] == 'IR'])
    st.metric("Incident Requests", ir_count)

with col5:
    no_sprint = len(filtered_df[
        (filtered_df['SprintsAssigned'].isna()) | 
        (filtered_df['SprintsAssigned'] == '')
    ]) if 'SprintsAssigned' in filtered_df.columns else 0
    st.metric("No Sprint Assigned", no_sprint)
