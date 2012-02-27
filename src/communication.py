import errno
import socket
import select

if __debug__:
    from dispersy.dprint import dprint

SOCKET_BLOCK_ERRORCODE = errno.EWOULDBLOCK

class DispersySocket(object):
    def __init__(self, callback, dispersy, port, ip="0.0.0.0"):
        while True:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 870400)
                self.socket.bind((ip, port))
                self.socket.setblocking(0)
                if __debug__: dprint("Dispersy listening at ", port, force=True)
            except socket.error, error:
                port += 1
                continue
            break

        self.callback = callback
        self.dispersy = dispersy
        self.sendqueue = []
        self.callback.register(self._periodic_IO)

    def _periodic_IO(self):
        POLLIN, POLLOUT = select.POLLIN, select.POLLOUT
        poll = select.poll()
        poll.register(self.socket, POLLIN)
        while True:
            yield 1.0
            for sock, event in poll.poll(0.0):
                if event & POLLIN:
                    packets = []
                    try:
                        while True:
                            (data, addr) = self.socket.recvfrom(65535)
                            packets.append((addr, data))
                    except socket.error:
                        pass

                    finally:
                        if packets:
                            self.dispersy.data_came_in(packets)

            if self.sendqueue:
                print "sendqueue fail..."
                del self.sendqueue[:]

    def get_address(self):
        return self.socket.getsockname()

    def send(self, address, data):
        try:
            self.socket.sendto(data, address)
        except socket.error, error:
            if error[0] == SOCKET_BLOCK_ERRORCODE:
                self.sendqueue.append((data, address))
                self.rawserver.add_task(self.process_sendqueue, 0.1)

    def process_sendqueue(self):
        sendqueue = self.sendqueue
        self.sendqueue = []

        while sendqueue:
            data, address = sendqueue.pop(0)
            try:
                self.socket.sendto(data, address)
            except socket.error, error:
                if error[0] == SOCKET_BLOCK_ERRORCODE:
                    self.sendqueue.append((data, address))
                    self.sendqueue.extend(sendqueue)
                    self.rawserver.add_task(self.process_sendqueue, 0.1)
                    break

def get_socket(callback, dispersy):
    return DispersySocket(callback, dispersy, 12345)
