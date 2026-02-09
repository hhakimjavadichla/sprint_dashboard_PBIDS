"""
Task Store Module
Single source of truth for all tasks across all sprints

Data Source Modes:
- CSV Mode: All data from local CSV (legacy, for backward compatibility)
- Snowflake Mode: iTrack fields from Snowflake, dashboard fields from local CSV

Sprint Assignment Policy:
- NO automatic sprint assignment based on dates
- All new tasks go to Work Backlogs with no sprint assigned
- Admin assigns tasks to sprints manually from Work Backlogs page
- SprintsAssigned column tracks all sprint assignments (comma-separated: "4, 5")
- Existing tasks preserve their sprint assignments on re-import
"""
import os
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from modules.sprint_calendar import get_sprint_calendar, format_sprints_assigned_display
from modules.sqlite_store import is_sqlite_enabled, load_task_view, save_tasks
from utils.name_mapper import apply_name_mapping, get_display_name
from modules.section_filter import filter_by_team_members
from utils.constants import IMPORT_THRESHOLD_DATE, OPEN_TASK_STATUSES, CLOSED_TASK_STATUSES
from modules.worklog_store import get_worklog_store

# Path to all tasks store (legacy CSV mode)
ALL_TASKS_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'all_tasks.csv'
)

# Path to dashboard annotations store (used in Snowflake mode)
DASHBOARD_ANNOTATIONS_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'dashboard_annotations.csv'
)

# Statuses that indicate a task is closed (won't carry over)
CLOSED_STATUSES = [
    'Completed', 'Closed', 'Resolved', 'Done', 'Canceled', 'Cancelled',
    'Excluded from Carryover'
]

# Goal types for capacity planning
GOAL_TYPES = ['', 'Mandatory', 'Stretch']
DEFAULT_GOAL_TYPE = ''

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

# =============================================================================
# FIELD OWNERSHIP MODEL
# Defines which system owns each field for import/update purposes
# =============================================================================

# Fields owned by iTrack - ALWAYS updated from iTrack imports
ITRACK_OWNED_FIELDS = [
    'TaskNum',              # Task identifier (primary key)
    'TicketNum',            # Parent ticket ID
    'TaskStatus',           # Task status from iTrack
    'TicketStatus',         # Ticket status from iTrack
    'AssignedTo',           # Current assignee
    'Subject',              # Task subject line
    'Section',              # Team/section
    'CustomerName',         # Customer name
    'TaskAssignedDt',       # When task was assigned
    'TaskCreatedDt',        # When task was created
    'TaskResolvedDt',       # When task was resolved
    'TicketCreatedDt',      # When parent ticket was created
    'TicketResolvedDt',     # When parent ticket was resolved
    'TicketTotalTimeSpent', # Time logged on ticket
    'TaskMinutesSpent',     # Time logged on task
]

# Fields owned by Dashboard - NEVER overwritten by iTrack imports
DASHBOARD_OWNED_FIELDS = [
    'SprintsAssigned',      # Which sprints task is assigned to (admin sets)
    'CustomerPriority',     # Priority set by customer/section
    'FinalPriority',        # Final priority set by admin
    'GoalType',             # Mandatory/Stretch goal classification
    'HoursEstimated',       # Estimated hours for the task
    'DependencyOn',         # Task dependencies
    'DependenciesLead',     # Who is leading dependency resolution
    'DependencySecured',    # Whether dependencies are secured
    'Comments',             # Admin/section comments
    'NonCompletionReason',  # Reason why task was not completed in sprint
    'StatusUpdateDt',       # When status was manually updated in dashboard
]

# Fields computed by the system during import
COMPUTED_FIELDS = [
    'TicketType',           # IR/SR/PR/NC extracted from Subject
    'DaysOpen',             # Calculated from TicketCreatedDt
]

# =============================================================================
# EDITABLE FIELDS CONFIGURATION
# Centralized definition of all editable fields with their types and options
# =============================================================================
EDITABLE_FIELDS = {
    'FinalPriority': {'type': 'int', 'nullable': True, 'options': [0, 1, 2, 3, 4, 5]},
    'GoalType': {'type': 'str', 'nullable': True, 'options': ['', 'Mandatory', 'Stretch']},
    'DependencyOn': {'type': 'str', 'nullable': True, 'options': ['', 'Yes', 'No']},
    'DependenciesLead': {'type': 'str', 'nullable': True},
    'DependencySecured': {'type': 'str', 'nullable': True, 'options': ['', 'Yes', 'Pending', 'No']},
    'Comments': {'type': 'str', 'nullable': True},
    'NonCompletionReason': {'type': 'str', 'nullable': True},
    'CustomerPriority': {'type': 'int', 'nullable': True, 'options': [0, 1, 2, 3, 4, 5]},
    'HoursEstimated': {'type': 'float', 'nullable': True},
}

# String columns that need to be converted at load time
STRING_COLUMNS = ['DependencyOn', 'DependenciesLead', 'DependencySecured', 'Comments', 'NonCompletionReason', 'GoalType', 'SprintsAssigned']


