"""
Admin Master Dashboard
Full view of all tasks, at-risk items, and capacity
"""
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
from modules.task_store import get_task_store, CLOSED_STATUSES
from modules.sprint_calendar import get_sprint_calendar
from modules.section_filter import apply_section_filters, get_available_sections
from components.auth import require_auth, display_user_info, get_user_role, get_user_section
from components.metrics_dashboard import display_sprint_overview
from components.at_risk_widget import display_at_risk_widget
from components.capacity_widget import display_capacity_summary
from utils.exporters import export_to_csv, export_to_excel
from utils.grid_styles import apply_grid_styles, get_custom_css, STATUS_CELL_STYLE, PRIORITY_CELL_STYLE, DAYS_OPEN_CELL_STYLE

st.set_page_config(
    page_title="Dashboard (Prototype)",
    page_icon="🧪",
    layout="wide"
)

# Apply custom tooltip styles
apply_grid_styles()

st.title("Sprint Dashboard")
st.caption("_Prototype — PBIDS Team_")

# Require authentication
require_auth("Dashboard")

# Display user info in sidebar
display_user_info()

# Load data from task store
task_store = get_task_store()
calendar = get_sprint_calendar()

# Get current sprint tasks (includes carryover from all previous sprints)
sprint_df = task_store.get_current_sprint_tasks()
current_sprint = calendar.get_current_sprint()

if sprint_df is None or sprint_df.empty:
    st.warning("⚠️ No tasks in current sprint")
    st.info("Upload tasks to view the dashboard")
    if get_user_role() == 'Admin':
        st.page_link("pages/2_📤_Upload_Tasks.py", label="📤 Upload Tasks", icon="📤")
    st.stop()

# Sprint header
if current_sprint:
    sprint_num = current_sprint['SprintNumber']
    sprint_name = current_sprint['SprintName']
    st.subheader(f"{sprint_name} (Sprint #{sprint_num})")
    st.caption(f"📅 {current_sprint['SprintStartDt'].strftime('%Y-%m-%d')} to {current_sprint['SprintEndDt'].strftime('%Y-%m-%d')}")
    
    # Show carryover info
    if 'IsCarryover' in sprint_df.columns:
        carryover_count = int(sprint_df['IsCarryover'].sum())
        original_count = len(sprint_df) - carryover_count
        st.caption(f"📊 {original_count} original tasks + {carryover_count} carryover from previous sprints")
else:
    sprint_num = sprint_df['SprintNumber'].iloc[0] if 'SprintNumber' in sprint_df.columns else 0
    sprint_name = f"Sprint {sprint_num}"
    st.subheader(sprint_name)

# Filter for section users
user_role = get_user_role()
if user_role != 'Admin':
    user_section = get_user_section()
    if user_section:
        sprint_df = sprint_df[sprint_df['Section'] == user_section]
        st.info(f"👁️ Viewing tasks for: **{user_section}**")

# Overview metrics
display_sprint_overview(sprint_df)

st.divider()

# Sidebar filters
with st.sidebar:
    st.subheader("🔍 Filters")
    
    # Section filter (Admin only)
    if user_role == 'Admin':
        sections = ['All'] + get_available_sections(sprint_df)
        selected_sections = st.multiselect(
            "Section",
            sections,
            default=['All'],
            help="Filter by lab section"
        )
    else:
        selected_sections = ['All']
    
    # Status filter
    all_statuses = ['All'] + sorted(sprint_df['Status'].unique().tolist())
    selected_statuses = st.multiselect(
        "Status",
        all_statuses,
        default=['All'],
        help="Filter by task status"
        )
    
    # Priority filter
    priority_range = st.slider(
        "Priority Range",
        0, 5, (0, 5),
        help="Filter by customer priority"
    )
    
    # Assignee filter - use display names
    dash_assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in sprint_df.columns else 'AssignedTo'
    all_assignees = ['All'] + sorted(sprint_df[dash_assignee_col].dropna().unique().tolist())
    selected_assignees = st.multiselect(
        "Assigned To",
        all_assignees,
        default=['All'],
        help="Filter by assignee"
    )
    
    # Show only at-risk
    show_at_risk = st.checkbox(
        "Show only at-risk tasks",
        help="Tasks approaching or exceeding TAT"
    )
    
    # Show only unestimated
    show_unestimated = st.checkbox(
        "Show only tasks without effort estimate"
    )

