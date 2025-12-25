"""
Admin Configuration Page
Configure sprint calendar and user accounts.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from modules.sprint_calendar import get_sprint_calendar
from modules.user_store import get_user_store, reset_user_store, VALID_ROLES
from components.auth import require_admin, display_user_info

st.set_page_config(
    page_title="Admin Configuration",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ Admin Configuration")
st.caption("_Configure sprint calendar and user accounts — PBIDS Team_")

# Require admin access
require_admin("Admin Configuration")
display_user_info()

# Tabs for different configuration sections
tab1, tab2 = st.tabs(["📅 Sprint Calendar", "👥 User Management"])

# ============================================================================
# SPRINT CALENDAR MANAGEMENT
# ============================================================================
with tab1:
    st.subheader("📅 Sprint Calendar Configuration")
    st.caption("Add, edit, or delete sprints")
    
    calendar = get_sprint_calendar()
    all_sprints = calendar.get_all_sprints()
    
    # Current sprints table
    st.markdown("### Current Sprints")
    
    if all_sprints.empty:
        st.info("No sprints defined yet")
    else:
        # Format dates for display
        display_sprints = all_sprints.copy()
        display_sprints['SprintStartDt'] = pd.to_datetime(display_sprints['SprintStartDt']).dt.strftime('%m/%d/%Y')
        display_sprints['SprintEndDt'] = pd.to_datetime(display_sprints['SprintEndDt']).dt.strftime('%m/%d/%Y')
        
        st.dataframe(
            display_sprints[['SprintNumber', 'SprintName', 'SprintStartDt', 'SprintEndDt']],
            use_container_width=True,
            hide_index=True,
            column_config={
                'SprintNumber': st.column_config.NumberColumn('Sprint #', format='%d'),
                'SprintName': 'Sprint Name',
                'SprintStartDt': 'Start Date',
                'SprintEndDt': 'End Date'
            }
        )
    
    st.divider()
    
    # Add new sprint
    st.markdown("### ➕ Add New Sprint")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Suggest next sprint number
        next_sprint_num = int(all_sprints['SprintNumber'].max()) + 1 if not all_sprints.empty else 1
        new_sprint_num = st.number_input("Sprint Number", min_value=0, value=next_sprint_num, step=1)
        new_sprint_name = st.text_input("Sprint Name", value=f"Sprint {new_sprint_num}")
    
    with col2:
        # Suggest dates based on last sprint
        if not all_sprints.empty:
            last_end = pd.to_datetime(all_sprints.iloc[-1]['SprintEndDt'])
            suggested_start = last_end + timedelta(days=1)
            suggested_end = suggested_start + timedelta(days=13)  # 2-week sprint
        else:
            suggested_start = datetime.now()
            suggested_end = suggested_start + timedelta(days=13)
        
        new_start_date = st.date_input("Start Date", value=suggested_start.date())
        new_end_date = st.date_input("End Date", value=suggested_end.date())
    
    if st.button("➕ Add Sprint", type="primary"):
        if new_sprint_num in all_sprints['SprintNumber'].values if not all_sprints.empty else False:
            st.error(f"Sprint {new_sprint_num} already exists")
        elif new_end_date <= new_start_date:
            st.error("End date must be after start date")
        else:
            # Add to calendar
            new_row = pd.DataFrame([{
                'SprintNumber': new_sprint_num,
                'SprintName': new_sprint_name,
                'SprintStartDt': new_start_date.strftime('%m/%d/%y'),
                'SprintEndDt': new_end_date.strftime('%m/%d/%y')
            }])
            
            updated_sprints = pd.concat([all_sprints, new_row], ignore_index=True)
            updated_sprints = updated_sprints.sort_values('SprintNumber').reset_index(drop=True)
            
            # Save to file
            calendar_path = calendar.calendar_path
            updated_sprints['SprintStartDt'] = pd.to_datetime(updated_sprints['SprintStartDt']).dt.strftime('%m/%d/%y')
            updated_sprints['SprintEndDt'] = pd.to_datetime(updated_sprints['SprintEndDt']).dt.strftime('%m/%d/%y')
            updated_sprints.to_csv(calendar_path, index=False)
            
            st.success(f"✅ Sprint {new_sprint_num} added successfully!")
            st.rerun()
    
    st.divider()
    
    # Edit existing sprint
    st.markdown("### ✏️ Edit Sprint")
    
    if not all_sprints.empty:
        sprint_to_edit = st.selectbox(
            "Select Sprint to Edit",
            options=all_sprints['SprintNumber'].tolist(),
            format_func=lambda x: f"Sprint {x}: {all_sprints[all_sprints['SprintNumber']==x]['SprintName'].iloc[0]}"
        )
        
        if sprint_to_edit is not None:
            sprint_data = all_sprints[all_sprints['SprintNumber'] == sprint_to_edit].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                edit_name = st.text_input("Sprint Name", value=sprint_data['SprintName'], key="edit_name")
            
            with col2:
                edit_start = st.date_input("Start Date", value=pd.to_datetime(sprint_data['SprintStartDt']).date(), key="edit_start")
                edit_end = st.date_input("End Date", value=pd.to_datetime(sprint_data['SprintEndDt']).date(), key="edit_end")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 Save Changes", key="save_sprint"):
                    if edit_end <= edit_start:
                        st.error("End date must be after start date")
                    else:
                        # Update sprint
                        mask = all_sprints['SprintNumber'] == sprint_to_edit
                        all_sprints.loc[mask, 'SprintName'] = edit_name
                        all_sprints.loc[mask, 'SprintStartDt'] = edit_start.strftime('%m/%d/%y')
                        all_sprints.loc[mask, 'SprintEndDt'] = edit_end.strftime('%m/%d/%y')
                        
                        # Save
                        all_sprints.to_csv(calendar.calendar_path, index=False)
                        st.success(f"✅ Sprint {sprint_to_edit} updated!")
                        st.rerun()
            
            with col2:
                if st.button("🗑️ Delete Sprint", key="delete_sprint", type="secondary"):
                    # Check if sprint has tasks
                    from modules.task_store import get_task_store
                    task_store = get_task_store()
                    sprint_tasks = task_store.get_sprint_tasks(sprint_to_edit)
                    
                    if not sprint_tasks.empty:
                        st.error(f"Cannot delete Sprint {sprint_to_edit} - it has {len(sprint_tasks)} tasks assigned")
                    else:
                        all_sprints = all_sprints[all_sprints['SprintNumber'] != sprint_to_edit]
                        all_sprints.to_csv(calendar.calendar_path, index=False)
                        st.success(f"✅ Sprint {sprint_to_edit} deleted!")
                        st.rerun()

# ============================================================================
# USER MANAGEMENT
# ============================================================================
with tab2:
    st.subheader("👥 User Management")
    st.caption("Add, edit, or delete user accounts")
    
    user_store = get_user_store()
    all_users = user_store.get_all_users()
    
    # Current users table
    st.markdown("### Current Users")
    
    if all_users.empty:
        st.info("No users defined yet")
    else:
        st.dataframe(
            all_users[['Username', 'DisplayName', 'Role', 'Section', 'Password']],
            use_container_width=True,
            hide_index=True,
            column_config={
                'Username': 'Username',
                'DisplayName': 'Display Name',
                'Role': 'Role',
                'Section': 'Section',
                'Password': 'Password'
            }
        )
    
    st.divider()
    
    # Add new user
    st.markdown("### ➕ Add New User")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_username = st.text_input("Username", key="new_username")
        new_password = st.text_input("Password", type="password", key="new_password")
        new_password_confirm = st.text_input("Confirm Password", type="password", key="new_password_confirm")
    
    with col2:
        new_display_name = st.text_input("Display Name", key="new_display_name")
        new_role = st.selectbox("Role", options=VALID_ROLES, key="new_role")
        
        # Get existing sections for suggestions
        existing_sections = user_store.get_sections()
        new_section = st.text_input(
            "Section (for Section Users)", 
            key="new_section",
            help=f"Existing sections: {', '.join(existing_sections) if existing_sections else 'None'}"
        )
    
    if st.button("➕ Add User", type="primary"):
        if not new_username:
            st.error("Username is required")
        elif not new_password:
            st.error("Password is required")
        elif new_password != new_password_confirm:
            st.error("Passwords do not match")
        elif new_role == 'Section User' and not new_section:
            st.error("Section is required for Section Users")
        else:
            success, message = user_store.add_user(
                username=new_username,
                password=new_password,
                role=new_role,
                section=new_section,
                display_name=new_display_name or new_username
            )
            
            if success:
                st.success(f"✅ {message}")
                reset_user_store()
                st.rerun()
            else:
                st.error(f"❌ {message}")
    
    st.divider()
    
    # Edit existing user
    st.markdown("### ✏️ Edit User")
    
    if not all_users.empty:
        user_to_edit = st.selectbox(
            "Select User to Edit",
            options=all_users['Username'].tolist(),
            format_func=lambda x: f"{x} ({all_users[all_users['Username']==x]['Role'].iloc[0]})"
        )
        
        if user_to_edit:
            user_data = user_store.get_user(user_to_edit)
            
            if user_data:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.text_input("Username", value=user_to_edit, disabled=True, key="edit_username_display")
                    edit_password = st.text_input(
                        "New Password (leave blank to keep current)", 
                        type="password", 
                        key="edit_password"
                    )
                    edit_display_name = st.text_input(
                        "Display Name", 
                        value=user_data['display_name'], 
                        key="edit_display_name"
                    )
                
                with col2:
                    edit_role = st.selectbox(
                        "Role", 
                        options=VALID_ROLES, 
                        index=VALID_ROLES.index(user_data['role']) if user_data['role'] in VALID_ROLES else 0,
                        key="edit_role"
                    )
                    edit_section = st.text_input(
                        "Section", 
                        value=user_data['section'] or '', 
                        key="edit_section"
                    )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("💾 Save Changes", key="save_user"):
                        success, message = user_store.update_user(
                            username=user_to_edit,
                            password=edit_password if edit_password else None,
                            role=edit_role,
                            section=edit_section,
                            display_name=edit_display_name
                        )
                        
                        if success:
                            st.success(f"✅ {message}")
                            reset_user_store()
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                
                with col2:
                    # Don't allow deleting yourself
                    current_user = st.session_state.get('username')
                    if user_to_edit == current_user:
                        st.button("🗑️ Delete User", disabled=True, help="Cannot delete your own account")
                    else:
                        if st.button("🗑️ Delete User", key="delete_user", type="secondary"):
                            success, message = user_store.delete_user(user_to_edit)
                            
                            if success:
                                st.success(f"✅ {message}")
                                reset_user_store()
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")

# Footer
st.divider()
st.caption("💡 **Note:** Changes to sprint calendar and user accounts take effect immediately.")
