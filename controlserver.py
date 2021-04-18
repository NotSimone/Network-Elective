# Control Server for Snooping Clients

import socket
import sys
from queue import Queue
from select import select
from typing import List
import time
from server import Server, SnoopedPacket

SNOOP_SERVER_IP = "149.171.36.192"
SNOOP_SERVER_PORT = 8154
HTTP_SERVER_PORT = 8080

snooped_packets: "Queue[SnoopedPacket]" = Queue()
pkts = {}

with Server() as server:
    # Connect and configure the clients
    client_count = 1 if len(sys.argv) < 2 else int(sys.argv[1])
    server.connect_clients(client_count)
    server.config_clients(ip=SNOOP_SERVER_IP, port=SNOOP_SERVER_PORT)
    
    ident = 30
    start = time.perf_counter()
    
    while True:
        
        server.send_snoop_req(0, 1, ident)
        time.sleep(0.05)
        server.send_snoop_req(1, 2, ident)
        time.sleep(0.05)
        ident += 1
        

        if(time.perf_counter()-start > 5): # 5 seconds have elapsed       
            #print(pkts)
            ttl_no_unique = len(pkts)
            unique_pkts = {}
            eom = -1
            for key, value in pkts.items():
                unique_pkts[value%ttl_no_unique] = key
                if '\x04' in key:
                    eom = value%ttl_no_unique
            
            print(sorted(unique_pkts))
            print("current pkts no: "+str(ttl_no_unique))
            # res = set(pkts.values()) # the unique set of messages
            
            # #print(res)
            # pkt_iden = dict((v,k) for k,v in pkts.items())
            
            
            # idenn = -1
            msg = ''

            # print(len(res))
            # for x in res:
            #     idenn = pkt_iden[x]
            #     if '\x04' in x: 
            #         eom = idenn%len(res)   
            #     unique_pkts[idenn%len(res)] = x
            
            l = list(unique_pkts.keys())
            #print(sorted(l)) #id of messages
            #print(list(range(min(l), max(l)+1)))
            print(unique_pkts)
            if sorted(l) == list(range(0, max(l)+1)): 
                #checking if all messages have been received
                print('snoop completed in (sec): '+str(time.perf_counter()-start))
                print('total no of packets: '+str(ttl_no_unique))
                print(sorted(unique_pkts))
                i = eom+1
                while i < len(l):
                    msg += unique_pkts[i]
                    i+=1

                i = 0
                while i < eom+1:
                    msg += unique_pkts[i]
                    i+=1

                print(msg)

                
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)     
                s.connect(('127.0.0.1',8080))
                
                message = "POST /session HTTP/1.1\r\n"
                Host = "Host: 127.0.0.1:8080\r\n"
                contentLength = "Content-Length: " + str(len(msg)) + "\r\n\r\n"
                contentType = "Content-Type: text/plain\r\n"
        
                data = message + Host + contentLength + msg
                s.sendall(str.encode(data))
                print(s.recv(4096))
            
                print('cant send')
            else:
                print('missing parts of message, current packets no.: '+str(len(l)))
            

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
                    snooped_packets.put(packet)
                    #pkts[packet.packet_ident] = packet.message
                    pkts[packet.message] = packet.packet_ident
            except ConnectionAbortedError:
                print(f"Client {server.connections.index(conn)} closed connection")
                exit()
