from os import path, makedirs
from sys import maxsize

from conversion import Conversion
from database import SquareDatabase
from payload import MemberInfoPayload, SquareInfoPayload, TextPayload
from state import DummyState, UnknownState, SquareState, TaskGroupState

from dispersy.authentication import MemberAuthentication
from dispersy.community import Community
from dispersy.conversion import DefaultConversion
from dispersy.destination import CommunityDestination
from dispersy.dispersy import MissingMessageCache, MissingLastMessageCache, CANDIDATE_WALKER_CALLBACK_ID
from dispersy.distribution import FullSyncDistribution, LastSyncDistribution
from dispersy.member import DummyMember
from dispersy.message import Message
from dispersy.resolution import DynamicResolution, PublicResolution, LinearResolution
if __debug__:
    from dispersy.dprint import dprint

class Member(object):
    __slots__ = ["square", "sync_id", "member_id", "alias", "thumbnail_hash"]

    def __init__(self, square, sync_id, member_id, alias, thumbnail_hash):
        assert isinstance(square, SquareBase)
        assert isinstance(sync_id, (int, long))
        assert isinstance(member_id, (int, long))
        assert isinstance(alias, unicode)
        assert isinstance(thumbnail_hash, str)
        self.square = square
        self.sync_id = sync_id
        self.member_id = member_id
        self.alias = alias
        self.thumbnail_hash = thumbnail_hash

    def __str__(self):
        return "<Member %d: %s>" % (self.sync_id, self.alias)

class Text(object):
    __slots__ = ["square", "member", "sync_id", "global_time", "text", "media_hash", "utc_timestamp"]

    def __init__(self, square, member, sync_id, global_time, text, media_hash, utc_timestamp):
        assert isinstance(square, SquareBase)
        assert isinstance(member, Member)
        assert isinstance(sync_id, (int, long))
        assert isinstance(global_time, (int, long))
        assert isinstance(text, unicode)
        assert isinstance(media_hash, str)
        assert isinstance(utc_timestamp, (int, long))
        self.square = square
        self.member = member
        self.sync_id = sync_id
        self.global_time = global_time
        self.text = text
        self.media_hash = media_hash
        self.utc_timestamp = utc_timestamp

    def __str__(self):
        return "<Text %d: %s>" % (self.sync_id, self.text)

