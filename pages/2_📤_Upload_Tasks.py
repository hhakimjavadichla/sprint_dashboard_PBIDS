"""
Upload Tasks Page
Simple task import from iTrack - tasks auto-assign to sprints by Task Assigned Date
Also supports worklog import for activity tracking.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from modules.data_loader import DataLoader
from modules.task_store import get_task_store, CLOSED_STATUSES
from modules.sprint_calendar import get_sprint_calendar
from modules.worklog_store import get_worklog_store, reset_worklog_store
from components.auth import require_admin, display_user_info

st.set_page_config(
    page_title="Upload Tasks",
    page_icon="📤",
    layout="wide"
)

st.title("📤 Upload iTrack Tasks")

# Require admin access
require_admin("Upload Tasks")
display_user_info()

# Load modules
data_loader = DataLoader()
task_store = get_task_store()
calendar = get_sprint_calendar()

# Instructions
with st.expander("ℹ️ How It Works - Simplified Workflow", expanded=True):
    st.markdown("""
    ### **New Simplified Workflow:**
    
    1. **Upload iTrack CSV** - can contain tasks spanning multiple sprints
    2. **Tasks auto-assign** to sprints based on **Task Assigned Date**
    3. **Each task gets a Unique ID**: `TaskNum_S{SprintNumber}`
    
    ### **Current Sprint Automatically Includes:**
    - Tasks assigned within the current sprint window
    - **ALL open tasks from previous sprints** (carryover)
    
    ### **No Manual Sprint Generation Needed!**
    
    ---
    
    **To close a task and prevent carryover:**
    - Go to **Sprint View** page
    - Select the task and update its status
    - Set the **Status Update Date** to control which sprint it closes in
    """)

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
    
    # Preview data distribution by sprint
    st.subheader("📊 Step 2: Review Task Distribution")
    
    st.markdown("Tasks will be automatically assigned to sprints based on **Task Assigned Date**:")
    
    if 'TaskAssignedDt' in mapped_df.columns:
        mapped_df['TaskAssignedDt'] = pd.to_datetime(mapped_df['TaskAssignedDt'], errors='coerce')
        
        # Count by sprint
        sprint_counts = {}
        no_sprint_tasks = []
        
        for idx, row in mapped_df.iterrows():
            sprint_info = calendar.get_sprint_for_date(row['TaskAssignedDt'])
            if sprint_info:
                sprint_num = sprint_info['SprintNumber']
                key = f"Sprint {sprint_num}"
                if key not in sprint_counts:
                    sprint_counts[key] = {
                        'count': 0,
                        'name': sprint_info['SprintName'],
                        'start': sprint_info['SprintStartDt'],
                        'end': sprint_info['SprintEndDt']
                    }
                sprint_counts[key]['count'] += 1
            else:
                no_sprint_tasks.append(row['TaskNum'])
        
        # Display as table
        if sprint_counts:
            sprint_data = []
            for sprint_key, info in sorted(sprint_counts.items(), key=lambda x: x[0]):
                sprint_data.append({
                    'Sprint': sprint_key,
                    'Name': info['name'],
                    'Window': f"{info['start'].strftime('%m/%d')} - {info['end'].strftime('%m/%d')}",
                    'Tasks': info['count']
                })
            
            st.dataframe(
                pd.DataFrame(sprint_data),
                use_container_width=True,
                hide_index=True
            )
        
        if no_sprint_tasks:
            st.warning(f"⚠️ {len(no_sprint_tasks)} tasks have dates outside defined sprint windows")
            with st.expander("View tasks without sprint"):
                st.write(no_sprint_tasks[:20])
                if len(no_sprint_tasks) > 20:
                    st.caption(f"... and {len(no_sprint_tasks) - 20} more")
    
    # Status breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        if 'Status' in mapped_df.columns:
            st.markdown("**Tasks by Status:**")
            status_counts = mapped_df['Status'].value_counts()
            for status, count in status_counts.items():
                marker = "🔴" if status in CLOSED_STATUSES else "🟢"
                st.write(f"{marker} {status}: **{count}**")
    
    with col2:
        open_count = len(mapped_df[~mapped_df['Status'].isin(CLOSED_STATUSES)]) if 'Status' in mapped_df.columns else len(mapped_df)
        closed_count = len(mapped_df) - open_count
        
        st.metric("Open Tasks", open_count, help="Will carry over to current sprint")
        st.metric("Closed Tasks", closed_count, help="Will stay in their original sprint")
    
    st.divider()
    
    # Import button
    st.subheader("📥 Step 3: Import Tasks")
    
    st.warning("⚠️ **IMPORTANT:** You must click the button below to save tasks. Step 2 is just a preview.")
    
    # Show import logic explanation
    st.markdown("""
    **Import Rules (Field Ownership Model):**
    - 🔄 **Existing tasks** → Only iTrack fields updated (Status, AssignedTo, Subject, dates)
    - 🛡️ **Dashboard annotations preserved** → SprintsAssigned, Priority, GoalType, Comments, etc.
    - ✅ **Completed tasks** → Auto-assigned to their original sprint
    - 📋 **Open tasks** → Go to Work Backlogs for admin assignment
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
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.metric("Total Processed", stats['total_imported'])
        with col_b:
            st.metric("New Tasks", stats['new_tasks'], help="First time imported")
        with col_c:
            st.metric("Updated Tasks", stats['updated_tasks'], help="iTrack fields changed")
        with col_d:
            st.metric("Unchanged", stats.get('unchanged_tasks', 0), help="No changes detected")
        
        # =================================================================
        # DETAILED IMPORT REPORT
        # =================================================================
        st.markdown("---")
        st.subheader("📊 Detailed Import Report")
        
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
        st.page_link("pages/8_📋_Work_Backlogs.py", label="Assign Tasks to Sprints", icon="📋")

