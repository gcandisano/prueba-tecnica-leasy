from __future__ import annotations

from uuid import UUID

from django.db import transaction

from reservations.constants import (
    RESERVATION_HOLDABLE_STATUSES,
    RESERVATION_STATUS_CONFIRMED,
    RESERVATION_STATUS_ON_HOLD,
    RESERVATION_STATUS_REQUESTED,
)
from reservations.exceptions import (
    ReservationHoldReasonRequiredError,
    ReservationNotFoundError,
    ReservationStatusTransitionError,
)
from reservations.models import Reservation


class ReservationQueryService:
    def get_reservation(self, *, reservation_id: UUID) -> Reservation:
        try:
            return Reservation.objects.select_related("customer__user", "room").get(
                pk=reservation_id
            )
        except Reservation.DoesNotExist as exc:
            raise ReservationNotFoundError() from exc


class ReservationUpdateService:
    def __init__(self) -> None:
        self._query_service = ReservationQueryService()

    @transaction.atomic
    def update_reservation(
        self,
        *,
        reservation_id: UUID,
        room_id: UUID,
        starts_at,
        ends_at,
        internal_note: str,
    ) -> Reservation:
        reservation = self._query_service.get_reservation(reservation_id=reservation_id)
        reservation.room_id = room_id
        reservation.starts_at = starts_at
        reservation.ends_at = ends_at
        reservation.internal_note = internal_note
        reservation.save(
            update_fields=["room", "starts_at", "ends_at", "internal_note", "updated_at"]
        )
        return reservation


class ReservationLifecycleService:
    def __init__(self) -> None:
        self._query_service = ReservationQueryService()

    @transaction.atomic
    def confirm_reservation(
        self,
        *,
        reservation_id: UUID,
        actor_id: int | None = None,
    ) -> Reservation:
        _ = actor_id
        reservation = self._get_reservation_for_update(reservation_id=reservation_id)

        if reservation.status != RESERVATION_STATUS_REQUESTED:
            raise ReservationStatusTransitionError()

        reservation.status = RESERVATION_STATUS_CONFIRMED
        reservation.save(update_fields=["status", "updated_at"])
        return reservation

    @transaction.atomic
    def hold_reservation(
        self,
        *,
        reservation_id: UUID,
        reason: str,
        actor_id: int | None = None,
    ) -> Reservation:
        _ = actor_id
        reason = (reason or "").strip()
        if not reason:
            raise ReservationHoldReasonRequiredError()

        reservation = self._get_reservation_for_update(reservation_id=reservation_id)

        if reservation.status not in RESERVATION_HOLDABLE_STATUSES:
            raise ReservationStatusTransitionError()

        reservation.status = RESERVATION_STATUS_ON_HOLD
        reservation.hold_reason = reason
        reservation.save(update_fields=["status", "hold_reason", "updated_at"])
        return reservation

    def _get_reservation_for_update(self, *, reservation_id: UUID) -> Reservation:
        try:
            return (
                Reservation.objects.select_for_update()
                .select_related("customer__user", "room")
                .get(pk=reservation_id)
            )
        except Reservation.DoesNotExist as exc:
            raise ReservationNotFoundError() from exc
