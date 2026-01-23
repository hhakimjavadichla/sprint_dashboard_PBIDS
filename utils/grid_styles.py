"""
Professional Dashboard Styles
Clean, modern design for project management dashboard
"""
import streamlit as st

# Custom CSS for AgGrid - applied via custom_css parameter
GRID_CUSTOM_CSS = {
    ".ag-tooltip": {
        "background-color": "#1a1a2e !important",
        "color": "#ffffff !important",
        "border": "2px solid #4a90d9 !important",
        "border-radius": "8px !important",
        "padding": "12px 16px !important",
        "max-width": "450px !important",
        "min-width": "200px !important",
        "font-size": "14px !important",
        "line-height": "1.5 !important",
        "box-shadow": "0 4px 16px rgba(0, 0, 0, 0.4) !important",
        "white-space": "normal !important",
        "word-wrap": "break-word !important",
        "z-index": "99999 !important",
    }
}

def apply_grid_styles():
    """
    Apply professional dashboard CSS styles.
    Call this once at the top of pages.
    """
    st.markdown("""
    <style>
    /* ===== PROFESSIONAL DASHBOARD THEME ===== */
    
    /* Compact metrics - smaller text */
    div[data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
        font-weight: 600 !important;
    }
    
    div[data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        color: #666 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    
    div[data-testid="stMetricDelta"] {
        font-size: 0.75rem !important;
    }
    
    /* Metric containers - tighter spacing */
    div[data-testid="metric-container"] {
        padding: 0.5rem 0 !important;
    }
    
    /* Page titles */
    h1 {
        font-size: 1.6rem !important;
        font-weight: 600 !important;
        color: #1a1a2e !important;
        margin-bottom: 0.25rem !important;
    }
    
    /* Section headers */
    h2, h3 {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        color: #333 !important;
        margin-top: 1rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Subheaders */
    .stSubheader {
        font-size: 1rem !important;
        font-weight: 500 !important;
    }
    
    /* Tab styling - cleaner look */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        padding: 8px 16px !important;
        border-radius: 4px 4px 0 0 !important;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa !important;
    }
    
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        font-size: 0.95rem !important;
    }
    
    /* Selectbox and inputs - smaller */
    .stSelectbox label, .stMultiSelect label, .stTextInput label {
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        color: #555 !important;
    }
    
    /* Button styling */
    .stButton > button {
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        border-radius: 4px !important;
    }
    
    /* Info/Warning/Success boxes - compact */
    .stAlert {
        padding: 0.5rem 1rem !important;
        font-size: 0.85rem !important;
    }
    
    /* Dividers - subtle */
    hr {
        margin: 0.75rem 0 !important;
        border-color: #e0e0e0 !important;
    }
    
    /* Caption text */
    .stCaption {
        font-size: 0.75rem !important;
        color: #888 !important;
    }
    
    /* Expander headers */
    .streamlit-expanderHeader {
        font-size: 0.85rem !important;
        font-weight: 500 !important;
    }
    
    /* AgGrid Tooltip Styling - Enhanced for visibility */
    .ag-tooltip,
    .ag-theme-streamlit .ag-tooltip,
    .ag-theme-alpine .ag-tooltip,
    div.ag-tooltip {
        background-color: #1a1a2e !important;
        color: #ffffff !important;
        border: 2px solid #4a90d9 !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        max-width: 450px !important;
        min-width: 200px !important;
        font-size: 14px !important;
        line-height: 1.5 !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4) !important;
        white-space: normal !important;
        word-wrap: break-word !important;
        z-index: 99999 !important;
    }
    
    /* AgGrid horizontal scroll bar */
    .ag-body-horizontal-scroll {
        display: block !important;
        height: 12px !important;
    }
    
    .ag-body-horizontal-scroll-viewport {
        overflow-x: scroll !important;
    }
    
    .ag-horizontal-scroll-viewport::-webkit-scrollbar {
        height: 12px !important;
    }
    
    .ag-horizontal-scroll-viewport::-webkit-scrollbar-thumb {
        background-color: #888 !important;
        border-radius: 6px !important;
    }
    
    .ag-horizontal-scroll-viewport::-webkit-scrollbar-track {
        background-color: #f1f1f1 !important;
    }
    
    /* Prototype banner - subtle */
    div[data-testid="stCaptionContainer"] {
        margin-bottom: 0.5rem !important;
    }
    
    /* Remove excess padding */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* Compact dataframe */
    .stDataFrame {
        font-size: 0.85rem !important;
    }
    
    /* ===== FULLSCREEN AGGRID STYLES ===== */
    /* Fullscreen container */
    .fullscreen-container {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        z-index: 9999 !important;
        background-color: white !important;
        padding: 20px !important;
        overflow: auto !important;
    }
    
    .fullscreen-container .stAgGrid {
        height: calc(100vh - 80px) !important;
    }
    
    /* Fullscreen button styling */
    .fullscreen-btn {
        position: absolute;
        top: 5px;
        right: 5px;
        z-index: 100;
        background: #f0f2f6;
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 4px 8px;
        cursor: pointer;
        font-size: 12px;
    }
    
    .fullscreen-btn:hover {
        background: #e0e2e6;
    }
    
    </style>
    """, unsafe_allow_html=True)


