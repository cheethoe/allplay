from __future__ import (absolute_import, division, print_function, unicode_literals)
import logging
import os
import shutil
import subprocess
from .tags import Tags


class Media(object):
    def __init__(self, config, library_object, db, full_path):
        self.db = db
        self.config = config
        self.lib = library_object
        self.logger = logging.getLogger()
        self.full_path = full_path
        try:
            self.media_id = self.lib.library[self.full_path]["media_id"]
            self.mount_alias = self.lib.library[self.full_path]["mount_alias"]
            self.path = self.lib.library[self.full_path]["path"]
            self.mtime = self.lib.library[self.full_path]["mtime"]
            self.times_played = self.lib.library[self.full_path]["times_played"]
        except KeyError as err:
            self.logger.error(f"Error accessing Library media Key: {err}")
            self.logger.error(self.lib.library[self.full_path])
            raise
        self.tags = Tags(self.config, self.db, self.media_id)
        self.exists = os.path.exists(self.full_path)
        if self.exists:
            self.files = self.get_files()
            if os.path.isdir(self.full_path) and len(self.files) == 0:
                self.logger.warning("No media found at {0}, tagging as {1}".format(self.full_path, self.config.non_media_tag))
                self.tags.add_tag(config.non_media_tag)
        else:
            self.files = list()
            self.delete()
        self.media_size = self.get_media_size()

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

    def get_files(self):
        # Get the files if full_path is a directory
        media_files = list()
        for path, dirs, files in os.walk(self.full_path):
            for found_file in files:
                if found_file.split('.')[-1].lower() in self.config.media_extensions:
                    self.logger.debug("Extension Match!: %s in %s" % (found_file, path))
                    media_files.append(os.path.join(path, found_file))
        return sorted(media_files)


    def get_media_size(self):
        """
        Loop through discovered files and sum up the file sizes.  Return Human readable form.
        """
        kb = 1024
        mb = 1024 * 1024
        gb = mb * 1024
        file_size_total = 0
        metric = "Bytes"
        if len(self.files) == 0 and os.path.isfile(self.full_path):
            try:
                file_size_total += os.path.getsize(self.full_path)
            except OSError as err:
                self.logger.error("File %s is inaccessible: %s" % (self.full_path, err))
        else:
            for media_file in self.files:
                try:
                    file_size_total += os.path.getsize(media_file)
                except OSError as err:
                    self.logger.error("File %s is inaccessible: %s" % (media_file, err))
        if file_size_total >= gb:
            file_size_metric = file_size_total / gb
            metric = "GB"
        elif file_size_total >= mb:
            file_size_metric = file_size_total / mb
            metric = "MB"
        elif file_size_total >= kb:
            file_size_metric = file_size_total / kb
            metric = "KB"
        else:
            file_size_metric = file_size_total
        return f'{file_size_metric:.2f} {metric}'

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
        if self.tags.tags:
            for tag in self.tags.tags:
                self.tags.remove_tag(tag)
        try:
            if os.path.isfile(self.full_path):
                os.unlink(self.full_path)
            elif os.path.isdir(self.full_path):
                shutil.rmtree(self.full_path)
            else:
                self.logger.warning("Cannot delete %s, not a file or directory" % self.full_path)
                self.lib.delete_from_library_and_db(self.full_path)
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
        except KeyboardInterrupt:
            # Kill media player
            playing.kill()
        except:
            self.logger.warning("Exception trying to run command: %s" % (command))
            raise
