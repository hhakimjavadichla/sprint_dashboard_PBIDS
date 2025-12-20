"""
Task Store Module
Single source of truth for all tasks across all sprints

Work Backlogs Workflow:
- All open tasks appear in Work Backlogs
- Admin assigns tasks to sprints from backlog (can assign same task to multiple sprints)
- SprintsAssigned column tracks all sprint assignments (comma-separated: "4, 5")
- Completed tasks are removed from backlog
- No automatic carryover - admin must explicitly assign each sprint
"""
import os
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from modules.sprint_calendar import get_sprint_calendar
from utils.name_mapper import apply_name_mapping, get_display_name
from modules.section_filter import filter_by_team_members

# Path to all tasks store
ALL_TASKS_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'all_tasks.csv'
)

# Statuses that indicate a task is closed (won't carry over)
CLOSED_STATUSES = [
    'Completed', 'Closed', 'Resolved', 'Done', 'Canceled', 
    'Excluded from Carryover'
]

# Goal types for capacity planning
GOAL_TYPES = ['Mandatory', 'Stretch']
DEFAULT_GOAL_TYPE = 'Mandatory'

# Capacity limits per person per sprint (based on 80 hours total)
CAPACITY_LIMITS = {
    'Mandatory': 48,  # 60% of 80 hours
    'Stretch': 16,    # 20% of 80 hours
    'Total': 80       # Total available hours
}

# All valid statuses for task management (based on iTrack system)
# Open statuses: Logged -> Assigned -> Accepted -> Waiting
# Closed statuses: Completed, Closed, Resolved, Done, Canceled, Excluded from Carryover
VALID_STATUSES = [
    'Logged',       # New task, not yet assigned
    'Assigned',     # Assigned to someone but not yet accepted
    'Accepted',     # Accepted by assignee, actively working
    'Waiting',      # On hold/waiting for external input
    'Completed',    # Work finished
    'Closed',       # Ticket closed
    'Resolved',     # Issue resolved
    'Done',         # Alternative completion status
    'Canceled',     # Task canceled
    'Excluded from Carryover'  # Manual exclusion from sprint carryover
]


