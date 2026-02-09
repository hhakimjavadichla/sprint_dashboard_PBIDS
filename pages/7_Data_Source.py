"""
Upload Tasks Page
Data source management - Snowflake connection or CSV import.
Also supports worklog import for activity tracking.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from modules.data_loader import DataLoader
from modules.task_store import get_task_store, reset_task_store, CLOSED_STATUSES
from modules.sprint_calendar import get_sprint_calendar, format_sprint_display
from modules.worklog_store import get_worklog_store, reset_worklog_store
from modules.snowflake_connector import (
    is_snowflake_configured,
    is_snowflake_enabled,
    test_snowflake_connection,
    get_last_refresh_time,
    refresh_snowflake_data,
    refresh_snowflake_worklogs,
    fetch_worklogs_from_snowflake,
    CACHE_TTL_SECONDS,
    list_tables,
    describe_table,
    preview_table,
    get_table_row_count,
    get_column_values,
    get_snowflake_config
)
from components.auth import require_admin, display_user_info

st.title("Data Source")

# Require admin access
require_admin("Data Source")
display_user_info()

# Load modules
data_loader = DataLoader()
task_store = get_task_store()
calendar = get_sprint_calendar()

# Check data source mode (enabled = actively using Snowflake for data loading)
snowflake_mode = is_snowflake_enabled()
snowflake_configured = is_snowflake_configured()

# Diagnostic info
from modules.sqlite_store import is_sqlite_enabled, sync_from_snowflake
sqlite_mode = is_sqlite_enabled()

with st.expander("🔧 Data Source Diagnostics", expanded=False):
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        st.write(f"**SQLite Enabled:** {is_sqlite_enabled()}")
    with col_d2:
        st.write(f"**Snowflake Enabled:** {snowflake_mode}")
    with col_d3:
        st.write(f"**Snowflake Configured:** {snowflake_configured}")
    
    st.write(f"**TaskStore Mode:** use_sqlite={task_store.use_sqlite}, use_snowflake={task_store.use_snowflake}")
    st.write(f"**Total Tasks Loaded:** {len(task_store.tasks_df)}")
    
    # Show most recent tasks
    if not task_store.tasks_df.empty and 'TaskCreatedDt' in task_store.tasks_df.columns:
        import pandas as pd
        df_diag = task_store.tasks_df.copy()
        df_diag['TaskCreatedDt'] = pd.to_datetime(df_diag['TaskCreatedDt'], errors='coerce')
        recent = df_diag.nlargest(3, 'TaskCreatedDt')[['TaskNum', 'TaskStatus', 'TaskCreatedDt']]
        st.write("**Most Recent Tasks in Store:**")
        st.dataframe(recent, hide_index=True)

# =============================================================================
# SQLITE + SNOWFLAKE MODE (SQLite for storage, Snowflake for data source)
# =============================================================================
if sqlite_mode and snowflake_configured:
    st.success("**SQLite Mode with Snowflake Sync** - Data stored locally, synced from Snowflake")
    
    with st.expander("ℹ️ How It Works", expanded=False):
        st.markdown(f"""
        ### **Data Source: Snowflake**
        
        - **iTrack data** is loaded directly from Snowflake (read-only)
        - **Dashboard annotations** (Priority, GoalType, Comments, etc.) are stored locally
        - Data is **cached** until you manually refresh (no auto-refresh)
        - Use the **Refresh Data** button below to get the latest data from Snowflake
        
        ### **To Assign Tasks to Sprints:**
        - Go to **Backlog Assign** page
        - Select tasks and assign to target sprint
        """)
    
    st.divider()
    
    # Connection Status
    st.subheader("Snowflake Connection")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # Test connection button
        if st.button("Test Connection"):
            with st.spinner("Testing Snowflake connection..."):
                success, message = test_snowflake_connection()
            if success:
                st.success(f"✅ {message}")
            else:
                st.error(f"❌ {message}")
    
    with col2:
        # Sync from Snowflake button
        if st.button("Sync from Snowflake", type="primary"):
            with st.spinner("Syncing data from Snowflake to SQLite..."):
                # Clear ALL caches aggressively
                st.cache_data.clear()  # Clear all Streamlit data caches
                from modules.section_filter import clear_team_cache
                clear_team_cache()  # Clear LRU cache for team members
                
                # Sync from Snowflake to SQLite
                sync_stats = sync_from_snowflake()
                
                if sync_stats['success']:
                    # Reset stores to reload from SQLite
                    reset_task_store()
                    reset_worklog_store()
                    
                    # Store stats in session state for display
                    st.session_state['snowflake_sync_stats'] = sync_stats
                    st.session_state['snowflake_refresh_success'] = True
                    
                    st.rerun()
                else:
                    st.error(f"❌ {sync_stats['message']}")
    
    # Display sync statistics if available
    if st.session_state.get('snowflake_refresh_success'):
        sync_stats = st.session_state.get('snowflake_sync_stats', {})
        
        st.success(f"✅ {sync_stats.get('message', 'Data synced successfully!')}")
        
        # Task Statistics
        st.subheader("📊 Task/Ticket Sync Statistics")
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.metric("Total Tasks", sync_stats.get('tasks_after', 0))
        with col_b:
            st.metric("New Tasks", sync_stats.get('new_tasks', 0), help="First time imported")
        with col_c:
            st.metric("Updated Tasks", sync_stats.get('updated_tasks', 0), help="Tasks with field changes")
        with col_d:
            st.metric("Unchanged", sync_stats.get('unchanged_tasks', 0), help="No changes detected")
        
        # Field-level task/ticket changes
        with st.expander("📋 Task/Ticket Field Changes", expanded=True):
            field_changes = [
                ("Task Status", len(sync_stats.get('task_status_changes', []))),
                ("Ticket Status", sync_stats.get('ticket_status_changed', 0)),
                ("Task Owner", sync_stats.get('task_owner_changed', 0)),
                ("Section", sync_stats.get('section_changed', 0)),
                ("Ticket Type", sync_stats.get('ticket_type_changed', 0)),
                ("Subject", sync_stats.get('subject_changed', 0)),
                ("Task Resolved Date", sync_stats.get('task_resolved_changed', 0)),
                ("Ticket Resolved Date", sync_stats.get('ticket_resolved_changed', 0)),
                ("Customer Name", sync_stats.get('customer_name_changed', 0)),
            ]
            field_df = pd.DataFrame(field_changes, columns=['Field', 'Records Changed'])
            field_df = field_df[field_df['Records Changed'] > 0]  # Only show fields with changes
            if not field_df.empty:
                st.dataframe(field_df, use_container_width=True, hide_index=True)
            else:
                st.info("No task/ticket field changes detected")
        
        # Worklog Statistics
        st.subheader("📝 Worklog Sync Statistics")
        col_w1, col_w2, col_w3, col_w4 = st.columns(4)
        with col_w1:
            st.metric("Total Worklogs", sync_stats.get('worklogs_after', 0))
        with col_w2:
            st.metric("New Worklogs", sync_stats.get('new_worklogs', 0), help="New worklog entries")
        with col_w3:
            st.metric("Updated Worklogs", sync_stats.get('worklogs_updated', 0), help="Worklogs with field changes")
        with col_w4:
            delta = sync_stats.get('worklogs_after', 0) - sync_stats.get('worklogs_before', 0)
            st.metric("Net Change", delta if delta != 0 else "—")
        
        # Field-level worklog changes
        with st.expander("📋 Worklog Field Changes", expanded=True):
            wl_field_changes = [
                ("Minutes Spent", sync_stats.get('worklog_minutes_changed', 0)),
                ("Description", sync_stats.get('worklog_description_changed', 0)),
                ("Log Date", sync_stats.get('worklog_logdate_changed', 0)),
            ]
            wl_field_df = pd.DataFrame(wl_field_changes, columns=['Field', 'Records Changed'])
            wl_field_df = wl_field_df[wl_field_df['Records Changed'] > 0]
            if not wl_field_df.empty:
                st.dataframe(wl_field_df, use_container_width=True, hide_index=True)
            else:
                st.info("No worklog field changes detected")
        
        # Detailed Reports
        st.markdown("---")
        
        # New Tasks by Status
        new_by_status = sync_stats.get('new_tasks_by_status', {})
        if new_by_status:
            with st.expander(f"🆕 New Tasks by Status ({sync_stats.get('new_tasks', 0)} total)", expanded=True):
                status_data = []
                for status, count in sorted(new_by_status.items(), key=lambda x: -x[1]):
                    marker = "🔴" if status in CLOSED_STATUSES else "🟢"
                    status_data.append({'Status': f"{marker} {status}", 'Count': count})
                st.dataframe(pd.DataFrame(status_data), use_container_width=True, hide_index=True)
        
        # Task Status Changes
        task_status_changes = sync_stats.get('task_status_changes', [])
        if task_status_changes:
            with st.expander(f"🔄 Task Status Changes ({len(task_status_changes)} tasks)", expanded=True):
                # Aggregate by transition type
                transitions = {}
                for change in task_status_changes:
                    key = f"{change['old_status']} → {change['new_status']}"
                    transitions[key] = transitions.get(key, 0) + 1
                
                transition_data = []
                for transition, count in sorted(transitions.items(), key=lambda x: -x[1]):
                    transition_data.append({'Status Change': transition, 'Count': count})
                st.dataframe(pd.DataFrame(transition_data), use_container_width=True, hide_index=True)
                
                # Show individual changes in nested expander
                with st.expander("View individual task changes"):
                    changes_df = pd.DataFrame(task_status_changes)
                    changes_df.columns = ['Task #', 'Old Status', 'New Status']
                    st.dataframe(changes_df, use_container_width=True, hide_index=True)
        
        # No changes message
        if not new_by_status and not task_status_changes and sync_stats.get('new_worklogs', 0) == 0:
            st.info("ℹ️ No new tasks, status changes, or worklog entries detected.")
        
        # Clear button
        if st.button("Clear Statistics"):
            st.session_state.pop('snowflake_refresh_success', None)
            st.session_state.pop('snowflake_sync_stats', None)
            st.rerun()
    
    with col3:
        # Show last refresh time
        last_refresh = get_last_refresh_time()
        if last_refresh:
            st.caption(f"Last refresh: {last_refresh.strftime('%H:%M:%S')}")
        else:
            st.caption("Not yet refreshed")
    
    # Show current configuration
    config = get_snowflake_config()
    with st.expander("⚙️ Current Configuration", expanded=False):
        st.code(f"""Database: {config.get('database', 'Not set')}
