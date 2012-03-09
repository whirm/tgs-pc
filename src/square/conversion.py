from struct import pack, unpack_from

from dispersy.conversion import BinaryConversion
from dispersy.message import DropPacket, DelayPacketByMissingMessage

class Conversion(BinaryConversion):
    def __init__(self, community):
        super(Conversion, self).__init__(community, "\x01")
        self.define_meta_message(chr(2), community.get_meta_message(u"member-info"), self._encode_member_info, self._decode_member_info)
        self.define_meta_message(chr(3), community.get_meta_message(u"square-info"), self._encode_square_info, self._decode_square_info)
        self.define_meta_message(chr(4), community.get_meta_message(u"text"), self._encode_text, self._decode_text)

    def _encode_member_info(self, message):
        alias = message.payload.alias.encode("UTF-8")
        thumbnail_hash = message.payload.thumbnail_hash or "\x00" * 20
        return pack("!B", min(len(alias), 256-1)), alias[:256-1], thumbnail_hash

    def _decode_member_info(self, placeholder, offset, data):
        if len(data) < offset + 1:
            raise DropPacket("Insufficient packet size")
        alias_length, = unpack_from("!B", data, offset)
        offset += 1

        if len(data) < offset + alias_length:
            raise DropPacket("Insufficient packet size")
        try:
            alias = data[offset:offset+alias_length].decode("UTF-8")
        except UnicodeError:
            raise DropPacket("Unable to decode UTF-8")
        offset += alias_length

        if len(data) < offset + 20:
            raise DropPacket("Insufficient packet size")
        thumbnail_hash = data[offset:offset+20]
        if thumbnail_hash == "\x00" * 20:
            thumbnail_hash = ""
        offset += 20

        return offset, placeholder.meta.payload.implement(alias, thumbnail_hash)

    def _encode_square_info(self, message):
        title = message.payload.title.encode("UTF-8")
        description = message.payload.description.encode("UTF-8")
        thumbnail_hash = message.payload.thumbnail_hash or "\x00" * 20
        location = message.payload.location
        radius = message.payload.radius
        return (pack("!B", min(len(title), 256-1)), title[:256-1],
                pack("!H", min(len(description), 1024-1)), description[:1024-1],
                thumbnail_hash,
                pack("!LLL", location[0], location[1], radius))

    def _decode_square_info(self, placeholder, offset, data):
        if len(data) < offset + 1:
            raise DropPacket("Insufficient packet size")
        title_length, = unpack_from("!B", data, offset)
        offset += 1

        if len(data) < offset + title_length:
            raise DropPacket("Insufficient packet size")
        try:
            title = data[offset:offset+title_length].decode("UTF-8")
        except UnicodeError:
            raise DropPacket("Unable to decode UTF-8")
        offset += title_length

        if len(data) < offset + 2:
            raise DropPacket("Insufficient packet size")
        description_length, = unpack_from("!H", data, offset)
        if not description_length < 1024:
            raise DropPacket("invalid description_length")
        offset += 2

        if len(data) < offset + description_length:
            raise DropPacket("Insufficient packet size")
        try:
            description = data[offset:offset+description_length].decode("UTF-8")
        except UnicodeError:
            raise DropPacket("Unable to decode UTF-8")
        offset += description_length

        if len(data) < offset + 20:
            raise DropPacket("Insufficient packet size")
        thumbnail_hash = data[offset:offset+20]
        if thumbnail_hash == "\x00" * 20:
            thumbnail_hash = ""
        offset += 20

        if len(data) < offset + 12:
            raise DropPacket("Insufficient packet size")
        longitude, latitude, radius, = unpack_from("!LLL", data, offset)
        offset += 12

        return offset, placeholder.meta.payload.implement(title, description, thumbnail_hash, (longitude, latitude), radius)

    def _encode_text(self, message):
        member_info_global_time = message.payload.member_info.distribution.global_time
        text = message.payload.text.encode("UTF-8")
        media_hash = message.payload.media_hash or "\x00" * 20
        return pack("!QH", member_info_global_time, min(len(text), 1024-1)), text[:1024], media_hash

    def _decode_text(self, placeholder, offset, data):
        if len(data) < offset + 2:
            raise DropPacket("Insufficient packet size")
        member_info_global_time, text_length = unpack_from("!QH", data, offset)
        member_info = self._community.dispersy.get_last_message(self._community, placeholder.authentication.member, self._community.get_meta_message(u"member-info"))
        if not (member_info and member_info_global_time < member_info.distribution.global_time):
            # TODO implement DelayPacketByMissingLastMessage
            raise DelayPacketByMissingMessage(self._community, placeholder.authentication.member, [member_info_global_time])
        if not text_length < 1024:
            raise DropPacket("invalid text_length")
        offset += 10

        if len(data) < offset + text_length:
            raise DropPacket("Insufficient packet size")
        try:
            text = data[offset:offset+text_length].decode("UTF-8")
        except UnicodeError:
            raise DropPacket("Unable to decode UTF-8")
        offset += text_length

        if len(data) < offset + 20:
            raise DropPacket("Insufficient packet size")
        media_hash = data[offset:offset+20]
        if media_hash == "\x00" * 20:
            media_hash = ""
        offset += 20

        return offset, placeholder.meta.payload.implement(member_info, text, media_hash)

