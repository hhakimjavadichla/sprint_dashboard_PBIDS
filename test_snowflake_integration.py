#!/usr/bin/env python3
"""
Test script to verify Snowflake integration with the three iTrack tables.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("=" * 60)
    print("SNOWFLAKE INTEGRATION TEST")
    print("=" * 60)
    
    # Test 1: Check Snowflake configuration
    print("\n[1] Checking Snowflake configuration...")
    from modules.snowflake_connector import is_snowflake_configured, is_snowflake_enabled
    
    configured = is_snowflake_configured()
    enabled = is_snowflake_enabled()
    
    print(f"    Configured: {configured}")
    print(f"    Enabled: {enabled}")
    
    if not configured:
        print("    ❌ Snowflake not configured. Check secrets.toml")
        return
    
    # Test 2: Fetch tasks from Snowflake
    print("\n[2] Fetching tasks from Snowflake...")
    from modules.snowflake_connector import fetch_tasks_from_snowflake
    
    tasks_df, success, message = fetch_tasks_from_snowflake()
    print(f"    Result: {message}")
    
    if success:
        print(f"    ✅ Loaded {len(tasks_df)} tasks")
        print(f"    Columns: {list(tasks_df.columns)}")
        
        # Check TicketType distribution would be calculated later
        if not tasks_df.empty:
            print(f"\n    Sample data (first 3 rows):")
            print(tasks_df[['TaskNum', 'Status', 'Subject', 'AssignedTo']].head(3).to_string(index=False))
    else:
        print(f"    ❌ Failed: {message}")
    
    # Test 3: Fetch worklogs from Snowflake
    print("\n[3] Fetching worklogs from Snowflake...")
    from modules.snowflake_connector import fetch_worklogs_from_snowflake
    
    worklogs_df, success, message = fetch_worklogs_from_snowflake()
    print(f"    Result: {message}")
    
    if success:
        print(f"    ✅ Loaded {len(worklogs_df)} worklog entries")
        print(f"    Columns: {list(worklogs_df.columns)}")
        
        if not worklogs_df.empty:
            print(f"\n    Sample data (first 3 rows):")
            print(worklogs_df[['TaskNum', 'Owner', 'LogDate', 'MinutesSpent']].head(3).to_string(index=False))
    else:
        print(f"    ❌ Failed: {message}")
    
    # Test 4: Test TaskStore with Snowflake mode
    print("\n[4] Testing TaskStore with Snowflake mode...")
    from modules.task_store import TaskStore
    
    # Force Snowflake mode for testing
    store = TaskStore(use_snowflake=True)
    
    if not store.tasks_df.empty:
        print(f"    ✅ TaskStore loaded {len(store.tasks_df)} tasks")
        
        # Check TicketType extraction
        if 'TicketType' in store.tasks_df.columns:
            type_counts = store.tasks_df['TicketType'].value_counts().to_dict()
            print(f"    TicketType distribution: {type_counts}")
        
        # Check DaysOpen calculation
        if 'DaysOpen' in store.tasks_df.columns:
            avg_days = store.tasks_df['DaysOpen'].mean()
            print(f"    Average DaysOpen: {avg_days:.1f}")
    else:
        print("    ⚠️ TaskStore returned empty DataFrame")
    
    # Test 5: Test WorklogStore with Snowflake mode
    print("\n[5] Testing WorklogStore with Snowflake mode...")
    from modules.worklog_store import WorklogStore
    
    # Force Snowflake mode for testing
    worklog_store = WorklogStore(use_snowflake=True)
    
    if not worklog_store.worklog_df.empty:
        print(f"    ✅ WorklogStore loaded {len(worklog_store.worklog_df)} entries")
    else:
        print("    ⚠️ WorklogStore returned empty DataFrame")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