else:
    # Show current store status when no file uploaded
    st.divider()
    st.subheader("📊 Current Task Store Status")
    
    all_tasks = task_store.get_all_tasks()
    
    if all_tasks.empty:
        st.info("📭 No tasks in store yet. Upload an iTrack file to get started.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Tasks", len(all_tasks))
        
        with col2:
            if 'Status' in all_tasks.columns:
                open_count = len(all_tasks[~all_tasks['Status'].isin(CLOSED_STATUSES)])
                st.metric("Open Tasks", open_count)
        
        with col3:
            if 'OriginalSprintNumber' in all_tasks.columns:
                sprint_count = all_tasks['OriginalSprintNumber'].nunique()
                st.metric("Sprints", sprint_count)
        
        with col4:
            current_sprint = calendar.get_current_sprint()
            if current_sprint:
                current_tasks = task_store.get_current_sprint_tasks()
                st.metric(f"Current Sprint", len(current_tasks))
        
        # Show current sprint info
        current_sprint = calendar.get_current_sprint()
        if current_sprint:
            st.success(f"📅 Current Sprint: **Sprint {current_sprint['SprintNumber']} - {current_sprint['SprintName']}** ({current_sprint['SprintStartDt'].strftime('%Y-%m-%d')} to {current_sprint['SprintEndDt'].strftime('%Y-%m-%d')})")
        
        st.page_link("pages/3_📋_Sprint_View.py", label="📋 Go to Sprint View", icon="📋")

# Worklog Upload Section
st.divider()
st.header("📝 Upload Worklog Data")
st.markdown("""
Upload the iTrack **Worklog export** to track team member activity.
This is a separate CSV file from the task export.
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
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rows", stats['total'])
        with col2:
            st.metric("Valid Logs", stats['valid_logs'])
        with col3:
            st.metric("Skipped", stats['skipped'])
        
        # Reset singleton to reload data
        reset_worklog_store()
        
        st.page_link("pages/9_📊_Worklog_Activity.py", label="📊 View Worklog Activity Report", icon="📊")
    else:
        st.error(f"❌ {message}")
else:
    # Show current worklog status
    worklog_store = get_worklog_store()
    all_worklogs = worklog_store.get_all_worklogs()
    
    if not all_worklogs.empty:
        st.info(f"📊 Current worklog data: **{len(all_worklogs)}** entries loaded")
        st.page_link("pages/9_📊_Worklog_Activity.py", label="📊 View Worklog Activity Report", icon="📊")
    else:
        st.caption("No worklog data imported yet.")
