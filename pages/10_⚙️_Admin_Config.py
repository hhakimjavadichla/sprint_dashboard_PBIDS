"""
Admin Configuration Page
Configure sprint calendar, user accounts, and team members.
"""
import streamlit as st
import pandas as pd
import toml
from pathlib import Path
from datetime import datetime, timedelta
from modules.sprint_calendar import get_sprint_calendar
from modules.user_store import get_user_store, reset_user_store, VALID_ROLES
from modules.offdays_store import get_offdays_store, reset_offdays_store
from components.auth import require_admin, display_user_info
from utils.constants import VALID_SECTIONS

# Path to itrack mapping config
ITRACK_MAPPING_PATH = Path(__file__).parent.parent / '.streamlit' / 'itrack_mapping.toml'

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
tab1, tab2, tab3, tab4 = st.tabs(["📅 Sprint Calendar", "👥 User Management", "🧑‍💼 Team Members", "🏖️ Off Days"])

# ============================================================================
# SPRINT CALENDAR MANAGEMENT
# ============================================================================
with tab1:
    st.subheader("📅 Sprint Calendar Configuration")
    st.caption("Add or edit sprints")
    
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
                'SprintStartDt': new_start_date,
                'SprintEndDt': new_end_date
            }])
            
            updated_sprints = pd.concat([all_sprints, new_row], ignore_index=True)
            updated_sprints = updated_sprints.sort_values('SprintNumber').reset_index(drop=True)
            
            # Convert ALL dates to consistent format before saving
            updated_sprints['SprintStartDt'] = pd.to_datetime(updated_sprints['SprintStartDt']).dt.strftime('%Y-%m-%d')
            updated_sprints['SprintEndDt'] = pd.to_datetime(updated_sprints['SprintEndDt']).dt.strftime('%Y-%m-%d')
            updated_sprints.to_csv(calendar.calendar_path, index=False)
            
            # Reload calendar to reflect changes
            calendar.reload()
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
                        all_sprints.loc[mask, 'SprintStartDt'] = edit_start
                        all_sprints.loc[mask, 'SprintEndDt'] = edit_end
                        
                        # Convert ALL dates to consistent format before saving
                        save_df = all_sprints.copy()
                        save_df['SprintStartDt'] = pd.to_datetime(save_df['SprintStartDt']).dt.strftime('%Y-%m-%d')
                        save_df['SprintEndDt'] = pd.to_datetime(save_df['SprintEndDt']).dt.strftime('%Y-%m-%d')
                        save_df.to_csv(calendar.calendar_path, index=False)
                        
                        # Reload calendar to reflect changes
                        calendar.reload()
                        st.success(f"✅ Sprint {sprint_to_edit} updated!")
                        st.rerun()
            

