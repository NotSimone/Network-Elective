// Utility functions for safer sending and receiving
// https://beej.us/guide/bgnet/html/

#include "network.h"

// Safer TCP send function call
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

// Safer UDP send function call
int sendAllTo(int s, char *buf, int len, struct sockaddr_in* sockaddr) {
    int total = 0;
    int bytesleft = len;
    int n;

    while(total < len) {
        n = sendto(s, buf+total, bytesleft, 0, (struct sockaddr*) sockaddr, sizeof(struct sockaddr_in));
        if (n == -1) { break; }
        total += n;
        bytesleft -= n;
    }

    len = total;

    return n == -1 ? -1 : 0;
}

