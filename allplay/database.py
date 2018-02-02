from __future__ import (absolute_import, division, print_function, unicode_literals)
import boto3
from botocore.exceptions import ClientError
import datetime
import logging
import os
import sqlite3
import subprocess
import sys
from tzlocal import get_localzone



class Database(object):
    def __init__(self, local_database=None, s3_database_bucket=None, s3_database_filename=None, s3_database_profile="default"):
        self.logger = logging.getLogger()
        self.local_database = local_database
        self.s3_database_bucket = s3_database_bucket
        self.s3_database_filename = s3_database_filename
        self.s3_database_profile = s3_database_profile
        self._s3_sync_enable = True

    def __enter__(self):
        if self._s3_sync_enable:
            self.s3_to_local()
        self.sqlite_conn = self.db_connect()
        self.sqlite_cursor = self.sqlite_conn.cursor()
        self.initialize_schema()
        return self

    def __exit__(self, type, value, traceback):
        self.sqlite_cursor.close()
        self.db_close()
        if self._s3_sync_enable:
            self.local_to_s3()

    def s3_sync_toggle(self, enable=False):
        self._s3_sync_enable = enable

    def local_db_modified(self):
        timezone = get_localzone()
        if os.path.isfile(self.local_database):
            local_last_modified = timezone.localize(datetime.datetime.fromtimestamp(os.path.getmtime(self.local_database)) + datetime.timedelta(minutes=1))
        else:
            local_last_modified = timezone.localize(datetime.datetime.min + datetime.timedelta(minutes=30000))
        return local_last_modified

    def local_db_age_sec(self):
        timezone = get_localzone()
        local_last_modified = self.local_db_modified()
        delta = timezone.localize(datetime.datetime.now()) - local_last_modified
        return int(delta.total_seconds())

    def s3_to_local(self):
        # Check to see if DB is opened by any processes, if so, skip
        try:
            fuser = subprocess.run(["/bin/fuser", self.local_database])
            if fuser.returncode == 0:
                # Something has the sqlite file open
                self.logger.debug("Skipping sync from S3, {0} is opened: {1}".format(self.local_database, fuser.stdout))
                return False
        except:
            return False
        if self.s3_database_bucket and self.s3_database_filename:
            timezone = get_localzone()
            local_last_modified = self.local_db_modified()
            self.logger.warning("Begining s3 to local sync.  Bucket: %s File: %s" % (self.s3_database_bucket, self.s3_database_filename))
            try:
                session = boto3.session.Session(profile_name=self.s3_database_profile)
                s3 = session.resource('s3')
                s3file = s3.Object(self.s3_database_bucket, self.s3_database_filename)
                if s3file.last_modified > local_last_modified:
                    self.logger.warning("Downloading from S3( %s ) to Local + 1min( %s ) due to modification date: " % (str(s3file.last_modified), str(local_last_modified)))
                    s3file.download_file(self.local_database)
                else:
                    self.logger.warning("Not downloading from S3( %s ) to Local + 1min( %s ) due to modification date: " % (str(s3file.last_modified), str(local_last_modified)))
            except (KeyboardInterrupt, SystemExit):
                raise
            except (ClientError, TypeError) as cerr:
                self.logger.warning("Error attempting to sync from s3: %s" % cerr)
                pass
            except:
                self.logger.warning("Error attempting to sync from s3: %s" % sys.exc_info()[0])
                pass
        else:
            self.logger.debug("Skipping sync from S3, s3 config options incomplete.")

    def local_to_s3(self):
        if self.s3_database_bucket and self.s3_database_filename:
            if os.path.isfile(self.local_database):
                timezone = get_localzone()
                local_last_modified = timezone.localize(datetime.datetime.fromtimestamp(os.path.getmtime(self.local_database)))
                try:
                    session = boto3.session.Session(profile_name=self.s3_database_profile)
                    s3 = session.resource('s3')
                    s3file = s3.Object(self.s3_database_bucket, self.s3_database_filename)
                    if s3file.last_modified < local_last_modified:
                        self.logger.warning("Uploading from Local ( %s ) to S3 ( %s ) due to modification date: " % (str(local_last_modified), str(s3file.last_modified)))
                        s3file.upload_file(self.local_database)
                    else:
                        self.logger.warning("Not uploading from Local ( %s ) to S3 ( %s ) due to modification date: " % (str(local_last_modified), str(s3file.last_modified)))
                except (KeyboardInterrupt, SystemExit):
                    raise
                except (ClientError) as cerr:
                    self.logger.warning("Error attempting to sync to s3: %s" % cerr)
                    pass
                except:
                    self.logger.warning("Error attempting to sync to s3: %s" % sys.exc_info()[0])
                    pass
            else:
                self.logger.warning("Cannot sync to s3, %s is not a file" % self.local_database)

    def db_connect(self):
        try:
            sqlite_conn = sqlite3.connect(self.local_database)
        except sqlite3.Error as err:
            self.logger.warning("Error attempting to connect to the sqlite database: %s" % err)
        return sqlite_conn

    def db_close(self):
        self.sqlite_conn.commit()
        self.sqlite_conn.close()

    def initialize_schema(self):
        self.sqlite_cursor.execute('''CREATE TABLE IF NOT EXISTS media (
                          media_id INTEGER PRIMARY KEY AUTOINCREMENT,
                          mount_alias VARCHAR(64),
                          path VARCHAR(255),
                          mtime VARCHAR(18) DEFAULT (datetime('now')),
                          times_played INT DEFAULT 0,
                          UNIQUE(mount_alias, path)
                          )''')
        self.sqlite_cursor.execute('''CREATE INDEX IF NOT EXISTS idx_mount_alias ON media (mount_alias)''')
        self.sqlite_cursor.execute('''CREATE INDEX IF NOT EXISTS idx_media_path ON media (mount_alias, path)''')
        self.sqlite_cursor.execute('''CREATE TABLE IF NOT EXISTS tags (
                          tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                          tag_name VARCHAR(64),
                          UNIQUE(tag_name)
                          )''')
        self.sqlite_cursor.execute('''CREATE INDEX IF NOT EXISTS idx_tag_name ON tags (tag_name)''')
        self.sqlite_cursor.execute('''CREATE TABLE IF NOT EXISTS media_tags (
                          tag_id INTEGER,
                          media_id INTEGER,
                          PRIMARY KEY (tag_id, media_id),
                          FOREIGN KEY(media_id) REFERENCES media(media_id),
                          FOREIGN KEY(tag_id) REFERENCES tags(tag_id)
                          )''')
        self.sqlite_conn.commit()

    def insert_test_data(self):
        self.sqlite_cursor.execute('''INSERT INTO media (mount_alias, path) VALUES (?,?)''', ('td', 'testing123.mp4'))
        self.sqlite_conn.commit()

    def db_query_iterator(self, query="SELECT * FROM media"):
        try:
            iterator = self.sqlite_cursor.execute(query)
            return iterator
        except ValueError as err:
            self.logger.warning(err)
            raise

    def db_query_qmark_iterator(self, query="SELECT * FROM media", parameters=()):
        try:
            iterator = self.sqlite_cursor.execute(query, parameters)
            return iterator
        except (ValueError, sqlite3.OperationalError) as err:
            self.logger.warning(err)
            raise

    def db_insert(self, query=None, parameters=()):
        ''' Returns a tuple of (rowcount, lastrowid) '''
        try:
            self.sqlite_cursor.execute(query, parameters)
            return_tuple = (self.sqlite_cursor.rowcount, self.sqlite_cursor.lastrowid)
            self.sqlite_conn.commit()
            return return_tuple
        except ValueError as err:
            self.logger.warning(err)
            raise
