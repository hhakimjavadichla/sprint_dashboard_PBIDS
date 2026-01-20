"""
Feature Requests & Revisions Tracking Page
Admin-only page for tracking feature requests, revisions, and other changes.
"""
import streamlit as st
import pandas as pd
import os
from datetime import datetime
from pathlib import Path
from components.auth import require_admin, display_user_info

# Data file path
DATA_DIR = Path(__file__).parent.parent / 'data'
REQUESTS_FILE = DATA_DIR / 'feature_requests.csv'

# Field definitions
CATEGORIES = ['Feature Request', 'Revision', 'Layout', 'Spelling/Typo', 'Bug Fix', 'Question', 'Other']
REQUEST_STATUS = ['Suggestion', "Let's Discuss", 'Approved', 'Rejected']
IMPLEMENTATION_STATUS = ['Not Started', 'In Progress', 'Completed', 'On Hold', 'Cancelled']

# Column definitions
COLUMNS = [
    'RequestID',
    'Request',
    'Category',
    'RequestDate',
    'RequestedBy',
    'Status',
    'Response',
    'ImplementationStatus',
    'ImplementationDate',
    'ConfirmImplemented'
]


def load_requests() -> pd.DataFrame:
    """Load feature requests from CSV file."""
    if os.path.exists(REQUESTS_FILE):
        try:
            df = pd.read_csv(REQUESTS_FILE, dtype=str)
            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = ''
            return df
        except Exception as e:
            st.error(f"Error loading requests: {e}")
            return pd.DataFrame(columns=COLUMNS)
    return pd.DataFrame(columns=COLUMNS)


