#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <errno.h>

#ifdef _WIN32
	#include <WinSock2.h>
    #include <WS2tcpip.h>
#else
    #include <sys/socket.h>
    #include <sys/types.h>
    #include <arpa/inet.h>
    #include <unistd.h>
#endif

#include "network.h"

void connectServer();
struct sockaddr_in getConfig();
void cleanup();

uint64_t serverIP;

int32_t serverHandle = -1;
int32_t snoopHandle = -1;

char recvBuf[1024];
char dataBuf[1024];

uint32_t prevPacketIdent = 0;

int main(int argc, char * argv[]) {
    serverIP = argc > 1 ? inet_addr(argv[1]) : inet_addr("127.0.0.1");

    connectServer();
    struct sockaddr_in snoopAddr = getConfig();

    fd_set fdSet;
    FD_ZERO(&fdSet);
    int32_t maxFd = snoopHandle > serverHandle ? snoopHandle : serverHandle;
    FD_SET(snoopHandle, &fdSet);
    FD_SET(serverHandle, &fdSet);

    while (1) {
        fd_set fdSetCopy = fdSet;
        // Block until we get a request
        uint32_t num = select(maxFd + 1, &fdSetCopy, NULL, NULL, NULL);
        if (num < 0) {
            printf("Error: Select error [%s]\n", strerror(errno));
            exit(EXIT_FAILURE);
        }

        // Check the control server
        if (FD_ISSET(serverHandle, &fdSetCopy)) {
            int32_t rec = recv(serverHandle, recvBuf, sizeof(recvBuf), 0);
            if (rec > 0) {
                // Continue until we get a whole snoop request
                int32_t rec_bytes = rec;
                memcpy(dataBuf, recvBuf, rec);
                while (rec_bytes < 8) {
                    rec += recv(serverHandle, recvBuf, sizeof(recvBuf), 0);
                    memcpy(&dataBuf[rec_bytes], recvBuf, rec);
                    rec_bytes += rec;
                }

                // Create the snoop request
                uint32_t requestNum = ((SnoopRequest*) dataBuf)->requestNum;
                uint32_t requestIdent = ((SnoopRequest*) dataBuf)->requestIdent;
                SnoopRequest request;
                request.requestNum = htonl(requestNum);
                request.requestIdent = htonl(requestIdent);

                // Send the snoop request
                if (sendAllTo(snoopHandle, (char*)&request, sizeof(SnoopRequest), &snoopAddr) == 0) {
                    printf("Sent snoop request (requestNum: %u, requestIdent: %u)\n", requestNum, requestIdent);
                } else {
                    printf("Error: Could not forward snoop request (requestNum: %u, requestIdent: %u) [%s]\n", requestNum, requestIdent, strerror(errno));
                    exit(EXIT_FAILURE);
                }
            } else if (rec == 0 || rec == 1) {
                printf("Error: Server closed connection\n");
                exit(EXIT_FAILURE);
            } else {
                printf("Error: Server recv error\n");
                exit(EXIT_FAILURE);
            }
        }

        // Check the snoop server
        if (FD_ISSET(snoopHandle, &fdSetCopy)) {
            int32_t rec = recvfrom(snoopHandle, recvBuf, sizeof(recvBuf), 0, NULL, NULL); 
            if (rec > 0) {
                // Repackage and forward to control server
                SnoopResponse* response = (SnoopResponse*) recvBuf;
                SnoopedPacket packet = { .requestIdent = htonl(response->requestIdent), .packetIdent = htonl(response->packetIdent) };

                // Taubman's server has a bug where it will sometimes send duplicates
                // Check packetIdent to discard these
                if (packet.packetIdent == prevPacketIdent) {
                    continue;
                }

                // Message length is recv size - two identifiers
                packet.messageLength = rec - 8;
                memcpy(packet.message, response->message, packet.messageLength);
                
                // New packet is larger because of the messageLength field
                sendAll(serverHandle, (char*) &packet, rec + 4);
                printf("Forwarded snooped packet to server (%d bytes)\n", packet.messageLength);
                fflush(stdout);
            } else {
                printf("Error: Snoop recv error [%s]\n", strerror(errno));
                exit(EXIT_FAILURE);
            }
        }
    }
}

