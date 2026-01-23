"""
Section-based filtering for lab section views
"""
import re
import os
import pandas as pd
from typing import List, Optional
from functools import lru_cache

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Python < 3.11


FOREVER_TICKET_SUBJECT_KEYWORDS = [
    "Standing Meeting",
    "Miscellaneous Meetings",
]


def is_forever_ticket_subject(subject: Optional[str]) -> bool:
    if subject is None or pd.isna(subject):
        return False

    subject_str = str(subject)
    for keyword in FOREVER_TICKET_SUBJECT_KEYWORDS:
        if keyword.lower() in subject_str.lower():
            return True

    return False


def exclude_forever_tickets(df: pd.DataFrame, subject_col: str = 'Subject') -> pd.DataFrame:
    if df.empty or subject_col not in df.columns:
        return df

    keywords = [re.escape(k) for k in FOREVER_TICKET_SUBJECT_KEYWORDS]
    pattern = "|".join(keywords)
    if not pattern:
        return df

    mask = ~df[subject_col].astype(str).str.contains(pattern, case=False, na=False)
    return df[mask].copy()


def exclude_ad_tickets(df: pd.DataFrame, ticket_type_col: str = 'TicketType') -> pd.DataFrame:
    """
    Filter out AD (Admin Request) tickets from the DataFrame.
    
    Args:
        df: DataFrame with task data
        ticket_type_col: Column name containing ticket type (default: 'TicketType')
    
    Returns:
        DataFrame with AD tickets excluded
    """
    if df.empty or ticket_type_col not in df.columns:
        return df
    
    mask = df[ticket_type_col].astype(str).str.upper() != 'AD'
    return df[mask].copy()


@lru_cache(maxsize=1)
def load_valid_team_members() -> List[str]:
    """
    Load valid team member list from config file.
    Returns list of account names (usernames).
    """
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        '.streamlit',
        'itrack_mapping.toml'
    )
    
    try:
        with open(config_path, 'rb') as f:
            config = tomllib.load(f)
        return config.get('team_members', {}).get('valid_team_members', [])
    except Exception as e:
        print(f"Warning: Could not load team members from config: {e}")
        return []


def filter_by_team_members(df: pd.DataFrame, assignee_col: str = 'AssignedTo') -> pd.DataFrame:
    """
    Filter DataFrame to only include tasks assigned to valid team members.
    Tasks assigned to people NOT in the team list will be excluded.
    
    Args:
        df: Sprint DataFrame
        assignee_col: Column name containing assignee (default: 'AssignedTo')
    
    Returns:
        Filtered DataFrame with only team member tasks
    """
    if df.empty or assignee_col not in df.columns:
        return df
    
    valid_team = load_valid_team_members()
    if not valid_team:
        # If no team list configured, return all tasks
        return df
    
    # Filter: keep tasks where assignee is in the valid team list (case-insensitive)
    # Also include unassigned tasks (empty/null AssignedTo) so they appear in backlog
    valid_team_lower = [name.lower() for name in valid_team]
    assignee_str = df[assignee_col].astype(str).str.lower().str.strip()
    
    # Include: valid team members OR unassigned tasks (empty, 'nan', or null)
    is_valid_team = assignee_str.isin(valid_team_lower)
    is_unassigned = (assignee_str == '') | (assignee_str == 'nan') | df[assignee_col].isna()
    mask = is_valid_team | is_unassigned
    
    return df[mask].copy()


def clear_team_cache():
    """Clear the cached team member list (call after config changes)"""
    load_valid_team_members.cache_clear()


def filter_by_section(df: pd.DataFrame, section: str) -> pd.DataFrame:
    """
    Filter DataFrame to show only tasks from specified section
    
    Args:
        df: Sprint DataFrame
        section: Section name to filter
    
    Returns:
        Filtered DataFrame
    """
    if df.empty or 'Section' not in df.columns:
        return df
    
    if pd.isna(section) or section == '' or section == 'All':
        return df
    
    filtered = df[df['Section'] == section].copy()
    return filtered


