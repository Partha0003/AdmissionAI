from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class TimelineEventResponse(BaseModel):
    id: str
    stage: str
    event_type: str
    actor_type: str  # SYSTEM_EVENT or HUMAN_ACTION
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    title: str
    description: str
    status: str
    reference_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime


class StudentJourneyTimelineResponse(BaseModel):
    application_id: str
    application_number: str
    current_lifecycle_status: str
    stages: Dict[str, str]  # stage_name -> NOT_STARTED / IN_PROGRESS / ACTION_REQUIRED / COMPLETED / BLOCKED
    events: List[TimelineEventResponse]


class AnalyticsOverviewResponse(BaseModel):
    institution_name: str
    academic_year: str
    date_filter: str
    filter_start_date: Optional[str] = None
    filter_end_date: Optional[str] = None
    
    applications: Dict[str, Any]
    documents: Dict[str, Any]
    physical_verification: Dict[str, Any]
    payments: Dict[str, Any]
    erp: Dict[str, Any]
    notifications: Dict[str, Any]
    
    bottlenecks: List[Dict[str, Any]]
    processing_times_hours: Dict[str, Optional[float]]
