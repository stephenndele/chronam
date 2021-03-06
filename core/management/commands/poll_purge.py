import os
import logging

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from chronam.core import tasks

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "manual command to process purge_batch requests  from CTS"

    def handle(self, *args, **options):
        try:
            tasks.poll_purge.apply()
        except Exception as e:
            LOGGER.exception(e)
            raise CommandError("Unable to purge batches")
