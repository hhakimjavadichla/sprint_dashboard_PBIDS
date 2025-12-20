"""
Constants and configuration values for the Sprint Dashboard
Values are loaded from config file with fallback defaults
"""
import os
try:
    import tomllib
except ImportError:
    import tomli as tomllib

# Load config file
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '.streamlit', 'itrack_mapping.toml')

def _load_config():
    """Load configuration from TOML file"""
    try:
        with open(CONFIG_PATH, 'rb') as f:
            return tomllib.load(f)
    except Exception:
        return {}

_config = _load_config()

# Sprint Configuration (from config with fallbacks)
_sprint_schedule = _config.get('sprint_schedule', {})
SPRINT_DURATION_DAYS = _sprint_schedule.get('duration_days', 14)
SPRINT_START_WEEKDAY = _sprint_schedule.get('start_weekday', 3)  # Thursday
SPRINT_END_WEEKDAY = _sprint_schedule.get('end_weekday', 2)  # Wednesday
SPRINT_CYCLE_NAME = _sprint_schedule.get('cycle_name', 'Thursday-to-Wednesday')
SPRINT_ENFORCE_START_DAY = _sprint_schedule.get('enforce_start_day', True)

# Capacity Configuration (from config with fallbacks)
_sprint_capacity = _config.get('sprint_capacity', {})
MAX_CAPACITY_HOURS = _sprint_capacity.get('max_hours', 52)
WARNING_CAPACITY_HOURS = _sprint_capacity.get('warning_hours', 45)
CAPACITY_PERCENTAGE_MAX = _sprint_capacity.get('capacity_percentage', 65)

# TAT Configuration (from config with fallbacks)
_tat_thresholds = _config.get('tat_thresholds', {})
TAT_IR_DAYS = _tat_thresholds.get('ir_days', 0.8)
TAT_SR_DAYS = _tat_thresholds.get('sr_days', 22)
TAT_WARNING_THRESHOLD = _tat_thresholds.get('warning_percent', 75) / 100

# Ticket Types
TICKET_TYPE_IR = "IR"  # Incident Request
TICKET_TYPE_SR = "SR"  # Service Request
TICKET_TYPE_PR = "PR"  # Project Request
TICKET_TYPE_NC = "NC"  # Not Classified

TICKET_TYPES = [TICKET_TYPE_IR, TICKET_TYPE_SR, TICKET_TYPE_PR, TICKET_TYPE_NC]

# Priority Levels
PRIORITY_CRITICAL = 5
PRIORITY_HIGH = 4
PRIORITY_MEDIUM = 3
PRIORITY_LOW = 2
PRIORITY_MINIMAL = 1
PRIORITY_NONE = 0

PRIORITIES = [PRIORITY_CRITICAL, PRIORITY_HIGH, PRIORITY_MEDIUM, 
              PRIORITY_LOW, PRIORITY_MINIMAL, PRIORITY_NONE]

# Status Values
STATUS_COMPLETED = "Completed"
STATUS_CANCELED = "Canceled"
STATUS_CLOSED = "Closed"
STATUS_RESOLVED = "Resolved"
STATUS_DONE = "Done"
STATUS_EXCLUDED_CARRYOVER = "Excluded from Carryover"  # Admin manual exclusion

# Statuses that prevent carryover to next sprint
STATUS_EXCLUDED = [
    STATUS_COMPLETED, 
    STATUS_CANCELED, 
    STATUS_CLOSED, 
    STATUS_RESOLVED, 
    STATUS_DONE,
    STATUS_EXCLUDED_CARRYOVER
]

# File Paths
DATA_DIR = "data"
CURRENT_SPRINT_FILE = f"{DATA_DIR}/current_sprint.csv"
PAST_SPRINTS_FILE = f"{DATA_DIR}/past_sprints.csv"
ITRACK_EXTRACT_FILE = f"{DATA_DIR}/itrack_extract.csv"

# Column Mappings (iTrack to Sprint)
ITRACK_TO_SPRINT_MAPPING = {
    'Task': 'TaskNum',
    'Parent ID': 'TicketNum',
    'Status': 'Status',
    'Assignee': 'AssignedTo',
    'Subject': 'Subject',
    'Team': 'Section',
    'Created On': 'TaskCreatedDt',
    'Created Inc': 'TicketCreatedDt_Inc',
    'Created SR': 'TicketCreatedDt_SR',
    'Customer Inc.': 'CustomerName_Inc',
    'Customer SR': 'CustomerName_SR',
}

# Sprint Column Schema (Fallback - prefer config-based column order)
SPRINT_COLUMNS = [
    'SprintNumber',
    'SprintName',
    'SprintStartDt',
    'SprintEndDt',
    'TaskNum',
    'TicketNum',
    'TicketType',
    'Section',
    'Status',
    'AssignedTo',
    'CustomerName',
    'Subject',
    'DaysOpen',
    'TaskAssignedDt',
    'TaskCreatedDt',
    'TaskResolvedDt',
    'TicketCreatedDt',
    'TicketResolvedDt',
    'HoursEstimated',
    'DependencyOn',
    'DependenciesLead',
    'DependencySecured',
    'Comments'
]

# UI Configuration
PAGE_ICON = "📊"
APP_TITLE = "PIBIDS Sprint Dashboard"
ROWS_PER_PAGE = 20

# Colors
COLOR_OVERLOAD = "#ffe6e6"
COLOR_WARNING = "#fff3cd"
COLOR_SUCCESS = "#d4edda"
COLOR_PRIMARY = "#1f77b4"
COLOR_DANGER = "#ff4444"

# Lab Sections Configuration
# Load valid sections from config file
import os
try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Python < 3.11

def load_valid_sections():
    """Load valid lab sections from configuration file"""
    sections_file = ".streamlit/sections.toml"
    if os.path.exists(sections_file):
        try:
            with open(sections_file, 'rb') as f:
                config = tomllib.load(f)
                return config['sections']['valid_sections']
        except Exception:
            pass
    
    # Fallback to hardcoded list if config file not found
    return [
        "LSC - Laboratory Service Center",
        "Micro - Microbiology",
        "CoreLab - Coagulation",
        "PCare",
        "CoreLab - Hematology",
        "HLA",
        "LSC - Outreach Services",
        "PIBIDS",
        "Immunology",
        "CoreLab - Chemistry",
        "LSS - Send out Laboratory",
        "Micro - Molecular Virology",
        "CoreLab - Point of Care",
        "CPM - Molecular",
        "TM - Blood Bank",
        "AP - Anatomic Pathology",
        "LSS - Lab Support Services - MainLab",
        "LSS - Lab Support Services - OPLab",
        "CoreLab - Bone Marrow Lab",
        "CPM - Cytogenetics",
        "CoreLab - Special Chemistry",
        "AP - Biorepository",
        "TM - Donor Center",
        "TM - Therapeutic Apheresis",
    ]

VALID_SECTIONS = load_valid_sections()
DEFAULT_SECTION = "PIBIDS"
