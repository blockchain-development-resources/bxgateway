from bxcommon.constants import MSG_TYPE_LEN
from bxcommon.test_utils import helpers
from bxcommon.test_utils.abstract_test_case import AbstractTestCase
from bxcommon.test_utils.helpers import create_input_buffer_with_message
from bxcommon.utils import crypto
from bxcommon.utils.object_hash import ObjectHash
from bxgateway.messages.btc.data_btc_message import GetBlocksBtcMessage
from bxgateway.messages.gateway.block_holding_message import BlockHoldingMessage
from bxgateway.messages.gateway.block_propagation_request import BlockPropagationRequestMessage
from bxgateway.messages.gateway.block_received_message import BlockReceivedMessage
from bxgateway.messages.gateway.blockchain_sync_request_message import BlockchainSyncRequestMessage
from bxgateway.messages.gateway.blockchain_sync_response_message import BlockchainSyncResponseMessage
from bxgateway.messages.gateway.gateway_hello_message import GatewayHelloMessage
from bxgateway.messages.gateway.gateway_message_factory import gateway_message_factory
from bxgateway.messages.gateway.gateway_message_type import GatewayMessageType
from bxgateway.utils.btc.btc_object_hash import BtcObjectHash


class GatewayMessageFactoryTest(AbstractTestCase):
    HASH = ObjectHash(crypto.double_sha256("123"))
    BLOCK = helpers.generate_bytearray(30)

    def get_message_preview_successfully(self, message, expected_command, expected_payload_length):
        is_full_message, command, payload_length = gateway_message_factory.get_message_header_preview_from_input_buffer(
            create_input_buffer_with_message(message)
        )
        self.assertTrue(is_full_message)
        self.assertEqual(expected_command, command)
        self.assertEqual(expected_payload_length, payload_length)

    def create_message_successfully(self, message, message_type):
        result = gateway_message_factory.create_message_from_buffer(message.rawbytes())
        self.assertIsInstance(result, message_type)
        return result

    def test_message_preview_success_all_gateway_types(self):
        self.get_message_preview_successfully(GatewayHelloMessage(123, 1, "127.0.0.1", 40000, 1),
                                              GatewayMessageType.HELLO, GatewayHelloMessage.PAYLOAD_LENGTH)
        self.get_message_preview_successfully(BlockReceivedMessage(self.HASH),
                                              GatewayMessageType.BLOCK_RECEIVED, BlockReceivedMessage.PAYLOAD_LENGTH)
        self.get_message_preview_successfully(BlockPropagationRequestMessage(self.BLOCK),
                                              GatewayMessageType.BLOCK_PROPAGATION_REQUEST, len(self.BLOCK))
        self.get_message_preview_successfully(BlockHoldingMessage(self.HASH),
                                              GatewayMessageType.BLOCK_HOLDING, BlockHoldingMessage.PAYLOAD_LENGTH)

        hash_val = BtcObjectHash(buf=crypto.double_sha256("123"), length=crypto.SHA256_HASH_LEN)
        blockchain_message = GetBlocksBtcMessage(12345, 23456, [hash_val], hash_val).rawbytes()
        self.get_message_preview_successfully(
            BlockchainSyncRequestMessage(GetBlocksBtcMessage.MESSAGE_TYPE, blockchain_message),
            BlockchainSyncRequestMessage.MESSAGE_TYPE,
            MSG_TYPE_LEN + len(blockchain_message)
        )
        self.get_message_preview_successfully(
            BlockchainSyncResponseMessage(GetBlocksBtcMessage.MESSAGE_TYPE, blockchain_message),
            BlockchainSyncResponseMessage.MESSAGE_TYPE,
            MSG_TYPE_LEN + len(blockchain_message)
        )

    def test_create_message_success_all_gateway_types(self):
        hello_message = self.create_message_successfully(GatewayHelloMessage(123, 1, "127.0.0.1", 40001, 1),
                                                         GatewayHelloMessage)
        self.assertEqual(123, hello_message.protocol_version())
        self.assertEqual(1, hello_message.network_num())
        self.assertEqual("127.0.0.1", hello_message.ip())
        self.assertEqual(40001, hello_message.port())
        self.assertEqual(1, hello_message.ordering())

        block_recv_message = self.create_message_successfully(BlockReceivedMessage(self.HASH), BlockReceivedMessage)
        self.assertEqual(self.HASH, block_recv_message.block_hash())

        block_holding_message = self.create_message_successfully(BlockHoldingMessage(self.HASH), BlockHoldingMessage)
        self.assertEqual(self.HASH, block_holding_message.block_hash())

        block_propagation_request_message = self.create_message_successfully(BlockPropagationRequestMessage(self.BLOCK),
                                                                             BlockPropagationRequestMessage)
        self.assertEqual(self.BLOCK, block_propagation_request_message.blob())

        hash_val = BtcObjectHash(buf=crypto.double_sha256("123"), length=crypto.SHA256_HASH_LEN)
        blockchain_message_in = GetBlocksBtcMessage(12345, 23456, [hash_val], hash_val).rawbytes()
        sync_request_message = self.create_message_successfully(
            BlockchainSyncRequestMessage(GetBlocksBtcMessage.MESSAGE_TYPE, blockchain_message_in),
            BlockchainSyncRequestMessage)
        blockchain_message_out = GetBlocksBtcMessage(buf=sync_request_message.payload())
        self.assertEqual(12345, blockchain_message_out.magic())
        self.assertEqual(23456, blockchain_message_out.version())
        self.assertEqual(1, blockchain_message_out.hash_count())
        self.assertEqual(hash_val, blockchain_message_out.hash_stop())

        sync_response_message = self.create_message_successfully(
            BlockchainSyncResponseMessage(GetBlocksBtcMessage.MESSAGE_TYPE, blockchain_message_in),
            BlockchainSyncResponseMessage)

        blockchain_message_out = GetBlocksBtcMessage(buf=sync_request_message.payload())
        self.assertEqual(12345, blockchain_message_out.magic())
        self.assertEqual(23456, blockchain_message_out.version())
        self.assertEqual(1, blockchain_message_out.hash_count())
        self.assertEqual(hash_val, blockchain_message_out.hash_stop())