class SquareBase(Community):
    def __init__(self, master, discovery):
        self._state = DummyState()
        super(SquareBase, self).__init__(master)

        self._database = SquareDatabase.has_instance()
        if not self._database:
            # our data storage
            sqlite_directory = path.join(self._dispersy.working_directory, u"sqlite")
            if not path.isdir(sqlite_directory):
                makedirs(sqlite_directory)

            self._database = SquareDatabase.get_instance(sqlite_directory)
            self._dispersy.database.attach_commit_callback(self._database.commit)

        self._discovery = discovery
        self._my_member_info = self._dispersy.get_last_message(self, self._my_member, self._meta_messages[u"member-info"])

        # get square info from self._database_id
        try:
            self._update_global_time, self._title, self._description, thumbnail_hash = self._database.execute(u"SELECT global_time, title, description, thumbnail_hash FROM square JOIN square_fts ON docid = sync_id WHERE square_id = ?", (self._database_id,)).next()
            self._thumbnail_hash = str(thumbnail_hash)
        except StopIteration:
            self._update_global_time = 0
            self._title = u""
            self._description = u""
            self._thumbnail_hash = ""

        # get my member info from self._database_id and self._my_member.database_id
        try:
            self._my_alias, my_thumbnail_hash = self._database.execute(u"SELECT alias, thumbnail_hash FROM member JOIN member_fts ON docid = sync_id WHERE member_id = ? AND square_id = ?", (self._my_member.database_id, self._database_id)).next()
            self._my_thumbnail_hash = str(my_thumbnail_hash)
        except StopIteration:
            self._my_alias = u"Anonymous"
            self._my_thumbnail_hash = ""

        self._dependencies = 0

        if __debug__: dprint("new Square '", self._title, "' using alias '", self._my_alias, "'")

        self.events = getEventBroker(self)
        self.global_events = getEventBroker(None)

        def load_history():
            sql = u"""
SELECT text.sync_id, text_fts.text, text.media_hash, text.utc_timestamp, text.global_time, member.sync_id, member.member_id, member_fts.alias, member.thumbnail_hash
FROM text
JOIN text_fts ON text_fts.docid = text.sync_id
JOIN member ON member.member_id = text.member_id
JOIN member_fts ON member_fts.docid = member.sync_id
WHERE text.square_id = ?
ORDER BY text.global_time, text.utc_timestamp DESC
LIMIT 100"""

            member_id = global_time = 0
            for text_sync_id, text, media_hash, utc_timestamp, global_time, member_sync_id, member_id, member_alias, member_thumbnail_hash in self._database.execute(sql, (self._database_id,)):
                member = Member(self, member_sync_id, member_id, member_alias, str(member_thumbnail_hash))
                text = Text(self, member, text_sync_id, global_time, text, str(media_hash), utc_timestamp)
                if __debug__: dprint(text)
                self.events.messageReceived(text)

            if member_id and global_time:
                # use one message to implicitly announce this square
                try:
                    packet, = self._dispersy.database.execute(u"SELECT packet FROM sync WHERE community = ? AND member = ? AND global_time = ?",
                                                              (self._database_id, member_id, global_time)).next()
                except StopIteration:
                    pass
                else:
                    message = self._dispersy.convert_packet_to_message(str(packet), self)
                    self._discovery.add_implicitly_hot_text([message])

        self._dispersy.callback.register(load_history, delay=1.0)

    def initiate_meta_messages(self):
        return [Message(self, u"member-info", MemberAuthentication(encoding="sha1"), DynamicResolution(PublicResolution(), LinearResolution()), LastSyncDistribution(synchronization_direction=u"ASC", priority=16, history_size=1), CommunityDestination(node_count=0), MemberInfoPayload(), self._dispersy._generic_timeline_check, self.on_member_info, self.undo_member_info),
                Message(self, u"square-info", MemberAuthentication(encoding="sha1"), DynamicResolution(PublicResolution(), LinearResolution()), LastSyncDistribution(synchronization_direction=u"ASC", priority=128, history_size=1), CommunityDestination(node_count=10), SquareInfoPayload(), self._dispersy._generic_timeline_check, self.on_square_info, self.undo_square_info),
                Message(self, u"text", MemberAuthentication(encoding="sha1"), DynamicResolution(PublicResolution(), LinearResolution()), FullSyncDistribution(enable_sequence_number=False, synchronization_direction=u"DESC", priority=128), CommunityDestination(node_count=10), TextPayload(), self._dispersy._generic_timeline_check, self.on_text, self.undo_text)]

    def initiate_conversions(self):
        return [DefaultConversion(self), Conversion(self)]

    @property
    def title(self):
        return self._title

    @property
    def description(self):
        return self._description

    @property
    def thumbnail_hash(self):
        return self._thumbnail_hash

    @property
    def location(self):
        return (0, 0)

    @property
    def radius(self):
        return 0

    @property
    def allowed_to_set_member_info(self):
        allowed, _ = self._timeline.allowed(self._meta_messages[u"member-info"], self.global_time + 1)
        return allowed

    @property
    def allowed_to_set_square_info(self):
        allowed, _ = self._timeline.allowed(self._meta_messages[u"square-info"], self.global_time + 1)
        return allowed

    @property
    def allowed_to_post_message(self):
        allowed, _ = self._timeline.allowed(self._meta_messages[u"text"], self.global_time + 1)
        return allowed

    def dispersy_on_dynamic_settings(self, messages, initializing=False):
        super(SquareBase, self).dispersy_on_dynamic_settings(messages, initializing)

        global_time = self.global_time + 1
        policies = []
        for name in [u"member-info", u"square-info", u"text"]:
            meta = self._meta_messages[name]
            policy, _ = self._timeline.get_resolution_policy(meta, global_time)
            policies.append(policy)

        if all(isinstance(policy, PublicResolution) for policy in policies):
            self._state = SquareState(self._state)
        elif all(isinstance(policy, LinearResolution) for policy in policies):
            self._state = TaskGroupState(self._state)
        else:
            self._state = UnknownState(self._state)

    def convert_to_task_group(self):
        # TODO this check should be done in dispersy.py
        meta = self._meta_messages[u"dispersy-dynamic-settings"]
        if not self._timeline.allowed(meta, self.global_time + 1)[0]:
            raise ValueError("not allowed")
        policies = []
        for name in [u"member-info", u"square-info", u"text"]:
            meta = self._meta_messages[name]
            policies.append((meta, meta.resolution.policies[1]))
        self._dispersy.create_dynamic_settings(self, policies)
        self._dispersy.reclassify_community(self, TaskGroup)

    def set_my_member_info(self, name, thumbnail_hash):
        if not (isinstance(name, unicode) and len(name.encode("UTF-8")) < 256):
            raise ValueError("invalid name")
        if not (isinstance(thumbnail_hash, str) and len(thumbnail_hash) in (0, 20)):
            raise ValueError("invalid thumbnail hash")
        meta = self._meta_messages[u"member-info"]
        if not self._timeline.allowed(meta, self.global_time + 1)[0]:
            raise ValueError("not allowed")
        global_time = self.claim_global_time()
        policy, _ = self._timeline.get_resolution_policy(meta, global_time)
        self._my_member_info = meta.impl(authentication=(self._my_member,),
                                         resolution=(policy.implement(),),
                                         distribution=(global_time,),
                                         payload=(name, thumbnail_hash))
        self._dispersy.store_update_forward([self._my_member_info], True, True, True)
        return self._my_member_info

    def on_member_info(self, messages):
        data = []
        data_fts = []

        for message in messages:
            member = self.message_to_member(message)
            if __debug__: dprint("member #", member.member_id, ": ", member.alias)

            # database data
            data.append((member.sync_id, member.member_id, self._database_id, buffer(member.thumbnail_hash)))
            data_fts.append((member.sync_id, member.alias))

            if member.member_id == self._my_member.database_id:
                self._my_alias = member.alias
                self._my_thumbnail_hash = member.thumbnail_hash

            self.events.memberInfoUpdated(member)

        self._database.executemany(u"INSERT OR REPLACE INTO member (sync_id, member_id, square_id, thumbnail_hash) VALUES (?, ?, ?, ?)", data)
        self._database.executemany(u"INSERT OR REPLACE INTO member_fts (docid, alias) VALUES (?, ?)", data_fts)

        # this might be a response to a dispersy-missing-message
        self._dispersy.handle_missing_messages(messages, MissingLastMessageCache)
        self._dispersy.handle_missing_messages(messages, MissingMessageCache)

    def undo_member_info(self, *args):
        pass

    def set_square_info(self, title, description, thumbnail_hash, location, radius):
        if not (isinstance(title, unicode) and len(title.encode("UTF-8")) < 256):
            raise ValueError("invalid title")
        if not (isinstance(description, unicode) and len(description.encode("UTF-8")) < 1024):
            raise ValueError("invalid description")
        if not (isinstance(thumbnail_hash, str) and len(thumbnail_hash) in (0, 20)):
            raise ValueError("invalid thumbnail hash")
        if not (isinstance(location, tuple) and len(location) == 2 and isinstance(location[0], int) and isinstance(location[1], int)):
            raise ValueError("invalid location")
        if not (isinstance(radius, int) and 0 <= radius):
            raise ValueError("invalid radius")
        meta = self._meta_messages[u"square-info"]
        if not self._timeline.allowed(meta, self.global_time + 1)[0]:
            raise ValueError("not allowed")
        global_time = self.claim_global_time()
        policy, _ = self._timeline.get_resolution_policy(meta, global_time)
        message = meta.impl(authentication=(self._my_member,),
                            resolution=(policy.implement(),),
                            distribution=(self.claim_global_time(),),
                            payload=(title, description, thumbnail_hash, location, radius))
        self._dispersy.store_update_forward([message], True, True, True)
        return message

    def on_square_info(self, messages):
        update = False
        for message in messages:
            # because LastSyncDistribution works per member we will need to keep the most recent
            if message.distribution.global_time > self._update_global_time:
                self._update_global_time = message.distribution.global_time
                self._title = message.payload.title
                self._description = message.payload.description
                self._thumbnail_hash = message.payload.thumbnail_hash
                self._database.execute(u"INSERT OR REPLACE INTO square (sync_id, square_id, global_time, thumbnail_hash) VALUES (?, ?, ?, ?)", (message.packet_id, self._database_id, self._update_global_time, buffer(self._thumbnail_hash)))
                self._database.execute(u"INSERT OR REPLACE INTO square_fts (docid, title, description) VALUES (?, ?, ?)", (message.packet_id, self._title, self._description))
                update = True

        if update:
            if __debug__: dprint("square ", self._title)
            # update GUI: square info has changed
            self.events.squareInfoUpdated()

        # this might be a response to a dispersy-missing-message
        self._dispersy.handle_missing_messages(messages, MissingMessageCache)

    def undo_square_info(self, *args):
        pass

    def post_text(self, text, media_hash):
        if self._my_member_info is None:
            self.set_my_member_info(self._my_alias, self._my_thumbnail_hash)
        if not (isinstance(text, unicode) and len(text.encode("UTF-8")) < 1024):
            raise ValueError("invalid text")
        if not (isinstance(media_hash, str) and len(media_hash) in (0, 20)):
            raise ValueError("invalid media hash")
        meta = self._meta_messages[u"text"]
        if not self._timeline.allowed(meta, self.global_time + 1)[0]:
            raise ValueError("not allowed")
        global_time = self.claim_global_time()
        policy, _ = self._timeline.get_resolution_policy(meta, global_time)
        message = meta.impl(authentication=(self._my_member,),
                            resolution=(policy.implement(),),
                            distribution=(self.claim_global_time(),),
                            payload=(self._my_member_info, text, media_hash, "now"))
        self._dispersy.store_update_forward([message], True, True, True)
        return message

    def on_text(self, messages, mark_as_hot=True):
        data = []
        data_fts = []

        for message in messages:
            text = self.message_to_text(message)
            if __debug__: dprint("text ", text.member.alias, " says ", text.text)

            # database data
            data.append((text.sync_id, self._database_id, text.member.member_id, text.global_time, buffer(text.media_hash), text.utc_timestamp))
            data_fts.append((text.sync_id, text.text))

            # update GUI: message has been received
            self.events.messageReceived(text)

        self._database.executemany(u"INSERT INTO text (sync_id, square_id, member_id, global_time, media_hash, utc_timestamp) VALUES (?, ?, ?, ?, ?, ?)", data)
        self._database.executemany(u"INSERT INTO text_fts (docid, text) VALUES (?, ?)", data_fts)

        if mark_as_hot:
            self._discovery.add_implicitly_hot_text(messages)

        # this might be a response to a dispersy-missing-message
        self._dispersy.handle_missing_messages(messages, MissingMessageCache)

    def message_to_member(self, message):
        assert message.name == u"member-info"
        return Member(self, message.packet_id, message.authentication.member.database_id, message.payload.alias, message.payload.thumbnail_hash)

    def message_to_text(self, message):
        assert message.name == u"text"
        return Text(self, self.message_to_member(message.payload.member_info), message.packet_id, message.distribution.global_time, message.payload.text, message.payload.media_hash, message.payload.utc_timestamp)

    def undo_text(self, *args):
        pass

    def fetch_message(self, mid, global_time, source, response_func=None, response_args=(), timeout=10.0):
        members = self._dispersy.get_members_from_id(mid)
        if members:
            for member in members:
                message = self._dispersy.get_message(self, member, global_time)
                if message:
                    if __debug__: dprint("message found")
                    return message

                else:
                    if __debug__: dprint("fetching message")
                    self._dispersy.create_missing_message_newstyle(self, source, member, global_time, response_func, response_args, timeout)

        else:
            if __debug__: dprint("fetching identity")
            self._dispersy.create_missing_identity(self, source, DummyMember(mid), response_func, response_args, timeout)

    # TODO remove fetch_hot_text
    def fetch_hot_text(self, hot):
        members = self._dispersy.get_members_from_id(hot.mid)
        if members:
            for member in members:
                message = self._dispersy.get_message(self, member, hot.global_time)
                if message:
                    return message
                else:
                    candidate = hot.sources.pop(0)
                    self._dispersy.create_missing_message(self, candidate, member, hot.global_time)

        else:
            self._dispersy.create_missing_identity(self, hot.sources[0], DummyMember(hot.mid))


    def has_dependencies(self):
        return self._dependencies > 0

    def inc_dependencies(self):
        self._dependencies += 1

    def dec_dependencies(self):
        self._dependencies -= 1

    def __str__(self):
        return "<%s %s>" % (self.__class__.__name__, self.title)

