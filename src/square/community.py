from os import path, makedirs

from conversion import Conversion
from database import SquareDatabase
from payload import MemberInfoPayload, SquareInfoPayload, TextPayload
from state import DummyState, UnknownState, SquareState, TaskGroupState

from dispersy.authentication import MemberAuthentication
from dispersy.community import Community
from dispersy.conversion import DefaultConversion
from dispersy.destination import CommunityDestination
from dispersy.distribution import FullSyncDistribution, LastSyncDistribution
from dispersy.member import DummyMember
from dispersy.message import Message
from dispersy.resolution import DynamicResolution, PublicResolution, LinearResolution

if __debug__:
    from dispersy.dprint import dprint

class Member(object):
    __slots__ = ["square", "id", "alias", "thumbnail_hash"]

    def __init__(self, square, id_, alias, thumbnail_hash):
        assert isinstance(square, SquareBase)
        assert isinstance(id_, (int, long))
        assert isinstance(alias, unicode)
        assert isinstance(thumbnail_hash, str)
        self.square = square
        self.id = id_
        self.alias = alias
        self.thumbnail_hash = thumbnail_hash

class Text(object):
    __slots__ = ["square", "id", "global_time", "member", "text", "media_hash", "utc_timestamp"]

    def __init__(self, square, id_, global_time, member, text, media_hash, utc_timestamp):
        assert isinstance(square, SquareBase)
        assert isinstance(id_, (int, long))
        assert isinstance(global_time, (int, long))
        assert isinstance(member, Member)
        assert isinstance(text, unicode)
        assert isinstance(media_hash, str)
        assert isinstance(utc_timestamp, (int, long))
        self.square = square
        self.id = id_
        self.global_time = global_time
        self.member = member
        self.text = text
        self.media_hash = media_hash
        self.utc_timestamp = utc_timestamp

    def __str__(self):
        return "<Text %d@%d %s>" % (self.id, self.global_time, self.text)

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

        try:
            self._update_global_time, self._title, self._description, thumbnail_hash = self._database.execute(u"SELECT global_time, title, description, thumbnail_hash FROM square WHERE id = ?", (self._database_id,)).next()
            self._thumbnail_hash = str(thumbnail_hash)
        except StopIteration:
            self._update_global_time = 0
            self._title = u""
            self._description = u""
            self._thumbnail_hash = ""

        try:
            self._my_alias, my_thumbnail_hash = self._database.execute(u"SELECT alias, thumbnail_hash FROM member WHERE id = ? AND square = ?", (self._my_member.database_id, self._database_id)).next()
            self._my_thumbnail_hash = str(my_thumbnail_hash)
        except StopIteration:
            self._my_alias = u"Anonymous"
            self._my_thumbnail_hash = ""

        if __debug__: dprint("new Square '", self._title, "'.  using alias '", self._my_alias, "'")

        self.events = getEventBroker(self)
        self.global_events = getEventBroker(None)

        def load_history():
            for id_, global_time, member_id, member_alias, member_thumbnail_hash, text, media_hash, utc_timestamp in self._database.execute(u"SELECT text.id, text.global_time, text.member, member.alias, member.thumbnail_hash, text.text, text.media_hash, text.utc_timestamp FROM text JOIN member ON member.id = text.member WHERE text.square = ? ORDER BY global_time, utc_timestamp DESC LIMIT 100", (self._database_id,)):
                member = Member(self, member_id, member_alias, str(member_thumbnail_hash))
                text = Text(self, id_, global_time, member, text, str(media_hash), utc_timestamp)
                self.events.messageReceived(text)
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
        for message in messages:
            member = Member(self, message.authentication.member.database_id, message.payload.alias, message.payload.thumbnail_hash)

            # database data
            data.append((member.id, self._database_id, member.alias, buffer(member.thumbnail_hash)))

            if member.id == self._my_member.database_id:
                self._my_alias = member.alias
                self._my_thumbnail_hash = member.thumbnail_hash

            self.events.memberInfoUpdated(member)

        self._database.executemany(u"INSERT OR REPLACE INTO member (id, square, alias, thumbnail_hash) VALUES (?, ?, ?, ?)", data)

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
                self._database.execute(u"INSERT OR REPLACE INTO square (id, global_time, title, description, thumbnail_hash) VALUES (?, ?, ?, ?, ?)", (self._database_id, self._update_global_time, self._title, self._description, buffer(self._thumbnail_hash)))
                update = True

        if update:
            # update GUI: square info has changed
            self.events.squareInfoUpdated()

    def undo_square_info(self, *args):
        pass

    def post_text(self, text, media_hash):
        if self._my_member_info is None:
            raise ValueError("invalid my member info, set_my_member_info must be called at least once before posting")
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
        for message in messages:
            member = Member(self, message.payload.member_info.authentication.member.database_id, message.payload.member_info.payload.alias, message.payload.member_info.payload.thumbnail_hash)
            text = Text(self, message.packet_id, message.distribution.global_time, member, message.payload.text, message.payload.media_hash, message.payload.utc_timestamp)

            # database data
            data.append((text.id, text.global_time, self._database_id, member.id, text.text, buffer(text.media_hash), text.utc_timestamp))

            # update GUI: message has been received
            self.events.messageReceived(text)

        self._database.executemany(u"INSERT INTO text (id, global_time, square, member, text, media_hash, utc_timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)", data)

        if mark_as_hot:
            self._discovery.add_implicitly_hot_text(messages)

    def undo_text(self, *args):
        pass

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

class SquareCommunity(SquareBase):
    def __init__(self, *argv, **kwargs):
        super(SquareCommunity, self).__init__(*argv, **kwargs)

        #Notify about new square creation
        self.global_events.newCommunityCreated(self)

    def leave_square(self):
        return self._dispersy.reclassify_community(self, PreviewCommunity)

class PreviewCommunity(SquareBase):
    def __init__(self, *argv, **kwargs):
        super(PreviewCommunity, self).__init__(*argv, **kwargs)
        #Notify about new square creation
        self.global_events.newPreviewCommunityCreated(self)

    def on_text(self, messages, mark_as_hot=False):
        return super(PreviewCommunity, self).on_text(messages, mark_as_hot=mark_as_hot)

    def join_square(self):
        return self._dispersy.reclassify_community(self, SquareCommunity)

    # @property
    # def dispersy_acceptable_global_time_range(self):
    #     # we will accept the full 64 bit global time range
    #     return 2**64 - self._global_time

    # @property
    # def dispersy_enable_candidate_walker(self):
    #     return False


from events import getEventBroker
