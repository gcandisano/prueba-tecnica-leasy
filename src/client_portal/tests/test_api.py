import uuid

import pytest

from client_portal.security import ClientTokenService
from reservations.constants import (
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_ON_HOLD,
    RESERVATION_STATUS_REQUESTED,
)
from reservations.tests.factories import CustomerFactory, ReservationFactory, UserFactory


def auth_header(customer) -> dict:
    token = ClientTokenService.issue_access_token(customer=customer)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def cancel_url(reservation_id) -> str:
    return f"/api/v1/reservations/{reservation_id}/cancel"


def assert_problem(response, *, status: int, code: str) -> dict:
    assert response.status_code == status
    payload = response.json()
    assert set(payload) == {"type", "title", "status", "detail", "code", "instance", "errors"}
    assert payload["status"] == status
    assert payload["code"] == code
    assert payload["type"] == f"urn:assessment:problem:{code}"
    assert payload["instance"] == response.request["PATH_INFO"]
    return payload


@pytest.mark.django_db
def test_login_returns_access_token(client):
    user = UserFactory(email="alice@example.com", username="alice", password="demo1234")
    customer = CustomerFactory(user=user)

    response = client.post(
        "/api/v1/auth/login",
        data={"email": customer.user.email, "password": "demo1234"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.django_db
def test_me_returns_customer_profile(client):
    customer = CustomerFactory()
    token = ClientTokenService.issue_access_token(customer=customer)

    response = client.get(
        "/api/v1/auth/me",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(customer.id)


@pytest.mark.django_db
def test_reservation_list_is_scoped_to_customer(client):
    customer = CustomerFactory()
    other_customer = CustomerFactory()
    own_reservation = ReservationFactory(customer=customer)
    ReservationFactory(customer=other_customer)
    token = ClientTokenService.issue_access_token(customer=customer)

    response = client.get(
        "/api/v1/reservations/",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == str(own_reservation.id)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "initial_status",
    [RESERVATION_STATUS_REQUESTED, RESERVATION_STATUS_ON_HOLD],
)
def test_cancel_reservation_cancels_own_reservation(client, initial_status):
    reservation = ReservationFactory(status=initial_status)

    response = client.post(
        cancel_url(reservation.id),
        data={"reason": "Plans changed."},
        content_type="application/json",
        **auth_header(reservation.customer),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(reservation.id)
    assert payload["status"] == RESERVATION_STATUS_CANCELLED
    assert payload["cancel_reason"] == "Plans changed."
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_CANCELLED


@pytest.mark.django_db
def test_cancel_reservation_of_other_customer_returns_not_found(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)
    other_customer = CustomerFactory()

    response = client.post(
        cancel_url(reservation.id),
        data={"reason": "Plans changed."},
        content_type="application/json",
        **auth_header(other_customer),
    )

    assert_problem(response, status=404, code="reservation_not_found")
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED


@pytest.mark.django_db
def test_cancel_unknown_reservation_returns_not_found(client):
    customer = CustomerFactory()

    response = client.post(
        cancel_url(uuid.uuid4()),
        data={"reason": "Plans changed."},
        content_type="application/json",
        **auth_header(customer),
    )

    assert_problem(response, status=404, code="reservation_not_found")


@pytest.mark.django_db
def test_cancel_already_cancelled_reservation_returns_conflict(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_CANCELLED)

    response = client.post(
        cancel_url(reservation.id),
        data={"reason": "Plans changed."},
        content_type="application/json",
        **auth_header(reservation.customer),
    )

    assert_problem(response, status=409, code="reservation_invalid_transition")


@pytest.mark.django_db
@pytest.mark.parametrize("body", [{}, {"reason": ""}, {"reason": "   "}])
def test_cancel_reservation_requires_reason(client, body):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)

    response = client.post(
        cancel_url(reservation.id),
        data=body,
        content_type="application/json",
        **auth_header(reservation.customer),
    )

    payload = assert_problem(response, status=422, code="validation_error")
    assert payload["errors"][0]["loc"][-1] == "reason"
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED


@pytest.mark.django_db
def test_cancel_reservation_without_token_returns_problem(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)

    response = client.post(
        cancel_url(reservation.id),
        data={"reason": "Plans changed."},
        content_type="application/json",
    )

    assert_problem(response, status=401, code="auth_required")


@pytest.mark.django_db
def test_cancel_reservation_with_invalid_token_returns_problem(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)

    response = client.post(
        cancel_url(reservation.id),
        data={"reason": "Plans changed."},
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer not-a-jwt",
    )

    assert_problem(response, status=401, code="auth_invalid_token")
