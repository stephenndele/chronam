import logging
import os

from datetime import datetime
from multiprocessing.pool import ThreadPool
from optparse import make_option

from django.core.management.base import BaseCommand

from chronam.core import title_loader
from chronam.core.index import index_titles
from chronam.core.models import Title

LOGGER = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Load a marcxml file of title records"
    args = '<location of marcxml>'
    option_list = BaseCommand.option_list + (
        make_option('--skip-index',
        action='store_true',
        dest='skip_index',
        default=False,
        help="\
                Skip the index process. Use this if you call this from \
                another process such as 'chronam_sync'. If you call this \
                directly, you don't want to use this flag. \
            "),
    )

    def __init__(self):
        super(Command, self).__init__()
        self.total_processed = 0
        self.total_created = 0
        self.total_updated = 0
        self.total_errors = 0
        self.total_missing_lccns = 0
        self.files_processed = 0
        self.start_time = datetime.now()
        self.xml_start = datetime.now()

    def xml_file_handler(self, marc_xml, skip_index):
        self.xml_start = datetime.now()
        results = title_loader.load(marc_xml)

    def add_results(self, results):
        '''
        The add results functions adds the new set of results to the
        running totals for the current run & retuns the new results set.
        '''
        self.total_processed += results[0]
        self.total_created += results[1]
        self.total_updated += results[2]
        self.total_errors += results[3]
        self.total_missing_lccns += results[4]

    def log_stats(self):
        LOGGER.info("############### TOTAL RESULTS ############")
        LOGGER.info("TITLE RECORDS PROCESSED: %i" % self.total_processed)
        LOGGER.info("NEW TITLES CREATED: %i" % self.total_created)
        LOGGER.info("EXISTING TITLES UPDATED: %i" % self.total_updated)
        LOGGER.info("ERRORS: %i" % self.total_errors)
        LOGGER.info("MISSING LCCNS: %i" % self.total_missing_lccns)
        LOGGER.info("FILES PROCESSED: %i" % self.files_processed)

        end = datetime.now()

        # Document titles that are not being updated.
        ts = Title.objects.filter(version__lt=self.start_time)
        not_updated = ts.count()
        LOGGER.info("TITLES NOT UPDATED: %i" % not_updated)

        # Total time to run.
        LOGGER.info("START TIME: %s" % str(self.start_time))
        LOGGER.info("END TIME: %s" % str(end))
        total_time = end - self.start_time
        LOGGER.info("TOTAL TIME: %s" % str(total_time))

    def handle(self, marc_xml_source, *args, **options):
        skip_index = options['skip_index']

        # check if arg passed is a file or a directory of files
        if os.path.isdir(marc_xml_source):
            marc_xml_dir = os.listdir(marc_xml_source)

            all_marc_files = []
            for xml_file in marc_xml_dir:
                xml_file_path = os.path.join(marc_xml_source, xml_file)
                all_marc_files.append(xml_file_path)

            pool = ThreadPool()
            for result in pool.imap_unordered(title_loader.load, all_marc_files):
                self.add_results(result)
                self.files_processed += 1

            self.log_stats()

        else:
            results = self.xml_file_handler(marc_xml_source, skip_index)
        
        if not skip_index:
            # need to index any titles that we just created
            LOGGER.info("indexing new titles")
            index_titles(since=self.start_time)