class SquareCommunity(SquareBase):
    def __init__(self, *argv, **kwargs):
        super(SquareCommunity, self).__init__(*argv, **kwargs)

        #Notify about new square creation
        self.global_events.newCommunityCreated(self)

    def leave_square(self):
        return self._dispersy.reclassify_community(self, PreviewCommunity)

class PreviewCommunity(SquareBase):
    def __init__(self, master, discovery, enable_walker):
        assert isinstance(enable_walker, bool)

        # set before calling super
        self._enable_walker = enable_walker

        super(PreviewCommunity, self).__init__(master, discovery)
        self._auto_unload_identifier = "auto-unload-preview-community-%s" % self._cid.encode("HEX")
        self._pending_callbacks.append(self._auto_unload_identifier)

        #Notify about new square creation
        self.global_events.newPreviewCommunityCreated(self)

    def dec_dependencies(self):
        super(PreviewCommunity, self).dec_dependencies()

        if self._dependencies <= 0:
            # unload after the grace period
            self._dispersy.callback.replace_register(self._auto_unload_identifier, self.auto_unload_community, delay=300.0)

    def auto_unload_community(self):
        if self._dependencies <=0:
            if __debug__: dprint("cleanup", box=1)
            self.unload_community()

    def on_text(self, messages, mark_as_hot=False):
        return super(PreviewCommunity, self).on_text(messages, mark_as_hot=mark_as_hot)

    def start_candidate_walker(self):
        assert not self._enable_walker
        self._enable_walker = True
        # hacking the walker...
        self._dispersy._walker_commmunities.insert(0, self)
        # restart walker scheduler
        self._dispersy.callback.replace_register(CANDIDATE_WALKER_CALLBACK_ID, self._dispersy._candidate_walker)

    def join_square(self):
        return self._dispersy.reclassify_community(self, SquareCommunity)

    @property
    def dispersy_acceptable_global_time_range(self):
        # we will accept the full 64 bit global time range
        return maxsize

    @property
    def dispersy_enable_candidate_walker(self):
        return self._enable_walker

    @property
    def dispersy_enable_candidate_walker_responses(self):
        # allow responses, otherwise we will not be able to enable/disable the walker on demand
        return True


from events import getEventBroker
