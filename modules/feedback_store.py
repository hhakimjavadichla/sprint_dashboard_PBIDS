"""
Sprint Feedback Store Module
Manages sprint feedback data for Section Managers.
"""
import os
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, List, Dict
from modules.sqlite_store import is_sqlite_enabled, load_feedback, save_feedback

# Default storage path
DEFAULT_FEEDBACK_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'sprint_feedback.csv')

# Feedback columns
FEEDBACK_COLUMNS = [
    'FeedbackId',
    'SprintNumber',
    'Section',
    'SubmittedBy',
    'SubmittedAt',
    'OverallSatisfaction',
    'WhatWentWell',
    'WhatDidNotGoWell'
]


class FeedbackStore:
    """Manages sprint feedback data"""
    
    def __init__(self, store_path: str = None):
        self.store_path = store_path or DEFAULT_FEEDBACK_PATH
        self.use_sqlite = is_sqlite_enabled()
        self.feedback_df = self._load_store()
    
    def _load_store(self) -> pd.DataFrame:
        """Load feedback from CSV or SQLite"""
        if self.use_sqlite:
            return self._load_from_sqlite()
        if not os.path.exists(self.store_path):
            # Create empty DataFrame if no file exists
            df = pd.DataFrame(columns=FEEDBACK_COLUMNS)
            self._save_df(df)
            return df
        
        try:
            df = pd.read_csv(self.store_path)
            # Ensure all required columns exist
            for col in FEEDBACK_COLUMNS:
                if col not in df.columns:
                    df[col] = ''
            return df
        except Exception as e:
            print(f"Error loading feedback store: {e}")
            return pd.DataFrame(columns=FEEDBACK_COLUMNS)
    
    def _save_df(self, df: pd.DataFrame) -> bool:
        """Save DataFrame to CSV"""
        try:
            os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
            df.to_csv(self.store_path, index=False)
            return True
        except Exception as e:
            print(f"Error saving feedback store: {e}")
            return False
    
    def save(self) -> bool:
        """Save current state to CSV or SQLite"""
        if self.use_sqlite:
            return save_feedback(None, self.feedback_df)
        return self._save_df(self.feedback_df)

    def _load_from_sqlite(self) -> pd.DataFrame:
        """Load feedback from SQLite."""
        df = load_feedback()
        for col in FEEDBACK_COLUMNS:
            if col not in df.columns:
                df[col] = ''
        return df
    
    def reload(self):
        """Reload data from disk"""
        self.feedback_df = self._load_store()
    
    def get_feedback_for_sprint(self, sprint_number: int, section: str = None) -> pd.DataFrame:
        """Get all feedback for a specific sprint, optionally filtered by section"""
        if self.feedback_df.empty:
            return pd.DataFrame(columns=FEEDBACK_COLUMNS)
        
        mask = self.feedback_df['SprintNumber'] == sprint_number
        if section:
            mask = mask & (self.feedback_df['Section'] == section)
        
        return self.feedback_df[mask].copy()
    
    def get_feedback_by_user(self, username: str) -> pd.DataFrame:
        """Get all feedback submitted by a specific user"""
        if self.feedback_df.empty:
            return pd.DataFrame(columns=FEEDBACK_COLUMNS)
        
        return self.feedback_df[self.feedback_df['SubmittedBy'] == username].copy()
    
    def has_feedback(self, sprint_number: int, section: str, username: str) -> bool:
        """Check if user has already submitted feedback for a sprint/section"""
        if self.feedback_df.empty:
            return False
        
        mask = (
            (self.feedback_df['SprintNumber'] == sprint_number) &
            (self.feedback_df['Section'] == section) &
            (self.feedback_df['SubmittedBy'] == username)
        )
        return mask.any()
    
    def add_feedback(
        self,
        sprint_number: int,
        section: str,
        submitted_by: str,
        overall_satisfaction: int,
        what_went_well: str,
        what_did_not_go_well: str
    ) -> Tuple[bool, str]:
        """Add new feedback for a sprint"""
        
        # Check if feedback already exists
        if self.has_feedback(sprint_number, section, submitted_by):
            return False, f"Feedback already submitted for Sprint {sprint_number} by {submitted_by} for section {section}"
        
        # Validate satisfaction rating
        if overall_satisfaction < 1 or overall_satisfaction > 5:
            return False, "Overall satisfaction must be between 1 and 5"
        
        # Generate feedback ID
        feedback_id = f"FB-{sprint_number}-{section}-{submitted_by}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create new feedback record
        new_feedback = pd.DataFrame([{
            'FeedbackId': feedback_id,
            'SprintNumber': sprint_number,
            'Section': section,
            'SubmittedBy': submitted_by,
            'SubmittedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'OverallSatisfaction': overall_satisfaction,
            'WhatWentWell': what_went_well,
            'WhatDidNotGoWell': what_did_not_go_well
        }])
        
        self.feedback_df = pd.concat([self.feedback_df, new_feedback], ignore_index=True)
        
        if self._save_df(self.feedback_df):
            return True, "Feedback submitted successfully"
        return False, "Failed to save feedback"
    
    def get_all_feedback(self) -> pd.DataFrame:
        """Get all feedback records"""
        return self.feedback_df.copy()


# Singleton instance
_feedback_store = None

def get_feedback_store() -> FeedbackStore:
    """Get singleton FeedbackStore instance"""
    global _feedback_store
    if _feedback_store is None:
        _feedback_store = FeedbackStore()
    return _feedback_store

def reset_feedback_store():
    """Reset singleton to force reload"""
    global _feedback_store
    _feedback_store = None
