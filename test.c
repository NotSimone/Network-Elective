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

typedef struct _SnoopRequest {
    uint32_t requestNum;
    uint32_t requestIdent;
} SnoopRequest;

int main(int argc, char * argv[]) {
    #ifdef _WIN32
        WSADATA wsa_data;
        if (WSAStartup(MAKEWORD(2,2), &wsa_data) != 0) {
            printf("Error: Could not start winsock (%d)\n", WSAGetLastError());
            exit(EXIT_FAILURE);
        }
    #endif

    // Configure and bind the socket
    struct sockaddr_in snoopAddr = {0};
    snoopAddr.sin_family = AF_INET;
    snoopAddr.sin_port = htons(8154);
    snoopAddr.sin_addr.s_addr = inet_addr("127.0.0.1");

    
    uint32_t snoopHandle = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);

    SnoopRequest request;
    request.requestIdent = htonl(123);
    request.requestNum = htonl(2);

    int32_t count = sendto(snoopHandle, (char*)&request, sizeof(SnoopRequest), 0, (struct sockaddr*)&snoopAddr, sizeof(struct sockaddr_in));
    printf("%u\n", count);


    #ifdef _WIN32
        WSACleanup();
    #endif

}
