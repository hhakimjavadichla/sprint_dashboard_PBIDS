"""
Upload Tasks Page
Simple task import from iTrack - tasks auto-assign to sprints by Task Assigned Date
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from modules.data_loader import DataLoader
from modules.task_store import get_task_store, CLOSED_STATUSES
from modules.sprint_calendar import get_sprint_calendar
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
    **Import Rules:**
    - ✅ **Completed tasks** → Auto-assigned to their original sprint
    - 📋 **Open tasks** → Go to Work Backlogs for admin assignment (no automatic carryover)
    """)
    
    if st.button("📥 Import All Tasks", type="primary", use_container_width=True):
        with st.spinner("Importing tasks to task store..."):
            stats = task_store.import_tasks(itrack_df, mapped_df)
            save_success = task_store.save()
        
        if not save_success:
            st.error("❌ Failed to save tasks to store. Check file permissions.")
            st.stop()
        
        st.success("✅ Import Complete!")
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Total Imported", stats['total_imported'])
        with col_b:
            st.metric("New Tasks", stats['new_tasks'])
        with col_c:
            st.metric("Updated Tasks", stats['updated_tasks'])
        
        # Get backlog count
        backlog_tasks = task_store.get_backlog_tasks()
        backlog_count = len(backlog_tasks) if not backlog_tasks.empty else 0
        
        st.info(f"📋 **{backlog_count} open tasks** are in the Work Backlogs.")
        
        # Link to Work Backlogs
        st.markdown("---")
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
