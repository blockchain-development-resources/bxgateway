from bxcommon.utils.blockchain_utils.ont import ont_common_constants

ONT_MAGIC_NUMBERS = {
    "mainnet": 0x8C77AB60,
    "polaris": 0x2D8829DF
}

STARTUP_CAP = bytes(32)
STARTUP_RELAY_STATE = True
STARTUP_IS_CONSENSUS = True

ONT_HDR_COMMON_OFF = 24
ONT_HEADER_MINUS_CHECKSUM = 20

ONT_HASH_LEN = ont_common_constants.ONT_HASH_LEN
ONT_BOOKKEEPER_LEN = 33
ONT_BOOKKEEPER_AND_VARINT_LEN = 42
ONT_NODE_ADDR_LEN = 44
ONT_VARINT_MAX_LEN = 9
ONT_IP_PORT_SIZE = 2
ONT_IP_ADDR_SIZE = 16

ONT_LONG_LONG_LEN = 8
ONT_INT_LEN = 4
ONT_SHORT_LEN = 2
ONT_CHAR_LEN = 1

ONT_MSG_CHECKSUM_LEN = 4
ONT_ADDR_TIME_AND_SERV_LEN = 16
ONT_ADDR_PORTS_AND_ID_LEN = 12
ONT_BLOCK_TIME_HEIGHT_CONS_DATA_LEN = 16
ONT_BLOCK_NEXT_BOOKKEEPER_LEN = 20
ONT_DATA_MSG_LEN = 65
ONT_GET_DATA_MSG_LEN = 33
ONT_VERSION_VER_SERV_TIME_LEN = 20
ONT_VERSION_PORTS_LEN = 6
ONT_VERSION_LOAD_LEN = 51
ONT_VERSION_MSG_LEN = 101

BLOCK_PROPOSAL_CONSENSUS_MESSAGE_TYPE = 0

ONT_NODE_SERVICES = 1

ONT_HELLO_MESSAGES = [b"version", b"verack"]

ONT_SHORT_ID_INDICATOR = 0xFF
ONT_SHORT_ID_INDICATOR_AS_BYTEARRAY = bytearray([ONT_SHORT_ID_INDICATOR])
ONT_SHORT_ID_INDICATOR_LENGTH = 1

ONT_PING_INTERVAL_S = 3
ONT_MAX_QUEUED_BLOCKS = 20

ONT_TX_DEPLOY_TYPE_INDICATOR = 0xD0
ONT_TX_DEPLOY_TYPE_INDICATOR_AS_BYTEARRAY = bytearray([ONT_TX_DEPLOY_TYPE_INDICATOR])
ONT_TX_INVOKE_TYPE_INDICATOR = 0xD1
ONT_TX_INVOKE_TYPE_INDICATOR_AS_BYTEARRAY = bytearray([ONT_TX_INVOKE_TYPE_INDICATOR])

ONT_DEFAULT_BLOCK_SIZE = 621000
ONT_MINIMAL_SUB_TASK_TX_COUNT = 2500

BLOCK_CONFIRMATION_REQUEST_INTERVALS = 5
BLOCK_CONFIRMATION_REQUEST_CACHE_INTERVAL_S = 30 * 60

TRACKED_BLOCK_CLEANUP_INTERVAL_S = 15
BLOCK_CLEANUP_NODE_BLOCK_LIST_POLL_INTERVAL_S = 0
