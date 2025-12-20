"""
Sprint data model with validation
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Literal
from utils.constants import SPRINT_DURATION_DAYS, SPRINT_START_WEEKDAY


class Sprint(BaseModel):
    """
    Sprint metadata model
    """
    
    sprint_number: int = Field(..., ge=1, description="Sequential sprint identifier")
    sprint_name: str = Field(..., description="Descriptive sprint name")
    sprint_start_dt: datetime = Field(..., description="Sprint start date (Thursday)")
    sprint_end_dt: datetime = Field(..., description="Sprint end date (Wednesday)")
    status: Literal["draft", "active", "locked", "archived"] = Field(default="draft")
    created_by: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    locked_at: datetime = None
    locked_by: str = None
    
    class Config:
        arbitrary_types_allowed = True
        use_enum_values = True
    
    @field_validator('sprint_start_dt')
    @classmethod
    def validate_thursday(cls, v):
        """Ensure sprint starts on Thursday"""
        if v.weekday() != SPRINT_START_WEEKDAY:
            raise ValueError(f"Sprint must start on Thursday (received {v.strftime('%A')})")
        return v
    
    @field_validator('sprint_end_dt')
    @classmethod
    def validate_duration(cls, v, info):
        """Ensure sprint is exactly 14 days"""
        start_dt = info.data.get('sprint_start_dt')
        if start_dt:
            delta = (v - start_dt).days
            if delta != (SPRINT_DURATION_DAYS - 1):  # 13 days difference
                raise ValueError(
                    f"Sprint must be exactly {SPRINT_DURATION_DAYS} days "
                    f"(received {delta + 1} days)"
                )
            
            # Also check if ends on Wednesday
            if v.weekday() != 2:  # Wednesday
                raise ValueError(f"Sprint must end on Wednesday (received {v.strftime('%A')})")
        
        return v
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'SprintNumber': self.sprint_number,
            'SprintName': self.sprint_name,
            'SprintStartDt': self.sprint_start_dt,
            'SprintEndDt': self.sprint_end_dt,
            'Status': self.status,
            'CreatedBy': self.created_by,
            'CreatedAt': self.created_at,
            'LockedAt': self.locked_at,
            'LockedBy': self.locked_by,
        }
