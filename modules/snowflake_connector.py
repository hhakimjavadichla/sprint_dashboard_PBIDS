"""
Snowflake Connector Module
Handles connection to Snowflake database for reading iTrack task data.

Configuration is stored in .streamlit/secrets.toml under [snowflake] section.
Column mappings are stored in .streamlit/itrack_mapping.toml.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Dict
from pathlib import Path
import logging
import toml

logger = logging.getLogger(__name__)

# Path to config file
CONFIG_FILE = Path(__file__).parent.parent / ".streamlit" / "itrack_mapping.toml"


def load_snowflake_column_mappings() -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Load Snowflake column mappings from config file.
    
    Returns:
        Tuple of (task_mapping, worklog_mapping) dictionaries
        Each maps SNOWFLAKE_COLUMN -> AppColumnName
    """
    try:
        config = toml.load(CONFIG_FILE)
        task_mapping = config.get("snowflake_task_mapping", {})
        worklog_mapping = config.get("snowflake_worklog_mapping", {})
        return task_mapping, worklog_mapping
    except Exception as e:
        logger.error(f"Error loading Snowflake column mappings: {e}")
        return {}, {}

# Cache TTL: None = no auto-refresh (on-demand only)
# Set to a number (e.g., 3600) for automatic refresh every N seconds
CACHE_TTL_SECONDS = None


def get_snowflake_config() -> Dict:
    """
    Get Snowflake configuration from Streamlit secrets.
    
    Returns:
        Dict with Snowflake connection parameters
    """
    if "snowflake" not in st.secrets:
        return {}
    
    config = dict(st.secrets["snowflake"])
    return config


def is_snowflake_enabled() -> bool:
    """Check if Snowflake data loading is enabled in config."""
    config = get_snowflake_config()
    # Must explicitly set enabled = true to use Snowflake for data loading
    return config.get("enabled", False) == True


def is_snowflake_configured() -> bool:
    """Check if Snowflake connection is configured in secrets."""
    config = get_snowflake_config()
    # Must have either 'url' or 'account', plus user, password, database, schema
    has_connection = config.get("url") or config.get("account")
    required_keys = ["user", "password", "database", "schema"]
    has_required = all(key in config and config[key] for key in required_keys)
    return has_connection and has_required


def extract_account_from_url(url: str) -> str:
    """
    Extract account identifier from Snowflake URL.
    
    URL formats:
    - https://xyz12345.us-east-1.snowflakecomputing.com
    - xyz12345.us-east-1.snowflakecomputing.com
    - https://orgname-accountname.snowflakecomputing.com
    
    Returns the account identifier (e.g., xyz12345.us-east-1)
    """
    # Remove protocol if present
    url = url.replace("https://", "").replace("http://", "")
    # Remove trailing slashes and paths
    url = url.split("/")[0]
    # Remove .snowflakecomputing.com suffix
    if ".snowflakecomputing.com" in url:
        url = url.replace(".snowflakecomputing.com", "")
    return url


def get_snowflake_connection():
    """
    Create and return a Snowflake connection.
    
    Supports two configuration modes:
    1. URL-based: Provide 'url' and account is extracted automatically
    2. Account-based: Provide 'account' directly
    
    Returns:
        Snowflake connection object or None if not configured
    """
    if not is_snowflake_configured():
        return None
    
    try:
        import snowflake.connector
        
        config = get_snowflake_config()
        
        # Determine account from URL or direct account config
        if config.get("url"):
            account = extract_account_from_url(config["url"])
        elif config.get("account"):
            account = config["account"]
        else:
            logger.error("Snowflake config must have either 'url' or 'account'")
            return None
        
        conn_params = {
            "account": account,
            "user": config["user"],
            "password": config["password"],
            "database": config["database"],
            "schema": config["schema"],
        }
        
        # Add warehouse if specified
        if config.get("warehouse"):
            conn_params["warehouse"] = config["warehouse"]
        
        conn = snowflake.connector.connect(**conn_params)
        return conn
    
    except ImportError:
        logger.error("snowflake-connector-python is not installed. Run: pip install snowflake-connector-python")
        return None
    except Exception as e:
        logger.error(f"Failed to connect to Snowflake: {e}")
        return None


