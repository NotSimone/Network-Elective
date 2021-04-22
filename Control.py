# Control Server for Snooping Clients

import socket
import sys
from select import select
from typing import List, Set
import time
import random
from Server import Server, SnoopedPacket
from MessageReconstructor import MessageReconstructor

SNOOP_SERVER_IP = "149.171.36.192"
SNOOP_SERVER_PORT = 8154
HTTP_SERVER_PORT = 8155

def main() -> None:
    with Server() as server:
        # Connect and configure the clients
        client_count = 1 if len(sys.argv) < 2 else int(sys.argv[1])
        bitrate = 1000 if len(sys.argv) < 3 else int(sys.argv[2])
        # Detection timeout
        timeout = 55 / bitrate

        server.connect_clients(client_count)
        server.config_clients(ip=SNOOP_SERVER_IP, port=SNOOP_SERVER_PORT)
        
        ident = 0
        
        # Set of clients that have responded this iteration
        client_responses = set(range(client_count))
        
        message_reconstructor = MessageReconstructor()
        
        while True:
            # If all clients have responded or we have timed out
            if len(client_responses) == client_count:
                message = message_reconstructor.reconstruct_message()
                if message:
                    # Send the message to the server
                    if (send_message(message)):
                        # Message accepted, reset the loop and continue
                        print("Message accepted by server")
                        message_reconstructor = MessageReconstructor()
                        client_responses = set(range(client_count))
                        continue

                # Add jitter into the timeout to make sure we dont just loop over the same messages
                jitter = random.randrange(0, 100)
                time.sleep(timeout + jitter / bitrate)

                # Send snoop requests to all clients
                # Make sure we send requests with consequtive queue positions
                for n in range(client_count):
                    server.send_snoop_req(n, 1 + 2*n, ident)
                    ident += 1

                client_responses = set()
                

            # Select on one of the clients returning data
            readable, _, exceptions = select(server.connections, [], server.connections, 1500/bitrate)
            conn: socket.socket

            # If we timeout for whatever reason, retry
            if len(readable) == len(exceptions) == 0:
                print(f"Timeout - retrying")
                client_responses = set(range(client_count))
                continue

            for conn in exceptions:
                print(f"Something has gone wrong with client {server.connections.index(conn)}")
                exit()

            for conn in readable:
                try:
                    for packet in server.get_snooped_packet(conn):
                        print(f"Got {packet.request_ident};{packet.packet_ident};{packet.message}")
                        message_reconstructor.all_packets.append(packet)
                        client_responses.add(server.connections.index(conn))
                except ConnectionAbortedError:
                    print(f"Client {server.connections.index(conn)} closed connection")
                    exit()

# Send complete message to server
# Return true if accepted
def send_message(message: str) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)    
    s.connect((SNOOP_SERVER_IP,HTTP_SERVER_PORT))
    
    header = "POST /session HTTP/1.1\r\n"
    host = "Host: " + SNOOP_SERVER_IP + ":8155\r\n"
    contentLength = "Content-Length: " + str(len(message)) + "\r\n\r\n"

    data = header + host + contentLength + message
    s.sendall(str.encode(data))

    rec = s.recv(4096)

    if "200" in rec.decode():
        return True
    elif "205" in rec.decode():
        exit()
    else:
        return False


main()
