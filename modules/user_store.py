"""
User Store Module
Manages user accounts for authentication.
"""
import os
import pandas as pd
from typing import Optional, Tuple, List, Dict

# Default storage path
DEFAULT_USERS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.csv')

# Valid roles
# Admin: Full access, can edit everything
# PBIDS User: Read-only, can view all sections but cannot edit
# Section Manager: Can edit CustomerPriority in their section(s)
# Section User: Same as Section Manager (may change later)
VALID_ROLES = ['Admin', 'PBIDS User', 'Section Manager', 'Section User']


class UserStore:
    """Manages user data for authentication"""
    
    def __init__(self, store_path: str = None):
        self.store_path = store_path or DEFAULT_USERS_PATH
        self.users_df = self._load_store()
    
    def _load_store(self) -> pd.DataFrame:
        """Load users from CSV"""
        if not os.path.exists(self.store_path):
            # Create default admin user if no file exists
            df = pd.DataFrame([{
                'Username': 'admin',
                'Password': 'admin123',
                'Role': 'Admin',
                'Section': '',
                'DisplayName': 'Administrator',
                'Active': True
            }])
            self._save_df(df)
            return df
        
        try:
            df = pd.read_csv(self.store_path)
            # Ensure required columns exist
            required_cols = ['Username', 'Password', 'Role', 'Section', 'DisplayName', 'Active']
            for col in required_cols:
                if col not in df.columns:
                    if col == 'Active':
                        df[col] = True  # Default to active for existing users
                    else:
                        df[col] = ''
            return df
        except Exception as e:
            print(f"Error loading user store: {e}")
            return pd.DataFrame(columns=['Username', 'Password', 'Role', 'Section', 'DisplayName', 'Active'])
    
    def _save_df(self, df: pd.DataFrame) -> bool:
        """Save DataFrame to CSV"""
        try:
            os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
            df.to_csv(self.store_path, index=False)
            return True
        except Exception as e:
            print(f"Error saving user store: {e}")
            return False
    
    def save(self) -> bool:
        """Save current users to CSV"""
        return self._save_df(self.users_df)
    
    def reload(self):
        """Reload users from file"""
        self.users_df = self._load_store()
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Authenticate a user.
        
        Returns:
            Tuple of (success, user_info_dict or None)
        """
        if self.users_df.empty:
            return False, None
        
        user_match = self.users_df[
            (self.users_df['Username'] == username) & 
            (self.users_df['Password'] == password)
        ]
        
        if user_match.empty:
            return False, None
        
        user = user_match.iloc[0]
        
        # Check if user is active
        is_active = user.get('Active', True)
        if isinstance(is_active, str):
            is_active = is_active.lower() == 'true'
        if not is_active:
            return False, {'error': 'inactive', 'message': 'Account is inactive. Contact admin.'}
        
        return True, {
            'username': user['Username'],
            'role': user['Role'],
            'section': user['Section'] if pd.notna(user['Section']) else None,
            'display_name': user['DisplayName'] if pd.notna(user['DisplayName']) else user['Username']
        }
    
    def get_all_users(self) -> pd.DataFrame:
        """Get all users (without passwords for display)"""
        if self.users_df.empty:
            return pd.DataFrame()
        
        display_df = self.users_df.copy()
        display_df['Password'] = '********'  # Mask passwords
        return display_df
    
    def get_user(self, username: str) -> Optional[Dict]:
        """Get a specific user by username"""
        if self.users_df.empty:
            return None
        
        user_match = self.users_df[self.users_df['Username'] == username]
        if user_match.empty:
            return None
        
        user = user_match.iloc[0]
        return {
            'username': user['Username'],
            'password': user['Password'],
            'role': user['Role'],
            'section': user['Section'] if pd.notna(user['Section']) else '',
            'display_name': user['DisplayName'] if pd.notna(user['DisplayName']) else ''
        }
    
    def add_user(self, username: str, password: str, role: str, section: str = '', display_name: str = '') -> Tuple[bool, str]:
        """Add a new user"""
        if not username or not password:
            return False, "Username and password are required"
        
        if role not in VALID_ROLES:
            return False, f"Invalid role. Must be one of: {VALID_ROLES}"
        
        # Check if username already exists
        if not self.users_df.empty and username in self.users_df['Username'].values:
            return False, f"Username '{username}' already exists"
        
        new_user = pd.DataFrame([{
            'Username': username,
            'Password': password,
            'Role': role,
            'Section': section,
            'DisplayName': display_name or username,
            'Active': True
        }])
        
        self.users_df = pd.concat([self.users_df, new_user], ignore_index=True)
        
        if self.save():
            return True, "User added successfully"
        return False, "Failed to save user"
    
    def update_user(self, username: str, password: str = None, role: str = None, 
                    section: str = None, display_name: str = None) -> Tuple[bool, str]:
        """Update an existing user"""
        if self.users_df.empty:
            return False, "No users found"
        
        mask = self.users_df['Username'] == username
        if not mask.any():
            return False, f"User '{username}' not found"
        
        if password is not None:
            self.users_df.loc[mask, 'Password'] = password
        if role is not None:
            if role not in VALID_ROLES:
                return False, f"Invalid role. Must be one of: {VALID_ROLES}"
            self.users_df.loc[mask, 'Role'] = role
        if section is not None:
            self.users_df.loc[mask, 'Section'] = section
        if display_name is not None:
            self.users_df.loc[mask, 'DisplayName'] = display_name
        
        if self.save():
            return True, "User updated successfully"
        return False, "Failed to save changes"
    
    def delete_user(self, username: str) -> Tuple[bool, str]:
        """Delete a user"""
        if self.users_df.empty:
            return False, "No users found"
        
        # Prevent deleting the last admin
        admin_count = len(self.users_df[self.users_df['Role'] == 'Admin'])
        user_is_admin = not self.users_df[(self.users_df['Username'] == username) & (self.users_df['Role'] == 'Admin')].empty
        
        if admin_count <= 1 and user_is_admin:
            return False, "Cannot delete the last admin user"
        
        original_len = len(self.users_df)
        self.users_df = self.users_df[self.users_df['Username'] != username]
        
        if len(self.users_df) == original_len:
            return False, f"User '{username}' not found"
        
        if self.save():
            return True, "User deleted successfully"
        return False, "Failed to save changes"
    
    def set_user_active(self, username: str, active: bool) -> Tuple[bool, str]:
        """Set user active/inactive status"""
        if self.users_df.empty:
            return False, "No users found"
        
        mask = self.users_df['Username'] == username
        if not mask.any():
            return False, f"User '{username}' not found"
        
        # Prevent deactivating the last active admin
        if not active:
            user_is_admin = not self.users_df[(self.users_df['Username'] == username) & (self.users_df['Role'] == 'Admin')].empty
            if user_is_admin:
                # Count active admins
                active_admins = self.users_df[(self.users_df['Role'] == 'Admin') & (self.users_df['Active'] == True)]
                if len(active_admins) <= 1:
                    return False, "Cannot deactivate the last active admin user"
        
        self.users_df.loc[mask, 'Active'] = active
        
        if self.save():
            status = "activated" if active else "deactivated"
            return True, f"User {status} successfully"
        return False, "Failed to save changes"
    
    def get_sections(self) -> List[str]:
        """Get list of unique sections"""
        if self.users_df.empty or 'Section' not in self.users_df.columns:
            return []
        
        sections = self.users_df['Section'].dropna().unique().tolist()
        return [s for s in sections if s]


# Singleton instance
_user_store = None

def get_user_store() -> UserStore:
    """Get singleton UserStore instance"""
    global _user_store
    if _user_store is None:
        _user_store = UserStore()
    return _user_store

def reset_user_store():
    """Reset the singleton (useful after changes)"""
    global _user_store
    _user_store = None
