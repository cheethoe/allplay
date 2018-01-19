import sys

class Interface(object):
    def __init__(self, config, lib, db, media):
        self.config = config
        self.db = db
        self.lib = lib
        self.media = media

    def media_menu(self):
        menu_text = ("Media Actions:\n"
                     "(y) Next\n"
                     "(r) Replay\n"
                     "(d) Delete media\n"
                     "(ds) Delete single file\n"
                     "(dt) Delete tags\n"
                     "(t) Add Tag\n"
                     "Or Jump to:\n"
                     "(l) Library Actions\n"
                     "(db) Database Actions\n"
                     "(x) Exit\n"
                     "Please make a selection: ")
        action = input(menu_text)
        if action != "y":
            if action == "r":
                self.media.play_media()
            elif action == "d":
                self.media.delete()
            elif action == "ds":
                self.media_delete_single_file()
            elif action == "dt":
                self.media_delete_tags()
            elif action == "t":
                self.media_add_tags()
            elif action == "l":
                self.library_menu()
            elif action == "db":
                self.database_menu()
            elif action == "x":
                sys.exit("Exiting...")
            self.media_menu()

    def print_list_indexes(self, input_list):
        if isinstance(input_list, list):
            for idx, val in enumerate(input_list):
                print('({0}) {1}'.format(idx, input_list))

    def media_delete_single_file(self):
        self.print_list_indexes(self.media.files)
        delete_indexes = input("Input the indexes to delete (space separated), or 'c' to cancel: ").split()
        for delete_index in delete_indexes:
            if isinstance(delete_index, int):
                if delete_index > len(self.media.files) - 1 or delete_index < 0:
                    print('{0} is an invalid index'.format(delete_index))
                else:
                    self.media.delete_file(delete_index)

    def media_delete_tags(self):
        self.print_list_indexes(self.media.tags)
        delete_indexes = input("Input the indexes to delete (space separated), or 'c' to cancel: ").split()
        for delete_index in delete_indexes:
            if isinstance(delete_index, int):
                if delete_index > len(self.media.tags) - 1 or delete_index < 0:
                    print('{0} is an invalid index'.format(delete_index))
                else:
                    self.media.remove_tag(self.media.tags[delete_index])

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
        print('Current Tags for {0}:'.format(self.media.full_path))
        if len(self.media.tags) > 0:
            self.print_list_indexes(self.media.tags)
        else:
            print("No Tags!")