# Apply filters
filtered_df = apply_section_filters(
    sprint_df,
    sections=selected_sections if 'All' not in selected_sections else None,
    status=selected_statuses if 'All' not in selected_statuses else None,
    priority_range=priority_range,
    assigned_to=selected_assignees if 'All' not in selected_assignees else None
)

# At-risk filter
if show_at_risk:
    filtered_df = filtered_df[
        ((filtered_df['TicketType'] == 'IR') & (filtered_df['DaysOpen'] >= 0.6)) |
        ((filtered_df['TicketType'] == 'SR') & (filtered_df['DaysOpen'] >= 18))
    ]

# Unestimated filter
if show_unestimated:
    filtered_df = filtered_df[filtered_df['HoursEstimated'].isna()]

st.caption(f"Showing {len(filtered_df)} of {len(sprint_df)} tasks")

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["All Tasks", "At Risk", "Capacity"])

with tab1:
    
    # Task table
    if not filtered_df.empty:
        # Select columns to display - use display name for assignee
        display_cols = [
            'TaskNum', 'TicketNum', 'TicketType', 'Subject',
            'Status', dash_assignee_col,
            'DaysOpen', 'Section', 'HoursEstimated'
        ]
        
        available_cols = [col for col in display_cols if col in filtered_df.columns]
        display_df = filtered_df[available_cols].copy()
        
        # Configure AgGrid
        gb = GridOptionsBuilder.from_dataframe(display_df)
        gb.configure_default_column(resizable=True, filterable=True, sortable=True)
        gb.configure_column('TaskNum', header_name='Task #', width=90)
        gb.configure_column('TicketNum', header_name='Ticket #', width=100)
        gb.configure_column('TicketType', header_name='Type', width=60)
        gb.configure_column('Subject', width=180, tooltipField='Subject')
        gb.configure_column('Status', width=100, cellStyle=STATUS_CELL_STYLE)
        gb.configure_column(dash_assignee_col, header_name='Assignee', width=120)
        gb.configure_column('DaysOpen', header_name='Days Open', width=80, cellStyle=DAYS_OPEN_CELL_STYLE)
        gb.configure_column('Section', width=80)
        gb.configure_column('HoursEstimated', header_name='Est. Hours', width=90)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=100)
        
        grid_options = gb.build()
        
        AgGrid(
            display_df,
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
        
        with col1:
            csv_data = export_to_csv(filtered_df)
            st.download_button(
                "📥 Export CSV",
                csv_data,
                f"sprint_{sprint_num}_tasks.csv",
                "text/csv",
                width="stretch"
            )
        
        with col2:
            excel_data = export_to_excel(filtered_df)
            st.download_button(
                "📥 Export Excel",
                excel_data,
                f"sprint_{sprint_num}_tasks.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch"
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

col1, col2, col3, col4 = st.columns(4)

with col1:
    priority_5 = len(filtered_df[filtered_df['CustomerPriority'] == 5])
    st.metric("Priority 5 Tasks", priority_5)

with col2:
    ir_count = len(filtered_df[filtered_df['TicketType'] == 'IR'])
    st.metric("Incident Request (IR)", ir_count)

with col3:
    sr_count = len(filtered_df[filtered_df['TicketType'] == 'SR'])
    st.metric("Service Request (SR)", sr_count)

with col4:
    unassigned = len(filtered_df[filtered_df['AssignedTo'].isna() | (filtered_df['AssignedTo'] == '')])
    st.metric("Unassigned", unassigned)