class TaskStore:
    """
    Manages all tasks in a single store.
    
    Work Backlogs Workflow:
    - All open tasks appear in Work Backlogs
    - Admin assigns tasks to sprints (can assign to multiple sprints over time)
    - Completed tasks are removed from backlog
    
    Key fields:
    - OriginalSprintNumber: Sprint when task was created (based on TaskAssignedDt)
    - SprintsAssigned: Comma-separated list of sprints task was assigned to (e.g., "4, 5")
    """
    
    def __init__(self, store_path: str = None):
        self.store_path = store_path or ALL_TASKS_PATH
        self.calendar = get_sprint_calendar()
        self.tasks_df = self._load_store()
    
    def _load_store(self) -> pd.DataFrame:
        """Load all tasks from store"""
        if not os.path.exists(self.store_path):
            return pd.DataFrame()
        
        try:
            # Read CSV with SprintsAssigned as string to preserve values
            df = pd.read_csv(self.store_path, dtype={'SprintsAssigned': str})
            
            # Ensure SprintsAssigned is string and handle NaN
            if 'SprintsAssigned' in df.columns:
                df['SprintsAssigned'] = df['SprintsAssigned'].fillna('').astype(str)
                # Clean up any 'nan' strings
                df['SprintsAssigned'] = df['SprintsAssigned'].replace('nan', '')
            
            # Parse date columns
            date_cols = ['TaskAssignedDt', 'StatusUpdateDt', 'TicketCreatedDt', 
                        'TaskCreatedDt', 'TaskResolvedDt', 'TicketResolvedDt']
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # Migration: Convert AssignedSprintNumber to SprintsAssigned
            if 'SprintsAssigned' not in df.columns:
                if 'AssignedSprintNumber' in df.columns:
                    # Convert single sprint number to comma-separated string
                    df['SprintsAssigned'] = df['AssignedSprintNumber'].apply(
                        lambda x: str(int(x)) if pd.notna(x) else ''
                    )
                elif 'OriginalSprintNumber' in df.columns:
                    # For completed tasks, use OriginalSprintNumber; for open tasks, empty
                    df['SprintsAssigned'] = df.apply(
                        lambda row: str(int(row['OriginalSprintNumber'])) if row.get('Status') in CLOSED_STATUSES and pd.notna(row.get('OriginalSprintNumber')) else '',
                        axis=1
                    )
                else:
                    df['SprintsAssigned'] = ''
            
            # Migration: Add GoalType column if not exists
            if 'GoalType' not in df.columns:
                df['GoalType'] = DEFAULT_GOAL_TYPE
            
            # Ensure dashboard-only priority columns exist (with None as default)
            if 'CustomerPriority' not in df.columns:
                df['CustomerPriority'] = None
            if 'FinalPriority' not in df.columns:
                df['FinalPriority'] = None
            
            return df
        except Exception as e:
            print(f"Error loading task store: {e}")
            return pd.DataFrame()
    
    def save(self) -> bool:
        """Save task store to CSV"""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
            
            # Ensure SprintsAssigned is saved as clean string (not float)
            if 'SprintsAssigned' in self.tasks_df.columns:
                self.tasks_df['SprintsAssigned'] = self.tasks_df['SprintsAssigned'].fillna('').astype(str)
                self.tasks_df['SprintsAssigned'] = self.tasks_df['SprintsAssigned'].replace('nan', '')
            
            self.tasks_df.to_csv(self.store_path, index=False)
            return True
        except Exception as e:
            print(f"Error saving task store: {e}")
            return False
    
    def import_tasks(self, itrack_df: pd.DataFrame, mapped_df: pd.DataFrame) -> Dict:
        """
        Import tasks from iTrack extract.
        Each task gets a UniqueTaskId = TaskNum_S{OriginalSprintNumber}
        
        Args:
            itrack_df: Raw iTrack DataFrame
            mapped_df: DataFrame after column mapping to sprint schema
        
        Returns:
            Dict with import statistics
        """
        stats = {
            'total_imported': 0,
            'new_tasks': 0,
            'updated_tasks': 0,
            'sprints_affected': set()
        }
        
        if mapped_df.empty:
            return stats
        
        # Ensure TaskAssignedDt is datetime
        if 'TaskAssignedDt' in mapped_df.columns:
            mapped_df['TaskAssignedDt'] = pd.to_datetime(
                mapped_df['TaskAssignedDt'], errors='coerce'
            )
        
        # Assign each task to its original sprint
        for idx, row in mapped_df.iterrows():
            task_num = row.get('TaskNum')
            task_assigned_dt = row.get('TaskAssignedDt')
            
            if pd.isna(task_num):
                continue
            
            # Find original sprint based on TaskAssignedDt
            original_sprint = self.calendar.get_sprint_for_date(task_assigned_dt)
            if original_sprint:
                original_sprint_num = original_sprint['SprintNumber']
                stats['sprints_affected'].add(original_sprint_num)
            else:
                # No matching sprint - assign to sprint 0 (unassigned)
                original_sprint_num = 0
            
            # Create unique task ID
            unique_id = f"{task_num}_S{original_sprint_num}"
            mapped_df.at[idx, 'UniqueTaskId'] = unique_id
            mapped_df.at[idx, 'OriginalSprintNumber'] = original_sprint_num
            
            # Apply assignment rules based on task status
            status = row.get('Status', '')
            if status in CLOSED_STATUSES:
                # COMPLETED TASKS: Auto-assign to their original sprint
                mapped_df.at[idx, 'SprintsAssigned'] = str(original_sprint_num)
                
                # Set StatusUpdateDt from resolved date
                resolved_dt = row.get('TaskResolvedDt') or row.get('TicketResolvedDt')
                if pd.notna(resolved_dt):
                    mapped_df.at[idx, 'StatusUpdateDt'] = resolved_dt
                else:
                    mapped_df.at[idx, 'StatusUpdateDt'] = datetime.now()
            else:
                # OPEN TASKS: Go to Work Backlogs (no sprints assigned yet)
                mapped_df.at[idx, 'SprintsAssigned'] = ''
            
            # Set default GoalType if not already set
            if 'GoalType' not in mapped_df.columns or pd.isna(mapped_df.at[idx, 'GoalType']):
                mapped_df.at[idx, 'GoalType'] = DEFAULT_GOAL_TYPE
            
            # Create dashboard-only priority columns (not from iTrack)
            if 'CustomerPriority' not in mapped_df.columns:
                mapped_df['CustomerPriority'] = None
            if 'FinalPriority' not in mapped_df.columns:
                mapped_df['FinalPriority'] = None
            
            stats['total_imported'] += 1
        
        # Merge with existing store
        if self.tasks_df.empty:
            self.tasks_df = mapped_df.copy()
            stats['new_tasks'] = len(mapped_df)
        else:
            # Update existing tasks, add new ones
            existing_ids = set(self.tasks_df['UniqueTaskId'].tolist()) if 'UniqueTaskId' in self.tasks_df.columns else set()
            
            for idx, row in mapped_df.iterrows():
                unique_id = row.get('UniqueTaskId')
                
                if unique_id in existing_ids:
                    # Update existing task (except admin-set fields)
                    mask = self.tasks_df['UniqueTaskId'] == unique_id
                    
                    # Fields to update from iTrack (not admin fields)
                    # Note: CustomerPriority/FinalPriority are dashboard-only, not from iTrack
                    update_fields = ['Status', 'AssignedTo', 'Subject']
                    for field in update_fields:
                        if field in row.index and pd.notna(row[field]):
                            # Don't overwrite if admin has set StatusUpdateDt
                            if field == 'Status' and pd.notna(self.tasks_df.loc[mask, 'StatusUpdateDt'].iloc[0]):
                                continue
                            self.tasks_df.loc[mask, field] = row[field]
                    
                    stats['updated_tasks'] += 1
                else:
                    # Add new task
                    self.tasks_df = pd.concat([self.tasks_df, row.to_frame().T], ignore_index=True)
                    stats['new_tasks'] += 1
        
        stats['sprints_affected'] = list(stats['sprints_affected'])
        return stats
    
    def _sprint_in_list(self, sprints_assigned: str, sprint_number: int) -> bool:
        """Check if a sprint number is in the SprintsAssigned comma-separated list"""
        if pd.isna(sprints_assigned) or sprints_assigned == '':
            return False
        try:
            sprint_list = [int(s.strip()) for s in str(sprints_assigned).split(',') if s.strip()]
            return sprint_number in sprint_list
        except:
            return False
    
    def get_sprint_tasks(self, sprint_number: int) -> pd.DataFrame:
        """
        Get all tasks assigned to a specific sprint.
        
        A task appears in Sprint N if:
        - SprintsAssigned contains N (admin assigned to this sprint)
        
        No automatic carryover - admin must explicitly assign each sprint.
        
        Args:
            sprint_number: Sprint number to get tasks for
        
        Returns:
            DataFrame of tasks for that sprint
        """
        if self.tasks_df.empty:
            return pd.DataFrame()
        
        sprint_info = self.calendar.get_sprint_by_number(sprint_number)
        if not sprint_info:
            return pd.DataFrame()
        
        # Ensure SprintsAssigned column exists
        if 'SprintsAssigned' not in self.tasks_df.columns:
            self.tasks_df['SprintsAssigned'] = ''
        
        # Tasks assigned to this sprint (sprint number is in SprintsAssigned list)
        mask = self.tasks_df['SprintsAssigned'].apply(
            lambda x: self._sprint_in_list(x, sprint_number)
        )
        result = self.tasks_df[mask].copy()
        
        # Determine TaskOrigin for each task
        if not result.empty:
            result['TaskOrigin'] = result.apply(
                lambda row: 'New' if row.get('OriginalSprintNumber') == sprint_number 
                else 'Assigned',
                axis=1
            )
        
        # Add sprint metadata
        if not result.empty:
            result['SprintNumber'] = sprint_number
            result['SprintName'] = sprint_info['SprintName']
            result['SprintStartDt'] = sprint_info['SprintStartDt']
            result['SprintEndDt'] = sprint_info['SprintEndDt']
            
            # Calculate DaysOpen (days since task was assigned)
            result = self._calculate_days_open(result)
            
            # Filter by valid team members
            result = filter_by_team_members(result, 'AssignedTo')
            
            # Apply name mapping for display names
            result = apply_name_mapping(result, 'AssignedTo')
        
        return result
    
    def _calculate_days_open(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate DaysOpen for all tasks based on Task Assigned Date"""
        if df.empty:
            return df
        
        today = datetime.now()
        
        if 'TaskAssignedDt' in df.columns:
            df['TaskAssignedDt'] = pd.to_datetime(df['TaskAssignedDt'], errors='coerce')
            df['DaysOpen'] = df['TaskAssignedDt'].apply(
                lambda x: (today - x).days if pd.notna(x) else 0
            )
        elif 'TicketCreatedDt' in df.columns:
            df['TicketCreatedDt'] = pd.to_datetime(df['TicketCreatedDt'], errors='coerce')
            df['DaysOpen'] = df['TicketCreatedDt'].apply(
                lambda x: (today - x).days if pd.notna(x) else 0
            )
        else:
            df['DaysOpen'] = 0
        
        return df
    
    def get_current_sprint_tasks(self) -> pd.DataFrame:
        """Get tasks for the current sprint (based on today's date)"""
        current_sprint = self.calendar.get_current_sprint()
        if not current_sprint:
            # No current sprint, try next
            current_sprint = self.calendar.get_next_sprint()
        
        if not current_sprint:
            return pd.DataFrame()
        
        return self.get_sprint_tasks(current_sprint['SprintNumber'])
    
    def update_task_status(
        self, 
        unique_task_id: str, 
        new_status: str, 
        status_update_dt: datetime
    ) -> bool:
        """
        Update a task's status with a specific update date.
        
        Args:
            unique_task_id: The UniqueTaskId of the task
            new_status: New status (e.g., 'Closed', 'Canceled')
            status_update_dt: Date when status change takes effect
        
        Returns:
            True if successful
        """
        if self.tasks_df.empty:
            return False
        
        mask = self.tasks_df['UniqueTaskId'] == unique_task_id
        if not mask.any():
            return False
        
        # Validate: StatusUpdateDt must be >= TaskAssignedDt
        task_assigned_dt = self.tasks_df.loc[mask, 'TaskAssignedDt'].iloc[0]
        if pd.notna(task_assigned_dt) and status_update_dt < task_assigned_dt:
            print(f"Error: StatusUpdateDt ({status_update_dt}) cannot be before TaskAssignedDt ({task_assigned_dt})")
            return False
        
        self.tasks_df.loc[mask, 'Status'] = new_status
        self.tasks_df.loc[mask, 'StatusUpdateDt'] = status_update_dt
        
        return self.save()
    
    def get_backlog_tasks(self) -> pd.DataFrame:
        """
        Get all open tasks in Work Backlogs.
        
        All open tasks appear in backlog (regardless of sprint assignment).
        Completed tasks are excluded.
        
        Returns:
            DataFrame of all open tasks
        """
        if self.tasks_df.empty:
            return pd.DataFrame()
        
        # Ensure SprintsAssigned column exists
        if 'SprintsAssigned' not in self.tasks_df.columns:
            self.tasks_df['SprintsAssigned'] = ''
        
        # Get all OPEN tasks (not completed)
        backlog_tasks = self.tasks_df[
            ~self.tasks_df['Status'].isin(CLOSED_STATUSES)
        ].copy()
        
        if not backlog_tasks.empty:
            # Calculate DaysOpen
            backlog_tasks = self._calculate_days_open(backlog_tasks)
            
            # Filter by valid team members
            backlog_tasks = filter_by_team_members(backlog_tasks, 'AssignedTo')
            
            # Apply name mapping for display names
            backlog_tasks = apply_name_mapping(backlog_tasks, 'AssignedTo')
        
        return backlog_tasks
    
    def get_queue_tasks(self) -> pd.DataFrame:
        """Alias for get_backlog_tasks for backward compatibility"""
        return self.get_backlog_tasks()
    
    def _add_sprint_to_list(self, current_sprints: str, sprint_number: int) -> str:
        """Add a sprint number to the SprintsAssigned list (if not already present)"""
        if pd.isna(current_sprints) or current_sprints == '':
            return str(sprint_number)
        
        try:
            sprint_list = [int(s.strip()) for s in str(current_sprints).split(',') if s.strip()]
            if sprint_number not in sprint_list:
                sprint_list.append(sprint_number)
            return ', '.join(map(str, sorted(sprint_list)))
        except:
            return str(sprint_number)
    
    def assign_task_to_sprint(self, unique_task_id: str, sprint_number: int) -> Tuple[bool, str]:
        """
        Add a sprint assignment to a task (appends to SprintsAssigned list).
        
        Args:
            unique_task_id: The UniqueTaskId of the task
            sprint_number: Sprint number to assign to
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if self.tasks_df.empty:
            return False, "Task store is empty"
        
        mask = self.tasks_df['UniqueTaskId'] == unique_task_id
        if not mask.any():
            return False, f"Task {unique_task_id} not found"
        
        # Get sprint info to validate
        sprint_info = self.calendar.get_sprint_by_number(sprint_number)
        if not sprint_info:
            return False, f"Sprint {sprint_number} not found"
        
        # VALIDATION: Cannot assign to sprint older than task creation date
        original_sprint = self.tasks_df.loc[mask, 'OriginalSprintNumber'].iloc[0]
        if pd.notna(original_sprint) and sprint_number < original_sprint:
            return False, f"Cannot assign to Sprint {sprint_number}. Task was created in Sprint {int(original_sprint)}."
        
        # Check if already assigned to this sprint
        current_sprints = self.tasks_df.loc[mask, 'SprintsAssigned'].iloc[0]
        if self._sprint_in_list(current_sprints, sprint_number):
            return False, f"Task already assigned to Sprint {sprint_number}"
        
        # Add sprint to the list
        new_sprints = self._add_sprint_to_list(current_sprints, sprint_number)
        self.tasks_df.loc[mask, 'SprintsAssigned'] = new_sprints
        
        if self.save():
            return True, "Success"
        return False, "Failed to save"
    
    def assign_tasks_to_sprint(self, unique_task_ids: List[str], sprint_number: int) -> Tuple[int, int, List[str]]:
        """
        Add sprint assignment to multiple tasks (appends to SprintsAssigned list).
        
        Args:
            unique_task_ids: List of UniqueTaskIds
            sprint_number: Sprint number to assign to
        
        Returns:
            Tuple of (assigned_count, skipped_count, error_messages)
        """
        if self.tasks_df.empty:
            return 0, 0, ["Task store is empty"]
        
        # Get sprint info to validate
        sprint_info = self.calendar.get_sprint_by_number(sprint_number)
        if not sprint_info:
            return 0, 0, [f"Sprint {sprint_number} not found"]
        
        assigned = 0
        skipped = 0
        errors = []
        
        for unique_id in unique_task_ids:
            mask = self.tasks_df['UniqueTaskId'] == unique_id
            if mask.any():
                # VALIDATION: Cannot assign to sprint older than task creation date
                original_sprint = self.tasks_df.loc[mask, 'OriginalSprintNumber'].iloc[0]
                if pd.notna(original_sprint) and sprint_number < original_sprint:
                    skipped += 1
                    task_num = self.tasks_df.loc[mask, 'TaskNum'].iloc[0]
                    errors.append(f"Task {task_num}: created in Sprint {int(original_sprint)}, cannot assign to Sprint {sprint_number}")
                else:
                    # Check if already assigned to this sprint
                    current_sprints = self.tasks_df.loc[mask, 'SprintsAssigned'].iloc[0]
                    if self._sprint_in_list(current_sprints, sprint_number):
                        skipped += 1
                        task_num = self.tasks_df.loc[mask, 'TaskNum'].iloc[0]
                        errors.append(f"Task {task_num}: already assigned to Sprint {sprint_number}")
                    else:
                        # Add sprint to the list
                        new_sprints = self._add_sprint_to_list(current_sprints, sprint_number)
                        self.tasks_df.loc[mask, 'SprintsAssigned'] = new_sprints
                        assigned += 1
        
        if assigned > 0:
            self.save()
        
        return assigned, skipped, errors
    
    def get_all_tasks(self) -> pd.DataFrame:
        """Get all tasks in the store"""
        return self.tasks_df.copy()
    
    def get_task_history(self, task_num: str) -> pd.DataFrame:
        """
        Get all instances of a task across sprints.
        Useful for tracking task movement.
        
        Args:
            task_num: Original TaskNum (not UniqueTaskId)
        
        Returns:
            DataFrame with task appearances across sprints
        """
        if self.tasks_df.empty:
            return pd.DataFrame()
        
        # Find all tasks with this TaskNum (could be in multiple sprints if reopened as new)
        mask = self.tasks_df['TaskNum'] == task_num
        return self.tasks_df[mask].copy()
    
    def get_capacity_summary(self, sprint_tasks: pd.DataFrame) -> pd.DataFrame:
        """
        Get capacity summary per person showing Mandatory vs Stretch hours.
        
        Args:
            sprint_tasks: DataFrame of tasks for a sprint (from get_sprint_tasks)
        
        Returns:
            DataFrame with columns: AssignedTo, MandatoryHours, StretchHours, TotalHours,
                                   MandatoryLimit, StretchLimit, MandatoryOver, StretchOver
        """
        if sprint_tasks.empty:
            return pd.DataFrame()
        
        # Ensure required columns exist
        if 'HoursEstimated' not in sprint_tasks.columns:
            sprint_tasks['HoursEstimated'] = 0
        if 'GoalType' not in sprint_tasks.columns:
            sprint_tasks['GoalType'] = DEFAULT_GOAL_TYPE
        
        # Use display name if available
        assignee_col = 'AssignedTo_Display' if 'AssignedTo_Display' in sprint_tasks.columns else 'AssignedTo'
        
        # Group by assignee and goal type
        summary_data = []
        for assignee in sprint_tasks[assignee_col].dropna().unique():
            assignee_tasks = sprint_tasks[sprint_tasks[assignee_col] == assignee]
            
            mandatory_hours = assignee_tasks[
                assignee_tasks['GoalType'] == 'Mandatory'
            ]['HoursEstimated'].fillna(0).sum()
            
            stretch_hours = assignee_tasks[
                assignee_tasks['GoalType'] == 'Stretch'
            ]['HoursEstimated'].fillna(0).sum()
            
            total_hours = mandatory_hours + stretch_hours
            
            summary_data.append({
                'AssignedTo': assignee,
                'MandatoryHours': mandatory_hours,
                'StretchHours': stretch_hours,
                'TotalHours': total_hours,
                'MandatoryLimit': CAPACITY_LIMITS['Mandatory'],
                'StretchLimit': CAPACITY_LIMITS['Stretch'],
                'TotalLimit': CAPACITY_LIMITS['Total'],
                'MandatoryOver': mandatory_hours > CAPACITY_LIMITS['Mandatory'],
                'StretchOver': stretch_hours > CAPACITY_LIMITS['Stretch'],
                'TotalOver': total_hours > CAPACITY_LIMITS['Total']
            })
        
        return pd.DataFrame(summary_data)


# Singleton instance
_store_instance = None

def get_task_store() -> TaskStore:
    """Get the singleton task store instance"""
    global _store_instance
    if _store_instance is None:
        _store_instance = TaskStore()
    return _store_instance
