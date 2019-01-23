import struct

from bxcommon.utils import crypto, convert
from bxgateway.btc_constants import BTC_HDR_COMMON_OFF, BTC_SHA_HASH_LEN
from bxgateway.messages.btc.btc_message import BtcMessage
from bxgateway.messages.btc.btc_message_type import BtcMessageType
from bxgateway.messages.btc.btc_messages_util import btcvarint_to_int, pack_int_to_btcvarint
from bxgateway.utils.btc.btc_object_hash import BtcObjectHash


def pack_outpoint(hash_val, index, buf, off):
    return struct.pack_into('<32cI', buf, off, hash_val, index)


# A transaction input.
# This class cannot parse a transaction input from rawbytes, but can construct one.
class TxIn(object):
    def __init__(self, prev_outpoint_hash=None, prev_out_index=None, sig_script=None, sequence=None, buf=None, off=None,
                 length=None):
        if buf is None:
            buf = bytearray(36 + 9 + len(sig_script) + 4)
            self.buf = buf

            off = 0
            pack_outpoint(prev_outpoint_hash, prev_out_index, buf, off)
            off += 36
            off += pack_int_to_btcvarint(len(sig_script), buf, off)
            buf[off:off + len(sig_script)] = sig_script
            off += len(sig_script)
            struct.pack('<I', buf, off, sequence)
            off += 4
            self.size = off
        else:
            self.buf = buf
            self.size = length
            self.off = off

        self._memoryview = memoryview(buf)

    def rawbytes(self):
        if self.size == len(self.buf) and self.off == 0:
            return self.buf
        else:
            return self._memoryview[self.off:self.off + self.size]


# A transaction output.
# This class cannot parse a transaction output from rawbytes, but can construct one.
class TxOut(object):
    def __init__(self, value=None, pk_script=None, buf=None, off=None, length=None):
        if buf is None:
            buf = bytearray(8 + 9 + len(pk_script))
            self.buf = buf

            off = 0
            struct.pack("<Q", buf, off, value)
            off += 8
            off += pack_int_to_btcvarint(len(pk_script), buf, off)
            buf[off:off + len(pk_script)] = pk_script
        else:
            self.buf = buf
            self.size = length
            self.off = off

        self._memoryview = memoryview(buf)

    def rawbytes(self):
        if self.size == len(self.buf) and self.off == 0:
            return self.buf
        else:
            return self._memoryview[self.off:self.off + self.size]


class TxBtcMessage(BtcMessage):
    """
    Transaction message. This class cannot fully parse a transaction message from bytes, but can construct one.

    Attributes
    ----------
    tx_in: a list of TxIn instances
    tx_out: a list of TxOut instances
    """
    MESSAGE_TYPE = BtcMessageType.TRANSACTIONS

    def __init__(self, magic=None, version=None, tx_in=None, tx_out=None, lock_time=None, buf=None):
        if buf is None:
            # TODO: this doesn't allocate correctly
            # need to allocate for len(tx_in) and len(tx_out) as well + test
            # and 2*9 is an upper bound for varint, find a precise value
            buf = bytearray(BTC_HDR_COMMON_OFF + 2 * 9 + 8)
            self.buf = buf

            off = BTC_HDR_COMMON_OFF
            struct.pack_into('<I', buf, off, version)
            off += 4
            off += pack_int_to_btcvarint(len(tx_in), buf, off)

            for inp in tx_in:
                rawbytes = inp.rawbytes()
                size = len(rawbytes)
                buf[off:off + size] = rawbytes
                off += size

            off += pack_int_to_btcvarint(len(tx_out), buf, off)

            for out in tx_out:
                rawbytes = out.rawbytes()
                size = len(rawbytes)
                buf[off:off + size] = rawbytes
                off += size

            struct.pack_into('<I', buf, off, lock_time)
            off += 4

            super(TxBtcMessage, self).__init__(magic, self.MESSAGE_TYPE, off - BTC_HDR_COMMON_OFF, buf)
        else:
            self.buf = buf
            self._memoryview = memoryview(buf)
            self._magic = self._command = self._payload_len = self._checksum = None
            self._payload = None

        self._version = None
        self._tx_in = None
        self._tx_out = None
        self._lock_time = None
        self._tx_hash = None
        self._tx_out_count = None
        self._tx_in_count = None

    def version(self):
        if self._version is None:
            off = BTC_HDR_COMMON_OFF
            self._version, = struct.unpack_from('<i', self.buf, off)
        return self._version

    def tx_in(self):
        if self._tx_in is None:
            off = BTC_HDR_COMMON_OFF + 4
            self._tx_in_count, size = btcvarint_to_int(self.buf, off)
            off += size
            self._tx_in = []

            start = off
            end = off

            for _ in xrange(self._tx_in_count):
                end += 36
                script_len, size = btcvarint_to_int(self.buf, end)
                end += size + script_len + 4
                self._tx_in.append(self.rawbytes()[start:end])
                start = end

            off = end
            self._tx_out_count, size = btcvarint_to_int(self.buf, off)
            self._tx_out = []
            off += size

            start = off
            end = off
            for _ in xrange(self._tx_out_count):
                end += 8
                script_len, size = btcvarint_to_int(self.buf, end)
                end += size + script_len
                self._tx_out.append(self.rawbytes()[start:end])

            off = end

            self._lock_time, = struct.unpack_from('<I', self.buf, off)

        return self._tx_in

    def tx_out(self):
        if self._tx_in is None:
            self.tx_in()
        return self._tx_out

    def lock_time(self):
        if self._tx_in is None:
            self.tx_in()
        return self._lock_time

    def tx_hash(self):
        if self._tx_hash is None:
            self._tx_hash = BtcObjectHash(buf=crypto.bitcoin_hash(self.payload()), length=BTC_SHA_HASH_LEN)
        return self._tx_hash

    def tx(self):
        return self.payload()

    def __repr__(self):
        return ("TxBtcMessage<version: {}, length: {}, tx_hash: {}, rawbytes: {}>"
                .format(self.version(),
                        len(self.rawbytes()),
                        convert.bytes_to_hex(self.tx_hash().binary),
                        convert.bytes_to_hex(
                            self.rawbytes().tobytes())))