// Initialise and connect to server
void connectServer() {
    // Windows requires additional initialisation
    #ifdef _WIN32
        WSADATA wsa_data;
        if (WSAStartup(MAKEWORD(2,2), &wsa_data) != 0) {
            printf("Error: Could not start winsock (%d)\n", WSAGetLastError());
            exit(EXIT_FAILURE);
        }
    #endif

    // TCP control server socket
    serverHandle = socket(AF_INET, SOCK_STREAM, IPPROTO_IP);
    // UDP snoop server socket
    snoopHandle = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
    // Not being able to get socket numbers is handled differently in windows
    #ifdef _WIN32
        if (serverHandle == INVALID_SOCKET || snoopHandle == INVALID_SOCKET) { 
            printf("Error: Unable to get socket [%s]\n", strerror(errno));
            exit(EXIT_FAILURE);
        }
    #else
        if (serverHandle < 0 || snoopHandle < 0) { 
            printf("Error: Unable to get socket [%s]\n", strerror(errno));
            exit(EXIT_FAILURE);
        }
    #endif
    
    // Register cleanup
    atexit(cleanup);
    signal(SIGINT, &exit);

    // Configure and bind the socket
    struct sockaddr_in serverSocketInfo = {0};
    serverSocketInfo.sin_family = AF_INET;
    serverSocketInfo.sin_port = htons(SERVER_PORT);
    serverSocketInfo.sin_addr.s_addr = serverIP;

    printf("Connecting to server %s on port %d\n", inet_ntoa(serverSocketInfo.sin_addr), SERVER_PORT);
    fflush(stdout);

    // Attempt to connect to the server
    if (connect(serverHandle, (struct sockaddr*) &serverSocketInfo, sizeof(serverSocketInfo)) != 0) {
        printf("Error: Unable to connect to server [%s]\n", strerror(errno));
        exit(EXIT_FAILURE);
    }

    // Handshake with server
    uint32_t rec = recv(serverHandle, recvBuf, sizeof(recvBuf), 0);

    if (rec == 0) {
        printf("Server connection aborted\n");
        exit(EXIT_FAILURE);
    } else if (strcmp(recvBuf, SERVER_HANDSHAKE) == 0) {
        printf("Connected to server\n");
        fflush(stdout);
    } else {
        printf("Error: Invalid server handshake [%s]\n", strerror(errno));
        exit(EXIT_FAILURE);
    }

    sendAll(serverHandle, CLIENT_HANDSHAKE, strlen(CLIENT_HANDSHAKE));
}

// Get config of snoop server we connect to from control server
struct sockaddr_in getConfig() {
    printf("Waiting for snoop server IP\n");
    uint32_t rec = recv(serverHandle, recvBuf, sizeof(recvBuf), 0);

    Config* config = (Config *) recvBuf;
    char ip[16];
    memcpy(ip, config->ip, rec-4);
    ip[rec-4] = '\0';
    uint32_t port = config->port;

    struct sockaddr_in snoopAddr;
    snoopAddr.sin_family = AF_INET;
    snoopAddr.sin_port = htons(port);
    snoopAddr.sin_addr.s_addr = inet_addr(ip);

    if (connect(snoopHandle, (struct sockaddr*)&snoopAddr, sizeof(snoopAddr)) != 0) {
        printf("Error: Could not connect to snoop server [%s]\n", strerror(errno));
        exit(EXIT_FAILURE);
    }

    printf("Snoop server connected to %s:%u\n", ip, port);

    return snoopAddr;
}

// Close ports and clean up before exiting
void cleanup() {
    printf("Closing handles and exiting\n");
    #ifdef _WIN32
        closesocket(serverHandle);
        closesocket(snoopHandle);
        WSACleanup();
    #else
        close(serverHandle);
        close(snoopHandle);
    #endif
}
