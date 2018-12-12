import socket
import time

from bxcommon.connections.connection_type import ConnectionType

from bxcommon.connections.abstract_connection import AbstractConnection
from bxcommon.utils import logger
from bxgateway import eth_constants
from bxgateway.messages.eth.discovery.eth_discovery_message_factory import eth_discovery_message_factory
from bxgateway.messages.eth.discovery.eth_discovery_message_type import EthDiscoveryMessageType
from bxgateway.messages.eth.discovery.ping_eth_discovery_message import PingEthDiscoveryMessage


class EthNodeDiscoveryConnection(AbstractConnection):
    
    """
    Discovery protocol connection with Ethereum node.
    This connection is used to obtain public key of Ethereum node from Ping message.
    """

    connection_type = ConnectionType.BLOCKCHAIN_NODE

    def __init__(self, sock, address, node, from_me):
        super(EthNodeDiscoveryConnection, self).__init__(sock, address, node, from_me)

        self.message_factory = eth_discovery_message_factory
        self.message_handlers = {
            EthDiscoveryMessageType.PING: self.msg_ping,
            EthDiscoveryMessageType.PONG: self.msg_pong
        }

        self.can_send_pings = True
        self.ping_message = PingEthDiscoveryMessage(None,
                                                    self.node.get_private_key(),
                                                    eth_constants.P2P_PROTOCOL_VERSION,
                                                    (self.external_ip, self.external_port, self.external_port),
                                                    (socket.gethostbyname(self.peer_ip), self.peer_port, self.peer_port),
                                                    int(time.time()) + eth_constants.PING_MSG_TTL_SEC)
        self.pong_message = None

        self._pong_received = False

        self.send_ping()
        self.node.alarm_queue.register_alarm(eth_constants.DISCOVERY_PONG_TIMEOUT_SEC, self._pong_timeout)

        self.hello_messages = [EthDiscoveryMessageType.PING, EthDiscoveryMessageType.PONG]

    def msg_ping(self, msg):
        logger.debug("Discovery ping message received. Ignoring.")

    def msg_pong(self, msg):
        logger.debug("Discovery pong received.")
        self.node.set_remote_public_key(self, msg.get_public_key())
        self._pong_received = True

    def _pong_timeout(self):
        if not self._pong_received:
            logger.warn("Pong message was not received within allocated timeout connection. Closing connection.")
            self.mark_for_close(force_destroy_now=True)
