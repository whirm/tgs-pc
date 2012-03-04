from struct import pack, unpack_from

from hot import Hot

from dispersy.conversion import BinaryConversion
from dispersy.message import DropPacket

class Conversion(BinaryConversion):
    def __init__(self, community):
        super(Conversion, self).__init__(community, "\x01")
        self.define_meta_message(chr(1), community.get_meta_message(u"hots"), self._encode_hots, self._decode_hots)

    def _encode_hots(self, message):
        return [pack("!20c20cQ", hot.cid, hot.mid, hot.global_time)[0] for hot in message.payload.hots]

    def _decode_hots(self, placeholder, offset, data):
        hots = []
        while len(data) > offset:
            if len(data) < offset + 48:
                raise DropPacket("Insufficient packet size")
            cid, mid, global_time = unpack_from("!20c20cQ", data, offset)
            offset += 48
            hots.append(Hot(cid, mid, global_time))

        if not hots:
            raise DropPacket("no hots found")

        return offset, placeholder.meta.payload.implement(hots)
