#define WIN32_LEAN_AND_MEAN
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>

#pragma comment(lib, "Ws2_32.lib")

#define PY_TO_C_PORT 6000
#define BROADCAST_PORT 6001
#define C_TO_PY_PORT 6002
#define BUFFER_SIZE 65507

int main() {
    WSADATA wsaData;
    SOCKET sock_recv, sock_broadcast, sock_forward;
    struct sockaddr_in addr_recv, addr_broadcast_send, addr_broadcast_recv, addr_forward, addr_src;
    char buffer[BUFFER_SIZE];
    int addr_len = sizeof(addr_src);
    fd_set readfds;
    
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        printf("WSAStartup échoué.\n");
        return 1;
    }

    // Socket pour recevoir depuis Python
    sock_recv = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_recv == INVALID_SOCKET) {
        printf("Erreur de création du socket de réception: %d\n", WSAGetLastError());
        return 1;
    }

    int reuse = 1;
    setsockopt(sock_recv, SOL_SOCKET, SO_REUSEADDR, (char*)&reuse, sizeof(reuse));

    memset(&addr_recv, 0, sizeof(addr_recv));
    addr_recv.sin_family = AF_INET;
    addr_recv.sin_addr.s_addr = INADDR_ANY;
    addr_recv.sin_port = htons(PY_TO_C_PORT);

    if (bind(sock_recv, (struct sockaddr*)&addr_recv, sizeof(addr_recv)) == SOCKET_ERROR) {
        printf("Erreur lors du bind du socket de réception: %d\n", WSAGetLastError());
        closesocket(sock_recv);
        WSACleanup();
        return 1;
    }

    // Socket pour envoyer en broadcast
    sock_broadcast = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_broadcast == INVALID_SOCKET) {
        printf("Erreur de création du socket broadcast: %d\n", WSAGetLastError());
        closesocket(sock_recv);
        WSACleanup();
        return 1;
    }

    int broadcastEnable = 1;
    setsockopt(sock_broadcast, SOL_SOCKET, SO_BROADCAST, (char*)&broadcastEnable, sizeof(broadcastEnable));

    memset(&addr_broadcast_send, 0, sizeof(addr_broadcast_send));
    addr_broadcast_send.sin_family = AF_INET;
    addr_broadcast_send.sin_port = htons(BROADCAST_PORT);
    addr_broadcast_send.sin_addr.s_addr = INADDR_BROADCAST;

    // Socket pour recevoir les broadcasts
    sock_forward = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_forward == INVALID_SOCKET) {
        printf("Erreur de création du socket forward: %d\n", WSAGetLastError());
        closesocket(sock_recv);
        closesocket(sock_broadcast);
        WSACleanup();
        return 1;
    }

    setsockopt(sock_forward, SOL_SOCKET, SO_REUSEADDR, (char*)&reuse, sizeof(reuse));
    setsockopt(sock_forward, SOL_SOCKET, SO_BROADCAST, (char*)&reuse, sizeof(reuse));

    memset(&addr_broadcast_recv, 0, sizeof(addr_broadcast_recv));
    addr_broadcast_recv.sin_family = AF_INET;
    addr_broadcast_recv.sin_addr.s_addr = INADDR_ANY;
    addr_broadcast_recv.sin_port = htons(BROADCAST_PORT);

    if (bind(sock_forward, (struct sockaddr*)&addr_broadcast_recv, sizeof(addr_broadcast_recv)) == SOCKET_ERROR) {
        printf("Erreur lors du bind du socket broadcast: %d\n", WSAGetLastError());
        closesocket(sock_recv);
        closesocket(sock_broadcast);
        closesocket(sock_forward);
        WSACleanup();
        return 1;
    }

    // Configuration de l'adresse pour forward vers Python
    memset(&addr_forward, 0, sizeof(addr_forward));
    addr_forward.sin_family = AF_INET;
    addr_forward.sin_port = htons(C_TO_PY_PORT);
    addr_forward.sin_addr.s_addr = inet_addr("127.0.0.1");

    printf("Relais UDP actif.\n");

    FD_ZERO(&readfds);
    FD_SET(sock_recv, &readfds);
    FD_SET(sock_forward, &readfds);

    while (1) {
        fd_set temp_fds = readfds;
        int activity = select(0, &temp_fds, NULL, NULL, NULL);

        if (activity == SOCKET_ERROR) {
            printf("Erreur select: %d\n", WSAGetLastError());
            break;
        }

        if (FD_ISSET(sock_recv, &temp_fds)) {
            int recv_len = recvfrom(sock_recv, buffer, BUFFER_SIZE, 0, (struct sockaddr*)&addr_src, &addr_len);
            if (recv_len > 0) {
                sendto(sock_broadcast, buffer, recv_len, 0, (struct sockaddr*)&addr_broadcast_send, sizeof(addr_broadcast_send));
            }
        }

        if (FD_ISSET(sock_forward, &temp_fds)) {
            int recv_len = recvfrom(sock_forward, buffer, BUFFER_SIZE, 0, (struct sockaddr*)&addr_src, &addr_len);
            if (recv_len > 0) {
                sendto(sock_forward, buffer, recv_len, 0, (struct sockaddr*)&addr_forward, sizeof(addr_forward));
            }
        }
    }

    closesocket(sock_recv);
    closesocket(sock_broadcast);
    closesocket(sock_forward);
    WSACleanup();
    return 0;
}