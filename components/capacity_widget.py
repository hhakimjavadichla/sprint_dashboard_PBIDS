"""
Capacity validation and display widgets
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from modules.capacity_validator import (
    validate_capacity,
    get_capacity_dataframe,
    get_capacity_chart_data
)
from utils.constants import MAX_CAPACITY_HOURS


def display_capacity_overview(sprint_df: pd.DataFrame):
    """
    Display high-level capacity metrics
    
    Args:
        sprint_df: Sprint DataFrame
    """
    capacity_info = validate_capacity(sprint_df)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Estimated Hours",
            f"{capacity_info['total_hours']:.1f}",
            help="Total effort allocated across all team members"
        )
    
    with col2:
        overload_count = len(capacity_info['overloaded'])
        st.metric(
            "Overloaded People",
            overload_count,
            delta="⚠️ Action needed" if overload_count > 0 else "✅ OK",
            help=f"People with > {MAX_CAPACITY_HOURS} hours assigned"
        )
    
    with col3:
        warning_count = len(capacity_info['warnings'])
        st.metric(
            "Near Capacity",
            warning_count,
            help="People approaching capacity limit"
        )
    
    with col4:
        st.metric(
            "Max Per Person",
            f"{capacity_info['max_capacity']} hrs",
            help="Maximum recommended hours per person per sprint"
        )


def display_capacity_alerts(sprint_df: pd.DataFrame):
    """
    Display capacity warnings and overload alerts
    
    Args:
        sprint_df: Sprint DataFrame
    """
    capacity_info = validate_capacity(sprint_df)
    
    # Overload alerts
    if capacity_info['overloaded']:
        st.error("⚠️ **Capacity Overload Detected!**")
        
        overload_data = []
        for person in capacity_info['overloaded']:
            info = capacity_info['per_person'][person]
            overload_data.append({
                'Person': person,
                'Assigned Hours': info['hours'],
                'Over Capacity By': info['over_capacity'],
                'Percentage': f"{info['percentage']:.0f}%"
            })
        
        overload_df = pd.DataFrame(overload_data)
        st.dataframe(overload_df, width="stretch", hide_index=True)
    
    # Warning alerts
    if capacity_info['warnings']:
        st.warning("⚡ **People Near Capacity Limit**")
        
        warning_data = []
        for person in capacity_info['warnings']:
            info = capacity_info['per_person'][person]
            warning_data.append({
                'Person': person,
                'Assigned Hours': info['hours'],
                'Available': info['available'],
                'Percentage': f"{info['percentage']:.0f}%"
            })
        
        warning_df = pd.DataFrame(warning_data)
        st.dataframe(warning_df, width="stretch", hide_index=True)


def display_capacity_table(sprint_df: pd.DataFrame):
    """
    Display detailed capacity table for all team members
    
    Args:
        sprint_df: Sprint DataFrame
    """
    capacity_df = get_capacity_dataframe(sprint_df)
    
    if capacity_df.empty:
        st.info("No capacity data available. Add effort estimates to see capacity analysis.")
        return
    
    st.subheader("Team Capacity Breakdown")
    
    # Style the dataframe
    def highlight_status(row):
        if row['Status'] == 'OVERLOAD':
            return ['background-color: #ffe6e6'] * len(row)
        elif row['Status'] == 'WARNING':
            return ['background-color: #fff3cd'] * len(row)
        else:
            return ['background-color: #d4edda'] * len(row)
    
    styled_df = capacity_df.style.apply(highlight_status, axis=1)
    
    st.dataframe(styled_df, width="stretch", hide_index=True)


def display_capacity_chart(sprint_df: pd.DataFrame):
    """
    Display capacity visualization chart
    
    Args:
        sprint_df: Sprint DataFrame
    """
    chart_data = get_capacity_chart_data(sprint_df)
    
    if chart_data.empty:
        return
    
    st.subheader("Capacity Utilization")
    
    # Create stacked bar chart
    fig = go.Figure()
    
    # Color mapping
    color_map = {
        'ok': '#28a745',
        'warning': '#ffc107',
        'overload': '#dc3545'
    }
    
    for person, row in chart_data.iterrows():
        color = color_map.get(row['Status'], '#6c757d')
        
        fig.add_trace(go.Bar(
            name=row['Person'],
            x=[row['Person']],
            y=[row['Allocated']],
            marker_color=color,
            text=[f"{row['Allocated']:.1f}h"],
            textposition='inside'
        ))
    
    # Add max capacity line
    fig.add_hline(
        y=MAX_CAPACITY_HOURS,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Max Capacity ({MAX_CAPACITY_HOURS}h)"
    )
    
    fig.update_layout(
        yaxis_title="Hours",
        xaxis_title="Team Member",
        showlegend=False,
        height=400
    )
    
    st.plotly_chart(fig, width="stretch")


def display_capacity_summary(sprint_df: pd.DataFrame, detailed: bool = True):
    """
    Display complete capacity summary with charts and tables
    
    Args:
        sprint_df: Sprint DataFrame
        detailed: Whether to show detailed breakdown
    """
    st.subheader("📊 Capacity Overview")
    
    # Overview metrics
    display_capacity_overview(sprint_df)
    
    st.divider()
    
    # Alerts
    display_capacity_alerts(sprint_df)
    
    if detailed:
        st.divider()
        
        # Detailed breakdown in columns
        col1, col2 = st.columns(2)
        
        with col1:
            display_capacity_chart(sprint_df)
        
        with col2:
            with st.expander("📋 View Capacity Table", expanded=True):
                display_capacity_table(sprint_df)
