"""
Past Sprints Page
View and analyze historical sprint data
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder
from modules.task_store import get_task_store
from modules.sprint_calendar import get_sprint_calendar
from components.auth import require_admin, display_user_info
from utils.exporters import export_to_excel, export_to_csv
from utils.grid_styles import apply_grid_styles, get_custom_css, STATUS_CELL_STYLE, PRIORITY_CELL_STYLE, DAYS_OPEN_CELL_STYLE

st.set_page_config(
    page_title="Past Sprints (Prototype)",
    page_icon="🧪",
    layout="wide"
)

# Apply custom tooltip styles
apply_grid_styles()

st.title("Past Sprints")
st.caption("_Prototype — PBIDS Team_")

# Require admin access
require_admin("Past Sprints")

# Display user info
display_user_info()

# Load task store and calendar
task_store = get_task_store()
calendar = get_sprint_calendar()
current_sprint = calendar.get_current_sprint()

# Get all tasks and identify past sprints
all_tasks = task_store.get_all_tasks()

if all_tasks.empty:
    st.info("📭 No tasks found in the system")
    st.write("Upload tasks first to view past sprints.")
    st.page_link("pages/2_📤_Upload_Tasks.py", label="📤 Upload Tasks", icon="📤")
    st.stop()

# Get past sprints (sprints before current sprint)
all_sprints = calendar.get_all_sprints()
current_sprint_num = current_sprint['SprintNumber'] if current_sprint else 999

# Build past sprints data by combining tasks from each past sprint
past_sprint_nums = [int(s) for s in all_sprints[all_sprints['SprintNumber'] < current_sprint_num]['SprintNumber'].tolist()]

if not past_sprint_nums:
    st.info("📭 No past sprints found")
    st.write("Past sprints will appear here as time progresses.")
    st.stop()

# Collect tasks from each past sprint
past_sprints_list = []
for sprint_num in past_sprint_nums:
    sprint_tasks = task_store.get_sprint_tasks(sprint_num)
    if not sprint_tasks.empty:
        past_sprints_list.append(sprint_tasks)

if not past_sprints_list:
    st.info("📭 No tasks in past sprints")
    st.stop()

past_sprints_df = pd.concat(past_sprints_list, ignore_index=True)

# Get unique sprint numbers and info
sprint_numbers = sorted(past_sprints_df['SprintNumber'].unique(), reverse=True)
total_archived_sprints = len(sprint_numbers)
total_archived_tasks = len(past_sprints_df)

st.success(f"📊 Found **{total_archived_sprints}** archived sprint(s) with **{total_archived_tasks}** total tasks")

# Tabs for different views
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Sprint List",
    "📊 Sprint Details",
    "📈 Trends & Comparison",
    "🔍 Search Tasks"
])

with tab1:
    st.subheader("Archived Sprints Overview")
    
    # Calculate summary statistics for each sprint
    sprint_summaries = []
    
    for sprint_num in sprint_numbers:
        sprint_data = past_sprints_df[past_sprints_df['SprintNumber'] == sprint_num]
        
        # Get sprint metadata
        sprint_name = sprint_data.get('SprintName', pd.Series([f"Sprint {sprint_num}"])).iloc[0]
        sprint_start = sprint_data.get('SprintStartDt', pd.Series([None])).iloc[0]
        sprint_end = sprint_data.get('SprintEndDt', pd.Series([None])).iloc[0]
        
        # Calculate statistics
        total_tasks = len(sprint_data)
        completed = len(sprint_data[sprint_data['Status'] == 'Completed'])
        in_progress = len(sprint_data[sprint_data['Status'].isin(['In Progress', 'Assigned', 'Accepted'])])
        cancelled = len(sprint_data[sprint_data['Status'].isin(['Cancelled', 'Canceled'])])
        
        completion_rate = (completed / total_tasks * 100) if total_tasks > 0 else 0
        
        # Count by type
        ir_count = len(sprint_data[sprint_data['TicketType'] == 'IR'])
        sr_count = len(sprint_data[sprint_data['TicketType'] == 'SR'])
        
        # Effort hours
        total_hours = sprint_data['HoursEstimated'].sum()
        
        # Unique metrics
        unique_tickets = sprint_data['TicketNum'].nunique()
        unique_assignees = sprint_data['AssignedTo'].nunique()
        unique_sections = sprint_data['Section'].nunique()
        
        sprint_summaries.append({
            'Sprint #': sprint_num,
            'Sprint Name': sprint_name,
            'Start Date': sprint_start,
            'End Date': sprint_end,
            'Total Tasks': total_tasks,
            'Completed': completed,
            'In Progress': in_progress,
            'Cancelled': cancelled,
            'Completion %': f"{completion_rate:.1f}%",
            'IR Tasks': ir_count,
            'SR Tasks': sr_count,
            'Total Hours': f"{total_hours:.1f}",
            'Tickets': unique_tickets,
            'Assignees': unique_assignees,
            'Sections': unique_sections
        })
    
    summary_df = pd.DataFrame(sprint_summaries)
    
    # Display summary table
    st.dataframe(
        summary_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Sprint #': st.column_config.NumberColumn('Sprint #', format='%d'),
            'Start Date': st.column_config.DateColumn('Start Date'),
            'End Date': st.column_config.DateColumn('End Date'),
            'Completion %': st.column_config.TextColumn('Completion %'),
        }
    )
    
    # Export all sprints summary
    st.divider()
    col1, col2 = st.columns([1, 4])
    with col1:
        csv_data = summary_df.to_csv(index=False)
        st.download_button(
            "📥 Export Summary (CSV)",
            csv_data,
            "past_sprints_summary.csv",
            "text/csv",
            use_container_width=True
        )

with tab2:
    st.subheader("Sprint Details")
    
    # Sprint selector
    selected_sprint = st.selectbox(
        "Select Sprint to View",
        options=sprint_numbers,
        format_func=lambda x: f"Sprint {x}"
    )
    
    if selected_sprint:
        sprint_data = past_sprints_df[past_sprints_df['SprintNumber'] == selected_sprint].copy()
        
        # Sprint header
        sprint_name = sprint_data.get('SprintName', pd.Series([f"Sprint {selected_sprint}"])).iloc[0]
        sprint_start = sprint_data.get('SprintStartDt', pd.Series([None])).iloc[0]
        sprint_end = sprint_data.get('SprintEndDt', pd.Series([None])).iloc[0]
        
        st.markdown(f"### {sprint_name}")
        if sprint_start and sprint_end:
            st.caption(f"📅 {sprint_start} to {sprint_end}")
        
        st.divider()
        
        # Key metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        total = len(sprint_data)
        completed = len(sprint_data[sprint_data['Status'] == 'Completed'])
        in_progress = len(sprint_data[sprint_data['Status'].isin(['In Progress', 'Assigned', 'Accepted'])])
        cancelled = len(sprint_data[sprint_data['Status'].isin(['Cancelled', 'Canceled'])])
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        with col1:
            st.metric("Total Tasks", total)
        with col2:
            st.metric("Completed", completed, delta=f"{completion_rate:.0f}%")
        with col3:
            st.metric("In Progress", in_progress)
        with col4:
            st.metric("Cancelled", cancelled)
        with col5:
            total_hours = sprint_data['HoursEstimated'].sum()
            st.metric("Total Hours", f"{total_hours:.1f}")
        
        st.divider()
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Status distribution
            st.subheader("Status Distribution")
            status_counts = sprint_data['Status'].value_counts()
            
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title='Tasks by Status',
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Section distribution
            st.subheader("Section Distribution")
            section_counts = sprint_data['Section'].value_counts().head(10)
            
            fig = px.bar(
                x=section_counts.values,
                y=section_counts.index,
                orientation='h',
                labels={'x': 'Tasks', 'y': 'Section'},
                title='Top 10 Sections by Task Count'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Task type breakdown
        col1, col2, col3 = st.columns(3)
        
        with col1:
            ir_count = len(sprint_data[sprint_data['TicketType'] == 'IR'])
            st.metric("🚨 IR Tasks", ir_count)
        
        with col2:
            sr_count = len(sprint_data[sprint_data['TicketType'] == 'SR'])
            st.metric("📋 SR Tasks", sr_count)
        
        with col3:
            priority_5 = len(sprint_data[sprint_data['CustomerPriority'] == 5])
            st.metric("⚠️ Priority 5", priority_5)
        
        st.divider()
        
        # Detailed task list
        st.subheader("Task Details")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.multiselect(
                "Filter by Status",
                options=sprint_data['Status'].unique(),
                default=None
            )
        
        with col2:
            section_filter = st.multiselect(
                "Filter by Section",
                options=sprint_data['Section'].unique(),
                default=None
            )
        
        with col3:
            type_filter = st.multiselect(
                "Filter by Type",
                options=sprint_data['TicketType'].unique(),
                default=None
            )
        
        # Apply filters
        filtered_data = sprint_data.copy()
        
        if status_filter:
            filtered_data = filtered_data[filtered_data['Status'].isin(status_filter)]
        
        if section_filter:
            filtered_data = filtered_data[filtered_data['Section'].isin(section_filter)]
        
        if type_filter:
            filtered_data = filtered_data[filtered_data['TicketType'].isin(type_filter)]
        
        st.caption(f"Showing {len(filtered_data)} of {len(sprint_data)} tasks")
        
        # Use display names if available
        ps_assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in filtered_data.columns else 'AssignedTo'
        
        # Display columns
        display_cols = [
            'TaskNum', 'TicketNum', 'TicketType', 'Section', 
            'Status', ps_assignee_col, 
            'Subject', 'HoursEstimated', 'DaysOpen'
        ]
        
        available_cols = [col for col in display_cols if col in filtered_data.columns]
        display_df = filtered_data[available_cols].copy()
        
        # Configure AgGrid
        gb = GridOptionsBuilder.from_dataframe(display_df)
        gb.configure_default_column(resizable=True, filterable=True, sortable=True)
        gb.configure_column('TaskNum', header_name='Task #', width=90)
        gb.configure_column('TicketNum', header_name='Ticket #', width=100)
        gb.configure_column('TicketType', header_name='Type', width=60)
        gb.configure_column('Section', width=80)
        gb.configure_column('Status', width=100, cellStyle=STATUS_CELL_STYLE)
        gb.configure_column(ps_assignee_col, header_name='Assignee', width=120)
        gb.configure_column('Subject', width=180, tooltipField='Subject')
        gb.configure_column('HoursEstimated', header_name='Est. Hours', width=90)
        gb.configure_column('DaysOpen', header_name='Days Open', width=80, cellStyle=DAYS_OPEN_CELL_STYLE)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=100)
        
        grid_options = gb.build()
        
        AgGrid(
            display_df,
            gridOptions=grid_options,
            allow_unsafe_jscode=True,
            height=400,
            theme='streamlit',
            fit_columns_on_grid_load=False,
            enable_enterprise_modules=False,
            custom_css=get_custom_css()
        )
        
        # Export this sprint
        st.divider()
        
        col1, col2, col3 = st.columns([1, 1, 3])
        
        with col1:
            excel_data = export_to_excel(sprint_data)
            st.download_button(
                "📥 Export Excel",
                excel_data,
                f"sprint_{selected_sprint}_details.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col2:
            csv_data = export_to_csv(sprint_data)
            st.download_button(
                "📥 Export CSV",
                csv_data,
                f"sprint_{selected_sprint}_details.csv",
                "text/csv",
                use_container_width=True
            )

with tab3:
    st.subheader("Sprint Trends & Comparison")
    
    if len(sprint_numbers) < 2:
        st.info("📊 Need at least 2 sprints to show trends")
    else:
        # Calculate trends data
        trends_data = []
        
        for sprint_num in sorted(sprint_numbers):
            sprint_data = past_sprints_df[past_sprints_df['SprintNumber'] == sprint_num]
            
            total = len(sprint_data)
            completed = len(sprint_data[sprint_data['Status'] == 'Completed'])
            completion_rate = (completed / total * 100) if total > 0 else 0
            
            total_hours = sprint_data['HoursEstimated'].sum()
            avg_days_open = sprint_data['DaysOpen'].mean() if 'DaysOpen' in sprint_data.columns else 0
            
            ir_count = len(sprint_data[sprint_data['TicketType'] == 'IR'])
            sr_count = len(sprint_data[sprint_data['TicketType'] == 'SR'])
            
            trends_data.append({
                'Sprint': f"Sprint {sprint_num}",
                'Sprint #': sprint_num,
                'Total Tasks': total,
                'Completed': completed,
                'Completion %': completion_rate,
                'Total Hours': total_hours,
                'Avg Days Open': avg_days_open,
                'IR Tasks': ir_count,
                'SR Tasks': sr_count
            })
        
        trends_df = pd.DataFrame(trends_data)
        
        # Completion rate trend
        st.subheader("📈 Completion Rate Trend")
        
        fig = px.line(
            trends_df,
            x='Sprint',
            y='Completion %',
            markers=True,
            title='Sprint Completion Rate Over Time',
            labels={'Completion %': 'Completion Rate (%)'}
        )
        fig.add_hline(y=100, line_dash="dash", line_color="green", annotation_text="100% Target")
        fig.add_hline(y=80, line_dash="dash", line_color="orange", annotation_text="80% Baseline")
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Task volume trend
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Task Volume Trend")
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='Total Tasks',
                x=trends_df['Sprint'],
                y=trends_df['Total Tasks'],
                marker_color='lightblue'
            ))
            fig.add_trace(go.Bar(
                name='Completed',
                x=trends_df['Sprint'],
                y=trends_df['Completed'],
                marker_color='green'
            ))
            
            fig.update_layout(
                barmode='group',
                title='Total vs Completed Tasks',
                xaxis_title='Sprint',
                yaxis_title='Number of Tasks'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("⏱️ Effort Trend")
            
            fig = px.bar(
                trends_df,
                x='Sprint',
                y='Total Hours',
                title='Total Estimated Hours per Sprint',
                labels={'Total Hours': 'Hours'}
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Task type distribution over time
        st.subheader("📋 Task Type Distribution")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            name='IR Tasks',
            x=trends_df['Sprint'],
            y=trends_df['IR Tasks'],
            mode='lines+markers',
            line=dict(color='red', width=2),
            marker=dict(size=8)
        ))
        fig.add_trace(go.Scatter(
            name='SR Tasks',
            x=trends_df['Sprint'],
            y=trends_df['SR Tasks'],
            mode='lines+markers',
            line=dict(color='blue', width=2),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            title='IR vs SR Tasks Over Time',
            xaxis_title='Sprint',
            yaxis_title='Number of Tasks'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Average days open trend
        st.subheader("📅 Average Days Open Trend")
        
        fig = px.line(
            trends_df,
            x='Sprint',
            y='Avg Days Open',
            markers=True,
            title='Average Task Age Over Time',
            labels={'Avg Days Open': 'Average Days Open'}
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Summary statistics table
        st.subheader("📊 Sprint Comparison Table")
        
        st.dataframe(
            trends_df[['Sprint', 'Total Tasks', 'Completed', 'Completion %', 
                       'Total Hours', 'Avg Days Open', 'IR Tasks', 'SR Tasks']],
            use_container_width=True,
            hide_index=True
        )

with tab4:
    st.subheader("🔍 Search Across All Past Sprints")
    
    # Search options
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_text = st.text_input(
            "Search in Subject or Task/Ticket Number",
            placeholder="Enter task number, ticket number, or keywords..."
        )
    
    with col2:
        search_sprint = st.multiselect(
            "Filter by Sprint",
            options=sprint_numbers,
            default=None,
            format_func=lambda x: f"Sprint {x}"
        )
    
    # Additional filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        search_status = st.multiselect(
            "Status",
            options=past_sprints_df['Status'].unique(),
            default=None
        )
    
    with col2:
        search_section = st.multiselect(
            "Section",
            options=sorted(past_sprints_df['Section'].unique()),
            default=None
        )
    
    with col3:
        search_assignee = st.multiselect(
            "Assignee",
            options=sorted(past_sprints_df['AssignedTo'].dropna().unique()),
            default=None
        )
    
    with col4:
        search_type = st.multiselect(
            "Ticket Type",
            options=past_sprints_df['TicketType'].unique(),
            default=None
        )
    
    # Apply search and filters
    search_results = past_sprints_df.copy()
    
    if search_text:
        search_mask = (
            search_results['Subject'].str.contains(search_text, case=False, na=False) |
            search_results['TaskNum'].astype(str).str.contains(search_text, na=False) |
            search_results['TicketNum'].astype(str).str.contains(search_text, na=False)
        )
        search_results = search_results[search_mask]
    
    if search_sprint:
        search_results = search_results[search_results['SprintNumber'].isin(search_sprint)]
    
    if search_status:
        search_results = search_results[search_results['Status'].isin(search_status)]
    
    if search_section:
        search_results = search_results[search_results['Section'].isin(search_section)]
    
    if search_assignee:
        search_results = search_results[search_results['AssignedTo'].isin(search_assignee)]
    
    if search_type:
        search_results = search_results[search_results['TicketType'].isin(search_type)]
    
    # Display results
    st.caption(f"Found **{len(search_results)}** task(s) matching criteria")
    
    if not search_results.empty:
        # Use display names if available
        sr_assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in search_results.columns else 'AssignedTo'
        
        # Display columns
        display_cols = [
            'SprintNumber', 'TaskNum', 'TicketNum', 'TicketType', 
            'Section', 'Status', sr_assignee_col,
            'Subject', 'HoursEstimated', 'DaysOpen'
        ]
        
        available_cols = [col for col in display_cols if col in search_results.columns]
        display_df = search_results[available_cols].sort_values(['SprintNumber', 'TaskNum'], ascending=[False, True]).copy()
        
        # Configure AgGrid
        gb = GridOptionsBuilder.from_dataframe(display_df)
        gb.configure_default_column(resizable=True, filterable=True, sortable=True)
        gb.configure_column('SprintNumber', header_name='Sprint', width=70)
        gb.configure_column('TaskNum', header_name='Task #', width=90)
        gb.configure_column('TicketNum', header_name='Ticket #', width=100)
        gb.configure_column('TicketType', header_name='Type', width=60)
        gb.configure_column('Section', width=80)
        gb.configure_column('Status', width=100, cellStyle=STATUS_CELL_STYLE)
        gb.configure_column(sr_assignee_col, header_name='Assignee', width=120)
        gb.configure_column('Subject', width=180, tooltipField='Subject')
        gb.configure_column('HoursEstimated', header_name='Est. Hours', width=90)
        gb.configure_column('DaysOpen', header_name='Days Open', width=80, cellStyle=DAYS_OPEN_CELL_STYLE)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=100)
        
        grid_options = gb.build()
        
        AgGrid(
            display_df,
            gridOptions=grid_options,
            allow_unsafe_jscode=True,
            height=400,
            theme='streamlit',
            fit_columns_on_grid_load=False,
            enable_enterprise_modules=False,
            custom_css=get_custom_css()
        )
        
        # Export search results
        st.divider()
        
        col1, col2, col3 = st.columns([1, 1, 3])
        
        with col1:
            excel_data = export_to_excel(search_results)
            st.download_button(
                "📥 Export Results (Excel)",
                excel_data,
                "search_results.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col2:
            csv_data = export_to_csv(search_results)
            st.download_button(
                "📥 Export Results (CSV)",
                csv_data,
                "search_results.csv",
                "text/csv",
                use_container_width=True
            )
    else:
        st.info("No tasks found matching the search criteria")

# Footer with overall statistics
st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Archived Sprints", total_archived_sprints)

with col2:
    st.metric("Total Archived Tasks", total_archived_tasks)

with col3:
    all_completed = len(past_sprints_df[past_sprints_df['Status'] == 'Completed'])
    overall_completion = (all_completed / total_archived_tasks * 100) if total_archived_tasks > 0 else 0
    st.metric("Overall Completion Rate", f"{overall_completion:.1f}%")

with col4:
    all_hours = past_sprints_df['HoursEstimated'].sum()
    st.metric("Total Hours Tracked", f"{all_hours:.1f}")
