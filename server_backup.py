# Server class

import socket
from typing import List

SERVER_PORT = 8080

CLIENT_HANDSHAKE = "snooping-client-req"
SERVER_HANDSHAKE = "snooping-server-ack"
ACK = "ack"

# Packet returned by client
class SnoopedPacket:
    def __init__(self, request_ident: int, packet_ident: int, message: str) -> None:
        self.request_ident = request_ident
        self.packet_ident = packet_ident
        self.message = message

# Control server
class Server:
    server_socket: socket.socket
    connections: List[socket.socket] = list()
    addresses: List = list()

    current_clients: int = 0
    total_clients: int

    def __enter__(self) -> "Server":
        self.init()
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback) -> None:
        self.cleanup()

    # Initialise the socket and begin listening
    def init(self) -> None:
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("", SERVER_PORT))
        self.server_socket.listen()
        print(f"Listening on port {SERVER_PORT}")

    # Connect to total_clients clients
    def connect_clients(self, total_clients: int) -> None:
        print(f"Waiting for {total_clients - self.current_clients} to connect")
        while self.current_clients < total_clients:
            conn, addr = self.server_socket.accept()
            print(f"Received connection from {addr}")
            data = conn.recv(1024)
            if data.decode() != CLIENT_HANDSHAKE:
                print(f"Bad handshake")
            else:
                conn.send(str.encode(SERVER_HANDSHAKE))
                data = conn.recv(1024)
                if data.decode() != ACK:
                    print("Bad ACK")
                    continue
                self.connections.append(conn)
                self.addresses.append(addr)
                self.current_clients += 1
                print(f"Handshake successful - client connected")
        print(f"All clients connected")

    # Configures snoopers to ip
    def config_clients(self, ip:str=None, port: int=None) -> None:
        if ip == None:
            ip = input("Enter server ip: ")
        if port == None:
            port = int(input("Enter server port: "))
        for conn in self.connections:
            conn.send(port.to_bytes(4, "little") + str.encode(ip))
        print(f"All clients configured to {ip}:{port}")
            
    # Send a snoop request to a client to forward onto the snoop server
    def send_snoop_req(self, client: int, request_num: int, request_ident: int) -> None:
        conn = self.connections[client]
        conn.send(request_num.to_bytes(4, "little") + request_ident.to_bytes(4, "little"))

    # Gets a snooped packet from an active connection
    def get_snooped_packet(self, conn: socket.socket) -> SnoopedPacket:
        data = conn.recv(1024)
        # Check if the connection is closed and return none
        if len(data) == 0:
            raise ConnectionAbortedError
        request_ident = int.from_bytes(data[:4], "little")
        packet_ident = int.from_bytes(data[4:8], "little")
        message_len = int.from_bytes(data[8:12], "little")
        message = data[12:12+message_len].decode()
        return SnoopedPacket(request_ident, packet_ident, message)

    # Cleanup when done
    def cleanup(self) -> None:
        print("Cleaning up")
        self.server_socket.close()
        for conn in self.connections:
            conn.close()
