#ifndef _network_lib

#include <stdint.h>

#ifdef _WIN32
	#include <WinSock2.h>
#else
    #include <sys/socket.h>
    #include <sys/types.h>
    #include <arpa/inet.h>
    #include <unistd.h>
#endif

#define CLIENT_HANDSHAKE "snooping-client-handshake"
#define SERVER_HANDSHAKE "snooping-server-handshake"

int sendAll(int s, char *buf, int len);
int sendAllTo(int s, char *buf, int len, struct sockaddr_in* sockaddr);
void checkRecv(int32_t recv);

typedef struct _SnoopResponse {
    uint32_t requestIdent;
    uint32_t packetIdent;
    char message[1016];
} SnoopResponse;

typedef struct _SnoopedPacket {
    uint32_t requestIdent;
    uint32_t packetIdent;
    uint32_t messageLength;
    char message[1016];
} SnoopedPacket;

typedef struct _SnoopRequest {
    uint32_t requestNum;
    uint32_t requestIdent;
} SnoopRequest;

typedef struct _Config {
    uint32_t port;
    char ip[16];
} Config;

#endif
