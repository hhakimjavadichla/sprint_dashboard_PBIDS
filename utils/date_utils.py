"""
Date utility functions for sprint management
"""
from datetime import datetime, timedelta
from typing import Tuple
import pandas as pd
from utils.constants import (
    SPRINT_DURATION_DAYS, 
    SPRINT_START_WEEKDAY,
    SPRINT_CYCLE_NAME,
    SPRINT_ENFORCE_START_DAY
)

# Weekday names for display
WEEKDAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def get_sprint_start_day_name() -> str:
    """Get the configured sprint start day name"""
    return WEEKDAY_NAMES[SPRINT_START_WEEKDAY]


def get_next_sprint_start(from_date: datetime = None) -> datetime:
    """
    Get the next sprint start date from a given date
    Uses the configured start weekday from config
    
    Args:
        from_date: Starting date (defaults to today)
    
    Returns:
        Next sprint start date as datetime
    """
    if from_date is None:
        from_date = datetime.now()
    
    days_until_start = (SPRINT_START_WEEKDAY - from_date.weekday()) % 7
    if days_until_start == 0:
        days_until_start = 7  # If today is start day, get next week
    
    return from_date + timedelta(days=days_until_start)


def get_next_thursday(from_date: datetime = None) -> datetime:
    """
    Get the next sprint start date (alias for backward compatibility)
    Note: Now uses configured start day, not hardcoded Thursday
    
    Args:
        from_date: Starting date (defaults to today)
    
    Returns:
        Next sprint start date as datetime
    """
    return get_next_sprint_start(from_date)


def validate_sprint_dates(start_date: datetime, end_date: datetime) -> Tuple[bool, str]:
    """
    Validate that sprint dates meet requirements based on config
    
    Args:
        start_date: Sprint start date
        end_date: Sprint end date
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if start day enforcement is enabled
    if SPRINT_ENFORCE_START_DAY:
        if start_date.weekday() != SPRINT_START_WEEKDAY:
            start_day_name = get_sprint_start_day_name()
            return False, f"Sprint must start on {start_day_name}"
    
    # Check duration
    duration = (end_date - start_date).days
    if duration != (SPRINT_DURATION_DAYS - 1):
        return False, f"Sprint must be exactly {SPRINT_DURATION_DAYS} days"
    
    return True, ""


def calculate_sprint_end_date(start_date: datetime) -> datetime:
    """
    Calculate the end date given a start date
    
    Args:
        start_date: Sprint start date
    
    Returns:
        Sprint end date (13 days after start)
    """
    return start_date + timedelta(days=SPRINT_DURATION_DAYS - 1)


def calculate_days_open(created_date: datetime, reference_date: datetime = None) -> float:
    """
    Calculate number of days a task has been open
    
    Args:
        created_date: When the task was created
        reference_date: Date to calculate from (defaults to now)
    
    Returns:
        Number of days open (rounded to 1 decimal)
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    delta = reference_date - created_date
    return round(delta.total_seconds() / 86400, 1)


def parse_date_flexible(date_str: str) -> datetime:
    """
    Parse date string with multiple format attempts
    
    Args:
        date_str: Date string to parse
    
    Returns:
        Parsed datetime object
    
    Raises:
        ValueError: If date cannot be parsed
    """
    if pd.isna(date_str) or date_str == '':
        raise ValueError("Empty date string")
    
    # Try common formats
    formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%Y-%m-%d %H:%M:%S',
        '%m/%d/%Y %H:%M:%S',
        '%Y/%m/%d',
        '%d-%m-%Y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(str(date_str), fmt)
        except ValueError:
            continue
    
    # Try pandas parser as last resort
    try:
        return pd.to_datetime(date_str)
    except:
        raise ValueError(f"Unable to parse date: {date_str}")


def format_date_display(date: datetime) -> str:
    """
    Format date for display
    
    Args:
        date: Datetime to format
    
    Returns:
        Formatted string (YYYY-MM-DD)
    """
    if pd.isna(date):
        return ""
    return date.strftime('%Y-%m-%d')


def get_days_remaining_in_sprint(sprint_end_date: datetime) -> int:
    """
    Calculate days remaining in current sprint
    
    Args:
        sprint_end_date: End date of sprint
    
    Returns:
        Number of days remaining (0 if sprint ended)
    """
    today = datetime.now()
    if pd.isna(sprint_end_date):
        return 0
    
    if isinstance(sprint_end_date, str):
        sprint_end_date = parse_date_flexible(sprint_end_date)
    
    remaining = (sprint_end_date - today).days
    return max(0, remaining)
