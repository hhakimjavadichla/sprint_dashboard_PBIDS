"""
Sprint Feedback Page
Bidirectional feedback between Lab Sections and PBIDS Team.
- Section users/managers: Submit feedback about PBIDS support (for their section only)
- PBIDS users: Submit feedback about section collaboration (can select any section)
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from modules.feedback_store import get_feedback_store, FEEDBACK_TYPE_SECTION, FEEDBACK_TYPE_PBIDS
from modules.sprint_calendar import get_sprint_calendar, format_sprint_display
from components.auth import require_auth, display_user_info, get_user_role, get_user_section, is_section_manager, is_team_member
from utils.grid_styles import apply_grid_styles
from utils.constants import VALID_SECTIONS

# Apply styles
apply_grid_styles()

st.title("Sprint Feedback")
st.caption("_Bidirectional feedback between Lab Sections and PBIDS Team_")

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

# Determine user type for feedback
is_pbids_team = is_team_member()  # Admin or PIBIDS User
is_section_user = user_role in ['Section Manager', 'Section User']

# All authenticated users can submit feedback
can_submit_feedback = True

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
if user_role == 'Admin':
    tab1, tab2, tab3 = st.tabs(["Submit Feedback", "View Previous Feedback", "All Feedback (Admin)"])
else:
    tab1, tab2 = st.tabs(["Submit Feedback", "View Previous Feedback"])

with tab1:
    st.subheader(f"Submit Feedback for Sprint {recent_sprint_num}")
    
    if recent_sprint_info is None:
        st.warning(f"Sprint {recent_sprint_num} not found in calendar.")
        st.info("No recent sprint available for feedback.")
    elif recent_sprint_num < 1:
        st.info("No previous sprint available for feedback yet.")
    else:
        # Show sprint info
        sprint_display = format_sprint_display(
            recent_sprint_info.get('SprintName', f'Sprint {recent_sprint_num}'),
            recent_sprint_info.get('SprintStartDt'),
            recent_sprint_info.get('SprintEndDt'),
            recent_sprint_num
        )
        
        st.info(f"**{sprint_display}**")
        
        # Different UI based on user type
        if is_pbids_team:
            # PBIDS Team feedback about sections
            st.markdown("### PBIDS Team Feedback")
            st.caption("Provide feedback about your collaboration with lab sections")
            
            # Section selector for PBIDS users
            available_sections = [s for s in VALID_SECTIONS if s != "PIBIDS"]
            selected_section = st.selectbox(
                "Select Lab Section to provide feedback for:",
                options=available_sections,
                key="pbids_section_select"
            )
            
            if selected_section:
                # Check if feedback already submitted for this section
                if feedback_store.has_feedback(recent_sprint_num, selected_section, username, FEEDBACK_TYPE_PBIDS):
                    st.success(f"Feedback already submitted for {selected_section}")
                    
                    # Show existing feedback
                    existing = feedback_store.get_feedback_for_sprint(recent_sprint_num, selected_section)
                    user_feedback = existing[(existing['SubmittedBy'] == username) & 
                                            (existing.get('FeedbackType', '') == FEEDBACK_TYPE_PBIDS)]
                    if not user_feedback.empty:
                        fb = user_feedback.iloc[0]
                        with st.expander("View your submitted feedback"):
                            st.write(f"**Communication:** {fb.get('CommunicationRating', 'N/A')} / 5")
                            st.write(f"**Responsiveness:** {fb.get('ResponsivenessRating', 'N/A')} / 5")
                            st.write(f"**What went well:** {fb.get('CollaborationWentWell', 'N/A')}")
                            st.write(f"**What could be improved:** {fb.get('CollaborationImprovement', 'N/A')}")
                            st.caption(f"Submitted: {fb['SubmittedAt']}")
                else:
                    # PBIDS feedback form
                    with st.form(key=f"pbids_feedback_form_{selected_section}"):
                        st.markdown(f"**Feedback for: {selected_section}**")
                        
                        communication = st.slider(
                            "a. Communication quality (1-5)",
                            min_value=1,
                            max_value=5,
                            value=3,
                            help="Rate the quality of communication with this section"
                        )
                        
                        responsiveness = st.slider(
                            "b. Responsiveness (1-5)",
                            min_value=1,
                            max_value=5,
                            value=3,
                            help="Rate how responsive this section was to requests and queries"
                        )
                        
                        collab_well = st.text_area(
                            "c. What went well working with this section?",
                            height=100,
                            placeholder="Describe positive aspects of collaboration..."
                        )
                        
                        collab_improve = st.text_area(
                            "d. What could be improved in working with this section?",
                            height=100,
                            placeholder="Describe areas for improvement..."
                        )
                        
                        submitted = st.form_submit_button("Submit PBIDS Feedback", type="primary")
                        
                        if submitted:
                            if not collab_well.strip() and not collab_improve.strip():
                                st.error("Please provide at least one comment")
                            else:
                                success, message = feedback_store.add_pbids_feedback(
                                    sprint_number=recent_sprint_num,
                                    section=selected_section,
                                    submitted_by=username,
                                    communication_rating=communication,
                                    responsiveness_rating=responsiveness,
                                    collaboration_went_well=collab_well.strip(),
                                    collaboration_improvement=collab_improve.strip()
                                )
                                
                                if success:
                                    st.success(f"{message}")
                                    st.rerun()
                                else:
                                    st.error(f"{message}")
        
        elif is_section_user:
            # Section user feedback about PBIDS
            st.markdown("### Section Feedback")
            st.caption("Provide feedback about PBIDS team support for your section")
            
            if not user_sections:
                st.error("No section assigned to your account")
                st.info("Please contact an administrator to assign a section to submit feedback.")
            else:
                # Allow feedback for each section the user belongs to
                for section in user_sections:
                    st.markdown(f"#### Feedback for Section: **{section}**")
                    
                    # Check if feedback already submitted
                    if feedback_store.has_feedback(recent_sprint_num, section, username, FEEDBACK_TYPE_SECTION):
                        st.success(f"Feedback already submitted for {section}")
                        
                        # Show existing feedback
                        existing = feedback_store.get_feedback_for_sprint(recent_sprint_num, section)
                        user_feedback = existing[(existing['SubmittedBy'] == username)]
                        if 'FeedbackType' in existing.columns:
                            user_feedback = user_feedback[user_feedback['FeedbackType'] == FEEDBACK_TYPE_SECTION]
                        if not user_feedback.empty:
                            fb = user_feedback.iloc[0]
                            with st.expander("View your submitted feedback"):
                                st.write(f"**Overall Satisfaction:** {fb['OverallSatisfaction']} / 5")
                                st.write(f"**What went well:** {fb['WhatWentWell']}")
                                st.write(f"**What did not go well:** {fb['WhatDidNotGoWell']}")
                                st.caption(f"Submitted: {fb['SubmittedAt']}")
                    else:
                        # Section feedback form
                        with st.form(key=f"section_feedback_form_{section}"):
                            satisfaction = st.slider(
                                "a. Overall satisfaction with PBIDS support (1-5)",
                                min_value=1,
                                max_value=5,
                                value=3,
                                key=f"satisfaction_{section}"
                            )
                            
                            went_well = st.text_area(
                                "b. What went well?",
                                height=100,
                                key=f"went_well_{section}",
                                placeholder="Share positive outcomes, achievements, and successes..."
                            )
                            
                            did_not_go_well = st.text_area(
                                "c. What did not go well?",
                                height=100,
                                key=f"did_not_go_well_{section}",
                                placeholder="Share challenges, blockers, or areas that need improvement..."
                            )
                            
                            submitted = st.form_submit_button("Submit Section Feedback", type="primary")
                            
                            if submitted:
                                if not went_well.strip() and not did_not_go_well.strip():
                                    st.error("Please provide at least one comment (what went well or what did not go well)")
                                else:
                                    success, message = feedback_store.add_section_feedback(
                                        sprint_number=recent_sprint_num,
                                        section=section,
                                        submitted_by=username,
                                        overall_satisfaction=satisfaction,
                                        what_went_well=went_well.strip(),
                                        what_did_not_go_well=did_not_go_well.strip()
                                    )
                                    
                                    if success:
                                        st.success(f"{message}")
                                        st.rerun()
                                    else:
                                        st.error(f"{message}")
                    
                    st.divider()
        else:
            st.warning("Unable to determine your user type. Please contact an administrator.")

with tab2:
    st.subheader("Your Previous Feedback")
    
    # Section filter for feedback history
    filter_sections = ["All Sections"] + sorted(VALID_SECTIONS)
    selected_filter_section = st.selectbox(
        "Filter by Section:",
        options=filter_sections,
        key="history_section_filter"
    )
    
    # Get all feedback by this user
    user_feedback = feedback_store.get_feedback_by_user(username)
    
    # Apply section filter
    if selected_filter_section != "All Sections" and not user_feedback.empty:
        user_feedback = user_feedback[user_feedback['Section'] == selected_filter_section]
    
    if user_feedback.empty:
        st.info("You haven't submitted any feedback yet." if selected_filter_section == "All Sections" 
                else f"No feedback found for {selected_filter_section}.")
    else:
        # Sort by sprint number descending
        user_feedback = user_feedback.sort_values('SprintNumber', ascending=False)
        
        # Group by sprint
        for sprint_num in user_feedback['SprintNumber'].unique():
            sprint_info = calendar.get_sprint_by_number(int(sprint_num))
            if sprint_info:
                sprint_display = format_sprint_display(sprint_info['SprintName'], sprint_info['SprintStartDt'], sprint_info['SprintEndDt'], int(sprint_num))
            else:
                sprint_display = f'Sprint {sprint_num}'
            
            with st.expander(f"**{sprint_display}**", expanded=(sprint_num == recent_sprint_num)):
                sprint_feedback = user_feedback[user_feedback['SprintNumber'] == sprint_num]
                
                for _, fb in sprint_feedback.iterrows():
                    feedback_type = fb.get('FeedbackType', FEEDBACK_TYPE_SECTION)
                    
                    st.markdown(f"**Section: {fb['Section']}**")
                    
                    if feedback_type == FEEDBACK_TYPE_PBIDS:
                        # PBIDS feedback display
                        st.caption("PBIDS Team Feedback (about section collaboration)")
                        col1, col2, col3 = st.columns([1, 1, 2])
                        with col1:
                            st.metric("Communication", f"{fb.get('CommunicationRating', 'N/A')} / 5")
                        with col2:
                            st.metric("Responsiveness", f"{fb.get('ResponsivenessRating', 'N/A')} / 5")
                        with col3:
                            st.caption(f"Submitted: {fb['SubmittedAt']}")
                        
                        st.markdown("**What went well:**")
                        st.write(fb.get('CollaborationWentWell', '') or "_No comment_")
                        
                        st.markdown("**What could be improved:**")
                        st.write(fb.get('CollaborationImprovement', '') or "_No comment_")
                    else:
                        # Section feedback display
                        st.caption("Section Feedback (about PBIDS support)")
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

# Admin-only tab: View all feedback
if user_role == 'Admin':
    with tab3:
        st.subheader("All Feedback (Admin View)")
        st.caption("Read-only view of all feedback across all sections")
        
        # Reload feedback to get latest data from all sections
        feedback_store.reload()
        
        # Get all feedback
        all_feedback = feedback_store.get_all_feedback()
        
        if all_feedback.empty:
            st.info("No feedback has been submitted yet.")
        else:
            # Sprint filter
            sprint_numbers = sorted(all_feedback['SprintNumber'].unique(), reverse=True)
            # Build sprint options with formatted names
            sprint_option_map = {}
            for s in sprint_numbers:
                s_info = calendar.get_sprint_by_number(int(s))
                if s_info:
                    sprint_option_map[s] = format_sprint_display(s_info['SprintName'], s_info['SprintStartDt'], s_info['SprintEndDt'], int(s))
                else:
                    sprint_option_map[s] = f'Sprint {s}'
            sprint_options = ["All Sprints"] + [sprint_option_map[s] for s in sprint_numbers]
            selected_sprint = st.selectbox("Filter by Sprint", sprint_options, key="admin_sprint_filter")
            
            # Filter by sprint if selected
            if selected_sprint != "All Sprints":
                # Find sprint number from selected option
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
                        sprint_display = format_sprint_display(sprint_info['SprintName'], sprint_info['SprintStartDt'], sprint_info['SprintEndDt'], int(sprint_num))
                    else:
                        sprint_display = f'Sprint {sprint_num}'
                    
                    with st.expander(f"**{sprint_display}**", expanded=(sprint_num == recent_sprint_num)):
                        sprint_feedback = filtered_feedback[filtered_feedback['SprintNumber'] == sprint_num]
                        
                        # Group by section within sprint
                        for section in sorted(sprint_feedback['Section'].unique()):
                            section_feedback = sprint_feedback[sprint_feedback['Section'] == section]
                            
                            st.markdown(f"### {section}")
                            
                            for _, fb in section_feedback.iterrows():
                                feedback_type = fb.get('FeedbackType', FEEDBACK_TYPE_SECTION)
                                
                                if feedback_type == FEEDBACK_TYPE_PBIDS:
                                    # PBIDS feedback display
                                    st.caption("PBIDS Team Feedback (about section collaboration)")
                                    col1, col2, col3, col4 = st.columns([1, 1, 2, 1])
                                    with col1:
                                        st.metric("Communication", f"{fb.get('CommunicationRating', 'N/A')} / 5")
                                    with col2:
                                        st.metric("Responsiveness", f"{fb.get('ResponsivenessRating', 'N/A')} / 5")
                                    with col3:
                                        st.caption(f"Submitted by: **{fb['SubmittedBy']}**")
                                    with col4:
                                        st.caption(f"{fb['SubmittedAt']}")
                                    
                                    st.markdown("**What went well:**")
                                    st.write(fb.get('CollaborationWentWell', '') or "_No comment_")
                                    
                                    st.markdown("**What could be improved:**")
                                    st.write(fb.get('CollaborationImprovement', '') or "_No comment_")
                                else:
                                    # Section feedback display
                                    st.caption("Section Feedback (about PBIDS support)")
                                    col1, col2, col3 = st.columns([1, 2, 1])
                                    with col1:
                                        st.metric("Satisfaction", f"{fb['OverallSatisfaction']} / 5")
                                    with col2:
                                        st.caption(f"Submitted by: **{fb['SubmittedBy']}**")
                                    with col3:
                                        st.caption(f"{fb['SubmittedAt']}")
                                    
                                    st.markdown("**What went well:**")
                                    st.write(fb['WhatWentWell'] if fb['WhatWentWell'] else "_No comment_")
                                    
                                    st.markdown("**What did not go well:**")
                                    st.write(fb['WhatDidNotGoWell'] if fb['WhatDidNotGoWell'] else "_No comment_")
                                
                                st.divider()

# Help section
with st.expander("About Sprint Feedback"):
    st.markdown(f"""
    ### How Sprint Feedback Works
    
    This is a **bidirectional feedback system** between Lab Sections and the PBIDS Team.
    
    **Who can submit:**
    - **Section Users/Managers:** Submit feedback about PBIDS support (for their own section only)
    - **PBIDS Team (Admin/PIBIDS User):** Submit feedback about section collaboration (can select any section)
    
    **When to submit:** Feedback can only be submitted for the **most recently completed sprint** (Sprint {recent_sprint_num})
    
    **Current sprint:** Sprint {current_sprint_num}
    
    ### Feedback Questions
    
    **For Section Users (about PBIDS support):**
    1. Overall Satisfaction (1-5)
    2. What went well
    3. What did not go well
    
    **For PBIDS Team (about section collaboration):**
    1. Communication quality (1-5)
    2. Responsiveness (1-5)
    3. What went well working with this section
    4. What could be improved
    
    ### Viewing History
    You can view your previously submitted feedback in the "View Previous Feedback" tab, filtered by section.
    """)