def get_custom_css():
    """Return custom CSS dict for AgGrid custom_css parameter"""
    return GRID_CUSTOM_CSS


def fullscreen_toggle(key: str) -> bool:
    """
    Create a fullscreen toggle checkbox for AgGrid tables.
    Returns True if fullscreen mode is enabled.
    
    Usage:
        is_fullscreen = fullscreen_toggle("my_table")
        height = "100vh" if is_fullscreen else 600
        AgGrid(..., height=height)
    """
    return st.checkbox("⛶ Expand table", key=f"fullscreen_{key}", help="Toggle fullscreen view")


def get_grid_height(is_fullscreen: bool, default_height: int = 600) -> int:
    """Get appropriate height for AgGrid based on fullscreen state."""
    return 900 if is_fullscreen else default_height


# ===== COLOR CODING DEFINITIONS =====
# These JsCode functions are used for conditional cell styling in AgGrid

from st_aggrid import JsCode

# Status color coding (based on iTrack workflow)
# Workflow: Logged -> Assigned -> Accepted -> Waiting -> Completed/Closed
STATUS_CELL_STYLE = JsCode("""
function(params) {
    if (!params.value) return {};
    const status = params.value.toLowerCase();
    
    if (status === 'completed' || status === 'closed' || status === 'resolved' || status === 'done') {
        return {'backgroundColor': '#d4edda', 'color': '#155724'};  // Green - Finished
    } else if (status === 'accepted') {
        return {'backgroundColor': '#d1ecf1', 'color': '#0c5460'};  // Cyan - Actively working
    } else if (status === 'assigned') {
        return {'backgroundColor': '#fff3cd', 'color': '#856404'};  // Yellow - Assigned, awaiting acceptance
    } else if (status === 'waiting') {
        return {'backgroundColor': '#ffeeba', 'color': '#856404'};  // Amber - On hold
    } else if (status === 'logged') {
        return {'backgroundColor': '#cce5ff', 'color': '#004085'};  // Blue - New, unassigned
    } else if (status === 'canceled' || status === 'cancelled' || status === 'excluded from carryover') {
        return {'backgroundColor': '#e2e3e5', 'color': '#383d41'};  // Gray - Excluded
    }
    return {};
}
""")

