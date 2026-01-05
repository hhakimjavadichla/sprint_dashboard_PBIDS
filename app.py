"""
PBIDS Sprint Workflow Dashboard - PROTOTYPE
Developed by the PBIDS Team for internal testing
This is NOT a production system
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from modules.task_store import get_task_store
from modules.sprint_calendar import get_sprint_calendar
from components.auth import (
    check_authentication,
    display_login_form,
    display_user_info,
    get_user_role
)
from components.metrics_dashboard import display_sprint_overview
from utils.date_utils import get_days_remaining_in_sprint

# Page configuration
st.set_page_config(
    page_title="PBIDS Sprint Dashboard (Prototype)",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .overload-warning {
        background-color: #ffe6e6;
        border-left: 4px solid #ff4444;
    }
    .at-risk-row {
        background-color: #fff3cd;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'user_section' not in st.session_state:
    st.session_state.user_section = None
if 'username' not in st.session_state:
    st.session_state.username = None

# Sidebar
with st.sidebar:
    st.markdown("### 🧪 PBIDS Sprint Dashboard")
    st.caption("**PROTOTYPE** - Developed by PBIDS Team")
    st.caption("_For internal testing only_")
    
    # User info
    display_user_info()
    
    # Current sprint info
    if check_authentication():
        st.divider()
        st.markdown("### Current Sprint")
        
        try:
            data_loader = DataLoader()
            current_sprint = data_loader.load_current_sprint()
            
            if current_sprint is not None and not current_sprint.empty:
                sprint_num = current_sprint['SprintNumber'].iloc[0]
                sprint_name = current_sprint.get('SprintName', pd.Series([f"Sprint {sprint_num}"])).iloc[0]
                sprint_start = current_sprint['SprintStartDt'].iloc[0]
                sprint_end = current_sprint['SprintEndDt'].iloc[0]
                
                st.metric("Sprint", f"#{sprint_num}")
                st.caption(f"**{sprint_name}**")
                st.caption(f"📅 {pd.to_datetime(sprint_start).strftime('%Y-%m-%d')} to {pd.to_datetime(sprint_end).strftime('%Y-%m-%d')}")
                
                # Days remaining
                days_remaining = get_days_remaining_in_sprint(pd.to_datetime(sprint_end))
                if days_remaining > 0:
                    st.info(f"⏳ {days_remaining} days remaining")
                else:
                    st.warning("⏰ Sprint ended")
            else:
                st.caption("No active sprint")
        except Exception as e:
            st.caption("Unable to load sprint info")

# Main content
st.markdown('<div class="main-header">PBIDS Sprint Dashboard</div>', unsafe_allow_html=True)
st.caption("_Prototype — PBIDS Team_")

# Check authentication
if not check_authentication():
    st.markdown("### Welcome")
    
    st.markdown("""
    This prototype explores sprint workflow management for the PBIDS team.
    
    **Features:** Sprint generation · TAT monitoring · Capacity tracking · Progress visibility · Section views
    
    **Access Levels:** Admin (full access) · Section User (read-only)
    """)
    
    st.divider()
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        display_login_form()
    
    with col2:
        st.markdown("### Test Credentials")
        st.markdown("""
        **Admin:**
        - `admin` / `admin123`
        
        **Section Users:**
        - `testuser` / `test123` (CoreLab - Chemistry)
        - `corelab` / `corelab123` (CoreLab - Hematology)
        - `micro` / `micro123` (Micro - Microbiology)
        - `multiuser` / `multi123` (Multi-section: Micro + CPM)
        """)

else:
    # Authenticated home page
    st.markdown(f"### Welcome, {st.session_state.username}")
    
    role = get_user_role()
    if role == 'Admin':
        st.caption("Admin access")
    else:
        st.caption(f"Section User ({st.session_state.user_section})")
    
    st.divider()
    
    # Load and display current sprint overview
    try:
        task_store = get_task_store()
        calendar = get_sprint_calendar()
        current_sprint = task_store.get_current_sprint_tasks()
        current_sprint_info = calendar.get_current_sprint()
        
        if current_sprint is not None and not current_sprint.empty:
            st.subheader("📊 Current Sprint Overview")
            display_sprint_overview(current_sprint)
            
            st.divider()
            st.subheader("📋 Recent Tasks")
            
            # Show top 5 recent tasks
            recent_tasks = current_sprint.sort_values('DaysOpen', ascending=False).head(5)
            
            display_cols = ['TaskNum', 'Subject', 'Status', 'AssignedTo', 'CustomerPriority', 'DaysOpen']
            available_cols = [col for col in display_cols if col in recent_tasks.columns]
            
            st.dataframe(
                recent_tasks[available_cols],
                width="stretch",
                hide_index=True
            )
        
        else:
            st.warning("⚠️ No active sprint found")
            
            if role == 'Admin':
                st.info("👉 Go to **Upload Tasks** page to import your first tasks")
                st.page_link("pages/2_📤_Upload_Tasks.py", label="📤 Upload Tasks", icon="📤")
            else:
                st.info("No sprint data available. Please contact an administrator.")
    
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")
        st.exception(e)
    
    # Help section
    with st.expander("ℹ️ Need Help?"):
        st.markdown("""
        **Getting Started:**
        1. **Admins**: Upload iTrack CSV - tasks auto-assign to sprints
        2. **View**: See current sprint with all carryover tasks
        3. **Update**: Close tasks with status + date to control positioning
        4. **Section Users**: View filtered tasks for your section
        
        **Support:**
        - For technical issues, contact IT support
        - For sprint planning questions, contact your admin
        """)

# Footer
st.divider()
st.caption("PIBIDS Sprint Workflow Dashboard © 2025 | Children's Hospital Los Angeles")
