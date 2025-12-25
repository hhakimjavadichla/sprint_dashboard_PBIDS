"""
Completed Tasks Page
View and analyze all completed tasks with their sprint history
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from modules.task_store import get_task_store
from modules.sprint_calendar import get_sprint_calendar
from components.auth import require_admin, display_user_info
from utils.exporters import export_to_excel, export_to_csv
from utils.grid_styles import apply_grid_styles, get_custom_css, STATUS_CELL_STYLE, PRIORITY_CELL_STYLE, DAYS_OPEN_CELL_STYLE, COLUMN_WIDTHS

st.set_page_config(
    page_title="Completed Tasks",
    page_icon="✅",
    layout="wide"
)

# Apply custom tooltip styles
apply_grid_styles()

st.title("✅ Completed Tasks")
st.caption("_Historical view of all completed tasks — PBIDS Team_")

# Require admin access
require_admin("Completed Tasks")

# Display user info
display_user_info()

# Load task store and calendar
task_store = get_task_store()
calendar = get_sprint_calendar()
current_sprint = calendar.get_current_sprint()
current_sprint_num = current_sprint['SprintNumber'] if current_sprint else 999

# Get all tasks
all_tasks = task_store.get_all_tasks()

if all_tasks.empty:
    st.info("📭 No tasks found in the system")
    st.write("Upload tasks first to view completed tasks.")
    st.page_link("pages/2_📤_Upload_Tasks.py", label="📤 Upload Tasks", icon="📤")
    st.stop()

# Filter to completed tasks only
completed_statuses = ['Completed', 'Closed', 'Resolved']
completed_tasks = all_tasks[all_tasks['Status'].isin(completed_statuses)].copy()

if completed_tasks.empty:
    st.info("📭 No completed tasks found")
    st.write("Completed tasks will appear here as they are finished.")
    st.stop()

# Calculate sprint history for each task
# A task shows as "Active" in sprints from OriginalSprintNumber to (CompletedSprintNumber - 1)
# and "Completed" in CompletedSprintNumber
def get_completed_sprint(row):
    """Determine which sprint a task was completed in based on SprintsAssigned"""
    sprints_assigned = str(row.get('SprintsAssigned', '')).strip()
    if sprints_assigned:
        try:
            sprint_list = [int(s.strip()) for s in sprints_assigned.split(',') if s.strip()]
            if sprint_list:
                return max(sprint_list)  # Completed in the last assigned sprint
        except:
            pass
    # Fallback to OriginalSprintNumber
    return row.get('OriginalSprintNumber', current_sprint_num)

completed_tasks['CompletedInSprint'] = completed_tasks.apply(get_completed_sprint, axis=1)

# Get all sprints for reference
all_sprints = calendar.get_all_sprints()

# Summary statistics
total_completed = len(completed_tasks)
unique_tickets = completed_tasks['TicketNum'].nunique()
unique_sections = completed_tasks['Section'].nunique()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("✅ Completed Tasks", total_completed)
with col2:
    st.metric("🎫 Unique Tickets", unique_tickets)
with col3:
    st.metric("📊 Sections", unique_sections)
with col4:
    total_hours = completed_tasks['HoursEstimated'].sum() if 'HoursEstimated' in completed_tasks.columns else 0
    st.metric("⏱️ Total Hours", f"{total_hours:.1f}")

st.divider()

# Tabs for different views
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 All Completed Tasks",
    "📊 By Sprint",
    "📈 Trends & Analytics",
    "🔍 Search Tasks"
])

with tab1:
    st.subheader("All Completed Tasks")
    st.caption("Tasks that have been completed, showing which sprint they were completed in")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        sections = ['All'] + sorted(completed_tasks['Section'].dropna().unique().tolist())
        section_filter = st.selectbox("Section", sections, key="ct_section")
    
    with col2:
        ticket_types = ['All'] + sorted(completed_tasks['TicketType'].dropna().unique().tolist())
        type_filter = st.selectbox("Ticket Type", ticket_types, key="ct_type")
    
    with col3:
        assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in completed_tasks.columns else 'AssignedTo'
        assignees = ['All'] + sorted(completed_tasks[assignee_col].dropna().unique().tolist())
        assignee_filter = st.selectbox("Assignee", assignees, key="ct_assignee")
    
    with col4:
        sprint_nums = ['All'] + sorted(completed_tasks['CompletedInSprint'].dropna().unique().tolist(), reverse=True)
        sprint_filter = st.selectbox("Completed In Sprint", sprint_nums, key="ct_sprint")
    
    # Apply filters
    display_tasks = completed_tasks.copy()
    
    if section_filter != 'All':
        display_tasks = display_tasks[display_tasks['Section'] == section_filter]
    if type_filter != 'All':
        display_tasks = display_tasks[display_tasks['TicketType'] == type_filter]
    if assignee_filter != 'All':
        display_tasks = display_tasks[display_tasks[assignee_col] == assignee_filter]
    if sprint_filter != 'All':
        display_tasks = display_tasks[display_tasks['CompletedInSprint'] == sprint_filter]
    
    st.caption(f"Showing {len(display_tasks)} of {total_completed} completed tasks")
    
    # Calculate TaskCount for multi-task tickets
    if 'TicketNum' in display_tasks.columns:
        ticket_counts = display_tasks.groupby('TicketNum').size().to_dict()
        display_tasks = display_tasks.sort_values(
            by=['CompletedInSprint', 'TicketNum', 'TaskNum'],
            ascending=[False, True, True]
        ).reset_index(drop=True)
        
        task_counts = []
        ticket_group_ids = []
        current_group = 0
        prev_ticket = None
        task_counter = {}
        
        for idx, row in display_tasks.iterrows():
            ticket = row['TicketNum']
            total = ticket_counts.get(ticket, 1)
            
            if ticket not in task_counter:
                task_counter[ticket] = 0
            task_counter[ticket] += 1
            task_counts.append(f"{task_counter[ticket]}/{total}")
            
            if ticket != prev_ticket:
                current_group += 1
                prev_ticket = ticket
            ticket_group_ids.append(current_group)
        
        display_tasks['TaskCount'] = task_counts
        display_tasks['_TicketGroup'] = ticket_group_ids
        display_tasks['_IsMultiTask'] = display_tasks['TicketNum'].map(lambda x: ticket_counts.get(x, 1) > 1)
    
    # Use display names
    if 'AssignedTo_Display' in display_tasks.columns:
        display_tasks['AssignedTo'] = display_tasks['AssignedTo_Display']
    
    # Display columns
    display_cols = [
        'CompletedInSprint', 'TicketNum', 'TaskCount', '_TicketGroup', '_IsMultiTask',
        'TicketType', 'Section', 'TaskNum', 'Status', 'AssignedTo', 
        'CustomerName', 'Subject', 'HoursEstimated', 'DaysOpen'
    ]
    
    available_cols = [col for col in display_cols if col in display_tasks.columns]
    grid_df = display_tasks[available_cols].copy()
    
    # Configure AgGrid
    gb = GridOptionsBuilder.from_dataframe(grid_df)
    gb.configure_default_column(resizable=True, filterable=True, sortable=True)
    
    gb.configure_column('CompletedInSprint', header_name='Sprint', width=COLUMN_WIDTHS['CompletedInSprint'])
    gb.configure_column('TicketNum', header_name='Ticket #', width=COLUMN_WIDTHS['TicketNum'])
    gb.configure_column('TaskCount', header_name='Task#', width=COLUMN_WIDTHS['TaskCount'])
    gb.configure_column('_TicketGroup', hide=True)
    gb.configure_column('_IsMultiTask', hide=True)
    gb.configure_column('TicketType', header_name='Type', width=COLUMN_WIDTHS['TicketType'])
    gb.configure_column('Section', width=COLUMN_WIDTHS['Section'])
    gb.configure_column('TaskNum', header_name='Task #', width=COLUMN_WIDTHS['TaskNum'])
    gb.configure_column('Status', width=COLUMN_WIDTHS['Status'])
    gb.configure_column('AssignedTo', header_name='Assignee', width=COLUMN_WIDTHS['AssignedTo'])
    gb.configure_column('CustomerName', header_name='Customer', width=COLUMN_WIDTHS['CustomerName'])
    gb.configure_column('Subject', width=COLUMN_WIDTHS['Subject'], tooltipField='Subject')
    gb.configure_column('HoursEstimated', header_name='Est. Hours', width=COLUMN_WIDTHS['HoursEstimated'])
    gb.configure_column('DaysOpen', header_name='Days Open', width=COLUMN_WIDTHS['DaysOpen'])
    
    gb.configure_pagination(enabled=False)
    
    # Row styling for multi-task ticket groups
    row_style_jscode = JsCode("""
    function(params) {
        if (params.data._IsMultiTask) {
            if (params.data._TicketGroup % 2 === 0) {
                return { 'backgroundColor': '#e8f4e8' };
            } else {
                return { 'backgroundColor': '#e8e8f4' };
            }
        }
        return null;
    }
    """)
    
    grid_options = gb.build()
    grid_options['getRowStyle'] = row_style_jscode
    
    AgGrid(
        grid_df,
        gridOptions=grid_options,
        allow_unsafe_jscode=True,
        height=500,
        theme='streamlit',
        fit_columns_on_grid_load=False,
        enable_enterprise_modules=False,
        custom_css=get_custom_css()
    )
    
    # Export
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 3])
    
    with col1:
        excel_data = export_to_excel(display_tasks)
        st.download_button(
            "📥 Export Excel",
            excel_data,
            "completed_tasks.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col2:
        csv_data = export_to_csv(display_tasks)
        st.download_button(
            "📥 Export CSV",
            csv_data,
            "completed_tasks.csv",
            "text/csv",
            use_container_width=True
        )

with tab2:
    st.subheader("Completed Tasks by Sprint")
    st.caption("View task completion history for each sprint")
    
    # Get sprints that have completed tasks
    sprints_with_completed = sorted(completed_tasks['CompletedInSprint'].dropna().unique(), reverse=True)
    
    if not sprints_with_completed:
        st.info("No sprints with completed tasks found")
    else:
        # Sprint selector
        selected_sprint = st.selectbox(
            "Select Sprint",
            options=sprints_with_completed,
            format_func=lambda x: f"Sprint {int(x)}"
        )
        
        if selected_sprint:
            sprint_completed = completed_tasks[completed_tasks['CompletedInSprint'] == selected_sprint].copy()
            
            # Get sprint info
            sprint_info = calendar.get_sprint_by_number(int(selected_sprint))
            
            if sprint_info:
                st.markdown(f"### Sprint {int(selected_sprint)}: {sprint_info['SprintName']}")
                st.caption(f"📅 {sprint_info['SprintStartDt'].strftime('%m/%d/%Y')} - {sprint_info['SprintEndDt'].strftime('%m/%d/%Y')}")
            else:
                st.markdown(f"### Sprint {int(selected_sprint)}")
            
            st.divider()
            
            # Metrics
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("✅ Completed", len(sprint_completed))
            with col2:
                ir_count = len(sprint_completed[sprint_completed['TicketType'] == 'IR'])
                st.metric("🚨 IR Tasks", ir_count)
            with col3:
                sr_count = len(sprint_completed[sprint_completed['TicketType'] == 'SR'])
                st.metric("📋 SR Tasks", sr_count)
            with col4:
                hours = sprint_completed['HoursEstimated'].sum() if 'HoursEstimated' in sprint_completed.columns else 0
                st.metric("⏱️ Total Hours", f"{hours:.1f}")
            with col5:
                sections = sprint_completed['Section'].nunique()
                st.metric("📊 Sections", sections)
            
            st.divider()
            
            # Charts
            col1, col2 = st.columns(2)
            
            with col1:
                # Section distribution
                section_counts = sprint_completed['Section'].value_counts().head(10)
                if not section_counts.empty:
                    fig = px.bar(
                        x=section_counts.values,
                        y=section_counts.index,
                        orientation='h',
                        labels={'x': 'Tasks', 'y': 'Section'},
                        title='Tasks by Section'
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Assignee distribution
                assignee_counts = sprint_completed['AssignedTo'].value_counts().head(10)
                if not assignee_counts.empty:
                    fig = px.bar(
                        x=assignee_counts.values,
                        y=assignee_counts.index,
                        orientation='h',
                        labels={'x': 'Tasks', 'y': 'Assignee'},
                        title='Tasks by Assignee'
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            
            # Task list
            st.subheader("Task Details")
            
            # Use display names
            if 'AssignedTo_Display' in sprint_completed.columns:
                sprint_completed['AssignedTo'] = sprint_completed['AssignedTo_Display']
            
            display_cols = [
                'TicketNum', 'TicketType', 'Section', 'TaskNum', 
                'Status', 'AssignedTo', 'Subject', 'HoursEstimated', 'DaysOpen'
            ]
            
            available_cols = [col for col in display_cols if col in sprint_completed.columns]
            display_df = sprint_completed[available_cols].copy()
            
            gb = GridOptionsBuilder.from_dataframe(display_df)
            gb.configure_default_column(resizable=True, filterable=True, sortable=True)
            gb.configure_column('TicketNum', header_name='Ticket #', width=COLUMN_WIDTHS['TicketNum'])
            gb.configure_column('TicketType', header_name='Type', width=COLUMN_WIDTHS['TicketType'])
            gb.configure_column('Section', width=COLUMN_WIDTHS['Section'])
            gb.configure_column('TaskNum', header_name='Task #', width=COLUMN_WIDTHS['TaskNum'])
            gb.configure_column('Status', width=COLUMN_WIDTHS['Status'])
            gb.configure_column('AssignedTo', header_name='Assignee', width=COLUMN_WIDTHS['AssignedTo'])
            gb.configure_column('Subject', width=COLUMN_WIDTHS['Subject'], tooltipField='Subject')
            gb.configure_column('HoursEstimated', header_name='Est. Hours', width=COLUMN_WIDTHS['HoursEstimated'])
            gb.configure_column('DaysOpen', header_name='Days Open', width=COLUMN_WIDTHS['DaysOpen'])
            gb.configure_pagination(enabled=False)
            
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

with tab3:
    st.subheader("Completion Trends & Analytics")
    
    # Calculate completion stats by sprint
    sprints_with_data = sorted(completed_tasks['CompletedInSprint'].dropna().unique())
    
    if len(sprints_with_data) < 2:
        st.info("📊 Need at least 2 sprints with completed tasks to show trends")
    else:
        trends_data = []
        
        for sprint_num in sprints_with_data:
            sprint_data = completed_tasks[completed_tasks['CompletedInSprint'] == sprint_num]
            
            ir_count = len(sprint_data[sprint_data['TicketType'] == 'IR'])
            sr_count = len(sprint_data[sprint_data['TicketType'] == 'SR'])
            total_hours = sprint_data['HoursEstimated'].sum() if 'HoursEstimated' in sprint_data.columns else 0
            avg_days = sprint_data['DaysOpen'].mean() if 'DaysOpen' in sprint_data.columns else 0
            
            trends_data.append({
                'Sprint': f"Sprint {int(sprint_num)}",
                'Sprint #': int(sprint_num),
                'Completed Tasks': len(sprint_data),
                'IR Tasks': ir_count,
                'SR Tasks': sr_count,
                'Total Hours': total_hours,
                'Avg Days Open': avg_days
            })
        
        trends_df = pd.DataFrame(trends_data)
        
        # Completion volume trend
        st.subheader("📈 Completion Volume Trend")
        
        fig = px.bar(
            trends_df,
            x='Sprint',
            y='Completed Tasks',
            title='Tasks Completed per Sprint',
            color='Completed Tasks',
            color_continuous_scale='greens'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Task type distribution over time
        col1, col2 = st.columns(2)
        
        with col1:
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
                title='IR vs SR Completions',
                xaxis_title='Sprint',
                yaxis_title='Tasks'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("⏱️ Effort Trend")
            
            fig = px.bar(
                trends_df,
                x='Sprint',
                y='Total Hours',
                title='Hours Completed per Sprint',
                labels={'Total Hours': 'Hours'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Average days open trend
        st.subheader("📅 Average Resolution Time")
        
        fig = px.line(
            trends_df,
            x='Sprint',
            y='Avg Days Open',
            markers=True,
            title='Average Days to Complete Tasks',
            labels={'Avg Days Open': 'Average Days'}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Summary table
        st.subheader("📊 Sprint Completion Summary")
        st.dataframe(trends_df, use_container_width=True, hide_index=True)

with tab4:
    st.subheader("🔍 Search Completed Tasks")
    
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
            options=sorted(completed_tasks['CompletedInSprint'].dropna().unique(), reverse=True),
            default=None,
            format_func=lambda x: f"Sprint {int(x)}"
        )
    
    # Additional filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        search_section = st.multiselect(
            "Section",
            options=sorted(completed_tasks['Section'].dropna().unique()),
            default=None
        )
    
    with col2:
        assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in completed_tasks.columns else 'AssignedTo'
        search_assignee = st.multiselect(
            "Assignee",
            options=sorted(completed_tasks[assignee_col].dropna().unique()),
            default=None
        )
    
    with col3:
        search_type = st.multiselect(
            "Ticket Type",
            options=completed_tasks['TicketType'].dropna().unique(),
            default=None
        )
    
    with col4:
        search_customer = st.multiselect(
            "Customer",
            options=sorted(completed_tasks['CustomerName'].dropna().unique()) if 'CustomerName' in completed_tasks.columns else [],
            default=None
        )
    
    # Apply search and filters
    search_results = completed_tasks.copy()
    
    if search_text:
        search_mask = (
            search_results['Subject'].str.contains(search_text, case=False, na=False) |
            search_results['TaskNum'].astype(str).str.contains(search_text, na=False) |
            search_results['TicketNum'].astype(str).str.contains(search_text, na=False)
        )
        search_results = search_results[search_mask]
    
    if search_sprint:
        search_results = search_results[search_results['CompletedInSprint'].isin(search_sprint)]
    
    if search_section:
        search_results = search_results[search_results['Section'].isin(search_section)]
    
    if search_assignee:
        search_results = search_results[search_results[assignee_col].isin(search_assignee)]
    
    if search_type:
        search_results = search_results[search_results['TicketType'].isin(search_type)]
    
    if search_customer and 'CustomerName' in search_results.columns:
        search_results = search_results[search_results['CustomerName'].isin(search_customer)]
    
    # Display results
    st.caption(f"Found **{len(search_results)}** task(s) matching criteria")
    
    if not search_results.empty:
        # Use display names
        if 'AssignedTo_Display' in search_results.columns:
            search_results['AssignedTo'] = search_results['AssignedTo_Display']
        
        display_cols = [
            'CompletedInSprint', 'TicketNum', 'TicketType', 'Section', 'TaskNum',
            'Status', 'AssignedTo', 'Subject', 'HoursEstimated', 'DaysOpen'
        ]
        
        available_cols = [col for col in display_cols if col in search_results.columns]
        display_df = search_results[available_cols].sort_values(['CompletedInSprint', 'TaskNum'], ascending=[False, True]).copy()
        
        gb = GridOptionsBuilder.from_dataframe(display_df)
        gb.configure_default_column(resizable=True, filterable=True, sortable=True)
        gb.configure_column('CompletedInSprint', header_name='Sprint', width=COLUMN_WIDTHS['CompletedInSprint'])
        gb.configure_column('TicketNum', header_name='Ticket #', width=COLUMN_WIDTHS['TicketNum'])
        gb.configure_column('TicketType', header_name='Type', width=COLUMN_WIDTHS['TicketType'])
        gb.configure_column('Section', width=COLUMN_WIDTHS['Section'])
        gb.configure_column('TaskNum', header_name='Task #', width=COLUMN_WIDTHS['TaskNum'])
        gb.configure_column('Status', width=COLUMN_WIDTHS['Status'])
        gb.configure_column('AssignedTo', header_name='Assignee', width=COLUMN_WIDTHS['AssignedTo'])
        gb.configure_column('Subject', width=COLUMN_WIDTHS['Subject'], tooltipField='Subject')
        gb.configure_column('HoursEstimated', header_name='Est. Hours', width=COLUMN_WIDTHS['HoursEstimated'])
        gb.configure_column('DaysOpen', header_name='Days Open', width=COLUMN_WIDTHS['DaysOpen'])
        gb.configure_pagination(enabled=False)
        
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
        
        # Export
        st.divider()
        col1, col2, col3 = st.columns([1, 1, 3])
        
        with col1:
            excel_data = export_to_excel(search_results)
            st.download_button(
                "📥 Export Excel",
                excel_data,
                "search_results.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col2:
            csv_data = export_to_csv(search_results)
            st.download_button(
                "📥 Export CSV",
                csv_data,
                "search_results.csv",
                "text/csv",
                use_container_width=True
            )
    else:
        st.info("No tasks found matching the search criteria")

# Footer
st.divider()
st.caption("💡 **Note:** This page shows all completed tasks for historical analysis. Sprint Planning is for current and future sprints only.")
