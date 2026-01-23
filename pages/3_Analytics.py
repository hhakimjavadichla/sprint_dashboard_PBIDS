"""
Analytics Page
Charts and insights about sprint progress
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from modules.task_store import get_task_store
from modules.tat_calculator import calculate_tat_metrics
from modules.capacity_validator import calculate_team_capacity_metrics
from components.auth import require_auth, display_user_info, get_user_role, get_user_section
from components.metrics_dashboard import (
    display_priority_breakdown,
    display_type_breakdown,
    display_section_breakdown
)
from utils.exporters import generate_sprint_summary, format_summary_report

st.title("Analytics")

# Require authentication
require_auth("Analytics")

# Display user info
display_user_info()

# Load data from task store
task_store = get_task_store()
sprint_df = task_store.get_current_sprint_tasks()

if sprint_df is None or sprint_df.empty:
    st.warning("⚠️ No tasks in current sprint")
    st.info("Upload tasks to view analytics")
    st.stop()

# Filter for section users
user_role = get_user_role()
user_section = get_user_section()

if user_role != 'Admin' and user_section:
    sprint_df = sprint_df[sprint_df['Section'] == user_section]
    st.info(f"👁️ Viewing analytics for: **{user_section}**")

# Check if data is available after filtering
if sprint_df.empty:
    st.warning("No tasks available for analytics in your section.")
    st.caption("Tasks may not be assigned to your section yet, or you may need to check with an administrator.")
    st.stop()

# Sprint header
sprint_num = sprint_df['SprintNumber'].iloc[0]
sprint_name = sprint_df.get('SprintName', pd.Series([f"Sprint {sprint_num}"])).iloc[0]

st.subheader(f"{sprint_name} Analytics")

# Tabs for different analytics views
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Overview",
    "⏰ TAT Analysis", 
    "👥 Team Performance",
    "📋 Summary Report"
])

with tab1:
    st.subheader("Sprint Overview")
    
    # Key metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total = len(sprint_df)
    completed = len(sprint_df[sprint_df['TaskStatus'] == 'Completed'])
    in_progress = len(sprint_df[sprint_df['TaskStatus'].isin(['Accepted', 'Assigned', 'Waiting'])])
    pending = len(sprint_df[sprint_df['TaskStatus'].isin(['Logged', 'Pending'])])
    
    with col1:
        st.metric("Total Tasks", total)
    with col2:
        completion_rate = (completed / total * 100) if total > 0 else 0
        st.metric("Completed", completed, delta=f"{completion_rate:.0f}%")
    with col3:
        st.metric("In Progress", in_progress)
    with col4:
        st.metric("Pending", pending)
    with col5:
        avg_days = sprint_df['DaysOpen'].mean() if 'DaysOpen' in sprint_df.columns else 0
        st.metric("Avg Days Open", f"{avg_days:.1f}")
    
    st.divider()
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        display_priority_breakdown(sprint_df)
    
    with col2:
        display_type_breakdown(sprint_df)
    
    st.divider()
    
    # Section breakdown (admin only)
    if user_role == 'Admin':
        display_section_breakdown(sprint_df)
    
    st.divider()
    
    # Status over time (simulated - in real implementation would track changes)
    st.subheader("Task Distribution by Assignee")
    
    if 'AssignedTo' in sprint_df.columns:
        assignee_counts = sprint_df['AssignedTo'].value_counts().head(10)
        
        fig = px.bar(
            x=assignee_counts.values,
            y=assignee_counts.index,
            orientation='h',
            labels={'x': 'Number of Tasks', 'y': 'Assignee'},
            title='Top 10 Assignees by Task Count',
            color=assignee_counts.values,
            color_continuous_scale='Blues'
        )
        
        st.plotly_chart(fig, width="stretch")
    
    st.divider()
    
    # Average Days Open by Ticket Type (excluding forever tickets)
    st.subheader("Average Days Open by Ticket Type")
    st.caption("Excludes Standing Meetings and Miscellaneous Meetings")
    
    from modules.section_filter import exclude_forever_tickets
    
    # Filter out forever tickets for this metric
    filtered_for_days = exclude_forever_tickets(sprint_df)
    
    if not filtered_for_days.empty and 'TicketType' in filtered_for_days.columns and 'DaysOpen' in filtered_for_days.columns:
        # Always show all 4 types in order: IR, SR, PR, NC
        all_types = ['IR', 'SR', 'PR', 'NC']
        
        # Calculate avg days open by ticket type
        days_by_type_raw = filtered_for_days.groupby('TicketType')['DaysOpen'].agg(['mean', 'count']).reset_index()
        days_by_type_raw.columns = ['Ticket Type', 'Avg Days Open', 'Task Count']
        
        # Create complete dataframe with all types (0 for missing)
        days_by_type = pd.DataFrame({'Ticket Type': all_types})
        days_by_type = days_by_type.merge(days_by_type_raw, on='Ticket Type', how='left')
        days_by_type['Avg Days Open'] = days_by_type['Avg Days Open'].fillna(0).round(1)
        days_by_type['Task Count'] = days_by_type['Task Count'].fillna(0).astype(int)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Bar chart
            type_labels = {
                'IR': '🚨 Incident Request (IR)',
                'SR': '📋 Service Request (SR)',
                'PR': '🎯 Project Request (PR)',
                'NC': '❓ Not Classified (NC)'
            }
            
            chart_df = days_by_type.copy()
            chart_df['Type Label'] = chart_df['Ticket Type'].map(type_labels).fillna(chart_df['Ticket Type'])
            
            fig = px.bar(
                chart_df,
                x='Type Label',
                y='Avg Days Open',
                text='Avg Days Open',
                title='Average Days Open by Type (Forever Tickets Excluded)',
                labels={'Type Label': 'Ticket Type', 'Avg Days Open': 'Avg Days Open'},
                color='Avg Days Open',
                color_continuous_scale='Reds'
            )
            fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Summary table
            display_df = days_by_type.copy()
            display_df['Ticket Type'] = display_df['Ticket Type'].map(type_labels).fillna(display_df['Ticket Type'])
            
            st.dataframe(
                display_df[['Ticket Type', 'Avg Days Open', 'Task Count']],
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("No task data available for days open analysis")

with tab2:
    st.subheader("Turn-Around Time (TAT) Analysis")
    
    tat_metrics = calculate_tat_metrics(sprint_df)
    
    # TAT Compliance metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Overall At Risk",
            tat_metrics['total_at_risk'],
            help="Tasks approaching TAT threshold"
        )
    
    with col2:
        st.metric(
            "TAT Exceeded",
            tat_metrics['total_exceeded'],
            delta="⚠️" if tat_metrics['total_exceeded'] > 0 else "✅",
            help="Tasks that have exceeded TAT limits"
        )
    
    with col3:
        st.metric(
            "IR Compliance",
            f"{tat_metrics['ir_compliance_rate']:.0f}%",
            help="Percentage of IR tasks within TAT"
        )
    
    with col4:
        st.metric(
            "SR Compliance",
            f"{tat_metrics['sr_compliance_rate']:.0f}%",
            help="Percentage of SR tasks within TAT"
        )
    
    st.divider()
    
    # TAT breakdown by type
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚨 Incident Requests (IR)")
        
        ir_data = pd.DataFrame({
            'Metric': ['Total', 'At Risk', 'Exceeded TAT', 'Compliance'],
            'Value': [
                str(tat_metrics['ir_tasks']),
                str(tat_metrics['ir_at_risk']),
                str(tat_metrics['ir_exceeded_tat']),
                f"{tat_metrics['ir_compliance_rate']:.1f}%"
            ]
        })
        
        st.dataframe(ir_data, use_container_width=True, hide_index=True)
        
        if tat_metrics['ir_exceeded_tat'] > 0:
            st.error(f"⚠️ {tat_metrics['ir_exceeded_tat']} IR tasks exceeded 0.8 day TAT")
        else:
            st.success("✅ All IR tasks within TAT")
    
    with col2:
        st.subheader("Service Requests (SR)")
        
        sr_data = pd.DataFrame({
            'Metric': ['Total', 'At Risk', 'Exceeded TAT', 'Compliance'],
            'Value': [
                str(tat_metrics['sr_tasks']),
                str(tat_metrics['sr_at_risk']),
                str(tat_metrics['sr_exceeded_tat']),
                f"{tat_metrics['sr_compliance_rate']:.1f}%"
            ]
        })
        
        st.dataframe(sr_data, use_container_width=True, hide_index=True)
        
        if tat_metrics['sr_exceeded_tat'] > 0:
            st.error(f"⚠️ {tat_metrics['sr_exceeded_tat']} SR tasks exceeded 22 day TAT")
        else:
            st.success("✅ All SR tasks within TAT")
    
    st.divider()
    
    # Days open distribution
    st.subheader("Task Age Distribution")
    
    if 'DaysOpen' in sprint_df.columns:
        fig = px.histogram(
            sprint_df,
            x='DaysOpen',
            nbins=20,
            title='Distribution of Days Open',
            labels={'DaysOpen': 'Days Open', 'count': 'Number of Tasks'},
            color_discrete_sequence=['#1f77b4']
        )
        
        # Add TAT threshold lines
        fig.add_vline(x=0.8, line_dash="dash", line_color="red", annotation_text="IR TAT (0.8d)")
        fig.add_vline(x=22, line_dash="dash", line_color="orange", annotation_text="SR TAT (22d)")
        
        st.plotly_chart(fig, width="stretch")

with tab3:
    st.subheader("Team Performance & Capacity")
    
    if user_role != 'Admin':
        st.info("Full team analytics available for administrators only")
        st.info("Contact your admin for comprehensive team reports")
    else:
        # Capacity metrics
        capacity_metrics = calculate_team_capacity_metrics(sprint_df)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Team Size",
                capacity_metrics['num_people'],
                help="Number of people with assignments"
            )
        
        with col2:
            st.metric(
                "Team Capacity",
                f"{capacity_metrics['total_team_capacity']:.0f}h",
                help="Total available capacity (52h × team size)"
            )
        
        with col3:
            st.metric(
                "Allocated Hours",
                f"{capacity_metrics['total_allocated']:.0f}h",
                help="Total hours assigned"
            )
        
        with col4:
            st.metric(
                "Utilization",
                f"{capacity_metrics['utilization_percentage']:.0f}%",
                help="Percentage of capacity allocated"
            )
        
        st.divider()
        
        # Capacity status
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🟢 OK", capacity_metrics['num_ok'], help="Under 45 hours")
        with col2:
            st.metric("🟡 Warning", capacity_metrics['num_warnings'], help="45-52 hours")
        with col3:
            st.metric("🔴 Overload", capacity_metrics['num_overloaded'], help="Over 52 hours")
        
        st.divider()
        
        # Team member performance table
        st.subheader("Individual Performance")
        
        if 'AssignedTo' in sprint_df.columns:
            team_stats = []
            
            for person in sprint_df['AssignedTo'].dropna().unique():
                person_tasks = sprint_df[sprint_df['AssignedTo'] == person]
                
                team_stats.append({
                    'Team Member': person,
                    'Total Tasks': len(person_tasks),
                    'Completed': len(person_tasks[person_tasks['TaskStatus'] == 'Completed']),
                    'In Progress': len(person_tasks[person_tasks['TaskStatus'].isin(['Accepted', 'Assigned', 'Waiting'])]),
                    'Estimated Hours': person_tasks['HoursEstimated'].sum(),
                    'Avg Days Open': person_tasks['DaysOpen'].mean()
                })
            
            team_df = pd.DataFrame(team_stats)
            team_df = team_df.sort_values('Total Tasks', ascending=False)
            
            st.dataframe(team_df, width="stretch", hide_index=True)

with tab4:
    st.subheader("Sprint Summary Report")
    
    # Generate summary
    summary = generate_sprint_summary(sprint_df)
    report_text = format_summary_report(summary, sprint_num)
    
    # Display in text area
    st.text_area(
        "Summary Report",
        report_text,
        height=600,
        help="Copy this report for documentation"
    )
    
    # Download button
    st.download_button(
        "📥 Download Report",
        report_text,
        f"sprint_{sprint_num}_summary_report.txt",
        "text/plain",
        width="stretch"
    )
    
    st.divider()
    
    # Summary statistics in table format
    st.subheader("Key Statistics")
    
    stats_df = pd.DataFrame({
        'Metric': [
            'Total Tasks',
            'Completed Tasks',
            'Completion Rate',
            'Priority 5 Tasks',
            'At-Risk Tasks',
            'IR Tasks',
            'SR Tasks',
            'Total Estimated Hours',
            'Average Days Open'
        ],
        'Value': [
            str(summary['total_tasks']),
            str(summary['completed_tasks']),
            f"{summary['completion_rate']:.1f}%",
            str(summary['priority_5_count']),
            str(summary['at_risk_count']),
            str(summary['ir_count']),
            str(summary['sr_count']),
            f"{summary['total_estimated_hours']:.1f}",
            f"{summary['avg_days_open']:.1f}"
        ]
    })
    
    st.dataframe(stats_df, use_container_width=True, hide_index=True)

# Export options at bottom
st.divider()

col1, col2 = st.columns([1, 4])

with col1:
    from utils.exporters import export_to_excel
    
    excel_data = export_to_excel(sprint_df)
    st.download_button(
        "📥 Export Full Sprint Data",
        excel_data,
        f"sprint_{sprint_num}_analytics.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
        help="Download complete sprint data with all fields"
    )
