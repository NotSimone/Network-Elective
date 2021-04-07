#include <stdint.h>

typedef struct _snoopResponse {
    uint32_t request_ident;
    uint32_t packet_ident;
    char * message;
} snoopResponse;
 