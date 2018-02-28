from __future__ import (absolute_import, division, print_function, unicode_literals)
import logging
import os
import shutil
import subprocess


class Media(object):
    def __init__(self, config, library_object, db, full_path):
        self.db = db
        self.config = config
        self.lib = library_object
        self.logger = logging.getLogger()
        self.full_path = full_path
        self.media_id = self.lib.library[self.full_path]["media_id"]
        self.mount_alias = self.lib.library[self.full_path]["mount_alias"]
        self.path = self.lib.library[self.full_path]["path"]
        self.mtime = self.lib.library[self.full_path]["mtime"]
        self.times_played = self.lib.library[self.full_path]["times_played"]
        self.tags = self.get_tags()
        self.exists = os.path.exists(self.full_path)
        if self.exists:
            self.files = self.get_files()
        else:
            self.files = list()

    def increment_times_played(self):
        sql = '''UPDATE media
                 SET times_played = ?
                 WHERE media_id = ?
                 LIMIT 1'''
        self.times_played += 1
        params = (self.times_played, self.media_id)
        (assoc_rowcount, assoc_lastrowid) = self.db.db_insert(sql, params)
        if assoc_rowcount == 1:
            self.logger.debug("Successfully incremented times_played to {0} for media_id {1}".format(self.times_played, self.media_id))
            return True
        else:
            self.logger.debug("Failed to increment times_played to {0} for media_id {1}".format(self.times_played, self.media_id))
            return False

    def get_tags(self):
        sql = '''SELECT t.tag_name 
                 FROM tags t, media_tags mt
                 WHERE t.tag_id = mt.tag_id
                 AND mt.media_id = ?'''
        params = (self.media_id,)
        # cursor.execute returns an iterator of rows, each row is a tuple)
        tags = [ tag[0] for tag in self.db.db_query_qmark_iterator(sql, params) ]
        self.db.sqlite_conn.commit()
        self.tags = tags

    def add_tag(self, tag):
        # Insert the tag
        insert_tag_sql = '''INSERT INTO tags (tag_name)
                            SELECT (?)
                            WHERE NOT EXISTS (
                                SELECT *
                                FROM tags as t
                                WHERE t.tag_name=?)'''
        (tag_rowcount, tag_lastrowid) = self.db.db_insert(insert_tag_sql, (tag, tag))
        if tag_rowcount == 1:
            self.logger.debug("Inserted tag %s" % tag)
        else:
            self.logger.debug("Tag %s not inserted: %s" % (tag, tag_rowcount))
        # Associate the tag
        insert_associate_sql = '''INSERT INTO media_tags (tag_id, media_id)
                                  VALUES ((SELECT tag_id FROM tags WHERE tag_name = ?), ?)'''
        (assoc_rowcount, assoc_lastrowid) = self.db.db_insert(insert_associate_sql, (tag, self.media_id))
        if assoc_rowcount == 1:
            self.logger.debug("Successfully tagged media")
            return True
        else:
            self.logger.debug("Failed to tag media_id %s with tag %s" % (self.media_id, tag))
            return False

    def remove_tag(self, tag):
        remove_tag_sql = '''DELETE FROM media_tags
                            WHERE media_id = ?
                            AND tag_id IN (
                                SELECT tag_id
                                FROM tags
                                WHERE tag_name = ?)'''
        (rm_rowcount, rm_lastrowid) = self.db.db_insert(remove_tag_sql, (self.media_id, tag))
        if rm_rowcount == 1:
            self.logger.warning("Removed tag %s from media" % tag)
        else: 
            self.logger.warning("Unable to remove tag %s from media" % tag)
            return False
        # Check to see if we need to remove orphaned tag
        check_orphaned_sql = '''SELECT COUNT(mt.media_id)
                                FROM media_tags mt, tags t
                                WHERE t.tag_id = mt.tag_id
                                AND t.tag_name = ?'''
        num_assoc_media = [ row[0] for row in self.db.db_query_qmark_iterator(check_orphaned_sql, (tag,)) ]
        self.db.sqlite_conn.commit()
        print(num_assoc_media)
        if int(num_assoc_media[0]) == 0:
            delete_actual_tag_sql = '''DELETE FROM tags WHERE tag_name = ?'''
            (del_rowcount, del_lastrowid) = self.db.db_insert(delete_actual_tag_sql, (tag,))
            if del_rowcount == 1:
                self.logger.warning("Deleted orphaned tag %s" % tag)
            else:
                self.logger.warning("Failed to delete orphaned tag %s" % tag)
        return True

    def get_files(self):
        # Get the files if full_path is a directory
        media_files = list()
        for path, dirs, files in os.walk(self.full_path):
            for found_file in files:
                if found_file.split('.')[-1].lower() in self.config.media_extensions:
                    self.logger.debug("Extension Match!: %s in %s" % (found_file, path))
                    media_files.append(os.path.join(path, found_file))
        return sorted(media_files)

    def delete(self):
        if os.path.normpath(self.full_path) == "/":
            self.logger.warning("Cannot delete %s: insanity" % self.full_path)
            return False
        for alias, path in self.config.media_sources.items():
            if os.path.normpath(self.full_path) == os.path.normpath(path):
                self.logger.warning("Cannot delete %s: is a mount" % self.full_path)
                return False
        self.logger.warning("Deleting %s" % self.full_path)
        # Remove tags first
        for tag in self.tags:
            self.remove_tag(tag)
        try:
            if os.path.isfile(self.full_path):
                os.unlink(self.full_path)
            elif os.path.isdir(self.full_path):
                shutil.rmtree(self.full_path)
            else:
                self.logger.warning("Cannot delete %s, not a file or directory" % self.full_path)
                return False
            self.lib.delete_from_library_and_db(self.full_path)
            return True
        except (shutil.Error, OSError) as err:
            self.logger.warning("Could not delete %s: %s" % (self.full_path, err))
            return False

    def delete_file(self, index):
        self.logger.warning("Deleting %s" % self.files[index])
        if os.unlink(self.files[index]):
            del(self.files[index])

    def move_to_new_mount_alias(self, new_mount_alias):
        new_mount = self.config.media_sources[new_mount_alias]
        new_full_path = os.path.join(new_mount, self.path)
        if os.path.isdir(new_mount):
            if os.path.exists(new_full_path):
                self.logger.warning("Cannot move %s to %s, path already exists!" % (self.full_path, new_full_path))
                return False
            else:
                try:
                    shutil.move(full_path, new_full_path)
                    self.mount_alias = new_mount
                    return True
                except shutil.Error as err:
                    self.logger.warning("Cannot move %s to %s: %s" % (self.full_path, new_full_path, err))
                    return False
        else:
            self.logger.warning("Cannot move %s to %s, path does not exist" % (self.full_path, new_mount))
            return False

    def play_media(self):
        command = [ self.config.media_handler ]
        if os.path.isfile(self.full_path):
            #formatted_full_path = '"' + self.full_path + '"'
            #command.append(formatted_full_path)
            command.append(self.full_path)
        else:
            for media in self.files:
                #formatted_media = '"' + media + '"'
                #command.append(formatted_media)
                command.append(media)
        try:
            self.logger.warning("trying to run command: %s" % (command))
            playing = subprocess.Popen(command, env=dict(os.environ), stdout=subprocess.PIPE)
            playing.wait()
            self.increment_times_played()
        except subprocess.CalledProcessError as err:
            self.logger.warning("Exception trying to run command: %s %s" % (err, command))
        except:
            self.logger.warning("Exception trying to run command: %s" % (command))
            raise