# Priority color coding (0=No longer needed, 1=Lowest to 5=Highest, NotAssigned)
PRIORITY_CELL_STYLE = JsCode("""
function(params) {
    if (params.value === null || params.value === undefined || params.value === '') return {};
    
    // Handle 'NotAssigned' string
    if (params.value === 'NotAssigned') {
        return {'backgroundColor': '#f0f0f0', 'color': '#666666', 'fontStyle': 'italic'};  // Light gray - Not assigned
    }
    
    const priority = parseInt(params.value);
    
    if (priority === 5) {
        return {'backgroundColor': '#f8d7da', 'color': '#721c24', 'fontWeight': 'bold'};  // Red - Highest
    } else if (priority === 4) {
        return {'backgroundColor': '#ffe5d0', 'color': '#8a4500'};  // Orange - High
    } else if (priority === 3) {
        return {'backgroundColor': '#fff3cd', 'color': '#856404'};  // Yellow - Medium
    } else if (priority === 2) {
        return {'backgroundColor': '#d4edda', 'color': '#155724'};  // Green - Low
    } else if (priority === 1) {
        return {'backgroundColor': '#cce5ff', 'color': '#004085'};  // Blue - Lowest
    } else if (priority === 0) {
        return {'backgroundColor': '#e2e3e5', 'color': '#383d41', 'textDecoration': 'line-through'};  // Gray strikethrough - No longer needed
    }
    return {};
}
""")

# Days Open color coding (based on TAT thresholds)
# IR: 0.8 days threshold, SR: 22 days threshold
# Yellow warning at 75% of threshold, Red when exceeded
DAYS_OPEN_CELL_STYLE = JsCode("""
function(params) {
    if (params.value === null || params.value === undefined) return {};
    const days = parseFloat(params.value);
    
    // Get ticket type from same row if available
    const ticketType = params.data ? params.data.TicketType : null;
    
    if (ticketType === 'IR') {
        // IR threshold: 0.8 days
        if (days >= 0.8) {
            return {'backgroundColor': '#f8d7da', 'color': '#721c24', 'fontWeight': 'bold'};  // Red - Exceeded
        } else if (days >= 0.6) {
            return {'backgroundColor': '#fff3cd', 'color': '#856404'};  // Yellow - At Risk (75%)
        }
    } else if (ticketType === 'SR') {
        // SR threshold: 22 days
        if (days >= 22) {
            return {'backgroundColor': '#f8d7da', 'color': '#721c24', 'fontWeight': 'bold'};  // Red - Exceeded
        } else if (days >= 16.5) {
            return {'backgroundColor': '#fff3cd', 'color': '#856404'};  // Yellow - At Risk (75%)
        }
    } else {
        // Generic coloring for PR/NC or unknown types
        if (days >= 30) {
            return {'backgroundColor': '#f8d7da', 'color': '#721c24', 'fontWeight': 'bold'};  // Red - Very old
        } else if (days >= 14) {
            return {'backgroundColor': '#fff3cd', 'color': '#856404'};  // Yellow - Getting old
        }
    }
    
    // Green for fresh tasks
    if (days <= 3) {
        return {'backgroundColor': '#d4edda', 'color': '#155724'};  // Green - Fresh
    }
    
    return {};
}
""")


# Task Origin color coding (New, Assigned)
TASK_ORIGIN_CELL_STYLE = JsCode("""
function(params) {
    if (!params.value) return {};
    const origin = params.value.toLowerCase();
    
    if (origin === 'new') {
        return {'backgroundColor': '#d4edda', 'color': '#155724', 'fontWeight': 'bold'};  // Green - New task (created in this sprint)
    } else if (origin === 'assigned') {
        return {'backgroundColor': '#cce5ff', 'color': '#004085', 'fontWeight': 'bold'};  // Blue - Assigned from backlog
    }
    return {};
}
""")


def get_color_coded_column_defs():
    """
    Return a dict of column names to their JsCode cell style functions.
    Use this to apply consistent color coding across all AgGrid tables.
    """
    return {
        'Status': STATUS_CELL_STYLE,
        'CustomerPriority': PRIORITY_CELL_STYLE,
        'Priority': PRIORITY_CELL_STYLE,
        'DaysOpen': DAYS_OPEN_CELL_STYLE,
        'Days Open': DAYS_OPEN_CELL_STYLE,
        'TaskOrigin': TASK_ORIGIN_CELL_STYLE,
    }


