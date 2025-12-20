"""
Reusable metrics dashboard components
"""
import streamlit as st
import pandas as pd
from typing import Optional
from modules.section_filter import exclude_forever_tickets


def display_metric_row(metrics: list):
    """
    Display a row of metrics
    
    Args:
        metrics: List of dicts with keys: label, value, delta (optional), help (optional)
    """
    cols = st.columns(len(metrics))
    
    for idx, metric in enumerate(metrics):
        with cols[idx]:
            st.metric(
                label=metric['label'],
                value=metric['value'],
                delta=metric.get('delta'),
                help=metric.get('help')
            )


def display_sprint_overview(sprint_df: pd.DataFrame):
    """
    Display overview metrics for a sprint
    
    Args:
        sprint_df: Sprint DataFrame
    """
    if sprint_df.empty:
        st.info("No sprint data available")
        return

    sprint_df = exclude_forever_tickets(sprint_df)
    
    # Calculate metrics
    total_tasks = len(sprint_df)
    completed = len(sprint_df[sprint_df['Status'] == 'Completed'])
    in_progress = len(sprint_df[sprint_df['Status'] == 'In Progress'])
    
    # At risk
    at_risk = len(sprint_df[
        ((sprint_df['TicketType'] == 'IR') & (sprint_df['DaysOpen'] >= 0.6)) |
        ((sprint_df['TicketType'] == 'SR') & (sprint_df['DaysOpen'] >= 18))
    ])
    
    # Average days open
    avg_days = sprint_df['DaysOpen'].mean() if 'DaysOpen' in sprint_df.columns else 0
    
    # Display metrics
    metrics = [
        {
            'label': 'Total Tasks',
            'value': total_tasks,
            'help': 'All tasks in current sprint'
        },
        {
            'label': 'Completed',
            'value': completed,
            'delta': f"{(completed/total_tasks*100):.0f}%" if total_tasks > 0 else "0%",
            'help': 'Tasks marked as Completed'
        },
        {
            'label': 'In Progress',
            'value': in_progress,
            'help': 'Tasks currently being worked on'
        },
        {
            'label': 'At Risk',
            'value': at_risk,
            'delta': '⚠️' if at_risk > 0 else '✅',
            'help': 'Tasks approaching or exceeding TAT'
        },
        {
            'label': 'Avg Days Open',
            'value': f"{avg_days:.1f}",
            'help': 'Average age of tasks'
        }
    ]
    
    display_metric_row(metrics)


def display_priority_breakdown(sprint_df: pd.DataFrame):
    """
    Display priority distribution
    
    Args:
        sprint_df: Sprint DataFrame
    """
    if sprint_df.empty:
        return

    sprint_df = exclude_forever_tickets(sprint_df)
    
    st.subheader("Priority Distribution")
    
    priority_counts = sprint_df['CustomerPriority'].dropna().value_counts().sort_index(ascending=False)
    
    if priority_counts.empty:
        st.info("No priority data set yet. Set priorities in Sprint Planning.")
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Bar chart
        import plotly.express as px
        
        priority_labels = {
            5: '🔴 Critical',
            4: '🟠 High',
            3: '🟡 Medium',
            2: '🟢 Low',
            1: '⚪ Minimal',
            0: '⚫ None'
        }
        
        chart_df = pd.DataFrame({
            'Priority': [priority_labels.get(p, f'P{p}') for p in priority_counts.index],
            'Count': priority_counts.values
        })
        
        fig = px.bar(
            chart_df,
            x='Priority',
            y='Count',
            title='Tasks by Priority',
            color='Count',
            color_continuous_scale='RdYlGn_r'
        )
        
        st.plotly_chart(fig, width="stretch")
    
    with col2:
        # Summary table
        st.dataframe(
            chart_df,
            width="stretch",
            hide_index=True
        )


def display_type_breakdown(sprint_df: pd.DataFrame):
    """
    Display ticket type distribution
    
    Args:
        sprint_df: Sprint DataFrame
    """
    if sprint_df.empty:
        return

    sprint_df = exclude_forever_tickets(sprint_df)

    st.subheader("Ticket Type Distribution")
    
    # Always show all 4 types in order: IR, SR, PR, NC
    all_types = ['IR', 'SR', 'PR', 'NC']
    type_counts = sprint_df['TicketType'].value_counts()
    
    # Create ordered series with all types (0 for missing types)
    ordered_counts = pd.Series({t: type_counts.get(t, 0) for t in all_types})
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Pie chart
        import plotly.express as px
        
        type_labels = {
            'IR': '🚨 Incident Request (IR)',
            'SR': '📋 Service Request (SR)',
            'PR': '🎯 Project Request (PR)',
            'NC': '❓ Not Classified (NC)'
        }
        
        chart_df = pd.DataFrame({
            'Type': [type_labels.get(t, t) for t in ordered_counts.index],
            'Count': ordered_counts.values
        })
        
        fig = px.pie(
            chart_df,
            values='Count',
            names='Type',
            title='Tasks by Type'
        )
        
        st.plotly_chart(fig, width="stretch")
    
    with col2:
        st.dataframe(
            chart_df,
            width="stretch",
            hide_index=True
        )


def display_status_breakdown(sprint_df: pd.DataFrame):
    """
    Display status distribution
    
    Args:
        sprint_df: Sprint DataFrame
    """
    if sprint_df.empty:
        return

    sprint_df = exclude_forever_tickets(sprint_df)

    status_counts = sprint_df['Status'].value_counts()
    
    # Horizontal bar chart
    import plotly.express as px
    
    chart_df = pd.DataFrame({
        'Status': status_counts.index,
        'Count': status_counts.values
    })
    
    fig = px.bar(
        chart_df,
        y='Status',
        x='Count',
        orientation='h',
        title='Tasks by Status',
        color='Count',
        color_continuous_scale='Blues'
    )
    
    st.plotly_chart(fig, width="stretch")


def display_section_breakdown(sprint_df: pd.DataFrame):
    """
    Display section distribution
    
    Args:
        sprint_df: Sprint DataFrame
    """
    if sprint_df.empty or 'Section' not in sprint_df.columns:
        return

    sprint_df = exclude_forever_tickets(sprint_df)
    
    st.subheader("Section Distribution")
    
    section_counts = sprint_df['Section'].value_counts()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        import plotly.express as px
        
        chart_df = pd.DataFrame({
            'Section': section_counts.index,
            'Count': section_counts.values
        })
        
        fig = px.bar(
            chart_df,
            x='Section',
            y='Count',
            title='Tasks by Section',
            color='Count',
            color_continuous_scale='Viridis'
        )
        
        st.plotly_chart(fig, width="stretch")
    
    with col2:
        st.dataframe(
            chart_df,
            width="stretch",
            hide_index=True
        )