# ============================================================================
# USER MANAGEMENT
# ============================================================================
with tab2:
    st.subheader("👥 User Management")
    st.caption("Add or edit user accounts")
    
    user_store = get_user_store()
    all_users = user_store.get_all_users()
    
    # Current users table
    st.markdown("### Current Users")
    
    if all_users.empty:
        st.info("No users defined yet")
    else:
        # Format Active column for display
        display_users = all_users.copy()
        if 'Active' in display_users.columns:
            display_users['Status'] = display_users['Active'].apply(
                lambda x: '✅ Active' if (x == True or x == 'True') else '❌ Inactive'
            )
        else:
            display_users['Status'] = '✅ Active'
        
        st.dataframe(
            display_users[['Username', 'DisplayName', 'Role', 'Section', 'Status']],
            use_container_width=True,
            hide_index=True,
            column_config={
                'Username': 'Username',
                'DisplayName': 'Display Name',
                'Role': 'Role',
                'Section': 'Section',
                'Status': 'Status'
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
        
        # Multi-select dropdown for sections
        new_sections = st.multiselect(
            "Sections (for Section Managers/Users)", 
            options=VALID_SECTIONS,
            key="new_sections",
            help="Select one or more sections this user can monitor and edit (required for Section Manager/User roles)"
        )
        new_section = ','.join(new_sections) if new_sections else ''
    
    if st.button("➕ Add User", type="primary"):
        if not new_username:
            st.error("Username is required")
        elif not new_password:
            st.error("Password is required")
        elif new_password != new_password_confirm:
            st.error("Passwords do not match")
        elif new_role in ['Section Manager', 'Section User'] and not new_sections:
            st.error("At least one section is required for Section Manager/User roles")
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
                    st.text_input("Username", value=user_to_edit, disabled=True, key=f"edit_username_{user_to_edit}")
                    edit_password = st.text_input(
                        "New Password (leave blank to keep current)", 
                        type="password", 
                        key=f"edit_password_{user_to_edit}"
                    )
                    edit_display_name = st.text_input(
                        "Display Name", 
                        value=user_data['display_name'], 
                        key=f"edit_display_name_{user_to_edit}"
                    )
                
                with col2:
                    edit_role = st.selectbox(
                        "Role", 
                        options=VALID_ROLES, 
                        index=VALID_ROLES.index(user_data['role']) if user_data['role'] in VALID_ROLES else 0,
                        key=f"edit_role_{user_to_edit}"
                    )
                    # Parse existing sections (comma-separated)
                    current_sections = [s.strip() for s in (user_data['section'] or '').split(',') if s.strip()]
                    # Filter to only include valid sections
                    current_sections = [s for s in current_sections if s in VALID_SECTIONS]
                    
                    edit_sections = st.multiselect(
                        "Sections (for Section Managers/Users)", 
                        options=VALID_SECTIONS,
                        default=current_sections,
                        key=f"edit_sections_{user_to_edit}",
                        help="Select one or more sections this user can monitor and edit (required for Section Manager/User roles)"
                    )
                    edit_section = ','.join(edit_sections) if edit_sections else ''
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("💾 Save Changes", key="save_user"):
                        # Validate sections for Section Manager/User roles
                        if edit_role in ['Section Manager', 'Section User'] and not edit_sections:
                            st.error("At least one section is required for Section Manager/User roles")
                        else:
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
                
                # Activate/Deactivate user
                current_user = st.session_state.get('username')
                st.divider()
                
                # Get current active status
                user_active = all_users[all_users['Username'] == user_to_edit]['Active'].iloc[0]
                if isinstance(user_active, str):
                    user_active = user_active.lower() == 'true'
                
                col1, col2 = st.columns(2)
                with col1:
                    if user_to_edit == current_user:
                        st.info("Cannot change your own account status")
                    elif user_active:
                        if st.button("🚫 Deactivate User", key="deactivate_user", type="secondary"):
                            success, message = user_store.set_user_active(user_to_edit, False)
                            if success:
                                st.success(f"✅ {message}")
                                reset_user_store()
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
                    else:
                        if st.button("✅ Activate User", key="activate_user", type="primary"):
                            success, message = user_store.set_user_active(user_to_edit, True)
                            if success:
                                st.success(f"✅ {message}")
                                reset_user_store()
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
                
                with col2:
                    if user_active:
                        st.caption("User can log in")
                    else:
                        st.caption("⚠️ User cannot log in (inactive)")

# ============================================================================
# TEAM MEMBERS MANAGEMENT
# ============================================================================
with tab3:
    st.subheader("🧑‍💼 Team Members Management")
    st.caption("Manage team members whose tasks appear in the dashboard")
    
    # Load current configuration
    def load_itrack_config():
        """Load the itrack mapping configuration."""
        if ITRACK_MAPPING_PATH.exists():
            with open(ITRACK_MAPPING_PATH, 'r') as f:
                return toml.load(f)
        return {}
    
    def save_itrack_config(config):
        """Save the itrack mapping configuration."""
        with open(ITRACK_MAPPING_PATH, 'w') as f:
            toml.dump(config, f)
    
    config = load_itrack_config()
    
    # Get current team members and name mappings
    team_members = config.get('team_members', {}).get('valid_team_members', [])
    inactive_members = config.get('team_members', {}).get('inactive_team_members', [])
    name_mapping = config.get('name_mapping', {})
    
    # Create DataFrame for display
    team_data = []
    for username in team_members:
        display_name = name_mapping.get(username, '')
        is_active = username not in inactive_members
        team_data.append({
            'Username': username,
            'Display Name': display_name,
            'Active': is_active
        })
    
    team_df = pd.DataFrame(team_data) if team_data else pd.DataFrame(columns=['Username', 'Display Name', 'Active'])
    
    # Current team members table
    st.markdown("### Current Team Members")
    st.caption(f"Total: {len(team_members)} team members")
    
    if team_df.empty:
        st.info("No team members defined yet")
    else:
        st.dataframe(
            team_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Username': st.column_config.TextColumn('Username (iTrack Account)', width='medium'),
                'Display Name': st.column_config.TextColumn('Display Name', width='large'),
                'Active': st.column_config.CheckboxColumn('Active', width='small')
            }
        )
    
    st.divider()
    
    # Add new team member
    st.markdown("### ➕ Add New Team Member")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_member_username = st.text_input(
            "Username (iTrack Account)", 
            key="new_member_username",
            help="The iTrack account username (e.g., 'jsmith')"
        )
    
    with col2:
        new_member_display = st.text_input(
            "Display Name", 
            key="new_member_display",
            help="Full name to display in reports (e.g., 'John Smith')"
        )
    
    if st.button("➕ Add Team Member", type="primary", key="add_member"):
        if not new_member_username:
            st.error("Username is required")
        elif new_member_username in team_members:
            st.error(f"Team member '{new_member_username}' already exists")
        else:
            # Add to team members list
            team_members.append(new_member_username)
            config['team_members']['valid_team_members'] = team_members
            
            # Add name mapping if provided
            if new_member_display:
                if 'name_mapping' not in config:
                    config['name_mapping'] = {}
                config['name_mapping'][new_member_username] = new_member_display
            
            # Save config
            save_itrack_config(config)
            st.success(f"✅ Team member '{new_member_username}' added successfully!")
            st.rerun()
    
    st.divider()
    
    # Activate/Deactivate team member
    st.markdown("### 🔄 Activate/Deactivate Team Member")
    
    if team_members:
        # Get inactive members list
        inactive_members = config.get('team_members', {}).get('inactive_team_members', [])
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            member_to_toggle = st.selectbox(
                "Select Team Member",
                options=team_members,
                format_func=lambda x: f"{x} ({name_mapping.get(x, 'No display name')}) - {'Inactive' if x in inactive_members else 'Active'}"
            )
        
        with col2:
            st.write("")  # Spacing
            st.write("")  # Spacing
            is_inactive = member_to_toggle in inactive_members
            if is_inactive:
                if st.button("✅ Activate", key="activate_member", type="primary"):
                    inactive_members.remove(member_to_toggle)
                    config['team_members']['inactive_team_members'] = inactive_members
                    save_itrack_config(config)
                    st.success(f"✅ Team member '{member_to_toggle}' activated!")
                    st.rerun()
            else:
                if st.button("🚫 Deactivate", key="deactivate_member", type="secondary"):
                    inactive_members.append(member_to_toggle)
                    config['team_members']['inactive_team_members'] = inactive_members
                    save_itrack_config(config)
                    st.success(f"✅ Team member '{member_to_toggle}' deactivated!")
                    st.rerun()
    else:
        st.info("No team members available.")
    
    st.divider()
    
    # Bulk edit section
    st.markdown("### ✏️ Edit Display Names")
    st.caption("Edit display names in the table below")
    
    # Create editable dataframe
    if not team_df.empty:
        edited_df = st.data_editor(
            team_df,
            use_container_width=True,
            hide_index=True,
            disabled=['Username'],  # Username is read-only
            column_config={
                'Username': st.column_config.TextColumn('Username (iTrack Account)', width='medium'),
                'Display Name': st.column_config.TextColumn('Display Name', width='large')
            },
            key="bulk_edit_members"
        )
        
        if st.button("💾 Save All Changes", key="save_bulk", type="primary"):
            # Update name mappings from edited dataframe
            if 'name_mapping' not in config:
                config['name_mapping'] = {}
            
            for _, row in edited_df.iterrows():
                username = row['Username']
                display_name = row['Display Name']
                
                if display_name:
                    config['name_mapping'][username] = display_name
                elif username in config['name_mapping']:
                    del config['name_mapping'][username]
            
            save_itrack_config(config)
            st.success("✅ All display names updated!")
            st.rerun()
    else:
        st.info("No team members to edit.")

# ============================================================================
# OFF DAYS MANAGEMENT
# ============================================================================
with tab4:
    st.subheader("🏖️ Team Member Off Days")
    st.caption("Configure off days for team members during sprints")
    
    # Load data
    offdays_store = get_offdays_store()
    calendar = get_sprint_calendar()
    all_sprints = calendar.get_all_sprints()
    
    # Load team members from itrack config
    def load_team_members_for_offdays():
        if ITRACK_MAPPING_PATH.exists():
            with open(ITRACK_MAPPING_PATH, 'r') as f:
                config = toml.load(f)
            members = config.get('team_members', {}).get('valid_team_members', [])
            inactive = config.get('team_members', {}).get('inactive_team_members', [])
            name_mapping = config.get('name_mapping', {})
            # Only return active members
            active_members = [m for m in members if m not in inactive]
            return active_members, name_mapping
        return [], {}
    
    team_members, name_mapping = load_team_members_for_offdays()
    
    if all_sprints.empty:
        st.warning("No sprints configured. Please add sprints first.")
    elif not team_members:
        st.warning("No active team members. Please add team members first.")
    else:
        # Sprint selector
        sprint_options = all_sprints['SprintNumber'].tolist()
        current_sprint = calendar.get_current_sprint()
        default_sprint_idx = 0
        if current_sprint is not None:
            try:
                default_sprint_idx = sprint_options.index(int(current_sprint['SprintNumber']))
            except ValueError:
                pass
        
        selected_sprint = st.selectbox(
            "Select Sprint",
            options=sprint_options,
            index=default_sprint_idx,
            format_func=lambda x: f"Sprint {x} ({all_sprints[all_sprints['SprintNumber']==x]['SprintName'].iloc[0]})"
        )
        
        # Get sprint date range
        sprint_info = calendar.get_sprint_by_number(selected_sprint)
        if sprint_info:
            sprint_start = pd.to_datetime(sprint_info['SprintStartDt'])
            sprint_end = pd.to_datetime(sprint_info['SprintEndDt'])
            st.info(f"**Sprint {selected_sprint}**: {sprint_info['SprintStartDt']} - {sprint_info['SprintEndDt']}")
            
            # Generate list of dates in the sprint (weekdays only)
            sprint_dates = pd.date_range(start=sprint_start, end=sprint_end, freq='B')  # Business days
            sprint_date_strs = [d.strftime('%Y-%m-%d') for d in sprint_dates]
        
        st.divider()
        
        # Availability Grid - checkbox table
        st.markdown("### 📅 Team Availability Grid")
        st.caption("✅ = Working day (checked) | ⬜ = Off day (unchecked). Uncheck dates when team members are off.")
        
        if sprint_info and sprint_date_strs:
            # Get current off days for this sprint
            sprint_offdays = offdays_store.get_offdays_for_sprint(selected_sprint)
            current_offdays = {}
            for _, row in sprint_offdays.iterrows():
                username = row['Username']
                off_date = row['OffDate']
                if username not in current_offdays:
                    current_offdays[username] = set()
                current_offdays[username].add(off_date)
            
            # Build availability grid data
            # Rows = team members, Columns = dates
            # True = working (available), False = off day
            grid_data = []
            for member in team_members:
                display_name = name_mapping.get(member, member)
                row_data = {'Team Member': display_name, '_username': member}
                member_offdays = current_offdays.get(member, set())
                for date_str in sprint_date_strs:
                    # Column name is formatted date
                    col_name = pd.to_datetime(date_str).strftime('%m/%d\n%a')
                    # True if NOT an off day (working), False if off day
                    row_data[col_name] = date_str not in member_offdays
                grid_data.append(row_data)
            
            grid_df = pd.DataFrame(grid_data)
            
            # Create column config for checkboxes
            date_columns = [c for c in grid_df.columns if c not in ['Team Member', '_username']]
            column_config = {
                'Team Member': st.column_config.TextColumn('Team Member', width='medium', disabled=True),
                '_username': None  # Hide username column
            }
            for col in date_columns:
                column_config[col] = st.column_config.CheckboxColumn(col, width='small')
            
            # Display editable grid
            edited_grid = st.data_editor(
                grid_df,
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                key=f"offdays_grid_{selected_sprint}"
            )
            
            # Save button
            if st.button("💾 Save Availability Changes", type="primary", key="save_offdays"):
                admin_user = st.session_state.get('username', 'admin')
                changes_made = 0
                
                for idx, row in edited_grid.iterrows():
                    username = row['_username']
                    member_offdays = current_offdays.get(username, set())
                    
                    for date_str in sprint_date_strs:
                        col_name = pd.to_datetime(date_str).strftime('%m/%d\n%a')
                        is_working = row[col_name]
                        was_off = date_str in member_offdays
                        
                        if is_working and was_off:
                            # Was off, now working - remove off day
                            offdays_store.remove_offday(username, selected_sprint, date_str)
                            changes_made += 1
                        elif not is_working and not was_off:
                            # Was working, now off - add off day
                            offdays_store.add_offday(
                                username=username,
                                sprint_number=selected_sprint,
                                off_date=date_str,
                                reason='',
                                created_by=admin_user
                            )
                            changes_made += 1
                
                if changes_made > 0:
                    reset_offdays_store()
                    st.success(f"✅ Saved {changes_made} availability change(s)")
                    st.rerun()
                else:
                    st.info("No changes to save")
        
        # Summary by team member
        st.divider()
        st.markdown(f"### 📊 Off Days Summary for Sprint {selected_sprint}")
        
        if sprint_info:
            total_business_days = len(sprint_date_strs) if sprint_date_strs else 0
            
            summary_data = []
            for member in team_members:
                display_name = name_mapping.get(member, member)
                off_count = offdays_store.get_offday_count(member, selected_sprint)
                available_days = total_business_days - off_count
                available_hours = available_days * 8  # Assuming 8 hours per day
                
                summary_data.append({
                    'Username': member,
                    'Display Name': display_name,
                    'Total Days': total_business_days,
                    'Off Days': off_count,
                    'Available Days': available_days,
                    'Available Hours': available_hours
                })
            
            summary_df = pd.DataFrame(summary_data)
            
            # Only show members with off days or show all
            show_all = st.checkbox("Show all team members", value=False)
            if not show_all:
                summary_df = summary_df[summary_df['Off Days'] > 0]
            
            if summary_df.empty:
                st.info("No off days configured for any team member in this sprint.")
            else:
                st.dataframe(
                    summary_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'Available Hours': st.column_config.NumberColumn('Available Hours', format='%.0f hrs')
                    }
                )

# Footer
st.divider()
st.caption("💡 **Note:** Changes to sprint calendar, user accounts, team members, and off days take effect immediately.")