def calc_column_width(header_name: str, min_width: int = 70, max_width: int = 250, 
                      char_width: int = 9, padding: int = 30) -> int:
    """
    Calculate column width based on header name length.
    
    Args:
        header_name: The column header text
        min_width: Minimum column width in pixels
        max_width: Maximum column width in pixels
        char_width: Approximate pixels per character (default 9 for typical fonts)
        padding: Extra padding for sort icon, filter icon, etc.
    
    Returns:
        Calculated width in pixels
    """
    # Calculate based on header length
    calculated = len(header_name) * char_width + padding
    
    # Clamp to min/max
    return max(min_width, min(calculated, max_width))


# Pre-calculated widths for common columns (ensures consistency across tables)
COLUMN_WIDTHS = {
    # Sprint fields
    'SprintNumber': calc_column_width('✏️ SprintNumber'),
    'SprintName': calc_column_width('SprintName'),
    'SprintStartDt': calc_column_width('SprintStartDt'),
    'SprintEndDt': calc_column_width('SprintEndDt'),
    
    # Task identifiers
    'TaskOrigin': calc_column_width('TaskOrigin'),
    'TicketNum': calc_column_width('TicketNum'),
    'TaskNum': calc_column_width('TaskNum'),
    'TaskCount': calc_column_width('Task#'),
    'UniqueTaskId': calc_column_width('UniqueTaskId'),
    
    # Task info
    'TicketType': calc_column_width('TicketType'),
    'Section': calc_column_width('Section'),
    'CustomerName': calc_column_width('CustomerName'),
    'Status': calc_column_width('Status'),
    'AssignedTo': calc_column_width('AssignedTo'),
    'Subject': 200,  # Keep wide for long text
    
    # Dates
    'TicketCreatedDt': calc_column_width('TicketCreatedDt'),
    'TaskCreatedDt': calc_column_width('TaskCreatedDt'),
    'TaskAssignedDt': calc_column_width('TaskAssignedDt'),
    'StatusUpdateDt': calc_column_width('StatusUpdateDt'),
    
    # Metrics
    'DaysOpen': calc_column_width('DaysOpen'),
    'DaysCreated': calc_column_width('DaysCreated'),
    
    # Editable planning fields (with ✏️ prefix)
    'CustomerPriority': calc_column_width('✏️ CustomerPriority'),
    'FinalPriority': calc_column_width('✏️ FinalPriority'),
    'GoalType': calc_column_width('✏️ GoalType'),
    'DependencyOn': calc_column_width('✏️ DependencyOn'),
    'DependenciesLead': calc_column_width('✏️ DependenciesLead'),
    'DependencySecured': calc_column_width('✏️ DependencySecured'),
    'Comments': calc_column_width('✏️ Comments'),
    'HoursEstimated': calc_column_width('✏️ HoursEstimated'),
    
    # Hours fields
    'TaskHoursSpent': calc_column_width('TaskHoursSpent'),
    'TicketHoursSpent': calc_column_width('TicketHoursSpent'),
    
    # Completed tasks specific
    'CompletedInSprint': calc_column_width('CompletedInSprint'),
    'SprintsAssigned': calc_column_width('SprintsAssigned'),
    'OriginalSprintNumber': calc_column_width('OriginalSprintNumber'),
    
    # Additional columns
    'TicketStatus': calc_column_width('TicketStatus'),
}


# ===== SUBJECT CLEANING =====
import re

def clean_subject_prefix(subject) -> str:
    """
    Remove LAB-XX: NNNNNN - prefix from subject.
    
    Example: "LAB-SR: 1891370 - PIBIDS - Clean up" -> "PIBIDS - Clean up"
    """
    import pandas as pd
    if pd.isna(subject):
        return subject
    return re.sub(r'^LAB-\w+:\s*\d+\s*-\s*', '', str(subject))