def get_available_sections(df: pd.DataFrame) -> List[str]:
    """
    Get list of unique sections in the sprint
    
    Args:
        df: Sprint DataFrame
    
    Returns:
        Sorted list of section names
    """
    if df.empty or 'Section' not in df.columns:
        return []
    
    sections = df['Section'].dropna().unique().tolist()
    return sorted(sections)


def get_section_summary(df: pd.DataFrame, section: str) -> dict:
    """
    Get summary statistics for a specific section
    
    Args:
        df: Sprint DataFrame
        section: Section name
    
    Returns:
        Dictionary of section statistics
    """
    section_df = filter_by_section(df, section)
    section_df = exclude_forever_tickets(section_df)
    
    summary = {
        'section': section,
        'total_tasks': len(section_df),
        'completed': 0,
        'in_progress': 0,
        'pending': 0,
        'at_risk': 0,
        'total_effort': 0.0,
        'avg_days_open': 0.0,
        'team_members': []
    }
    
    if section_df.empty:
        return summary
    
    # Count by status
    summary['completed'] = len(section_df[section_df['TaskStatus'] == 'Completed'])
    summary['in_progress'] = len(section_df[section_df['TaskStatus'].isin(['Accepted', 'Assigned', 'Waiting'])])
    summary['pending'] = len(section_df[section_df['TaskStatus'].isin(['Logged', 'Pending'])])
    
    # At-risk tasks
    summary['at_risk'] = len(section_df[
        ((section_df['TicketType'] == 'IR') & (section_df['DaysOpen'] >= 0.6)) |
        ((section_df['TicketType'] == 'SR') & (section_df['DaysOpen'] >= 18))
    ])
    
    # Effort
    if 'HoursEstimated' in section_df.columns:
        total_effort = section_df['HoursEstimated'].sum()
        summary['total_effort'] = total_effort if pd.notna(total_effort) else 0.0
    
    # Days open
    if 'DaysOpen' in section_df.columns:
        avg_days = section_df['DaysOpen'].mean()
        summary['avg_days_open'] = round(avg_days, 1) if pd.notna(avg_days) else 0.0
    
    # Team members
    if 'AssignedTo' in section_df.columns:
        members = section_df['AssignedTo'].dropna().unique().tolist()
        summary['team_members'] = sorted(members)
    
    return summary


def get_all_section_summaries(df: pd.DataFrame) -> List[dict]:
    """
    Get summaries for all sections
    
    Args:
        df: Sprint DataFrame
    
    Returns:
        List of section summary dictionaries
    """
    sections = get_available_sections(df)
    summaries = []
    
    for section in sections:
        summary = get_section_summary(df, section)
        summaries.append(summary)
    
    # Sort by total tasks (descending)
    summaries.sort(key=lambda x: x['total_tasks'], reverse=True)
    
    return summaries


def apply_section_filters(
    df: pd.DataFrame,
    sections: List[str] = None,
    status: List[str] = None,
    priority_range: tuple = None,
    assigned_to: List[str] = None
) -> pd.DataFrame:
    """
    Apply multiple filters to DataFrame
    
    Args:
        df: Sprint DataFrame
        sections: List of sections to include
        status: List of statuses to include
        priority_range: Tuple of (min, max) priority
        assigned_to: List of people to filter by
    
    Returns:
        Filtered DataFrame
    """
    filtered = df.copy()
    
    # Section filter
    if sections and 'All' not in sections:
        filtered = filtered[filtered['Section'].isin(sections)]
    
    # Status filter
    if status and 'All' not in status:
        filtered = filtered[filtered['TaskStatus'].isin(status)]
    
    # Priority range filter
    if priority_range:
        min_priority, max_priority = priority_range
        filtered = filtered[
            (filtered['CustomerPriority'].fillna(0) >= min_priority) &
            (filtered['CustomerPriority'].fillna(0) <= max_priority)
        ]
    
    # Assignee filter - use display names if available
    if assigned_to and 'All' not in assigned_to:
        assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in filtered.columns else 'AssignedTo'
        filtered = filtered[filtered[assignee_col].isin(assigned_to)]
    
    return filtered
