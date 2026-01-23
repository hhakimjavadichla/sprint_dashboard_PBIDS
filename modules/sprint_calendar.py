"""
Sprint Calendar Module
Manages sprint windows defined in CSV file and auto-assigns tasks to sprints
"""
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List

# Path to sprint calendar CSV
SPRINT_CALENDAR_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'sprint_calendar.csv'
)


class SprintCalendar:
    """Manages sprint windows from CSV calendar file"""
    
    def __init__(self, calendar_path: str = None):
        """
        Initialize sprint calendar
        
        Args:
            calendar_path: Path to sprint calendar CSV (optional)
        """
        self.calendar_path = calendar_path or SPRINT_CALENDAR_PATH
        self.calendar_df = self._load_calendar()
    
    def _load_calendar(self) -> pd.DataFrame:
        """Load sprint calendar from CSV"""
        if not os.path.exists(self.calendar_path):
            return pd.DataFrame(columns=[
                'SprintNumber', 'SprintName', 'SprintStartDt', 'SprintEndDt'
            ])
        
        try:
            df = pd.read_csv(self.calendar_path)
            # Parse dates with flexible format (handles both YYYY-MM-DD and M/D/YY)
            df['SprintStartDt'] = pd.to_datetime(df['SprintStartDt'], format='mixed', dayfirst=False)
            df['SprintEndDt'] = pd.to_datetime(df['SprintEndDt'], format='mixed', dayfirst=False)
            df = df.sort_values('SprintStartDt')
            return df
        except Exception as e:
            print(f"Error loading sprint calendar: {e}")
            return pd.DataFrame(columns=[
                'SprintNumber', 'SprintName', 'SprintStartDt', 'SprintEndDt'
            ])
    
    def reload(self):
        """Reload calendar from file"""
        self.calendar_df = self._load_calendar()
    
    def get_all_sprints(self) -> pd.DataFrame:
        """Get all defined sprints"""
        return self.calendar_df.copy()
    
    def get_sprint_by_number(self, sprint_number: int) -> Optional[Dict]:
        """
        Get sprint info by number
        
        Args:
            sprint_number: Sprint number to look up
            
        Returns:
            Dict with sprint info or None if not found
        """
        matches = self.calendar_df[
            self.calendar_df['SprintNumber'] == sprint_number
        ]
        
        if len(matches) == 0:
            return None
        
        row = matches.iloc[0]
        return {
            'SprintNumber': int(row['SprintNumber']),
            'SprintName': row['SprintName'],
            'SprintStartDt': row['SprintStartDt'],
            'SprintEndDt': row['SprintEndDt']
        }
    
    def get_sprint_for_date(self, date: datetime) -> Optional[Dict]:
        """
        Find which sprint a date falls into
        
        Args:
            date: Date to check
            
        Returns:
            Dict with sprint info or None if no matching sprint
        """
        if pd.isna(date):
            return None
        
        # Convert to datetime if needed
        if isinstance(date, str):
            date = pd.to_datetime(date)
        
        # Find sprint where date falls between start and end (date-only comparison)
        # Use .date() to ensure end date is inclusive of entire day
        check_date = date.date() if hasattr(date, 'date') else pd.to_datetime(date).date()
        matches = self.calendar_df[
            (self.calendar_df['SprintStartDt'].dt.date <= check_date) & 
            (self.calendar_df['SprintEndDt'].dt.date >= check_date)
        ]
        
        if len(matches) == 0:
            return None
        
        row = matches.iloc[0]
        return {
            'SprintNumber': int(row['SprintNumber']),
            'SprintName': row['SprintName'],
            'SprintStartDt': row['SprintStartDt'],
            'SprintEndDt': row['SprintEndDt']
        }
    
    def get_current_sprint(self) -> Optional[Dict]:
        """Get the sprint for today's date"""
        return self.get_sprint_for_date(datetime.now())
    
    def get_next_sprint(self) -> Optional[Dict]:
        """Get the next upcoming sprint after today"""
        today = datetime.now()
        
        future_sprints = self.calendar_df[
            self.calendar_df['SprintStartDt'] > today
        ]
        
        if len(future_sprints) == 0:
            return None
        
        row = future_sprints.iloc[0]
        return {
            'SprintNumber': int(row['SprintNumber']),
            'SprintName': row['SprintName'],
            'SprintStartDt': row['SprintStartDt'],
            'SprintEndDt': row['SprintEndDt']
        }
    
    def get_active_or_next_sprint(self) -> Optional[Dict]:
        """Get current sprint if active, otherwise next sprint"""
        current = self.get_current_sprint()
        if current:
            return current
        return self.get_next_sprint()
    
    def assign_tasks_to_sprint(
        self, 
        df: pd.DataFrame, 
        date_column: str = 'TaskAssignedDt'
    ) -> pd.DataFrame:
        """
        Assign sprint info to tasks based on their assigned date
        
        Args:
            df: DataFrame with tasks
            date_column: Column containing the date to use for sprint assignment
            
        Returns:
            DataFrame with SprintNumber, SprintName, SprintStartDt, SprintEndDt added
        """
        result = df.copy()
        
        # Initialize sprint columns
        result['SprintNumber'] = None
        result['SprintName'] = None
        result['SprintStartDt'] = None
        result['SprintEndDt'] = None
        
        if date_column not in result.columns:
            return result
        
        # Assign each task to its sprint
        for idx, row in result.iterrows():
            task_date = row[date_column]
            sprint_info = self.get_sprint_for_date(task_date)
            
            if sprint_info:
                result.at[idx, 'SprintNumber'] = sprint_info['SprintNumber']
                result.at[idx, 'SprintName'] = sprint_info['SprintName']
                result.at[idx, 'SprintStartDt'] = sprint_info['SprintStartDt']
                result.at[idx, 'SprintEndDt'] = sprint_info['SprintEndDt']
        
        return result
    
    def get_tasks_for_sprint(
        self, 
        df: pd.DataFrame, 
        sprint_number: int,
        date_column: str = 'TaskAssignedDt'
    ) -> pd.DataFrame:
        """
        Get tasks that belong to a specific sprint
        
        Args:
            df: DataFrame with tasks
            sprint_number: Sprint number to filter for
            date_column: Column containing the date to use
            
        Returns:
            DataFrame with only tasks for that sprint
        """
        sprint_info = self.get_sprint_by_number(sprint_number)
        if not sprint_info:
            return pd.DataFrame()
        
        start = sprint_info['SprintStartDt']
        end = sprint_info['SprintEndDt']
        
        if date_column not in df.columns:
            return pd.DataFrame()
        
        # Filter tasks where date falls within sprint window
        mask = (df[date_column] >= start) & (df[date_column] <= end)
        return df[mask].copy()
    
    def add_sprint(
        self, 
        sprint_number: int, 
        sprint_name: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> bool:
        """
        Add a new sprint to the calendar
        
        Args:
            sprint_number: Sprint number
            sprint_name: Sprint name
            start_date: Start date
            end_date: End date
            
        Returns:
            True if successful
        """
        new_row = pd.DataFrame([{
            'SprintNumber': sprint_number,
            'SprintName': sprint_name,
            'SprintStartDt': start_date,
            'SprintEndDt': end_date
        }])
        
        self.calendar_df = pd.concat(
            [self.calendar_df, new_row], 
            ignore_index=True
        )
        self.calendar_df = self.calendar_df.sort_values('SprintStartDt')
        
        return self.save()
    
    def save(self) -> bool:
        """Save calendar to CSV file"""
        try:
            # Format dates for CSV
            save_df = self.calendar_df.copy()
            save_df['SprintStartDt'] = save_df['SprintStartDt'].dt.strftime('%Y-%m-%d')
            save_df['SprintEndDt'] = save_df['SprintEndDt'].dt.strftime('%Y-%m-%d')
            
            save_df.to_csv(self.calendar_path, index=False)
            return True
        except Exception as e:
            print(f"Error saving sprint calendar: {e}")
            return False
    
    def get_sprint_options(self) -> List[Tuple[int, str]]:
        """
        Get list of sprints for dropdown selection
        
        Returns:
            List of (sprint_number, display_string) tuples
        """
        options = []
        for _, row in self.calendar_df.iterrows():
            display = f"Sprint {int(row['SprintNumber'])}: {row['SprintName']} ({row['SprintStartDt'].strftime('%Y-%m-%d')} to {row['SprintEndDt'].strftime('%Y-%m-%d')})"
            options.append((int(row['SprintNumber']), display))
        return options


# Singleton instance
_calendar_instance = None

def get_sprint_calendar() -> SprintCalendar:
    """Get the singleton sprint calendar instance"""
    global _calendar_instance
    if _calendar_instance is None:
        _calendar_instance = SprintCalendar()
    return _calendar_instance
