"""
Professional Dashboard Styles
Clean, modern design for project management dashboard
"""
import streamlit as st

# Custom CSS for AgGrid - applied via custom_css parameter
GRID_CUSTOM_CSS = {
    ".ag-tooltip": {
        "background-color": "#2d2d2d !important",
        "color": "#ffffff !important",
        "border": "1px solid #555 !important",
        "border-radius": "4px !important",
        "padding": "8px 12px !important",
        "max-width": "300px !important",
        "font-size": "12px !important",
        "line-height": "1.4 !important",
        "box-shadow": "0 2px 8px rgba(0, 0, 0, 0.3) !important",
        "white-space": "normal !important",
        "word-wrap": "break-word !important",
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
    
    /* AgGrid Tooltip Styling */
    .ag-tooltip,
    .ag-theme-streamlit .ag-tooltip,
    .ag-theme-alpine .ag-tooltip,
    div.ag-tooltip {
        background-color: #2d2d2d !important;
        color: #ffffff !important;
        border: 1px solid #444 !important;
        border-radius: 4px !important;
        padding: 8px 12px !important;
        max-width: 300px !important;
        font-size: 12px !important;
        line-height: 1.4 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
        white-space: normal !important;
        word-wrap: break-word !important;
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
    
    </style>
    """, unsafe_allow_html=True)


def get_custom_css():
    """Return custom CSS dict for AgGrid custom_css parameter"""
    return GRID_CUSTOM_CSS


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
    } else if (status === 'canceled' || status === 'excluded from carryover') {
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