Schema: {config.get('schema', 'Not set')}
Tasks Table: {config.get('tasks_table', 'Not set')}
URL: {config.get('url', config.get('account', 'Not set'))}""")
    
    st.divider()
    
    # =================================================================
    # DATABASE EXPLORATION SECTION
    # =================================================================
    st.subheader("🔎 Explore Database")
    
    with st.expander("📋 List Tables & Views", expanded=True):
        if st.button("🔄 Load Tables"):
            with st.spinner("Loading tables..."):
                tables_df, success, message = list_tables()
            
            if success:
                st.success(message)
                if not tables_df.empty:
                    st.dataframe(tables_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No tables found in the schema")
            else:
                st.error(message)
    
    # Table exploration
    with st.expander("🔍 Explore Table Structure", expanded=True):
        table_name = st.text_input(
            "Enter table/view name to explore:",
            value=config.get('tasks_table', ''),
            help="Enter the exact name of the table or view"
        )
        
        if table_name:
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                if st.button("📊 Describe Columns"):
                    with st.spinner("Loading column info..."):
                        cols_df, success, message = describe_table(table_name)
                    
                    if success:
                        st.success(message)
                        st.dataframe(cols_df, use_container_width=True, hide_index=True)
                    else:
                        st.error(message)
            
            with col_b:
                if st.button("👁️ Preview Data (10 rows)"):
                    with st.spinner("Loading preview..."):
                        preview_df, success, message = preview_table(table_name, limit=10)
                    
                    if success:
                        st.success(message)
                        st.dataframe(preview_df, use_container_width=True, hide_index=True)
                    else:
                        st.error(message)
            
            with col_c:
                if st.button("🔢 Count Rows"):
                    with st.spinner("Counting rows..."):
                        count, success, message = get_table_row_count(table_name)
                    
                    if success:
                        st.metric("Total Rows", f"{count:,}")
                    else:
                        st.error(message)
    
    # Column value exploration
    with st.expander("📈 Explore Column Values", expanded=False):
        col_table = st.text_input(
            "Table name:",
            value=config.get('tasks_table', ''),
            key="col_value_table"
        )
        col_name = st.text_input(
            "Column name:",
            placeholder="e.g., STATUS, SECTION, ASSIGNEDTO"
        )
        
        if col_table and col_name:
            if st.button("📊 Show Distinct Values"):
                with st.spinner("Loading values..."):
                    values_df, success, message = get_column_values(col_table, col_name)
                
                if success:
                    st.success(message)
                    st.dataframe(values_df, use_container_width=True, hide_index=True)
                else:
                    st.error(message)
    
    st.divider()
    
    # Current Data Status
    st.subheader("Current Task Data")
    
    all_tasks = task_store.get_all_tasks()
    
    if all_tasks.empty:
        st.warning("📭 No tasks loaded from Snowflake")
        st.info("Click **Refresh Data** to load tasks, or check your Snowflake connection settings.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Tasks", len(all_tasks))
        
        with col2:
            if 'TaskStatus' in all_tasks.columns:
                open_count = len(all_tasks[~all_tasks['TaskStatus'].isin(CLOSED_STATUSES)])
                st.metric("Open Tasks", open_count)
        
        with col3:
            if 'SprintsAssigned' in all_tasks.columns:
                all_sprints = set()
                for sprints in all_tasks['SprintsAssigned'].dropna():
                    if sprints and str(sprints).strip():
                        for s in str(sprints).split(','):
                            if s.strip():
                                all_sprints.add(s.strip())
                st.metric("Sprints", len(all_sprints))
        
        with col4:
            current_sprint = calendar.get_current_sprint()
            if current_sprint:
                current_tasks = task_store.get_current_sprint_tasks()
                st.metric("Current Sprint", len(current_tasks))
        
        # Show current sprint info
        current_sprint = calendar.get_current_sprint()
        if current_sprint:
            sprint_display = format_sprint_display(current_sprint['SprintName'], current_sprint['SprintStartDt'], current_sprint['SprintEndDt'], int(current_sprint['SprintNumber']))
            st.success(f"📅 Current Sprint: **{sprint_display}**")
        
        st.page_link("pages/1_Overview.py", label="Go to Overview")

# =============================================================================
# CSV MODE (Legacy)
# =============================================================================
else:
    st.info("📁 **CSV Mode** - Upload iTrack exports manually")
    
    # Instructions
    with st.expander("ℹ️ How It Works", expanded=True):
        st.markdown("""
        ### **Sprint Assignment Policy:**
        
        1. **Upload iTrack CSV** - imports all tasks from iTrack
        2. **Sprints are assigned manually** via the **Backlog Assign** page
        3. **No automatic sprint assignment** based on dates
        
        ### **What Happens on Upload:**
        - New tasks are added to the backlog (no sprint assigned)
        - Existing tasks preserve their sprint assignments
        - iTrack fields are updated (Status, AssignedTo, dates, etc.)
        - Dashboard annotations are preserved (Priority, GoalType, Comments, etc.)
        
        ### **To Assign Tasks to Sprints:**
        - Go to **Backlog Assign** page
        - Select tasks and assign to target sprint
        
        ---
        
        💡 **Tip:** To enable automatic data loading from Snowflake, set `enabled = true` in the `[snowflake]` section of `.streamlit/secrets.toml`
        """)
    
    # Show Snowflake exploration tools if configured (even when not enabled)
    if snowflake_configured and not snowflake_mode:
        st.divider()
        st.subheader("Snowflake Database Explorer")
        st.info("ℹ️ Snowflake is configured but **not enabled** for data loading. Use CSV upload above, or explore the database below.")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔍 Test Connection"):
                with st.spinner("Testing Snowflake connection..."):
                    success, message = test_snowflake_connection()
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ {message}")
        
        # Show current configuration
        config = get_snowflake_config()
        with st.expander("⚙️ Current Configuration", expanded=False):
            st.code(f"""Database: {config.get('database', 'Not set')}
