"""
Data loading and CSV processing utilities
"""
import pandas as pd
import os
from typing import Optional, Tuple, Dict
from datetime import datetime
try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Python < 3.11

from utils.constants import (
    CURRENT_SPRINT_FILE,
    PAST_SPRINTS_FILE
)
from utils.date_utils import parse_date_flexible
from models.validation import validate_itrack_csv, validate_sprint_csv


class DataLoader:
    """Handle all data loading and CSV operations"""
    
    def __init__(self, data_dir: str = None, config_path: str = None):
        # Get the project root directory (parent of modules/)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Use absolute paths
        if data_dir is None:
            data_dir = os.path.join(project_root, "data")
        self.data_dir = data_dir
        
        if config_path is None:
            config_path = os.path.join(project_root, ".streamlit", "itrack_mapping.toml")
        
        self.current_sprint_path = os.path.join(data_dir, "current_sprint.csv")
        self.past_sprints_path = os.path.join(data_dir, "past_sprints.csv")
        self.config = self._load_config(config_path)
    
    def _load_config(self, config_path: str) -> Dict:
        """Load iTrack mapping configuration from TOML file"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'rb') as f:
            return tomllib.load(f)
    
    def load_itrack_extract(self, file_path: Optional[str] = None, uploaded_file=None) -> Tuple[pd.DataFrame, bool, list]:
        """
        Load and validate iTrack extract CSV using standard format from configuration
        
        Args:
            file_path: Path to CSV file
            uploaded_file: Streamlit UploadedFile object
        
        Returns:
            Tuple of (DataFrame, is_valid, errors)
        """
        try:
            # Get format settings from config
            encoding = self.config['file_format']['encoding']
            delimiter = self.config['file_format']['delimiter']
            
            # Load CSV with standard format
            if uploaded_file is not None:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=delimiter, encoding=encoding)
            elif file_path:
                df = pd.read_csv(file_path, sep=delimiter, encoding=encoding)
            else:
                return pd.DataFrame(), False, ["No file provided"]
            
            if df.empty:
                return pd.DataFrame(), False, ["CSV file is empty"]
            
            # Apply column mapping from config
            try:
                df = self._apply_column_mapping(df)
            except Exception as e:
                return pd.DataFrame(), False, [f"Error applying column mapping: {str(e)}"]
            
            # Validate required columns
            try:
                is_valid, errors = self._validate_required_columns(df)
                if not is_valid:
                    return df, False, errors
            except Exception as e:
                return pd.DataFrame(), False, [f"Error validating columns: {str(e)}"]
            
            # Apply default values
            try:
                df = self._apply_defaults(df)
            except Exception as e:
                return pd.DataFrame(), False, [f"Error applying defaults: {str(e)}"]
            
            # Validate with standard validation
            try:
                is_valid, errors = validate_itrack_csv(df)
                if not is_valid:
                    return df, False, errors
            except Exception as e:
                return pd.DataFrame(), False, [f"Error in validation: {str(e)}"]
            
            # Parse dates
            try:
                df = self._parse_itrack_dates(df)
            except Exception as e:
                return pd.DataFrame(), False, [f"Error parsing dates: {str(e)}"]
            
            return df, True, []
        
        except Exception as e:
            import traceback
            return pd.DataFrame(), False, [f"Error loading file: {str(e)}\n{traceback.format_exc()}"]
    
    def load_current_sprint(self, include_completed: bool = False) -> Optional[pd.DataFrame]:
        """
        Load current sprint CSV, excluding completed tasks by default
        
        Args:
            include_completed: If True, include completed tasks. Default False.
        
        Returns:
            DataFrame or None if file doesn't exist or is empty
        """
        if not os.path.exists(self.current_sprint_path):
            return None
        
        # Check if file is empty
        if os.path.getsize(self.current_sprint_path) == 0:
            return None
        
        try:
            df = pd.read_csv(self.current_sprint_path)
            # Check if DataFrame is empty after reading
            if df.empty or len(df.columns) == 0:
                return None
            df = self._parse_sprint_dates(df)
            
            # Filter out completed tasks unless explicitly requested
            if not include_completed and 'Status' in df.columns:
                # Exclude tasks with status 'Completed' or 'Closed'
                completed_statuses = ['Completed', 'Closed', 'Done', 'Resolved']
                df = df[~df['Status'].isin(completed_statuses)]
                
                # If all tasks were completed, return None
                if df.empty:
                    return None
            
            return df
        except Exception as e:
            # Silently return None for empty or invalid files
            return None
    
    def load_past_sprints(self) -> Optional[pd.DataFrame]:
        """
        Load past sprints archive
        
        Returns:
            DataFrame or None if file doesn't exist or is empty
        """
        if not os.path.exists(self.past_sprints_path):
            return None
        
        # Check if file is empty
        if os.path.getsize(self.past_sprints_path) == 0:
            return None
        
        try:
            df = pd.read_csv(self.past_sprints_path)
            # Check if DataFrame is empty after reading
            if df.empty or len(df.columns) == 0:
                return None
            df = self._parse_sprint_dates(df)
            return df
        except Exception as e:
            # Silently return None for empty or invalid files
            return None
    
    def save_current_sprint(self, df: pd.DataFrame) -> bool:
        """
        Save current sprint to CSV
        
        Args:
            df: Sprint DataFrame
        
        Returns:
            True if successful
        """
        try:
            # Ensure directory exists
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Save
            df.to_csv(self.current_sprint_path, index=False)
            return True
        except Exception as e:
            print(f"Error saving current sprint: {e}")
            return False
    
    def save_past_sprints(self, df: pd.DataFrame) -> bool:
        """
        Save past sprints archive
        
        Args:
            df: Past sprints DataFrame
        
        Returns:
            True if successful
        """
        try:
            # Ensure directory exists
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Save
            df.to_csv(self.past_sprints_path, index=False)
            return True
        except Exception as e:
            print(f"Error saving past sprints: {e}")
            return False
    
    def archive_current_sprint(self) -> bool:
        """
        Archive current sprint to past sprints (includes ALL tasks, even completed)
        
        Returns:
            True if successful
        """
        # Load current sprint WITH completed tasks for archiving
        current = self.load_current_sprint(include_completed=True)
        
        if current is None or len(current) == 0:
            return True  # Nothing to archive
        
        # Load existing past sprints
        past = self.load_past_sprints()
        
        if past is None:
            # Create new archive
            combined = current
        else:
            # Append to existing
            combined = pd.concat([past, current], ignore_index=True)
        
        # Save combined archive
        return self.save_past_sprints(combined)
    
    def _apply_column_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply column mapping from config file
        Maps iTrack column names to internal column names
        """
        column_mapping = self.config['column_mapping']
        
        # Create rename map for columns that exist
        rename_map = {}
        for itrack_col, internal_col in column_mapping.items():
            if itrack_col in df.columns:
                rename_map[itrack_col] = internal_col
        
        # Apply the mapping
        df = df.rename(columns=rename_map)
        
        return df
    
    def _validate_required_columns(self, df: pd.DataFrame) -> Tuple[bool, list]:
        """
        Validate that all required columns from config are present
        """
        required_cols_original = self.config['validation']['required_columns']
        column_mapping = self.config['column_mapping']
        
        # Map required columns to their internal names
        required_cols_internal = []
        for col in required_cols_original:
            if col in column_mapping:
                required_cols_internal.append(column_mapping[col])
            else:
                required_cols_internal.append(col)
        
        # Check which columns are missing
        missing_cols = [col for col in required_cols_internal if col not in df.columns]
        
        if missing_cols:
            return False, [f"Missing required columns after mapping: {', '.join(missing_cols)}"]
        
        return True, []
    
    def _apply_defaults(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply default values from config for missing or empty columns
        """
        defaults = self.config['default_values']
        
        for col, default_value in defaults.items():
            if col not in df.columns:
                # Add column with default value
                df[col] = default_value
            else:
                # Fill empty/null values with default
                df[col] = df[col].fillna(default_value)
                # Handle 'nan' strings
                if df[col].dtype == 'object':
                    df[col] = df[col].replace('nan', default_value)
                    df[col] = df[col].replace('', default_value)
                    # Strip whitespace for string columns
                    df[col] = df[col].astype(str).str.strip()
                    # Replace empty after strip
                    df[col] = df[col].replace('', default_value)
        
        return df
    
    def _parse_itrack_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse date columns in iTrack extract"""
        # Support both old and new format date columns
        date_columns = [
            'Task Assigned Date', 
            'Task Created Date',
            'Task Resolved Date',
            'Ticket Created Date',
            'Ticket Resolved Date',
            'Created On', 
            'Created Inc', 
            'Created SR', 
            'Day of Ticket_Createddatetime', 
            'Day of Task_Created_DateTime'
        ]
        
        for col in date_columns:
            if col in df.columns:
                # Handle various date formats from iTrack
                df[col] = pd.to_datetime(df[col], errors='coerce', format='mixed')
        
        return df
    
    def _parse_sprint_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse date columns in sprint files"""
        date_columns = [
            'SprintStartDt',
            'SprintEndDt',
            'TaskAssignedDt',
            'TaskCreatedDt',
            'TaskResolvedDt',
            'TicketCreatedDt',
            'TicketResolvedDt'
        ]
        
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce', format='mixed')
        
        return df
    
    def map_itrack_to_sprint(self, itrack_df: pd.DataFrame) -> pd.DataFrame:
        """
        Map iTrack columns to sprint schema using configuration
        
        Args:
            itrack_df: iTrack extract DataFrame (already has internal column names)
        
        Returns:
            DataFrame with sprint column names
        """
        # Get sprint schema mapping from config
        sprint_mapping = self.config['sprint_schema_mapping']
        
        # Rename columns to sprint schema
        sprint_df = itrack_df.rename(columns=sprint_mapping)
        
        # Merge Created dates (Inc vs SR) - only if direct TicketCreatedDt doesn't exist
        if 'TicketCreatedDt_Inc' in sprint_df.columns and 'TicketCreatedDt' not in sprint_df.columns:
            sprint_df['TicketCreatedDt'] = sprint_df['TicketCreatedDt_Inc'].fillna(
                sprint_df.get('TicketCreatedDt_SR', pd.Series())
            )
        
        # Merge Customer names
        if 'CustomerName_Inc' in sprint_df.columns:
            sprint_df['CustomerName'] = sprint_df['CustomerName_Inc'].fillna(
                sprint_df.get('CustomerName_SR', pd.Series())
            )
        
        # Extract ticket type from subject
        sprint_df['TicketType'] = sprint_df['Subject'].apply(self._extract_ticket_type)
        
        # Initialize planning columns
        sprint_df['HoursEstimated'] = None
        sprint_df['GoalType'] = ''  # Default to blank, not 'n'
        sprint_df['DependencyOn'] = None
        sprint_df['DependenciesLead'] = None
        sprint_df['DependencySecured'] = None
        sprint_df['Comments'] = None
        
        # Select and order columns from config (only those that exist)
        column_order = self.config.get('sprint_columns', {}).get('column_order', [])
        if not column_order:
            # Fallback to all columns if config not defined
            available_columns = list(sprint_df.columns)
        else:
            available_columns = [col for col in column_order if col in sprint_df.columns]
        
        sprint_df = sprint_df[available_columns]
        
        return sprint_df
    
    def _extract_ticket_type(self, subject: str) -> str:
        """Extract ticket type from subject line"""
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
        
        return "NC"
    
    def get_last_sprint_number(self) -> int:
        """
        Get the most recent sprint number
        
        Returns:
            Last sprint number, or 0 if no sprints exist
        """
        # Include completed tasks to get accurate sprint number
        current = self.load_current_sprint(include_completed=True)
        
        if current is not None and len(current) > 0:
            return int(current['SprintNumber'].iloc[0])
        
        past = self.load_past_sprints()
        
        if past is not None and len(past) > 0:
            return int(past['SprintNumber'].max())
        
        return 0