def save_requests(df: pd.DataFrame):
    """Save feature requests to CSV file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(REQUESTS_FILE, index=False)


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}"


# Page setup
st.title("📝 Feature Requests & Revisions")
st.caption("_Track feature requests, revisions, and other changes — Admin Only_")

# Require admin access
require_admin("Feature Requests")
display_user_info()

# Page description
with st.expander("ℹ️ How to use this page", expanded=False):
    st.markdown("""
    This page allows admins to **submit and track requests** for new features, revisions, 
    layout changes, bug fixes, or any other improvements to the dashboard.
    
    **Submitting a request:** Use the "New Request" tab to describe what you need. 
    Select a category and submit. Each request gets a unique ID for tracking.
    
    **Tracking progress:** The "View Requests" tab shows all submitted requests. 
    You can filter by category, status, or implementation state. Click on any request 
    to expand it and update its status, add a response, or mark it as implemented.
    
    **Status workflow:** Requests start as "Suggestion" and move through 
    "Let's Discuss" → "Approved" (or "Rejected"). Once approved, the implementation 
    status tracks progress from "Not Started" through "In Progress" to "Completed".
    """)

# Load existing requests
requests_df = load_requests()

# Tabs
tab1, tab2 = st.tabs(["📋 View Requests", "➕ New Request"])

# ============================================================================
# VIEW REQUESTS TAB
# ============================================================================
with tab1:
    st.subheader("All Requests")
    
    if requests_df.empty:
        st.info("No requests yet. Use the 'New Request' tab to add one.")
    else:
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_category = st.multiselect(
                "Filter by Category",
                options=CATEGORIES,
                default=[]
            )
        with col2:
            filter_status = st.multiselect(
                "Filter by Status",
                options=REQUEST_STATUS,
                default=[]
            )
        with col3:
            filter_impl_status = st.multiselect(
                "Filter by Implementation",
                options=IMPLEMENTATION_STATUS,
                default=[]
            )
        
        # Apply filters
        filtered_df = requests_df.copy()
        if filter_category:
            filtered_df = filtered_df[filtered_df['Category'].isin(filter_category)]
        if filter_status:
            filtered_df = filtered_df[filtered_df['Status'].isin(filter_status)]
        if filter_impl_status:
            filtered_df = filtered_df[filtered_df['ImplementationStatus'].isin(filter_impl_status)]
        
        st.markdown(f"**Showing {len(filtered_df)} of {len(requests_df)} requests**")
        
        # Display each request as an expandable card
        for idx, row in filtered_df.iterrows():
            request_id = row.get('RequestID', f'REQ-{idx}')
            category = row.get('Category', 'Other')
            status = row.get('Status', 'Suggestion')
            impl_status = row.get('ImplementationStatus', 'Not Started')
            
            # Status color coding
            status_emoji = {
                'Suggestion': '💡',
                "Let's Discuss": '💬',
                'Approved': '✅',
                'Rejected': '❌'
            }.get(status, '📌')
            
            impl_emoji = {
                'Not Started': '⏳',
                'In Progress': '🔄',
                'Completed': '✅',
                'On Hold': '⏸️',
                'Cancelled': '🚫'
            }.get(impl_status, '📌')
            
            with st.expander(f"{status_emoji} **{request_id}** | {category} | {impl_emoji} {impl_status}"):
                # Display request details
                st.markdown(f"**Request:** {row.get('Request', '')}")
                st.markdown(f"**Requested by:** {row.get('RequestedBy', 'Unknown')} on {row.get('RequestDate', 'Unknown')}")
                
                st.divider()
                
                # Editable fields
                col1, col2 = st.columns(2)
                
                with col1:
                    new_status = st.selectbox(
                        "Status",
                        options=REQUEST_STATUS,
                        index=REQUEST_STATUS.index(status) if status in REQUEST_STATUS else 0,
                        key=f"status_{request_id}"
                    )
                
                with col2:
                    new_impl_status = st.selectbox(
                        "Implementation Status",
                        options=IMPLEMENTATION_STATUS,
                        index=IMPLEMENTATION_STATUS.index(impl_status) if impl_status in IMPLEMENTATION_STATUS else 0,
                        key=f"impl_status_{request_id}"
                    )
                
                new_response = st.text_area(
                    "Response from Implementer",
                    value=row.get('Response', ''),
                    key=f"response_{request_id}"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    impl_date = row.get('ImplementationDate', '')
                    new_impl_date = st.text_input(
                        "Implementation Date",
                        value=impl_date,
                        placeholder="YYYY-MM-DD",
                        key=f"impl_date_{request_id}"
                    )
                
                with col2:
                    confirmed = row.get('ConfirmImplemented', '') == 'Yes'
                    new_confirmed = st.checkbox(
                        "Confirm Implemented",
                        value=confirmed,
                        key=f"confirmed_{request_id}"
                    )
                
                # Save button
                if st.button("💾 Save Changes", key=f"save_{request_id}"):
                    requests_df.loc[idx, 'Status'] = new_status
                    requests_df.loc[idx, 'ImplementationStatus'] = new_impl_status
                    requests_df.loc[idx, 'Response'] = new_response
                    requests_df.loc[idx, 'ImplementationDate'] = new_impl_date
                    requests_df.loc[idx, 'ConfirmImplemented'] = 'Yes' if new_confirmed else 'No'
                    
                    save_requests(requests_df)
                    st.success("Changes saved!")
                    st.rerun()

# ============================================================================
# NEW REQUEST TAB
# ============================================================================
with tab2:
    st.subheader("Submit New Request")
    
    with st.form("new_request_form"):
        request_text = st.text_area(
            "Request *",
            placeholder="Describe the feature, revision, or question...",
            height=150
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            category = st.selectbox(
                "Category *",
                options=CATEGORIES
            )
        
        with col2:
            status = st.selectbox(
                "Initial Status",
                options=REQUEST_STATUS,
                index=0
            )
        
        submitted = st.form_submit_button("📤 Submit Request", type="primary")
        
        if submitted:
            if not request_text.strip():
                st.error("Please enter a request description")
            else:
                # Create new request
                new_request = {
                    'RequestID': generate_request_id(),
                    'Request': request_text.strip(),
                    'Category': category,
                    'RequestDate': datetime.now().strftime('%Y-%m-%d'),
                    'RequestedBy': st.session_state.get('username', 'Unknown'),
                    'Status': status,
                    'Response': '',
                    'ImplementationStatus': 'Not Started',
                    'ImplementationDate': '',
                    'ConfirmImplemented': 'No'
                }
                
                # Add to dataframe
                new_df = pd.DataFrame([new_request])
                requests_df = pd.concat([requests_df, new_df], ignore_index=True)
                
                save_requests(requests_df)
                st.success(f"✅ Request submitted! ID: {new_request['RequestID']}")
                st.rerun()

# ============================================================================
# SUMMARY SECTION
# ============================================================================
st.divider()
st.subheader("📊 Summary")

if not requests_df.empty:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total = len(requests_df)
        st.metric("Total Requests", total)
    
    with col2:
        pending = len(requests_df[requests_df['Status'].isin(['Suggestion', "Let's Discuss"])])
        st.metric("Pending Review", pending)
    
    with col3:
        approved = len(requests_df[requests_df['Status'] == 'Approved'])
        st.metric("Approved", approved)
    
    with col4:
        completed = len(requests_df[requests_df['ImplementationStatus'] == 'Completed'])
        st.metric("Completed", completed)
else:
    st.info("No requests to summarize yet.")
