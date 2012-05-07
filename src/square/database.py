from os import path

from dispersy.database import Database

LATEST_VERSION = 1

schema = u"""
CREATE TABLE square(
 sync_id INTEGER,                               -- sync.id for square_info message
 square_id INTEGER,                             -- community.id for the square
 global_time INTEGER,                           -- sync.global_time for text message
 thumbnail_hash BLOB,
 PRIMARY KEY (sync_id));

CREATE TABLE member(
 sync_id INTEGER,                               -- sync.id for member_info message
 member_id INTEGER,                             -- sync.member for member_info message
 square_id INTEGER REFERENCES square(sync_id),  -- community.id for the square
 thumbnail_hash BLOB,
 PRIMARY KEY (sync_id),
 UNIQUE (member_id, square_id));

CREATE TABLE text(
 sync_id INTEGER,                               -- sync.id for text message
 square_id INTEGER REFERENCES square(sync_id),  -- community.id for the square
 member_id INTEGER REFERENCES member(sync_id),  -- sync.member for member info message
 global_time INTEGER,                           -- sync.global_time for text message
 media_hash BLOB,
 utc_timestamp INTEGER,
 PRIMARY KEY (sync_id));

CREATE VIRTUAL TABLE square_fts USING fts4(title, description, tokenize=porter);
CREATE VIRTUAL TABLE member_fts USING fts4(alias, tokenize=porter);
CREATE VIRTUAL TABLE text_fts USING fts4(text, tokenize=porter);

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
