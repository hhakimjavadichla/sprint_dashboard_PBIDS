"""
At-risk tasks display widget
"""
import streamlit as st
import pandas as pd
from modules.tat_calculator import get_at_risk_tasks, calculate_tat_metrics


def display_at_risk_summary(sprint_df: pd.DataFrame):
    """
    Display summary of at-risk tasks
    
    Args:
        sprint_df: Sprint DataFrame
    """
    tat_metrics = calculate_tat_metrics(sprint_df)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Tasks At Risk",
            tat_metrics['total_at_risk'],
            help="Tasks approaching TAT threshold (75%)"
        )
    
    with col2:
        st.metric(
            "Exceeded TAT",
            tat_metrics['total_exceeded'],
            delta="⚠️ Critical" if tat_metrics['total_exceeded'] > 0 else "✅",
            help="Tasks that have exceeded TAT limits"
        )
    
    with col3:
        compliance = (tat_metrics['ir_compliance_rate'] + tat_metrics['sr_compliance_rate']) / 2
        st.metric(
            "TAT Compliance",
            f"{compliance:.0f}%",
            help="Overall TAT compliance rate"
        )


def display_at_risk_tasks(sprint_df: pd.DataFrame, max_rows: int = 10):
    """
    Display table of at-risk tasks
    
    Args:
        sprint_df: Sprint DataFrame
        max_rows: Maximum number of rows to display
    """
    at_risk = get_at_risk_tasks(sprint_df)
    
    if at_risk.empty:
        st.success("✅ No tasks at risk of missing TAT!")
        return
    
    st.warning(f"⚠️ **{len(at_risk)} Tasks Approaching or Exceeding TAT**")
    
    # Select columns to display
    display_columns = [
        'TaskNum',
        'TicketType',
        'Subject',
        'DaysOpen',
        'TAT_Percentage',
        'Days_Until_Escalation',
        'Status',
        'AssignedTo'
    ]
    
    # Filter to available columns
    available_cols = [col for col in display_columns if col in at_risk.columns]
    display_df = at_risk[available_cols].head(max_rows)
    
    # Format for display
    if 'TAT_Percentage' in display_df.columns:
        display_df['TAT %'] = display_df['TAT_Percentage'].apply(lambda x: f"{x:.0f}%")
        display_df = display_df.drop('TAT_Percentage', axis=1)
    
    if 'Days_Until_Escalation' in display_df.columns:
        display_df['Days Until Escalation'] = display_df['Days_Until_Escalation'].apply(
            lambda x: f"{x:.1f}" if x > 0 else "EXCEEDED"
        )
        display_df = display_df.drop('Days_Until_Escalation', axis=1)
    
    # Style based on TAT percentage
    def highlight_tat(row):
        colors = []
        for col in row.index:
            if 'TAT %' in str(row.get('TAT %', '')):
                percentage = float(str(row['TAT %']).replace('%', ''))
                if percentage >= 100:
                    colors.append('background-color: #ffe6e6')
                elif percentage >= 75:
                    colors.append('background-color: #fff3cd')
                else:
                    colors.append('')
            else:
                colors.append('')
        return colors
    
    st.dataframe(display_df, width="stretch", hide_index=True)
    
    if len(at_risk) > max_rows:
        st.caption(f"Showing {max_rows} of {len(at_risk)} at-risk tasks. Sorted by urgency.")


def display_tat_breakdown(sprint_df: pd.DataFrame):
    """
    Display TAT metrics breakdown by type
    
    Args:
        sprint_df: Sprint DataFrame
    """
    tat_metrics = calculate_tat_metrics(sprint_df)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚨 Incident Requests (IR)")
        
        ir_data = {
            'Metric': ['Total Tasks', 'At Risk', 'Exceeded TAT', 'Compliance Rate'],
            'Value': [
                tat_metrics['ir_tasks'],
                tat_metrics['ir_at_risk'],
                tat_metrics['ir_exceeded_tat'],
                f"{tat_metrics['ir_compliance_rate']:.1f}%"
            ]
        }
        
        st.dataframe(pd.DataFrame(ir_data), width="stretch", hide_index=True)
        
        if tat_metrics['ir_exceeded_tat'] > 0:
            st.error(f"⚠️ {tat_metrics['ir_exceeded_tat']} IR tasks exceeded 0.8 day TAT")
    
    with col2:
        st.subheader("📋 Service Requests (SR)")
        
        sr_data = {
            'Metric': ['Total Tasks', 'At Risk', 'Exceeded TAT', 'Compliance Rate'],
            'Value': [
                tat_metrics['sr_tasks'],
                tat_metrics['sr_at_risk'],
                tat_metrics['sr_exceeded_tat'],
                f"{tat_metrics['sr_compliance_rate']:.1f}%"
            ]
        }
        
        st.dataframe(pd.DataFrame(sr_data), width="stretch", hide_index=True)
        
        if tat_metrics['sr_exceeded_tat'] > 0:
            st.error(f"⚠️ {tat_metrics['sr_exceeded_tat']} SR tasks exceeded 22 day TAT")


def display_at_risk_widget(sprint_df: pd.DataFrame, detailed: bool = True):
    """
    Display complete at-risk widget with summary and details
    
    Args:
        sprint_df: Sprint DataFrame
        detailed: Whether to show detailed breakdown
    """
    st.subheader("⚠️ At-Risk Tasks")
    
    # Summary metrics
    display_at_risk_summary(sprint_df)
    
    st.divider()
    
    # At-risk tasks table
    display_at_risk_tasks(sprint_df)
    
    if detailed:
        st.divider()
        
        with st.expander("📊 TAT Breakdown by Type"):
            display_tat_breakdown(sprint_df)