def test_snowflake_connection() -> Tuple[bool, str]:
    """
    Test the Snowflake connection.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    if not is_snowflake_configured():
        return False, "Snowflake is not configured. Add [snowflake] section to .streamlit/secrets.toml"
    
    try:
        conn = get_snowflake_connection()
        if conn is None:
            return False, "Failed to establish connection"
        
        # Test with a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_TIMESTAMP()")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return True, f"Connected successfully. Server time: {result[0]}"
    
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


# =============================================================================
# TABLE NAMES (from the iTrack views)
# =============================================================================
TASK_TABLE = "DS_VW_ITRACK_LPM_TASK"
INCIDENT_VIEW = "DS_VW_ITRACK_PLMGETINCIDENT"  # Pre-joined task+incident view
WORKLOG_TABLE = "DS_VW_ITRACK_LPM_WORKLOG"


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_tasks_from_snowflake(_timestamp: str = None) -> Tuple[pd.DataFrame, bool, str]:
    """
    Fetch tasks from Snowflake for LAB PATH INFORMATICS team.
    
    Only imports INCIDENT tickets (not Service Requests).
    Tasks are filtered by OWNERTEAM = 'LAB PATH INFORMATICS'.
    
    The _timestamp parameter is used to invalidate cache on manual refresh.
    
    Returns:
        Tuple of (DataFrame, success: bool, message: str)
    """
    if not is_snowflake_configured():
        return pd.DataFrame(), False, "Snowflake is not configured"
    
    try:
        conn = get_snowflake_connection()
        if conn is None:
            return pd.DataFrame(), False, "Failed to connect to Snowflake"
        
        config = get_snowflake_config()
        schema = f"{config['database']}.{config['schema']}"
        
        # Join Task table with Incident view for ticket details
        # Only tasks owned by LAB PATH INFORMATICS are imported
        # TicketType is extracted from Subject by _extract_ticket_type() in sqlite_store.py
        query = f"""
        SELECT 
            t.ASSIGNMENTID as TaskNum,
            t.PARENTOBJECTDISPLAYID as TicketNum,
            t.STATUS as TaskStatus,
            t.SUBJECT as Subject,
            t.OWNER as AssignedTo,
            t.OWNERTEAM as TaskOwnerTeam,
            t.ASSIGNEDDATETIME as TaskAssignedDt,
            t.CREATEDDATETIME as TaskCreatedDt,
            t.RESOLVEDDATETIME as TaskResolvedDt,
            t.ACTUALEFFORT as TaskMinutesSpent,
            inc.TICKETSTATUS as TicketStatus,
            inc.CUSTNAME as CustomerName,
            inc.SECTION as Section,
            inc.TICKETOWNERTEAM as TicketOwnerTeam,
            inc.CREATEDBY as TicketCreatedBy,
            inc.TICKETCREATEDDATETIME as TicketCreatedDt,
            inc.TICKETRESOLVEDDATETIME as TicketResolvedDt,
            inc.TOTALTIMESPENTONTICKET as TicketTotalTimeSpent
        FROM {schema}.{TASK_TABLE} t
        LEFT JOIN {schema}.{INCIDENT_VIEW} inc
            ON t.ASSIGNMENTID = inc.ASSIGNMENTID
        WHERE t.OWNERTEAM = 'LAB PATH INFORMATICS'
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        # Load column mappings from config file
        task_mapping, _ = load_snowflake_column_mappings()
        
        # Snowflake returns uppercase column names
        # The config maps uppercase column names to app schema names
        column_rename = {}
        for col in df.columns:
            col_upper = col.upper()
            if col_upper in task_mapping:
                column_rename[col] = task_mapping[col_upper]
        
        df = df.rename(columns=column_rename)
        
        # Convert column types
        if not df.empty:
            # Parse dates
            date_cols = ['TaskAssignedDt', 'TaskCreatedDt', 'TaskResolvedDt', 
                        'TicketCreatedDt', 'TicketResolvedDt']
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # Convert numeric columns to clean string (remove .0 suffix)
            if 'TaskNum' in df.columns:
                df['TaskNum'] = df['TaskNum'].apply(lambda x: str(int(x)) if pd.notna(x) else '')
            if 'TicketNum' in df.columns:
                df['TicketNum'] = df['TicketNum'].apply(lambda x: str(int(x)) if pd.notna(x) else '')
        
        return df, True, f"Loaded {len(df)} tasks from Snowflake"
    
    except Exception as e:
        logger.error(f"Error fetching tasks from Snowflake: {e}")
        return pd.DataFrame(), False, f"Error: {str(e)}"


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_worklogs_from_snowflake(_timestamp: str = None) -> Tuple[pd.DataFrame, bool, str]:
    """
    Fetch worklogs from Snowflake by joining Worklog and Task tables.
    
    Joins:
    - DS_VW_ITRACK_LPM_WORKLOG (primary)
    - DS_VW_ITRACK_LPM_TASK (to get TaskNum/ASSIGNMENTID)
    
    Returns:
        Tuple of (DataFrame, success: bool, message: str)
    """
    if not is_snowflake_configured():
        return pd.DataFrame(), False, "Snowflake is not configured"
    
    try:
        conn = get_snowflake_connection()
        if conn is None:
            return pd.DataFrame(), False, "Failed to connect to Snowflake"
        
        config = get_snowflake_config()
        schema = f"{config['database']}.{config['schema']}"
        
        # Query joining Worklog and Task tables
        query = f"""
        SELECT 
            w.RECID as RecordId,
            t.ASSIGNMENTID as TaskNum,
            w.CREATEDBY as Owner,
            w.DESCRIPTION as Description,
            w.LOGDATE as LogDate,
            w.MINUTESSPENT as MinutesSpent,
            w.SHORTDESCRIPTION as ShortDescription
        FROM {schema}.{WORKLOG_TABLE} w
        INNER JOIN {schema}.{TASK_TABLE} t
            ON w.PARENTLINK_RECID = t.RECID
        WHERE t.OWNERTEAM = 'LAB PATH INFORMATICS'
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        # Load column mappings from config file
        _, worklog_mapping = load_snowflake_column_mappings()
        
        # Snowflake returns uppercase column names
        # The config maps source Snowflake columns to app columns
        column_rename = {}
        for col in df.columns:
            col_upper = col.upper()
            if col_upper in worklog_mapping:
                column_rename[col] = worklog_mapping[col_upper]
        
        df = df.rename(columns=column_rename)
        
        # Convert column types
        if not df.empty:
            if 'LogDate' in df.columns:
                df['LogDate'] = pd.to_datetime(df['LogDate'], errors='coerce')
            if 'TaskNum' in df.columns:
                df['TaskNum'] = df['TaskNum'].apply(lambda x: str(int(x)) if pd.notna(x) else '')
        
        return df, True, f"Loaded {len(df)} worklog entries from Snowflake"
    
    except Exception as e:
        logger.error(f"Error fetching worklogs from Snowflake: {e}")
        return pd.DataFrame(), False, f"Error: {str(e)}"


def clear_snowflake_cache():
    """Clear all Snowflake data caches to force a refresh."""
    fetch_tasks_from_snowflake.clear()
    fetch_worklogs_from_snowflake.clear()


def get_last_refresh_time() -> Optional[datetime]:
    """
    Get the time of the last data refresh.
    Stored in session state.
    """
    return st.session_state.get("snowflake_last_refresh")


def set_last_refresh_time():
    """Set the last refresh time to now."""
    st.session_state["snowflake_last_refresh"] = datetime.now()


def refresh_snowflake_data(previous_df: pd.DataFrame = None) -> Tuple[pd.DataFrame, bool, str, Dict]:
    """
    Force refresh data from Snowflake by clearing cache and fetching fresh data.
    Compares with previous data to show what changed.
    
    Args:
        previous_df: Previous DataFrame to compare against (optional)
    
    Returns:
        Tuple of (DataFrame, success: bool, message: str, change_summary: Dict)
    """
    change_summary = {
        'total_before': 0,
        'total_after': 0,
        'new_tasks': 0,
        'removed_tasks': 0,
        'updated_tasks': 0,
        'unchanged_tasks': 0,
        'status_changed': 0,
        'new_tasks_by_status': {},
        'task_status_changes': [],
    }
    
    # Build lookup from previous data
    previous_tasks = set()
    previous_data = {}
    if previous_df is not None and not previous_df.empty and 'TaskNum' in previous_df.columns:
        change_summary['total_before'] = len(previous_df)
        for _, row in previous_df.iterrows():
            task_num = str(row['TaskNum'])
            previous_tasks.add(task_num)
            previous_data[task_num] = {
                'TaskStatus': str(row.get('TaskStatus', '')),
                'AssignedTo': str(row.get('AssignedTo', '')),
                'Subject': str(row.get('Subject', ''))[:100],  # Truncate for comparison
            }
    
    clear_snowflake_cache()
    # Use current timestamp to bust cache
    timestamp = datetime.now().isoformat()
    df, success, message = fetch_tasks_from_snowflake(_timestamp=timestamp)
    
    if success:
        set_last_refresh_time()
        
        if not df.empty and 'TaskNum' in df.columns:
            change_summary['total_after'] = len(df)
            current_tasks = set(df['TaskNum'].astype(str).unique())
            
            # Calculate changes
            new_task_nums = current_tasks - previous_tasks
            removed_task_nums = previous_tasks - current_tasks
            existing_task_nums = current_tasks & previous_tasks
            
            change_summary['new_tasks'] = len(new_task_nums)
            change_summary['removed_tasks'] = len(removed_task_nums)
            
            # Track new tasks by status
            new_by_status = {}
            for _, row in df.iterrows():
                task_num = str(row['TaskNum'])
                if task_num in new_task_nums:
                    status = str(row.get('TaskStatus', 'Unknown'))
                    new_by_status[status] = new_by_status.get(status, 0) + 1
            change_summary['new_tasks_by_status'] = new_by_status
            
            # Check for changes on existing tasks
            updated_count = 0
            unchanged_count = 0
            status_changes = []
            
            for _, row in df.iterrows():
                task_num = str(row['TaskNum'])
                if task_num in existing_task_nums:
                    prev = previous_data.get(task_num, {})
                    curr_status = str(row.get('TaskStatus', ''))
                    curr_assigned = str(row.get('AssignedTo', ''))
                    curr_subject = str(row.get('Subject', ''))[:100]
                    
                    has_changes = False
                    
                    # Check status change
                    if prev.get('TaskStatus', '') != curr_status:
                        status_changes.append({
                            'task_num': task_num,
                            'old_status': prev.get('TaskStatus', ''),
                            'new_status': curr_status
                        })
                        has_changes = True
                    
                    # Check other field changes
                    if prev.get('AssignedTo', '') != curr_assigned:
                        has_changes = True
                    if prev.get('Subject', '') != curr_subject:
                        has_changes = True
                    
                    if has_changes:
                        updated_count += 1
                    else:
                        unchanged_count += 1
            
            change_summary['updated_tasks'] = updated_count
            change_summary['unchanged_tasks'] = unchanged_count
            change_summary['status_changed'] = len(status_changes)
            change_summary['task_status_changes'] = status_changes
    
    return df, success, message, change_summary


def refresh_snowflake_worklogs(previous_df: pd.DataFrame = None) -> Tuple[pd.DataFrame, bool, str, Dict]:
    """
    Force refresh worklog data from Snowflake by clearing cache and fetching fresh data.
    Compares with previous data to show what changed.
    
    Args:
        previous_df: Previous worklog DataFrame to compare against (optional)
    
    Returns:
        Tuple of (DataFrame, success: bool, message: str, change_summary: Dict)
    """
    change_summary = {
        'total_before': 0,
        'total_after': 0,
        'new_worklogs': 0,
        'removed_worklogs': 0,
    }
    
    # Build lookup from previous data
    previous_records = set()
    if previous_df is not None and not previous_df.empty and 'RecordId' in previous_df.columns:
        change_summary['total_before'] = len(previous_df)
        previous_records = set(previous_df['RecordId'].astype(str).unique())
    
    # Clear cache and fetch fresh data
    fetch_worklogs_from_snowflake.clear()
    timestamp = datetime.now().isoformat()
    df, success, message = fetch_worklogs_from_snowflake(_timestamp=timestamp)
    
    if success:
        if not df.empty and 'RecordId' in df.columns:
            change_summary['total_after'] = len(df)
            current_records = set(df['RecordId'].astype(str).unique())
            
            # Calculate changes
            new_records = current_records - previous_records
            removed_records = previous_records - current_records
            
            change_summary['new_worklogs'] = len(new_records)
            change_summary['removed_worklogs'] = len(removed_records)
    
    return df, success, message, change_summary


# =============================================================================
# DATABASE EXPLORATION FUNCTIONS
# =============================================================================

def list_tables() -> Tuple[pd.DataFrame, bool, str]:
    """
    List all tables and views in the configured schema.
    
    Returns:
        Tuple of (DataFrame with table info, success: bool, message: str)
    """
    try:
        conn = get_snowflake_connection()
        if conn is None:
            return pd.DataFrame(), False, "Failed to connect to Snowflake"
        
        config = get_snowflake_config()
        
        query = f"""
        SELECT 
            TABLE_NAME,
            TABLE_TYPE,
            ROW_COUNT,
            CREATED,
            LAST_ALTERED
        FROM {config['database']}.INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = '{config['schema'].upper()}'
        ORDER BY TABLE_NAME
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        return df, True, f"Found {len(df)} tables/views"
    
    except Exception as e:
        return pd.DataFrame(), False, f"Error listing tables: {str(e)}"


