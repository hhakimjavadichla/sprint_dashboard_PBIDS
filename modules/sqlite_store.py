"""
SQLite data access helpers for task and worklog stores.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional

import pandas as pd

from modules.sqlite_db import connect, get_db_path, initialize_db


def is_sqlite_enabled() -> bool:
    """Check if SQLite mode is enabled. 
    
    SQLite mode is automatically enabled when Snowflake is enabled in secrets.toml.
    Can also be enabled via environment variable for backward compatibility.
    """
    # Check environment variable (backward compatibility)
    env_value = os.environ.get("SPRINT_DASHBOARD_USE_SQLITE", "").strip().lower()
    if env_value in {"1", "true", "yes", "on"}:
        return True
    
    # Check if Snowflake is enabled in secrets.toml - if so, SQLite is also enabled
    from modules.snowflake_connector import is_snowflake_enabled
    return is_snowflake_enabled()


def sync_from_snowflake(db_path: Optional[str] = None) -> dict:
    """
    Sync task and worklog data from Snowflake into SQLite.
    
    - iTrack fields (Status, AssignedTo, dates) are updated from Snowflake
    - Dashboard annotations (Priority, Comments, SprintsAssigned) are preserved
    - New tasks are added, existing tasks are updated
    
    Returns:
        dict with sync statistics
    """
    from modules.snowflake_connector import (
        fetch_tasks_from_snowflake,
        fetch_worklogs_from_snowflake,
        clear_snowflake_cache,
        is_snowflake_configured,
    )
    
    stats = {
        'success': False,
        'message': '',
        'tasks_before': 0,
        'tasks_after': 0,
        'new_tasks': 0,
        'updated_tasks': 0,
        'unchanged_tasks': 0,
        # Task/Ticket field update counts
        'task_status_changes': [],
        'ticket_status_changed': 0,
        'task_owner_changed': 0,
        'section_changed': 0,
        'ticket_type_changed': 0,
        'subject_changed': 0,
        'task_resolved_changed': 0,
        'ticket_resolved_changed': 0,
        'customer_name_changed': 0,
        'new_tasks_by_status': {},
        # Worklog stats
        'worklogs_before': 0,
        'worklogs_after': 0,
        'new_worklogs': 0,
        'worklogs_updated': 0,
        'worklog_minutes_changed': 0,
        'worklog_description_changed': 0,
        'worklog_logdate_changed': 0,
    }
    
    if not is_snowflake_configured():
        stats['message'] = "Snowflake is not configured"
        return stats
    
    path = get_db_path(db_path)
    conn = connect(path)
    initialize_db(conn)
    
    try:
        # Clear Snowflake cache to get fresh data
        clear_snowflake_cache()
        
        # Load existing data from SQLite for comparison (all fields that can be updated)
        existing_tasks = pd.read_sql_query(
            """SELECT t.task_num, t.task_status, t.assigned_to, t.task_resolved_dt,
                      tk.ticket_num, tk.ticket_status, tk.section, tk.ticket_type,
                      tk.subject, tk.ticket_resolved_dt, tk.customer_name
               FROM tasks t
               LEFT JOIN tickets tk ON t.ticket_num = tk.ticket_num""", conn
        )
        existing_task_nums = set(existing_tasks['task_num'].astype(str).tolist())
        # Create lookup dict for existing task/ticket data
        existing_data = {}
        for _, row in existing_tasks.iterrows():
            existing_data[str(row['task_num'])] = {
                'task_status': str(row['task_status'] or ''),
                'assigned_to': str(row['assigned_to'] or ''),
                'task_resolved_dt': str(row['task_resolved_dt'] or ''),
                'ticket_status': str(row['ticket_status'] or ''),
                'section': str(row['section'] or ''),
                'ticket_type': str(row['ticket_type'] or ''),
                'subject': str(row['subject'] or ''),
                'ticket_resolved_dt': str(row['ticket_resolved_dt'] or ''),
                'customer_name': str(row['customer_name'] or ''),
            }
        stats['tasks_before'] = len(existing_task_nums)
        
        # Load existing annotations to preserve them
        existing_annotations = pd.read_sql_query(
            """SELECT task_num, sprints_assigned, customer_priority, final_priority,
                      goal_type, hours_estimated, dependency_on, dependencies_lead,
                      dependency_secured, comments, status_update_dt
               FROM dashboard_task_annotations""", conn
        )
        annotations_dict = {}
        for _, row in existing_annotations.iterrows():
            annotations_dict[str(row['task_num'])] = row.to_dict()
        
        # Fetch fresh data from Snowflake
        snowflake_df, success, message = fetch_tasks_from_snowflake()
        
        if not success or snowflake_df.empty:
            stats['message'] = f"Failed to fetch from Snowflake: {message}"
            return stats
        
        # Import ALL tasks from Snowflake - no date filter during sync
        # Date/status filtering is done at the app display level, not during import
        snowflake_df['TaskCreatedDt'] = pd.to_datetime(snowflake_df['TaskCreatedDt'], errors='coerce')
        
        # Extract TicketType from Subject if not already present
        if 'TicketType' not in snowflake_df.columns or snowflake_df['TicketType'].isna().all():
            snowflake_df['TicketType'] = snowflake_df['Subject'].apply(_extract_ticket_type)
        
        # Section comes from Snowflake incident table - keep NULL values as-is
        
        # Track changes - field-level statistics
        new_task_nums = set()
        updated_count = 0
        unchanged_count = 0
        status_changes = []
        new_by_status = {}
        
        # Merge with existing annotations and track field-level changes
        for idx, row in snowflake_df.iterrows():
            task_num = str(row['TaskNum'])
            
            if task_num in existing_task_nums:
                # Existing task - compare each field
                old = existing_data.get(task_num, {})
                new_status = str(row.get('TaskStatus', '') or '')
                new_assigned = str(row.get('AssignedTo', '') or '')
                new_task_resolved = str(row.get('TaskResolvedDt', '') or '')
                new_ticket_status = str(row.get('TicketStatus', '') or '')
                new_section = str(row.get('Section', '') or '')
                new_ticket_type = str(row.get('TicketType', '') or '')
                new_subject = str(row.get('Subject', '') or '')
                new_ticket_resolved = str(row.get('TicketResolvedDt', '') or '')
                new_customer = str(row.get('CustomerName', '') or '')
                
                has_changes = False
                
                if old.get('task_status', '') != new_status:
                    status_changes.append({
                        'task_num': task_num,
                        'old_status': old.get('task_status', ''),
                        'new_status': new_status
                    })
                    has_changes = True
                
                if old.get('assigned_to', '') != new_assigned:
                    stats['task_owner_changed'] += 1
                    has_changes = True
                
                if old.get('task_resolved_dt', '') != new_task_resolved:
                    stats['task_resolved_changed'] += 1
                    has_changes = True
                
                if old.get('ticket_status', '') != new_ticket_status:
                    stats['ticket_status_changed'] += 1
                    has_changes = True
                
                if old.get('section', '') != new_section:
                    stats['section_changed'] += 1
                    has_changes = True
                
                if old.get('ticket_type', '') != new_ticket_type:
                    stats['ticket_type_changed'] += 1
                    has_changes = True
                
                if old.get('subject', '') != new_subject:
                    stats['subject_changed'] += 1
                    has_changes = True
                
                if old.get('ticket_resolved_dt', '') != new_ticket_resolved:
                    stats['ticket_resolved_changed'] += 1
                    has_changes = True
                
                if old.get('customer_name', '') != new_customer:
                    stats['customer_name_changed'] += 1
                    has_changes = True
                
                if has_changes:
                    updated_count += 1
                else:
                    unchanged_count += 1
            else:
                # New task
                new_task_nums.add(task_num)
                status = str(row.get('TaskStatus', 'Unknown'))
                new_by_status[status] = new_by_status.get(status, 0) + 1
            
            # Preserve existing annotations if they exist
            if task_num in annotations_dict:
                ann = annotations_dict[task_num]
                snowflake_df.at[idx, 'SprintsAssigned'] = ann.get('sprints_assigned', '')
                snowflake_df.at[idx, 'CustomerPriority'] = ann.get('customer_priority')
                snowflake_df.at[idx, 'FinalPriority'] = ann.get('final_priority')
                snowflake_df.at[idx, 'GoalType'] = ann.get('goal_type', '')
                snowflake_df.at[idx, 'HoursEstimated'] = ann.get('hours_estimated')
                snowflake_df.at[idx, 'DependencyOn'] = ann.get('dependency_on', '')
                snowflake_df.at[idx, 'DependenciesLead'] = ann.get('dependencies_lead', '')
                snowflake_df.at[idx, 'DependencySecured'] = ann.get('dependency_secured', '')
                snowflake_df.at[idx, 'Comments'] = ann.get('comments', '')
                snowflake_df.at[idx, 'StatusUpdateDt'] = ann.get('status_update_dt')
        
        # Save to SQLite
        _upsert_tasks(conn, snowflake_df)
        conn.commit()
        
        stats['new_tasks'] = len(new_task_nums)
        stats['updated_tasks'] = updated_count
        stats['unchanged_tasks'] = unchanged_count
        stats['new_tasks_by_status'] = new_by_status
        stats['task_status_changes'] = status_changes
        stats['tasks_after'] = len(snowflake_df)
        
        # Now sync worklogs with field-level tracking
        existing_worklogs = pd.read_sql_query(
            "SELECT record_id, minutes_spent, description, log_date FROM worklogs", conn
        )
        existing_worklog_ids = set(existing_worklogs['record_id'].astype(str).tolist())
        # Create lookup for existing worklog data
        existing_wl_data = {}
        for _, row in existing_worklogs.iterrows():
            existing_wl_data[str(row['record_id'])] = {
                'minutes_spent': str(row['minutes_spent'] or ''),
                'description': str(row['description'] or ''),
                'log_date': str(row['log_date'] or ''),
            }
        stats['worklogs_before'] = len(existing_worklog_ids)
        
        worklog_df, wl_success, wl_message = fetch_worklogs_from_snowflake()
        
        if wl_success and not worklog_df.empty:
            # Track worklog field-level changes
            worklogs_updated = 0
            for _, row in worklog_df.iterrows():
                record_id = str(row.get('RecordId', ''))
                if record_id in existing_wl_data:
                    old_wl = existing_wl_data[record_id]
                    new_minutes = str(row.get('MinutesSpent', '') or '')
                    new_desc = str(row.get('Description', '') or '')
                    new_logdate = str(row.get('LogDate', '') or '')
                    
                    has_wl_changes = False
                    if old_wl.get('minutes_spent', '') != new_minutes:
                        stats['worklog_minutes_changed'] += 1
                        has_wl_changes = True
                    if old_wl.get('description', '') != new_desc:
                        stats['worklog_description_changed'] += 1
                        has_wl_changes = True
                    if old_wl.get('log_date', '') != new_logdate:
                        stats['worklog_logdate_changed'] += 1
                        has_wl_changes = True
                    
                    if has_wl_changes:
                        worklogs_updated += 1
            
            stats['worklogs_updated'] = worklogs_updated
            
            # Disable FK checks for worklogs
            conn.execute("PRAGMA foreign_keys = OFF")
            _upsert_worklogs(conn, worklog_df)
            conn.commit()
            
            current_worklog_ids = set(worklog_df['RecordId'].astype(str).tolist())
            stats['new_worklogs'] = len(current_worklog_ids - existing_worklog_ids)
            stats['worklogs_after'] = len(worklog_df)
        
        stats['success'] = True
        stats['message'] = f"Synced {len(snowflake_df)} tasks and {len(worklog_df) if wl_success else 0} worklogs from Snowflake"
        
    except Exception as e:
        stats['message'] = f"Sync failed: {str(e)}"
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
    
    return stats


def load_task_view(db_path: Optional[str] = None) -> pd.DataFrame:
    path = get_db_path(db_path)
    if not os.path.exists(path):
        return pd.DataFrame()
    conn = connect(path)
    initialize_db(conn)
    try:
        return pd.read_sql_query("SELECT * FROM task_flat_view", conn)
    finally:
        conn.close()


def load_worklogs(db_path: Optional[str] = None) -> pd.DataFrame:
    path = get_db_path(db_path)
    if not os.path.exists(path):
        return pd.DataFrame()
    conn = connect(path)
    initialize_db(conn)
    try:
        return pd.read_sql_query(
            """
            SELECT
              record_id AS RecordId,
              task_num AS TaskNum,
              owner AS Owner,
              minutes_spent AS MinutesSpent,
              description AS Description,
              log_date AS LogDate,
              sprint_number AS SprintNumber,
              imported_at AS ImportedAt
            FROM worklogs
            """,
            conn,
        )
    finally:
        conn.close()


def save_tasks(db_path: Optional[str], tasks_df: pd.DataFrame) -> bool:
    if tasks_df is None or tasks_df.empty:
        return True
    path = get_db_path(db_path)
    conn = connect(path)
    initialize_db(conn)
    try:
        _upsert_tasks(conn, tasks_df)
        conn.commit()
        return True
    except Exception as exc:
        print(f"SQLite save_tasks failed: {exc}")
        return False
    finally:
        conn.close()


def save_worklogs(db_path: Optional[str], worklog_df: pd.DataFrame) -> bool:
    if worklog_df is None or worklog_df.empty:
        return True
    path = get_db_path(db_path)
    conn = connect(path)
    initialize_db(conn)
    try:
        # Disable FK checks - worklogs may reference tasks not yet imported
        conn.execute("PRAGMA foreign_keys = OFF")
        _upsert_worklogs(conn, worklog_df)
        conn.commit()
        return True
    except Exception as exc:
        print(f"SQLite save_worklogs failed: {exc}")
        return False
    finally:
        conn.close()


def _clean_value(value: object) -> Optional[object]:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.lower() in {"nan", "none", "null"}:
            return None
        return text
    return value


def _to_datetime_str(value: object) -> Optional[str]:
    """Convert datetime/Timestamp to ISO format string for SQLite."""
    if value is None or pd.isna(value):
        return None
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in {"nan", "none", "null", "nat"}:
            return None
        return text
    return str(value) if value else None


def _to_int(value: object) -> Optional[int]:
    cleaned = _clean_value(value)
    if cleaned is None:
        return None
    try:
        return int(float(cleaned))
    except (TypeError, ValueError):
        return None


def _to_float(value: object) -> Optional[float]:
    cleaned = _clean_value(value)
    if cleaned is None:
        return None
    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return None


def _parse_sprints(value: object) -> List[int]:
    cleaned = _clean_value(value)
    if cleaned is None:
        return []
    parts = [p.strip() for p in str(cleaned).split(",")]
    sprint_numbers: List[int] = []
    for part in parts:
        if not part:
            continue
        try:
            sprint_numbers.append(int(float(part)))
        except (ValueError, TypeError):
            continue
    return sorted(set(sprint_numbers))


def _extract_ticket_type(subject: Optional[str]) -> str:
    if not subject:
        return "NC"
    subject_upper = subject.upper()
    if "LAB-IR" in subject_upper or "-IR:" in subject_upper:
        return "IR"
    if "LAB-SR" in subject_upper or "-SR:" in subject_upper:
        return "SR"
    if "LAB-PR" in subject_upper or "-PR:" in subject_upper:
        return "PR"
    if "LAB-AD" in subject_upper or "-AD:" in subject_upper:
        return "AD"
    if "LAB INCIDENT" in subject_upper:
        return "IR"
    return "NC"


def _upsert_tasks(conn, tasks_df: pd.DataFrame) -> None:
    df = tasks_df.copy()
    required_columns = [
        "TaskNum",
        "TicketNum",
        "TaskStatus",
        "AssignedTo",
        "TaskAssignedDt",
        "TaskCreatedDt",
        "TaskResolvedDt",
        "TaskMinutesSpent",
        "UniqueTaskId",
        "OriginalSprintNumber",
        "SprintNumber",
        "SprintsAssigned",
        "CustomerPriority",
        "FinalPriority",
        "GoalType",
        "HoursEstimated",
        "DependencyOn",
        "DependenciesLead",
        "DependencySecured",
        "Comments",
        "StatusUpdateDt",
        "TicketStatus",
        "TicketCreatedDt",
        "TicketResolvedDt",
        "TicketTotalTimeSpent",
        "Subject",
        "CustomerName",
        "Section",
        "TicketType",
    ]
    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    ticket_rows = []
    task_rows = []
    annotation_rows = []
    delete_sprint_rows = []
    sprint_rows = []

    # Pre-compute TicketType from earliest task's subject per ticket
    # Group by ticket and find earliest task (by TaskCreatedDt)
    ticket_type_map = {}
    for ticket_num, group in df.groupby("TicketNum"):
        if pd.isna(ticket_num):
            continue
        # Sort by TaskCreatedDt to find earliest task
        group_sorted = group.sort_values("TaskCreatedDt", na_position="last")
        earliest_subject = _clean_value(group_sorted.iloc[0].get("Subject"))
        ticket_type_map[str(ticket_num)] = _extract_ticket_type(earliest_subject)

    for _, row in df.iterrows():
        task_num = _clean_value(row.get("TaskNum"))
        ticket_num = _clean_value(row.get("TicketNum"))
        if not task_num or not ticket_num:
            continue

        task_subject = _clean_value(row.get("Subject"))
        # TicketType derived from earliest task's subject per ticket
        ticket_type = _clean_value(row.get("TicketType")) or ticket_type_map.get(ticket_num, "NC")

        ticket_rows.append(
            (
                ticket_num,
                _clean_value(row.get("TicketStatus")),
                _to_datetime_str(row.get("TicketCreatedDt")),
                _to_datetime_str(row.get("TicketResolvedDt")),
                _to_float(row.get("TicketTotalTimeSpent")),
                task_subject,  # TicketSubject defaults to first task's subject
                _clean_value(row.get("CustomerName")),
                _clean_value(row.get("Section")),
                ticket_type,
                "local",
            )
        )

        sprints_assigned = _clean_value(row.get("SprintsAssigned"))
        sprint_list = _parse_sprints(sprints_assigned)
        last_sprint_number = _to_int(row.get("SprintNumber"))
        if last_sprint_number is None and sprint_list:
            last_sprint_number = max(sprint_list)

        task_rows.append(
            (
                task_num,
                ticket_num,
                _clean_value(row.get("TaskStatus")),
                task_subject,
                _clean_value(row.get("AssignedTo")),
                _to_datetime_str(row.get("TaskAssignedDt")),
                _to_datetime_str(row.get("TaskCreatedDt")),
                _to_datetime_str(row.get("TaskResolvedDt")),
                _to_float(row.get("TaskMinutesSpent")),
                _clean_value(row.get("UniqueTaskId")),
                _to_int(row.get("OriginalSprintNumber")),
                last_sprint_number,
                datetime.utcnow().isoformat(),
            )
        )

        annotation_rows.append(
            (
                task_num,
                sprints_assigned,
                _to_float(row.get("CustomerPriority")),
                _to_float(row.get("FinalPriority")),
                _clean_value(row.get("GoalType")),
                _to_float(row.get("HoursEstimated")),
                _clean_value(row.get("DependencyOn")),
                _clean_value(row.get("DependenciesLead")),
                _clean_value(row.get("DependencySecured")),
                _clean_value(row.get("Comments")),
                _to_datetime_str(row.get("StatusUpdateDt")),
                datetime.utcnow().isoformat(),
            )
        )

        delete_sprint_rows.append((task_num,))
        for sprint in sprint_list:
            sprint_rows.append((task_num, sprint))

    conn.executemany(
        """
        INSERT OR REPLACE INTO tickets (
          ticket_num, ticket_status, ticket_created_dt, ticket_resolved_dt,
          ticket_total_time_spent, subject, customer_name, section, ticket_type,
          ticket_source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ticket_rows,
    )

    conn.executemany(
        """
        INSERT OR REPLACE INTO tasks (
          task_num, ticket_num, task_status, subject, assigned_to, task_assigned_dt,
          task_created_dt, task_resolved_dt, task_minutes_spent, unique_task_id,
          original_sprint_number, last_sprint_number, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        task_rows,
    )

    conn.executemany(
        """
        INSERT OR REPLACE INTO dashboard_task_annotations (
          task_num, sprints_assigned, customer_priority, final_priority,
          goal_type, hours_estimated, dependency_on, dependencies_lead,
          dependency_secured, comments, status_update_dt, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        annotation_rows,
    )

    if delete_sprint_rows:
        conn.executemany(
            "DELETE FROM task_sprint_assignments WHERE task_num = ?",
            delete_sprint_rows,
        )

    if sprint_rows:
        conn.executemany(
            """
            INSERT OR IGNORE INTO task_sprint_assignments (task_num, sprint_number)
            VALUES (?, ?)
            """,
            sprint_rows,
        )


def load_users(db_path: Optional[str] = None) -> pd.DataFrame:
    path = get_db_path(db_path)
    if not os.path.exists(path):
        return pd.DataFrame()
    conn = connect(path)
    initialize_db(conn)
    try:
        return pd.read_sql_query(
            """
            SELECT
              username AS Username,
              password AS Password,
              role AS Role,
              section AS Section,
              display_name AS DisplayName,
              active AS Active
            FROM users
            """,
            conn,
        )
    finally:
        conn.close()


def save_users(db_path: Optional[str], users_df: pd.DataFrame) -> bool:
    if users_df is None or users_df.empty:
        return True
    path = get_db_path(db_path)
    conn = connect(path)
    initialize_db(conn)
    try:
        _upsert_users(conn, users_df)
        conn.commit()
        return True
    except Exception as exc:
        print(f"SQLite save_users failed: {exc}")
        return False
    finally:
        conn.close()


def load_offdays(db_path: Optional[str] = None) -> pd.DataFrame:
    path = get_db_path(db_path)
    if not os.path.exists(path):
        return pd.DataFrame()
    conn = connect(path)
    initialize_db(conn)
    try:
        return pd.read_sql_query(
            """
            SELECT
              username AS Username,
              sprint_number AS SprintNumber,
              off_date AS OffDate,
              reason AS Reason,
              created_by AS CreatedBy,
              created_at AS CreatedAt
            FROM offdays
            """,
            conn,
        )
    finally:
        conn.close()


def save_offdays(db_path: Optional[str], offdays_df: pd.DataFrame) -> bool:
    if offdays_df is None or offdays_df.empty:
        return True
    path = get_db_path(db_path)
    conn = connect(path)
    initialize_db(conn)
    try:
        _upsert_offdays(conn, offdays_df)
        conn.commit()
        return True
    except Exception as exc:
        print(f"SQLite save_offdays failed: {exc}")
        return False
    finally:
        conn.close()


def load_feedback(db_path: Optional[str] = None) -> pd.DataFrame:
    path = get_db_path(db_path)
    if not os.path.exists(path):
        return pd.DataFrame()
    conn = connect(path)
    initialize_db(conn)
    try:
        return pd.read_sql_query(
            """
            SELECT
              feedback_id AS FeedbackId,
              sprint_number AS SprintNumber,
              section AS Section,
              submitted_by AS SubmittedBy,
              submitted_at AS SubmittedAt,
              overall_satisfaction AS OverallSatisfaction,
              what_went_well AS WhatWentWell,
              what_did_not_go_well AS WhatDidNotGoWell
            FROM feedback
            """,
            conn,
        )
    finally:
        conn.close()


def save_feedback(db_path: Optional[str], feedback_df: pd.DataFrame) -> bool:
    if feedback_df is None or feedback_df.empty:
        return True
    path = get_db_path(db_path)
    conn = connect(path)
    initialize_db(conn)
    try:
        _upsert_feedback(conn, feedback_df)
        conn.commit()
        return True
    except Exception as exc:
        print(f"SQLite save_feedback failed: {exc}")
        return False
    finally:
        conn.close()


def _upsert_users(conn, users_df: pd.DataFrame) -> None:
    rows = []
    for _, row in users_df.iterrows():
        username = _clean_value(row.get("Username"))
        if not username:
            continue
        active = row.get("Active", True)
        if isinstance(active, str):
            active = active.lower() in {"true", "1", "yes"}
        rows.append(
            (
                username,
                _clean_value(row.get("Password")),
                _clean_value(row.get("Role")),
                _clean_value(row.get("Section")),
                _clean_value(row.get("DisplayName")),
                1 if active else 0,
            )
        )
    if rows:
        conn.executemany(
            """
            INSERT OR REPLACE INTO users (
              username, password, role, section, display_name, active
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def _upsert_offdays(conn, offdays_df: pd.DataFrame) -> None:
    rows = []
    for _, row in offdays_df.iterrows():
        username = _clean_value(row.get("Username"))
        sprint_number = _to_int(row.get("SprintNumber"))
        off_date = _clean_value(row.get("OffDate"))
        if not username or sprint_number is None or not off_date:
            continue
        rows.append(
            (
                username,
                sprint_number,
                off_date,
                _clean_value(row.get("Reason")),
                _clean_value(row.get("CreatedBy")),
                _clean_value(row.get("CreatedAt")),
            )
        )
    if rows:
        conn.executemany(
            """
            INSERT OR REPLACE INTO offdays (
              username, sprint_number, off_date, reason, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def _upsert_feedback(conn, feedback_df: pd.DataFrame) -> None:
    rows = []
    for _, row in feedback_df.iterrows():
        feedback_id = _clean_value(row.get("FeedbackId"))
        if not feedback_id:
            continue
        rows.append(
            (
                feedback_id,
                _to_int(row.get("SprintNumber")),
                _clean_value(row.get("Section")),
                _clean_value(row.get("SubmittedBy")),
                _clean_value(row.get("SubmittedAt")),
                _to_int(row.get("OverallSatisfaction")),
                _clean_value(row.get("WhatWentWell")),
                _clean_value(row.get("WhatDidNotGoWell")),
            )
        )
    if rows:
        conn.executemany(
            """
            INSERT OR REPLACE INTO feedback (
              feedback_id, sprint_number, section, submitted_by, submitted_at,
              overall_satisfaction, what_went_well, what_did_not_go_well
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def _upsert_worklogs(conn, worklog_df: pd.DataFrame) -> None:
    df = worklog_df.copy()
    required_columns = [
        "RecordId",
        "TaskNum",
        "Owner",
        "MinutesSpent",
        "Description",
        "LogDate",
        "SprintNumber",
        "ImportedAt",
    ]
    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    rows = []
    for _, row in df.iterrows():
        record_id = _clean_value(row.get("RecordId"))
        if not record_id:
            continue
        rows.append(
            (
                record_id,
                _clean_value(row.get("TaskNum")),
                _clean_value(row.get("Owner")),
                _to_int(row.get("MinutesSpent")),
                _clean_value(row.get("Description")),
                _to_datetime_str(row.get("LogDate")),
                _to_int(row.get("SprintNumber")),
                _to_datetime_str(row.get("ImportedAt")),
            )
        )

    if rows:
        conn.executemany(
            """
            INSERT OR REPLACE INTO worklogs (
              record_id, task_num, owner, minutes_spent, description,
              log_date, sprint_number, imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
