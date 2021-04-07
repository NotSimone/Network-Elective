#ifndef _network_lib

#include <stdint.h>

int sendAll(int s, char *buf, int len);

typedef struct _snoopResponse {
    uint32_t requestIdent;
    uint32_t packetIdent;
    char* message;
} snoopResponse;

typedef struct _snoopedPacket {
    uint32_t packetIdent;
    uint32_t messageLength;
    char* message;
} snoopedPacket;
 

#endif