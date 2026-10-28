from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints


class ProblemDetailSchema(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    code: str
    instance: str
    errors: list[dict] | None = None

    @classmethod
    def make(
        cls,
        *,
        request,
        status: int,
        code: str,
        title: str,
        detail: str,
        errors: list[dict] | None = None,
    ) -> "ProblemDetailSchema":
        return cls(
            type=f"urn:assessment:problem:{code}",
            title=title,
            status=status,
            detail=detail,
            code=code,
            instance=request.path,
            errors=errors,
        )


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=4, max_length=255)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ClientProfileSchema(BaseModel):
    id: UUID
    email: str
    display_name: str


class ReservationListItem(BaseModel):
    id: UUID
    room_name: str
    status: str
    starts_at: datetime
    ends_at: datetime
    cancel_reason: str | None = None


class CancelReservationRequest(BaseModel):
    reason: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=1000),
    ]
