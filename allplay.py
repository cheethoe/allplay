#!/usr/bin/env python3
from config import Config
from database import Database
from library import Library
from media import Media
from interface import Interface

def main():
    myconfig = Config()
    #with Database(myconfig.local_database) as db:
    with Database(myconfig.local_database, myconfig.s3_database['bucket'], myconfig.s3_database['filename'], myconfig.s3_database['profile']) as db:
        lib = Library(db)
        lib.populate_from_db(myconfig)
        for path_alias, path in myconfig.media_sources.items():
            lib.scan_source(myconfig, path_alias, path)
        lib.scanned_to_library_and_db(myconfig)
        print(len(lib.library))
        for full_path in lib.library:
            print(full_path)
            mymedia = Media(myconfig, lib, db, full_path)
            mymedia.get_tags()
            print("%s %s %s %s %s %s %s" % (mymedia.media_id,
                                         mymedia.mount_alias,
                                         mymedia.path,
                                         mymedia.mtime,
                                         mymedia.times_played,
                                         mymedia.tags,
                                         mymedia.files))
            mymedia.play_media()
            menu = Interface(myconfig, lib, db, mymedia)
            menu.media_menu()
            del(mymedia)
        

if __name__ == '__main__':
    main()
