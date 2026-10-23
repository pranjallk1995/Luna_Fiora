from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, field_validator

Name = str
class TransactionInput(BaseModel):
    occurred_at: datetime
    kind: Literal["income", "expense"]
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    merchant: str = Field(min_length=1, max_length=120)
    category: str = Field(default="Uncategorized", min_length=1, max_length=60)
    account: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=500)
    source: Literal["manual", "gmail", "mcp"] = "manual"
    external_id: str | None = Field(default=None, max_length=255)

class CommitmentInput(BaseModel):
    kind: Literal["emi", "sip"]
    name: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(gt=0)
    day_of_month: int = Field(ge=1, le=31)
    start_date: date
    end_date: date | None = None
    active: bool = True

class GoalInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    target_amount: Decimal = Field(gt=0)
    current_amount: Decimal = Field(default=0, ge=0)
    target_date: date
    priority: Literal["low", "medium", "high"] = "medium"
    notes: str | None = Field(default=None, max_length=500)

class ReminderInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    due_at: datetime
    recurrence: Literal["none", "monthly", "yearly"] = "none"
    entity_type: Literal["general", "emi", "sip", "goal"] = "general"
    entity_id: int | None = None
    completed: bool = False

class DateRange(BaseModel):
    start: date
    end: date
    @field_validator("end")
    @classmethod
    def valid_end(cls, value, info):
        if info.data.get("start") and value < info.data["start"]:
            raise ValueError("end must be on or after start")
        return value