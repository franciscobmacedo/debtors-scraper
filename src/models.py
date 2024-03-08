import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Step(BaseModel):
    start: int
    end: Optional[int] = None


class DebtorType(str, Enum):
    COLECTIVE = "colectivo"
    SINGULAR = "singular"


class Debtor(BaseModel):
    name: str
    step_text: str
    step: Step


class SingularDebtor(Debtor):
    nif: int


class ColectiveDebtor(Debtor):
    nipc: int



class Metadata(BaseModel):
    step_text: str
    step: Step
    debtor_type: DebtorType
    last_updated: Optional[str] = None