Schema: {config.get('schema', 'Not set')}
Tasks Table: {config.get('tasks_table', 'Not set')}
URL: {config.get('url', config.get('account', 'Not set'))}
Enabled: {config.get('enabled', False)}""")
        
        # Table exploration
        with st.expander("🔍 Explore Table Structure", expanded=False):
            table_name = st.text_input(
                "Enter table/view name to explore:",
                value=config.get('tasks_table', ''),
                help="Enter the exact name of the table or view",
                key="csv_mode_table_name"
            )
            
            if table_name:
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    if st.button("📊 Describe Columns", key="csv_describe"):
                        with st.spinner("Loading column info..."):
                            cols_df, success, message = describe_table(table_name)
                        
                        if success:
                            st.success(message)
                            st.dataframe(cols_df, use_container_width=True, hide_index=True)
                        else:
                            st.error(message)
                
                with col_b:
                    if st.button("👁️ Preview Data", key="csv_preview"):
                        with st.spinner("Loading preview..."):
                            preview_df, success, message = preview_table(table_name, limit=10)
                        
                        if success:
                            st.success(message)
                            st.dataframe(preview_df, use_container_width=True, hide_index=True)
                        else:
                            st.error(message)
                
                with col_c:
                    if st.button("🔢 Count Rows", key="csv_count"):
                        with st.spinner("Counting rows..."):
                            count, success, message = get_table_row_count(table_name)
                        
                        if success:
                            st.metric("Total Rows", f"{count:,}")
                        else:
                            st.error(message)
    
    st.divider()
    
    # File Upload
    st.subheader("📁 Step 1: Upload iTrack Export")
    
    uploaded_file = st.file_uploader(
        "Choose iTrack CSV file",
        type=['csv'],
        help="Upload the standard iTrack table export (UTF-16, tab-delimited)"
    )
    
    if uploaded_file:
        # Load and validate
        with st.spinner("Loading and validating file..."):
            itrack_df, is_valid, validation_msg = data_loader.load_itrack_extract(uploaded_file)
        
        if not is_valid:
            st.error(f"❌ Validation Error: {validation_msg}")
            st.stop()
        
        st.success(f"✅ Loaded {len(itrack_df)} tasks from iTrack")
        
        # Map to sprint schema
        mapped_df = data_loader.map_itrack_to_sprint(itrack_df)
        
        # Preview task summary (no auto sprint assignment)
        st.subheader("Step 2: Review Task Summary")
        
        st.info("📋 **Note:** Tasks will be added to the backlog. Use **Work Backlogs** page to assign sprints.")
        
        # Status breakdown
        col1, col2 = st.columns(2)
        
        with col1:
            if 'TaskStatus' in mapped_df.columns:
                st.markdown("**Tasks by Status:**")
                status_counts = mapped_df['TaskStatus'].value_counts()
                for status, count in status_counts.items():
                    marker = "🔴" if status in CLOSED_STATUSES else "🟢"
                    st.write(f"{marker} {status}: **{count}**")
        
        with col2:
            open_count = len(mapped_df[~mapped_df['TaskStatus'].isin(CLOSED_STATUSES)]) if 'TaskStatus' in mapped_df.columns else len(mapped_df)
            closed_count = len(mapped_df) - open_count
            
            st.metric("Open Tasks", open_count, help="Available for sprint assignment in Work Backlogs")
            st.metric("Closed Tasks", closed_count, help="Completed tasks")
        
        st.divider()
        
        # Import button
        st.subheader("📥 Step 3: Import Tasks")
        
        st.warning("⚠️ **IMPORTANT:** You must click the button below to save tasks. Step 2 is just a preview.")
        
        # Show import logic explanation
        st.markdown("""
        **Import Rules (Field Ownership Model):**
        - 🔄 **Existing tasks** → Only iTrack fields updated (Status, AssignedTo, Subject, dates)
        - 🛡️ **Dashboard annotations preserved** → SprintsAssigned, Priority, GoalType, Comments, etc.
        - 📋 **New tasks** → Added to backlog with no sprint assignment
        - ✅ **Previously assigned tasks** → Keep their sprint assignments
        """)
        
        if st.button("📥 Import All Tasks", type="primary", use_container_width=True):
            with st.spinner("Importing tasks to task store..."):
                stats = task_store.import_tasks(itrack_df, mapped_df)
                save_success = task_store.save()
            
            if not save_success:
                st.error("❌ Failed to save tasks to store. Check file permissions.")
                st.stop()
            
            st.success("✅ Import Complete!")
            
            # Summary metrics
            col_a, col_b, col_c, col_d, col_e = st.columns(5)
            with col_a:
                st.metric("Total Processed", stats['total_imported'])
            with col_b:
                st.metric("New Tasks", stats['new_tasks'], help="First time imported")
            with col_c:
                st.metric("Updated Tasks", stats['updated_tasks'], help="iTrack fields changed")
            with col_d:
                st.metric("Unchanged", stats.get('unchanged_tasks', 0), help="No changes detected")
            with col_e:
                skipped = stats.get('skipped_old_closed', 0)
                st.metric("Skipped (Old Closed)", skipped, help="Closed/cancelled tasks created before threshold date")
        
            # =================================================================
            # DETAILED IMPORT REPORT
            # =================================================================
            st.markdown("---")
            st.subheader("Detailed Import Report")
            
            # New Tasks by Status
            new_by_status = stats.get('new_tasks_by_status', {})
            if new_by_status:
                with st.expander(f"🆕 New Tasks by Status ({stats['new_tasks']} total)", expanded=True):
                    status_data = []
                    for status, count in sorted(new_by_status.items(), key=lambda x: -x[1]):
                        marker = "🔴" if status in CLOSED_STATUSES else "🟢"
                        status_data.append({'Status': f"{marker} {status}", 'Count': count})
                    st.dataframe(pd.DataFrame(status_data), use_container_width=True, hide_index=True)
            
            # Task Status Changes
            task_status_changes = stats.get('task_status_changes', [])
            if task_status_changes:
                with st.expander(f"🔄 Task Status Changes ({len(task_status_changes)} tasks)", expanded=True):
                    # Aggregate by transition type
                    transitions = {}
                    for change in task_status_changes:
                        key = f"{change['old_status']} → {change['new_status']}"
                        transitions[key] = transitions.get(key, 0) + 1
                    
                    transition_data = []
                    for transition, count in sorted(transitions.items(), key=lambda x: -x[1]):
                        transition_data.append({'Status Change': transition, 'Count': count})
                    st.dataframe(pd.DataFrame(transition_data), use_container_width=True, hide_index=True)
                    
                    # Show individual changes in nested expander
                    with st.expander("View individual task changes"):
                        changes_df = pd.DataFrame(task_status_changes)
                        changes_df.columns = ['Task #', 'Old Status', 'New Status']
                        st.dataframe(changes_df, use_container_width=True, hide_index=True)
            
            # Ticket Status Changes
            ticket_status_changes = stats.get('ticket_status_changes', [])
            if ticket_status_changes:
                with st.expander(f"🎫 Ticket Status Changes ({len(ticket_status_changes)} tickets)", expanded=True):
                    # Aggregate by transition type
                    transitions = {}
                    for change in ticket_status_changes:
                        key = f"{change['old_status']} → {change['new_status']}"
                        transitions[key] = transitions.get(key, 0) + 1
                    
                    transition_data = []
                    for transition, count in sorted(transitions.items(), key=lambda x: -x[1]):
                        transition_data.append({'Status Change': transition, 'Count': count})
                    st.dataframe(pd.DataFrame(transition_data), use_container_width=True, hide_index=True)
                    
                    # Show individual changes in nested expander
                    with st.expander("View individual ticket changes"):
                        changes_df = pd.DataFrame(ticket_status_changes)
                        changes_df.columns = ['Task #', 'Old Status', 'New Status']
                        st.dataframe(changes_df, use_container_width=True, hide_index=True)
            
            # Field Changes Summary
            field_changes = stats.get('field_changes', {})
            if field_changes:
                with st.expander(f"📝 Field Changes Summary ({sum(field_changes.values())} changes)", expanded=False):
                    field_data = []
                    for field, count in sorted(field_changes.items(), key=lambda x: -x[1]):
                        field_data.append({'Field': field, 'Changes': count})
                    st.dataframe(pd.DataFrame(field_data), use_container_width=True, hide_index=True)
            
            # No changes message
            if not new_by_status and not task_status_changes and not ticket_status_changes:
                st.info("ℹ️ No new tasks or status changes detected in this import.")
            
            # =================================================================
            # BACKLOG STATUS
            # =================================================================
            st.markdown("---")
            
            # Get backlog count
            backlog_tasks = task_store.get_backlog_tasks()
            backlog_count = len(backlog_tasks) if not backlog_tasks.empty else 0
            
            st.info(f"📋 **{backlog_count} open tasks** are in the Work Backlogs.")
            
            # Link to Work Backlogs
            st.markdown("### 👉 Next Steps:")
            st.page_link("pages/4_PIBIDS_Sprint_Planning/2_Backlog_Assign.py", label="Assign Tasks to Sprints")

    else:
        # Show current store status when no file uploaded
        st.divider()
        st.subheader("Current Task Store Status")
        
        all_tasks = task_store.get_all_tasks()
        
        if all_tasks.empty:
            st.info("📭 No tasks in store yet. Upload an iTrack file to get started.")
        else:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Tasks", len(all_tasks))
            
            with col2:
                if 'TaskStatus' in all_tasks.columns:
                    open_count = len(all_tasks[~all_tasks['TaskStatus'].isin(CLOSED_STATUSES)])
                    st.metric("Open Tasks", open_count)
            
            with col3:
                if 'SprintsAssigned' in all_tasks.columns:
                    # Count unique sprints from SprintsAssigned column
                    all_sprints = set()
                    for sprints in all_tasks['SprintsAssigned'].dropna():
                        if sprints and str(sprints).strip():
                            for s in str(sprints).split(','):
                                if s.strip():
                                    all_sprints.add(s.strip())
                    st.metric("Sprints", len(all_sprints))
            
            with col4:
                current_sprint = calendar.get_current_sprint()
                if current_sprint:
                    current_tasks = task_store.get_current_sprint_tasks()
                    st.metric(f"Current Sprint", len(current_tasks))
            
            # Show current sprint info
            current_sprint = calendar.get_current_sprint()
            if current_sprint:
                sprint_display = format_sprint_display(current_sprint['SprintName'], current_sprint['SprintStartDt'], current_sprint['SprintEndDt'], int(current_sprint['SprintNumber']))
            st.success(f"📅 Current Sprint: **{sprint_display}**")
            
            st.page_link("pages/1_Overview.py", label="Go to Overview")
            
            # =================================================================
            # CLEANUP OLD CLOSED TASKS SECTION
            # =================================================================
            st.divider()
            st.subheader("🧹 Cleanup Old Closed Tasks")
            
            from utils.constants import IMPORT_THRESHOLD_DATE, CLOSED_TASK_STATUSES
            
            st.markdown(f"""
            Remove closed/cancelled tasks created **before {IMPORT_THRESHOLD_DATE.strftime('%Y-%m-%d')}** from the store.
            
            **What will be removed:**
            - Tasks with status: {', '.join(CLOSED_TASK_STATUSES)}
            - Created before the threshold date
            
            **What will be kept:**
            - All tasks created on or after the threshold (any status)
            - Open tasks created before the threshold (Waiting, Logged, Accepted, Assigned)
            """)
            
            if st.button("🧹 Run Cleanup", type="secondary"):
                with st.spinner("Cleaning up old closed tasks..."):
                    cleanup_stats = task_store.cleanup_old_closed_tasks()
                    save_success = task_store.save()
                
                if save_success:
                    st.success(f"✅ Cleanup Complete!")
                    
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Before", cleanup_stats['total_before'])
                    with col_b:
                        st.metric("Removed", cleanup_stats['removed'], delta=-cleanup_stats['removed'] if cleanup_stats['removed'] > 0 else None)
                    with col_c:
                        st.metric("Kept", cleanup_stats['kept'])
                    
                    if cleanup_stats['removed_by_status']:
                        st.markdown("**Removed by Status:**")
                        for status, count in cleanup_stats['removed_by_status'].items():
                            st.write(f"- {status}: {count}")
                    
                    st.rerun()
                else:
                    st.error("❌ Failed to save after cleanup. Check file permissions.")

# Worklog Upload Section
st.divider()
st.header("📝 Upload Worklog Data")
st.markdown("""
Upload the iTrack **Worklog export** to track team member activity.
This is a separate CSV file from the task export.