def describe_table(table_name: str) -> Tuple[pd.DataFrame, bool, str]:
    """
    Get column information for a specific table.
    
    Returns:
        Tuple of (DataFrame with column info, success: bool, message: str)
    """
    try:
        conn = get_snowflake_connection()
        if conn is None:
            return pd.DataFrame(), False, "Failed to connect to Snowflake"
        
        config = get_snowflake_config()
        
        query = f"""
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            CHARACTER_MAXIMUM_LENGTH,
            NUMERIC_PRECISION,
            COLUMN_DEFAULT
        FROM {config['database']}.INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = '{config['schema'].upper()}'
          AND TABLE_NAME = '{table_name.upper()}'
        ORDER BY ORDINAL_POSITION
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        return df, True, f"Found {len(df)} columns in {table_name}"
    
    except Exception as e:
        return pd.DataFrame(), False, f"Error describing table: {str(e)}"


def preview_table(table_name: str, limit: int = 10) -> Tuple[pd.DataFrame, bool, str]:
    """
    Get a preview of data from a specific table.
    
    Returns:
        Tuple of (DataFrame with sample data, success: bool, message: str)
    """
    try:
        conn = get_snowflake_connection()
        if conn is None:
            return pd.DataFrame(), False, "Failed to connect to Snowflake"
        
        config = get_snowflake_config()
        full_table_name = f"{config['database']}.{config['schema']}.{table_name}"
        
        query = f"SELECT * FROM {full_table_name} LIMIT {limit}"
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        return df, True, f"Showing {len(df)} rows from {table_name}"
    
    except Exception as e:
        return pd.DataFrame(), False, f"Error previewing table: {str(e)}"


def get_table_row_count(table_name: str) -> Tuple[int, bool, str]:
    """
    Get the row count for a specific table.
    
    Returns:
        Tuple of (row_count, success: bool, message: str)
    """
    try:
        conn = get_snowflake_connection()
        if conn is None:
            return 0, False, "Failed to connect to Snowflake"
        
        config = get_snowflake_config()
        full_table_name = f"{config['database']}.{config['schema']}.{table_name}"
        
        query = f"SELECT COUNT(*) as cnt FROM {full_table_name}"
        
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return result[0], True, f"Table {table_name} has {result[0]} rows"
    
    except Exception as e:
        return 0, False, f"Error counting rows: {str(e)}"


def get_column_values(table_name: str, column_name: str, limit: int = 50) -> Tuple[pd.DataFrame, bool, str]:
    """
    Get distinct values for a specific column.
    
    Returns:
        Tuple of (DataFrame with distinct values, success: bool, message: str)
    """
    try:
        conn = get_snowflake_connection()
        if conn is None:
            return pd.DataFrame(), False, "Failed to connect to Snowflake"
        
        config = get_snowflake_config()
        full_table_name = f"{config['database']}.{config['schema']}.{table_name}"
        
        query = f"""
        SELECT {column_name}, COUNT(*) as count 
        FROM {full_table_name} 
        GROUP BY {column_name} 
        ORDER BY count DESC 
        LIMIT {limit}
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        return df, True, f"Found {len(df)} distinct values"
    
    except Exception as e:
        return pd.DataFrame(), False, f"Error getting column values: {str(e)}"


