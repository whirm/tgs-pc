
from state import DummyState, UnknownState, SquareState, TaskGroupState
from conversion import Conversion
from payload import MemberInfoPayload, SquareInfoPayload, MessagePayload

from dispersy.authentication import MemberAuthentication
from dispersy.community import Community
from dispersy.conversion import DefaultConversion
from dispersy.destination import CommunityDestination
from dispersy.distribution import FullSyncDistribution, LastSyncDistribution
from dispersy.message import Message
from dispersy.resolution import DynamicResolution, PublicResolution, LinearResolution

if __debug__:
    from dispersy.dprint import dprint

class SquareBase(Community):
    def __init__(self, master, my_member):
        self._state = DummyState()

        super(SquareBase, self).__init__(master, my_member)

        try:
            packet, = self._dispersy.database.execute(u"SELECT packet FROM sync WHERE meta_message = ? AND member = ? ORDER BY global_time DESC LIMIT 1", (self._meta_messages[u"member-info"].database_id, self._my_member.database_id)).next()
        except StopIteration:
            self._my_member_info = None
        else:
            self._my_member_info = self._dispersy.convert_packet_to_message(str(packet), self)

        if self._my_member_info is None:
            self.set_member_info(u"Anonymous", "")

        try:
            packet, = self._dispersy.database.execute(u"SELECT packet FROM sync WHERE meta_message = ? ORDER BY global_time DESC LIMIT 1", (self._meta_messages[u"member-info"].database_id,)).next()
        except StopIteration:
            self._square_info = None
        else:
            self._square_info = self._dispersy.convert_packet_to_message(str(packet), self)

        if self._square_info is None:
            self.set_square_info(u"Unknown", u"", "", (0, 0), 0)

    def initiate_meta_messages(self):
        return [Message(self, u"member-info", MemberAuthentication(encoding="sha1"), DynamicResolution(PublicResolution(), LinearResolution()), LastSyncDistribution(synchronization_direction=u"ASC", priority=16, history_size=1), CommunityDestination(node_count=0), MemberInfoPayload(), self._dispersy._generic_timeline_check, self.on_member_info),
                Message(self, u"square-info", MemberAuthentication(encoding="sha1"), DynamicResolution(PublicResolution(), LinearResolution()), LastSyncDistribution(synchronization_direction=u"ASC", priority=128, history_size=1), CommunityDestination(node_count=10), SquareInfoPayload(), self._dispersy._generic_timeline_check, self.on_square_info),
                Message(self, u"message", MemberAuthentication(encoding="sha1"), DynamicResolution(PublicResolution(), LinearResolution()), FullSyncDistribution(enable_sequence_number=False, synchronization_direction=u"DESC", priority=128), CommunityDestination(node_count=10), MessagePayload(), self._dispersy._generic_timeline_check, self.on_message)]

    def initiate_conversions(self):
        return [DefaultConversion(self), Conversion(self)]

    @property
    def my_member_info(self):
        return self._my_member_info.payload

    @property
    def title(self):
        return self._square_info.payload.title

    @property
    def description(self):
        return self._square_info.payload.description

    @property
    def thumbnail_hash(self):
        return self._square_info.payload.thumbnail_hash

    @property
    def location(self):
        return self._square_info.payload.location

    @property
    def radius(self):
        return self._square_info.payload.radius

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
        allowed, _ = self._timeline.allowed(self._meta_messages[u"message"], self.global_time + 1)
        return allowed

    def dispersy_on_dynamic_settings(self, messages, initializing=False):
        super(SquareBase, self).dispersy_on_dynamic_settings(messages, initializing)

        global_time = self.global_time + 1
        policies = []
        for name in [u"member-info", u"square-info", u"message"]:
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
        for name in [u"member-info", u"square-info", u"message"]:
            meta = self._meta_messages[name]
            policies.append((meta, meta.resolution.policies[1]))
        self._dispersy.create_dynamic_settings(self, policies)
        self._dispersy.reclassify_community(self, TaskGroup)

    def convert_to_square(self):
        # TODO this check should be done in dispersy.py
        meta = self._meta_messages[u"dispersy-dynamic-settings"]
        if not self._timeline.allowed(meta, self.global_time + 1)[0]:
            raise ValueError("not allowed")
        policies = []
        for name in [u"member-info", u"square-info", u"message"]:
            meta = self._meta_messages[name]
            policies.append((meta, meta.resolution.policies[0]))
        self._dispersy.create_dynamic_settings(self, policies)
        self._dispersy.reclassify_community(self, Square)

    def set_member_info(self, name, thumbnail_hash):
        if not (isinstance(name, unicode) and len(name.encode("UTF-8")) < 256):
            raise ValueError("invalid name")
        if not (isinstance(thumbnail_hash, str) and len(thumbnail_hash) in (0, 20)):
            raise ValueError("invalid thumbnail hash")
        meta = self._meta_messages[u"member-info"]
        if not self._timeline.allowed(meta, self.global_time + 1)[0]:
            raise ValueError("not allowed")
        self._my_member_info = meta.impl(authentication=(self._my_member,), distribution=(self.claim_global_time(),), payload=(name, thumbnail_hash))
        self._dispersy.store_update_forward([self._my_member_info], True, True, True)
        return self._my_member_info

    def on_member_info(self, messages):
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
        message = meta.impl(authentication=(self._my_member,), distribution=(self.claim_global_time(),), payload=(title, description, thumbnail_hash, location, radius))
        self._dispersy.store_update_forward([message], True, True, True)
        return message

    def on_square_info(self, messages):
        # because LastSyncDistribution works per member we will need to keep the most recent
        for message in messages:
            if message.distribution.global_time > self._square_info.distribution.global_time and message.packet > self._square_info.packet:
                self._square_info = message
        # update GUI: square info has changed

    def post_message(self, message, media_hash):
        if not (isinstance(message, unicode) and len(message.encode("UTF-8")) < 1024):
            raise ValueError("invalid message")
        if not (isinstance(media_hash, str) and len(media_hash) in (0, 20)):
            raise ValueError("invalid media hash")
        meta = self._meta_messages[u"text"]
        if not self._timeline.allowed(meta, self.global_time + 1)[0]:
            raise ValueError("not allowed")
        message = meta.impl(authentication=(self._my_member,), distribution=(self.claim_global_time(),), payload=(message, media_hash))
        self._dispersy.store_update_forward([message], True, True, True)
        return message

    def on_message(self, messages):
        for message in messages:
            pass
            # TODO store in local chat log database
            # update GUI: message has been received
            # self.textMessageReceived.emit(message.payload.text)

    def get_hot_message(self, hot):
        members = self._dispersy.get_members_from_id

class SquareCommunity(SquareBase):
    pass

class PreviewCommunity(SquareBase):
    @property
    def dispersy_acceptable_global_time_range(self):
        # we will accept the full 64 bit global time range
        return 2**64 - self._global_time

    @property
    def dispersy_enable_candidate_walker(self):
        return False