**Import Strategy:** Date-based merge — records for dates in the upload are updated; 
records for dates NOT in the upload are preserved.
""")

worklog_file = st.file_uploader(
    "Choose iTrack Worklog CSV file",
    type=['csv'],
    help="Upload the iTrack worklog table export (UTF-16, tab-delimited)",
    key="worklog_upload"
)

if worklog_file:
    worklog_store = get_worklog_store()
    
    with st.spinner("Importing worklog data..."):
        success, message, stats = worklog_store.import_worklog(file_content=worklog_file.read())
    
    if success:
        st.success(f"✅ {message}")
        
        # Row 1: Upload stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rows", stats['total'])
        with col2:
            st.metric("Valid Logs", stats['valid_logs'])
        with col3:
            st.metric("Dates in Upload", stats.get('dates_in_upload', 0))
        
        # Row 2: Merge stats
        col4, col5, col6 = st.columns(3)
        with col4:
            st.metric("Records Replaced", stats.get('records_replaced', 0), 
                     help="Existing records for dates in upload that were replaced")
        with col5:
            st.metric("Records Preserved", stats.get('records_preserved', 0),
                     help="Existing records for dates NOT in upload that were kept")
        with col6:
            st.metric("Skipped", stats['skipped'])
        
        # Reset singleton to reload data
        reset_worklog_store()
        
        st.page_link("pages/4_PIBIDS_Sprint_Planning/3_Worklog_Activity.py", label="View Worklog Activity Report")
    else:
        st.error(f"❌ {message}")
else:
    # Show current worklog status
    worklog_store = get_worklog_store()
    all_worklogs = worklog_store.get_all_worklogs()
    
    if not all_worklogs.empty:
        st.info(f"📊 Current worklog data: **{len(all_worklogs)}** entries loaded")
        st.page_link("pages/4_PIBIDS_Sprint_Planning/3_Worklog_Activity.py", label="View Worklog Activity Report")
    else:
        st.caption("No worklog data imported yet.")
