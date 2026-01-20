#!/usr/bin/env python3
"""
Test script to verify Snowflake table joins work correctly.
Run this before implementing the full Snowflake integration.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.snowflake_connector import test_table_joins, is_snowflake_configured

def main():
    print("=" * 60)
    print("SNOWFLAKE TABLE JOIN TEST")
    print("=" * 60)
    
    # Check if Snowflake is configured
    if not is_snowflake_configured():
        print("❌ Snowflake is not configured. Please check secrets.toml")
        return
    
    print("✅ Snowflake is configured. Running join tests...\n")
    
    # Run the join tests
    results, success, message = test_table_joins()
    
    if not success:
        print(f"❌ Test failed: {message}")
        return
    
    print(f"✅ {message}\n")
    
    # Display results
    print("-" * 60)
    print("TABLE RECORD COUNTS")
    print("-" * 60)
    print(f"  DS_VW_ITRACK_LPM_TASK:     {results['task_count']:,} records")
    print(f"  DS_VW_ITRACK_LPM_INCIDENT: {results['incident_count']:,} records")
    print(f"  DS_VW_ITRACK_LPM_WORKLOG:  {results['worklog_count']:,} records")
    
    print("\n" + "-" * 60)
    print("JOIN TEST RESULTS")
    print("-" * 60)
    
    # Task-Incident join
    print("\n📋 Task → Incident Join (PARENTOBJECTDISPLAYID = INCIDENTNUMBER)")
    print(f"   Matched: {results['task_incident_join_count']:,} / {results['task_count']:,} tasks")
    print(f"   Match Rate: {results['task_incident_match_rate']:.1f}%")
    if results['task_incident_match_rate'] >= 95:
        print("   ✅ GOOD - High match rate")
    elif results['task_incident_match_rate'] >= 80:
        print("   ⚠️ WARNING - Some tasks don't have matching incidents")
    else:
        print("   ❌ PROBLEM - Low match rate, join key may be incorrect")
    
    # Worklog-Task join
    print("\n📝 Worklog → Task Join (PARENTLINK_RECID = RECID)")
    print(f"   Matched: {results['worklog_task_join_count']:,} / {results['worklog_count']:,} worklogs")
    print(f"   Match Rate: {results['worklog_task_match_rate']:.1f}%")
    if results['worklog_task_match_rate'] >= 95:
        print("   ✅ GOOD - High match rate")
    elif results['worklog_task_match_rate'] >= 80:
        print("   ⚠️ WARNING - Some worklogs don't have matching tasks")
    else:
        print("   ❌ PROBLEM - Low match rate, join key may be incorrect")
    
    # Sample data
    print("\n" + "-" * 60)
    print("SAMPLE JOINED TASK DATA (LAB PATH INFORMATICS)")
    print("-" * 60)
    if results['sample_joined_tasks'] is not None and len(results['sample_joined_tasks']) > 0:
        print(results['sample_joined_tasks'].to_string(index=False))
    else:
        print("   No sample data returned")
    
    print("\n" + "-" * 60)
    print("SAMPLE JOINED WORKLOG DATA (LAB PATH INFORMATICS)")
    print("-" * 60)
    if results['sample_joined_worklogs'] is not None and len(results['sample_joined_worklogs']) > 0:
        print(results['sample_joined_worklogs'].to_string(index=False))
    else:
        print("   No sample data returned")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
