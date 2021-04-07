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

#include "packet.h"

#define CLIENT_HANDSHAKE "snooping-client-req"
#define SERVER_HANDSHAKE "snooping-server-ack"

void connectServer();
void cleanup();

uint64_t serverIP;
uint32_t serverPort = 7209;

int32_t serverHandle = -1;

char recvBuf[1025] = "";
char sendBuf[1024] = "";

int main(int argc, char * argv[]) {
    serverIP = argc > 1 ? inet_addr(argv[1]) : inet_addr("127.0.0.1");
    connectServer();

    while (1) {
        // Get keyboard input
        sendBuf[0] = '\0';
        scanf("%s", sendBuf);

        // Send and receive
        int32_t sent = send(serverHandle, sendBuf, strlen(sendBuf) + 1, 0);
        printf("Send: %s (%d)\n", sendBuf, sent);
        sendBuf[0] = '\0';
        int32_t rec = recv(serverHandle, sendBuf, sizeof(sendBuf), 0);
        if (rec > 0) {
            printf("Echo: %s\n", sendBuf);
        } else if (rec == 0) {
            printf("Error: Server closed connection\n");
            exit(EXIT_FAILURE);
        } else {
            printf("Error: recv error\n");
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


    serverHandle = socket(AF_INET, SOCK_STREAM, IPPROTO_IP);
    // Not being able to get socket numbers is handled differently in windows
    #ifdef _WIN32
        if (serverHandle == INVALID_SOCKET) { 
            printf("Error: Unable to get socket\n");
            exit(EXIT_FAILURE);
        }
    #else
        if (serverHandle < 0) { 
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
    serverSocketInfo.sin_port = htons(serverPort);
    serverSocketInfo.sin_addr.s_addr = serverIP;

    printf("Connecting to server %s on port %d\n", inet_ntoa(serverSocketInfo.sin_addr), serverPort);
    fflush(stdout);

    // Attempt to connect to the server
    if (connect(serverHandle, (struct sockaddr*) &serverSocketInfo, sizeof(serverSocketInfo)) != 0) {
        printf("Error: Unable to connect to server\n");
        exit(EXIT_FAILURE);
    }

    // Handshake with server
    send(serverHandle, CLIENT_HANDSHAKE, strlen(CLIENT_HANDSHAKE) + 1, 0);
    recv(serverHandle, recvBuf, sizeof(recvBuf), 0);
    if (strcmp(recvBuf, SERVER_HANDSHAKE) == 0) {
        printf("Connected to server\n");
        fflush(stdout);
    } else {
        printf("Error: Invalid server handshake\n");
        exit(EXIT_FAILURE);
    }    
}

void cleanup() {
    printf("Closing handles and exiting\n");
    #ifdef _WIN32
        closesocket(serverHandle);
        WSACleanup();
    #else
        close(serverHandle);
    #endif
}
