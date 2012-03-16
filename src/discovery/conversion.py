from struct import pack, unpack_from

from hot import Hot

from dispersy.conversion import BinaryConversion
from dispersy.message import DropPacket

class Conversion(BinaryConversion):
    def __init__(self, community):
        super(Conversion, self).__init__(community, "\x01")
        self.define_meta_message(chr(1), community.get_meta_message(u"hots"), self._encode_hots, self._decode_hots)
        self.define_meta_message(chr(2), community.get_meta_message(u"search"), self._encode_search_request, self._decode_search_request)
        self.define_meta_message(chr(3), community.get_meta_message(u"search-response"), self._encode_search_response, self._decode_search_response)


    def _encode_hots(self, message):
        return [pack("!20s20sQ", hot.cid, hot.mid, hot.global_time) for hot in message.payload.hots]

    def _decode_hots(self, placeholder, offset, data):
        hots = []
        while len(data) > offset:
            if len(data) < offset + 48:
                raise DropPacket("Insufficient packet size")
            cid, mid, global_time = unpack_from("!20s20sQ", data, offset)
            offset += 48
            hots.append(Hot(cid, mid, global_time))

        if not hots:
            raise DropPacket("no hots found")

        return offset, placeholder.meta.payload.implement(hots)

    def _encode_search_request(self, message):
        identifier = message.payload.identifier
        expression = message.payload.expression.encode("UTF-8")
        return pack("!HH", identifier, min(len(expression), 1024-1)), expression[:1024-1]

    def _decode_search_request(self, placeholder, offset, data):
        if len(data) < offset + 4:
            raise DropPacket("Insufficient packet size")
        identifier, expression_length = unpack_from("!HH", data, offset)
        if not expression_length < 1024:
            raise DropPacket("invalid description_length")
        offset += 4

        if len(data) < offset + expression_length:
            raise DropPacket("Insufficient packet size")
        try:
            expression = data[offset:offset+expression_length].decode("UTF-8")
        except UnicodeError:
            raise DropPacket("Unable to decode UTF-8")
        offset += expression_length

        return offset, placeholder.meta.payload.implement(identifier, expression)

    def _encode_search_response(self, message):
        l = [pack("!H", message.payload.identifier)]
        l.extend(pack("!20s20sQ", hot.cid, hot.mid, hot.global_time) for hot in message.payload.hots)
        return l

    def _decode_search_response(self, placeholder, offset, data):
        if len(data) < offset + 2:
            raise DropPacket("Insufficient packet size")
        identifier, = unpack_from("!H", data, offset)
        offset += 2

        hots = []
        while len(data) > offset:
            if len(data) < offset + 48:
                raise DropPacket("Insufficient packet size")
            cid, mid, global_time = unpack_from("!20s20sQ", data, offset)
            offset += 48
            hots.append(Hot(cid, mid, global_time))

        if not hots:
            raise DropPacket("no hots found")

        return offset, placeholder.meta.payload.implement(identifier, hots)
