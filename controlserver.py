# Control Server for Snooping Clients

import socket
import sys
from select import select
from typing import List, Set
import time
import random
from server import Server, SnoopedPacket

SNOOP_SERVER_IP = "149.171.36.192"
SNOOP_SERVER_PORT = 8154
HTTP_SERVER_PORT = 8155

class MessageReconstructor:
    all_packets: List[SnoopedPacket] = []           # All packets we capture
    invalid_message_length: List[int] = list()      # Message lengths confirmed bad
    start_ident: int                                # Identifier for a starting message
    confirmed_message_length: int = -1
    eof: List[int]

    def __init__(self) -> None:
        self.all_packets = list()
        self.invalid_message_length = list()
        self.start_ident = -1
        self.confirmed_message_length = -1

    # Attempt to reconstruct the whole message
    # Sends it to the server if it finds one
    # Return true if successful
    def reconstruct_message(self) -> bool:
        if self.confirmed_message_length == -1:
            # Get list of packet ident where the message had an EOF
            self.eof: List[int] = [x.packet_ident for x in self.all_packets if x.message[-1] == "\x04"]

            if len(self.eof) < 3:
                return False

            # Get list of differences in length and determine possible message lengths
            eof_distance = [self.eof[x+1] - self.eof[x] for x in range(len(self.eof) - 1)]
            # Get the factors for each eof distance
            eof_distance_factors = list(map(lambda x: factors(x), eof_distance))
            # Get the common factors for the eof distances
            common_eof_distance_factors = list(set.intersection(*eof_distance_factors))
            # Rule out the known bad lengths and we should be left with possible message lengths
            possible_message_len = [x for x in common_eof_distance_factors if x not in self.invalid_message_length]

            print(f"Possible message len: {possible_message_len}")

            # Check if we have only a single message length left
            if len(possible_message_len) == 1:
                self.confirmed_message_length = possible_message_len[0]
            elif len(possible_message_len) == 0:
                print(f"Error: 0 length message len - resetting")
                self = MessageReconstructor()
        else:
            possible_message_len = [self.confirmed_message_length]

        # Check each possible message length
        for message_len in possible_message_len:
            message = self.validate_message_len(message_len)
            if (message):
                # Send the whole message to the server
                return send_message(message)
        return False
        
    # Attempt to construct a message with length
    # Returns empty string on fail
    def validate_message_len(self, length: int) -> str:
        messages: List[str] = [""] * length
        # Check validity using all the packets we found so far
        for x in self.all_packets:
            index = (x.packet_ident - self.eof[0] - 1) % length
            if messages[index] == "":
                messages[index] = x.message
            else:
                # On mismatch, mark length as invalid and return
                if messages[index] != x.message:
                    self.invalid_message_length.append(length)
                    return ""

        # Check if we found a whole message
        missing_messages = [x for x in messages if x == ""]
        if len(missing_messages) == 0:
            complete_message = "".join(messages)
            print(f"Complete message: {complete_message}")
            return complete_message

        if self.confirmed_message_length != -1:
            print(f"{len(missing_messages)} missing messages")

        return ""

        

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
                if (message_reconstructor.reconstruct_message()):
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

# Get factors of a number
# https://stackoverflow.com/questions/6800193/what-is-the-most-efficient-way-of-finding-all-the-factors-of-a-number-in-python
def factors(n) -> Set[int]:
    return set(x for tup in ([i, n//i] 
                for i in range(1, int(n**0.5)+1) if n % i == 0) for x in tup)

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
