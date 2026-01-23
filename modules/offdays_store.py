"""
Off Days Store Module
Manages team member off days / availability during sprints.
"""
import os
import pandas as pd
from datetime import datetime, date
from typing import Optional, Tuple, List
from modules.sqlite_store import is_sqlite_enabled, load_offdays, save_offdays

# Default storage path
DEFAULT_OFFDAYS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'team_offdays.csv')

# Off days columns
OFFDAYS_COLUMNS = [
    'Username',
    'SprintNumber',
    'OffDate',
    'Reason',
    'CreatedBy',
    'CreatedAt'
]


class OffDaysStore:
    """Manages team member off days data"""
    
    def __init__(self, store_path: str = None):
        self.store_path = store_path or DEFAULT_OFFDAYS_PATH
        self.use_sqlite = is_sqlite_enabled()
        self.offdays_df = self._load_store()
    
    def _load_store(self) -> pd.DataFrame:
        """Load off days from CSV or SQLite"""
        if self.use_sqlite:
            return self._load_from_sqlite()
        if not os.path.exists(self.store_path):
            df = pd.DataFrame(columns=OFFDAYS_COLUMNS)
            self._save_df(df)
            return df
        
        try:
            df = pd.read_csv(self.store_path)
            for col in OFFDAYS_COLUMNS:
                if col not in df.columns:
                    df[col] = ''
            return df
        except Exception as e:
            print(f"Error loading off days store: {e}")
            return pd.DataFrame(columns=OFFDAYS_COLUMNS)
    
    def _save_df(self, df: pd.DataFrame) -> bool:
        """Save DataFrame to CSV"""
        try:
            os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
            df.to_csv(self.store_path, index=False)
            return True
        except Exception as e:
            print(f"Error saving off days store: {e}")
            return False
    
    def save(self) -> bool:
        """Save current state to CSV or SQLite"""
        if self.use_sqlite:
            return save_offdays(None, self.offdays_df)
        return self._save_df(self.offdays_df)

    def _load_from_sqlite(self) -> pd.DataFrame:
        """Load off days from SQLite."""
        df = load_offdays()
        for col in OFFDAYS_COLUMNS:
            if col not in df.columns:
                df[col] = ''
        return df
    
    def reload(self):
        """Reload data from disk"""
        self.offdays_df = self._load_store()
    
    def get_offdays_for_sprint(self, sprint_number: int) -> pd.DataFrame:
        """Get all off days for a specific sprint"""
        if self.offdays_df.empty:
            return pd.DataFrame(columns=OFFDAYS_COLUMNS)
        
        return self.offdays_df[self.offdays_df['SprintNumber'] == sprint_number].copy()
    
    def get_offdays_for_user(self, username: str, sprint_number: int = None) -> pd.DataFrame:
        """Get off days for a specific user, optionally filtered by sprint"""
        if self.offdays_df.empty:
            return pd.DataFrame(columns=OFFDAYS_COLUMNS)
        
        mask = self.offdays_df['Username'] == username
        if sprint_number is not None:
            mask = mask & (self.offdays_df['SprintNumber'] == sprint_number)
        
        return self.offdays_df[mask].copy()
    
    def get_offday_count(self, username: str, sprint_number: int) -> int:
        """Get number of off days for a user in a sprint"""
        offdays = self.get_offdays_for_user(username, sprint_number)
        return len(offdays)
    
    def get_off_dates_list(self, username: str, sprint_number: int) -> List[str]:
        """Get list of off dates for a user in a sprint"""
        offdays = self.get_offdays_for_user(username, sprint_number)
        if offdays.empty:
            return []
        return offdays['OffDate'].tolist()
    
    def is_off_day(self, username: str, sprint_number: int, check_date: str) -> bool:
        """Check if a specific date is an off day for a user"""
        offdays = self.get_offdays_for_user(username, sprint_number)
        if offdays.empty:
            return False
        return check_date in offdays['OffDate'].values
    
    def add_offday(
        self,
        username: str,
        sprint_number: int,
        off_date: str,
        reason: str,
        created_by: str
    ) -> Tuple[bool, str]:
        """Add an off day for a team member"""
        
        # Check if already exists
        existing = self.offdays_df[
            (self.offdays_df['Username'] == username) &
            (self.offdays_df['SprintNumber'] == sprint_number) &
            (self.offdays_df['OffDate'] == off_date)
        ]
        
        if not existing.empty:
            return False, f"Off day already exists for {username} on {off_date}"
        
        new_offday = pd.DataFrame([{
            'Username': username,
            'SprintNumber': sprint_number,
            'OffDate': off_date,
            'Reason': reason,
            'CreatedBy': created_by,
            'CreatedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }])
        
        self.offdays_df = pd.concat([self.offdays_df, new_offday], ignore_index=True)
        
        if self._save_df(self.offdays_df):
            return True, "Off day added successfully"
        return False, "Failed to save off day"
    
    def remove_offday(self, username: str, sprint_number: int, off_date: str) -> Tuple[bool, str]:
        """Remove an off day"""
        mask = (
            (self.offdays_df['Username'] == username) &
            (self.offdays_df['SprintNumber'] == sprint_number) &
            (self.offdays_df['OffDate'] == off_date)
        )
        
        if not mask.any():
            return False, "Off day not found"
        
        self.offdays_df = self.offdays_df[~mask]
        
        if self._save_df(self.offdays_df):
            return True, "Off day removed successfully"
        return False, "Failed to remove off day"
    
    def get_all_offdays(self) -> pd.DataFrame:
        """Get all off days records"""
        return self.offdays_df.copy()
    
    def calculate_available_days(self, username: str, sprint_number: int, total_sprint_days: int) -> int:
        """Calculate available working days for a user in a sprint"""
        off_count = self.get_offday_count(username, sprint_number)
        return max(0, total_sprint_days - off_count)
    
    def calculate_available_hours(self, username: str, sprint_number: int, total_sprint_days: int, hours_per_day: float = 8.0) -> float:
        """Calculate available working hours for a user in a sprint"""
        available_days = self.calculate_available_days(username, sprint_number, total_sprint_days)
        return available_days * hours_per_day


# Singleton instance
_offdays_store = None

def get_offdays_store() -> OffDaysStore:
    """Get singleton OffDaysStore instance"""
    global _offdays_store
    if _offdays_store is None:
        _offdays_store = OffDaysStore()
    return _offdays_store

def reset_offdays_store():
    """Reset singleton to force reload"""
    global _offdays_store
    _offdays_store = None
