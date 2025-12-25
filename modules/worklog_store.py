"""
Worklog Store Module
Manages worklog data imported from iTrack worklog exports.

Each worklog entry represents a team member's activity log for a task.
"""
import os
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Dict, List
from modules.sprint_calendar import get_sprint_calendar
from modules.section_filter import filter_by_team_members
from utils.name_mapper import apply_name_mapping

# Default storage path
DEFAULT_WORKLOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'worklog_data.csv')

# Column mapping from iTrack worklog export
WORKLOG_COLUMN_MAP = {
    'Task ID': 'TaskNum',
    'Task_Owner': 'Owner',
    'Recid': 'RecordId',
    'Task_Minutesspent_From_Worklog': 'MinutesSpent',
    'Description': 'Description',
    'Logdate': 'LogDate'
}


class WorklogStore:
    """
    Manages worklog data for tracking team member activity.
    
    Key fields:
    - TaskNum: Task number (links to main task data)
    - Owner: Team member who logged the activity
    - RecordId: Unique ID for each worklog entry
    - MinutesSpent: Minutes spent on the activity
    - Description: Worklog description
    - LogDate: Date of the activity log
    - SprintNumber: Sprint when the activity was logged (calculated from LogDate)
    """
    
    def __init__(self, store_path: str = None):
        self.store_path = store_path or DEFAULT_WORKLOG_PATH
        self.worklog_df = self._load_store()
        self.calendar = get_sprint_calendar()
    
    def _load_store(self) -> pd.DataFrame:
        """Load worklog data from CSV"""
        if not os.path.exists(self.store_path):
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(self.store_path)
            
            # Parse date columns
            if 'LogDate' in df.columns:
                df['LogDate'] = pd.to_datetime(df['LogDate'], errors='coerce')
            
            return df
        except Exception as e:
            print(f"Error loading worklog store: {e}")
            return pd.DataFrame()
    
    def save(self) -> bool:
        """Save worklog data to CSV"""
        try:
            os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
            self.worklog_df.to_csv(self.store_path, index=False)
            return True
        except Exception as e:
            print(f"Error saving worklog store: {e}")
            return False
    
    def import_worklog(self, file_path: str = None, file_content: bytes = None) -> Tuple[bool, str, Dict]:
        """
        Import worklog data from iTrack export file.
        
        Args:
            file_path: Path to the CSV file (UTF-16 encoded TSV from iTrack)
            file_content: Raw file content bytes
        
        Returns:
            Tuple of (success, message, stats)
        """
        stats = {'total': 0, 'valid_logs': 0, 'skipped': 0}
        
        try:
            # Read the file - handle UTF-16 encoding from iTrack
            if file_content:
                import io
                # Try UTF-16 first (iTrack format), fall back to UTF-8
                try:
                    content_str = file_content.decode('utf-16')
                except:
                    content_str = file_content.decode('utf-8')
                df = pd.read_csv(io.StringIO(content_str), sep='\t')
            elif file_path:
                # Try UTF-16 first
                try:
                    df = pd.read_csv(file_path, encoding='utf-16', sep='\t')
                except:
                    df = pd.read_csv(file_path, sep='\t')
            else:
                return False, "No file provided", stats
            
            stats['total'] = len(df)
            
            # Map column names
            df = df.rename(columns=WORKLOG_COLUMN_MAP)
            
            # Filter to rows that have actual worklog entries (have RecordId)
            if 'RecordId' in df.columns:
                df = df[df['RecordId'].notna() & (df['RecordId'] != '')]
            
            if df.empty:
                return False, "No valid worklog entries found in file", stats
            
            # Parse LogDate
            if 'LogDate' in df.columns:
                df['LogDate'] = pd.to_datetime(df['LogDate'], errors='coerce')
            
            # Convert MinutesSpent to numeric
            if 'MinutesSpent' in df.columns:
                df['MinutesSpent'] = pd.to_numeric(df['MinutesSpent'], errors='coerce').fillna(0).astype(int)
            
            # Add sprint number based on LogDate
            df['SprintNumber'] = df['LogDate'].apply(self._get_sprint_for_date)
            
            # Add import timestamp
            df['ImportedAt'] = datetime.now()
            
            stats['valid_logs'] = len(df)
            stats['skipped'] = stats['total'] - stats['valid_logs']
            
            # Replace existing data with new import
            self.worklog_df = df
            
            if self.save():
                return True, f"Successfully imported {stats['valid_logs']} worklog entries", stats
            else:
                return False, "Failed to save worklog data", stats
                
        except Exception as e:
            return False, f"Import error: {str(e)}", stats
    
    def _get_sprint_for_date(self, date) -> int:
        """Get sprint number for a given date"""
        if pd.isna(date):
            return 0
        
        sprint = self.calendar.get_sprint_for_date(date)
        if sprint:
            return sprint['SprintNumber']
        return 0
    
    def get_all_worklogs(self) -> pd.DataFrame:
        """Get all worklog entries"""
        if self.worklog_df.empty:
            return pd.DataFrame()
        
        result = self.worklog_df.copy()
        result = filter_by_team_members(result, 'Owner')
        result = apply_name_mapping(result, 'Owner')
        return result
    
    def get_worklog_by_sprint(self, sprint_number: int) -> pd.DataFrame:
        """Get worklog entries for a specific sprint"""
        if self.worklog_df.empty:
            return pd.DataFrame()
        
        result = self.worklog_df[self.worklog_df['SprintNumber'] == sprint_number].copy()
        result = filter_by_team_members(result, 'Owner')
        result = apply_name_mapping(result, 'Owner')
        return result
    
    def get_activity_summary(self, sprint_number: int = None) -> pd.DataFrame:
        """
        Get activity summary by user and date.
        
        Returns DataFrame with columns:
        - Owner: Team member
        - LogDate: Date of activity
        - LogCount: Number of worklog entries
        - TotalMinutes: Sum of minutes logged
        - SprintNumber: Sprint number
        """
        if self.worklog_df.empty:
            return pd.DataFrame()
        
        df = self.worklog_df.copy()
        
        if sprint_number:
            df = df[df['SprintNumber'] == sprint_number]
        
        if df.empty:
            return pd.DataFrame()
        
        # Filter to team members
        df = filter_by_team_members(df, 'Owner')
        
        # Create date-only column for grouping
        df['Date'] = df['LogDate'].dt.date
        
        # Group by owner and date
        summary = df.groupby(['Owner', 'Date', 'SprintNumber']).agg(
            LogCount=('RecordId', 'count'),
            TotalMinutes=('MinutesSpent', 'sum')
        ).reset_index()
        
        # Apply name mapping
        summary = apply_name_mapping(summary, 'Owner')
        
        # Sort by date descending, then owner
        summary = summary.sort_values(['Date', 'Owner'], ascending=[False, True])
        
        return summary
    
    def get_user_activity(self, owner: str, sprint_number: int = None) -> pd.DataFrame:
        """Get activity for a specific user"""
        if self.worklog_df.empty:
            return pd.DataFrame()
        
        df = self.worklog_df[self.worklog_df['Owner'] == owner].copy()
        
        if sprint_number:
            df = df[df['SprintNumber'] == sprint_number]
        
        return df
    
    def get_worklogs_with_task_info(self) -> pd.DataFrame:
        """
        Get all worklog entries joined with task information.
        
        This performs a LEFT JOIN between worklogs and the main tasks table
        to enrich worklog data with task details like TicketType, Section, etc.
        
        Relationship: 1 Task -> Many Worklogs (1:N)
        
        Returns DataFrame with worklog columns plus:
        - TicketType: From tasks table (IR, SR, PR, NC, etc.)
        - Section: Lab section from tasks table
        - CustomerName: Customer name from tasks table
        - Subject: Task subject from tasks table
        - Status: Task status from tasks table
        - AssignedTo: Task assignee from tasks table
        """
        if self.worklog_df.empty:
            return pd.DataFrame()
        
        # Import task store here to avoid circular imports
        from modules.task_store import get_task_store
        
        result = self.worklog_df.copy()
        result = filter_by_team_members(result, 'Owner')
        
        # Get tasks data
        task_store = get_task_store()
        tasks_df = task_store.get_all_tasks()
        
        if not tasks_df.empty:
            # Select only the columns we need from tasks
            task_cols = ['TaskNum', 'TicketType', 'Section', 'CustomerName', 'Subject', 'Status', 'AssignedTo']
            available_cols = [col for col in task_cols if col in tasks_df.columns]
            tasks_subset = tasks_df[available_cols].drop_duplicates(subset=['TaskNum'])
            
            # Join worklogs with tasks (LEFT JOIN to keep all worklogs)
            result = result.merge(tasks_subset, on='TaskNum', how='left')
            
            # Fill missing TicketType by extracting from TaskNum as fallback
            if 'TicketType' in result.columns:
                mask = result['TicketType'].isna() | (result['TicketType'] == '')
                result.loc[mask, 'TicketType'] = result.loc[mask, 'TaskNum'].astype(str).str.extract(r'^([A-Z]+)', expand=False).fillna('Other')
            else:
                result['TicketType'] = result['TaskNum'].astype(str).str.extract(r'^([A-Z]+)', expand=False).fillna('Other')
        else:
            # No tasks data - derive TicketType from TaskNum
            result['TicketType'] = result['TaskNum'].astype(str).str.extract(r'^([A-Z]+)', expand=False).fillna('Other')
        
        result = apply_name_mapping(result, 'Owner')
        return result
    
    def get_sprint_totals(self) -> pd.DataFrame:
        """
        Get total activity per sprint.
        
        Returns DataFrame with:
        - SprintNumber
        - TotalLogs: Total number of worklog entries
        - TotalMinutes: Total minutes logged
        - UniqueUsers: Number of unique team members with logs
        - UniqueDays: Number of days with activity
        """
        if self.worklog_df.empty:
            return pd.DataFrame()
        
        df = filter_by_team_members(self.worklog_df.copy(), 'Owner')
        
        if df.empty:
            return pd.DataFrame()
        
        df['Date'] = df['LogDate'].dt.date
        
        totals = df.groupby('SprintNumber').agg(
            TotalLogs=('RecordId', 'count'),
            TotalMinutes=('MinutesSpent', 'sum'),
            UniqueUsers=('Owner', 'nunique'),
            UniqueDays=('Date', 'nunique')
        ).reset_index()
        
        return totals.sort_values('SprintNumber', ascending=False)


# Singleton instance
_worklog_store = None

def get_worklog_store() -> WorklogStore:
    """Get singleton WorklogStore instance"""
    global _worklog_store
    if _worklog_store is None:
        _worklog_store = WorklogStore()
    return _worklog_store

def reset_worklog_store():
    """Reset the singleton (useful after import)"""
    global _worklog_store
    _worklog_store = None
