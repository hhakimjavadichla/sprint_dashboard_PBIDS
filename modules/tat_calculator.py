"""
Turn Around Time (TAT) calculation and escalation logic
"""
import pandas as pd
from typing import Tuple
from datetime import datetime
from modules.section_filter import exclude_forever_tickets, is_forever_ticket_subject
from utils.constants import (
    TAT_IR_DAYS,
    TAT_SR_DAYS,
    TAT_WARNING_THRESHOLD,
    PRIORITY_CRITICAL
)


def apply_tat_escalation(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """
    Apply TAT-based priority escalation
    
    Rules:
    - IR (Incident): DaysOpen >= 0.8 → Priority = 5
    - SR (Service Request): DaysOpen >= 22 → Priority = 5
    - PR (Project Request): No automatic escalation
    
    Args:
        df: Sprint DataFrame
    
    Returns:
        Tuple of (updated DataFrame, count of escalated tasks)
    """
    if df.empty:
        return df, 0
    
    escalated_count = 0
    
    for idx, row in df.iterrows():
        if is_forever_ticket_subject(row.get('Subject')):
            continue
        if pd.isna(row.get('DaysOpen')) or pd.isna(row.get('TicketType')):
            continue
        
        original_priority = row.get('CustomerPriority')
        if pd.isna(original_priority):
            original_priority = 0
        should_escalate = False
        escalation_reason = ""
        
        # IR escalation
        if row['TicketType'] == 'IR' and row['DaysOpen'] >= TAT_IR_DAYS:
            should_escalate = True
            escalation_reason = f"IR TAT exceeded ({row['DaysOpen']:.1f} days >= {TAT_IR_DAYS} days)"
        
        # SR escalation
        elif row['TicketType'] == 'SR' and row['DaysOpen'] >= TAT_SR_DAYS:
            should_escalate = True
            escalation_reason = f"SR TAT exceeded ({row['DaysOpen']:.1f} days >= {TAT_SR_DAYS} days)"
        
        if should_escalate and original_priority != PRIORITY_CRITICAL:
            df.at[idx, 'CustomerPriority'] = PRIORITY_CRITICAL
            escalated_count += 1
            
            # Add escalation comment
            _add_escalation_comment(df, idx, escalation_reason)
    
    return df, escalated_count


def get_at_risk_tasks(df: pd.DataFrame, threshold: float = None) -> pd.DataFrame:
    """
    Get tasks approaching TAT threshold
    
    Args:
        df: Sprint DataFrame
        threshold: Percentage of TAT (default from constants)
    
    Returns:
        DataFrame of at-risk tasks with TAT percentage
    """
    if threshold is None:
        threshold = TAT_WARNING_THRESHOLD
    
    if df.empty:
        return pd.DataFrame()

    df = exclude_forever_tickets(df)
    
    # Calculate TAT thresholds
    ir_threshold = TAT_IR_DAYS * threshold
    sr_threshold = TAT_SR_DAYS * threshold
    
    # Filter at-risk tasks
    at_risk = df[
        ((df['TicketType'] == 'IR') & (df['DaysOpen'] >= ir_threshold)) |
        ((df['TicketType'] == 'SR') & (df['DaysOpen'] >= sr_threshold))
    ].copy()
    
    if at_risk.empty:
        return at_risk
    
    # Calculate TAT percentage for each task
    at_risk['TAT_Percentage'] = at_risk.apply(
        lambda row: _calculate_tat_percentage(row),
        axis=1
    )
    
    # Add days until escalation
    at_risk['Days_Until_Escalation'] = at_risk.apply(
        lambda row: _calculate_days_until_escalation(row),
        axis=1
    )
    
    # Sort by urgency (highest TAT percentage first)
    at_risk = at_risk.sort_values('TAT_Percentage', ascending=False)
    
    return at_risk


def calculate_tat_metrics(df: pd.DataFrame) -> dict:
    """
    Calculate TAT-related metrics for a sprint
    
    Args:
        df: Sprint DataFrame
    
    Returns:
        Dictionary of TAT metrics
    """
    df = exclude_forever_tickets(df)

    metrics = {
        'total_tasks': len(df),
        'ir_tasks': 0,
        'sr_tasks': 0,
        'ir_exceeded_tat': 0,
        'sr_exceeded_tat': 0,
        'ir_at_risk': 0,
        'sr_at_risk': 0,
        'total_exceeded': 0,
        'total_at_risk': 0,
        'ir_compliance_rate': 100.0,
        'sr_compliance_rate': 100.0,
    }
    
    if df.empty:
        return metrics
    
    # Count by type
    metrics['ir_tasks'] = len(df[df['TicketType'] == 'IR'])
    metrics['sr_tasks'] = len(df[df['TicketType'] == 'SR'])
    
    # Count exceeded TAT
    metrics['ir_exceeded_tat'] = len(df[
        (df['TicketType'] == 'IR') & (df['DaysOpen'] >= TAT_IR_DAYS)
    ])
    metrics['sr_exceeded_tat'] = len(df[
        (df['TicketType'] == 'SR') & (df['DaysOpen'] >= TAT_SR_DAYS)
    ])
    metrics['total_exceeded'] = metrics['ir_exceeded_tat'] + metrics['sr_exceeded_tat']
    
    # Count at risk (75% threshold)
    ir_warning = TAT_IR_DAYS * TAT_WARNING_THRESHOLD
    sr_warning = TAT_SR_DAYS * TAT_WARNING_THRESHOLD
    
    metrics['ir_at_risk'] = len(df[
        (df['TicketType'] == 'IR') & 
        (df['DaysOpen'] >= ir_warning) & 
        (df['DaysOpen'] < TAT_IR_DAYS)
    ])
    metrics['sr_at_risk'] = len(df[
        (df['TicketType'] == 'SR') & 
        (df['DaysOpen'] >= sr_warning) & 
        (df['DaysOpen'] < TAT_SR_DAYS)
    ])
    metrics['total_at_risk'] = metrics['ir_at_risk'] + metrics['sr_at_risk']
    
    # Calculate compliance rates
    if metrics['ir_tasks'] > 0:
        metrics['ir_compliance_rate'] = (
            (metrics['ir_tasks'] - metrics['ir_exceeded_tat']) / metrics['ir_tasks'] * 100
        )
    else:
        metrics['ir_compliance_rate'] = 100.0
    
    if metrics['sr_tasks'] > 0:
        metrics['sr_compliance_rate'] = (
            (metrics['sr_tasks'] - metrics['sr_exceeded_tat']) / metrics['sr_tasks'] * 100
        )
    else:
        metrics['sr_compliance_rate'] = 100.0
    
    return metrics


def _add_escalation_comment(df: pd.DataFrame, idx: int, reason: str):
    """Add comment about TAT escalation"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    comment = f"[{timestamp}] Auto-escalated to Priority 5: {reason}"
    
    existing = df.at[idx, 'Comments']
    if pd.notna(existing) and existing:
        df.at[idx, 'Comments'] = f"{existing}\n{comment}"
    else:
        df.at[idx, 'Comments'] = comment


def _calculate_tat_percentage(row) -> float:
    """Calculate what percentage of TAT has been used"""
    if row['TicketType'] == 'IR':
        return (row['DaysOpen'] / TAT_IR_DAYS) * 100
    elif row['TicketType'] == 'SR':
        return (row['DaysOpen'] / TAT_SR_DAYS) * 100
    return 0.0


def _calculate_days_until_escalation(row) -> float:
    """Calculate days remaining until TAT escalation"""
    if row['TicketType'] == 'IR':
        return max(0, TAT_IR_DAYS - row['DaysOpen'])
    elif row['TicketType'] == 'SR':
        return max(0, TAT_SR_DAYS - row['DaysOpen'])
    return 0.0
