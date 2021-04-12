# Control Server for Snooping Clients

import socket
from typing import List

SERVER_PORT = 7209

CLIENT_HANDSHAKE = "snooping-client-req"
SERVER_HANDSHAKE = "snooping-server-ack"

class Server:
    server_socket: socket.socket
    connections: List[socket.socket] = list()
    addresses: List = list()

    current_clients: int = 0
    total_clients: int

    def __init__(self) -> None:
        pass

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
                self.connections.append(conn)
                self.addresses.append(addr)
                self.current_clients += 1
                print(f"Handshake successful - client connected")
        print(f"All clients connected")

    # Configures snoopers to ip
    def config_ip(self) -> None:
        ip = input("Enter server ip: ")
        for conn in self.connections:
            conn.send(str.encode(ip))

    # Send a snoop request to a client to forward onto the snoop server
    def send_snoop_req(self, client: int, request_num: int, request_ident: int) -> None:
        conn = self.connections[client]
        conn.send(request_num.to_bytes(4, "little") + request_ident.to_bytes(4, "little"))

    # Cleanup when done
    def cleanup(self) -> None:
        print("Cleaning up")
        self.server_socket.close()
        for conn in self.connections:
            conn.close()



server = Server()
try:
    server.init()
    server.connect_clients(1)
    server.config_ip()
    server.send_snoop_req(0, 12345, 6789)
finally:
    server.cleanup()
