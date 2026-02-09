"""
PIBIDS Sprint Workflow Dashboard - PROTOTYPE
Developed by the PIBIDS Team for internal testing
This is NOT a production system
"""
import streamlit as st
from components.auth import check_authentication, display_login_form, display_user_info, is_admin

# Page configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="PIBIDS Sprint Dashboard (Prototype)",
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
    st.markdown("## 🧪 PIBIDS Sprint Dashboard")
    st.caption("**PROTOTYPE** - Developed by PIBIDS Team")
    
    st.markdown("### Welcome")
    st.markdown("""
    This prototype explores sprint workflow management for the PIBIDS team.
    
    **Features:** Sprint generation · TAT monitoring · Capacity tracking · Progress visibility · Section views
    
    **Access Levels:** Admin (full access) · Section User (read-only)
    """)
    
    st.divider()
    
    display_login_form()
    
    st.stop()

# User is authenticated - show navigation
# Define pages for navigation
overview_page = st.Page("pages/1_Overview.py", title="Overview")

# Lab Section View pages
sprint_overview = st.Page("pages/2_Lab_Section_View/1_Sprint_Overview.py", title="Sprint Overview")
sprint_prioritization = st.Page("pages/2_Lab_Section_View/2_Sprint_Prioritization.py", title="Sprint Prioritization")
sprint_feedback = st.Page("pages/2_Lab_Section_View/3_Sprint_Feedback.py", title="Sprint Feedback")


# PIBIDS Sprint Planning pages (order: Backlog Assign, Sprint Update, Worklog Activity)
backlog_assign = st.Page("pages/4_PIBIDS_Sprint_Planning/1_Backlog_Assign.py", title="Backlog Assign")
sprint_update = st.Page("pages/4_PIBIDS_Sprint_Planning/2_Sprint_Update.py", title="Sprint Update")
worklog_page = st.Page("pages/4_PIBIDS_Sprint_Planning/3_Worklog_Activity.py", title="Worklog Activity")
admin_page = st.Page("pages/6_Admin_Config.py", title="Admin Config")
upload_page = st.Page("pages/7_Data_Source.py", title="Data Source")
feature_requests_page = st.Page("pages/8_Feature_Requests.py", title="Feature Requests")
reports_analytics_page = st.Page("pages/9_Reports_Analytics.py", title="Reports & Analytics")

# Create navigation with sections based on user role
nav_sections = {
    "Dashboard": [overview_page],
    "Lab Section View": [sprint_overview, sprint_prioritization, sprint_feedback],
    "PIBIDS Sprint Planning": [backlog_assign, sprint_update, worklog_page],
    "Under Construction": [reports_analytics_page],
}

# Admin-only pages
if is_admin():
    nav_sections["Admin"] = [admin_page, upload_page, feature_requests_page]

pg = st.navigation(nav_sections)

# Run the selected page
pg.run()
