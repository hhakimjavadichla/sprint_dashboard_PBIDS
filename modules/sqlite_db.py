"""
SQLite database utilities for Sprint Dashboard migration and storage.
"""
from __future__ import annotations

import os
import sqlite3
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.environ.get(
    "SPRINT_DASHBOARD_DB_PATH",
    os.path.join(PROJECT_ROOT, "data", "sprint_dashboard.sqlite3"),
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS app_metadata (
  key TEXT PRIMARY KEY,
  value TEXT
);

INSERT OR IGNORE INTO app_metadata (key, value)
VALUES ('schema_version', '1');

CREATE TABLE IF NOT EXISTS tickets (
  ticket_num TEXT PRIMARY KEY,
  ticket_status TEXT,
  ticket_created_dt TEXT,
  ticket_resolved_dt TEXT,
  ticket_total_time_spent REAL,
  subject TEXT,
  customer_name TEXT,
  section TEXT,
  ticket_type TEXT,
  ticket_source TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
  task_num TEXT PRIMARY KEY,
  ticket_num TEXT NOT NULL,
  task_status TEXT,
  subject TEXT,
  assigned_to TEXT,
  task_assigned_dt TEXT,
  task_created_dt TEXT,
  task_resolved_dt TEXT,
  task_minutes_spent REAL,
  unique_task_id TEXT,
  original_sprint_number INTEGER,
  last_sprint_number INTEGER,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT,
  FOREIGN KEY(ticket_num) REFERENCES tickets(ticket_num)
);

CREATE TABLE IF NOT EXISTS dashboard_task_annotations (
  task_num TEXT PRIMARY KEY,
  sprints_assigned TEXT,
  customer_priority INTEGER,
  final_priority INTEGER,
  goal_type TEXT,
  hours_estimated REAL,
  dependency_on TEXT,
  dependencies_lead TEXT,
  dependency_secured TEXT,
  comments TEXT,
  status_update_dt TEXT,
  updated_at TEXT,
  FOREIGN KEY(task_num) REFERENCES tasks(task_num)
);

CREATE TABLE IF NOT EXISTS task_sprint_assignments (
  task_num TEXT NOT NULL,
  sprint_number INTEGER NOT NULL,
  PRIMARY KEY (task_num, sprint_number),
  FOREIGN KEY(task_num) REFERENCES tasks(task_num)
);

CREATE TABLE IF NOT EXISTS sprint_calendar (
  sprint_number INTEGER PRIMARY KEY,
  sprint_name TEXT,
  sprint_start_dt TEXT,
  sprint_end_dt TEXT
);

CREATE TABLE IF NOT EXISTS task_raw (
  task_num TEXT PRIMARY KEY,
  row_json TEXT NOT NULL,
  source_file TEXT,
  imported_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(task_num) REFERENCES tasks(task_num)
);

CREATE TABLE IF NOT EXISTS worklogs (
  record_id TEXT PRIMARY KEY,
  task_num TEXT,
  owner TEXT,
  minutes_spent INTEGER,
  description TEXT,
  log_date TEXT,
  sprint_number INTEGER,
  imported_at TEXT,
  FOREIGN KEY(task_num) REFERENCES tasks(task_num)
);

CREATE TABLE IF NOT EXISTS offdays (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT,
  sprint_number INTEGER,
  off_date TEXT,
  reason TEXT,
  created_by TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS feedback (
  feedback_id TEXT PRIMARY KEY,
  sprint_number INTEGER,
  section TEXT,
  submitted_by TEXT,
  submitted_at TEXT,
  overall_satisfaction INTEGER,
  what_went_well TEXT,
  what_did_not_go_well TEXT
);

CREATE TABLE IF NOT EXISTS users (
  username TEXT PRIMARY KEY,
  password TEXT,
  role TEXT,
  section TEXT,
  display_name TEXT,
  active TEXT
);

CREATE TABLE IF NOT EXISTS feature_requests (
  request_id TEXT PRIMARY KEY,
  request TEXT,
  category TEXT,
  request_date TEXT,
  requested_by TEXT,
  status TEXT,
  response TEXT,
  implementation_status TEXT,
  implementation_date TEXT,
  confirm_implemented TEXT
);

CREATE TABLE IF NOT EXISTS migration_conflicts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT,
  entity_id TEXT,
  field_name TEXT,
  values_json TEXT,
  resolution TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ticket_field_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_num TEXT,
  field_name TEXT,
  field_value TEXT,
  source_task_num TEXT,
  source_task_created_dt TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_ticket_num ON tasks(ticket_num);
CREATE INDEX IF NOT EXISTS idx_tasks_last_sprint ON tasks(last_sprint_number);
CREATE INDEX IF NOT EXISTS idx_task_sprint_sprint ON task_sprint_assignments(sprint_number);
CREATE INDEX IF NOT EXISTS idx_worklogs_task ON worklogs(task_num);
CREATE INDEX IF NOT EXISTS idx_worklogs_sprint ON worklogs(sprint_number);
"""

VIEW_SQL = """
DROP VIEW IF EXISTS task_flat_view;

CREATE VIEW task_flat_view AS
SELECT
  t.task_num AS TaskNum,
  t.ticket_num AS TicketNum,
  tk.ticket_type AS TicketType,
  tk.section AS Section,
  t.task_status AS TaskStatus,
  t.assigned_to AS AssignedTo,
  tk.customer_name AS CustomerName,
  -- Single Subject column: use TaskSubject (each task has its own)
  -- For single-task tickets, TaskSubject equals TicketSubject anyway
  t.subject AS Subject,
  -- Task count per ticket for reference
  (SELECT COUNT(*) FROM tasks t2 WHERE t2.ticket_num = t.ticket_num) AS TaskCount,
  t.task_assigned_dt AS TaskAssignedDt,
  t.task_created_dt AS TaskCreatedDt,
  t.task_resolved_dt AS TaskResolvedDt,
  tk.ticket_created_dt AS TicketCreatedDt,
  tk.ticket_resolved_dt AS TicketResolvedDt,
  a.hours_estimated AS HoursEstimated,
  a.dependency_on AS DependencyOn,
  a.dependencies_lead AS DependenciesLead,
  a.dependency_secured AS DependencySecured,
  a.comments AS Comments,
  tk.ticket_total_time_spent AS TicketTotalTimeSpent,
  t.task_minutes_spent AS TaskMinutesSpent,
  t.unique_task_id AS UniqueTaskId,
  t.original_sprint_number AS OriginalSprintNumber,
  COALESCE(
    (
      SELECT group_concat(sa.sprint_number, ', ')
      FROM task_sprint_assignments sa
      WHERE sa.task_num = t.task_num
    ),
    a.sprints_assigned
  ) AS SprintsAssigned,
  a.status_update_dt AS StatusUpdateDt,
  a.goal_type AS GoalType,
  a.customer_priority AS CustomerPriority,
  a.final_priority AS FinalPriority,
  tk.ticket_status AS TicketStatus,
  t.last_sprint_number AS SprintNumber,
  sc.sprint_name AS SprintName,
  sc.sprint_start_dt AS SprintStartDt,
  sc.sprint_end_dt AS SprintEndDt
FROM tasks t
JOIN tickets tk ON tk.ticket_num = t.ticket_num
LEFT JOIN dashboard_task_annotations a ON a.task_num = t.task_num
LEFT JOIN sprint_calendar sc ON sc.sprint_number = t.last_sprint_number;
"""


def get_db_path(db_path: Optional[str] = None) -> str:
    return db_path or DEFAULT_DB_PATH


def connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = get_db_path(db_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def initialize_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    # Migration: Add subject column to tasks table if it doesn't exist
    cursor = conn.execute("PRAGMA table_info(tasks)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'subject' not in columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN subject TEXT")
    conn.executescript(VIEW_SQL)
    conn.commit()
