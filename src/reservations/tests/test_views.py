import pytest
from django.urls import reverse

from reservations.constants import (
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_ON_HOLD,
    RESERVATION_STATUS_REQUESTED,
)
from reservations.exceptions import ReservationStatusTransitionError
from reservations.tests.factories import ReservationFactory, UserFactory, grant_permission


@pytest.mark.django_db
def test_reservation_list_requires_login(client):
    response = client.get(reverse("reservation_list"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_reservation_list_renders_for_user_with_permission(client):
    reservation = ReservationFactory()
    user = UserFactory()
    grant_permission(user=user, codename="view_reservation")
    client.force_login(user)

    response = client.get(reverse("reservation_list"))

    assert response.status_code == 200
    assert reservation.customer.display_name in response.content.decode()


@pytest.mark.django_db
def test_reservation_confirm_requires_permission(client):
    reservation = ReservationFactory()
    user = UserFactory()
    client.force_login(user)

    response = client.post(reverse("reservation_confirm", args=[reservation.id]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_reservation_hold_requires_login(client):
    reservation = ReservationFactory()

    response = client.post(
        reverse("reservation_hold", args=[reservation.id]),
        {"reason": "Pending payment."},
    )

    assert response.status_code == 302
    assert reverse("login") in response["Location"]


@pytest.mark.django_db
def test_reservation_hold_page_renders_for_user_with_permission(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)
    user = UserFactory()
    grant_permission(user=user, codename="hold_reservation")
    client.force_login(user)

    response = client.get(reverse("reservation_hold", args=[reservation.id]))

    assert response.status_code == 200
    assert "reservations/hold.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_reservation_hold_page_requires_hold_permission(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)
    user = UserFactory()
    grant_permission(user=user, codename="view_reservation")
    grant_permission(user=user, codename="change_reservation")
    client.force_login(user)

    response = client.get(reverse("reservation_hold", args=[reservation.id]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_reservation_hold_requires_hold_permission(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)
    user = UserFactory()
    grant_permission(user=user, codename="view_reservation")
    grant_permission(user=user, codename="change_reservation")
    client.force_login(user)

    response = client.post(
        reverse("reservation_hold", args=[reservation.id]),
        {"reason": "Pending payment."},
    )

    assert response.status_code == 403
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED
    assert reservation.hold_reason == ""


@pytest.mark.django_db
def test_reservation_hold_puts_reservation_on_hold(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)
    user = UserFactory()
    grant_permission(user=user, codename="hold_reservation")
    client.force_login(user)

    response = client.post(
        reverse("reservation_hold", args=[reservation.id]),
        {"reason": "Pending payment."},
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("reservation_detail", args=[reservation.id])
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_ON_HOLD
    assert reservation.hold_reason == "Pending payment."


@pytest.mark.django_db
def test_reservation_hold_without_reason_returns_422(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)
    user = UserFactory()
    grant_permission(user=user, codename="hold_reservation")
    client.force_login(user)

    response = client.post(
        reverse("reservation_hold", args=[reservation.id]),
        {"reason": "   "},
    )

    assert response.status_code == 422
    assert "reservations/hold.html" in [t.name for t in response.templates]
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED


@pytest.mark.django_db
def test_reservation_hold_invalid_transition_redirects_with_error(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_CANCELLED)
    user = UserFactory()
    grant_permission(user=user, codename="view_reservation")
    grant_permission(user=user, codename="hold_reservation")
    client.force_login(user)

    response = client.post(
        reverse("reservation_hold", args=[reservation.id]),
        {"reason": "Pending payment."},
        follow=True,
    )

    assert response.status_code == 200
    assert ReservationStatusTransitionError.detail in response.content.decode()
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_CANCELLED


@pytest.mark.django_db
def test_reservation_detail_shows_hold_reason(client):
    reservation = ReservationFactory(
        status=RESERVATION_STATUS_ON_HOLD,
        hold_reason="Pending payment.",
    )
    user = UserFactory()
    grant_permission(user=user, codename="view_reservation")
    client.force_login(user)

    response = client.get(reverse("reservation_detail", args=[reservation.id]))

    assert response.status_code == 200
    assert "Pending payment." in response.content.decode()


@pytest.mark.django_db
def test_reservation_detail_shows_hold_action_only_with_permission(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)
    hold_url = reverse("reservation_hold", args=[reservation.id])
    operator = UserFactory()
    grant_permission(user=operator, codename="view_reservation")
    manager = UserFactory()
    grant_permission(user=manager, codename="view_reservation")
    grant_permission(user=manager, codename="hold_reservation")

    client.force_login(operator)
    operator_response = client.get(reverse("reservation_detail", args=[reservation.id]))
    client.force_login(manager)
    manager_response = client.get(reverse("reservation_detail", args=[reservation.id]))

    assert hold_url not in operator_response.content.decode()
    assert hold_url in manager_response.content.decode()


@pytest.mark.django_db
def test_reservation_list_shows_on_hold_status(client):
    ReservationFactory(status=RESERVATION_STATUS_ON_HOLD)
    user = UserFactory()
    grant_permission(user=user, codename="view_reservation")
    client.force_login(user)

    response = client.get(reverse("reservation_list"))

    assert response.status_code == 200
    assert "On hold" in response.content.decode()
