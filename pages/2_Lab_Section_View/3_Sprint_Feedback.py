"""
Sprint Feedback Page
Simplified policy: Only section managers can submit feedback.
Each section manager can submit ONE feedback per sprint.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from modules.feedback_store import get_feedback_store, FEEDBACK_TYPE_SECTION
from modules.sprint_calendar import get_sprint_calendar, format_sprint_display
from components.auth import require_auth, display_user_info, get_user_role, get_user_section, is_section_manager, is_admin, is_pbids_viewer, is_section_user, can_submit_feedback
from utils.grid_styles import apply_grid_styles
from utils.constants import VALID_SECTIONS

# Apply styles
apply_grid_styles()

st.title("Sprint Feedback")
st.caption("_Section managers provide feedback about PBIDS support_")

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

# Check if user can submit feedback (Admin, PIBIDS User, Section Manager only)
# PIBIDS Viewer and Section User are view-only
can_submit = can_submit_feedback()

# Get sprint calendar
calendar = get_sprint_calendar()
current_sprint = calendar.get_current_sprint()
all_sprints = calendar.get_all_sprints()

if all_sprints.empty:
    st.error("No sprints configured. Please contact an administrator.")
    st.stop()

# Determine the "recent" sprint (just finished sprint)
if current_sprint is not None:
    current_sprint_num = int(current_sprint['SprintNumber'])
    recent_sprint_num = current_sprint_num - 1
else:
    current_sprint_num = int(all_sprints['SprintNumber'].max())
    recent_sprint_num = current_sprint_num

# Get recent sprint info
recent_sprint_info = calendar.get_sprint_by_number(recent_sprint_num)

# Get feedback store
feedback_store = get_feedback_store()

st.divider()

# Tabs based on role
# Admin and PIBIDS Viewer can see all feedback
if is_admin() or is_pbids_viewer():
    tab1, tab2, tab3 = st.tabs(["Submit Feedback", "View My Feedback", "All Feedback"])
else:
    tab1, tab2 = st.tabs(["Submit Feedback", "View My Feedback"])

# ===== TAB 1: SUBMIT FEEDBACK =====
with tab1:
    st.subheader(f"Submit Feedback for Sprint {recent_sprint_num}")
    
    if not can_submit:
        if is_pbids_viewer():
            st.info("🔒 **View-only access** - PIBIDS Viewers cannot submit feedback.")
        elif is_section_user():
            st.info("🔒 **View-only access** - Section Users cannot submit feedback. Only Section Managers can submit.")
        else:
            st.warning("Only Admin, PIBIDS User, and Section Managers can submit feedback.")
            st.info("If you believe you should have access, please contact an administrator.")
    elif recent_sprint_info is None or recent_sprint_num < 1:
        st.warning(f"Sprint {recent_sprint_num} not found or no previous sprint available.")
    else:
        # Show sprint info
        sprint_display = format_sprint_display(
            recent_sprint_info.get('SprintName', f'Sprint {recent_sprint_num}'),
            recent_sprint_info.get('SprintStartDt'),
            recent_sprint_info.get('SprintEndDt'),
            recent_sprint_num
        )
        st.info(f"**{sprint_display}**")
        
        # Check if user already submitted feedback for this sprint
        if feedback_store.has_user_feedback_for_sprint(recent_sprint_num, username):
            st.success("You have already submitted feedback for this sprint.")
            
            # Show existing feedback
            existing = feedback_store.get_user_feedback_for_sprint(recent_sprint_num, username)
            if not existing.empty:
                fb = existing.iloc[0]
                with st.expander("View your submitted feedback"):
                    st.write(f"**Section:** {fb['Section']}")
                    st.write(f"**Overall Satisfaction:** {fb['OverallSatisfaction']} / 5")
                    timeliness = fb.get('TimelinessRating', 'N/A')
                    st.write(f"**Timeliness of Response:** {timeliness} / 5")
                    st.write(f"**What went well:** {fb['WhatWentWell']}")
                    improved = fb.get('WhatCouldBeImproved') or fb.get('WhatDidNotGoWell', '')
                    st.write(f"**What could be improved:** {improved}")
                    st.caption(f"Submitted: {fb['SubmittedAt']}")
        else:
            if not user_sections:
                st.error("No section assigned to your account.")
                st.info("Please contact an administrator to assign a section.")
            else:
                # Section dropdown for multi-section managers
                if len(user_sections) > 1:
                    selected_section = st.selectbox(
                        "Select your section for this feedback:",
                        options=user_sections,
                        help="Choose which section you are providing feedback for"
                    )
                else:
                    selected_section = user_sections[0]
                    st.markdown(f"**Section:** {selected_section}")
                
                # Feedback form
                with st.form(key="feedback_form"):
                    st.markdown("### Sprint Feedback Survey")
                    st.markdown("""**Instructions:** Please rate each item using the scale below.
