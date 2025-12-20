"""
Data formatting utilities for display
"""
import pandas as pd
from typing import Any


def format_priority(priority: int) -> str:
    """
    Format priority level for display
    
    Args:
        priority: Priority number (0-5)
    
    Returns:
        Formatted string with emoji
    """
    priority_map = {
        5: "🔴 Critical (5)",
        4: "🟠 High (4)",
        3: "🟡 Medium (3)",
        2: "🟢 Low (2)",
        1: "⚪ Minimal (1)",
        0: "⚫ None (0)"
    }
    return priority_map.get(priority, f"❓ Unknown ({priority})")


def format_ticket_type(ticket_type: str) -> str:
    """
    Format ticket type for display
    
    Args:
        ticket_type: Ticket type code
    
    Returns:
        Formatted string with description
    """
    type_map = {
        'IR': '🚨 Incident Request (IR)',
        'SR': '📋 Service Request (SR)',
        'PR': '🎯 Project Request (PR)',
        'NC': '❓ Not Classified (NC)'
    }
    return type_map.get(ticket_type, ticket_type)


def format_hours(hours: float) -> str:
    """
    Format hours for display
    
    Args:
        hours: Number of hours
    
    Returns:
        Formatted string
    """
    if pd.isna(hours):
        return "-"
    return f"{hours:.1f}h"


def format_capacity_status(hours: float, max_hours: float = 52) -> str:
    """
    Format capacity status with color indicator
    
    Args:
        hours: Allocated hours
        max_hours: Maximum capacity
    
    Returns:
        Formatted string with status
    """
    if pd.isna(hours):
        return "⚪ Not Set"
    
    percentage = (hours / max_hours) * 100
    
    if hours > max_hours:
        return f"🔴 Overload ({percentage:.0f}%)"
    elif hours > 45:
        return f"🟡 Warning ({percentage:.0f}%)"
    else:
        return f"🟢 OK ({percentage:.0f}%)"


def format_days_open(days: float, ticket_type: str = None) -> str:
    """
    Format days open with TAT warning if applicable
    
    Args:
        days: Days open
        ticket_type: Type of ticket (for TAT check)
    
    Returns:
        Formatted string
    """
    if pd.isna(days):
        return "-"
    
    result = f"{days:.1f} days"
    
    # Add TAT warning
    if ticket_type == 'IR' and days >= 0.6:  # 75% of 0.8
        result += " ⚠️"
    elif ticket_type == 'SR' and days >= 18:  # 75% of 22
        result += " ⚠️"
    
    return result


def format_status(status: str) -> str:
    """
    Format status with emoji
    
    Args:
        status: Status string
    
    Returns:
        Formatted string
    """
    status_map = {
        'Completed': '✅ Completed',
        'Canceled': '❌ Canceled',
        'In Progress': '🔄 In Progress',
        'Accepted': '📥 Accepted',
        'Pending': '⏳ Pending',
        'On Hold': '⏸️ On Hold',
        'Assigned': '👤 Assigned',
    }
    return status_map.get(status, status)


def truncate_text(text: str, max_length: int = 50) -> str:
    """
    Truncate long text for display
    
    Args:
        text: Text to truncate
        max_length: Maximum length
    
    Returns:
        Truncated text with ellipsis if needed
    """
    if pd.isna(text):
        return ""
    
    text = str(text)
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."


def format_percentage(value: float, total: float) -> str:
    """
    Format a percentage
    
    Args:
        value: Numerator
        total: Denominator
    
    Returns:
        Formatted percentage string
    """
    if total == 0:
        return "0%"
    
    percentage = (value / total) * 100
    return f"{percentage:.1f}%"


def format_metric_delta(value: int, is_good: bool = True) -> str:
    """
    Format a metric delta indicator
    
    Args:
        value: Change value
        is_good: Whether positive change is good
    
    Returns:
        Formatted delta string
    """
    if value == 0:
        return "→"
    elif value > 0:
        return "↑" if is_good else "↓"
    else:
        return "↓" if is_good else "↑"
