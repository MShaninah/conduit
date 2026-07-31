import time

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError

MAX_RETRIES = 30
RETRY_DELAY_SECONDS = 2


class Command(BaseCommand):
    help = 'Wait until the default database is available.'

    def handle(self, *args, **options):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                connections['default'].cursor()
                self.stdout.write('Database is available.')
                return
            except OperationalError:
                self.stdout.write(
                    f'Database not ready (attempt {attempt}/{MAX_RETRIES}), retrying...'
                )
                time.sleep(RETRY_DELAY_SECONDS)

        self.stderr.write('Could not connect to the database, giving up.')
        raise SystemExit(1)
