import datetime
import time

from bxcommon.connections.abstract_connection import AbstractConnection
from bxcommon.messages.bloxroute.broadcast_message import BroadcastMessage
from bxcommon.messages.bloxroute.key_message import KeyMessage
from bxcommon.utils import logger, convert
from bxcommon.utils.object_hash import ObjectHash
from bxcommon.utils.stats.block_stat_event_type import BlockStatEventType
from bxcommon.utils.stats.block_statistics_service import block_stats


class AbstractGatewayBlockchainConnection(AbstractConnection):
    def __init__(self, sock, address, node, from_me=False):
        super(AbstractGatewayBlockchainConnection, self).__init__(sock, address, node, from_me)

        self.message_converter = None

    def msg_tx(self, msg):
        """
        Handle a TX message by broadcasting to the entire network
        """
        blx_txmsgs = self.message_converter.tx_to_bx_txs(msg, self.network_num)

        for (blx_txmsg, tx_hash, tx_bytes) in blx_txmsgs:
            # All connections outside of this one is a bloXroute server
            logger.debug("Broadcasting the transaction to peers")
            self.node.broadcast(blx_txmsg, self)
            self.node.get_tx_service().hash_to_contents[tx_hash] = tx_bytes

    def msg_block(self, msg):
        """
        Handle a block message. Sends to node for encryption, then broadcasts.
        """
        block_hash = msg.block_hash()

        block_stats.add_block_event_by_block_hash(block_hash, BlockStatEventType.BLOCK_RECEIVED_FROM_BLOCKCHAIN_NODE)

        if block_hash in self.node.blocks_seen.contents:
            block_stats.add_block_event_by_block_hash(block_hash,
                                                      BlockStatEventType.BLOCK_RECEIVED_FROM_BLOCKCHAIN_NODE_IGNORE_SEEN)
            logger.debug("Have seen block {0} before. Ignoring.".format(block_hash))
            return

        compress_start = datetime.datetime.utcnow()
        bloxroute_block = self.message_converter.block_to_bx_block(msg, self.node.get_tx_service())
        encrypted_block, block_hash = self.node.in_progress_blocks.encrypt_and_add_payload(bloxroute_block)
        broadcast_message = BroadcastMessage(ObjectHash(block_hash), self.network_num, encrypted_block)

        block_stats.add_block_event_by_block_hash(msg.block_hash(),
                                                  BlockStatEventType.BLOCK_COMPRESSED,
                                                  start_date_time=compress_start,
                                                  end_date_time=datetime.datetime.utcnow(),
                                                  encrypted_block_hash=convert.bytes_to_hex(block_hash),
                                                  original_size=len(msg.rawbytes()),
                                                  compressed_size=len(bloxroute_block))
        logger.debug("Compressed block with hash {0} to size {1} from size {2}"
                     .format(block_hash, len(broadcast_message.rawbytes()), len(msg.rawbytes())))

        self.node.block_recovery_service.cancel_recovery_for_block(msg.block_hash())

        conns = self.node.broadcast(broadcast_message, self)

        block_stats.add_block_event_by_block_hash(block_hash,
                                                  BlockStatEventType.ENC_BLOCK_SENT_FROM_GATEWAY_TO_PEER,
                                                  peers=map(lambda conn: (conn.peer_desc, conn.connection_type), conns))

        # TODO: wait for receipt of other messages before sending key
        self.send_key(block_hash)

    def send_key(self, block_hash):
        """
        Sends out the decryption key for a block hash.
        """
        key = self.node.in_progress_blocks.get_encryption_key(block_hash)
        key_message = KeyMessage(ObjectHash(block_hash), key, self.network_num)
        conns = self.node.broadcast(key_message, self)

        block_stats.add_block_event_by_block_hash(block_hash,
                                                  BlockStatEventType.ENC_BLOCK_KEY_SENT_FROM_GATEWAY_TO_PEER,
                                                  peers=map(lambda conn: (conn.peer_desc, conn.connection_type), conns))
