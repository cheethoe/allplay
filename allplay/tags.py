from __future__ import (absolute_import, division, print_function, unicode_literals)
import logging

class Tags(object):
    def __init__(self, config, db, media_id):
        self.db = db
        self.config = config
        self.logger = logging.getLogger()
        self.media_id = media_id
        self.tags = []
        self.get_tags()

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
        # First check if tag already exists
        if tag in self.tags:
            return True
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
