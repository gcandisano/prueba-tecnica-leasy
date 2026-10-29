import pytest
from django.core.management import call_command

from reservations.models import Reservation
from reservations.tests.factories import ReservationFactory


@pytest.mark.django_db
def test_seed_demo_data_if_empty_seeds_an_empty_database():
    call_command("seed_demo_data_if_empty")

    assert Reservation.objects.exists()


@pytest.mark.django_db
def test_seed_demo_data_if_empty_skips_when_reservations_exist():
    ReservationFactory()

    call_command("seed_demo_data_if_empty")

    assert Reservation.objects.count() == 1
