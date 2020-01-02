from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import print
import datetime
from collections import defaultdict
import logging
import os
import sys
import types

class Library(object):
    def __init__(self, db):
        self.library = defaultdict()
        self.library_list = []
        self.library_scanned = {}
        self.logger = logging.getLogger()
        self.db = db
        self.sql = '''SELECT media_id, mount_alias, path, mtime, times_played FROM media'''


    def populate_from_db(self, config, sql=None, sql_params=None):
        self.library.clear()
        del self.library_list[:]
        if sql is not None:
            if sql_params is None:
                iterator = self.db.db_query_iterator(sql)
            else:
                iterator = self.db.db_query_qmark_iterator(query=sql, parameters=sql_params)
        else:
            iterator = self.db.db_query_iterator(self.sql)
        
        for entry in iterator:
            (media_id, mount_alias, path, mtime, times_played) = entry
            full_path = os.path.join(config.media_sources[mount_alias], path)
            self.logger.debug("Adding entry for {0}.".format(full_path))
            self.library_list.append(full_path)
            self.library[full_path] = { "media_id": media_id,
                                        "mount_alias": mount_alias,
                                        "path": path,
                                        "mtime": mtime,
                                        "times_played": times_played
                                      }
        self.db.sqlite_conn.commit()
        self.logger.debug("populate_from_db Library: %s" % self.library)


    def populate_from_db_sort(self, config, sort_by=None, desc=None):
        sql = self.sql
        sql += ' ORDER BY '
        sql += sort_by
        if desc:
            sql += ' DESC'
        else:
            sql += ' ASC'
        self.logger.warning(sql)
        self.populate_from_db(config=config, sql=sql)


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
                sql += "))"
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
                sql += " ))"
            if len(search_strings) > 0:
                # Build portion of query for search strings in path
                if len(sql_params) > 0:
                    param_end = ")"
                    sql += " AND ("
                else:
                    param_end = ""
                for idx, search_string in enumerate(search_strings):
                    if idx > 0:
                        sql += " " + search_strings_andor + " "
                    sql += " path LIKE ?"
                    sql_params.append('%' + search_string + '%')
                sql += param_end
        self.logger.debug(sql)
        self.logger.debug(sql_params)
        self.populate_from_db(config, sql, tuple(sql_params))


    def decode_name(self, name):
        # Attempt to deal with unicode decoding error.
        if type(name) == str: # leave unicode ones alone
            try:
                name = name.decode('utf8')
            except:
                name = name.decode('windows-1252')
        return name


    def scan_source(self, config, path_alias='here', path='.'):
        #with os.scandir(path) as dir_entries:
        try:
            if sys.version_info[0] < 3:
                for entry in os.listdir(path):
                    entry = self.decode_name(entry)
                    basename = os.path.basename(entry)
                    full_entry = self.decode_name(os.path.join(path, entry))
                    self.logger.warning(full_entry)
                    if basename.startswith('.'):
                        # skip
                        continue
                    elif full_entry in self.library:
                        # skip, it's already in the library
                        continue
                    elif os.path.isfile(full_entry):
                        if basename.split('.')[-1].lower() in config.media_extensions:
                            self.library_scanned[basename] = { "mount_alias": path_alias,
                                                               "path": basename,
                                                               "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(full_entry)),
                                                               "times_played": 0
                                                             }
                    elif os.path.isdir(full_entry):
                        # Find files in dir and ensure at last one match the media_extensions
                        self.logger.warning("Scanning possible media dir %s" % full_entry)
                        media_files = self.scan_for_media_files(config, full_entry)
                        try:
                            media_file = next(media_files)
                            while isinstance(media_file, types.GeneratorType):
                                media_file = next(media_files)
                            self.logger.warning("Found media file %s" % media_file)
                            self.library_scanned[basename] = { "mount_alias": path_alias,
                                                               "path": basename,
                                                               "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(full_entry)),
                                                               "times_played": 0
                                                             }
                            del media_files
                        except StopIteration:
                            self.logger.warning("No media found in dir %s" % full_entry)
                            del media_files
                            pass
                    else:
                        self.logger.warning("Nothing matches: %s" % full_entry)
            else:
                dir_entries = os.scandir(path)
                for entry in dir_entries:
                    if entry.name.startswith('.'):
                        # skip
                        continue
                    elif entry.path in self.library:
                        # skip, it's already in the library
                        continue
                    elif entry.is_file():
                        if entry.name.split('.')[-1].lower() in config.media_extensions:
                            self.library_scanned[entry.path] = { "mount_alias": path_alias,
                                                                 "path": entry.name,
                                                                 "mtime": datetime.datetime.fromtimestamp(entry.stat().st_mtime),
                                                                 "times_played": 0
                                                               }
                    elif entry.is_dir():
                        # Find files in dir and ensure at last one match the media_extensions
                        self.logger.warning("Scanning possible media dir %s" % entry.path)
                        media_files = self.scan_for_media_files(config, entry.path)
                        try:
                            media_file = next(media_files)
                            while isinstance(media_file, types.GeneratorType):
                                media_file = next(media_files)
                            self.logger.warning("Found media file %s" % media_file)
                            self.library_scanned[entry.path] = { "mount_alias": path_alias,
                                                                 "path": entry.name,
                                                                 "mtime": datetime.datetime.fromtimestamp(entry.stat().st_mtime),
                                                                 "times_played": 0
                                                               }
                            del media_files
                        except StopIteration:
                            self.logger.warning("No media found in dir %s" % entry.path)
                            del media_files
                            pass
        except (KeyboardInterrupt, SystemExit):
            raise
        except (AttributeError, Exception) as err:
            print("Passing exception: {0}".format(err))
            pass
        self.logger.debug("scan_source Scanned Library updates: %s" % self.library_scanned)


    def scan_for_media_files(self, config, path):
        # Just scan for files in a dir that match the configured media extensions
        # I'm hoping this will be lighter weight than an os.walk()
        try:
            for entry in os.listdir(path):
                if sys.version_info[0] < 3:
                    full_path = self.decode_name(os.path.join(path, entry))
                else:
                    full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    yield self.scan_for_media_files(config, full_path)
                elif os.path.isfile(full_path):
                    if entry.split('.')[-1].lower() in config.media_extensions:
                        self.logger.debug("Extension Match!: %s" % full_path)
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
