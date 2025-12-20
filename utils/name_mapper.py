"""
Name Mapper Utility
Maps iTrack account names to display names using config
"""
import os
import pandas as pd
from typing import Optional, Dict
from functools import lru_cache

try:
    import tomllib  # Python 3.11+
except ImportError:
    import toml as tomllib  # Fallback for older Python

# Config file path
CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    '.streamlit',
    'itrack_mapping.toml'
)


@lru_cache(maxsize=1)
def load_name_mapping() -> Dict[str, str]:
    """
    Load name mapping from config file.
    Returns a dict mapping account names to display names.
    """
    try:
        # Try Python 3.11+ tomllib (binary mode)
        if hasattr(tomllib, 'load'):
            try:
                with open(CONFIG_PATH, 'rb') as f:
                    config = tomllib.load(f)
            except TypeError:
                # Fallback to toml (text mode)
                with open(CONFIG_PATH, 'r') as f:
                    config = tomllib.load(f)
        else:
            # toml package uses text mode
            with open(CONFIG_PATH, 'r') as f:
                config = tomllib.load(f)
        return config.get('name_mapping', {})
    except Exception:
        return {}


def get_display_name(account_name: Optional[str]) -> str:
    """
    Get display name for an account name.
    Returns the mapped display name if available, otherwise returns the original name.
    
    Args:
        account_name: The iTrack account name (username)
    
    Returns:
        The display name if mapped, otherwise the original account name
    """
    if not account_name or pd.isna(account_name):
        return 'Unassigned'
    
    name_map = load_name_mapping()
    
    # Try exact match first
    if account_name in name_map:
        return name_map[account_name]
    
    # Try lowercase match
    account_lower = str(account_name).lower()
    for key, value in name_map.items():
        if key.lower() == account_lower:
            return value
    
    # No mapping found, return original
    return str(account_name)


def apply_name_mapping(df: pd.DataFrame, column: str = 'AssignedTo') -> pd.DataFrame:
    """
    Apply name mapping to a DataFrame column.
    Creates a new column with '_Display' suffix containing the mapped names.
    
    Args:
        df: DataFrame to process
        column: Column name containing account names (default: 'AssignedTo')
    
    Returns:
        DataFrame with new display name column
    """
    if df.empty or column not in df.columns:
        return df
    
    df = df.copy()
    display_col = f"{column}_Display"
    df[display_col] = df[column].apply(get_display_name)
    
    return df


def get_all_mapped_names() -> Dict[str, str]:
    """
    Get all configured name mappings.
    
    Returns:
        Dictionary of account_name -> display_name
    """
    return load_name_mapping()


def clear_name_cache():
    """Clear the cached name mapping (call after config changes)"""
    load_name_mapping.cache_clear()
