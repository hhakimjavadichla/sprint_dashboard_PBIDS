"""
CSV -> SQLite migration utilities for Sprint Dashboard.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

from modules.sqlite_db import connect, initialize_db, DEFAULT_DB_PATH

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATA_DIR = os.path.join(PROJECT_ROOT, "data")

TICKET_FIELD_MAP = {
    "TicketStatus": "ticket_status",
    "TicketCreatedDt": "ticket_created_dt",
    "TicketResolvedDt": "ticket_resolved_dt",
    "TicketTotalTimeSpent": "ticket_total_time_spent",
    "Subject": "subject",
    "CustomerName": "customer_name",
    "Section": "section",
    "TicketType": "ticket_type",
}

TICKET_FIELD_STRATEGY = {
    "TicketCreatedDt": "earliest_date",
    "TicketResolvedDt": "latest_date",
    "TicketTotalTimeSpent": "max_numeric",
    "TicketStatus": "latest",
    "Subject": "latest",
    "CustomerName": "latest",
    "Section": "latest",
    "TicketType": "latest",
}

DASHBOARD_FIELDS = [
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
]


def _clean_str(value: object) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.lower() in {"nan", "none", "null"}:
        return None
    return text


def _clean_value(value: object) -> Optional[object]:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.lower() in {"nan", "none", "null"}:
            return None
        return text
    return value


def _select_value(series: pd.Series, strategy: str) -> Optional[object]:
    if series is None or series.empty:
        return None

    if strategy == "earliest_date":
        parsed = pd.to_datetime(series, errors="coerce")
        if parsed.notna().any():
            idx = parsed.idxmin()
            return _clean_value(series.loc[idx])
        strategy = "earliest"

    if strategy == "latest_date":
        parsed = pd.to_datetime(series, errors="coerce")
        if parsed.notna().any():
            idx = parsed.idxmax()
            return _clean_value(series.loc[idx])
        strategy = "latest"

    if strategy == "max_numeric":
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().any():
            idx = numeric.idxmax()
            return _clean_value(series.loc[idx])
        strategy = "latest"

    if strategy == "earliest":
        for value in series.tolist():
            cleaned = _clean_value(value)
            if cleaned is not None:
                return cleaned
        return None

    for value in reversed(series.tolist()):
        cleaned = _clean_value(value)
        if cleaned is not None:
            return cleaned
    return None


def _to_int(value: object) -> Optional[int]:
    cleaned = _clean_value(value)
    if cleaned is None:
        return None
    try:
        return int(float(cleaned))
    except (ValueError, TypeError):
        return None


def _to_float(value: object) -> Optional[float]:
    cleaned = _clean_value(value)
    if cleaned is None:
        return None
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _to_json_row(row: pd.Series) -> str:
    data: Dict[str, object] = {}
    for key, value in row.items():
        if pd.isna(value):
            data[key] = None
        else:
            data[key] = value
    return json.dumps(data, default=str)


def _distinct_values(values: Iterable[object]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        cleaned = _clean_value(value)
        if cleaned is None:
            continue
        text = str(cleaned)
        if text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


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


def _load_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str)


def migrate_csv_to_sqlite(
    db_path: str = DEFAULT_DB_PATH,
    data_dir: Optional[str] = None,
    overwrite: bool = False,
) -> Dict[str, int]:
    data_dir = data_dir or DEFAULT_DATA_DIR
    all_tasks_path = os.path.join(data_dir, "all_tasks.csv")
    dashboard_path = os.path.join(data_dir, "dashboard_annotations.csv")
    sprint_calendar_path = os.path.join(data_dir, "sprint_calendar.csv")
    users_path = os.path.join(data_dir, "users.csv")
    offdays_path = os.path.join(data_dir, "team_offdays.csv")
    feedback_path = os.path.join(data_dir, "sprint_feedback.csv")
    feature_requests_path = os.path.join(data_dir, "feature_requests.csv")
    worklog_path = os.path.join(data_dir, "worklog_data.csv")

    if not os.path.exists(all_tasks_path):
        raise FileNotFoundError(f"Missing required file: {all_tasks_path}")

    if os.path.exists(db_path):
        if not overwrite:
            raise FileExistsError(f"SQLite DB already exists at {db_path}. Pass overwrite=True to recreate.")
        os.remove(db_path)

    conn = connect(db_path)
    # Disable FK checks during bulk migration to allow orphaned worklogs
    conn.execute("PRAGMA foreign_keys = OFF")
    initialize_db(conn)

    all_tasks_df = _load_csv(all_tasks_path)
    dashboard_df = _load_csv(dashboard_path)

    if not all_tasks_df.empty:
        all_tasks_df["TaskNum"] = all_tasks_df["TaskNum"].apply(_clean_str)
        all_tasks_df["TicketNum"] = all_tasks_df["TicketNum"].apply(_clean_str)

    if not dashboard_df.empty:
        dashboard_df["TaskNum"] = dashboard_df["TaskNum"].apply(_clean_str)
        dashboard_df = dashboard_df.set_index("TaskNum")

    missing_ticket_mask = all_tasks_df["TicketNum"].isna()
    if missing_ticket_mask.any():
        all_tasks_df.loc[missing_ticket_mask, "TicketNum"] = all_tasks_df.loc[
            missing_ticket_mask, "TaskNum"
        ].apply(lambda x: f"UNKNOWN-{x}" if x else "UNKNOWN")

    all_tasks_df["_TaskCreatedDtParsed"] = pd.to_datetime(
        all_tasks_df.get("TaskCreatedDt"), errors="coerce"
    )

    ticket_records: List[Tuple] = []
    ticket_history_records: List[Tuple] = []
    conflict_records: List[Tuple] = []

    for ticket_num, group in all_tasks_df.groupby("TicketNum", dropna=False):
        if not ticket_num:
            continue
        group_sorted = group.sort_values("_TaskCreatedDtParsed")

        selected_values: Dict[str, Optional[str]] = {}
        for src_col, dest_col in TICKET_FIELD_MAP.items():
            series = group_sorted[src_col] if src_col in group_sorted.columns else pd.Series([], dtype=object)
            distinct = _distinct_values(series)
            strategy = TICKET_FIELD_STRATEGY.get(src_col, "latest")
            selected = _select_value(series, strategy)

            if len(distinct) > 1:
                conflict_records.append(
                    (
                        "ticket",
                        ticket_num,
                        dest_col,
                        json.dumps(distinct),
                        str(selected) if selected is not None else None,
                    )
                )
            selected_values[dest_col] = selected

        subject = selected_values.get("subject")
        ticket_type = selected_values.get("ticket_type") or _extract_ticket_type(subject)

        ticket_records.append(
            (
                ticket_num,
                selected_values.get("ticket_status"),
                selected_values.get("ticket_created_dt"),
                selected_values.get("ticket_resolved_dt"),
                _to_float(selected_values.get("ticket_total_time_spent")),
                subject,
                selected_values.get("customer_name"),
                selected_values.get("section"),
                ticket_type,
                "csv",
            )
        )

        for _, row in group_sorted.iterrows():
            task_num = _clean_str(row.get("TaskNum"))
            task_created = _clean_value(row.get("TaskCreatedDt"))
            for src_col, dest_col in TICKET_FIELD_MAP.items():
                value = _clean_value(row.get(src_col))
                if value is None:
                    continue
                ticket_history_records.append(
                    (ticket_num, dest_col, str(value), task_num, str(task_created) if task_created else None)
                )

    conn.executemany(
        """
        INSERT OR REPLACE INTO tickets (
          ticket_num, ticket_status, ticket_created_dt, ticket_resolved_dt,
          ticket_total_time_spent, subject, customer_name, section, ticket_type,
          ticket_source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ticket_records,
    )

    if ticket_history_records:
        conn.executemany(
            """
            INSERT INTO ticket_field_history (
              ticket_num, field_name, field_value, source_task_num, source_task_created_dt
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ticket_history_records,
        )

    if conflict_records:
        conn.executemany(
            """
            INSERT INTO migration_conflicts (
              entity_type, entity_id, field_name, values_json, resolution
            ) VALUES (?, ?, ?, ?, ?)
            """,
            conflict_records,
        )

    task_records: List[Tuple] = []
    raw_records: List[Tuple] = []
    annotation_records: List[Tuple] = []
    sprint_assignment_records: List[Tuple] = []

    for _, row in all_tasks_df.iterrows():
        task_num = _clean_str(row.get("TaskNum"))
        ticket_num = _clean_str(row.get("TicketNum"))
        if not task_num or not ticket_num:
            continue

        sprint_number = _to_int(row.get("SprintNumber"))
        task_row_sprints = row.get("SprintsAssigned")

        annotation_row = None
        if not dashboard_df.empty and task_num in dashboard_df.index:
            annotation_row = dashboard_df.loc[task_num]

        annotation_values: Dict[str, Optional[object]] = {}
        for field in DASHBOARD_FIELDS:
            value = None
            if annotation_row is not None:
                value = _clean_value(annotation_row.get(field))
            if value is None:
                value = _clean_value(row.get(field))
            annotation_values[field] = value

        sprints_assigned = annotation_values.get("SprintsAssigned") or task_row_sprints
        sprint_list = _parse_sprints(sprints_assigned)
        if sprint_number is None and sprint_list:
            sprint_number = max(sprint_list)

        task_records.append(
            (
                task_num,
                ticket_num,
                _clean_value(row.get("Status")),
                _clean_value(row.get("AssignedTo")),
                _clean_value(row.get("TaskAssignedDt")),
                _clean_value(row.get("TaskCreatedDt")),
                _clean_value(row.get("TaskResolvedDt")),
                _to_float(row.get("TaskMinutesSpent")),
                _clean_value(row.get("UniqueTaskId")),
                _to_int(row.get("OriginalSprintNumber")),
                sprint_number,
            )
        )

        raw_records.append(
            (task_num, _to_json_row(row), os.path.basename(all_tasks_path))
        )

        annotation_records.append(
            (
                task_num,
                _clean_value(sprints_assigned),
                _to_float(annotation_values.get("CustomerPriority")),
                _to_float(annotation_values.get("FinalPriority")),
                _clean_value(annotation_values.get("GoalType")),
                _to_float(annotation_values.get("HoursEstimated")),
                _clean_value(annotation_values.get("DependencyOn")),
                _clean_value(annotation_values.get("DependenciesLead")),
                _clean_value(annotation_values.get("DependencySecured")),
                _clean_value(annotation_values.get("Comments")),
                _clean_value(annotation_values.get("StatusUpdateDt")),
            )
        )

        for sprint in sprint_list:
            sprint_assignment_records.append((task_num, sprint))

    conn.executemany(
        """
        INSERT OR REPLACE INTO tasks (
          task_num, ticket_num, task_status, assigned_to, task_assigned_dt,
          task_created_dt, task_resolved_dt, task_minutes_spent, unique_task_id,
          original_sprint_number, last_sprint_number
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        task_records,
    )

    if raw_records:
        conn.executemany(
            """
            INSERT OR REPLACE INTO task_raw (task_num, row_json, source_file)
            VALUES (?, ?, ?)
            """,
            raw_records,
        )

    if annotation_records:
        conn.executemany(
            """
            INSERT OR REPLACE INTO dashboard_task_annotations (
              task_num, sprints_assigned, customer_priority, final_priority,
              goal_type, hours_estimated, dependency_on, dependencies_lead,
              dependency_secured, comments, status_update_dt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            annotation_records,
        )

    if sprint_assignment_records:
        conn.executemany(
            """
            INSERT OR IGNORE INTO task_sprint_assignments (task_num, sprint_number)
            VALUES (?, ?)
            """,
            sprint_assignment_records,
        )

    sprint_calendar_df = _load_csv(sprint_calendar_path)
    if not sprint_calendar_df.empty:
        sprint_records = []
        for _, row in sprint_calendar_df.iterrows():
            sprint_records.append(
                (
                    _to_int(row.get("SprintNumber")),
                    _clean_value(row.get("SprintName")),
                    _clean_value(row.get("SprintStartDt")),
                    _clean_value(row.get("SprintEndDt")),
                )
            )
        conn.executemany(
            """
            INSERT OR REPLACE INTO sprint_calendar (
              sprint_number, sprint_name, sprint_start_dt, sprint_end_dt
            ) VALUES (?, ?, ?, ?)
            """,
            sprint_records,
        )

    users_df = _load_csv(users_path)
    if not users_df.empty:
        user_records = []
        for _, row in users_df.iterrows():
            user_records.append(
                (
                    _clean_value(row.get("Username")),
                    _clean_value(row.get("Password")),
                    _clean_value(row.get("Role")),
                    _clean_value(row.get("Section")),
                    _clean_value(row.get("DisplayName")),
                    _clean_value(row.get("Active")),
                )
            )
        conn.executemany(
            """
            INSERT OR REPLACE INTO users (
              username, password, role, section, display_name, active
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            user_records,
        )

    offdays_df = _load_csv(offdays_path)
    if not offdays_df.empty:
        offday_records = []
        for _, row in offdays_df.iterrows():
            offday_records.append(
                (
                    _clean_value(row.get("Username")),
                    _to_int(row.get("SprintNumber")),
                    _clean_value(row.get("OffDate")),
                    _clean_value(row.get("Reason")),
                    _clean_value(row.get("CreatedBy")),
                    _clean_value(row.get("CreatedAt")),
                )
            )
        conn.executemany(
            """
            INSERT INTO offdays (
              username, sprint_number, off_date, reason, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            offday_records,
        )

    feedback_df = _load_csv(feedback_path)
    if not feedback_df.empty:
        feedback_records = []
        for _, row in feedback_df.iterrows():
            feedback_records.append(
                (
                    _clean_value(row.get("FeedbackId")),
                    _to_int(row.get("SprintNumber")),
                    _clean_value(row.get("Section")),
                    _clean_value(row.get("SubmittedBy")),
                    _clean_value(row.get("SubmittedAt")),
                    _to_int(row.get("OverallSatisfaction")),
                    _clean_value(row.get("WhatWentWell")),
                    _clean_value(row.get("WhatDidNotGoWell")),
                )
            )
        conn.executemany(
            """
            INSERT OR REPLACE INTO feedback (
              feedback_id, sprint_number, section, submitted_by, submitted_at,
              overall_satisfaction, what_went_well, what_did_not_go_well
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            feedback_records,
        )

    feature_df = _load_csv(feature_requests_path)
    if not feature_df.empty:
        feature_records = []
        for _, row in feature_df.iterrows():
            feature_records.append(
                (
                    _clean_value(row.get("RequestID")),
                    _clean_value(row.get("Request")),
                    _clean_value(row.get("Category")),
                    _clean_value(row.get("RequestDate")),
                    _clean_value(row.get("RequestedBy")),
                    _clean_value(row.get("Status")),
                    _clean_value(row.get("Response")),
                    _clean_value(row.get("ImplementationStatus")),
                    _clean_value(row.get("ImplementationDate")),
                    _clean_value(row.get("ConfirmImplemented")),
                )
            )
        conn.executemany(
            """
            INSERT OR REPLACE INTO feature_requests (
              request_id, request, category, request_date, requested_by,
              status, response, implementation_status, implementation_date,
              confirm_implemented
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            feature_records,
        )

    worklog_df = _load_csv(worklog_path)
    if not worklog_df.empty:
        worklog_records = []
        for _, row in worklog_df.iterrows():
            worklog_records.append(
                (
                    _clean_value(row.get("RecordId")),
                    _clean_value(row.get("TaskNum")),
                    _clean_value(row.get("Owner")),
                    _to_int(row.get("MinutesSpent")),
                    _clean_value(row.get("Description")),
                    _clean_value(row.get("LogDate")),
                    _to_int(row.get("SprintNumber")),
                    _clean_value(row.get("ImportedAt")),
                )
            )
        conn.executemany(
            """
            INSERT OR REPLACE INTO worklogs (
              record_id, task_num, owner, minutes_spent, description,
              log_date, sprint_number, imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            worklog_records,
        )

    conn.commit()

    summary = {
        "tickets": len(ticket_records),
        "tasks": len(task_records),
        "annotations": len(annotation_records),
        "sprint_assignments": len(sprint_assignment_records),
        "worklogs": 0 if worklog_df.empty else len(worklog_df),
        "users": 0 if users_df.empty else len(users_df),
        "offdays": 0 if offdays_df.empty else len(offdays_df),
        "feedback": 0 if feedback_df.empty else len(feedback_df),
        "feature_requests": 0 if feature_df.empty else len(feature_df),
        "conflicts": len(conflict_records),
    }

    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate CSV data to SQLite")
    parser.add_argument(
        "--db-path",
        default=DEFAULT_DB_PATH,
        help="Path to SQLite database file (default: data/sprint_dashboard.sqlite3)",
    )
    parser.add_argument(
        "--data-dir",
        default=DEFAULT_DATA_DIR,
        help="Path to data directory containing CSV files",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing SQLite database file",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    result = migrate_csv_to_sqlite(
        db_path=args.db_path,
        data_dir=args.data_dir,
        overwrite=args.overwrite,
    )
    print("Migration complete:")
    for key, value in result.items():
        print(f"- {key}: {value}")
