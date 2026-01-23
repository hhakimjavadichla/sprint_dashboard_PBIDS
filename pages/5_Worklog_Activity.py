"""
Worklog Activity Report Page
Shows team member activity based on worklog data imported from iTrack.
Displays log frequency and minutes spent per user per day within each sprint.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder
from modules.worklog_store import get_worklog_store
from modules.sprint_calendar import get_sprint_calendar
from modules.section_filter import load_valid_team_members
from utils.name_mapper import apply_name_mapping
from components.auth import require_admin, display_user_info
from utils.grid_styles import apply_grid_styles, get_custom_css
from utils.exporters import export_to_excel, export_to_csv

apply_grid_styles()

st.title("Worklog Activity")
st.caption("_Team member activity tracking based on iTrack worklog data — PIBIDS Team_")

# Require admin access
require_admin("Worklog Activity")
display_user_info()

# Load data
worklog_store = get_worklog_store()
calendar = get_sprint_calendar()
current_sprint = calendar.get_current_sprint()

# Get all worklogs with task info (joined with tasks table for TicketType, Section, etc.)
all_worklogs = worklog_store.get_worklogs_with_task_info()

if all_worklogs.empty:
    st.info("No worklog data available")
    st.markdown("""
    **To view worklog activity:**
    1. Go to **Upload Tasks** page
    2. Upload the iTrack **Worklog export** CSV file
    3. Return here to view activity reports
    """)
    st.page_link("pages/7_Data_Source.py", label="Upload Worklog Data")
    st.stop()

# Summary stats
sprint_totals = worklog_store.get_sprint_totals()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📝 Total Log Entries", len(all_worklogs))
with col2:
    total_minutes = all_worklogs['MinutesSpent'].sum() if 'MinutesSpent' in all_worklogs.columns else 0
    total_hours = total_minutes / 60
    st.metric("⏱️ Total Hours Logged", f"{total_hours:.1f}")
with col3:
    unique_users = all_worklogs['Owner'].nunique() if 'Owner' in all_worklogs.columns else 0
    st.metric("👥 Team Members", unique_users)
with col4:
    if current_sprint:
        st.metric("🎯 Current Sprint", f"Sprint {current_sprint['SprintNumber']}")
    else:
        st.metric("🎯 Current Sprint", "N/A")

st.divider()

# Sprint Item only filter - filter to only tasks assigned to any sprint
sprint_items_only = st.checkbox(
    "Sprint Items Only",
    value=False,
    help="Show only worklogs for tasks assigned to any sprint (excludes tasks not in any sprint)"
)

# Apply Sprint Items Only filter if enabled
if sprint_items_only:
    # Filter to only tasks that have SprintsAssigned (non-empty)
    if 'SprintsAssigned' in all_worklogs.columns:
        all_worklogs = all_worklogs[
            all_worklogs['SprintsAssigned'].notna() & 
            (all_worklogs['SprintsAssigned'].astype(str).str.strip() != '')
        ].copy()

# Daily Activity section (removed By User, Sprint Summary, Raw Data tabs)
st.subheader("Daily Activity by User")
st.caption("Shows log frequency and minutes spent per user per day")

# Derive sprint number from LogDate using sprint calendar
def get_sprint_for_log_date(log_date, calendar):
    """Get sprint number for a given date."""
    if pd.isna(log_date):
        return None
    sprint = calendar.get_sprint_for_date(log_date)
    return sprint['SprintNumber'] if sprint else None

# Add derived SprintNumber based on LogDate
if 'LogDate' in all_worklogs.columns:
    all_worklogs['DerivedSprintNumber'] = all_worklogs['LogDate'].apply(
        lambda x: get_sprint_for_log_date(x, calendar)
    )
else:
    all_worklogs['DerivedSprintNumber'] = None

# Date range filter options - use derived sprint numbers from LogDate
available_sprints = sorted(all_worklogs['DerivedSprintNumber'].dropna().unique(), reverse=True)
available_sprints = [int(s) for s in available_sprints if s and s > 0]

# Get available ticket types and sections
available_ticket_types = ['All'] + sorted(all_worklogs['TicketType'].dropna().unique().tolist())
available_sections = ['All']
if 'Section' in all_worklogs.columns:
    available_sections += sorted(all_worklogs['Section'].dropna().unique().tolist())

# Date range mode selector
date_mode = st.radio(
    "Date Range",
    options=["Sprint", "Custom Range"],
    horizontal=True,
    help="Filter by sprint dates or select a custom date range"
)

col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

if date_mode == "Sprint":
    with col1:
        if available_sprints:
            default_sprint = current_sprint['SprintNumber'] if current_sprint and current_sprint['SprintNumber'] in available_sprints else available_sprints[0]
            selected_sprint = st.selectbox(
                "Select Sprint",
                options=available_sprints,
                index=available_sprints.index(default_sprint) if default_sprint in available_sprints else 0,
                format_func=lambda x: f"Sprint {int(x)}"
            )
        else:
            selected_sprint = None
            st.warning("No sprint data available")
    
    with col2:
        selected_ticket_types = st.multiselect(
            "Ticket Type",
            options=available_ticket_types[1:],  # Exclude 'All' from multiselect
            default=[],
            help="Filter by ticket type (leave empty for all)",
            key="tab1_ticket_type_sprint"
        )
    
    with col3:
        selected_section = st.selectbox(
            "Section",
            options=available_sections,
            index=0,
            help="Filter by lab section",
            key="tab1_section_sprint"
        )
    
    # Get sprint date range
    if selected_sprint:
        sprint_info = calendar.get_sprint_by_number(int(selected_sprint))
        if sprint_info is not None:
            filter_start = pd.to_datetime(sprint_info['SprintStartDt']).date()
            filter_end = pd.to_datetime(sprint_info['SprintEndDt']).date()
        else:
            filter_start = None
            filter_end = None
    else:
        filter_start = None
        filter_end = None
else:
    # Custom date range
    from datetime import date, timedelta
    
    # Default to last 30 days
    default_end = date.today()
    default_start = default_end - timedelta(days=30)
    
    with col1:
        filter_start = st.date_input(
            "Start Date",
            value=default_start,
            help="Select start date for the range"
        )
    
    with col2:
        filter_end = st.date_input(
            "End Date",
            value=default_end,
            help="Select end date for the range"
        )
    
    with col3:
        selected_ticket_types = st.multiselect(
            "Ticket Type",
            options=available_ticket_types[1:],  # Exclude 'All' from multiselect
            default=[],
            help="Filter by ticket type (leave empty for all)",
            key="tab1_ticket_type_custom"
        )
    
    with col4:
        selected_section = st.selectbox(
            "Section",
            options=available_sections,
            index=0,
            help="Filter by lab section",
            key="tab1_section_custom"
        )
    
    selected_sprint = None  # No sprint filter in custom mode

if filter_start and filter_end:
    # Generate all dates in the range
    all_sprint_dates = pd.date_range(start=filter_start, end=filter_end).date.tolist()
    
    # Filter worklogs by date range
    all_worklogs['LogDate'] = pd.to_datetime(all_worklogs['LogDate'])
    sprint_worklogs = all_worklogs[
        (all_worklogs['LogDate'].dt.date >= filter_start) &
        (all_worklogs['LogDate'].dt.date <= filter_end)
    ].copy()
    if selected_ticket_types:
        sprint_worklogs = sprint_worklogs[sprint_worklogs['TicketType'].isin(selected_ticket_types)]
    if selected_section != 'All' and 'Section' in sprint_worklogs.columns:
        sprint_worklogs = sprint_worklogs[sprint_worklogs['Section'] == selected_section]
    
    # Get all team members (including those without activity)
    all_team_members = load_valid_team_members()
    # Create a DataFrame to get display names for all team members
    team_df = pd.DataFrame({'Owner': all_team_members})
    team_df = apply_name_mapping(team_df, 'Owner')
    display_col = 'Owner_Display' if 'Owner_Display' in team_df.columns else 'Owner'
    all_display_names = sorted(team_df[display_col].tolist())
    
    # Create activity summary from filtered worklogs
    if sprint_worklogs.empty:
        # Show empty tables with all team members
        st.markdown("### Work Log Entry Frequency by User & Date")
        st.caption("Number of worklog entries per day")
        filter_parts = []
        if selected_ticket_types:
            filter_parts.append(', '.join(selected_ticket_types))
        if selected_section != 'All':
            filter_parts.append(selected_section)
        filter_msg = f" ({', '.join(filter_parts)})" if filter_parts else ""
        date_range_msg = f"Sprint {int(selected_sprint)}" if selected_sprint else f"{filter_start} to {filter_end}"
        st.info(f"No activity recorded for {date_range_msg}{filter_msg}")
    else:
        # Apply name mapping to filtered worklogs
        sprint_worklogs = apply_name_mapping(sprint_worklogs, 'Owner')
        act_display_col = 'Owner_Display' if 'Owner_Display' in sprint_worklogs.columns else 'Owner'
        
        # Create Date column for grouping
        sprint_worklogs['Date'] = sprint_worklogs['LogDate'].dt.date
        
        # Build filter label for captions
        filter_parts = []
        if selected_ticket_types:
            filter_parts.append(', '.join(selected_ticket_types))
        if selected_section != 'All':
            filter_parts.append(selected_section)
        filter_label = f" (Filtered: {', '.join(filter_parts)})" if filter_parts else ""
        
        # Color legend
        st.markdown("**Color Legend:** Weekends shown in light grey")
        
        # Pivot table: users as rows, dates as columns
        st.markdown("### Work Log Entry Frequency by User & Date")
        st.caption(f"Number of worklog entries per day{filter_label}")
        
        # Create pivot for log count
        log_pivot = sprint_worklogs.pivot_table(
            index=act_display_col,
            columns='Date',
            values='RecordId',
            aggfunc='count',
            fill_value=0
        )
        
        # Reindex to include all team members
        log_pivot = log_pivot.reindex(all_display_names, fill_value=0)
        
        # Reindex columns to include all sprint dates
        if all_sprint_dates:
            log_pivot = log_pivot.reindex(columns=all_sprint_dates, fill_value=0)
        
        # Sort columns (dates) in reverse chronological order
        sorted_dates = sorted(log_pivot.columns, reverse=True)
        log_pivot = log_pivot[sorted_dates]
        
        # Identify weekend columns (Saturday=5, Sunday=6)
        weekend_cols = [d.strftime('%m/%d') for d in sorted_dates if hasattr(d, 'weekday') and d.weekday() >= 5]
        
        # Rename columns to shorter MM/DD format
        log_pivot.columns = [d.strftime('%m/%d') if hasattr(d, 'strftime') else str(d)[-5:] for d in log_pivot.columns]
        
        # Style weekends with light grey
        def highlight_weekends(df, weekend_cols):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            for col in weekend_cols:
                if col in df.columns:
                    styles[col] = 'background-color: #e0e0e0'  # Light grey for weekends
            return styles
        
        st.dataframe(
            log_pivot.style.background_gradient(cmap='Blues', axis=None).apply(
                lambda df: highlight_weekends(df, weekend_cols), axis=None
            ),
            use_container_width=False
        )
        
        st.divider()
        
        # Hours pivot
        st.markdown("### Work Logged Hours by User & Date")
        st.caption(f"Total hours spent per day{filter_label}")
        
        hours_pivot = sprint_worklogs.pivot_table(
            index=act_display_col,
            columns='Date',
            values='MinutesSpent',
            aggfunc='sum',
            fill_value=0
        )
        
        # Convert minutes to hours
        hours_pivot = (hours_pivot / 60).round(1)
        
        # Reindex to include all team members
        hours_pivot = hours_pivot.reindex(all_display_names, fill_value=0)
        
        # Reindex columns to include all sprint dates
        if all_sprint_dates:
            hours_pivot = hours_pivot.reindex(columns=all_sprint_dates, fill_value=0)
        
        # Sort columns (dates) in reverse chronological order
        sorted_dates_hrs = sorted(hours_pivot.columns, reverse=True)
        hours_pivot = hours_pivot[sorted_dates_hrs]
        
        # Identify weekend columns for hours table
        weekend_cols_hrs = [d.strftime('%m/%d') for d in sorted_dates_hrs if hasattr(d, 'weekday') and d.weekday() >= 5]
        
        # Rename columns to shorter MM/DD format
        hours_pivot.columns = [d.strftime('%m/%d') if hasattr(d, 'strftime') else str(d)[-5:] for d in hours_pivot.columns]
        
        # Display hours with green color gradient and weekend highlighting (format to 1 decimal place)
        st.dataframe(
            hours_pivot.style.background_gradient(cmap='Greens', axis=None).apply(
                lambda df: highlight_weekends(df, weekend_cols_hrs), axis=None
            ).format("{:.1f}"),
            use_container_width=False
        )
        
        st.divider()
        
        # Task count pivot - unique tasks worked on per day per person
        st.markdown("### Tasks Worked by User & Date")
        st.caption(f"Number of unique tasks worked on per day (not log entries){filter_label}")
        
        # Count unique tasks per user per date (using already filtered sprint_worklogs)
        task_counts = sprint_worklogs.groupby([act_display_col, 'Date'])['TaskNum'].nunique().reset_index()
        task_counts.columns = [act_display_col, 'Date', 'TaskCount']
        
        # Pivot table
        task_pivot = task_counts.pivot_table(
            index=act_display_col,
            columns='Date',
            values='TaskCount',
            aggfunc='sum',
            fill_value=0
        )
        
        # Reindex to include all team members
        task_pivot = task_pivot.reindex(all_display_names, fill_value=0)
        
        # Reindex columns to include all sprint dates
        if all_sprint_dates:
            task_pivot = task_pivot.reindex(columns=all_sprint_dates, fill_value=0)
        
        # Sort columns (dates) in reverse chronological order
        sorted_dates_tasks = sorted(task_pivot.columns, reverse=True)
        task_pivot = task_pivot[sorted_dates_tasks]
        
        # Identify weekend columns for tasks table
        weekend_cols_tasks = [d.strftime('%m/%d') for d in sorted_dates_tasks if hasattr(d, 'weekday') and d.weekday() >= 5]
        
        # Rename columns to shorter MM/DD format
        task_pivot.columns = [d.strftime('%m/%d') if hasattr(d, 'strftime') else str(d)[-5:] for d in task_pivot.columns]
        
        # Display with orange color gradient and weekend highlighting
        st.dataframe(
            task_pivot.style.background_gradient(cmap='Oranges', axis=None).apply(
                lambda df: highlight_weekends(df, weekend_cols_tasks), axis=None
            ),
            use_container_width=False
        )
        
        # Export
        st.divider()
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            export_df = sprint_worklogs.copy()
            export_df['Hours'] = export_df['MinutesSpent'] / 60
            excel_data = export_to_excel(export_df)
            sprint_label = int(selected_sprint) if selected_sprint else "all"
            st.download_button(
                "📥 Export Excel",
                excel_data,
                f"sprint_{sprint_label}_activity.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

# Footer
st.divider()
st.caption("💡 **Tip:** Upload new worklog data from the **Upload Tasks** page to update this report.")
