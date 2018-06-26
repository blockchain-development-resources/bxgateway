#
# Copyright (C) 2017, bloXroute Labs, All rights reserved.
# See the file COPYING for details.
#
# Startup script for nodes
#

from bxcommon.util import startup_util
from connections import *

# Extra parameters for gateway that are parsed from the config file.
GATEWAY_PARAMS = [
    'node_params',
    'node_addr'
]
MAX_NUM_CONN = 8192
CONFIG_FILE_NAME = "config.cfg"

if __name__ == '__main__':
    # Log our pid to a file.
    with open("relay.pid", "w") as f:
        f.write(str(os.getpid()))

    parser = startup_util.get_default_parser()
    parser.add_argument("-b", "--blockchain-node",
                        help="Blockchain node ip and port to connect to, space delimited, typically localhost")
    parser.add_argument("--blockchain-net-magic", help="Blockchain net.magic parameter")
    parser.add_argument("--blockchain-services", help="Blockchain services parameter")
    parser.add_argument("--bloxroute-version", help="Bloxroute version number")
    parser.add_argument("--blockchain-version", help="Blockchain protocol version")

    opts = parser.parse_args()

    # The local name is the section of the config.cfg we will read
    # It can be specified with -c or will be the local ip of the machine
    my_local_name = opts.config_name or startup_util.get_my_ip()

    # Parse the config file.
    config, params = startup_util.parse_config_file(CONFIG_FILE_NAME, my_local_name, GATEWAY_PARAMS)

    # Set basic variables.
    # XXX: Add assert statements to make sure these make sense.
    ip = opts.network_ip or params['my_ip']
    assert ip is not None, "Your IP address is not specified in config.cfg or as --network-ip. Check that the '-n' " \
                           "argument reflects the name of a section in config.cfg!"

    port = int(opts.port or params['my_port'])

    log_setmyname("%s:%d" % (ip, port))
    log_path = opts.log_path or params['log_path']
    use_stdout = opts.to_stdout or params['log_stdout']
    log_init(log_path, use_stdout)
    log_debug("My own IP for config purposes is {0}".format(my_local_name))

    # Initialize the node and register the peerfile update signal to USR2 signal.
    relay_nodes = startup_util.parse_peers(opts.peers or params['peers'])

    node_param_list = {}
    if params['node_params']:
        node_param_list = [x.strip() for x in params['node_params'].split(",")]

    node_params = {}

    if node_param_list:
        for param in node_param_list:
            node_params[param] = startup_util.getparam(config, my_local_name, param)

    if opts.blockchain_node:
        params['node_addr'] = opts.blockchain_node
    if opts.blockchain_net_magic:
        node_params['magic'] = opts.blockchain_net_magic
    if opts.blockchain_services:
        node_params['services'] = opts.blockchain_services
    if opts.bloxroute_version:
        node_params['bloxroute_version'] = opts.bloxroute_version
    if opts.blockchain_version:
        node_params['protocol_version'] = opts.blockchain_version
    if opts.bloxroute_version:
        node_params['version'] = opts.bloxroute_version

    tokens = params['node_addr'].strip().split()
    node_ip = socket.gethostbyname(tokens[0])
    node_port = int(tokens[1])
    node_addr = (node_ip, node_port)

    node = Client(ip, port, relay_nodes, node_addr, node_params)

    # Start main loop
    try:
        log_debug("running node")
        node.run()
    finally:
        log_crash("node run method returned")
        log_crash("Log closed")
        log_close()
