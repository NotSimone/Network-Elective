# Control Server for Snooping Clients

import socket
import sys
from select import select
from typing import List
import time
import random
from server import Server, SnoopedPacket

SNOOP_SERVER_IP = "149.171.36.192"
SNOOP_SERVER_PORT = 8154
HTTP_SERVER_PORT = 8155

all_packets: List[SnoopedPacket] = []           # All packets we capture
invalid_message_length: List[int] = list()      # Message lengths confirmed bad
start_ident: int                                # Identifier for starting message

def main() -> None:
    with Server() as server:
        # Connect and configure the clients
        client_count = 1 if len(sys.argv) < 2 else int(sys.argv[1])
        bitrate = 1000 if len(sys.argv) < 3 else int(sys.argv[2])
        # Detection timeout
        timeout = 50 / bitrate

        server.connect_clients(client_count)
        server.config_clients(ip=SNOOP_SERVER_IP, port=SNOOP_SERVER_PORT)
        
        ident = 30
        
        client_responses = client_count
        
        while True:
            if client_responses == client_count:
                if (reconstruct_message()):
                    print("Message accepted by server")
                    exit()

                # Add jitter into the timeout to make sure we dont just loop over the same messages
                jitter = random.randrange(0, 100)
                time.sleep(timeout + jitter / bitrate)

                # Send snoop requests to all clients
                # Make sure we send requests with consequtive queue positions
                for n in range(client_count):
                    server.send_snoop_req(n, n+1, ident)
                    ident += 1

                client_responses = 0
                

            # Select on one of the clients returning data
            readable, _, exceptions = select(server.connections, [], server.connections)
            conn: socket.socket

            for conn in exceptions:
                print(f"Something has gone wrong with client {server.connections.index(conn)}")
                exit()

            for conn in readable:
                try:
                    for packet in server.get_snooped_packet(conn):
                        print(f"Got {packet.request_ident};{packet.packet_ident};{packet.message}")
                        all_packets.append(packet)
                        client_responses += 1
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

    if "205" in rec.decode():
        return True
    else:
        return False

# Get factors of a number
# https://stackoverflow.com/questions/6800193/what-is-the-most-efficient-way-of-finding-all-the-factors-of-a-number-in-python
def factors(n) -> List[int]:
    return list(x for tup in ([i, n//i] 
                for i in range(1, int(n**0.5)+1) if n % i == 0) for x in tup)

# Attempt to reconstruct the whole message
# Sends it to the server if it finds one
# Return true if successful
def reconstruct_message() -> bool:
    # Get list of packet ident where the message had an EOF
    eof: List[int] = [x.packet_ident for x in all_packets if x.message[-1] == "\x04"]

    if len(eof) < 3:
        return False

    # Determine an identifier for the beginning of the message
    global start_ident
    start_ident = eof[0] + 1

    # Get list of differences in length and determine possible message lengths
    eof_diff = [eof[x+1] - eof[x] for x in range(len(eof) - 1)]
    possible_message_len = [x for x in factors(min(eof_diff)) if x not in invalid_message_length]

    # Check each possible message length
    for message_len in possible_message_len:
        message = validate_message_len(message_len)
        if (message):
            # Send the whole message to the server
            return send_message(message)
    
    return False
    
# Attempt to construct a message with length
# Returns empty string on fail
def validate_message_len(length: int) -> str:
    messages: List[str] = [""] * length
    # Check validity using all the packets we found so far
    for x in all_packets:
        index = (x.packet_ident - start_ident) % length
        if messages[index] == "":
            messages[index] = x.message
        else:
            # On mismatch, mark length as invalid and return
            if messages[index] != x.message:
                invalid_message_length.append(length)
                return ""

    # Check if we found a whole message
    missing_messages = [x for x in messages if x == ""]
    if len(missing_messages) == 0:
        complete_message = "".join(messages)
        print(f"Complete message: {complete_message}")
        return complete_message

    return ""

main()
