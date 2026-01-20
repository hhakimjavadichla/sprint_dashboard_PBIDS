"""
Sprint Feedback Page
Section Managers can submit feedback for the recently completed sprint.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from modules.feedback_store import get_feedback_store
from modules.sprint_calendar import get_sprint_calendar
from components.auth import require_auth, display_user_info, get_user_role, get_user_section, is_section_manager
from utils.grid_styles import apply_grid_styles

# Apply styles
apply_grid_styles()

st.title("💬 Sprint Feedback")
st.caption("_Prototype — PBIDS Team_")

# Require authentication
require_auth("Sprint Feedback")

# Display user info
display_user_info()

# Get user info
user_role = get_user_role()
username = st.session_state.get('username', '')
user_section_raw = get_user_section()

# Parse user sections
user_sections = []
if user_section_raw:
    user_sections = [s.strip() for s in user_section_raw.split(',') if s.strip()]

# Check if user is Section Manager
if user_role not in ['Section Manager', 'Admin']:
    st.warning("⚠️ This page is only accessible to Section Managers")
    st.info("Section Managers can submit feedback for recently completed sprints.")
    st.stop()

# Get sprint calendar
calendar = get_sprint_calendar()
current_sprint = calendar.get_current_sprint()
all_sprints = calendar.get_all_sprints()

if all_sprints.empty:
    st.error("No sprints configured. Please contact an administrator.")
    st.stop()

# Determine the "recent" sprint (just finished sprint)
# If current sprint is N, recent sprint is N-1
if current_sprint is not None:
    current_sprint_num = int(current_sprint['SprintNumber'])
    recent_sprint_num = current_sprint_num - 1
else:
    # If no current sprint, use the last sprint in the calendar
    current_sprint_num = int(all_sprints['SprintNumber'].max())
    recent_sprint_num = current_sprint_num

# Get recent sprint info
recent_sprint_info = calendar.get_sprint_by_number(recent_sprint_num)

# Get feedback store
feedback_store = get_feedback_store()

st.divider()

# Tabs for submitting feedback and viewing history
tab1, tab2 = st.tabs(["📝 Submit Feedback", "📋 View Previous Feedback"])

with tab1:
    st.subheader(f"Submit Feedback for Sprint {recent_sprint_num}")
    
    if recent_sprint_info is None:
        st.warning(f"Sprint {recent_sprint_num} not found in calendar.")
        st.info("No recent sprint available for feedback.")
    elif recent_sprint_num < 1:
        st.info("No previous sprint available for feedback yet.")
    else:
        # Show sprint info
        sprint_name = recent_sprint_info.get('SprintName', f'Sprint {recent_sprint_num}')
        sprint_start = recent_sprint_info.get('SprintStartDt', 'N/A')
        sprint_end = recent_sprint_info.get('SprintEndDt', 'N/A')
        
        st.info(f"**{sprint_name}** ({sprint_start} - {sprint_end})")
        
        if not user_sections:
            st.error("⚠️ No section assigned to your account")
            st.info("Please contact an administrator to assign a section to submit feedback.")
        else:
            # Allow feedback for each section the user manages
            for section in user_sections:
                st.markdown(f"#### Feedback for Section: **{section}**")
                
                # Check if feedback already submitted
                if feedback_store.has_feedback(recent_sprint_num, section, username):
                    st.success(f"✅ Feedback already submitted for {section}")
                    
                    # Show existing feedback
                    existing = feedback_store.get_feedback_for_sprint(recent_sprint_num, section)
                    user_feedback = existing[existing['SubmittedBy'] == username]
                    if not user_feedback.empty:
                        fb = user_feedback.iloc[0]
                        with st.expander("View your submitted feedback"):
                            st.write(f"**Overall Satisfaction:** {fb['OverallSatisfaction']} / 5")
                            st.write(f"**What went well:** {fb['WhatWentWell']}")
                            st.write(f"**What did not go well:** {fb['WhatDidNotGoWell']}")
                            st.caption(f"Submitted: {fb['SubmittedAt']}")
                else:
                    # Feedback form
                    with st.form(key=f"feedback_form_{section}"):
                        st.markdown("**a. Overall satisfaction of this sprint?**")
                        satisfaction = st.slider(
                            "Rate from 1 (Very Unsatisfied) to 5 (Very Satisfied)",
                            min_value=1,
                            max_value=5,
                            value=3,
                            key=f"satisfaction_{section}"
                        )
                        
                        st.markdown("**b. What went well?**")
                        went_well = st.text_area(
                            "Describe what went well during this sprint",
                            height=100,
                            key=f"went_well_{section}",
                            placeholder="Share positive outcomes, achievements, and successes..."
                        )
                        
                        st.markdown("**c. What did not go well?**")
                        did_not_go_well = st.text_area(
                            "Describe what did not go well or areas for improvement",
                            height=100,
                            key=f"did_not_go_well_{section}",
                            placeholder="Share challenges, blockers, or areas that need improvement..."
                        )
                        
                        submitted = st.form_submit_button("📤 Submit Feedback", type="primary")
                        
                        if submitted:
                            if not went_well.strip() and not did_not_go_well.strip():
                                st.error("Please provide at least one comment (what went well or what did not go well)")
                            else:
                                success, message = feedback_store.add_feedback(
                                    sprint_number=recent_sprint_num,
                                    section=section,
                                    submitted_by=username,
                                    overall_satisfaction=satisfaction,
                                    what_went_well=went_well.strip(),
                                    what_did_not_go_well=did_not_go_well.strip()
                                )
                                
                                if success:
                                    st.success(f"✅ {message}")
                                    st.rerun()
                                else:
                                    st.error(f"❌ {message}")
                
                st.divider()

with tab2:
    st.subheader("📋 Your Previous Feedback")
    
    # Get all feedback by this user
    user_feedback = feedback_store.get_feedback_by_user(username)
    
    if user_feedback.empty:
        st.info("You haven't submitted any feedback yet.")
    else:
        # Sort by sprint number descending
        user_feedback = user_feedback.sort_values('SprintNumber', ascending=False)
        
        # Group by sprint
        for sprint_num in user_feedback['SprintNumber'].unique():
            sprint_info = calendar.get_sprint_by_number(int(sprint_num))
            sprint_name = sprint_info.get('SprintName', f'Sprint {sprint_num}') if sprint_info else f'Sprint {sprint_num}'
            
            with st.expander(f"**{sprint_name}**", expanded=(sprint_num == recent_sprint_num)):
                sprint_feedback = user_feedback[user_feedback['SprintNumber'] == sprint_num]
                
                for _, fb in sprint_feedback.iterrows():
                    st.markdown(f"**Section: {fb['Section']}**")
                    
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.metric("Satisfaction", f"{fb['OverallSatisfaction']} / 5")
                    with col2:
                        st.caption(f"Submitted: {fb['SubmittedAt']}")
                    
                    st.markdown("**What went well:**")
                    st.write(fb['WhatWentWell'] if fb['WhatWentWell'] else "_No comment_")
                    
                    st.markdown("**What did not go well:**")
                    st.write(fb['WhatDidNotGoWell'] if fb['WhatDidNotGoWell'] else "_No comment_")
                    
                    st.divider()

# Help section
with st.expander("ℹ️ About Sprint Feedback"):
    st.markdown(f"""
    ### How Sprint Feedback Works
    
    - **Who can submit:** Section Managers only
    - **When to submit:** Feedback can only be submitted for the **most recently completed sprint** (Sprint {recent_sprint_num})
    - **Current sprint:** Sprint {current_sprint_num}
    - **One submission per section:** Each Section Manager can submit one feedback per section they manage
    
    ### Feedback Questions
    1. **Overall Satisfaction (1-5):** Rate your overall satisfaction with the sprint
    2. **What went well:** Share positive outcomes and achievements
    3. **What did not go well:** Share challenges and areas for improvement
    
    ### Viewing History
    You can view your previously submitted feedback in the "View Previous Feedback" tab, but you cannot edit past submissions.
    """)