def clean_subject_column(df, subject_col: str = 'Subject'):
    """
    Apply subject prefix cleaning to a DataFrame column.
    
    Args:
        df: DataFrame to modify
        subject_col: Name of the subject column
    
    Returns:
        DataFrame with cleaned subject column
    """
    if subject_col in df.columns:
        df[subject_col] = df[subject_col].apply(clean_subject_prefix)
    return df


# ===== STANDARDIZED COLUMN ORDER =====
# This defines the consistent column order across Dashboard, Section View, Sprint Planning
# Internal/hidden columns (_TicketGroup, _IsMultiTask) are prepended by each page
STANDARD_COLUMN_ORDER = [
    # Sprint info (for Sprint Planning, Sprint View)
    'SprintNumber', 'SprintName', 'SprintStartDt', 'SprintEndDt', 'SprintsAssigned',
    # Ticket/Task identifiers
    'TicketNum', 'TicketType', 'Subject',
    # Task info
    'TaskNum', 'TaskCount', 'Section', 'CustomerName',
    # Status and assignment
    'TaskStatus', 'TicketStatus', 'AssignedTo',
    # Dates
    'TicketCreatedDt', 'TaskCreatedDt', 'DaysOpen',
    # Planning fields
    'CustomerPriority', 'FinalPriority', 'GoalType',
    # Dependencies
    'DependencyOn', 'DependenciesLead', 'DependencySecured',
    # Notes and effort
    'Comments', 'HoursEstimated', 'TaskHoursSpent', 'TicketHoursSpent',
]

# Work Backlogs column order - starts with SprintsAssigned, no sprint detail columns
BACKLOG_COLUMN_ORDER = [
    # Sprint assignment (key column for backlog)
    'SprintsAssigned',
    # Ticket/Task identifiers
    'TicketNum', 'TicketType', 'Subject',
    # Task info
    'TaskNum', 'TaskCount', 'Section', 'CustomerName',
    # Status and assignment
    'TaskStatus', 'TicketStatus', 'AssignedTo',
    # Dates
    'TicketCreatedDt', 'TaskCreatedDt', 'DaysOpen',
    # Planning fields
    'CustomerPriority', 'FinalPriority', 'GoalType',
    # Dependencies
    'DependencyOn', 'DependenciesLead', 'DependencySecured',
    # Notes and effort
    'Comments', 'HoursEstimated', 'TaskHoursSpent', 'TicketHoursSpent',
]


def get_standard_column_order(assignee_col: str = 'AssignedTo') -> list:
    """
    Get the standard column order for task tables.
    
    Args:
        assignee_col: The assignee column name to use (e.g., 'AssignedTo' or 'AssignedTo_Display')
    
    Returns:
        List of column names in the standard order
    """
    # Replace 'AssignedTo' with the specified column name
    return [assignee_col if col == 'AssignedTo' else col for col in STANDARD_COLUMN_ORDER]


def get_display_column_order(assignee_col: str = 'AssignedTo') -> list:
    """
    Get the full display column order including hidden columns for row styling.
    
    Args:
        assignee_col: The assignee column name to use
    
    Returns:
        List of column names including hidden columns at the start
    """
    return ['_TicketGroup', '_IsMultiTask'] + get_standard_column_order(assignee_col)


def get_backlog_column_order(assignee_col: str = 'AssignedTo') -> list:
    """
    Get the column order for Work Backlogs page.
    Starts with SprintsAssigned, excludes sprint detail columns (SprintNumber, SprintName, etc.)
    
    Args:
        assignee_col: The assignee column name to use
    
    Returns:
        List of column names for backlog display
    """
    cols = [assignee_col if col == 'AssignedTo' else col for col in BACKLOG_COLUMN_ORDER]
    return ['_TicketGroup', '_IsMultiTask'] + cols


