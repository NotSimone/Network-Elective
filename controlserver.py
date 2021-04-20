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

all_packets: List[SnoopedPacket] = []
invalid_message_length: List[int] = list()

# Send complete message to server
# Return true if accepted
def send_message(msg: str) -> bool:
    ################################
    #POST
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)    
    s.connect((SNOOP_SERVER_IP,HTTP_SERVER_PORT))
    
    header = "POST /session HTTP/1.1\r\n"
    host = "Host: " + SNOOP_SERVER_IP + ":8155\r\n"
    contentLength = "Content-Length: " + str(len(msg)) + "\r\n\r\n"
    contentType = "Content-Type: text/plain\r\n"

    data = header + host + contentLength + msg
    s.sendall(str.encode(data))
    print(s.recv(4096))

    # TODO
    return True

# Get factors of a number
# https://stackoverflow.com/questions/6800193/what-is-the-most-efficient-way-of-finding-all-the-factors-of-a-number-in-python
def factors(n):
    return set(x for tup in ([i, n//i] 
                for i in range(1, int(n**0.5)+1) if n % i == 0) for x in tup)

# Attempt to reconstruct the whole message and send it off
# Return true if successful
def reconstruct_message() -> bool:
    # Get list of packet ident where the message had an EOF
    eof: List[int] = [x.packet_ident for x in all_packets if x.message[-1] == "\x04"]

    if len(eof) < 3:
        return False

    # Get list of differences in length and determine possible message lengths
    eof_diff = [eof[x+1] - eof[x] for x in range(len(eof) - 1)]
    possible_message_len = factors(min(eof_diff))

    # If there is only one possible message length
    if len(possible_message_len) == 1:
        message_length = possible_message_len[0]
    if len(possible_message_len) == 2:
        message_length = possible_message_len[1]

    # Check each possible message length
    for x in possible_message_len:
        message = validate_message_len(x)
        if (message):
            send_message(message)
            return True
    
    return False
    
# Attempt to construct a message with length
# Returns empty string on fail
def validate_message_len(length: int) -> str:
    # If message length is bad, return early
    if length in invalid_message_length:
        return ""

    messages = [None] * length
    start_ident = all_packets[0].packet_ident
    # Check validity using all the packets we found so far
    for x in all_packets:
        index = (x.packet_ident - start_ident + 1) % length
        if messages[index] == None:
            messages[index] = x.message
        else:
            # On mismatch, mark length as invalid and return
            if messages[index] != x.message:
                invalid_message_length.append(length)
                return ""

    # Check if we found a whole message
    missing_messages = [x for x in messages if x == None]
    if len(missing_messages) == 0:
        complete_message = "".join(messages)
        print(complete_message)
        return complete_message

    return ""

with Server() as server:
    # Connect and configure the clients
    client_count = 1 if len(sys.argv) < 2 else int(sys.argv[1])
    bitrate = 1000 if len(sys.argv) < 3 else int(sys.argv[2])
    # Detection timeout
    timeout = 50 / bitrate

    server.connect_clients(client_count)
    server.config_clients(ip=SNOOP_SERVER_IP, port=SNOOP_SERVER_PORT)
    
    ident = 30
    start = time.perf_counter()
    
    client_responses = client_count
    
    while True:
        if client_responses == client_count:
            if (reconstruct_message()):
                exit

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
