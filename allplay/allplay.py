#!/usr/bin/env python
from __future__ import (absolute_import, division, print_function, unicode_literals)
import copy
from .config import Config
from .database import Database
from .library import Library
import logging
from .media import Media
from .interface import Interface
import os
import random
import sys

def main():
    logging.basicConfig(stream=sys.stdout, level=logging.WARNING, format='%(message)s')
    logger = logging.getLogger()
    config = Config()
    #with Database(config.local_database) as db:
    with Database(config.local_database, config.s3_database['bucket'], config.s3_database['filename'], config.s3_database['profile']) as db:
        lib = Library(db)
        lib.populate_from_db(config)
        # Check to see if local db is older than allowed delay
        if db.local_db_age_sec() > config.local_scan_delay:
            for path_alias, path in config.media_sources.items():
                lib.scan_source(config, path_alias, path)
            lib.scanned_to_library_and_db(config)
        library_list = list(lib.library)
        orig_library_length = len(lib.library)
        random.seed()
        random.shuffle(library_list)
        while len(library_list) > 0:
            logger.warning("Media {0} of {1}".format(str(len(library_list)), str(orig_library_length)))
            full_path = library_list.pop()
            media = Media(config, lib, db, full_path)
            media.get_tags()
            media.play_media()
            menu = Interface(config, lib, db, media)
            print("Media Files:")
            menu.print_list_indexes(media.files)
            print("Tags:")
            menu.print_list_indexes(media.tags)
            menu_action = menu.media_menu()
            logger.debug(menu_action)
            if menu_action == "next":
                continue
            elif menu_action == "library_update":
                logger.warn("Library has been updated, using new library.")
                library_list = list(lib.library)
                orig_library_length = len(lib.library)
                random.shuffle(library_list)
                continue
        logger.warning("No more media.")

if __name__ == '__main__':
    main()
