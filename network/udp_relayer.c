#define WIN32_LEAN_AND_MEAN
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>

#pragma comment(lib, "Ws2_32.lib")

#define PY_TO_C_PORT 6000      // Port d'écoute pour les messages venant de Python
#define BROADCAST_PORT 6001    // Port pour le broadcast UDP
#define C_TO_PY_PORT 6002      // Port de transfert vers Python locale
#define BUFFER_SIZE 65507

DWORD WINAPI broadcast_sender(LPVOID arg) {
    SOCKET sock_recv = INVALID_SOCKET, sock_broadcast = INVALID_SOCKET;
    struct sockaddr_in addr_recv, addr_broadcast;
    char buffer[BUFFER_SIZE];
    int addr_len = sizeof(addr_recv);

    // Socket pour recevoir depuis Python
    sock_recv = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_recv == INVALID_SOCKET) {
        printf("Erreur de création du socket de réception: %d\n", WSAGetLastError());
        return 1;
    }
    memset(&addr_recv, 0, sizeof(addr_recv));
    addr_recv.sin_family = AF_INET;
    addr_recv.sin_addr.s_addr = INADDR_ANY;
    addr_recv.sin_port = htons(PY_TO_C_PORT);

    if (bind(sock_recv, (struct sockaddr *)&addr_recv, sizeof(addr_recv)) == SOCKET_ERROR) {
        printf("Erreur lors du bind du socket de réception: %d\n", WSAGetLastError());
        closesocket(sock_recv);
        return 1;
    }

    // Socket pour envoyer en broadcast
    sock_broadcast = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_broadcast == INVALID_SOCKET) {
        printf("Erreur de création du socket broadcast: %d\n", WSAGetLastError());
        closesocket(sock_recv);
        return 1;
    }
    int broadcastEnable = 1;
    if (setsockopt(sock_broadcast, SOL_SOCKET, SO_BROADCAST, (char *)&broadcastEnable, sizeof(broadcastEnable)) == SOCKET_ERROR) {
        printf("Erreur lors de l'activation du broadcast: %d\n", WSAGetLastError());
        closesocket(sock_recv);
        closesocket(sock_broadcast);
        return 1;
    }
    memset(&addr_broadcast, 0, sizeof(addr_broadcast));
    addr_broadcast.sin_family = AF_INET;
    addr_broadcast.sin_port = htons(BROADCAST_PORT);
    // Adaptation : utiliser le broadcast correspondant à l'interface Wi-Fi (pour 172.20.10.0/28, broadcast=172.20.10.15)
    addr_broadcast.sin_addr.s_addr = inet_addr("172.20.10.15");

    printf("Thread broadcast_sender actif. Ecoute sur le port %d...\n", PY_TO_C_PORT);
    while (1) {
        int recv_len = recvfrom(sock_recv, buffer, BUFFER_SIZE, 0, (struct sockaddr *)&addr_recv, &addr_len);
        if (recv_len > 0) {
            if (sendto(sock_broadcast, buffer, recv_len, 0, (struct sockaddr *)&addr_broadcast, sizeof(addr_broadcast)) == SOCKET_ERROR) {
                printf("Erreur lors de l'envoi broadcast: %d\n", WSAGetLastError());
            } else {
                printf("Donnees recues de Python et retransmises en broadcast.\n");
            }
        }
    }
    closesocket(sock_recv);
    closesocket(sock_broadcast);
    return 0;
}

