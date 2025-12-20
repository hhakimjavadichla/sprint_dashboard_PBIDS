"""
Capacity validation and workload management
"""
import pandas as pd
from typing import Dict, List
from utils.constants import MAX_CAPACITY_HOURS, WARNING_CAPACITY_HOURS
from modules.section_filter import exclude_forever_tickets


def validate_capacity(df: pd.DataFrame) -> Dict:
    """
    Validate team capacity against 52-hour rule
    
    Args:
        df: Sprint DataFrame with AssignedTo and Estimated Effort columns
    
    Returns:
        Dictionary with capacity analysis:
        - total_hours: Overall sprint hours
        - per_person: Dict of person -> capacity info
        - overloaded: List of overloaded people
        - warnings: List of people approaching limit
        - available_capacity: Remaining capacity per person
    """
    result = {
        'total_hours': 0.0,
        'per_person': {},
        'overloaded': [],
        'warnings': [],
        'available_capacity': {},
        'max_capacity': MAX_CAPACITY_HOURS
    }
    
    df = exclude_forever_tickets(df)

    if df.empty or 'AssignedTo' not in df.columns:
        return result
    
    # Calculate per-person totals
    capacity = df.groupby('AssignedTo')['HoursEstimated'].sum()
    capacity = capacity[capacity.notna()]
    
    if capacity.empty:
        return result
    
    result['total_hours'] = round(capacity.sum(), 1)
    
    # Analyze each person's capacity
    for person, hours in capacity.items():
        if pd.isna(person) or person == '':
            continue
        
        percentage = (hours / MAX_CAPACITY_HOURS) * 100
        available = max(0, MAX_CAPACITY_HOURS - hours)
        
        # Determine status
        if hours > MAX_CAPACITY_HOURS:
            status = 'overload'
            result['overloaded'].append(person)
        elif hours > WARNING_CAPACITY_HOURS:
            status = 'warning'
            result['warnings'].append(person)
        else:
            status = 'ok'
        
        result['per_person'][person] = {
            'hours': round(hours, 1),
            'percentage': round(percentage, 1),
            'status': status,
            'available': round(available, 1),
            'over_capacity': max(0, hours - MAX_CAPACITY_HOURS)
        }
        
        result['available_capacity'][person] = round(available, 1)
    
    return result


def get_capacity_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get formatted capacity summary as DataFrame for display
    
    Args:
        df: Sprint DataFrame
    
    Returns:
        DataFrame with capacity summary
    """
    capacity_info = validate_capacity(df)
    
    if not capacity_info['per_person']:
        return pd.DataFrame(columns=[
            'AssignedTo', 'Total Hours', 'Capacity %', 
            'Available', 'Status', 'Status_Icon'
        ])
    
    rows = []
    for person, info in capacity_info['per_person'].items():
        # Add status icon
        if info['status'] == 'overload':
            icon = '🔴'
        elif info['status'] == 'warning':
            icon = '🟡'
        else:
            icon = '🟢'
        
        rows.append({
            'AssignedTo': person,
            'Total Hours': info['hours'],
            'Capacity %': info['percentage'],
            'Available': info['available'],
            'Status': info['status'].upper(),
            'Status_Icon': icon
        })
    
    capacity_df = pd.DataFrame(rows)
    capacity_df = capacity_df.sort_values('Total Hours', ascending=False)
    
    return capacity_df


def get_capacity_chart_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get data formatted for capacity visualization charts
    
    Args:
        df: Sprint DataFrame
    
    Returns:
        DataFrame optimized for plotting
    """
    capacity_info = validate_capacity(df)
    
    if not capacity_info['per_person']:
        return pd.DataFrame()
    
    rows = []
    for person, info in capacity_info['per_person'].items():
        rows.append({
            'Person': person,
            'Allocated': info['hours'],
            'Available': info['available'],
            'Max Capacity': MAX_CAPACITY_HOURS,
            'Status': info['status']
        })
    
    chart_df = pd.DataFrame(rows)
    chart_df = chart_df.sort_values('Allocated', ascending=False)
    
    return chart_df


