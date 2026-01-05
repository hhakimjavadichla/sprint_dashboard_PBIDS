"""
Task data model with validation
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Literal
import pandas as pd


class Task(BaseModel):
    """
    Task/Ticket model representing a single work item in a sprint
    """
    
    # Identifiers
    task_num: str = Field(..., description="Unique task ID from iTrack")
    ticket_num: str = Field(..., description="Parent ticket ID")
    
    # Classification
    ticket_type: Literal["IR", "SR", "PR", "NC"] = Field(default="NC")
    section: Optional[str] = None
    
    # Assignment
    assigned_to: Optional[str] = None
    customer_name: str = ""
    subject: str = ""
    
    # Status & Priority
    status: str = ""
    customer_priority: int = Field(default=0, ge=0, le=5)
    
    # Dates
    ticket_created_dt: Optional[datetime] = None
    task_created_dt: Optional[datetime] = None
    
    # Planning fields
    estimated_effort: Optional[float] = Field(None, ge=0, description="Hours")
    dependency_on: Optional[str] = None
    dependencies_lead: Optional[str] = None
    dependency_secured: Optional[str] = None
    comments: Optional[str] = None
    
    # Sprint assignment
    sprint_number: Optional[int] = None
    sprint_name: Optional[str] = None
    sprint_start_dt: Optional[datetime] = None
    sprint_end_dt: Optional[datetime] = None
    
    # Calculated
    days_open: Optional[float] = None
    
    class Config:
        # Allow arbitrary types (for datetime)
        arbitrary_types_allowed = True
        # Use enum values
        use_enum_values = True
    
    @field_validator('ticket_type', mode='before')
    @classmethod
    def extract_ticket_type(cls, v, info):
        """Extract ticket type from subject if not provided"""
        if v and v != "NC":
            return v
        
        # Try to extract from subject
        subject = info.data.get('subject', '')
        if subject:
            subject_upper = str(subject).upper()
            if 'LAB-IR' in subject_upper or '-IR:' in subject_upper:
                return "IR"
            elif 'LAB-SR' in subject_upper or '-SR:' in subject_upper:
                return "SR"
            elif 'LAB-PR' in subject_upper or '-PR:' in subject_upper:
                return "PR"
            elif 'LAB-AD' in subject_upper or '-AD:' in subject_upper:
                return "AD"
        
        return v if v else "NC"
    
    def calculate_days_open(self, reference_date: datetime = None) -> float:
        """
        Calculate days open from ticket creation date
        
        Args:
            reference_date: Date to calculate from (defaults to now)
        
        Returns:
            Number of days open
        """
        if self.ticket_created_dt is None:
            return 0.0
        
        if reference_date is None:
            reference_date = datetime.now()
        
        delta = reference_date - self.ticket_created_dt
        return round(delta.total_seconds() / 86400, 1)
    
    def is_at_risk(self) -> bool:
        """
        Check if task is at risk of missing TAT
        
        Returns:
            True if approaching or exceeding TAT
        """
        if self.days_open is None:
            return False
        
        if self.ticket_type == "IR" and self.days_open >= 0.6:  # 75% of 0.8
            return True
        elif self.ticket_type == "SR" and self.days_open >= 18:  # 82% of 22
            return True
        
        return False
    
    def should_escalate(self) -> bool:
        """
        Check if task should be auto-escalated to Priority 5
        
        Returns:
            True if TAT threshold exceeded
        """
        if self.days_open is None:
            return False
        
        if self.ticket_type == "IR" and self.days_open >= 0.8:
            return True
        elif self.ticket_type == "SR" and self.days_open >= 22:
            return True
        
        return False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for DataFrame"""
        return {
            'TaskNum': self.task_num,
            'TicketNum': self.ticket_num,
            'TicketType': self.ticket_type,
            'Section': self.section,
            'Status': self.status,
            'AssignedTo': self.assigned_to,
            'CustomerName': self.customer_name,
            'Subject': self.subject,
            'CustomerPriority': self.customer_priority,
            'DaysOpen': self.days_open,
            'TicketCreatedDt': self.ticket_created_dt,
            'TaskCreatedDt': self.task_created_dt,
            'HoursEstimated': self.estimated_effort,
            'DependencyOn': self.dependency_on,
            'DependenciesLead': self.dependencies_lead,
            'DependencySecured': self.dependency_secured,
            'Comments': self.comments,
            'SprintNumber': self.sprint_number,
            'SprintName': self.sprint_name,
            'SprintStartDt': self.sprint_start_dt,
            'SprintEndDt': self.sprint_end_dt,
        }