- **1** = Strongly Disagree / Very Poor
- **5** = Strongly Agree / Excellent""")
                    
                    st.markdown("---")
                    
                    # Q1: Overall Satisfaction
                    st.markdown("**Q1. Overall Satisfaction with This Sprint**")
                    st.caption("How satisfied were you with the outcomes and support provided during this sprint?")
                    satisfaction_options = {
                        1: "1 - Very dissatisfied",
                        2: "2 - Dissatisfied",
                        3: "3 - Neutral",
                        4: "4 - Satisfied",
                        5: "5 - Very satisfied"
                    }
                    satisfaction = st.radio(
                        "Select your rating:",
                        options=[1, 2, 3, 4, 5],
                        format_func=lambda x: satisfaction_options[x],
                        index=None,
                        key="q1_satisfaction",
                        horizontal=True
                    )
                    
                    st.markdown("---")
                    
                    # Q2: Timeliness
                    st.markdown("**Q2. Timeliness of Response to Queries (within 24 hours)**")
                    st.caption("How would you rate the team's responsiveness to your questions or requests during this sprint?")
                    timeliness_options = {
                        1: "1 - Very poor (responses were rarely timely)",
                        2: "2 - Poor",
                        3: "3 - Acceptable",
                        4: "4 - Good",
                        5: "5 - Excellent (responses were consistently within 24 hours)"
                    }
                    timeliness = st.radio(
                        "Select your rating:",
                        options=[1, 2, 3, 4, 5],
                        format_func=lambda x: timeliness_options[x],
                        index=None,
                        key="q2_timeliness",
                        horizontal=True
                    )
                    
                    st.markdown("---")
                    
                    # Q3: What went well
                    st.markdown("**Q3. What went well during this sprint?**")
                    went_well = st.text_area(
                        "Your response:",
                        height=100,
                        placeholder="Share positive outcomes, achievements, and successes...",
                        key="q3_went_well",
                        label_visibility="collapsed"
                    )
                    
                    st.markdown("---")
                    
                    # Q4: What could be improved
                    st.markdown("**Q4. What could be improved for the next sprint?**")
                    could_improve = st.text_area(
                        "Your response:",
                        height=100,
                        placeholder="Share suggestions for improvement...",
                        key="q4_improve",
                        label_visibility="collapsed"
                    )
                    
                    st.markdown("---")
                    
                    submitted = st.form_submit_button("Submit Feedback", type="primary")
                    
                    if submitted:
                        # Validate required ratings
                        if satisfaction is None:
                            st.error("Please select a rating for Q1 (Overall Satisfaction).")
                        elif timeliness is None:
                            st.error("Please select a rating for Q2 (Timeliness of Response).")
                        elif not went_well.strip() and not could_improve.strip():
                            st.error("Please provide at least one comment (Q3 or Q4).")
                        else:
                            success, message = feedback_store.add_section_feedback(
                                sprint_number=recent_sprint_num,
                                section=selected_section,
                                submitted_by=username,
                                overall_satisfaction=satisfaction,
                                timeliness_rating=timeliness,
                                what_went_well=went_well.strip(),
                                what_could_be_improved=could_improve.strip()
                            )
                            
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)

# ===== TAB 2: VIEW MY FEEDBACK =====
with tab2:
    st.subheader("Your Previous Feedback")
    
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
            if sprint_info:
                sprint_display = format_sprint_display(
                    sprint_info['SprintName'],
                    sprint_info['SprintStartDt'],
                    sprint_info['SprintEndDt'],
                    int(sprint_num)
                )
            else:
                sprint_display = f'Sprint {sprint_num}'
            
            with st.expander(f"**{sprint_display}**", expanded=(sprint_num == recent_sprint_num)):
                sprint_feedback = user_feedback[user_feedback['SprintNumber'] == sprint_num]
                
                for _, fb in sprint_feedback.iterrows():
                    st.markdown(f"**Section:** {fb['Section']}")
                    
                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        st.metric("Satisfaction", f"{fb['OverallSatisfaction']} / 5")
                    with col2:
                        timeliness = fb.get('TimelinessRating', 'N/A')
                        st.metric("Timeliness", f"{timeliness} / 5" if timeliness != 'N/A' else "N/A")
                    with col3:
                        st.caption(f"Submitted: {fb['SubmittedAt']}")
                    
                    st.markdown("**What went well:**")
                    st.write(fb['WhatWentWell'] if fb['WhatWentWell'] else "_No comment_")
                    
                    st.markdown("**What could be improved:**")
                    improved = fb.get('WhatCouldBeImproved') or fb.get('WhatDidNotGoWell', '')
                    st.write(improved if improved else "_No comment_")
                    
                    st.divider()

# ===== TAB 3: ALL FEEDBACK VIEW (Admin and PIBIDS Viewer) ===
if is_admin() or is_pbids_viewer():
    with tab3:
        st.subheader("All Feedback")
        st.caption("View all feedback submitted by section managers")
        
        # Reload to get latest data
        feedback_store.reload()
        
        # Get all feedback
        all_feedback = feedback_store.get_all_feedback()
        
        if all_feedback.empty:
            st.info("No feedback has been submitted yet.")
        else:
            # Sprint filter
            sprint_numbers = sorted(all_feedback['SprintNumber'].unique(), reverse=True)
            sprint_option_map = {}
            for s in sprint_numbers:
                s_info = calendar.get_sprint_by_number(int(s))
                if s_info:
                    sprint_option_map[s] = format_sprint_display(
                        s_info['SprintName'],
                        s_info['SprintStartDt'],
                        s_info['SprintEndDt'],
                        int(s)
                    )
                else:
                    sprint_option_map[s] = f'Sprint {s}'
            
            sprint_options = ["All Sprints"] + [sprint_option_map[s] for s in sprint_numbers]
            selected_sprint = st.selectbox("Filter by Sprint", sprint_options, key="admin_sprint_filter")
            
            # Filter by sprint if selected
            if selected_sprint != "All Sprints":
                sprint_num = None
                for s, label in sprint_option_map.items():
                    if label == selected_sprint:
                        sprint_num = s
                        break
                if sprint_num is not None:
                    filtered_feedback = all_feedback[all_feedback['SprintNumber'] == sprint_num]
                else:
                    filtered_feedback = all_feedback
            else:
                filtered_feedback = all_feedback
            
            # Sort by sprint (descending), then section
            filtered_feedback = filtered_feedback.sort_values(
                ['SprintNumber', 'Section'], ascending=[False, True]
            )
            
            if filtered_feedback.empty:
                st.info("No feedback matches the filter.")
            else:
                # Group by sprint
                for sprint_num in filtered_feedback['SprintNumber'].unique():
                    sprint_info = calendar.get_sprint_by_number(int(sprint_num))
                    if sprint_info:
                        sprint_display = format_sprint_display(
                            sprint_info['SprintName'],
                            sprint_info['SprintStartDt'],
                            sprint_info['SprintEndDt'],
                            int(sprint_num)
                        )
                    else:
                        sprint_display = f'Sprint {sprint_num}'
                    
                    with st.expander(f"**{sprint_display}**", expanded=(sprint_num == recent_sprint_num)):
                        sprint_feedback = filtered_feedback[filtered_feedback['SprintNumber'] == sprint_num]
                        
                        for _, fb in sprint_feedback.iterrows():
                            # Show user name and role
                            submitter = fb['SubmittedBy']
                            section = fb['Section']
                            
                            st.markdown(f"### Feedback from: **{submitter}**")
                            st.caption(f"Section Manager of **{section}**")
                            
                            col1, col2, col3 = st.columns([1, 1, 2])
                            with col1:
                                st.metric("Satisfaction", f"{fb['OverallSatisfaction']} / 5")
                            with col2:
                                timeliness = fb.get('TimelinessRating', 'N/A')
                                st.metric("Timeliness", f"{timeliness} / 5" if timeliness != 'N/A' else "N/A")
                            with col3:
                                st.caption(f"Submitted: {fb['SubmittedAt']}")
                            
                            st.markdown("**What went well:**")
                            st.write(fb['WhatWentWell'] if fb['WhatWentWell'] else "_No comment_")
                            
                            st.markdown("**What could be improved:**")
                            improved = fb.get('WhatCouldBeImproved') or fb.get('WhatDidNotGoWell', '')
                            st.write(improved if improved else "_No comment_")
                            
                            st.divider()

# Help section
with st.expander("About Sprint Feedback"):
    st.markdown(f"""
    ### How Sprint Feedback Works
    
    **Who can submit:**
    - Only **Section Managers** can submit feedback
    - Each section manager can submit **one feedback per sprint**
    - If you manage multiple sections, select which section to provide feedback for
    
    **When to submit:** 
    Feedback is for the most recently completed sprint (Sprint {recent_sprint_num})
    
    **Current sprint:** Sprint {current_sprint_num}
    
    ### Feedback Questions
    
    1. **Overall Satisfaction (1-5)** - Rate your satisfaction with outcomes and support
    2. **Timeliness of Response (1-5)** - Rate the team's responsiveness to queries
    3. **What went well** - Share positive outcomes and successes
    4. **What could be improved** - Share suggestions for improvement
    
    ### Viewing History
    View your previously submitted feedback in the "View My Feedback" tab.
    """)
