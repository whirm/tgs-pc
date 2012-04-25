from os import path

from dispersy.database import Database

LATEST_VERSION = 1

schema = u"""
CREATE TABLE square(
 id INTEGER,                    -- the dispersy Community.database_id
 global_time INTEGER,           -- the dispersy Message.distribution.global_time
 title TEXT,
 description TEXT,
 thumbnail_hash BLOB,
 PRIMARY KEY (id));

CREATE TABLE member(
 id INTEGER,                    -- the dispersy Member.database_id
 square INTEGER REFERENCES square(id),
 alias TEXT,
 thumbnail_hash BLOB,
 PRIMARY KEY (id, square));

CREATE TABLE text(
 id INTEGER,                    -- the dispersy Message.database_id
 global_time INTEGER,           -- the dispersy Message.distribution.global_time
 square INTEGER REFERENCES square(id),
 member INTEGER REFERENCES member(id),
 text TEXT,
 media_hash BLOB,
 utc_timestamp INTEGER,
 PRIMARY KEY (id));

CREATE TABLE option(key TEXT PRIMARY KEY, value BLOB);
INSERT INTO option(key, value) VALUES('database_version', '""" + str(LATEST_VERSION) + """');
"""

class SquareDatabase(Database):
    if __debug__:
        __doc__ = schema

    def __init__(self, working_directory):
        assert isinstance(working_directory, unicode)
        Database.__init__(self, path.join(working_directory, u"square.db"))

    def check_database(self, database_version):
        assert isinstance(database_version, unicode)
        assert database_version.isdigit()
        assert int(database_version) >= 0
        database_version = int(database_version)

        if database_version == 0:
            # setup new database with current database_version
            self.executescript(schema)

        else:
            # upgrade an older version

            # upgrade from version 1 to version 2
            if database_version < 2:
                # there is no version 2 yet...
                # if __debug__: dprint("upgrade database ", database_version, " -> ", 2)
                # self.executescript(u"""UPDATE option SET value = '2' WHERE key = 'database_version';""")
                # if __debug__: dprint("upgrade database ", database_version, " -> ", 2, " (done)")
                pass

        return LATEST_VERSION