# Load column descriptions from config file
def _load_column_descriptions() -> dict:
    """Load column descriptions from .streamlit/column_descriptions.toml"""
    import os
    try:
        import tomli
    except ImportError:
        try:
            import tomllib as tomli
        except ImportError:
            # Fallback to empty dict if toml library not available
            return {}
    
    config_path = os.path.join(os.path.dirname(__file__), '..', '.streamlit', 'column_descriptions.toml')
    
    try:
        with open(config_path, 'rb') as f:
            config = tomli.load(f)
            return config.get('descriptions', {})
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

# Column descriptions loaded from config file
COLUMN_DESCRIPTIONS = _load_column_descriptions()


def get_column_description(column_name: str) -> str:
    """Get the description for a column to use as header tooltip."""
    return COLUMN_DESCRIPTIONS.get(column_name, '')


def get_column_width(column_name: str, header_name: str = None) -> int:
    """
    Get the width for a column, using pre-calculated widths or calculating on the fly.
    
    Args:
        column_name: The column field name
        header_name: Optional display header name (if different from column_name)
    
    Returns:
        Width in pixels
    """
    # Check pre-calculated widths first
    if column_name in COLUMN_WIDTHS:
        return COLUMN_WIDTHS[column_name]
    
    # Calculate based on header name
    display_name = header_name or column_name
    return calc_column_width(display_name)


def display_column_help(columns: list = None, title: str = "📖 Column Descriptions"):
    """
    Display an expandable section with column descriptions.
    
    Args:
        columns: Optional list of column names to show. If None, shows all available descriptions.
        title: Title for the expander
    """
    with st.expander(title, expanded=False):
        if columns:
            # Show only specified columns
            descriptions = {col: COLUMN_DESCRIPTIONS.get(col, '') for col in columns if col in COLUMN_DESCRIPTIONS}
        else:
            descriptions = COLUMN_DESCRIPTIONS
        
        if not descriptions:
            st.info("No column descriptions available.")
            return
        
        # Group columns by category
        categories = {
            "Sprint Fields": ["SprintNumber", "SprintName", "SprintStartDt", "SprintEndDt", "SprintsAssigned"],
            "Task Identifiers": ["TaskOrigin", "TicketNum", "TaskNum", "TaskCount"],
            "Task Info": ["TicketType", "Section", "CustomerName", "Status", "AssignedTo", "Subject"],
            "Dates": ["TicketCreatedDt", "TaskCreatedDt", "TaskAssignedDt", "StatusUpdateDt"],
            "Metrics": ["DaysOpen", "DaysCreated"],
            "Planning Fields": ["CustomerPriority", "FinalPriority", "GoalType", "DependencyOn", "DependenciesLead", "DependencySecured", "Comments", "HoursEstimated"],
            "Hours": ["TaskHoursSpent", "TicketHoursSpent"],
            "Other": ["CompletedInSprint", "OriginalSprintNumber", "IsCarryover"]
        }
        
        # Display in columns for better layout
        col1, col2 = st.columns(2)
        
        displayed = set()
        col_idx = 0
        
        for category, cat_columns in categories.items():
            # Filter to only columns that exist in descriptions
            cat_items = [(col, descriptions[col]) for col in cat_columns if col in descriptions]
            if not cat_items:
                continue
            
            target_col = col1 if col_idx % 2 == 0 else col2
            col_idx += 1
            
            with target_col:
                st.markdown(f"**{category}**")
                for col_name, desc in cat_items:
                    st.markdown(f"- **{col_name}**: {desc}")
                    displayed.add(col_name)
                st.write("")  # spacing
        
        # Show any remaining columns not in categories
        remaining = [(k, v) for k, v in descriptions.items() if k not in displayed]
        if remaining:
            st.markdown("**Other Fields**")
            for col_name, desc in remaining:
                st.markdown(f"- **{col_name}**: {desc}")
