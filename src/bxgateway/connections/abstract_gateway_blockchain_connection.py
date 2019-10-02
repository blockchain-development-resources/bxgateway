import socket
import time
import typing
from typing import TYPE_CHECKING

from bxutils import logging

from bxcommon.connections.abstract_connection import AbstractConnection
from bxcommon.connections.connection_type import ConnectionType
from bxcommon.messages.abstract_block_message import AbstractBlockMessage
from bxcommon.utils.stats import stats_format, hooks
from bxcommon.utils.stats.block_stat_event_type import BlockStatEventType
from bxcommon.utils.stats.block_statistics_service import block_stats
from bxcommon.utils.memory_utils import ObjectSize
from bxcommon.utils import memory_utils

from bxgateway import gateway_constants

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    from bxgateway.connections.abstract_gateway_node import AbstractGatewayNode

logger = logging.get_logger(__name__)


class AbstractGatewayBlockchainConnection(AbstractConnection["AbstractGatewayNode"]):
    CONNECTION_TYPE = ConnectionType.BLOCKCHAIN_NODE

    def __init__(self, sock, address, node, from_me=False):
        super(AbstractGatewayBlockchainConnection, self).__init__(sock, address, node, from_me)

        if node.opts.tune_send_buffer_size:
            # Requires OS tuning (for Linux here; MacOS and windows require different commands):
            # echo 'net.core.wmem_max=16777216' >> /etc/sysctl.conf && sysctl -p
            # cat /proc/sys/net/core/wmem_max # to check
            previous_buffer_size = sock.socket_instance.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
            try:
                sock.socket_instance.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF,
                                                gateway_constants.BLOCKCHAIN_SOCKET_SEND_BUFFER_SIZE)
                logger.info("Set socket send buffer size for blockchain connection to {}",
                            sock.socket_instance.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF))
            except Exception as e:
                logger.error("Could not set socket send buffer size for blockchain connection: {}", e)

            # Linux systems generally set the value to 2x what was passed in, so just make sure
            # the socket buffer is at least the size set
            set_buffer_size = sock.socket_instance.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
            if set_buffer_size < gateway_constants.BLOCKCHAIN_SOCKET_SEND_BUFFER_SIZE:
                logger.warning("Socket buffer size set was unsuccessful, and was instead set to {}. Reverting to: {}",
                            set_buffer_size, previous_buffer_size)
                sock.socket_instance.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, previous_buffer_size)

        self.message_converter = None
        self.connection_protocol = None
        self.is_server = False

    def advance_sent_bytes(self, bytes_sent):
        if self.message_tracker and self.message_tracker.is_sending_block_message():
            assert self.node.opts.track_detailed_sent_messages

            entry = self.message_tracker.messages[0]
            super(AbstractGatewayBlockchainConnection, self).advance_sent_bytes(bytes_sent)

            if not self.message_tracker.is_sending_block_message():
                block_message = typing.cast(AbstractBlockMessage, entry.message)
                block_message_queue_time = entry.queued_time
                block_message_length = entry.length
                block_hash = block_message.block_hash()
                handling_time, relay_desc = self.node.track_block_from_bdn_handling_ended(block_hash)
                block_stats.add_block_event_by_block_hash(block_hash,
                                                          BlockStatEventType.BLOCK_SENT_TO_BLOCKCHAIN_NODE,
                                                          network_num=self.network_num,
                                                          more_info="{} in {}; Handled in {}; R - {}; {}".format(
                                                              stats_format.byte_count(
                                                                  block_message_length
                                                              ),
                                                              stats_format.timespan(
                                                                  block_message_queue_time,
                                                                  time.time()
                                                              ),
                                                              stats_format.duration(handling_time),
                                                              relay_desc,
                                                              block_message.extra_stats_data()
                                                          ))
        else:
            super(AbstractGatewayBlockchainConnection, self).advance_sent_bytes(bytes_sent)

    def log_connection_mem_stats(self) -> None:
        """
        logs the connection's memory stats
        """
        super(AbstractGatewayBlockchainConnection, self).log_connection_mem_stats()
        t0 = time.time()
        class_name = self.__class__.__name__
        if self.message_converter is not None:
            hooks.add_obj_mem_stats(
                class_name,
                self.network_num,
                self.message_converter,
                "message_converter",
                memory_utils.ObjectSize(
                    "message_converter", memory_utils.get_special_size(self.message_converter).size, is_actual_size=True
                ),
                object_item_count=1,
                object_type=memory_utils.ObjectType.META,
                size_type=memory_utils.SizeType.SPECIAL
            )
        t_m_c_diff = round(time.time() - t0, 3)
        logger.info("Recording {} message_converter MemoryStats took: {} seconds".format(class_name, t_m_c_diff))
