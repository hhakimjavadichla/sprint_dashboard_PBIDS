"""
PBIDS Sprint Workflow Dashboard - PROTOTYPE
Developed by the PBIDS Team for internal testing
This is NOT a production system
"""
import streamlit as st
from components.auth import check_authentication, display_login_form, display_user_info, is_admin

# Page configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="PBIDS Sprint Dashboard (Prototype)",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Check if user is authenticated
if not check_authentication():
    # Show login page
    st.markdown("## 🧪 PBIDS Sprint Dashboard")
    st.caption("**PROTOTYPE** - Developed by PBIDS Team")
    
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
    
    st.stop()

# User is authenticated - show navigation
# Define pages for navigation
overview_page = st.Page("pages/1_📊_Overview.py", title="Overview", icon="📊")

# Lab Section View pages
sprint_prioritization = st.Page("pages/2_Lab_Section_View/1_📋_Sprint_Prioritization.py", title="Sprint Prioritization", icon="📋")
sprint_feedback = st.Page("pages/2_Lab_Section_View/2_💬_Sprint_Feedback.py", title="Sprint Feedback", icon="💬")

analytics_page = st.Page("pages/3_📈_Analytics.py", title="Analytics", icon="📈")

# PIBIDS Sprint Planning pages
sprint_update = st.Page("pages/4_PIBIDS_Sprint_Planning/1_✏️_Sprint_Update.py", title="Sprint Update", icon="✏️")
backlog_assign = st.Page("pages/4_PIBIDS_Sprint_Planning/2_📋_Backlog_Assign.py", title="Backlog Assign", icon="📋")

worklog_page = st.Page("pages/5_📊_Worklog_Activity.py", title="Worklog Activity", icon="📊")
admin_page = st.Page("pages/6_⚙️_Admin_Config.py", title="Admin Config", icon="⚙️")
upload_page = st.Page("pages/7_📤_Upload_Tasks.py", title="Data Source", icon="📤")
feature_requests_page = st.Page("pages/8_📝_Feature_Requests.py", title="Feature Requests", icon="📝")

# Create navigation with sections based on user role
nav_sections = {
    "Dashboard": [overview_page, analytics_page],
    "Lab Section View": [sprint_prioritization, sprint_feedback],
    "PIBIDS Sprint Planning": [sprint_update, backlog_assign],
}

# Admin-only pages
if is_admin():
    nav_sections["Admin"] = [worklog_page, admin_page, upload_page, feature_requests_page]

pg = st.navigation(nav_sections)

# Run the selected page
pg.run()
