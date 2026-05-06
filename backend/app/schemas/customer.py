from datetime import datetime

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = None
    short_name: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    industry: str | None = None
    level: str | None = None
    source: str | None = None
    notes: str | None = None
    customer_type: str | None = None
    region: str | None = None
    credit_limit: float | None = None
    credit_level: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = None
    short_name: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    industry: str | None = None
    level: str | None = None
    source: str | None = None
    notes: str | None = None
    customer_type: str | None = None
    region: str | None = None
    credit_limit: float | None = None
    credit_level: str | None = None


class CustomerResponse(BaseModel):
    id: int
    code: str | None
    name: str
    short_name: str | None
    contact_person: str | None
    phone: str | None
    email: str | None
    address: str | None
    industry: str | None
    level: str | None
    source: str | None
    notes: str | None
    customer_type: str | None
    region: str | None
    credit_limit: float | None
    credit_level: str | None
    last_contacted_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    title: str | None = None
    role: str | None = None
    phone: str | None = None
    email: str | None = None
    wechat: str | None = None
    is_primary: bool = False
    notes: str | None = None


class FollowUpCreate(BaseModel):
    method: str | None = None
    status: str | None = None
    content: str | None = None
    result: str | None = None
    planned_at: str | None = None
    completed_at: str | None = None
    priority: str | None = None
    assigned_to: str | None = None
