from collections import deque

from bxcommon.connections.connection_state import ConnectionState
from bxgateway import gateway_constants
from bxgateway.connections.btc.btc_base_connection_protocol import BtcBaseConnectionProtocol
from bxgateway.messages.btc.btc_message_type import BtcMessageType
from bxgateway.messages.btc.ver_ack_btc_message import VerAckBtcMessage


class BtcRemoteConnectionProtocol(BtcBaseConnectionProtocol):
    def __init__(self, connection):
        super(BtcRemoteConnectionProtocol, self).__init__(connection)

        connection.message_handlers.update({
            BtcMessageType.VERSION: self.msg_version,
            BtcMessageType.BLOCK: self.msg_proxy_response,
            BtcMessageType.HEADERS: self.msg_proxy_response,
            BtcMessageType.INVENTORY: self.msg_proxy_response,
        })

    def msg_version(self, _msg):
        """
        Handle version message.
        Gateway initiates connection, so do not check for misbehavior. Record that we received the version message,
        send a verack, and synchronize chains if need be.
        """
        self.connection.state |= ConnectionState.ESTABLISHED
        reply = VerAckBtcMessage(self.magic)
        self.connection.enqueue_msg(reply)
        self.connection.node.alarm_queue.register_alarm(gateway_constants.BLOCKCHAIN_PING_INTERVAL_S,
                                                        self.connection.send_ping)

        if self.connection.is_active():
            for each_msg in self.connection.node.remote_node_msg_queue:
                self.connection.enqueue_msg_bytes(each_msg)

            if self.connection.node.remote_node_msg_queue:
                self.connection.node.remote_node_msg_queue = deque()

            self.connection.node.remote_node_conn = self.connection