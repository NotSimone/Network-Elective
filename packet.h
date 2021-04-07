#include <stdint.h>

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
 