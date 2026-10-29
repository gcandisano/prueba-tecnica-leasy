from django.core.management import call_command
from django.core.management.base import BaseCommand

from reservations.models import Reservation


class Command(BaseCommand):
    help = "Run seed_assessment_data only if the database has no reservations yet."

    def handle(self, *args, **options):
        # seed_assessment_data duplicates reservations when run twice, so the
        # container entrypoint must be able to call this on every start.
        if Reservation.objects.exists():
            self.stdout.write("Demo data already present, skipping seed.")
            return
        call_command("seed_assessment_data")
