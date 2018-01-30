#!/usr/bin/env python3
from collections import defaultdict
import logging
import os
import sys
from yaml import load, dump, YAMLError
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


class Config(object):
    def __init__(self, config_file=None):
        self.logger = logging.getLogger()
        self.config_file = config_file or os.path.join(os.path.expanduser('~'),
                                                       ".allplay",
                                                       "config")
        self.raw_config = self.loadConfig()
        self.logger.debug(self.raw_config)
        # Start loading config items or defaults
        self.media_sources = self.raw_config.get("media_sources") or {'.': '.'}
        self.local_database = self.raw_config.get("local_database") or os.path.join(os.path.expanduser('~'),
                                                                               ".allplay",
                                                                               "allplay.sqlite3")
        self.local_scan_delay = int(self.raw_config.get("local_scan_delay")) or 86400
        self.s3_database = self.raw_config.get("s3_database") or None
        self.quick_tags = self.raw_config.get("quick_tags") or None
        self.auto_tags = self.raw_config.get("auto_tags") or None
        self.media_handler = self.raw_config.get("media_handler") or os.path.join("usr", "bin", "mpv")
        self.media_extensions = self.raw_config.get("media_extensions") or list()

    def loadConfig(self):
        if os.path.isfile(self.config_file):
            with open(self.config_file, 'r') as stream:
                try:
                    raw_config = load(stream, Loader=Loader)
                except yaml.YAMLError as exc:
                    self.logger.error("Error loading yaml config file %s: %s" %
                                      (self.config_file, exc))
                    if hasattr(exc, 'problem_mark'):
                        mark = exc.problem_mark
                        self.logger.error("Error position: (%s:%s)" %
                                          (mark.line + 1, mark.column + 1))
        else:
            self.logger.warning("No Config file found, using defaults: %s" %
                              self.config_file)
            return {}
        return raw_config
