"""
Export utilities for generating reports
"""
import pandas as pd
from io import BytesIO
from datetime import datetime
from modules.section_filter import exclude_forever_tickets


def export_to_csv(df: pd.DataFrame, filename: str = None) -> bytes:
    """
    Export DataFrame to CSV bytes
    
    Args:
        df: DataFrame to export
        filename: Optional filename (not used, for compatibility)
    
    Returns:
        CSV data as bytes
    """
    return df.to_csv(index=False).encode('utf-8')


def export_to_excel(df: pd.DataFrame, sheet_name: str = "Sprint Data") -> bytes:
    """
    Export DataFrame to Excel bytes
    
    Args:
        df: DataFrame to export
        sheet_name: Name of the Excel sheet
    
    Returns:
        Excel data as bytes
    """
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets[sheet_name]
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    return output.getvalue()


def generate_sprint_summary(sprint_df: pd.DataFrame) -> dict:
    """
    Generate summary statistics for a sprint
    
    Args:
        sprint_df: Sprint DataFrame
    
    Returns:
        Dictionary of summary statistics
    """
    sprint_df = exclude_forever_tickets(sprint_df)

    summary = {}
    
    # Basic counts
    summary['total_tasks'] = len(sprint_df)
    summary['completed_tasks'] = len(sprint_df[sprint_df['TaskStatus'] == 'Completed'])
    summary['canceled_tasks'] = len(sprint_df[sprint_df['TaskStatus'] == 'Cancelled'])
    summary['in_progress_tasks'] = len(sprint_df[sprint_df['TaskStatus'].isin(['Accepted', 'Assigned', 'Waiting'])])
    
    # Completion rate
    if summary['total_tasks'] > 0:
        summary['completion_rate'] = (summary['completed_tasks'] / summary['total_tasks']) * 100
    else:
        summary['completion_rate'] = 0
    
    # Priority breakdown
    summary['priority_5_count'] = len(sprint_df[sprint_df['CustomerPriority'] == 5])
    summary['priority_4_count'] = len(sprint_df[sprint_df['CustomerPriority'] == 4])
    summary['priority_3_count'] = len(sprint_df[sprint_df['CustomerPriority'] == 3])
    
    # Type breakdown
    summary['ir_count'] = len(sprint_df[sprint_df['TicketType'] == 'IR'])
    summary['sr_count'] = len(sprint_df[sprint_df['TicketType'] == 'SR'])
    summary['pr_count'] = len(sprint_df[sprint_df['TicketType'] == 'PR'])
    
    # Effort
    estimated_effort = sprint_df['HoursEstimated'].sum()
    summary['total_estimated_hours'] = estimated_effort if pd.notna(estimated_effort) else 0
    
    # Days open
    if 'DaysOpen' in sprint_df.columns:
        summary['avg_days_open'] = sprint_df['DaysOpen'].mean()
        summary['max_days_open'] = sprint_df['DaysOpen'].max()
    else:
        summary['avg_days_open'] = 0
        summary['max_days_open'] = 0
    
    # At risk tasks (approaching TAT)
    at_risk = sprint_df[
        ((sprint_df['TicketType'] == 'IR') & (sprint_df['DaysOpen'] >= 0.6)) |
        ((sprint_df['TicketType'] == 'SR') & (sprint_df['DaysOpen'] >= 18))
    ]
    summary['at_risk_count'] = len(at_risk)
    
    # Section breakdown
    if 'Section' in sprint_df.columns:
        section_counts = sprint_df['Section'].value_counts().to_dict()
        summary['section_breakdown'] = section_counts
    else:
        summary['section_breakdown'] = {}
    
    return summary


def format_summary_report(summary: dict, sprint_number: int = None) -> str:
    """
    Format summary dictionary as text report
    
    Args:
        summary: Summary dictionary from generate_sprint_summary
        sprint_number: Optional sprint number
    
    Returns:
        Formatted text report
    """
    report = []
    report.append("=" * 60)
    if sprint_number:
        report.append(f"SPRINT {sprint_number} SUMMARY REPORT")
    else:
        report.append("SPRINT SUMMARY REPORT")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 60)
    report.append("")
    
    # Overview
    report.append("OVERVIEW")
    report.append("-" * 60)
    report.append(f"Total Tasks: {summary['total_tasks']}")
    report.append(f"Completed: {summary['completed_tasks']} ({summary['completion_rate']:.1f}%)")
    report.append(f"In Progress: {summary['in_progress_tasks']}")
    report.append(f"Canceled: {summary['canceled_tasks']}")
    report.append("")
    
    # Priority breakdown
    report.append("PRIORITY BREAKDOWN")
    report.append("-" * 60)
    report.append(f"Priority 5 (Critical): {summary['priority_5_count']}")
    report.append(f"Priority 4 (High): {summary['priority_4_count']}")
    report.append(f"Priority 3 (Medium): {summary['priority_3_count']}")
    report.append("")
    
    # Type breakdown
    report.append("TICKET TYPE BREAKDOWN")
    report.append("-" * 60)
    report.append(f"Incident Requests (IR): {summary['ir_count']}")
    report.append(f"Service Requests (SR): {summary['sr_count']}")
    report.append(f"Project Requests (PR): {summary['pr_count']}")
    report.append("")
    
    # Effort
    report.append("EFFORT ESTIMATION")
    report.append("-" * 60)
    report.append(f"Total Estimated Hours: {summary['total_estimated_hours']:.1f}")
    report.append("")
    
    # Days open
    report.append("TASK AGE")
    report.append("-" * 60)
    report.append(f"Average Days Open: {summary['avg_days_open']:.1f}")
    report.append(f"Maximum Days Open: {summary['max_days_open']:.1f}")
    report.append(f"At-Risk Tasks: {summary['at_risk_count']}")
    report.append("")
    
    # Section breakdown
    if summary['section_breakdown']:
        report.append("SECTION BREAKDOWN")
        report.append("-" * 60)
        for section, count in sorted(summary['section_breakdown'].items()):
            report.append(f"{section}: {count} tasks")
        report.append("")
    
    report.append("=" * 60)
    
    return "\n".join(report)
