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

st.set_page_config(
    page_title="Worklog Activity",
    page_icon="📊",
    layout="wide"
)

apply_grid_styles()

st.title("📊 Worklog Activity Report")
st.caption("_Team member activity tracking based on iTrack worklog data — PBIDS Team_")

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
    st.info("📭 No worklog data available")
    st.markdown("""
    **To view worklog activity:**
    1. Go to **Upload Tasks** page
    2. Upload the iTrack **Worklog export** CSV file
    3. Return here to view activity reports
    """)
    st.page_link("pages/2_📤_Upload_Tasks.py", label="📤 Upload Worklog Data", icon="📤")
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

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📅 Daily Activity",
    "👤 By User",
    "📈 Sprint Summary",
    "📋 Raw Data"
])

with tab1:
    st.subheader("Daily Activity by User")
    st.caption("Shows log frequency and minutes spent per user per day")
    
    # Sprint filter
    available_sprints = sorted(all_worklogs['SprintNumber'].dropna().unique(), reverse=True)
    available_sprints = [s for s in available_sprints if s > 0]
    
    # Get available ticket types and sections
    available_ticket_types = ['All'] + sorted(all_worklogs['TicketType'].dropna().unique().tolist())
    available_sections = ['All']
    if 'Section' in all_worklogs.columns:
        available_sections += sorted(all_worklogs['Section'].dropna().unique().tolist())
    
    col1, col2, col3 = st.columns([1, 1, 1])
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
        selected_ticket_type = st.selectbox(
            "Ticket Type",
            options=available_ticket_types,
            index=0,
            help="Filter by ticket type (IR, SR, PR, NC, etc.)"
        )
    
    with col3:
        selected_section = st.selectbox(
            "Section",
            options=available_sections,
            index=0,
            help="Filter by lab section"
        )
    
    if selected_sprint:
        # Get sprint date range
        sprint_info = calendar.get_sprint_by_number(int(selected_sprint))
        if sprint_info is not None:
            sprint_start = pd.to_datetime(sprint_info['SprintStartDt']).date()
            sprint_end = pd.to_datetime(sprint_info['SprintEndDt']).date()
            # Generate all dates in sprint range
            all_sprint_dates = pd.date_range(start=sprint_start, end=sprint_end).date.tolist()
        else:
            all_sprint_dates = None
        
        # Filter worklogs by sprint, ticket type, and section
        sprint_worklogs = all_worklogs[all_worklogs['SprintNumber'] == selected_sprint].copy()
        if selected_ticket_type != 'All':
            sprint_worklogs = sprint_worklogs[sprint_worklogs['TicketType'] == selected_ticket_type]
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
            if selected_ticket_type != 'All':
                filter_parts.append(selected_ticket_type)
            if selected_section != 'All':
                filter_parts.append(selected_section)
            filter_msg = f" ({', '.join(filter_parts)})" if filter_parts else ""
            st.info(f"No activity recorded for Sprint {int(selected_sprint)}{filter_msg}")
        else:
            # Apply name mapping to filtered worklogs
            sprint_worklogs = apply_name_mapping(sprint_worklogs, 'Owner')
            act_display_col = 'Owner_Display' if 'Owner_Display' in sprint_worklogs.columns else 'Owner'
            
            # Create Date column for grouping
            sprint_worklogs['Date'] = sprint_worklogs['LogDate'].dt.date
            
            # Build filter label for captions
            filter_parts = []
            if selected_ticket_type != 'All':
                filter_parts.append(selected_ticket_type)
            if selected_section != 'All':
                filter_parts.append(selected_section)
            filter_label = f" (Filtered: {', '.join(filter_parts)})" if filter_parts else ""
            
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
            
            # Style with weekend highlighting
            def highlight_weekends(df, weekend_cols):
                styles = pd.DataFrame('', index=df.index, columns=df.columns)
                for col in weekend_cols:
                    if col in df.columns:
                        styles[col] = 'background-color: #f8f5fc'  # Very light purple for weekends
                return styles
            
            st.dataframe(
                log_pivot.style.background_gradient(cmap='Blues', axis=None).apply(
                    lambda df: highlight_weekends(df, weekend_cols), axis=None
                ),
                use_container_width=True
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
                use_container_width=True
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
                use_container_width=True
            )
            
            # Export
            st.divider()
            col1, col2, col3 = st.columns([1, 1, 3])
            with col1:
                export_df = sprint_worklogs.copy()
                export_df['Hours'] = export_df['MinutesSpent'] / 60
                excel_data = export_to_excel(export_df)
                st.download_button(
                    "📥 Export Excel",
                    excel_data,
                    f"sprint_{int(selected_sprint)}_activity.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

with tab2:
    st.subheader("Activity by User")
    
    # Get unique users
    display_col = 'Owner_Display' if 'Owner_Display' in all_worklogs.columns else 'Owner'
    users = sorted(all_worklogs[display_col].dropna().unique())
    
    if not users:
        st.info("No user data available")
    else:
        selected_user = st.selectbox("Select Team Member", users)
        
        if selected_user:
            # Filter to selected user
            user_col = 'Owner_Display' if 'Owner_Display' in all_worklogs.columns else 'Owner'
            user_logs = all_worklogs[all_worklogs[user_col] == selected_user].copy()
            
            if user_logs.empty:
                st.info(f"No activity for {selected_user}")
            else:
                # User stats
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📝 Total Logs", len(user_logs))
                with col2:
                    total_mins = user_logs['MinutesSpent'].sum()
                    st.metric("⏱️ Total Hours", f"{total_mins/60:.1f}")
                with col3:
                    unique_days = user_logs['LogDate'].dt.date.nunique()
                    st.metric("📅 Days Active", unique_days)
                with col4:
                    unique_tasks = user_logs['TaskNum'].nunique()
                    st.metric("📋 Tasks Worked", unique_tasks)
                
                st.divider()
                
                # Activity over time chart
                st.markdown("### Activity Over Time")
                
                user_logs['Date'] = user_logs['LogDate'].dt.date
                daily_activity = user_logs.groupby('Date').agg(
                    Logs=('RecordId', 'count'),
                    Minutes=('MinutesSpent', 'sum')
                ).reset_index()
                daily_activity['Hours'] = daily_activity['Minutes'] / 60
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=daily_activity['Date'],
                    y=daily_activity['Logs'],
                    name='Log Count',
                    marker_color='steelblue'
                ))
                fig.add_trace(go.Scatter(
                    x=daily_activity['Date'],
                    y=daily_activity['Hours'],
                    name='Hours',
                    yaxis='y2',
                    line=dict(color='orange', width=2),
                    mode='lines+markers'
                ))
                
                fig.update_layout(
                    title=f"Daily Activity - {selected_user}",
                    xaxis_title='Date',
                    yaxis_title='Log Count',
                    yaxis2=dict(
                        title='Hours',
                        overlaying='y',
                        side='right'
                    ),
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Recent activity table
                st.markdown("### Recent Activity")
                
                recent = user_logs.sort_values('LogDate', ascending=False).head(50)
                display_cols = ['LogDate', 'TaskNum', 'MinutesSpent', 'Description', 'SprintNumber']
                available_cols = [c for c in display_cols if c in recent.columns]
                
                gb = GridOptionsBuilder.from_dataframe(recent[available_cols])
                gb.configure_default_column(resizable=True, filterable=True, sortable=True)
                gb.configure_column('LogDate', header_name='Date', width=120)
                gb.configure_column('TaskNum', header_name='Task #', width=100)
                gb.configure_column('MinutesSpent', header_name='Minutes', width=80)
                gb.configure_column('Description', width=300, tooltipField='Description')
                gb.configure_column('SprintNumber', header_name='Sprint', width=70)
                gb.configure_pagination(paginationPageSize=20)
                
                AgGrid(
                    recent[available_cols],
                    gridOptions=gb.build(),
                    height=400,
                    theme='streamlit',
                    custom_css=get_custom_css()
                )

with tab3:
    st.subheader("Sprint Summary")
    
    if sprint_totals.empty:
        st.info("No sprint summary data available")
    else:
        # Summary table
        st.markdown("### Activity by Sprint")
        
        display_totals = sprint_totals.copy()
        display_totals['TotalHours'] = display_totals['TotalMinutes'] / 60
        display_totals = display_totals[['SprintNumber', 'TotalLogs', 'TotalHours', 'UniqueUsers', 'UniqueDays']]
        display_totals.columns = ['Sprint', 'Total Logs', 'Total Hours', 'Active Users', 'Active Days']
        display_totals['Total Hours'] = display_totals['Total Hours'].apply(lambda x: f"{x:.1f}")
        
        st.dataframe(display_totals, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Log Volume by Sprint")
            fig = px.bar(
                sprint_totals,
                x='SprintNumber',
                y='TotalLogs',
                title='Total Worklog Entries per Sprint',
                labels={'SprintNumber': 'Sprint', 'TotalLogs': 'Log Count'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### Hours Logged by Sprint")
            chart_data = sprint_totals.copy()
            chart_data['Hours'] = chart_data['TotalMinutes'] / 60
            fig = px.bar(
                chart_data,
                x='SprintNumber',
                y='Hours',
                title='Total Hours Logged per Sprint',
                labels={'SprintNumber': 'Sprint', 'Hours': 'Hours'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # User activity comparison across sprints
        st.markdown("### User Activity Comparison")
        
        # Get activity for all sprints
        all_activity = worklog_store.get_activity_summary()
        if not all_activity.empty:
            display_col = 'Owner_Display' if 'Owner_Display' in all_activity.columns else 'Owner'
            
            user_sprint_summary = all_activity.groupby([display_col, 'SprintNumber']).agg(
                TotalLogs=('LogCount', 'sum'),
                TotalMinutes=('TotalMinutes', 'sum')
            ).reset_index()
            
            user_sprint_summary['Hours'] = user_sprint_summary['TotalMinutes'] / 60
            
            fig = px.bar(
                user_sprint_summary,
                x='SprintNumber',
                y='TotalLogs',
                color=display_col,
                title='Log Count by User per Sprint',
                labels={'SprintNumber': 'Sprint', 'TotalLogs': 'Logs', display_col: 'User'},
                barmode='stack'
            )
            st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Raw Worklog Data")
    st.caption("All imported worklog entries")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        display_col = 'Owner_Display' if 'Owner_Display' in all_worklogs.columns else 'Owner'
        users = ['All'] + sorted(all_worklogs[display_col].dropna().unique().tolist())
        filter_user = st.selectbox("Filter by User", users, key="raw_user")
    
    with col2:
        sprints = ['All'] + sorted([int(s) for s in all_worklogs['SprintNumber'].dropna().unique() if s > 0], reverse=True)
        filter_sprint = st.selectbox("Filter by Sprint", sprints, key="raw_sprint", format_func=lambda x: f"Sprint {x}" if x != 'All' else 'All')
    
    with col3:
        has_minutes = st.checkbox("Only entries with minutes logged", value=False)
    
    # Apply filters
    filtered = all_worklogs.copy()
    
    if filter_user != 'All':
        filtered = filtered[filtered[display_col] == filter_user]
    
    if filter_sprint != 'All':
        filtered = filtered[filtered['SprintNumber'] == filter_sprint]
    
    if has_minutes:
        filtered = filtered[filtered['MinutesSpent'] > 0]
    
    st.caption(f"Showing {len(filtered)} of {len(all_worklogs)} entries")
    
    # Display columns
    display_cols = ['LogDate', 'Owner', 'TaskNum', 'MinutesSpent', 'Description', 'SprintNumber', 'RecordId']
    if 'Owner_Display' in filtered.columns:
        display_cols = ['LogDate', 'Owner_Display', 'TaskNum', 'MinutesSpent', 'Description', 'SprintNumber', 'RecordId']
    
    available_cols = [c for c in display_cols if c in filtered.columns]
    display_df = filtered[available_cols].sort_values('LogDate', ascending=False)
    
    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_default_column(resizable=True, filterable=True, sortable=True)
    gb.configure_column('LogDate', header_name='Date', width=120)
    gb.configure_column('Owner_Display' if 'Owner_Display' in display_df.columns else 'Owner', header_name='User', width=120)
    gb.configure_column('TaskNum', header_name='Task #', width=100)
    gb.configure_column('MinutesSpent', header_name='Minutes', width=80)
    gb.configure_column('Description', width=300, tooltipField='Description')
    gb.configure_column('SprintNumber', header_name='Sprint', width=70)
    gb.configure_column('RecordId', header_name='Record ID', width=100)
    gb.configure_pagination(paginationPageSize=50)
    
    AgGrid(
        display_df,
        gridOptions=gb.build(),
        height=500,
        theme='streamlit',
        custom_css=get_custom_css()
    )
    
    # Export
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        excel_data = export_to_excel(filtered)
        st.download_button(
            "📥 Export Excel",
            excel_data,
            "worklog_data.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    with col2:
        csv_data = export_to_csv(filtered)
        st.download_button(
            "📥 Export CSV",
            csv_data,
            "worklog_data.csv",
            "text/csv",
            use_container_width=True
        )

# Footer
st.divider()
st.caption("💡 **Tip:** Upload new worklog data from the **Upload Tasks** page to update this report.")
