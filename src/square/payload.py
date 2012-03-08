from dispersy.payload import Payload

class MemberInfoPayload(Payload):
    class Implementation(Payload.Implementation):
        def __init__(self, meta, alias, thumbnail_hash):
            assert isinstance(alias, unicode)
            assert len(alias.encode("UTF-8")) < 256
            assert isinstance(thumbnail_hash, str)
            assert thumbnail_hash == "" or len(thumbnail_hash) == 20
            super(MemberInfoPayload.Implementation, self).__init__(meta)
            self._alias = alias
            self._thumbnail_hash = thumbnail_hash

        @property
        def alias(self):
            return self._alias

        @property
        def thumbnail_hash(self):
            return self._thumbnail_hash

class SquareInfoPayload(Payload):
    class Implementation(Payload.Implementation):
        def __init__(self, meta, title, description, thumbnail_hash, location, radius):
            assert isinstance(title, unicode)
            assert len(title.encode("UTF-8")) < 256
            assert isinstance(description, unicode)
            assert len(description.encode("UTF-8")) < 1024
            assert isinstance(thumbnail_hash, str)
            assert thumbnail_hash == "" or len(thumbnail_hash) == 20
            assert isinstance(location, tuple)
            assert len(location) == 2
            assert isinstance(location[0], int)
            assert isinstance(location[1], int)
            assert isinstance(radius, int)
            super(SquareInfoPayload.Implementation, self).__init__(meta)
            self._title = title
            self._description = description
            self._thumbnail_hash = thumbnail_hash
            self._location = location
            self._radius = radius

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
            return self._location

        @property
        def radius(self):
            return self._radius

class TextPayload(Payload):
    class Implementation(Payload.Implementation):
        def __init__(self, meta, member_info, text, media_hash):
            if __debug__:
                from dispersy.message import Message
            assert isinstance(member_info, Message.Implementation), member_info
            assert isinstance(text, unicode), text
            assert len(text.encode("UTF-8")) < 1024, text
            assert isinstance(media_hash, str), media_hash
            assert media_hash == "" or len(media_hash) == 20, media_hash
            super(TextPayload.Implementation, self).__init__(meta)
            self._member_info = member_info
            self._text = text
            self._media_hash = media_hash

        @property
        def member_info(self):
            return self._member_info

        @property
        def text(self):
            return self._text

        @property
        def media_hash(self):
            return self._media_hash
