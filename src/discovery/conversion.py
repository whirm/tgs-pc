from struct import pack, unpack_from

from dispersy.conversion import BinaryConversion
from dispersy.message import DropPacket

class Conversion(BinaryConversion):
    def __init__(self, community):
        super(Conversion, self).__init__(community, "\x01")
        self.define_meta_message(chr(1), community.get_meta_message(u"hots"), self._encode_hots, self._decode_hots)
        self.define_meta_message(chr(2), community.get_meta_message(u"search-member-request"), self._encode_search_request, self._decode_search_request)
        self.define_meta_message(chr(3), community.get_meta_message(u"search-member-response"), self._encode_search_response, self._decode_search_response)
        self.define_meta_message(chr(4), community.get_meta_message(u"search-square-request"), self._encode_search_request, self._decode_search_request)
        self.define_meta_message(chr(5), community.get_meta_message(u"search-square-response"), self._encode_search_response, self._decode_search_response)
        self.define_meta_message(chr(6), community.get_meta_message(u"search-text-request"), self._encode_search_request, self._decode_search_request)
        self.define_meta_message(chr(7), community.get_meta_message(u"search-text-response"), self._encode_search_response, self._decode_search_response)

    def _encode_hots(self, message):
        data = [pack("!B", len(message.payload.suggestions))]
        for weight, cid, mid, global_time in message.payload.suggestions:
            data.append(pack("!B20s20sQ", weight, cid, mid, global_time))
        return data

    def _decode_hots(self, placeholder, offset, data):
        if len(data) < offset + 1:
            raise DropPacket("Insufficient packet size")
        count, = unpack_from("!B", data, offset)
        offset += 1

        suggestions = []
        for _ in xrange(count):
            if len(data) < offset + 49:
                raise DropPacket("Insufficient packet size")
            suggestions.append(unpack_from("!B20s20sQ", data, offset))
            offset += 49

        if not suggestions:
            raise DropPacket("no suggestions found")

        return offset, placeholder.meta.payload.implement(suggestions)

    def _encode_search_request(self, message):
        payload = message.payload
        data = [pack("!HBB", payload.identifier, payload.threshold, len(payload.terms))]
        for weight, term in payload.terms:
            term = term.encode("UTF-8")
            data.append(pack("!bB", weight, len(term)))
            data.append(term)
        data.append(pack("!B", len(payload.squares)))
        for weight, cid in payload.squares:
            data.append(pack("!b20s", weight, cid))
        return data

    def _decode_search_request(self, placeholder, offset, data):
        if len(data) < offset + 4:
            raise DropPacket("Insufficient packet size")
        identifier, threshold, term_length = unpack_from("!HBB", data, offset)
        offset += 4

        terms = []
        for _ in xrange(term_length):
            if len(data) < offset + 2:
                raise DropPacket("Insufficient packet size")
            weight, term_length = unpack_from("!bB", data, offset)
            offset += 2

            if len(data) < offset + term_length:
                raise DropPacket("Insufficient packet size")
            try:
                term = data[offset:offset+term_length].decode("UTF-8")
            except UnicodeError:
                raise DropPacket("Unable to decode UTF-8")
            offset += term_length

            terms.append((weight, term))

        if len(data) < offset + 1:
            raise DropPacket("Insufficient packet size")
        square_length, = unpack_from("!B", data, offset)
        offset += 1

        squares = []
        for _ in xrange(square_length):
            if len(data) < offset + 21:
                raise DropPacket("Insufficient packet size")
            squares.append(unpack_from("!b20s", data, offset))
            offset += 21

        return offset, placeholder.meta.payload.implement(identifier, terms, squares, threshold)

    def _encode_search_response(self, message):
        payload = message.payload
        data = [pack("!HB", payload.identifier, len(payload.suggestions))]
        for weight, cid, mid, global_time in payload.suggestions:
            data.append(pack("!B20s20sQ", weight, cid, mid, global_time))
        return data

    def _decode_search_response(self, placeholder, offset, data):
        if len(data) < offset + 3:
            raise DropPacket("Insufficient packet size")
        identifier, count = unpack_from("!HB", data, offset)
        offset += 3

        suggestions = []
        for _ in xrange(count):
            if len(data) < offset + 49:
                raise DropPacket("Insufficient packet size")
            suggestions.append(unpack_from("!B20s20sQ", data, offset))
            offset += 49

        return offset, placeholder.meta.payload.implement(identifier, suggestions)
