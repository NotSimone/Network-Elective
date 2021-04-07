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

#define CLIENT_HANDSHAKE "snooping-client-req"
#define SERVER_HANDSHAKE "snooping-server-ack"

void init();
void connectClients(int32_t* handles);
void cleanup();

int32_t clientPort = 7209;

int32_t serverSocketHandle = -1;
int32_t* clientConnHandles = NULL;

int32_t currentClients = 0;
int32_t totalClients = 1;

char recvBuf[1024] = "";

int main(int argc, char * argv[]) {
    // Initialise socket
    init();

    if (argc > 1) totalClients = atoi(argv[1]);

    int32_t* fd = calloc(totalClients, sizeof(int32_t));
    connectClients(fd);

    // Initialise select
    fd_set serverFdSet;
    FD_ZERO(&serverFdSet);
    int32_t maxFd = 0;
    for (int32_t i = 0; i < totalClients; i++) {
        if (fd[i] > maxFd) maxFd = fd[i];
        FD_SET(fd[i], &serverFdSet);
    }
    

    /*
    Under Linux, select() may report a socket file descriptor as "ready for reading", while nevertheless a subsequent read blocks. This could for example happen when data has arrived but upon examination has wrong checksum and is discarded. There may be other circumstances in which a file descriptor is spuriously reported as ready. Thus it may be safer to use O_NONBLOCK on sockets that should not block.

    Just leave it for now unless its a problem
    */

    // Main loop
    while (1) {
        fd_set copyFdSet = serverFdSet;
        // Block until a client sends to us
        uint32_t num = select(maxFd + 1, &copyFdSet, NULL, NULL, NULL);
        if (num < 0) {
            printf("Error: Select timeout\n");
            exit(EXIT_FAILURE);
        }

        // Check each client in turn until we find the ones that sent
        for (uint32_t i = 0; i < totalClients; i++) {
            int32_t clientHandle = clientConnHandles[i];
            if (FD_ISSET(clientHandle, &copyFdSet)) {
                // Receive from the client
                // TODO: Actually do something here
                // right now, all it does is echo back messages
                int32_t rec = recv(clientHandle, (char *)recvBuf, sizeof(recvBuf), 0);
                if (rec > 0) {
                    sendAll(clientHandle, recvBuf, strlen(recvBuf) + 1);
                    printf("%d: %s\n", i, recvBuf);
                    fflush(stdout);
                } else if (rec == 0 || rec == -1) {
                    // Client closed connection
                    printf("Error: Client %d closed connection\n", i);
                    exit(EXIT_FAILURE);
                } else {
                    printf("Error: Failed to recv\n");
                    exit(EXIT_FAILURE);
                }
            }
        }
    }
}

// Sets up the socket required to listen for client connections
void init() {
    // Windows requires additional initialisation
    #ifdef _WIN32
        WSADATA wsa_data;
        if (WSAStartup(MAKEWORD(2, 0), &wsa_data) != 0) {
            printf("Error: Could not start winsock (%d)\n", WSAGetLastError());
            exit(EXIT_FAILURE);
        }
    #endif

    // Create socket
    serverSocketHandle = socket(AF_INET, SOCK_STREAM, IPPROTO_IP);
    // Not being able to get socket numbers is handled differently in windows
    #ifdef _WIN32
        if (serverSocketHandle == INVALID_SOCKET) { 
            printf("Error: Unable to get socket\n");
            exit(EXIT_FAILURE);
        }
    #else
        if (serverSocketHandle < 0) { 
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
    serverSocketInfo.sin_port = htons(clientPort);
    serverSocketInfo.sin_addr.s_addr = htonl(INADDR_ANY);

    // Bind socket
    #ifdef _WIN32
        if (bind(serverSocketHandle, (struct sockaddr*) &serverSocketInfo, sizeof(serverSocketInfo)) == INVALID_SOCKET) { 
            printf("Error: Unable to bind socket\n");
            exit(EXIT_FAILURE);
        }
    #else
        if (bind(serverSocketHandle, (struct sockaddr*) &serverSocketInfo, sizeof(serverSocketInfo)) < 0) { 
            printf("Error: Unable to bind socket\n");
            exit(EXIT_FAILURE);
        }
    #endif
}

// Connect the req number of clients and fill the array with the connection handles
void connectClients(int32_t* handles) {
    printf("Listening for %d clients on port %d\n", totalClients, clientPort);
    fflush(stdout);

    // Listen and get handles to client connections
    if (listen(serverSocketHandle, 10) != 0) {
        printf("Error: Unable to listen on socket\n");
        exit(EXIT_FAILURE);
    }

    // Setup client connection details
    struct sockaddr_in* clientSocketInfo = calloc(totalClients, sizeof(struct sockaddr_in));
    clientConnHandles = calloc(totalClients, sizeof(int32_t));

    // Create connections to the clients
    for (currentClients = 0; currentClients < totalClients; currentClients++) {
        struct sockaddr_in currClientSocketInfo;
        socklen_t len = sizeof(currClientSocketInfo);

        // Block until we get an incoming connection
        int32_t currHandle = accept(serverSocketHandle, (struct sockaddr*) &currClientSocketInfo, &len);

        // Handshake to confirm we got a client
        recv(currHandle, recvBuf, sizeof(recvBuf), 0);
        if (strcmp(recvBuf, CLIENT_HANDSHAKE) != 0) {
            currentClients--;
            continue;
        }

        sendAll(currHandle, SERVER_HANDSHAKE, sizeof(SERVER_HANDSHAKE) + 1);
        clientConnHandles[currentClients] = currHandle;

        // Store connection handle and details
        clientSocketInfo[currentClients] = currClientSocketInfo;
        handles[currentClients] = currHandle;
        #ifdef _WIN32
            if (currHandle == INVALID_SOCKET) {
                printf("Error: Invalid client socket\n");
                exit(EXIT_FAILURE);
            }
        #else
            if (currHandle < 0) {
                printf("Error: Invalid client socket\n");
                exit(EXIT_FAILURE);
            }
        #endif

        printf("Connected client %d from %s\n", currentClients, inet_ntoa(currClientSocketInfo.sin_addr));
        fflush(stdout);
    }

    printf("All clients connected.\n");
}

// Pre exit
void cleanup() {
    printf("Closing handles and exiting\n");
    #ifdef _WIN32
        closesocket(serverSocketHandle);
        for (int32_t curr = 0; curr < currentClients; curr++) {
            closesocket(clientConnHandles[curr]);
        }
        WSACleanup();
    #else
        close(serverSocketHandle);
        for (int32_t curr = 0; curr < currentClients; curr++) {
            close(clientConnHandles[curr]);
        }
    #endif
}
