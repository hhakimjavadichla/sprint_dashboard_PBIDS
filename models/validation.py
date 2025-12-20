"""
Data validation utilities
"""
import pandas as pd
from typing import List, Tuple, Dict


def validate_itrack_csv(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate that uploaded CSV has required iTrack columns
    Supports both old and new (normalized) format
    
    Args:
        df: DataFrame to validate
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Required columns - check for either old or new format names
    required_column_alternatives = [
        ['Task ID', 'Task'],  # Task ID column (new vs old)
        ['Ticket Number', 'Parent ID', 'Ticket ID'],  # Ticket/Parent ID column
        ['Task Status', 'Status'],  # Status column (new vs old)
        ['Subject', 'Ticket_Subject'],  # Subject column
        ['Task Assigned Date', 'Task Created Date', 'Created On', 'Day of Task_Created_DateTime'],  # Date column (Format 03+ uses various date fields)
    ]
    
    missing_alternatives = []
    for alternatives in required_column_alternatives:
        if not any(col in df.columns for col in alternatives):
            missing_alternatives.append(f"({' or '.join(alternatives)})")
    
    if missing_alternatives:
        errors.append(f"Missing required columns: {', '.join(missing_alternatives)}")
    
    # Check for empty DataFrame
    if len(df) == 0:
        errors.append("CSV file is empty")
    
    # Check for duplicate task numbers
    task_col = None
    if 'Task ID' in df.columns:
        task_col = 'Task ID'
    elif 'Task' in df.columns:
        task_col = 'Task'
    
    if task_col:
        duplicates = df[task_col].duplicated().sum()
        if duplicates > 0:
            errors.append(f"Found {duplicates} duplicate Task IDs")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def validate_sprint_csv(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate sprint CSV structure
    
    Args:
        df: DataFrame to validate
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    required_columns = [
        'SprintNumber',
        'TaskNum',
        'TicketNum',
        'Status',
        'Subject',
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")
    
    # Check sprint number consistency
    if 'SprintNumber' in df.columns and len(df) > 0:
        unique_sprints = df['SprintNumber'].nunique()
        if unique_sprints > 1:
            errors.append(f"Sprint file contains multiple sprint numbers: {unique_sprints}")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def validate_task_data(task_dict: dict) -> Tuple[bool, List[str]]:
    """
    Validate individual task data
    
    Args:
        task_dict: Dictionary of task data
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required fields
    if not task_dict.get('TaskNum'):
        errors.append("TaskNum is required")
    
    if not task_dict.get('TicketNum'):
        errors.append("TicketNum is required")
    
    # Validate priority range (if provided - it's a dashboard-only field)
    priority = task_dict.get('CustomerPriority')
    if priority is not None and priority != '':
        try:
            priority = int(priority)
            if priority < 0 or priority > 5:
                errors.append(f"CustomerPriority must be 0-5 (received: {priority})")
        except (ValueError, TypeError):
            pass  # Allow None/empty - it's optional
    
    # Validate estimated effort
    effort = task_dict.get('HoursEstimated')
    if effort is not None and not pd.isna(effort):
        try:
            effort_float = float(effort)
            if effort_float < 0:
                errors.append("Estimated Effort cannot be negative")
            elif effort_float > 100:
                errors.append("Estimated Effort seems unusually high (>100 hours)")
        except (ValueError, TypeError):
            errors.append(f"Invalid Estimated Effort value: {effort}")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def get_data_quality_report(df: pd.DataFrame) -> Dict:
    """
    Generate data quality report for a sprint DataFrame
    
    Args:
        df: Sprint DataFrame
    
    Returns:
        Dictionary with data quality metrics
    """
    report = {
        'total_rows': len(df),
        'issues': []
    }
    
    # Check for missing critical data
    critical_cols = ['TaskNum', 'TicketNum', 'Status', 'Subject']
    for col in critical_cols:
        if col in df.columns:
            missing = df[col].isna().sum()
            if missing > 0:
                report['issues'].append(f"{col}: {missing} missing values")
    
    # Check for missing assignments
    if 'AssignedTo' in df.columns:
        unassigned = df['AssignedTo'].isna().sum()
        report['unassigned_tasks'] = unassigned
        if unassigned > 0:
            report['issues'].append(f"{unassigned} tasks without assignment")
    
    # Check for missing effort estimates
    if 'HoursEstimated' in df.columns:
        no_estimate = df['HoursEstimated'].isna().sum()
        report['tasks_without_estimate'] = no_estimate
        if no_estimate > 0:
            report['issues'].append(f"{no_estimate} tasks without effort estimate")
    
    # Check for invalid priorities
    invalid_priority = df[
        df['CustomerPriority'].notna() & 
        ((df['CustomerPriority'] < 0) | (df['CustomerPriority'] > 5))
    ]
    if len(invalid_priority) > 0:
        report['issues'].append(f"{len(invalid_priority)} tasks with invalid priority")
    
    # Check for duplicate tasks
    if 'TaskNum' in df.columns:
        duplicates = df['TaskNum'].duplicated().sum()
        if duplicates > 0:
            report['issues'].append(f"{duplicates} duplicate task numbers")
    
    # Calculate completeness score
    total_checks = len(critical_cols) + 3  # Critical cols + assignments + estimates + priorities
    issues_count = len(report['issues'])
    report['quality_score'] = max(0, ((total_checks - issues_count) / total_checks) * 100)
    
    return report