DWORD WINAPI forwarder(LPVOID arg) {
    SOCKET sock_broadcast = INVALID_SOCKET, sock_forward = INVALID_SOCKET;
    struct sockaddr_in addr_broadcast, addr_forward, addr_src;
    char buffer[BUFFER_SIZE];
    int addr_len = sizeof(addr_src);

    // Récupérer l'IP locale
    char localHostname[256];
    char localIP[INET_ADDRSTRLEN] = "";
    if (gethostname(localHostname, sizeof(localHostname)) == 0) {
        struct hostent *host = gethostbyname(localHostname);
        if (host && host->h_addr_list[0]) {
            inet_ntop(AF_INET, host->h_addr_list[0], localIP, sizeof(localIP));
        }
    }

    // Socket pour recevoir les broadcasts
    sock_broadcast = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_broadcast == INVALID_SOCKET) {
        printf("Erreur de création du socket broadcast (recep): %d\n", WSAGetLastError());
        return 1;
    }
    int reuse = 1;
    if (setsockopt(sock_broadcast, SOL_SOCKET, SO_REUSEADDR, (char *)&reuse, sizeof(reuse)) == SOCKET_ERROR) {
        printf("Erreur lors de la configuration SO_REUSEADDR: %d\n", WSAGetLastError());
        closesocket(sock_broadcast);
        return 1;
    }
    memset(&addr_broadcast, 0, sizeof(addr_broadcast));
    addr_broadcast.sin_family = AF_INET;
    addr_broadcast.sin_addr.s_addr = INADDR_ANY;
    addr_broadcast.sin_port = htons(BROADCAST_PORT);
    if (bind(sock_broadcast, (struct sockaddr *)&addr_broadcast, sizeof(addr_broadcast)) == SOCKET_ERROR) {
        printf("Erreur lors du bind du socket broadcast (recep): %d\n", WSAGetLastError());
        closesocket(sock_broadcast);
        return 1;
    }

    // Socket pour forwarder vers Python
    sock_forward = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_forward == INVALID_SOCKET) {
        printf("Erreur de création du socket forward: %d\n", WSAGetLastError());
        closesocket(sock_broadcast);
        return 1;
    }
    memset(&addr_forward, 0, sizeof(addr_forward));
    addr_forward.sin_family = AF_INET;
    addr_forward.sin_port = htons(C_TO_PY_PORT);
    addr_forward.sin_addr.s_addr = inet_addr("127.0.0.1");

    printf("Thread forwarder actif. Ecoute des broadcasts sur le port %d...\n", BROADCAST_PORT);
    while (1) {
        int recv_len = recvfrom(sock_broadcast, buffer, BUFFER_SIZE, 0, (struct sockaddr *)&addr_src, &addr_len);
        if (recv_len > 0) {
            // Vérifier si le message provient de la machine locale
            char *src_ip = inet_ntoa(addr_src.sin_addr);
            if (sendto(sock_forward, buffer, recv_len, 0, (struct sockaddr *)&addr_forward, sizeof(addr_forward)) == SOCKET_ERROR) {
                printf("Erreur lors du forwarding vers Python: %d\n", WSAGetLastError());
            } else {
                printf("Message broadcast reçu de %s:%d et transmis à Python.\n",
                       src_ip, ntohs(addr_src.sin_port));
            }
        }
    }
    closesocket(sock_broadcast);
    closesocket(sock_forward);
    return 0;
}

int main() {
    WSADATA wsaData;
    HANDLE hThread1, hThread2;
    DWORD threadId1, threadId2;

    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        printf("WSAStartup échoué.\n");
        return 1;
    }

    hThread1 = CreateThread(NULL, 0, broadcast_sender, NULL, 0, &threadId1);
    if (hThread1 == NULL) {
        printf("Erreur lors de la création du thread broadcast_sender: %d\n", GetLastError());
        WSACleanup();
        return 1;
    }
    hThread2 = CreateThread(NULL, 0, forwarder, NULL, 0, &threadId2);
    if (hThread2 == NULL) {
        printf("Erreur lors de la création du thread forwarder: %d\n", GetLastError());
        TerminateThread(hThread1, 0);
        WSACleanup();
        return 1;
    }

    printf("Relais UDP actif.\n");

    WaitForSingleObject(hThread1, INFINITE);
    WaitForSingleObject(hThread2, INFINITE);
    CloseHandle(hThread1);
    CloseHandle(hThread2);
    
    WSACleanup();
    return 0;
}