def get_unassigned_tasks(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get tasks without assignment
    
    Args:
        df: Sprint DataFrame
    
    Returns:
        DataFrame of unassigned tasks
    """
    if 'AssignedTo' not in df.columns:
        return pd.DataFrame()
    
    unassigned = df[df['AssignedTo'].isna() | (df['AssignedTo'] == '')]
    return unassigned


def get_tasks_by_person(df: pd.DataFrame, person: str) -> pd.DataFrame:
    """
    Get all tasks assigned to a specific person
    
    Args:
        df: Sprint DataFrame
        person: Person's name
    
    Returns:
        DataFrame of tasks for that person
    """
    if 'AssignedTo' not in df.columns:
        return pd.DataFrame()
    
    person_tasks = df[df['AssignedTo'] == person]
    return person_tasks


def suggest_reassignments(df: pd.DataFrame) -> List[Dict]:
    """
    Suggest task reassignments to balance capacity
    
    Args:
        df: Sprint DataFrame
    
    Returns:
        List of suggested reassignment actions
    """
    suggestions = []
    capacity_info = validate_capacity(df)
    
    if not capacity_info['overloaded']:
        return suggestions
    
    # Find people with available capacity
    available_people = [
        (person, info['available'])
        for person, info in capacity_info['per_person'].items()
        if info['available'] > 0
    ]
    
    if not available_people:
        return suggestions
    
    # Sort by most available capacity
    available_people.sort(key=lambda x: x[1], reverse=True)
    
    # For each overloaded person, suggest moving tasks
    for overloaded_person in capacity_info['overloaded']:
        person_info = capacity_info['per_person'][overloaded_person]
        over_by = person_info['over_capacity']
        
        # Get their tasks, sorted by effort (smallest first for easier balancing)
        person_tasks = get_tasks_by_person(df, overloaded_person)
        person_tasks = person_tasks.sort_values(
            'HoursEstimated', 
            ascending=True
        )
        
        # Try to reassign tasks
        for idx, task in person_tasks.iterrows():
            if over_by <= 0:
                break
            
            task_effort = task.get('HoursEstimated', 0)
            if pd.isna(task_effort) or task_effort == 0:
                continue
            
            # Find someone who can take this task
            for available_person, available_hours in available_people:
                if available_hours >= task_effort:
                    suggestions.append({
                        'task_num': task['TaskNum'],
                        'subject': task['Subject'],
                        'effort': task_effort,
                        'from_person': overloaded_person,
                        'to_person': available_person,
                        'reason': f"Balance workload ({overloaded_person} overloaded by {person_info['over_capacity']:.1f}h)"
                    })
                    over_by -= task_effort
                    # Update available capacity
                    available_people = [
                        (p, (h - task_effort if p == available_person else h))
                        for p, h in available_people
                    ]
                    available_people.sort(key=lambda x: x[1], reverse=True)
                    break
    
    return suggestions


def calculate_team_capacity_metrics(df: pd.DataFrame) -> Dict:
    """
    Calculate high-level team capacity metrics
    
    Args:
        df: Sprint DataFrame
    
    Returns:
        Dictionary of team-wide metrics
    """
    capacity_info = validate_capacity(df)
    
    num_people = len(capacity_info['per_person'])
    total_capacity = num_people * MAX_CAPACITY_HOURS
    
    metrics = {
        'num_people': num_people,
        'total_team_capacity': total_capacity,
        'total_allocated': capacity_info['total_hours'],
        'total_available': max(0, total_capacity - capacity_info['total_hours']),
        'utilization_percentage': (
            (capacity_info['total_hours'] / total_capacity * 100) if total_capacity > 0 else 0
        ),
        'num_overloaded': len(capacity_info['overloaded']),
        'num_warnings': len(capacity_info['warnings']),
        'num_ok': num_people - len(capacity_info['overloaded']) - len(capacity_info['warnings']),
        'balance_score': _calculate_balance_score(capacity_info)
    }
    
    return metrics


def _calculate_balance_score(capacity_info: Dict) -> float:
    """
    Calculate how balanced the workload is (0-100, higher is better)
    
    Args:
        capacity_info: Capacity validation result
    
    Returns:
        Balance score (100 = perfectly balanced, 0 = very unbalanced)
    """
    if not capacity_info['per_person']:
        return 100.0
    
    percentages = [
        info['percentage'] 
        for info in capacity_info['per_person'].values()
    ]
    
    if not percentages:
        return 100.0
    
    # Calculate standard deviation of capacity percentages
    import numpy as np
    std_dev = np.std(percentages)
    
    # Convert to score (lower std dev = better balance)
    # Assume std dev of 30% is "unbalanced", 0% is perfect
    max_std_dev = 30
    balance_score = max(0, 100 - (std_dev / max_std_dev * 100))
    
    return round(balance_score, 1)
