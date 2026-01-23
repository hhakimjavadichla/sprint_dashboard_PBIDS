"""
Worklog Store Module
Manages worklog data imported from iTrack worklog exports.

Data Source Modes:
- CSV Mode: Worklog data from local CSV (legacy, for backward compatibility)
- Snowflake Mode: Worklog data from Snowflake DS_VW_ITRACK_LPM_WORKLOG table

Each worklog entry represents a team member's activity log for a task.
"""
import os
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Dict, List
from modules.sprint_calendar import get_sprint_calendar
from modules.section_filter import filter_by_team_members
from utils.name_mapper import apply_name_mapping
from modules.sqlite_store import is_sqlite_enabled, load_worklogs, save_worklogs

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
    
    Data Source Modes:
    - CSV Mode (legacy): All data from local CSV file
    - Snowflake Mode: Worklog data from Snowflake
    
    Key fields:
    - TaskNum: Task number (links to main task data)
    - Owner: Team member who logged the activity
    - RecordId: Unique ID for each worklog entry
    - MinutesSpent: Minutes spent on the activity
    - Description: Worklog description
    - LogDate: Date of the activity log
    - SprintNumber: Sprint when the activity was logged (calculated from LogDate)
    """
    
    def __init__(self, store_path: str = None, use_snowflake: bool = None):
        self.store_path = store_path or DEFAULT_WORKLOG_PATH
        self.calendar = get_sprint_calendar()
        self.use_sqlite = is_sqlite_enabled()
        
        # Determine data source mode
        if self.use_sqlite:
            self.use_snowflake = False
        elif use_snowflake is None:
            # Auto-detect: use Snowflake if explicitly enabled in config
            from modules.snowflake_connector import is_snowflake_enabled
            self.use_snowflake = is_snowflake_enabled()
        else:
            self.use_snowflake = use_snowflake
        
        self.worklog_df = self._load_store()
    
    def _load_store(self) -> pd.DataFrame:
        """Load worklog data from store (CSV or Snowflake mode)"""
        if self.use_sqlite:
            return self._load_from_sqlite()
        if self.use_snowflake:
            return self._load_from_snowflake()
        else:
            return self._load_from_csv()

    def _load_from_sqlite(self) -> pd.DataFrame:
        """Load worklog data from SQLite."""
        df = load_worklogs()
        if df.empty:
            return df
        if 'LogDate' in df.columns:
            df['LogDate'] = pd.to_datetime(df['LogDate'], errors='coerce')
        return df
    
    def _load_from_snowflake(self) -> pd.DataFrame:
        """Load worklog data from Snowflake"""
        from modules.snowflake_connector import fetch_worklogs_from_snowflake, is_snowflake_configured
        
        if not is_snowflake_configured():
            print("WorklogStore: Snowflake not configured, falling back to CSV")
            return self._load_from_csv()
        
        # Fetch worklog data from Snowflake
        snowflake_df, success, message = fetch_worklogs_from_snowflake()
        
        if not success or snowflake_df.empty:
            print(f"WorklogStore: Failed to load from Snowflake: {message}")
            # Fall back to CSV if Snowflake fails
            return self._load_from_csv()
        
        # Ensure TaskNum is string
        if 'TaskNum' in snowflake_df.columns:
            snowflake_df['TaskNum'] = snowflake_df['TaskNum'].astype(str)
        
        # Calculate SprintNumber from LogDate
        if 'LogDate' in snowflake_df.columns:
            snowflake_df['SprintNumber'] = snowflake_df['LogDate'].apply(
                lambda d: self.calendar.get_sprint_for_date(d) if pd.notna(d) else None
            )
        
        print(f"WorklogStore: Loaded {len(snowflake_df)} worklog entries from Snowflake")
        return snowflake_df
    
    def _load_from_csv(self) -> pd.DataFrame:
        """Load worklog data from CSV (legacy mode)"""
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
        if self.use_sqlite:
            return save_worklogs(None, self.worklog_df)
        try:
            os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
            self.worklog_df.to_csv(self.store_path, index=False)
            return True
        except Exception as e:
            print(f"Error saving worklog store: {e}")
            return False
    
    def import_worklog(self, file_path: str = None, file_content: bytes = None) -> Tuple[bool, str, Dict]:
        """
        Import worklog data from iTrack export file using date-based merge strategy.
        
        Strategy:
        - For dates included in the upload: Replace all records for those dates
        - For dates NOT in the upload: Preserve existing data
        
        This allows incremental updates (e.g., weekly exports) while preserving
        historical data for dates not included in the upload.
        
        Args:
            file_path: Path to the CSV file (UTF-16 encoded TSV from iTrack)
            file_content: Raw file content bytes
        
        Returns:
            Tuple of (success, message, stats)
        """
        stats = {
            'total': 0,
            'valid_logs': 0,
            'skipped': 0,
            'dates_in_upload': 0,
            'records_replaced': 0,
            'records_preserved': 0
        }
        
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
            
            # Date-based merge strategy
            # Get unique dates from uploaded data (as date only, not datetime)
            uploaded_dates = set(df['LogDate'].dt.date.dropna().unique())
            stats['dates_in_upload'] = len(uploaded_dates)
            
            if not self.worklog_df.empty and 'LogDate' in self.worklog_df.columns:
                # Get existing records for dates NOT in the upload
                existing_df = self.worklog_df.copy()
                existing_df['_date'] = pd.to_datetime(existing_df['LogDate'], errors='coerce').dt.date
                
                # Keep only records where date is NOT in the uploaded dates
                preserved_df = existing_df[~existing_df['_date'].isin(uploaded_dates)].drop(columns=['_date'])
                stats['records_preserved'] = len(preserved_df)
                
                # Count how many records we're replacing (for dates in upload)
                replaced_df = existing_df[existing_df['_date'].isin(uploaded_dates)]
                stats['records_replaced'] = len(replaced_df)
                
                # Merge: preserved records + new uploaded records
                self.worklog_df = pd.concat([preserved_df, df], ignore_index=True)
            else:
                # No existing data, just use new data
                self.worklog_df = df
                stats['records_preserved'] = 0
                stats['records_replaced'] = 0
            
            if self.save():
                msg = f"Successfully imported {stats['valid_logs']} worklog entries for {stats['dates_in_upload']} dates"
                if stats['records_preserved'] > 0:
                    msg += f" (preserved {stats['records_preserved']} existing records for other dates)"
                return True, msg, stats
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
            task_cols = ['TaskNum', 'TicketType', 'Section', 'CustomerName', 'Subject', 'TaskStatus', 'AssignedTo', 'SprintsAssigned']
            available_cols = [col for col in task_cols if col in tasks_df.columns]
            tasks_subset = tasks_df[available_cols].drop_duplicates(subset=['TaskNum'])
            
            # Join worklogs with tasks (LEFT JOIN to keep all worklogs)
            result = result.merge(tasks_subset, on='TaskNum', how='left')
            
            # TicketType comes from Subject parsing in tasks - no fallback
            if 'TicketType' not in result.columns:
                result['TicketType'] = 'NC'
        else:
            # No tasks data - default to NC
            result['TicketType'] = 'NC'
        
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
