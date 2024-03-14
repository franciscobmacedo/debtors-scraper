from enum import Enum
from typing import Optional

from pydantic import BaseModel


def to_currency(value: int) -> str:
    return "{:,}€".format(value).replace(",", ".")


class Step(BaseModel):
    start: int
    end: Optional[int] = None

    def __hash__(self) -> int:
        return self.start.__hash__()

    @property
    def text(self):
        start = to_currency(self.start)
        if self.end:
            end = to_currency(self.end)
            return f"{start} - {end}"
        return f"more than {start}"


class DebtorType(str, Enum):
    COLECTIVE = "colectivo"
    SINGULAR = "singular"


class Debtor(BaseModel):
    name: str
    step: Step


class SingularDebtor(Debtor):
    nif: int


class ColectiveDebtor(Debtor):
    nipc: int


class Metadata(BaseModel):
    step: Step
    debtor_type: DebtorType
    last_updated: Optional[str] = None


class SingularDebtorsData(BaseModel):
    debtors: list[SingularDebtor]
    last_updated: str


class ColectiveDebtorsData(BaseModel):
    debtors: list[ColectiveDebtor]
    last_updated: str


class DebtorsData(BaseModel):
    singular_debtors: list[SingularDebtor]
    colective_debtors: list[ColectiveDebtor]
    last_updated: Optional[str] = None
