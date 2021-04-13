#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>

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

char recvBuf[1024] = "";
char sendBuf[1024] = "";

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
            printf("Error: Select error\n");
            exit(EXIT_FAILURE);
        }

        // Check the control server
        if (FD_ISSET(serverHandle, &fdSetCopy)) {
            int32_t rec = recv(serverHandle, recvBuf, sizeof(recvBuf), 0);
            if (rec > 0) {
                // Forward the snoopRequest onto the snoop server
                SnoopRequest* request = (SnoopRequest*) recvBuf;
                if (sendAllTo(snoopHandle, recvBuf, sizeof(SnoopRequest), &snoopAddr) == 0) {
                    printf("Forwarded snoop request (requestNum: %u, requestIdent: %u)\n", request->requestNum, request->requestIdent);
                } else {
                    printf("Error: Could not forward snoop request (requestNum: %u, requestIdent: %u)\n", request->requestNum, request->requestIdent);
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
            struct sockaddr snoopServer;
            socklen_t len;
            int32_t rec = recvfrom(snoopHandle, recvBuf, sizeof(recvBuf), 0, &snoopServer, &len); 
            if (rec > 0) {
                // Repackage and forward to control server
                SnoopResponse* response = (SnoopResponse*) recvBuf;
                SnoopedPacket packet = { .requestIdent = response->requestIdent, .packetIdent = response->packetIdent};
                // Message length is recv size - two identifiers
                packet.messageLength = rec - 8;
                memcpy(packet.message, response->message, packet.messageLength);
                // New packet is larger because of the messageLength field
                sendAll(serverHandle, (char*) &packet, rec + 4);
                printf("Forwarded snooped packet to server (%d bytes)", packet.messageLength);
                fflush(stdout);
            } else {
                printf("Error: Snoop recv error\n");
                exit(EXIT_FAILURE);
            }

            exit(EXIT_FAILURE);
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
            printf("Error: Unable to get socket\n");
            exit(EXIT_FAILURE);
        }
    #else
        if (serverHandle < 0 || snoopHandle < 0) { 
            printf("Error: Unable to get socket\n");
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
        printf("Error: Unable to connect to server\n");
        exit(EXIT_FAILURE);
    }

    // Handshake with server
    sendAll(serverHandle, CLIENT_HANDSHAKE, strlen(CLIENT_HANDSHAKE));
    uint32_t rec = recv(serverHandle, recvBuf, sizeof(recvBuf), 0);
    recvBuf[rec] = '\0';
    if (strcmp(recvBuf, SERVER_HANDSHAKE) == 0) {
        printf("Connected to server\n");
        fflush(stdout);
    } else {
        printf("Error: Invalid server handshake\n");
        exit(EXIT_FAILURE);
    }    
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
    printf("Snoop server configured to %s:%u\n", ip, port);

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