def test_table_joins() -> Tuple[Dict, bool, str]:
    """
    Test the joins between the three iTrack tables:
    - DS_VW_ITRACK_LPM_TASK
    - DS_VW_ITRACK_LPM_INCIDENT  
    - DS_VW_ITRACK_LPM_WORKLOG
    
    Returns:
        Tuple of (results dict, success: bool, message: str)
    """
    results = {
        'task_count': 0,
        'incident_count': 0,
        'worklog_count': 0,
        'task_incident_join_count': 0,
        'task_incident_match_rate': 0.0,
        'worklog_task_join_count': 0,
        'worklog_task_match_rate': 0.0,
        'sample_joined_tasks': None,
        'sample_joined_worklogs': None,
    }
    
    try:
        conn = get_snowflake_connection()
        if conn is None:
            return results, False, "Failed to connect to Snowflake"
        
        config = get_snowflake_config()
        schema = f"{config['database']}.{config['schema']}"
        
        # 1. Count records in each table (use uppercase CNT for Snowflake)
        task_count_query = f"SELECT COUNT(*) as CNT FROM {schema}.DS_VW_ITRACK_LPM_TASK"
        results['task_count'] = pd.read_sql(task_count_query, conn).iloc[0]['CNT']
        
        incident_count_query = f"SELECT COUNT(*) as CNT FROM {schema}.DS_VW_ITRACK_LPM_INCIDENT"
        results['incident_count'] = pd.read_sql(incident_count_query, conn).iloc[0]['CNT']
        
        worklog_count_query = f"SELECT COUNT(*) as CNT FROM {schema}.DS_VW_ITRACK_LPM_WORKLOG"
        results['worklog_count'] = pd.read_sql(worklog_count_query, conn).iloc[0]['CNT']
        
        # 2. Test Task-Incident join (PARENTOBJECTDISPLAYID = INCIDENTNUMBER)
        task_incident_join_query = f"""
        SELECT COUNT(*) as CNT
        FROM {schema}.DS_VW_ITRACK_LPM_TASK t
        INNER JOIN {schema}.DS_VW_ITRACK_LPM_INCIDENT i
            ON t.PARENTOBJECTDISPLAYID = i.INCIDENTNUMBER
        """
        results['task_incident_join_count'] = pd.read_sql(task_incident_join_query, conn).iloc[0]['CNT']
        
        if results['task_count'] > 0:
            results['task_incident_match_rate'] = (results['task_incident_join_count'] / results['task_count']) * 100
        
        # 3. Test Worklog-Task join (PARENTLINK_RECID = RECID)
        worklog_task_join_query = f"""
        SELECT COUNT(*) as CNT
        FROM {schema}.DS_VW_ITRACK_LPM_WORKLOG w
        INNER JOIN {schema}.DS_VW_ITRACK_LPM_TASK t
            ON w.PARENTLINK_RECID = t.RECID
        """
        results['worklog_task_join_count'] = pd.read_sql(worklog_task_join_query, conn).iloc[0]['CNT']
        
        if results['worklog_count'] > 0:
            results['worklog_task_match_rate'] = (results['worklog_task_join_count'] / results['worklog_count']) * 100
        
        # 4. Sample joined task data
        sample_task_query = f"""
        SELECT 
            t.ASSIGNMENTID as TaskNum,
            t.PARENTOBJECTDISPLAYID as TicketNum,
            t.STATUS as TaskStatus,
            t.SUBJECT as Subject,
            t.OWNER as AssignedTo,
            t.ASSIGNEDDATETIME as TaskAssignedDt,
            i.STATUS as TicketStatus,
            i.PROFILEFULLNAME as CustomerName,
            i.INCIDENTNUMBER as IncidentNum
        FROM {schema}.DS_VW_ITRACK_LPM_TASK t
        LEFT JOIN {schema}.DS_VW_ITRACK_LPM_INCIDENT i
            ON t.PARENTOBJECTDISPLAYID = i.INCIDENTNUMBER
        WHERE t.OWNERTEAM = 'LAB PATH INFORMATICS'
        LIMIT 5
        """
        results['sample_joined_tasks'] = pd.read_sql(sample_task_query, conn)
        
        # 5. Sample joined worklog data
        sample_worklog_query = f"""
        SELECT 
            w.RECID as RecordId,
            t.ASSIGNMENTID as TaskNum,
            w.CREATEDBY as Owner,
            w.LOGDATE as LogDate,
            w.MINUTESSPENT as MinutesSpent,
            w.SHORTDESCRIPTION as ShortDesc
        FROM {schema}.DS_VW_ITRACK_LPM_WORKLOG w
        INNER JOIN {schema}.DS_VW_ITRACK_LPM_TASK t
            ON w.PARENTLINK_RECID = t.RECID
        WHERE t.OWNERTEAM = 'LAB PATH INFORMATICS'
        LIMIT 5
        """
        results['sample_joined_worklogs'] = pd.read_sql(sample_worklog_query, conn)
        
        conn.close()
        
        return results, True, "Join tests completed successfully"
    
    except Exception as e:
        return results, False, f"Error testing joins: {str(e)}"
