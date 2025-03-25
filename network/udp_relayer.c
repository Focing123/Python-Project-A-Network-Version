#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <winsock2.h>
#include <ws2tcpip.h>

#pragma comment(lib, "ws2_32.lib")  // Linker automatique avec Winsock

#define PORT_MANAGER 1234  // Port pour écouter le Network Manager
#define BUFFER_SIZE 65535

int main() {
    WSADATA wsa;
    SOCKET sock_manager;
    struct sockaddr_in server_addr, sender_addr;
    char buffer[BUFFER_SIZE];
    int addr_len = sizeof(sender_addr);

    // Initialisation de Winsock
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        printf("Erreur WSAStartup : %d\n", WSAGetLastError());
        return 1;
    }

    // Création de la socket UDP
    if ((sock_manager = socket(AF_INET, SOCK_DGRAM, 0)) == INVALID_SOCKET) {
        printf("Erreur lors de la création de la socket : %d\n", WSAGetLastError());
        WSACleanup();
        return 1;
    }

    // Configuration de l'adresse d'écoute
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(PORT_MANAGER);

    // Liaison de la socket
    if (bind(sock_manager, (struct sockaddr *)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        printf("Erreur lors de la liaison de la socket : %d\n", WSAGetLastError());
        closesocket(sock_manager);
        WSACleanup();
        return 1;
    }

    printf("En attente des paquets UDP du Network Manager sur le port %d...\n", PORT_MANAGER);

    while (1) {
        int received_bytes = recvfrom(sock_manager, buffer, BUFFER_SIZE, 0,
                                      (struct sockaddr *)&sender_addr, &addr_len);
        if (received_bytes == SOCKET_ERROR) {
            printf("Erreur lors de la réception des données : %d\n", WSAGetLastError());
            continue;
        }

        buffer[received_bytes] = '\0'; // Assurer la terminaison de la chaîne
        printf("Message reçu du Network Manager (%s:%d) : %s\n",
               inet_ntoa(sender_addr.sin_addr), ntohs(sender_addr.sin_port), buffer);
    }

    closesocket(sock_manager);
    WSACleanup();
    return 0;
}