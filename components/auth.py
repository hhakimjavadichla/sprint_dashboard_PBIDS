"""
Authentication helper functions
"""
import streamlit as st
from typing import Tuple, Optional


def check_authentication() -> bool:
    """
    Check if user is authenticated
    
    Returns:
        True if authenticated
    """
    return st.session_state.get('authenticated', False)


def get_user_role() -> Optional[str]:
    """
    Get current user's role
    
    Returns:
        User role ('Admin' or 'Section User') or None
    """
    return st.session_state.get('user_role')


def get_user_section() -> Optional[str]:
    """
    Get current user's section (for Section Users)
    
    Returns:
        Section name or None
    """
    return st.session_state.get('user_section')


def is_admin() -> bool:
    """
    Check if current user is an admin
    
    Returns:
        True if user is admin
    """
    return get_user_role() == 'Admin'


def login(username: str, password: str) -> Tuple[bool, str]:
    """
    Attempt to log in user
    
    Args:
        username: Username
        password: Password
    
    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Try user store first (CSV-based)
        from modules.user_store import get_user_store
        user_store = get_user_store()
        
        success, user_info = user_store.authenticate(username, password)
        
        if success and user_info:
            st.session_state.authenticated = True
            st.session_state.username = user_info['username']
            st.session_state.user_role = user_info['role']
            st.session_state.user_section = user_info['section']
            st.session_state.display_name = user_info['display_name']
            return True, ""
        
        # Fall back to secrets (for backward compatibility)
        credentials = st.secrets.get('credentials', {})
        user_roles = st.secrets.get('user_roles', {})
        user_sections = st.secrets.get('user_sections', {})
        
        if username in credentials and credentials[username] == password:
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.user_role = user_roles.get(username, 'Section User')
            st.session_state.user_section = user_sections.get(username)
            return True, ""
        
        return False, "Invalid username or password"
    
    except Exception as e:
        return False, f"Authentication error: {str(e)}"


def logout():
    """Log out current user"""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.user_role = None
    st.session_state.user_section = None


def require_auth(page_name: str = "page"):
    """
    Decorator/helper to require authentication for a page
    
    Args:
        page_name: Name of page for error message
    
    Returns:
        True if authenticated, stops execution if not
    """
    if not check_authentication():
        st.error(f"🔐 Authentication required to access {page_name}")
        st.info("Please log in from the home page")
        st.stop()
    
    return True


def require_admin(page_name: str = "page"):
    """
    Require admin access for a page
    
    Args:
        page_name: Name of page for error message
    
    Returns:
        True if admin, stops execution if not
    """
    require_auth(page_name)
    
    if not is_admin():
        st.error(f"⛔ Admin access required for {page_name}")
        st.info("This page is restricted to administrators only")
        st.stop()
    
    return True


def display_user_info():
    """Display current user information in sidebar"""
    if check_authentication():
        with st.sidebar:
            st.success(f"👤 {st.session_state.get('username', 'User')}")
            
            role = get_user_role()
            if role:
                st.info(f"🏷️ Role: {role}")
            
            section = get_user_section()
            if section:
                st.info(f"📍 Section: {section}")
            
            st.divider()
            
            if st.button("🚪 Logout", width="stretch"):
                logout()
                st.rerun()


def display_login_form():
    """Display login form"""
    st.markdown("### 🔐 Login")
    
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submit = st.form_submit_button("Login", width="stretch")
        
        if submit:
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                success, error = login(username, password)
                
                if success:
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error(f"❌ {error}")
