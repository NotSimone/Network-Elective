// Utility functions for safer sending and receiving
// https://beej.us/guide/bgnet/html/

#include "network.h"

#ifdef _WIN32
    #include <WinSock2.h>
#else
    #include <sys/types.h>
    #include <sys/socket.h>
#endif

int sendAll(int s, char *buf, int len) {
    int total = 0;
    int bytesleft = len;
    int n;

    while(total < len) {
        n = send(s, buf+total, bytesleft, 0);
        if (n == -1) { break; }
        total += n;
        bytesleft -= n;
    }

    len = total;

    return n == -1 ? -1 : 0;
}
