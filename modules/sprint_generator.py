"""
Sprint generation core logic
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Dict
from modules.data_loader import DataLoader
from modules.tat_calculator import apply_tat_escalation
from utils.constants import STATUS_EXCLUDED, SPRINT_DURATION_DAYS
from utils.date_utils import calculate_days_open


class SprintGenerator:
    """
    Core sprint generation logic
    Handles carryover, new task identification, and sprint creation
    """
    
    def __init__(self, data_loader: DataLoader = None):
        if data_loader is None:
            data_loader = DataLoader()
        self.data_loader = data_loader
    
    def generate_new_sprint(
        self,
        itrack_df: pd.DataFrame,
        sprint_number: int,
        sprint_start_dt: datetime,
        sprint_name: str = None,
        sprint_end_dt: datetime = None
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Generate new sprint from iTrack data
        
        Args:
            itrack_df: iTrack extract DataFrame
            sprint_number: Sprint number
            sprint_start_dt: Sprint start date
            sprint_name: Optional sprint name
            sprint_end_dt: Optional sprint end date (from calendar). If not provided, calculated from duration.
        
        Returns:
            Tuple of (Sprint DataFrame, Statistics dictionary)
        """
        stats = {
            'carryover_count': 0,
            'new_task_count': 0,
            'escalated_count': 0,
            'total_tasks': 0,
            'archived': False
        }
        
        # Step 1: Archive current sprint
        archived = self.data_loader.archive_current_sprint()
        stats['archived'] = archived
        
        # Step 2: Load previous sprint (include completed tasks for carryover analysis)
        prev_sprint = self.data_loader.load_current_sprint(include_completed=True)
        
        # Calculate sprint_end_dt if not provided (from calendar)
        if sprint_end_dt is None:
            sprint_end_dt = sprint_start_dt + timedelta(days=SPRINT_DURATION_DAYS - 1)
        
        if prev_sprint is None or prev_sprint.empty:
            prev_sprint = pd.DataFrame()
        
        # Step 3: Identify carryover tasks (incomplete from previous sprint)
        carryover_tasks = self._get_carryover_tasks(prev_sprint, itrack_df)
        stats['carryover_count'] = len(carryover_tasks)
        
        # Get carryover task numbers to exclude from window tasks
        carryover_task_nums = []
        if len(carryover_tasks) > 0:
            carryover_task_nums = carryover_tasks['TaskNum'].tolist()
        
        # Step 4: Get tasks assigned within this sprint window
        # Only include tasks where Task Assigned Date falls between sprint start and end
        window_tasks = self._get_tasks_in_sprint_window(
            itrack_df, 
            sprint_start_dt, 
            sprint_end_dt,
            carryover_task_nums  # Exclude carryover tasks
        )
        stats['new_task_count'] = len(window_tasks)
        
        # Step 5: Combine carryover + window tasks
        if len(carryover_tasks) > 0 and len(window_tasks) > 0:
            sprint_df = pd.concat([carryover_tasks, window_tasks], ignore_index=True)
        elif len(carryover_tasks) > 0:
            sprint_df = carryover_tasks
        elif len(window_tasks) > 0:
            sprint_df = window_tasks
        else:
            # Empty sprint (unusual but possible)
            sprint_df = pd.DataFrame()
        
        if sprint_df.empty:
            stats['total_tasks'] = 0
            return sprint_df, stats
        
        # Step 6: Add sprint metadata
        
        if sprint_name is None:
            sprint_name = f"Sprint {sprint_number}"
        
        sprint_df['SprintNumber'] = sprint_number
        sprint_df['SprintName'] = sprint_name
        sprint_df['SprintStartDt'] = sprint_start_dt
        sprint_df['SprintEndDt'] = sprint_end_dt
        
        # Step 7: Calculate DaysOpen
        sprint_df = self._calculate_days_open(sprint_df)
        
        # Step 8: Apply TAT escalation
        sprint_df, escalated = apply_tat_escalation(sprint_df)
        stats['escalated_count'] = escalated
        
        # Step 9: Sort by days open (descending) - priority is dashboard-only
        sprint_df = sprint_df.sort_values(
            ['DaysOpen'],
            ascending=[False]
        )
        
        # Reset index
        sprint_df = sprint_df.reset_index(drop=True)
        
        # Step 10: Reorder columns according to config
        sprint_df = self._reorder_columns(sprint_df)
        
        stats['total_tasks'] = len(sprint_df)
        
        return sprint_df, stats
    
    def _get_carryover_tasks(
        self,
        prev_sprint: pd.DataFrame,
        itrack_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Get uncompleted tasks from previous sprint
        
        Args:
            prev_sprint: Previous sprint DataFrame
            itrack_df: Fresh iTrack data
        
        Returns:
            DataFrame of carryover tasks with updated status/priority
        """
        if prev_sprint is None or prev_sprint.empty:
            return pd.DataFrame()
        
        # Filter: Not Completed and Not Canceled
        carryover = prev_sprint[
            ~prev_sprint['TaskStatus'].isin(STATUS_EXCLUDED)
        ].copy()
        
        if carryover.empty:
            return pd.DataFrame()
        
        # Update status and priority from fresh iTrack data
        for idx in carryover.index:
            task_num = carryover.at[idx, 'TaskNum']
            
            # Find matching task in iTrack
            fresh_data = itrack_df[itrack_df['Task'] == task_num]
            
            if not fresh_data.empty:
                # Update status
                if 'TaskStatus' in fresh_data.columns:
                    carryover.at[idx, 'TaskStatus'] = fresh_data.iloc[0]['TaskStatus']
                
                # Note: CustomerPriority is dashboard-only, not updated from iTrack
                
                # Update assignee if changed
                if 'Assignee' in fresh_data.columns:
                    carryover.at[idx, 'AssignedTo'] = fresh_data.iloc[0]['Assignee']
        
        # Clear estimated effort for re-evaluation
        carryover['HoursEstimated'] = None
        
        # Add carryover comment
        carryover['Comments'] = carryover['Comments'].fillna('') + '\n[Carried over from previous sprint]'
        carryover['Comments'] = carryover['Comments'].str.strip()
        
        return carryover
    
    def _get_tasks_in_sprint_window(
        self,
        itrack_df: pd.DataFrame,
        sprint_start_dt: datetime,
        sprint_end_dt: datetime,
        carryover_task_nums: list = None
    ) -> pd.DataFrame:
        """
        Get tasks where Task Assigned Date falls within the sprint window
        
        Args:
            itrack_df: iTrack extract DataFrame
            sprint_start_dt: Sprint start date
            sprint_end_dt: Sprint end date
            carryover_task_nums: List of task numbers already included as carryover (to exclude)
        
        Returns:
            DataFrame of tasks assigned within the sprint window
        """
        # Map iTrack columns to sprint schema
        sprint_df = self.data_loader.map_itrack_to_sprint(itrack_df)
        
        if carryover_task_nums is None:
            carryover_task_nums = []
        
        # Exclude carryover tasks (they're already added separately)
        if carryover_task_nums:
            sprint_df = sprint_df[~sprint_df['TaskNum'].isin(carryover_task_nums)]
        
        # Filter by Task Assigned Date within sprint window
        if 'TaskAssignedDt' in sprint_df.columns:
            sprint_df['TaskAssignedDt'] = pd.to_datetime(
                sprint_df['TaskAssignedDt'],
                errors='coerce'
            )
            
            # Tasks assigned within this sprint window
            tasks_in_window = sprint_df[
                (sprint_df['TaskAssignedDt'] >= sprint_start_dt) &
                (sprint_df['TaskAssignedDt'] <= sprint_end_dt)
            ].copy()
        elif 'TicketCreatedDt' in sprint_df.columns:
            # Fallback to ticket created date if no task assigned date
            sprint_df['TicketCreatedDt'] = pd.to_datetime(
                sprint_df['TicketCreatedDt'],
                errors='coerce'
            )
            
            tasks_in_window = sprint_df[
                (sprint_df['TicketCreatedDt'] >= sprint_start_dt) &
                (sprint_df['TicketCreatedDt'] <= sprint_end_dt)
            ].copy()
        else:
            # No date column available - include all non-carryover tasks
            tasks_in_window = sprint_df.copy()
        
        return tasks_in_window
    
    def _calculate_days_open(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate DaysOpen for all tasks based on Task Assigned Date
        
        DaysOpen = Days since task was assigned (not created)
        Falls back to TicketCreatedDt if TaskAssignedDt not available
        
        Args:
            df: Sprint DataFrame
        
        Returns:
            DataFrame with DaysOpen calculated
        """
        # Prefer TaskAssignedDt, fall back to TicketCreatedDt
        if 'TaskAssignedDt' in df.columns:
            date_col = 'TaskAssignedDt'
        elif 'TicketCreatedDt' in df.columns:
            date_col = 'TicketCreatedDt'
        else:
            df['DaysOpen'] = 0.0
            return df
        
        def calc_days(assigned_dt):
            if pd.isna(assigned_dt):
                return 0.0
            return calculate_days_open(assigned_dt)
        
        df['DaysOpen'] = df[date_col].apply(calc_days)
        
        return df
    
    def _reorder_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Reorder DataFrame columns according to config
        
        Args:
            df: Sprint DataFrame
        
        Returns:
            DataFrame with columns in configured order
        """
        # Get column order from config
        config = self.data_loader.config
        column_order = config.get('sprint_columns', {}).get('column_order', [])
        
        if not column_order:
            # No config defined, return as-is
            return df
        
        # Select only columns that exist in the DataFrame, in config order
        available_columns = [col for col in column_order if col in df.columns]
        
        # Add any columns not in config at the end (shouldn't happen, but safe)
        extra_columns = [col for col in df.columns if col not in column_order]
        final_columns = available_columns + extra_columns
        
        return df[final_columns]
    
    def validate_sprint_data(self, sprint_df: pd.DataFrame) -> Tuple[bool, list]:
        """
        Validate sprint data before saving
        
        Args:
            sprint_df: Sprint DataFrame
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if sprint_df.empty:
            errors.append("Sprint is empty")
            return False, errors
        
        # Check required columns
        required_cols = [
            'SprintNumber', 'TaskNum', 'TicketNum', 
            'TaskStatus', 'Subject', 'SprintStartDt', 'SprintEndDt'
        ]
        
        missing = [col for col in required_cols if col not in sprint_df.columns]
        if missing:
            errors.append(f"Missing required columns: {', '.join(missing)}")
        
        # Check sprint number consistency
        if 'SprintNumber' in sprint_df.columns:
            unique_sprint_nums = sprint_df['SprintNumber'].nunique()
            if unique_sprint_nums > 1:
                errors.append(f"Multiple sprint numbers found: {unique_sprint_nums}")
        
        # Check for duplicate task numbers
        if 'TaskNum' in sprint_df.columns:
            duplicates = sprint_df['TaskNum'].duplicated().sum()
            if duplicates > 0:
                errors.append(f"Found {duplicates} duplicate task numbers")
        
        is_valid = len(errors) == 0
        return is_valid, errors