class TaskStore:
    """
    Manages all tasks in a single store.
    
    Data Source Modes:
    - CSV Mode (legacy): All data from local CSV file
    - Snowflake Mode: iTrack fields from Snowflake, dashboard fields from local CSV
    
    Sprint Assignment Policy:
    - NO automatic sprint assignment based on dates
    - NO automatic carryover between sprints
    - All sprint assignments are done manually via Work Backlogs page
    - SprintsAssigned: Comma-separated list of sprints task was assigned to (e.g., "4, 5")
    """
    
    def __init__(self, store_path: str = None, use_snowflake: bool = None):
        self.store_path = store_path or ALL_TASKS_PATH
        self.annotations_path = DASHBOARD_ANNOTATIONS_PATH
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

        self.tasks_df = self._load_store()
    
    def _load_store(self) -> pd.DataFrame:
        """Load all tasks from store (CSV or Snowflake mode)"""
        if self.use_sqlite:
            return self._load_from_sqlite()
        if self.use_snowflake:
            return self._load_from_snowflake()
        else:
            return self._load_from_csv()
    
    def _load_from_snowflake(self) -> pd.DataFrame:
        """Load tasks from Snowflake and merge with local dashboard annotations"""
        from modules.snowflake_connector import fetch_tasks_from_snowflake, is_snowflake_configured
        
        if not is_snowflake_configured():
            print("TaskStore: Snowflake not configured, falling back to CSV")
            return self._load_from_csv()
        
        # Fetch iTrack data from Snowflake
        snowflake_df, success, message = fetch_tasks_from_snowflake()
        
        if not success or snowflake_df.empty:
            print(f"TaskStore: Failed to load from Snowflake: {message}")
            # Fall back to CSV if Snowflake fails
            return self._load_from_csv()
        
        # Normalize column names (Snowflake query already returns correct names)
        snowflake_df = self._normalize_snowflake_columns(snowflake_df)
        
        # Extract TicketType from Subject (same logic as CSV import)
        snowflake_df['TicketType'] = snowflake_df['Subject'].apply(self._extract_ticket_type)
        
        # Derive Section from AssignedTo (team member) or TaskOwnerTeam
        if 'Section' not in snowflake_df.columns:
            snowflake_df['Section'] = 'PIBIDS'  # Default section
        
        # Apply date-based filtering (same as import logic)
        snowflake_df = self._apply_date_filter(snowflake_df)
        
        # Load dashboard annotations from local CSV
        annotations_df = self._load_dashboard_annotations()
        
        # Merge Snowflake data with dashboard annotations
        if not annotations_df.empty and 'TaskNum' in annotations_df.columns:
            # Ensure TaskNum is string for merge
            snowflake_df['TaskNum'] = snowflake_df['TaskNum'].astype(str)
            annotations_df['TaskNum'] = annotations_df['TaskNum'].astype(str)
            
            # Only merge columns that exist in annotations
            merge_cols = ['TaskNum'] + [c for c in DASHBOARD_OWNED_FIELDS if c in annotations_df.columns]
            
            # Merge on TaskNum, keeping all Snowflake records
            df = snowflake_df.merge(
                annotations_df[merge_cols],
                on='TaskNum',
                how='left'
            )
        else:
            df = snowflake_df.copy()
        
        # Ensure dashboard fields exist with defaults
        df = self._ensure_dashboard_fields(df)
        
        # Calculate DaysOpen
        df = self._calculate_days_open(df)
        
        print(f"TaskStore: Loaded {len(df)} tasks from Snowflake")
        return df

    def _load_from_sqlite(self) -> pd.DataFrame:
        """Load tasks from SQLite compatibility view."""
        df = load_task_view()
        if df.empty:
            return df

        df = self._ensure_dashboard_fields(df)

        date_cols = [
            'TaskAssignedDt', 'StatusUpdateDt', 'TicketCreatedDt',
            'TaskCreatedDt', 'TaskResolvedDt', 'TicketResolvedDt',
            'SprintStartDt', 'SprintEndDt'
        ]
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', format='mixed')

        if 'TicketType' not in df.columns or df['TicketType'].isna().all():
            df['TicketType'] = df['Subject'].apply(self._extract_ticket_type)

        if 'SprintNumber' in df.columns:
            sprint_df = self.calendar.get_all_sprints()
            if not sprint_df.empty:
                sprint_df = sprint_df.copy()
                sprint_df['SprintNumber'] = pd.to_numeric(
                    sprint_df['SprintNumber'], errors='coerce'
                )
                sprint_df = sprint_df.dropna(subset=['SprintNumber'])
                sprint_df['SprintNumber'] = sprint_df['SprintNumber'].astype(int)

                sprint_map = sprint_df.set_index('SprintNumber')
                sprint_nums = pd.to_numeric(df['SprintNumber'], errors='coerce')
                df['SprintName'] = sprint_nums.map(sprint_map['SprintName'])
                df['SprintStartDt'] = sprint_nums.map(sprint_map['SprintStartDt'])
                df['SprintEndDt'] = sprint_nums.map(sprint_map['SprintEndDt'])

        # Apply date filter for display: only show open tickets + tickets after threshold date
        df = self._apply_date_filter(df)
        
        return df
    
    def _extract_ticket_type(self, subject: str) -> str:
        """Extract ticket type from subject line (same as CSV import)"""
        if pd.isna(subject):
            return "NC"
        
        subject_upper = str(subject).upper()
        if 'LAB-IR' in subject_upper or '-IR:' in subject_upper:
            return "IR"
        elif 'LAB-SR' in subject_upper or '-SR:' in subject_upper:
            return "SR"
        elif 'LAB-PR' in subject_upper or '-PR:' in subject_upper:
            return "PR"
        elif 'LAB-AD' in subject_upper or '-AD:' in subject_upper:
            return "AD"
        elif 'LAB INCIDENT' in subject_upper:
            return "IR"
        
        return "NC"
    
    def _normalize_snowflake_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize Snowflake column names to match expected schema"""
        # Snowflake returns uppercase columns, map to expected names
        column_mapping = {
            'TASKNUM': 'TaskNum',
            'TICKETNUM': 'TicketNum',
            'STATUS': 'TaskStatus',
            'TICKETSTATUS': 'TicketStatus',
            'ASSIGNEDTO': 'AssignedTo',
            'SUBJECT': 'Subject',
            'SECTION': 'Section',
            'CUSTOMERNAME': 'CustomerName',
            'TASKASSIGNEDDT': 'TaskAssignedDt',
            'TASKCREATEDDT': 'TaskCreatedDt',
            'TASKRESOLVEDDT': 'TaskResolvedDt',
            'TICKETCREATEDDT': 'TicketCreatedDt',
            'TICKETRESOLVEDDT': 'TicketResolvedDt',
            'TICKETTOTALTIMESPENT': 'TicketTotalTimeSpent',
            'TASKMINUTESSPENT': 'TaskMinutesSpent',
            'TICKETTYPE': 'TicketType',
        }
        
        # Rename columns that exist
        rename_map = {k: v for k, v in column_mapping.items() if k in df.columns}
        df = df.rename(columns=rename_map)
        
        # Parse date columns
        date_cols = ['TaskAssignedDt', 'TaskCreatedDt', 'TaskResolvedDt', 
                    'TicketCreatedDt', 'TicketResolvedDt']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    def _apply_date_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply date-based filtering to exclude old closed tasks"""
        if df.empty or 'TaskCreatedDt' not in df.columns:
            return df
        
        def should_keep(row):
            task_created = row.get('TaskCreatedDt')
            status = str(row.get('TaskStatus', '')).strip()
            
            if pd.isna(task_created):
                return True
            if task_created >= IMPORT_THRESHOLD_DATE:
                return True
            if status in OPEN_TASK_STATUSES:
                return True
            return False
        
        return df[df.apply(should_keep, axis=1)].copy()
    
    def _load_dashboard_annotations(self) -> pd.DataFrame:
        """Load dashboard-owned field annotations from local CSV.
        
        Falls back to all_tasks.csv if annotations file doesn't exist (migration case).
        """
        # Try dedicated annotations file first
        if os.path.exists(self.annotations_path):
            try:
                df = pd.read_csv(self.annotations_path, dtype={'SprintsAssigned': str, 'TaskNum': str})
                for col in STRING_COLUMNS:
                    if col in df.columns:
                        df[col] = df[col].fillna('').astype(str).replace('nan', '')
                return df
            except Exception as e:
                print(f"TaskStore: Error loading annotations: {e}")
        
        # Fall back to all_tasks.csv for migration (extract dashboard fields)
        if os.path.exists(self.store_path):
            try:
                print("TaskStore: Migrating annotations from all_tasks.csv...")
                full_df = pd.read_csv(self.store_path, dtype={'SprintsAssigned': str, 'TaskNum': str})
                
                # Extract only dashboard-owned fields + TaskNum
                cols_to_keep = ['TaskNum'] + [c for c in DASHBOARD_OWNED_FIELDS if c in full_df.columns]
                if len(cols_to_keep) > 1:  # Has at least TaskNum + one annotation field
                    annotations_df = full_df[cols_to_keep].copy()
                    
                    # Clean string columns
                    for col in STRING_COLUMNS:
                        if col in annotations_df.columns:
                            annotations_df[col] = annotations_df[col].fillna('').astype(str).replace('nan', '')
                    
                    # Save to annotations file for future use
                    os.makedirs(os.path.dirname(self.annotations_path), exist_ok=True)
                    annotations_df.to_csv(self.annotations_path, index=False)
                    print(f"TaskStore: Migrated {len(annotations_df)} task annotations to {self.annotations_path}")
                    
                    return annotations_df
            except Exception as e:
                print(f"TaskStore: Error migrating annotations: {e}")
        
        return pd.DataFrame()
    
    def _ensure_dashboard_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure all dashboard-owned fields exist with defaults"""
        if 'SprintsAssigned' not in df.columns:
            df['SprintsAssigned'] = ''
        if 'GoalType' not in df.columns:
            df['GoalType'] = DEFAULT_GOAL_TYPE
        if 'CustomerPriority' not in df.columns:
            df['CustomerPriority'] = None
        if 'FinalPriority' not in df.columns:
            df['FinalPriority'] = None
        if 'HoursEstimated' not in df.columns:
            df['HoursEstimated'] = None
        if 'DependencyOn' not in df.columns:
            df['DependencyOn'] = ''
        if 'DependenciesLead' not in df.columns:
            df['DependenciesLead'] = ''
        if 'DependencySecured' not in df.columns:
            df['DependencySecured'] = ''
        if 'Comments' not in df.columns:
            df['Comments'] = ''
        if 'NonCompletionReason' not in df.columns:
            df['NonCompletionReason'] = ''
        
        # Convert string columns
        for col in STRING_COLUMNS:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str).replace('nan', '')
        
        return df
    
    def _load_from_csv(self) -> pd.DataFrame:
        """Load all tasks from CSV store (legacy mode)"""
        if not os.path.exists(self.store_path):
            return pd.DataFrame()
        
        try:
            # Read CSV with SprintsAssigned as string to preserve values
            df = pd.read_csv(self.store_path, dtype={'SprintsAssigned': str})
            
            # Convert all string columns at load time to avoid dtype issues later
            for col in STRING_COLUMNS:
                if col in df.columns:
                    df[col] = df[col].fillna('').astype(str).replace('nan', '')
            
            # Parse date columns
            date_cols = ['TaskAssignedDt', 'StatusUpdateDt', 'TicketCreatedDt', 
                        'TaskCreatedDt', 'TaskResolvedDt', 'TicketResolvedDt']
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # Migration: Ensure SprintsAssigned column exists
            if 'SprintsAssigned' not in df.columns:
                if 'AssignedSprintNumber' in df.columns:
                    # Convert single sprint number to comma-separated string
                    df['SprintsAssigned'] = df['AssignedSprintNumber'].apply(
                        lambda x: str(int(x)) if pd.notna(x) else ''
                    )
                else:
                    # No automatic assignment - all tasks start with empty sprints
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
        """Save task store (mode-dependent)"""
        if self.use_sqlite:
            return save_tasks(None, self.tasks_df)
        if self.use_snowflake:
            return self._save_annotations()
        else:
            return self._save_csv()
    
    def _save_csv(self) -> bool:
        """Save full task store to CSV (legacy mode)"""
        try:
            os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
            
            if 'SprintsAssigned' in self.tasks_df.columns:
                self.tasks_df['SprintsAssigned'] = self.tasks_df['SprintsAssigned'].fillna('').astype(str)
                self.tasks_df['SprintsAssigned'] = self.tasks_df['SprintsAssigned'].replace('nan', '')
            
            self.tasks_df.to_csv(self.store_path, index=False)
            print(f"TaskStore: Saved {len(self.tasks_df)} tasks to {self.store_path}")
            return True
        except Exception as e:
            print(f"Error saving task store: {e}")
            return False
    
    def _save_annotations(self) -> bool:
        """Save only dashboard annotations to local CSV (Snowflake mode)"""
        try:
            os.makedirs(os.path.dirname(self.annotations_path), exist_ok=True)
            
            # Extract only dashboard-owned fields + TaskNum as key
            annotation_cols = ['TaskNum'] + [f for f in DASHBOARD_OWNED_FIELDS if f in self.tasks_df.columns]
            annotations_df = self.tasks_df[annotation_cols].copy()
            
            # Clean string columns
            if 'SprintsAssigned' in annotations_df.columns:
                annotations_df['SprintsAssigned'] = annotations_df['SprintsAssigned'].fillna('').astype(str)
                annotations_df['SprintsAssigned'] = annotations_df['SprintsAssigned'].replace('nan', '')
            
            annotations_df.to_csv(self.annotations_path, index=False)
            print(f"TaskStore: Saved annotations for {len(annotations_df)} tasks to {self.annotations_path}")
            return True
        except Exception as e:
            print(f"Error saving annotations: {e}")
            return False
    
    def reload(self) -> None:
        """Reload task store from data source"""
        if self.use_snowflake:
            # Clear Snowflake cache to get fresh data
            from modules.snowflake_connector import clear_snowflake_cache
            clear_snowflake_cache()
        self.tasks_df = self._load_store()
    
    def update_tasks(self, updates: List[Dict]) -> Tuple[int, List[str]]:
        """
        Update multiple tasks with validation and type conversion.
        Centralized method for all editable field updates.
        
        Args:
            updates: List of dicts with 'TaskNum' and field:value pairs
                     e.g., [{'TaskNum': '123', 'GoalType': 'Mandatory', 'DependencyOn': 'Yes'}]
        
        Returns:
            Tuple of (success_count, error_messages)
        """
        success = 0
        errors = []
        
        for update in updates:
            task_num = update.get('TaskNum')
            if not task_num or pd.isna(task_num):
                continue
            
            mask = self.tasks_df['TaskNum'].astype(str) == str(task_num)
            
            if not mask.any():
                errors.append(f"Task {task_num} not found")
                continue
            
            try:
                for field, value in update.items():
                    if field == 'TaskNum':
                        continue
                    if field not in EDITABLE_FIELDS:
                        continue
                    
                    # Type-safe conversion
                    clean_value = self._convert_field_value(field, value)
                    self.tasks_df.loc[mask, field] = clean_value
                
                success += 1
            except Exception as e:
                errors.append(f"Task {task_num}: {str(e)}")
        
        # Save if any updates succeeded
        if success > 0:
            self.save()
        
        return success, errors
    
    def _convert_field_value(self, field: str, value) -> any:
        """
        Convert a value to the correct type for a field.
        Handles None, NaN, 'nan', 'None' strings consistently.
        """
        field_def = EDITABLE_FIELDS.get(field, {})
        field_type = field_def.get('type', 'str')
        
        # Handle empty/null values
        if value is None or pd.isna(value):
            return '' if field_type == 'str' else None
        
        str_value = str(value).strip()
        if str_value.lower() in ('nan', 'none', ''):
            return '' if field_type == 'str' else None
        
        # Type conversion
        if field_type == 'int':
            try:
                return int(float(str_value))
            except (ValueError, TypeError):
                return None
        elif field_type == 'float':
            try:
                return float(str_value)
            except (ValueError, TypeError):
                return None
        
        return str_value
    
    def import_tasks(self, itrack_df: pd.DataFrame, mapped_df: pd.DataFrame) -> Dict:
        """
        Import tasks from iTrack extract using Field Ownership Model.
        
        - TaskNum is the unique identifier for each task
        - iTrack-owned fields are ALWAYS updated from imports
        - Dashboard-owned fields are NEVER overwritten by imports
        - New tasks get default values for dashboard fields
        
        Args:
            itrack_df: Raw iTrack DataFrame (unused, kept for compatibility)
            mapped_df: DataFrame after column mapping to sprint schema
        
        Returns:
            Dict with import statistics
        """
        stats = {
            'total_imported': 0,
            'new_tasks': 0,
            'updated_tasks': 0,
            'unchanged_tasks': 0,
            'sprints_affected': set(),
            # Detailed breakdowns
            'new_tasks_by_status': {},        # {status: count}
            'task_status_changes': [],        # [{task_num, old_status, new_status}]
            'ticket_status_changes': [],      # [{task_num, old_status, new_status}]
            'field_changes': {}               # {field_name: count}
        }
        
        if mapped_df.empty:
            return stats
        
        # Ensure TaskAssignedDt is datetime
        if 'TaskAssignedDt' in mapped_df.columns:
            mapped_df['TaskAssignedDt'] = pd.to_datetime(
                mapped_df['TaskAssignedDt'], errors='coerce'
            )
        
        # Ensure TaskCreatedDt is datetime for filtering
        if 'TaskCreatedDt' in mapped_df.columns:
            mapped_df['TaskCreatedDt'] = pd.to_datetime(
                mapped_df['TaskCreatedDt'], errors='coerce'
            )
        
        # =============================================================
        # DATE-BASED IMPORT FILTER
        # - Tasks created ON or AFTER threshold: import ALL statuses
        # - Tasks created BEFORE threshold: only import OPEN statuses
        # =============================================================
        stats['skipped_old_closed'] = 0
        
        def should_import_task(row):
            """Check if task should be imported based on date and status"""
            task_created = row.get('TaskCreatedDt')
            status = str(row.get('TaskStatus', '')).strip()
            
            # If no creation date, import the task (safe default)
            if pd.isna(task_created):
                return True
            
            # Tasks created on/after threshold: import everything
            if task_created >= IMPORT_THRESHOLD_DATE:
                return True
            
            # Tasks created before threshold: only import if status is open
            if status in OPEN_TASK_STATUSES:
                return True
            
            # Exclude closed/cancelled tasks created before threshold
            return False
        
        # Apply filter and track skipped count
        original_count = len(mapped_df)
        import_mask = mapped_df.apply(should_import_task, axis=1)
        stats['skipped_old_closed'] = original_count - import_mask.sum()
        mapped_df = mapped_df[import_mask].copy()
        
        # Get existing TaskNums for quick lookup
        existing_task_nums = set()
        if not self.tasks_df.empty and 'TaskNum' in self.tasks_df.columns:
            existing_task_nums = set(self.tasks_df['TaskNum'].dropna().astype(str).tolist())
        
        # Process each task from import
        for idx, row in mapped_df.iterrows():
            task_num = row.get('TaskNum')
            
            if pd.isna(task_num):
                continue
            
            task_num_str = str(task_num)
            
            # NOTE: OriginalSprintNumber is no longer computed or used
            # All sprint assignments are done manually via Work Backlogs
            
            if task_num_str in existing_task_nums:
                # =============================================================
                # EXISTING TASK: Update only iTrack-owned fields
                # =============================================================
                mask = self.tasks_df['TaskNum'].astype(str) == task_num_str
                
                # Update iTrack-owned fields (except TaskNum which is the key)
                fields_updated = False
                for field in ITRACK_OWNED_FIELDS:
                    if field == 'TaskNum':  # Skip the key field
                        continue
                    if field in row.index and field in self.tasks_df.columns:
                        old_value = self.tasks_df.loc[mask, field].iloc[0]
                        new_value = row[field]
                        # Only update if value has changed and new value is not null
                        if pd.notna(new_value) and str(old_value) != str(new_value):
                            self.tasks_df.loc[mask, field] = new_value
                            fields_updated = True
                            
                            # Track field change count
                            stats['field_changes'][field] = stats['field_changes'].get(field, 0) + 1
                            
                            # Track Task Status changes specifically
                            if field == 'Status':
                                old_status = str(old_value) if pd.notna(old_value) else 'Unknown'
                                new_status = str(new_value)
                                stats['task_status_changes'].append({
                                    'task_num': task_num_str,
                                    'old_status': old_status,
                                    'new_status': new_status
                                })
                            
                            # Track Ticket Status changes specifically
                            if field == 'TicketStatus':
                                old_status = str(old_value) if pd.notna(old_value) else 'Unknown'
                                new_status = str(new_value)
                                stats['ticket_status_changes'].append({
                                    'task_num': task_num_str,
                                    'old_status': old_status,
                                    'new_status': new_status
                                })
                
                if fields_updated:
                    stats['updated_tasks'] += 1
                else:
                    stats['unchanged_tasks'] += 1
                
                # NOTE: Dashboard-owned fields are NOT touched:
                # SprintsAssigned, CustomerPriority, FinalPriority, GoalType,
                # HoursEstimated, DependencyOn, DependenciesLead, DependencySecured,
                # Comments, StatusUpdateDt - all preserved!
                
            else:
                # =============================================================
                # NEW TASK: Initialize with defaults for dashboard fields
                # =============================================================
                new_task = row.copy()
                
                # Initialize dashboard-owned fields with defaults
                # NO AUTO-ASSIGNMENT: All new tasks go to backlog, sprints assigned via Work Backlogs
                new_task['SprintsAssigned'] = ''
                
                status = row.get('TaskStatus', '')
                if status in CLOSED_STATUSES:
                    resolved_dt = row.get('TaskResolvedDt') or row.get('TicketResolvedDt')
                    new_task['StatusUpdateDt'] = resolved_dt if pd.notna(resolved_dt) else datetime.now()
                else:
                    new_task['StatusUpdateDt'] = None
                
                # Set other dashboard field defaults
                new_task['CustomerPriority'] = None
                new_task['FinalPriority'] = None
                new_task['GoalType'] = DEFAULT_GOAL_TYPE
                new_task['HoursEstimated'] = None
                new_task['DependencyOn'] = None
                new_task['DependenciesLead'] = None
                new_task['DependencySecured'] = None
                new_task['Comments'] = None
                new_task['NonCompletionReason'] = None
                
                # Add to store
                if self.tasks_df.empty:
                    self.tasks_df = pd.DataFrame([new_task])
                else:
                    self.tasks_df = pd.concat([self.tasks_df, new_task.to_frame().T], ignore_index=True)
                
                stats['new_tasks'] += 1
                existing_task_nums.add(task_num_str)  # Track for duplicates in same import
                
                # Track new tasks by status
                task_status = str(status) if status else 'Unknown'
                stats['new_tasks_by_status'][task_status] = stats['new_tasks_by_status'].get(task_status, 0) + 1
            
            stats['total_imported'] += 1
        
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
        
        # TaskOrigin is now always 'Assigned' since all assignments are manual
        if not result.empty:
            result['TaskOrigin'] = 'Assigned'
        
        # Add sprint metadata
        if not result.empty:
            result['SprintNumber'] = sprint_number
            result['SprintName'] = sprint_info['SprintName']
            result['SprintStartDt'] = sprint_info['SprintStartDt']
            result['SprintEndDt'] = sprint_info['SprintEndDt']
            
            # Calculate DaysOpen (days since task was assigned)
            result = self._calculate_days_open(result)
            
            # Calculate hours from worklog (total hours, not sprint-specific)
            result = self._calculate_hours_from_worklog(result, sprint_number=None)
            
            # Filter by valid team members
            result = filter_by_team_members(result, 'AssignedTo')
            
            # Apply name mapping for display names
            result = apply_name_mapping(result, 'AssignedTo')
            
            # Format SprintsAssigned for display (e.g., "1, 2" -> "26-1, 26-2")
            if 'SprintsAssigned' in result.columns:
                result['SprintsAssigned'] = result['SprintsAssigned'].apply(format_sprints_assigned_display)
        
        return result
    
    def _calculate_days_open(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate DaysOpen for all tasks based on Task Assigned Date.
        
        Uses TaskAssignedDt as primary, falls back to TaskCreatedDt if not available.
        DaysOpen is clamped to minimum 0 to handle timezone differences.
        """
        if df.empty:
            return df
        
        today = datetime.now()
        
        if 'TaskAssignedDt' in df.columns:
            df['TaskAssignedDt'] = pd.to_datetime(df['TaskAssignedDt'], errors='coerce')
            df['DaysOpen'] = df['TaskAssignedDt'].apply(
                lambda x: max(0, (today - x).days) if pd.notna(x) else 0
            )
        elif 'TaskCreatedDt' in df.columns:
            df['TaskCreatedDt'] = pd.to_datetime(df['TaskCreatedDt'], errors='coerce')
            df['DaysOpen'] = df['TaskCreatedDt'].apply(
                lambda x: max(0, (today - x).days) if pd.notna(x) else 0
            )
        else:
            df['DaysOpen'] = 0
        
        return df
    
    def _calculate_hours_from_worklog(self, df: pd.DataFrame, sprint_number: int = None) -> pd.DataFrame:
        """
        Calculate TaskHoursSpent and TicketHoursSpent from worklog entries.
        
        Args:
            df: DataFrame of tasks
            sprint_number: If provided, only count hours logged during this sprint.
                          If None, count all hours (total).
        
        Returns:
            DataFrame with updated TaskHoursSpent and TicketHoursSpent columns
        """
        if df.empty:
            return df
        
        worklog_store = get_worklog_store()
        
        # Get task hours from worklog
        task_hours = worklog_store.get_task_hours_spent(sprint_number)
        
        # Build task-to-ticket mapping
        task_to_ticket = {}
        if 'TaskNum' in df.columns and 'TicketNum' in df.columns:
            task_to_ticket = dict(zip(df['TaskNum'].astype(str), df['TicketNum'].astype(str)))
        
        # Get ticket hours from worklog
        ticket_hours = worklog_store.get_ticket_hours_spent(task_to_ticket, sprint_number)
        
        # Apply task hours (rounded to 2 decimal places)
        df['TaskHoursSpent'] = df['TaskNum'].astype(str).map(task_hours).fillna(0.0).round(2)
        
        # Apply ticket hours (rounded to 2 decimal places)
        df['TicketHoursSpent'] = df['TicketNum'].astype(str).map(ticket_hours).fillna(0.0).round(2)
        
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
        task_num: str, 
        new_status: str, 
        status_update_dt: datetime
    ) -> bool:
        """
        Update a task's status with a specific update date.
        
        Args:
            task_num: The TaskNum of the task
            new_status: New status (e.g., 'Closed', 'Canceled')
            status_update_dt: Date when status change takes effect
        
        Returns:
            True if successful
        """
        if self.tasks_df.empty:
            return False
        
        mask = self.tasks_df['TaskNum'].astype(str) == str(task_num)
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
    
    def update_task(self, task_num: str, updates: dict) -> bool:
        """
        Update a task with the given field updates.
        
        Args:
            task_num: The TaskNum of the task to update
            updates: Dictionary of field names and their new values
        
        Returns:
            True if successful, False otherwise
        """
        if self.tasks_df.empty or not updates:
            print(f"update_task: Empty df or no updates - df empty: {self.tasks_df.empty}, updates: {updates}")
            return False
        
        # Handle both int and string TaskNum
        task_num_str = str(task_num).strip()
        mask = self.tasks_df['TaskNum'].astype(str).str.strip() == task_num_str
        if not mask.any():
            print(f"update_task: TaskNum {task_num_str} not found in tasks_df")
            return False
        
        # Apply updates
        for field, value in updates.items():
            if field in self.tasks_df.columns:
                self.tasks_df.loc[mask, field] = value
                print(f"update_task: Updated {field} = {value} for TaskNum {task_num_str}")
        
        result = self.save()
        print(f"update_task: Save result = {result}")
        return result
    
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
            ~self.tasks_df['TaskStatus'].isin(CLOSED_STATUSES)
        ].copy()
        
        if not backlog_tasks.empty:
            # Calculate DaysOpen
            backlog_tasks = self._calculate_days_open(backlog_tasks)
            
            # Calculate hours from worklog (total - no sprint filter)
            backlog_tasks = self._calculate_hours_from_worklog(backlog_tasks, sprint_number=None)
            
            # Filter by valid team members
            backlog_tasks = filter_by_team_members(backlog_tasks, 'AssignedTo')
            
            # Apply name mapping for display names
            backlog_tasks = apply_name_mapping(backlog_tasks, 'AssignedTo')
            
            # Format SprintsAssigned for display (e.g., "1, 2" -> "26-1, 26-2")
            if 'SprintsAssigned' in backlog_tasks.columns:
                backlog_tasks['SprintsAssigned'] = backlog_tasks['SprintsAssigned'].apply(format_sprints_assigned_display)
        
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
    
    def _remove_sprint_from_list(self, current_sprints: str, sprint_number: int) -> str:
        """Remove a sprint number from the SprintsAssigned comma-separated list"""
        if pd.isna(current_sprints) or current_sprints == '':
            return ''
        
        try:
            sprint_list = [int(s.strip()) for s in str(current_sprints).split(',') if s.strip()]
            if sprint_number in sprint_list:
                sprint_list.remove(sprint_number)
            return ', '.join(map(str, sorted(sprint_list))) if sprint_list else ''
        except:
            return ''
    
    def remove_task_from_sprint(self, task_num: str, sprint_number: int) -> Tuple[bool, str]:
        """
        Remove a sprint from a task's SprintsAssigned list.
        
        Example: Task assigned to "1, 2" → remove sprint 1 → becomes "2"
        If task was only in sprint 1, SprintsAssigned becomes empty (true backlog).
        
        Args:
            task_num: The TaskNum of the task
            sprint_number: Sprint number to remove from SprintsAssigned
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if self.tasks_df.empty:
            return False, "Task store is empty"
        
        mask = self.tasks_df['TaskNum'].astype(str) == str(task_num)
        if not mask.any():
            return False, f"Task {task_num} not found"
        
        current_sprints = self.tasks_df.loc[mask, 'SprintsAssigned'].iloc[0]
        if not self._sprint_in_list(current_sprints, sprint_number):
            return False, f"Task {task_num} not in Sprint {sprint_number}"
        
        new_sprints = self._remove_sprint_from_list(current_sprints, sprint_number)
        self.tasks_df.loc[mask, 'SprintsAssigned'] = new_sprints
        self.save()
        return True, f"Removed Sprint {sprint_number} from task {task_num}"
    
    def assign_task_to_sprint(self, task_num: str, sprint_number: int) -> Tuple[bool, str]:
        """
        Add a sprint assignment to a task (appends to SprintsAssigned list).
        
        Args:
            task_num: The TaskNum of the task
            sprint_number: Sprint number to assign to
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if self.tasks_df.empty:
            return False, "Task store is empty"
        
        mask = self.tasks_df['TaskNum'].astype(str) == str(task_num)
        if not mask.any():
            return False, f"Task {task_num} not found"
        
        # Get sprint info to validate
        sprint_info = self.calendar.get_sprint_by_number(sprint_number)
        if not sprint_info:
            return False, f"Sprint {sprint_number} not found"
        
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
    
    def assign_tasks_to_sprint(self, task_nums: List[str], sprint_number: int) -> Tuple[int, int, List[str]]:
        """
        Add sprint assignment to multiple tasks (appends to SprintsAssigned list).
        
        Args:
            task_nums: List of TaskNums
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
        
        for task_num in task_nums:
            mask = self.tasks_df['TaskNum'].astype(str) == str(task_num)
            if mask.any():
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
        result = self.tasks_df.copy()
        # Format SprintsAssigned for display (e.g., "1, 2" -> "26-1, 26-2")
        if not result.empty and 'SprintsAssigned' in result.columns:
            result['SprintsAssigned'] = result['SprintsAssigned'].apply(format_sprints_assigned_display)
        return result
    
    def get_task_history(self, task_num: str) -> pd.DataFrame:
        """
        Get a task by its TaskNum.
        
        Args:
            task_num: TaskNum (primary identifier)
        
        Returns:
            DataFrame with task data
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
            
            none_hours = assignee_tasks[
                (assignee_tasks['GoalType'] == 'None') | (assignee_tasks['GoalType'].isna()) | (assignee_tasks['GoalType'] == '')
            ]['HoursEstimated'].fillna(0).sum()
            
            total_hours = mandatory_hours + stretch_hours + none_hours
            
            summary_data.append({
                'AssignedTo': assignee,
                'NoneHours': none_hours,
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
    
    def cleanup_old_closed_tasks(self) -> Dict:
        """
        Retroactively remove closed/cancelled tasks created before the threshold date.
        
        This applies the same logic as import filtering to the existing store:
        - Tasks created ON or AFTER threshold: keep all statuses
        - Tasks created BEFORE threshold: only keep OPEN statuses
        
        Returns:
            Dict with cleanup statistics
        """
        stats = {
            'total_before': len(self.tasks_df),
            'removed': 0,
            'kept': 0,
            'removed_by_status': {}
        }
        
        if self.tasks_df.empty:
            return stats
        
        # Ensure TaskCreatedDt is datetime
        if 'TaskCreatedDt' in self.tasks_df.columns:
            self.tasks_df['TaskCreatedDt'] = pd.to_datetime(
                self.tasks_df['TaskCreatedDt'], errors='coerce'
            )
        
        def should_keep_task(row):
            """Check if task should be kept based on date and status"""
            task_created = row.get('TaskCreatedDt')
            status = str(row.get('TaskStatus', '')).strip()
            
            # If no creation date, keep the task (safe default)
            if pd.isna(task_created):
                return True
            
            # Tasks created on/after threshold: keep everything
            if task_created >= IMPORT_THRESHOLD_DATE:
                return True
            
            # Tasks created before threshold: only keep if status is open
            if status in OPEN_TASK_STATUSES:
                return True
            
            # Remove closed/cancelled tasks created before threshold
            return False
        
        # Track what we're removing
        for idx, row in self.tasks_df.iterrows():
            if not should_keep_task(row):
                status = str(row.get('TaskStatus', 'Unknown'))
                stats['removed_by_status'][status] = stats['removed_by_status'].get(status, 0) + 1
        
        # Apply filter
        keep_mask = self.tasks_df.apply(should_keep_task, axis=1)
        stats['removed'] = (~keep_mask).sum()
        stats['kept'] = keep_mask.sum()
        
        self.tasks_df = self.tasks_df[keep_mask].copy()
        
        return stats


# Singleton instance
_store_instance = None

def get_task_store() -> TaskStore:
    """Get the singleton task store instance"""
    global _store_instance
    if _store_instance is None:
        _store_instance = TaskStore()
    return _store_instance


def reset_task_store() -> None:
    """Reset the task store singleton to force reload from data source"""
    global _store_instance
    _store_instance = None
