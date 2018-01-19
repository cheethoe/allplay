#!/usr/bin/env python3
import datetime
from collections import defaultdict
import logging
import os
import sys

class Library(object):
    def __init__(self, db):
        self.library = defaultdict()
        self.library_scanned = {}
        self.logger = logging.getLogger()
        self.db = db
        self.sql = '''SELECT media_id, mount_alias, path, mtime, times_played FROM media'''

    def populate_from_db(self, config, sql=None, sql_params=None):
        if sql is not None:
            if sql_params is None:
                iterator = self.db.db_query_iterator(sql)
            else:
                iterator = self.db.db_query_qmark_iterator(sql, sql_params)
        else:
            iterator = self.db.db_query_iterator(self.sql)
        
        for entry in iterator:
            (media_id, mount_alias, path, mtime, times_played) = entry
            full_path = os.path.join(config.media_sources[mount_alias], path)
            self.library[full_path] = { "media_id": media_id,
                                        "mount_alias": mount_alias,
                                        "path": path,
                                        "mtime": mtime,
                                        "times_played": times_played
                                      }
        self.logger.debug("populate_from_db Library: %s" % self.library)


    def populate_from_db_search(self, config, tags=list(), tag_andor="or", search_strings=list(), search_strings_andor="or"):
        sql = self.sql
        sql_params = list()
        if len(tags) > 0 or len(search_strings) > 0:
            sql += " WHERE "
            if tag_andor == "or" and len(tags) > 0:
                # Search for media with any of the listed tags
                sql += ''' media_id IN (SELECT mt.media_id
                           FROM tags t, media_tags mt
                           WHERE t.tag_id = mt.tag_id
                           AND t.tag_name IN ('''
                for idx, tag in enumerate(tags):
                    if idx > 0:
                        sql += ","
                    sql += "?"
                    sql_params.append(tag)
                sql += ")"
            elif tag_andor == "and" and len(tags) > 0:
                # Search for media with all of the listed tags
                sql += " ("
                for idx, tag in enumerate(tags):
                    if idx > 0:
                        sql += " AND "
                    sql += ''' media_id IN (SELECT mt.media_id
                               FROM tags t, media_tags mt
                               WHERE t.tag_id = mt.tag_id
                               AND t.tag_name = ?'''
                    sql_params.append(tag)
                sql += " )"
            if len(search_strings) > 0:
                # Build portion of query for search strings in path
                if len(sql_params) > 0:
                    sql += " AND ("
                for idx, search_string in enumerate(search_strings):
                    if idx > 0:
                        sql += " " + search_strings_andor + " "
                    sql += " path LIKE '%?%'"
                    sql_params.append(search_string)
                sql += ")"
        self.populate_from_db(config, sql, sql_params)
                    
                

    def scan_source(self, config, path_alias='here', path='.'):
        #with os.scandir(path) as dir_entries:
        try:
            dir_entries = os.scandir(path)
            for entry in dir_entries:
                if entry.name.startswith('.'):
                    # skip
                    continue
                elif entry.path in self.library:
                    # skip, it's already in the library
                    continue
                elif entry.is_file():
                    if entry.name.split('.')[-1] in config.media_extensions:
                        self.library_scanned[entry.path] = { "mount_alias": path_alias,
                                                             "path": entry.name,
                                                             "mtime": datetime.datetime.fromtimestamp(entry.stat().st_mtime),
                                                             "times_played": 0
                                                           }
                elif entry.is_dir():
                    # Find files in dir and ensure at last one match the media_extensions
                    self.logger.debug("Scanning possible media dir %s" % entry.path)
                    media_files = self.scan_for_media_files(config, entry.path)
                    try:
                        media_file = next(media_files)
                        self.library_scanned[entry.path] = { "mount_alias": path_alias,
                                                             "path": entry.name,
                                                             "mtime": datetime.datetime.fromtimestamp(entry.stat().st_mtime),
                                                             "times_played": 0
                                                           }
                        del media_files
                    except StopIteration:
                        del media_files
                        pass
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            pass
        self.logger.debug("scan_source Scanned Library updates: %s" % self.library_scanned)

    def scan_for_media_files(self, config, path):
        # Just scan for files in a dir that match the configured media extensions
        # I'm hoping this will be lighter weight than an os.walk()
        try:
            for entry in os.listdir(path):
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    yield self.scan_for_media_files(config, full_path)
                elif os.path.isfile(full_path):
                    if entry.split('.')[-1] in config.media_extensions:
                        yield full_path
        except (KeyboardInterrupt, SystemExit):
            raise
        except GeneratorExit:
            pass
        except:
            self.logger.warning("Exception scanning %s: %s" % (path, sys.exc_info()[0]))
            pass

    def scanned_to_library_and_db(self, config):
        self.library.update(self.library_scanned)
        for full_path, value_dict in self.library_scanned.items():
            self.logger.warning("Adding entry to db: %s %s" % (full_path, value_dict))
            self.db.sqlite_cursor.execute('''INSERT INTO media (mount_alias, path, mtime, times_played) VALUES(?,?,?,?)''', (value_dict["mount_alias"],
                                                                                                                             value_dict["path"],
                                                                                                                             value_dict["mtime"],
                                                                                                                             value_dict["times_played"]))
        self.db.sqlite_conn.commit()

    def delete_from_library_and_db(self, media_entry):
        if self.library[media_entry] is not None:
            self.db.sqlite_cursor.execute('''DELETE FROM media WHERE mount_alias = ? AND path = ? LIMIT 1''', 
                                          (self.library[media_entry]["mount_alias"],
                                          self.library[media_entry]["path"]))
            self.db.sqlite_conn.commit()
            del(self.library[media_entry])
