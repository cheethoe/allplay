from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import input
import sys

class Interface(object):
    def __init__(self, config, lib, db, media):
        self.config = config
        self.db = db
        self.lib = lib
        self.media = media

    def media_menu(self):
        menu_text = ("Media Actions:\n"
                     "(y)  Next\n"
                     "(r)  Replay\n"
                     "(d)  Delete media\n"
                     "(ds) Delete single file\n"
                     "(dt) Delete tags\n"
                     "(t)  Add Tag\n"
                     "(i)  Info Dump\n"
                     "Or Jump to:\n"
                     "(l) Library Actions\n"
                     "(db) Database Actions\n"
                     "(x) Exit\n"
                     "Please make a selection: ")
        action = input(menu_text)

        return_action = "menu"
        if action == "l":
            return_action = self.library_menu()
        elif action == "db":
            return_action = self.database_menu()
        elif action == "d":
            self.media.delete()
            return "next"
        elif action == "y":
            return "next"
        else:
            # These actions don't return anything
            if action == "r":
                self.media.play_media()
            elif action == "ds":
                self.media_delete_single_file()
            elif action == "dt":
                self.media_delete_tags()
            elif action == "t":
                self.media_add_tags()
            elif action == "i":
                print("media_id: '{0}'".format(self.media.media_id))
                print("mount_alias: '{0}'".format(self.media.mount_alias))
                print("path: '{0}'".format(self.media.path))
                print("mtime: '{0}'".format(self.media.mtime))
                print("times_played: '{0}'".format(self.media.times_played))
                print("tags: '{0}'".format(self.media.tags))
                print("files: '{0}'".format(self.media.files))
            elif action == "x":
                self.exit()
        if return_action == "menu":
            return self.media_menu()
        else:
            return return_action


    def print_list_indexes(self, input_list):
        if isinstance(input_list, list):
            for idx, val in enumerate(input_list):
                print('({0}) {1}'.format(idx, val))

    def media_delete_single_file(self):
        self.print_list_indexes(self.media.files)
        delete_indexes = input("Input the indexes to delete (space separated), or 'c' to cancel: ").split()
        for delete_index in delete_indexes:
            if delete_index.isdigit():
                if int(delete_index) > len(self.media.files) - 1 or int(delete_index) < 0:
                    print('{0} is an invalid index'.format(delete_index))
                else:
                    self.media.delete_file(int(delete_index))

    def media_delete_tags(self):
        self.print_list_indexes(self.media.tags)
        delete_indexes = input("Input the indexes to delete (space separated), or 'c' to cancel: ").split()
        for delete_index in delete_indexes:
            if delete_index.isdigit():
                if int(delete_index) > len(self.media.tags) - 1 or int(delete_index) < 0:
                    print('{0} is an invalid index'.format(delete_index))
                else:
                    self.media.remove_tag(self.media.tags[int(delete_index)])

    def media_add_tags(self):
        if self.config.quick_tags is not None:
            print("Select from the following quick tags:")
            for quick_tag, full_tag in self.config.quick_tags.items():
                print ('({0}) {1}'.format(quick_tag, full_tag))
            print("Or...")
        input_tags = input("Input the tags to add (space separated), or 'c' to cancel: ").split()
        for input_tag in input_tags:
            if input_tag == 'c':
                break
            if self.config.quick_tags is not None:
                # Check if tag matches a quick tag
                if input_tag in self.config.quick_tags.keys():
                    self.media.add_tag(self.config.quick_tags[input_tag])
                    continue
            self.media.add_tag(input_tag)
        self.media.get_tags()
        print('Current Tags for {0}:'.format(self.media.full_path))
        if len(self.media.tags) > 0:
            self.print_list_indexes(self.media.tags)
        else:
            print("No Tags!")

    def library_menu(self):
        menu_text = ("Library Actions:\n"
                     "(r) Rescan\n"
                     "(st) Search Tags\n"
                     "(ss) Search String\n"
                     "(sb) Search Both Tags and Strings\n"
                     "Or Jump to:\n"
                     "(m) Media Actions\n"
                     "(db) Database Actions\n"
                     "(x) Exit\n"
                     "Please make a selection: ")
        action = input(menu_text)
        return_action = "library_update"
        if action == "r":
            return self.library_rescan()
        elif action == "st":
            return self.library_search_tags()
        elif action == "ss":
            return self.library_search_strings()
        elif action == "sb":
            return self.library_search_tags_and_strings()
        elif action == "m":
            return "menu"
        elif action == "db":
            return self.db_menu()
        elif action == "x":
            self.exit()
        else:
            return self.library_menu()

    def library_search_get_tags(self):
        if self.config.quick_tags is not None:
            print("Select from the following quick tags:")
            for quick_tag, full_tag in self.config.quick_tags.items():
                print ('({0}) {1}'.format(quick_tag, full_tag))
            print("Or...")
        input_tags = input("Input the tags to search (space separated), or 'c' to cancel: ").split()
        for input_index, input_tag in enumerate(input_tags):
            if self.config.quick_tags is not None:
                # Check if tag matches a quick tag
                if input_tag in self.config.quick_tags.keys():
                    input_tags[input_index] = self.config.quick_tags[input_tag]
                    continue
        return input_tags

    def library_search_get_strings(self):
        input_strings = input("Input the strings to search (space separated), or 'c' to cancel: ").split()
        return input_strings

    def library_search_tags(self):
        input_tags = self.library_search_get_tags()
        if "c" in input_tags:
            return "menu"
        self.lib.populate_from_db_search(self.config, tags=input_tags)
        return "library_update"

    def library_search_strings(self):
        input_strings = self.library_search_get_strings()
        if "c" in input_strings:
            return "menu"
        self.lib.populate_from_db_search(self.config, search_strings=input_strings)
        return "library_update"


    def library_search_tags_and_strings(self):
        input_tags = self.library_search_get_tags()
        if "c" in input_tags:
            return "menu"
        input_strings = self.library_search_get_strings()
        if "c" in input_strings:
            return "menu"
        self.lib.populate_from_db_search(self.config, tags=input_tags, search_strings=input_strings)
        return "library_update"

    def library_rescan(self):
        for path_alias, path in self.config.media_sources.items():
            self.lib.scan_source(config=self.config, path_alias=path_alias, path=path)
        self.lib.scanned_to_library_and_db(self.config)
        return "library_update"


    def database_menu(self):
        menu_text = ("DB Actions:\n"
                     "(s) Sync from S3\n"
                     "(p) Push to S3\n"
                     "(d) Disable Automatic Push to S3\n"
                     "Or Jump to:\n"
                     "(m) Media Actions\n"
                     "(l) Library Actions\n"
                     "(x) Exit\n"
                     "Please make a selection: ")
        action = input(menu_text)
        return_action = "menu"
        if action == "s":
            self.db.s3_to_local()
            self.lib.populate_from_db(self.config)
            return "library_update"
        elif action == "p":
            self.db.local_to_s3(force=True)
        elif action == "d":
            self.db.s3_sync_toggle(enable=False)
        elif action == "x":
            self.exit()
        return return_action
 
    def exit(self):
        sys.exit("Exiting...")
