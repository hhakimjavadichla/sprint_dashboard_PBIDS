"""
Reports & Analytics Page
Comprehensive reports and visualizations for PIBIDS sprint data
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Tuple, List, Optional

from modules.task_store import get_task_store
from modules.sprint_calendar import SprintCalendar, format_sprint_display
from modules.section_filter import (
    load_valid_team_members,
    exclude_ad_tickets,
    exclude_forever_tickets
)
from modules.worklog_store import get_worklog_store
from modules.offdays_store import get_offdays_store
from components.auth import require_team_member, display_user_info, get_user_role

from utils.constants import (
    OPEN_TASK_STATUSES,
    CLOSED_TASK_STATUSES,
    VALID_SECTIONS,
    TICKET_TYPES
)
from utils.name_mapper import get_display_name

st.title("📊 Reports & Analytics")

# Require team member access (Admin or PIBIDS User)
require_team_member("Reports & Analytics")
display_user_info()


# =============================================================================
# SHARED FILTER COMPONENTS
# =============================================================================

def render_time_window_filter(key_prefix: str = "tw") -> Tuple[str, Optional[int], Optional[datetime], Optional[datetime]]:
    """
    Render time window filter (Sprint OR Date Range - mutually exclusive)
    Compact single-row layout.
    
    Returns:
        Tuple of (filter_type, sprint_number, start_date, end_date)
    """
    calendar = SprintCalendar()
    all_sprints = calendar.get_all_sprints()
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    sprint_number = None
    start_date = None
    end_date = None
    
    with col1:
        filter_type = st.radio(
            "Time Window",
            options=["Sprint", "Date Range"],
            key=f"{key_prefix}_filter_type",
            horizontal=True,
            label_visibility="collapsed"
        )
    
    if filter_type == "Sprint":
        if all_sprints.empty:
            with col2:
                st.warning("No sprints defined")
        else:
            # Sort sprints by date to find current/previous sprint
            sprints_sorted = all_sprints.copy()
            sprints_sorted['SprintStartDt'] = pd.to_datetime(sprints_sorted['SprintStartDt'])
            sprints_sorted['SprintEndDt'] = pd.to_datetime(sprints_sorted['SprintEndDt'])
            sprints_sorted = sprints_sorted.sort_values('SprintStartDt')
            
            sprint_options = all_sprints['SprintNumber'].tolist()
            sprint_labels = [
                format_sprint_display(row['SprintName'], row['SprintStartDt'], row['SprintEndDt'], int(row['SprintNumber']))
                for _, row in all_sprints.iterrows()
            ]
            
            # Find previous sprint based on dates
            today = pd.Timestamp.now().normalize()
            previous_sprint_num = None
            
            # Find current sprint (contains today or most recent past sprint)
            current_sprint_idx = None
            for i, (_, sprint) in enumerate(sprints_sorted.iterrows()):
                if sprint['SprintStartDt'] <= today <= sprint['SprintEndDt']:
                    current_sprint_idx = i
                    break
                elif sprint['SprintEndDt'] < today:
                    current_sprint_idx = i  # Keep updating to most recent past sprint
            
            # Previous sprint is the one before current
            if current_sprint_idx is not None and current_sprint_idx > 0:
                previous_sprint_num = sprints_sorted.iloc[current_sprint_idx - 1]['SprintNumber']
            elif current_sprint_idx == 0:
                # Current is first sprint, use it as default
                previous_sprint_num = sprints_sorted.iloc[0]['SprintNumber']
            else:
                # Fallback to first sprint
                previous_sprint_num = sprints_sorted.iloc[0]['SprintNumber']
            
            # Find index of previous sprint in original list
            default_idx = 0
            for i, snum in enumerate(sprint_options):
                if snum == previous_sprint_num:
                    default_idx = i
                    break
            
            with col2:
                selected_label = st.selectbox(
                    "Sprint",
                    options=sprint_labels,
                    index=default_idx,
                    key=f"{key_prefix}_sprint_select",
                    label_visibility="collapsed"
                )
            
            selected_idx = sprint_labels.index(selected_label)
            sprint_number = sprint_options[selected_idx]
            
            sprint_info = calendar.get_sprint_by_number(sprint_number)
            if sprint_info:
                start_date = sprint_info['SprintStartDt']
                end_date = sprint_info['SprintEndDt']
    else:
        with col2:
            start_date = st.date_input(
                "From",
                value=datetime.now() - timedelta(days=30),
                key=f"{key_prefix}_start_date",
                label_visibility="collapsed"
            )
        with col3:
            end_date = st.date_input(
                "To",
                value=datetime.now(),
                key=f"{key_prefix}_end_date",
                label_visibility="collapsed"
            )
        
        start_date = datetime.combine(start_date, datetime.min.time())
        end_date = datetime.combine(end_date, datetime.max.time())
    
    return (filter_type.lower().replace(" ", ""), sprint_number, start_date, end_date)


def render_section_filter(key_prefix: str = "sec", multi: bool = True) -> Tuple[List[str], List[str]]:
    """
    Render lab section filter with empty default (meaning All)
    
    Returns:
        Tuple of (selected_sections, all_sections)
        If selected is empty, caller should treat as "All"
    """
    # Exclude PIBIDS from section filter - it's an internal team name, not an iTrack section
    sections = [s for s in VALID_SECTIONS if s != "PIBIDS"] if VALID_SECTIONS else []
    
    if not sections:
        task_store = get_task_store()
        all_tasks = task_store.get_all_tasks()
        if not all_tasks.empty and 'Section' in all_tasks.columns:
            sections = sorted([s for s in all_tasks['Section'].dropna().unique().tolist() if s != "PIBIDS"])
    
    if multi:
        selected = st.multiselect(
            "Lab Section(s)",
            options=sections,
            default=[],
            key=f"{key_prefix}_sections",
            placeholder="All sections"
        )
    else:
        selected = st.selectbox(
            "Lab Section",
            options=["All"] + sections,
            key=f"{key_prefix}_section"
        )
        selected = [] if selected == "All" else [selected]
    
    return (selected if selected else sections, sections)


def render_team_member_filter(key_prefix: str = "tm") -> Tuple[List[str], List[str]]:
    """
    Render team member filter with empty default (meaning All)
    
    Returns:
        Tuple of (selected_members, all_members)
        If selected is empty, caller should treat as "All"
    """
    team_members = load_valid_team_members()
    
    if not team_members:
        st.caption("No team members configured")
        return ([], [])
    
    selected = st.multiselect(
        "Team Member(s)",
        options=team_members,
        default=[],
        key=f"{key_prefix}_members",
        placeholder="All team members"
    )
    
    return (selected if selected else team_members, team_members)


def render_status_filter(key_prefix: str = "st") -> Tuple[List[str], List[str]]:
    """
    Render task status filter with empty default (meaning All)
    
    Returns:
        Tuple of (selected_statuses, all_statuses)
        If selected is empty, caller should treat as "All"
    """
    all_statuses = OPEN_TASK_STATUSES + CLOSED_TASK_STATUSES
    
    selected = st.multiselect(
        "Task Status",
        options=all_statuses,
        default=[],
        key=f"{key_prefix}_statuses",
        placeholder="All statuses"
    )
    
    return (selected if selected else all_statuses, all_statuses)


def render_ad_ticket_toggle(key_prefix: str = "ad") -> bool:
    """
    Render toggle to include/exclude AD tickets
    
    Returns:
        True if AD tickets should be included
    """
    return st.checkbox(
        "Include AD (Admin) tickets",
        value=False,
        key=f"{key_prefix}_include_ad"
    )


# =============================================================================
# DATA LOADING HELPERS
# =============================================================================

def load_filtered_tasks(
    start_date: datetime,
    end_date: datetime,
    sections: List[str] = None,
    team_members: List[str] = None,
    statuses: List[str] = None,
    include_ad: bool = False
) -> pd.DataFrame:
    """
    Load and filter tasks based on criteria
    """
    task_store = get_task_store()
    df = task_store.get_all_tasks()
    
    if df.empty:
        return df
    
    # Ensure date column exists and filter by creation date
    if 'TaskCreatedDt' in df.columns:
        df['TaskCreatedDt'] = pd.to_datetime(df['TaskCreatedDt'], errors='coerce')
        df = df[
            (df['TaskCreatedDt'] >= start_date) &
            (df['TaskCreatedDt'] <= end_date)
        ]
    
    # Filter by sections
    if sections and 'Section' in df.columns:
        df = df[df['Section'].isin(sections)]
    
    # Filter by team members
    if team_members and 'AssignedTo' in df.columns:
        df = df[df['AssignedTo'].isin(team_members)]
    
    # Filter by status
    if statuses and 'TaskStatus' in df.columns:
        df = df[df['TaskStatus'].isin(statuses)]
    
    # Exclude AD tickets unless specified
    if not include_ad:
        df = exclude_ad_tickets(df)
    
    # Exclude forever tickets
    df = exclude_forever_tickets(df)
    
    return df


# =============================================================================
# MAIN PAGE - TABS
# =============================================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Tickets & Tasks Count",
    "Tickets & Tasks Status",
    "Efforts by Lab Section",
    "Effort Distribution by Team",
    "Task Completion Rate"
])


# =============================================================================
# TAB 1: TICKETS & TASKS COUNT
# =============================================================================

with tab1:
    st.subheader("Tickets & Tasks Count by Lab Section")
    st.caption("Count of tickets and tasks per lab section, broken down by ticket type")
    
    # Filters - compact layout
    with st.expander("Filters", expanded=True):
        # Row 1: Time Window (compact single line)
        tw_type, tw_sprint, tw_start, tw_end = render_time_window_filter("t1_tw")
        
        # Row 2: Section, Team Members, Status
        row2_cols = st.columns(3)
        with row2_cols[0]:
            t1_sections, _ = render_section_filter("t1_sec")
        with row2_cols[1]:
            t1_members, _ = render_team_member_filter("t1_tm")
        with row2_cols[2]:
            t1_statuses, _ = render_status_filter("t1_st")
        
        # Row 3: Options
        t1_include_ad = render_ad_ticket_toggle("t1_ad")
    
    # Calculation explanation
    with st.expander("How are these numbers calculated?", expanded=False):
        st.markdown("""
        **Chart: Tickets & Tasks Count by Lab Section**
        
        - **Data Source**: Tasks table filtered by sprint/date range
        - **Count Method**: Each task is counted once per Lab Section
        - **Stacking**: Bars are stacked by Ticket Type (IR, SR, PR, NC, AD)
        - **Filters Applied**:
            - Time Window: Tasks assigned to selected sprint OR within date range
            - Lab Section: Only tasks from selected sections
            - Team Members: Only tasks assigned to selected members
            - Task Status: Only tasks with selected statuses
            - AD Tickets: Included/excluded based on toggle
        """)
    
    # Load and filter data
    if tw_start and tw_end:
        df = load_filtered_tasks(
            start_date=tw_start,
            end_date=tw_end,
            sections=t1_sections,
            team_members=t1_members,
            statuses=t1_statuses,
            include_ad=t1_include_ad
        )
        
        if df.empty:
            st.warning("No data available for the selected filters.")
        else:
            # Ensure TicketType column exists
            if 'TicketType' not in df.columns:
                st.warning("TicketType column not found in data.")
            else:
                # Chart 1a: Tickets by Lab Section
                st.markdown("#### Tickets by Lab Section")
                
                # Count unique tickets per section and type
                ticket_counts = df.groupby(['Section', 'TicketType'])['TicketNum'].nunique().reset_index()
                ticket_counts.columns = ['Section', 'TicketType', 'Count']
                
                if not ticket_counts.empty:
                    fig_tickets = px.bar(
                        ticket_counts,
                        x='Section',
                        y='Count',
                        color='TicketType',
                        title='Tickets by Lab Section',
                        labels={'Count': 'Number of Tickets', 'Section': 'Lab Section'},
                        barmode='stack',
                        color_discrete_sequence=px.colors.qualitative.Set2
                    )
                    fig_tickets.update_layout(
                        xaxis_tickangle=-45,
                        legend_title_text='Ticket Type',
                        height=450
                    )
                    st.plotly_chart(fig_tickets, use_container_width=True)
                    
                    # Summary metrics
                    total_tickets = ticket_counts['Count'].sum()
                    st.caption(f"**Total Tickets:** {total_tickets}")
                else:
                    st.info("No ticket data to display.")
                
                st.divider()
                
                # Chart 1b: Tasks by Lab Section
                st.markdown("#### 📝 Tasks by Lab Section")
                
                # Count tasks per section and type
                task_counts = df.groupby(['Section', 'TicketType'])['TaskNum'].nunique().reset_index()
                task_counts.columns = ['Section', 'TicketType', 'Count']
                
                if not task_counts.empty:
                    fig_tasks = px.bar(
                        task_counts,
                        x='Section',
                        y='Count',
                        color='TicketType',
                        title='Tasks by Lab Section',
                        labels={'Count': 'Number of Tasks', 'Section': 'Lab Section'},
                        barmode='stack',
                        color_discrete_sequence=px.colors.qualitative.Set2
                    )
                    fig_tasks.update_layout(
                        xaxis_tickangle=-45,
                        legend_title_text='Ticket Type',
                        height=450
                    )
                    st.plotly_chart(fig_tasks, use_container_width=True)
                    
                    # Summary metrics
                    total_tasks = task_counts['Count'].sum()
                    st.caption(f"**Total Tasks:** {total_tasks}")
                else:
                    st.info("No task data to display.")
    else:
        st.warning("Please select a valid time window.")


# =============================================================================
# TAB 2: TICKETS & TASKS STATUS
# =============================================================================

with tab2:
    st.subheader("Tickets & Tasks Status")
    st.caption("Open vs Completed items by lab section")
    
    # Filters - compact layout
    with st.expander("Filters", expanded=True):
        tw2_type, tw2_sprint, tw2_start, tw2_end = render_time_window_filter("t2_tw")
        
        row2_cols = st.columns([2, 1, 1])
        with row2_cols[0]:
            t2_sections, _ = render_section_filter("t2_sec")
        with row2_cols[1]:
            t2_view = st.radio("View", ["Tickets", "Tasks"], key="t2_view", horizontal=True)
        with row2_cols[2]:
            t2_include_ad = render_ad_ticket_toggle("t2_ad")
    
    # Calculation explanation
    with st.expander("How are these numbers calculated?", expanded=False):
        st.markdown("""
        **Chart: Tickets & Tasks Status (Pie Charts)**
        
        - **View Toggle**: Switch between Tickets and Tasks
        - **For Tasks**:
            - **Open**: Tasks with status in `Waiting`, `Accepted`, `Assigned`, `Logged`
            - **Completed**: Tasks with status in `Completed`, `Cancelled`
        - **For Tickets**:
            - **Open**: Tickets with status in `Active`, `Reopen`, `Waiting for Customer`, `Waiting for Resolution`
            - **Completed**: Tickets with status in `Closed`, `Resolved`
        - **Grouping**: Pie charts show distribution by Lab Section
        - **Colors**: Consistent color mapping across both pie charts
        """)
    
    # Load and filter data
    if tw2_start and tw2_end:
        df = load_filtered_tasks(
            start_date=tw2_start,
            end_date=tw2_end,
            sections=t2_sections,
            team_members=None,
            statuses=None,
            include_ad=t2_include_ad
        )
        
        if df.empty:
            st.warning("No data available for the selected filters.")
        else:
            # Determine which column to use based on view toggle
            if t2_view == "Tickets":
                id_col = 'TicketNum'
                status_col = 'TicketStatus' if 'TicketStatus' in df.columns else 'TaskStatus'
                item_label = "Tickets"
            else:
                id_col = 'TaskNum'
                status_col = 'TaskStatus'
                item_label = "Tasks"
            
            # Ensure required columns exist
            if id_col not in df.columns or 'Section' not in df.columns:
                st.warning(f"Required columns not found in data.")
            else:
                # Classify items as Open or Completed
                # Ticket statuses: Closed, Active, Resolved, Reopen, Waiting for Customer, Waiting for Resolution
                OPEN_TICKET_STATUSES = ['Active', 'Reopen', 'Waiting for Customer', 'Waiting for Resolution']
                CLOSED_TICKET_STATUSES = ['Closed', 'Resolved']
                
                if t2_view == "Tickets":
                    # For tickets: use TicketStatus with proper ticket terminology
                    df['StatusCategory'] = df[status_col].apply(
                        lambda x: 'Completed' if x in CLOSED_TICKET_STATUSES else 'Open'
                    )
                else:
                    # For tasks: use task status
                    df['StatusCategory'] = df[status_col].apply(
                        lambda x: 'Open' if x in OPEN_TASK_STATUSES else 'Completed'
                    )
                
                # Count by section and status category
                if t2_view == "Tickets":
                    # Count unique tickets
                    status_counts = df.groupby(['Section', 'StatusCategory'])[id_col].nunique().reset_index()
                else:
                    # Count tasks
                    status_counts = df.groupby(['Section', 'StatusCategory'])[id_col].count().reset_index()
                
                status_counts.columns = ['Section', 'StatusCategory', 'Count']
                
                # Split into Open and Completed
                open_df = status_counts[status_counts['StatusCategory'] == 'Open'].copy()
                completed_df = status_counts[status_counts['StatusCategory'] == 'Completed'].copy()
                
                # Create consistent color map for all sections
                all_sections = sorted(status_counts['Section'].unique().tolist())
                colors = px.colors.qualitative.Set2
                section_color_map = {section: colors[i % len(colors)] for i, section in enumerate(all_sections)}
                
                # Display pie charts side by side
                chart_cols = st.columns(2)
                
                with chart_cols[0]:
                    st.markdown(f"#### 🔓 Open {item_label} by Lab Section")
                    if not open_df.empty and open_df['Count'].sum() > 0:
                        fig_open = px.pie(
                            open_df,
                            values='Count',
                            names='Section',
                            title=f'Open {item_label}',
                            color='Section',
                            color_discrete_map=section_color_map,
                            hole=0.3
                        )
                        fig_open.update_traces(
                            textposition='inside',
                            textinfo='percent+value',
                            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}<extra></extra>'
                        )
                        fig_open.update_layout(
                            showlegend=False,
                            height=400,
                            margin=dict(b=20)
                        )
                        st.plotly_chart(fig_open, use_container_width=True)
                        st.caption(f"**Total Open:** {open_df['Count'].sum()}")
                    else:
                        st.info(f"No open {item_label.lower()} found.")
                
                with chart_cols[1]:
                    st.markdown(f"#### Completed {item_label} by Lab Section")
                    if not completed_df.empty and completed_df['Count'].sum() > 0:
                        fig_completed = px.pie(
                            completed_df,
                            values='Count',
                            names='Section',
                            title=f'Completed {item_label}',
                            color='Section',
                            color_discrete_map=section_color_map,
                            hole=0.3
                        )
                        fig_completed.update_traces(
                            textposition='inside',
                            textinfo='percent+value',
                            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}<extra></extra>'
                        )
                        fig_completed.update_layout(
                            showlegend=False,
                            height=400,
                            margin=dict(b=20)
                        )
                        st.plotly_chart(fig_completed, use_container_width=True)
                        st.caption(f"**Total Completed:** {completed_df['Count'].sum()}")
                    else:
                        st.info(f"No completed {item_label.lower()} found.")
                
                # Shared legend below charts
                st.markdown("**Legend:**")
                legend_cols = st.columns(min(len(all_sections), 6))
                for i, section in enumerate(all_sections):
                    col_idx = i % min(len(all_sections), 6)
                    with legend_cols[col_idx]:
                        color = section_color_map[section]
                        st.markdown(f"<span style='color:{color}'>●</span> {section}", unsafe_allow_html=True)
                
                # Summary table
                st.divider()
                st.markdown("#### Summary by Section")
                
                # Pivot for summary
                summary_pivot = status_counts.pivot_table(
                    index='Section',
                    columns='StatusCategory',
                    values='Count',
                    fill_value=0,
                    aggfunc='sum'
                ).reset_index()
                
                # Ensure both columns exist
                if 'Open' not in summary_pivot.columns:
                    summary_pivot['Open'] = 0
                if 'Completed' not in summary_pivot.columns:
                    summary_pivot['Completed'] = 0
                
                summary_pivot['Total'] = summary_pivot['Open'] + summary_pivot['Completed']
                summary_pivot['Completion Rate'] = (summary_pivot['Completed'] / summary_pivot['Total'] * 100).round(1)
                summary_pivot['Completion Rate'] = summary_pivot['Completion Rate'].apply(lambda x: f"{x}%")
                
                st.dataframe(
                    summary_pivot[['Section', 'Open', 'Completed', 'Total', 'Completion Rate']],
                    use_container_width=True,
                    hide_index=True
                )
    else:
        st.warning("Please select a valid time window.")


# =============================================================================
# TAB 3: EFFORTS BY LAB SECTION
# =============================================================================

with tab3:
    st.subheader("Efforts by Lab Section")
    st.caption("PIBIDS effort distribution across lab sections by ticket type (percentage)")
    
    # Filters - compact layout
    with st.expander("Filters", expanded=True):
        tw3_type, tw3_sprint, tw3_start, tw3_end = render_time_window_filter("t3_tw")
        
        row2_cols = st.columns([2, 1, 1])
        with row2_cols[0]:
            t3_sections, _ = render_section_filter("t3_sec")
        with row2_cols[1]:
            t3_hours_type = st.radio("Hours Type", ["Logged Hours", "Expected Hours"], key="t3_hours_type", horizontal=True)
        with row2_cols[2]:
            t3_include_ad = render_ad_ticket_toggle("t3_ad")
    
    # Calculation explanation
    with st.expander("How are these numbers calculated?", expanded=False):
        st.markdown("""
        **Chart: Efforts by Lab Section**
        
        - **Hours Type Toggle**:
            - **Logged Hours**: Sum of actual worklog entries from team members
            - **Expected Hours**: Sum of estimated hours from task assignments
        - **Percentage Calculation**: `(Section Hours / Total Hours) × 100`
        - **Stacking**: Bars are stacked by Ticket Type (IR, SR, PR, NC, AD)
        - **Data Source**:
            - Logged Hours: Worklog table joined with Tasks
            - Expected Hours: Task assignments with ExpectedHours field
        - **Filters**: Lab Section, AD Tickets toggle
        """)
    
    # Load and process data
    if tw3_start and tw3_end:
        if t3_hours_type == "Logged Hours":
            # Get worklogs with task info
            worklog_store = get_worklog_store()
            worklogs_df = worklog_store.get_worklogs_with_task_info()
            
            if worklogs_df.empty:
                st.warning("No worklog data available.")
            else:
                # Filter by date range
                if 'LogDate' in worklogs_df.columns:
                    worklogs_df['LogDate'] = pd.to_datetime(worklogs_df['LogDate'], errors='coerce')
                    worklogs_df = worklogs_df[
                        (worklogs_df['LogDate'] >= tw3_start) & 
                        (worklogs_df['LogDate'] <= tw3_end)
                    ]
                
                # Exclude AD tickets if not included
                if not t3_include_ad and 'TicketType' in worklogs_df.columns:
                    worklogs_df = worklogs_df[worklogs_df['TicketType'] != 'AD']
                
                if worklogs_df.empty:
                    st.warning("No worklog data for the selected time window.")
                else:
                    # Calculate hours by Section and TicketType
                    if 'MinutesSpent' in worklogs_df.columns:
                        worklogs_df['Hours'] = worklogs_df['MinutesSpent'] / 60.0
                    else:
                        worklogs_df['Hours'] = 0
                    
                    # Group by Section and TicketType
                    effort_df = worklogs_df.groupby(['Section', 'TicketType'])['Hours'].sum().reset_index()
                    
                    # Calculate total hours for percentage
                    total_hours = effort_df['Hours'].sum()
                    
                    # Filter by selected sections (visibility only)
                    display_df = effort_df[effort_df['Section'].isin(t3_sections)].copy()
                    
                    if display_df.empty:
                        st.warning("No data for selected sections.")
                    else:
                        # Calculate percentage based on total hours (not filtered)
                        display_df['Percentage'] = (display_df['Hours'] / total_hours * 100).round(1)
                        
                        # Create consistent color map for ticket types
                        ticket_types = sorted(display_df['TicketType'].unique().tolist())
                        colors = px.colors.qualitative.Set2
                        type_color_map = {t: colors[i % len(colors)] for i, t in enumerate(ticket_types)}
                        
                        # Create stacked bar chart
                        st.markdown("#### Effort Distribution by Lab Section")
                        
                        fig = px.bar(
                            display_df,
                            x='Section',
                            y='Percentage',
                            color='TicketType',
                            color_discrete_map=type_color_map,
                            title='Logged Hours by Lab Section (% of Total)',
                            labels={'Percentage': 'Percentage (%)', 'Section': 'Lab Section'},
                            text='Percentage'
                        )
                        fig.update_traces(
                            texttemplate='%{text:.1f}%',
                            textposition='inside',
                            hovertemplate='<b>%{x}</b><br>Type: %{fullData.name}<br>Hours: %{customdata:.1f}h<br>Percent: %{y:.1f}%<extra></extra>',
                            customdata=display_df['Hours']
                        )
                        fig.update_layout(
                            barmode='stack',
                            xaxis_tickangle=-45,
                            height=500,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Summary metrics
                        st.caption(f"**Total Logged Hours:** {total_hours:.1f}h | **Displayed:** {display_df['Hours'].sum():.1f}h ({display_df['Percentage'].sum():.1f}%)")
                        
                        # Summary table
                        st.divider()
                        st.markdown("#### Summary Table")
                        summary = display_df.pivot_table(
                            index='Section',
                            columns='TicketType',
                            values='Hours',
                            aggfunc='sum',
                            fill_value=0
                        ).reset_index()
                        summary['Total'] = summary.drop('Section', axis=1).sum(axis=1)
                        st.dataframe(summary, use_container_width=True, hide_index=True)
        else:
            # Expected Hours from task annotations
            df = load_filtered_tasks(
                start_date=tw3_start,
                end_date=tw3_end,
                sections=None,
                team_members=None,
                statuses=None,
                include_ad=t3_include_ad
            )
            
            if df.empty:
                st.warning("No task data available.")
            elif 'HoursEstimated' not in df.columns:
                st.warning("HoursEstimated column not found in data.")
            else:
                # Clean hours estimated
                df['Hours'] = pd.to_numeric(df['HoursEstimated'], errors='coerce').fillna(0)
                
                # Group by Section and TicketType
                effort_df = df.groupby(['Section', 'TicketType'])['Hours'].sum().reset_index()
                
                # Calculate total hours for percentage
                total_hours = effort_df['Hours'].sum()
                
                if total_hours == 0:
                    st.warning("No estimated hours data available.")
                else:
                    # Filter by selected sections (visibility only)
                    display_df = effort_df[effort_df['Section'].isin(t3_sections)].copy()
                    
                    if display_df.empty:
                        st.warning("No data for selected sections.")
                    else:
                        # Calculate percentage based on total hours (not filtered)
                        display_df['Percentage'] = (display_df['Hours'] / total_hours * 100).round(1)
                        
                        # Create consistent color map for ticket types
                        ticket_types = sorted(display_df['TicketType'].unique().tolist())
                        colors = px.colors.qualitative.Set2
                        type_color_map = {t: colors[i % len(colors)] for i, t in enumerate(ticket_types)}
                        
                        # Create stacked bar chart
                        st.markdown("#### Effort Distribution by Lab Section")
                        
                        fig = px.bar(
                            display_df,
                            x='Section',
                            y='Percentage',
                            color='TicketType',
                            color_discrete_map=type_color_map,
                            title='Expected Hours by Lab Section (% of Total)',
                            labels={'Percentage': 'Percentage (%)', 'Section': 'Lab Section'},
                            text='Percentage'
                        )
                        fig.update_traces(
                            texttemplate='%{text:.1f}%',
                            textposition='inside',
                            hovertemplate='<b>%{x}</b><br>Type: %{fullData.name}<br>Hours: %{customdata:.1f}h<br>Percent: %{y:.1f}%<extra></extra>',
                            customdata=display_df['Hours']
                        )
                        fig.update_layout(
                            barmode='stack',
                            xaxis_tickangle=-45,
                            height=500,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Summary metrics
                        st.caption(f"**Total Expected Hours:** {total_hours:.1f}h | **Displayed:** {display_df['Hours'].sum():.1f}h ({display_df['Percentage'].sum():.1f}%)")
                        
                        # Summary table
                        st.divider()
                        st.markdown("#### Summary Table")
                        summary = display_df.pivot_table(
                            index='Section',
                            columns='TicketType',
                            values='Hours',
                            aggfunc='sum',
                            fill_value=0
                        ).reset_index()
                        summary['Total'] = summary.drop('Section', axis=1).sum(axis=1)
                        st.dataframe(summary, use_container_width=True, hide_index=True)
    else:
        st.warning("Please select a valid time window.")


# =============================================================================
# TAB 4: EFFORT DISTRIBUTION BY TEAM
# =============================================================================

with tab4:
    st.subheader("Effort Distribution by PIBIDS Team")
    st.caption("How each team member allocates their available hours")
    
    # Filters - compact layout
    with st.expander("Filters", expanded=True):
        tw4_type, tw4_sprint, tw4_start, tw4_end = render_time_window_filter("t4_tw")
        
        row2_cols = st.columns([2, 1, 1])
        with row2_cols[0]:
            t4_members, _ = render_team_member_filter("t4_tm")
        with row2_cols[1]:
            t4_denominator = st.radio("Denominator", ["Total Allocated", "Total Worklog"], key="t4_denominator", horizontal=True)
        with row2_cols[2]:
            t4_include_ad = render_ad_ticket_toggle("t4_ad")
    
    # Calculation explanation
    with st.expander("How are these numbers calculated?", expanded=False):
        st.markdown("""
        **Charts: Effort Distribution by Team Member**
        
        - **Chart 4A**: Effort by Ticket Type per Team Member
        - **Chart 4B**: Effort by Lab Section per Team Member
        
        **Denominator Toggle**:
        - **Total Allocated**: Available working hours = `(Weekdays in period × 8) - (Off Days × 8)`
        - **Total Worklog**: Sum of all logged hours for that team member
        
        **Percentage Calculation**: `(Category Hours / Denominator) × 100`
        
        **Unaccounted (grey)**: When using "Total Allocated":
        - `Unaccounted Hours = Available Hours - Logged Hours`
        - Represents time not logged to any task
        
        **Note**: Percentages sum to 100% when using "Total Allocated" (includes Unaccounted)
        """)
    
    # Load and process data
    if tw4_start and tw4_end:
        # Get worklogs with task info
        worklog_store = get_worklog_store()
        worklogs_df = worklog_store.get_worklogs_with_task_info()
        
        if worklogs_df.empty:
            st.warning("No worklog data available.")
        else:
            # Filter by date range
            if 'LogDate' in worklogs_df.columns:
                worklogs_df['LogDate'] = pd.to_datetime(worklogs_df['LogDate'], errors='coerce')
                worklogs_df = worklogs_df[
                    (worklogs_df['LogDate'] >= tw4_start) & 
                    (worklogs_df['LogDate'] <= tw4_end)
                ]
            
            # Exclude AD tickets if not included
            if not t4_include_ad and 'TicketType' in worklogs_df.columns:
                worklogs_df = worklogs_df[worklogs_df['TicketType'] != 'AD']
            
            # Filter by selected team members
            if 'Owner' in worklogs_df.columns:
                worklogs_df = worklogs_df[worklogs_df['Owner'].isin(t4_members)]
            
            if worklogs_df.empty:
                st.warning("No worklog data for the selected filters.")
            else:
                # Calculate hours
                if 'MinutesSpent' in worklogs_df.columns:
                    worklogs_df['Hours'] = worklogs_df['MinutesSpent'] / 60.0
                else:
                    worklogs_df['Hours'] = 0
                
                # Calculate available hours per member
                offdays_store = get_offdays_store()
                calendar = SprintCalendar()
                
                # Count weekdays in the time window
                def count_weekdays(start, end):
                    days = 0
                    current = start
                    while current <= end:
                        if current.weekday() < 5:  # Monday=0 to Friday=4
                            days += 1
                        current += timedelta(days=1)
                    return days
                
                total_weekdays = count_weekdays(tw4_start, tw4_end)
                
                # Get off days count per member
                member_available_hours = {}
                for member in t4_members:
                    if tw4_type == "sprint" and tw4_sprint:
                        off_count = offdays_store.get_offday_count(member, tw4_sprint)
                    else:
                        off_count = 0  # For date range, no off days data
                    available_days = max(0, total_weekdays - off_count)
                    member_available_hours[member] = available_days * 8.0
                
                # ============================================
                # Chart 4A: Effort by Ticket Type per Member
                # ============================================
                st.markdown("#### Chart 4A: Effort by Ticket Type per Team Member")
                
                # Fill null TicketType values with 'Unknown'
                worklogs_df['TicketType'] = worklogs_df['TicketType'].fillna('Unknown').replace('', 'Unknown')
                
                # Group by Owner and TicketType
                type_effort = worklogs_df.groupby(['Owner', 'TicketType'])['Hours'].sum().reset_index()
                
                # Calculate total logged hours per member
                member_totals = worklogs_df.groupby('Owner')['Hours'].sum().to_dict()
                
                # Prepare data for stacked bar chart
                chart_data_a = []
                for member in t4_members:
                    member_type_data = type_effort[type_effort['Owner'] == member]
                    logged_total = member_totals.get(member, 0)
                    available = member_available_hours.get(member, 80)
                    
                    # Determine denominator
                    if t4_denominator == "Total Allocated":
                        denominator = available
                    else:
                        denominator = logged_total if logged_total > 0 else 1
                    
                    display_name = get_display_name(member)
                    for _, row in member_type_data.iterrows():
                        pct = (row['Hours'] / denominator * 100) if denominator > 0 else 0
                        chart_data_a.append({
                            'TeamMember': display_name,
                            'TicketType': row['TicketType'],
                            'Hours': row['Hours'],
                            'Percentage': round(pct, 1)
                        })
                    
                    # Add Unaccounted if using Total Allocated
                    if t4_denominator == "Total Allocated":
                        unaccounted = max(0, available - logged_total)
                        # Always add unaccounted row (even if 0) to ensure member appears
                        pct = (unaccounted / denominator * 100) if denominator > 0 else 0
                        chart_data_a.append({
                            'TeamMember': display_name,
                            'TicketType': 'Unaccounted',
                            'Hours': unaccounted,
                            'Percentage': round(pct, 1)
                        })
                
                if chart_data_a:
                    df_chart_a = pd.DataFrame(chart_data_a)
                    
                    # Create consistent color map
                    all_types = sorted(df_chart_a['TicketType'].unique().tolist())
                    colors_list = px.colors.qualitative.Set2
                    type_color_map = {t: colors_list[i % len(colors_list)] for i, t in enumerate(all_types)}
                    type_color_map['Unaccounted'] = '#E0E0E0'  # Gray for unaccounted
                    
                    # Build chart using go.Figure for better bar width control
                    fig_a = go.Figure()
                    team_members_sorted = sorted(df_chart_a['TeamMember'].unique().tolist())
                    
                    for ticket_type in all_types:
                        type_data = df_chart_a[df_chart_a['TicketType'] == ticket_type]
                        fig_a.add_trace(go.Bar(
                            y=type_data['TeamMember'],
                            x=type_data['Percentage'],
                            name=ticket_type,
                            orientation='h',
                            marker_color=type_color_map.get(ticket_type, '#888888'),
                            text=type_data['Percentage'].apply(lambda x: f'{x:.0f}%'),
                            textposition='inside',
                            hovertemplate='<b>%{y}</b><br>Type: ' + ticket_type + '<br>Percent: %{x:.1f}%<extra></extra>'
                        ))
                    
                    fig_a.update_layout(
                        barmode='stack',
                        title=f'Effort by Ticket Type (% of {t4_denominator})',
                        xaxis_title='Percentage (%)',
                        yaxis_title='Team Member',
                        height=max(400, len(team_members_sorted) * 35),
                        legend=dict(
                            orientation="v",
                            yanchor="top",
                            y=1,
                            xanchor="left",
                            x=1.02,
                            font=dict(size=10),
                            title=dict(text="Ticket Type", font=dict(size=11))
                        ),
                        margin=dict(r=150),
                        yaxis=dict(categoryorder='category ascending')
                    )
                    st.plotly_chart(fig_a, use_container_width=True)
                else:
                    st.info("No data available for Chart 4A.")
                
                st.divider()
                
                # ============================================
                # Chart 4B: Effort by Lab Section per Member
                # ============================================
                st.markdown("#### Chart 4B: Effort by Lab Section per Team Member")
                
                # Fill null Section values with 'Unknown'
                worklogs_df['Section'] = worklogs_df['Section'].fillna('Unknown').replace('', 'Unknown')
                
                # Group by Owner and Section
                section_effort = worklogs_df.groupby(['Owner', 'Section'])['Hours'].sum().reset_index()
                
                # Prepare data for stacked bar chart
                chart_data_b = []
                for member in t4_members:
                    member_section_data = section_effort[section_effort['Owner'] == member]
                    logged_total = member_totals.get(member, 0)
                    available = member_available_hours.get(member, 80)
                    
                    # Determine denominator
                    if t4_denominator == "Total Allocated":
                        denominator = available
                    else:
                        denominator = logged_total if logged_total > 0 else 1
                    
                    display_name = get_display_name(member)
                    for _, row in member_section_data.iterrows():
                        pct = (row['Hours'] / denominator * 100) if denominator > 0 else 0
                        chart_data_b.append({
                            'TeamMember': display_name,
                            'Section': row['Section'],
                            'Hours': row['Hours'],
                            'Percentage': round(pct, 1)
                        })
                    
                    # Add Unaccounted if using Total Allocated
                    if t4_denominator == "Total Allocated":
                        unaccounted = max(0, available - logged_total)
                        # Always add unaccounted row (even if 0) to ensure member appears
                        pct = (unaccounted / denominator * 100) if denominator > 0 else 0
                        chart_data_b.append({
                            'TeamMember': display_name,
                            'Section': 'Unaccounted',
                            'Hours': unaccounted,
                            'Percentage': round(pct, 1)
                        })
                
                if chart_data_b:
                    df_chart_b = pd.DataFrame(chart_data_b)
                    
                    # Create consistent color map
                    all_sections = sorted(df_chart_b['Section'].unique().tolist())
                    colors_list_b = px.colors.qualitative.Set2
                    section_color_map = {s: colors_list_b[i % len(colors_list_b)] for i, s in enumerate(all_sections)}
                    section_color_map['Unaccounted'] = '#E0E0E0'  # Gray for unaccounted
                    
                    # Build chart using go.Figure for better bar width control
                    fig_b = go.Figure()
                    team_members_sorted_b = sorted(df_chart_b['TeamMember'].unique().tolist())
                    
                    for section in all_sections:
                        section_data = df_chart_b[df_chart_b['Section'] == section]
                        fig_b.add_trace(go.Bar(
                            y=section_data['TeamMember'],
                            x=section_data['Percentage'],
                            name=section,
                            orientation='h',
                            marker_color=section_color_map.get(section, '#888888'),
                            text=section_data['Percentage'].apply(lambda x: f'{x:.0f}%'),
                            textposition='inside',
                            hovertemplate='<b>%{y}</b><br>Section: ' + section + '<br>Percent: %{x:.1f}%<extra></extra>'
                        ))
                    
                    fig_b.update_layout(
                        barmode='stack',
                        title=f'Effort by Lab Section (% of {t4_denominator})',
                        xaxis_title='Percentage (%)',
                        yaxis_title='Team Member',
                        height=max(400, len(team_members_sorted_b) * 35),
                        legend=dict(
                            orientation="v",
                            yanchor="top",
                            y=1,
                            xanchor="left",
                            x=1.02,
                            font=dict(size=9),
                            title=dict(text="Lab Section", font=dict(size=11))
                        ),
                        margin=dict(r=180),
                        yaxis=dict(categoryorder='category ascending')
                    )
                    st.plotly_chart(fig_b, use_container_width=True)
                else:
                    st.info("No data available for Chart 4B.")
                
                # Summary table
                st.divider()
                st.markdown("#### Summary by Team Member")
                summary_data = []
                for member in t4_members:
                    logged = member_totals.get(member, 0)
                    available = member_available_hours.get(member, 80)
                    utilization = (logged / available * 100) if available > 0 else 0
                    summary_data.append({
                        'Team Member': get_display_name(member),
                        'Logged Hours': round(logged, 1),
                        'Available Hours': round(available, 1),
                        'Utilization': f"{utilization:.1f}%"
                    })
                st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
    else:
        st.warning("Please select a valid time window.")


# =============================================================================
# TAB 5: TASK COMPLETION RATE
# =============================================================================

with tab5:
    st.subheader("Task Completion Rate by Sprint")
    st.caption("Execution efficiency: tasks completed within sprint windows")
    
    # Filters - compact layout
    with st.expander("Filters", expanded=True):
        tw5_type, tw5_sprint, tw5_start, tw5_end = render_time_window_filter("t5_tw")
        
        row2_cols = st.columns([2, 1])
        with row2_cols[0]:
            t5_members, _ = render_team_member_filter("t5_tm")
        with row2_cols[1]:
            t5_include_ad = render_ad_ticket_toggle("t5_ad")
    
    # Calculation explanation
    with st.expander("How are these numbers calculated?", expanded=False):
        st.markdown("""
        **Charts: Task Completion Rate**
        
        - **Chart 5A**: Completion Rate by Sprint
        - **Chart 5B**: Completion Rate by Team Member
        
        **Completion Rate Formula**:
        ```
        Completion Rate = (Completed Tasks / Committed Tasks) × 100
        ```
        
        **Definitions**:
        - **Committed Tasks**: Tasks assigned to the sprint (via SprintsAssigned field)
        - **Completed Tasks**: Tasks that meet BOTH conditions:
            1. Status is in `Completed`, `Cancelled`, `Closed`, `Resolved`, `Done`
            2. TaskResolvedDt falls within the sprint window (between sprint start and end dates)
        
        **Multi-Sprint Assignment**: A task assigned to multiple sprints is counted separately for each sprint it's assigned to.
        
        **Hover Info**: Shows "Completed X of Y tasks" for each bar.
        """)
    
    # Load task data
    task_store = get_task_store()
    all_tasks = task_store.get_all_tasks()
    calendar = SprintCalendar()
    all_sprints = calendar.get_all_sprints()
    
    if all_tasks.empty:
        st.warning("No task data available.")
    elif all_sprints.empty:
        st.warning("No sprint data available.")
    else:
        # Exclude AD tickets if not included
        if not t5_include_ad and 'TicketType' in all_tasks.columns:
            all_tasks = all_tasks[all_tasks['TicketType'] != 'AD']
        
        # Filter by team members
        if 'AssignedTo' in all_tasks.columns:
            all_tasks = all_tasks[all_tasks['AssignedTo'].isin(t5_members)]
        
        # Define closed statuses
        CLOSED_STATUSES = ['Completed', 'Cancelled', 'Closed', 'Resolved', 'Done']
        
        # ============================================
        # Chart 5A: Completion Rate by Sprint
        # ============================================
        st.markdown("#### Chart 5A: Completion Rate by Sprint")
        
        # Calculate completion rate for each sprint
        sprint_data = []
        for _, sprint in all_sprints.iterrows():
            sprint_num = sprint['SprintNumber']
            sprint_name = sprint['SprintName']
            sprint_start = pd.to_datetime(sprint['SprintStartDt'])
            sprint_end = pd.to_datetime(sprint['SprintEndDt'])
            
            # Tasks assigned to this sprint (via SprintsAssigned column)
            if 'SprintsAssigned' in all_tasks.columns:
                assigned_mask = all_tasks['SprintsAssigned'].apply(
                    lambda x: str(sprint_num) in str(x).split(',') if pd.notna(x) else False
                )
            else:
                assigned_mask = all_tasks['SprintNumber'] == sprint_num
            
            assigned_tasks = all_tasks[assigned_mask]
            committed_count = len(assigned_tasks)
            
            if committed_count == 0:
                continue
            
            # Tasks completed within sprint window
            if 'TaskResolvedDt' in assigned_tasks.columns:
                assigned_tasks['TaskResolvedDt'] = pd.to_datetime(assigned_tasks['TaskResolvedDt'], errors='coerce')
                completed_mask = (
                    assigned_tasks['TaskStatus'].isin(CLOSED_STATUSES) &
                    (assigned_tasks['TaskResolvedDt'] >= sprint_start) &
                    (assigned_tasks['TaskResolvedDt'] <= sprint_end)
                )
                completed_count = completed_mask.sum()
            else:
                completed_count = assigned_tasks[assigned_tasks['TaskStatus'].isin(CLOSED_STATUSES)].shape[0]
            
            completion_rate = (completed_count / committed_count * 100) if committed_count > 0 else 0
            
            sprint_data.append({
                'Sprint': f"Sprint {sprint_num}",
                'SprintName': sprint_name,
                'Committed': committed_count,
                'Completed': completed_count,
                'CompletionRate': round(completion_rate, 1)
            })
        
        if sprint_data:
            df_sprint = pd.DataFrame(sprint_data)
            
            fig_5a = go.Figure()
            fig_5a.add_trace(go.Bar(
                x=df_sprint['Sprint'],
                y=df_sprint['CompletionRate'],
                text=df_sprint['CompletionRate'].apply(lambda x: f'{x:.0f}%'),
                textposition='outside',
                marker_color='#4CAF50',
                hovertemplate='<b>%{x}</b><br>Completion Rate: %{y:.1f}%<br>Completed: %{customdata[0]} of %{customdata[1]}<extra></extra>',
                customdata=df_sprint[['Completed', 'Committed']].values
            ))
            
            fig_5a.update_layout(
                title='Task Completion Rate by Sprint',
                xaxis_title='Sprint',
                yaxis_title='Completion Rate (%)',
                yaxis=dict(range=[0, max(110, df_sprint['CompletionRate'].max() + 10)]),
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig_5a, use_container_width=True)
            
            # Summary
            avg_rate = df_sprint['CompletionRate'].mean()
            st.caption(f"**Average Completion Rate:** {avg_rate:.1f}%")
        else:
            st.info("No sprint data with assigned tasks found.")
        
        st.divider()
        
        # ============================================
        # Chart 5B: Completion Rate by Team Member
        # ============================================
        st.markdown("#### Chart 5B: Completion Rate by Team Member")
        
        # Filter by time window
        if tw5_start and tw5_end:
            # Get sprints within time window
            sprints_in_range = all_sprints[
                (pd.to_datetime(all_sprints['SprintStartDt']) >= tw5_start) &
                (pd.to_datetime(all_sprints['SprintEndDt']) <= tw5_end)
            ]
            
            if sprints_in_range.empty and tw5_sprint:
                # Use selected sprint
                sprints_in_range = all_sprints[all_sprints['SprintNumber'] == tw5_sprint]
            
            member_data = []
            for member in t5_members:
                member_tasks = all_tasks[all_tasks['AssignedTo'] == member]
                
                total_committed = 0
                total_completed = 0
                
                for _, sprint in sprints_in_range.iterrows():
                    sprint_num = sprint['SprintNumber']
                    sprint_start = pd.to_datetime(sprint['SprintStartDt'])
                    sprint_end = pd.to_datetime(sprint['SprintEndDt'])
                    
                    # Tasks assigned to this sprint
                    if 'SprintsAssigned' in member_tasks.columns:
                        assigned_mask = member_tasks['SprintsAssigned'].apply(
                            lambda x: str(sprint_num) in str(x).split(',') if pd.notna(x) else False
                        )
                    else:
                        assigned_mask = member_tasks['SprintNumber'] == sprint_num
                    
                    assigned = member_tasks[assigned_mask]
                    total_committed += len(assigned)
                    
                    # Completed within sprint window
                    if not assigned.empty and 'TaskResolvedDt' in assigned.columns:
                        assigned['TaskResolvedDt'] = pd.to_datetime(assigned['TaskResolvedDt'], errors='coerce')
                        completed_mask = (
                            assigned['TaskStatus'].isin(CLOSED_STATUSES) &
                            (assigned['TaskResolvedDt'] >= sprint_start) &
                            (assigned['TaskResolvedDt'] <= sprint_end)
                        )
                        total_completed += completed_mask.sum()
                
                if total_committed > 0:
                    completion_rate = (total_completed / total_committed * 100)
                    member_data.append({
                        'TeamMember': get_display_name(member),
                        'Committed': total_committed,
                        'Completed': total_completed,
                        'CompletionRate': round(completion_rate, 1)
                    })
            
            if member_data:
                df_member = pd.DataFrame(member_data)
                df_member = df_member.sort_values('CompletionRate', ascending=True)
                
                fig_5b = go.Figure()
                fig_5b.add_trace(go.Bar(
                    y=df_member['TeamMember'],
                    x=df_member['CompletionRate'],
                    text=df_member['CompletionRate'].apply(lambda x: f'{x:.0f}%'),
                    textposition='outside',
                    orientation='h',
                    marker_color='#2196F3',
                    hovertemplate='<b>%{y}</b><br>Completion Rate: %{x:.1f}%<br>Completed: %{customdata[0]} of %{customdata[1]}<extra></extra>',
                    customdata=df_member[['Completed', 'Committed']].values
                ))
                
                fig_5b.update_layout(
                    title='Task Completion Rate by Team Member',
                    xaxis_title='Completion Rate (%)',
                    yaxis_title='Team Member',
                    xaxis=dict(range=[0, max(110, df_member['CompletionRate'].max() + 10)]),
                    height=max(400, len(member_data) * 35),
                    showlegend=False
                )
                st.plotly_chart(fig_5b, use_container_width=True)
                
                # Summary table
                st.divider()
                st.markdown("#### Summary Table")
                st.dataframe(
                    df_member[['TeamMember', 'Committed', 'Completed', 'CompletionRate']].rename(
                        columns={'TeamMember': 'Team Member', 'CompletionRate': 'Completion Rate (%)'}
                    ).sort_values('Completion Rate (%)', ascending=False),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No tasks assigned to team members in the selected time window.")
        else:
            st.warning("Please select a valid time window.")


# =============================================================================
# FOOTER
# =============================================================================

st.divider()
st.caption("Reports & Analytics | PIBIDS Sprint Dashboard")
