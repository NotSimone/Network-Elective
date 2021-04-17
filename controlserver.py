# Control Server for Snooping Clients

import socket
import sys
from select import select
from typing import List

from server import Server, SnoopedPacket

SNOOP_SERVER_IP = "149.171.36.192"
SNOOP_SERVER_PORT = 8154

with Server() as server:
    # Connect and configure the clients
    client_count = 1 if len(sys.argv) < 2 else int(sys.argv[1])
    server.connect_clients(client_count)
    server.config_clients(ip=SNOOP_SERVER_IP, port=SNOOP_SERVER_PORT)

    ident = 30
    server.send_snoop_req(0, 1, ident)

    while True:
        ident += 1

        # Select on one of the clients returning data
        readable, _, exceptions = select(server.connections, [], server.connections)
        conn: socket.socket

        for conn in exceptions:
            print(f"Something has gone wrong with client {server.connections.index(conn)}")
            exit()

        for conn in readable:
            try:
                packets: List[SnoopedPacket] = server.get_snooped_packet(conn)
                for packet in packets:
                    print(f"Got {packet.request_ident};{packet.packet_ident};{packet.message}")
            except ConnectionAbortedError:
                print(f"Client {server.connections.index(conn)} closed connection")
                exit()
