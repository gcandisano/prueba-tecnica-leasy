import uuid

import pytest

from reservations.constants import (
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_CONFIRMED,
    RESERVATION_STATUS_ON_HOLD,
    RESERVATION_STATUS_REQUESTED,
)
from reservations.exceptions import (
    ReservationHoldReasonRequiredError,
    ReservationNotFoundError,
    ReservationStatusTransitionError,
)
from reservations.services import ReservationLifecycleService
from reservations.tests.factories import ReservationFactory


@pytest.mark.django_db
def test_confirm_reservation_moves_requested_to_confirmed():
    reservation = ReservationFactory(status="requested")

    ReservationLifecycleService().confirm_reservation(reservation_id=reservation.id)

    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_CONFIRMED


@pytest.mark.django_db
def test_confirm_reservation_rejects_invalid_transition():
    reservation = ReservationFactory(status=RESERVATION_STATUS_CANCELLED)

    with pytest.raises(ReservationStatusTransitionError):
        ReservationLifecycleService().confirm_reservation(reservation_id=reservation.id)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "initial_status",
    [RESERVATION_STATUS_REQUESTED, RESERVATION_STATUS_CONFIRMED],
)
def test_hold_reservation_moves_to_on_hold_and_stores_reason(initial_status):
    reservation = ReservationFactory(status=initial_status)

    ReservationLifecycleService().hold_reservation(
        reservation_id=reservation.id,
        reason="  Pending payment verification.  ",
    )

    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_ON_HOLD
    assert reservation.hold_reason == "Pending payment verification."


@pytest.mark.django_db
@pytest.mark.parametrize(
    "initial_status",
    [RESERVATION_STATUS_CANCELLED, RESERVATION_STATUS_ON_HOLD],
)
def test_hold_reservation_rejects_invalid_transition(initial_status):
    reservation = ReservationFactory(status=initial_status)

    with pytest.raises(ReservationStatusTransitionError):
        ReservationLifecycleService().hold_reservation(
            reservation_id=reservation.id,
            reason="Any reason.",
        )

    reservation.refresh_from_db()
    assert reservation.status == initial_status


@pytest.mark.django_db
@pytest.mark.parametrize("reason", ["", "   "])
def test_hold_reservation_requires_reason(reason):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)

    with pytest.raises(ReservationHoldReasonRequiredError):
        ReservationLifecycleService().hold_reservation(
            reservation_id=reservation.id,
            reason=reason,
        )

    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED
    assert reservation.hold_reason == ""


@pytest.mark.django_db
def test_hold_reservation_raises_not_found_for_unknown_id():
    with pytest.raises(ReservationNotFoundError):
        ReservationLifecycleService().hold_reservation(
            reservation_id=uuid.uuid4(),
            reason="Any reason.",
        )
