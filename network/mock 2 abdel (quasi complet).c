#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include "cJSON.h"

#pragma comment(lib, "ws2_32.lib")

#define LISTEN_PORT 12345       // Port d'écoute
#define DEST_IP "127.0.0.1" // Adresse IP du joueur B (remplace par la vraie IP)
#define DEST_PORT 54321         // Port du joueur B
#define BUFFER_SIZE 1024

typedef struct {
    int id;
    char message[BUFFER_SIZE];
} EventData;

void parse_json(const char *json_str, EventData *event_data) {
    cJSON *json = cJSON_Parse(json_str);
    if (json == NULL) {
        fprintf(stderr, "Erreur de parsing JSON\n");
        return;
    }

    cJSON *id = cJSON_GetObjectItemCaseSensitive(json, "id");
    cJSON *message = cJSON_GetObjectItemCaseSensitive(json, "message");

    if (cJSON_IsNumber(id)) {
        event_data->id = id->valueint;
    }

    if (cJSON_IsString(message) && (message->valuestring != NULL)) {
        strncpy(event_data->message, message->valuestring, BUFFER_SIZE - 1);
        event_data->message[BUFFER_SIZE - 1] = '\0'; // Assurer la terminaison
    }

    cJSON_Delete(json);
}

int main() {
    WSADATA wsaData;
    SOCKET sockfd;
    struct sockaddr_in listen_addr, dest_addr;
    char buffer[BUFFER_SIZE] = {0};
    EventData event_data;
    int recv_len;
    socklen_t addr_len = sizeof(listen_addr);

    // Initialisation de Winsock
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        fprintf(stderr, "Erreur de WSAStartup\n");
        exit(EXIT_FAILURE);
    }

    // Création du socket UDP
    if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) == INVALID_SOCKET) {
        perror("Erreur de socket");
        WSACleanup();
        exit(EXIT_FAILURE);
    }

    // Configuration du serveur en écoute
    memset(&listen_addr, 0, sizeof(listen_addr));
    listen_addr.sin_family = AF_INET;
    listen_addr.sin_addr.s_addr = INADDR_ANY;
    listen_addr.sin_port = htons(LISTEN_PORT);

    // Lier le socket au port d'écoute
    if (bind(sockfd, (struct sockaddr *)&listen_addr, sizeof(listen_addr)) == SOCKET_ERROR) {
        perror("Erreur de bind");
        closesocket(sockfd);
        WSACleanup();
        exit(EXIT_FAILURE);
    }

    // Configuration de l'adresse de destination (Joueur B)
    memset(&dest_addr, 0, sizeof(dest_addr));
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port = htons(DEST_PORT);
    if (inet_pton(AF_INET, DEST_IP, &dest_addr.sin_addr) <= 0) {
        perror("Adresse IP invalide");
        closesocket(sockfd);
        WSACleanup();
        exit(EXIT_FAILURE);
    }

    printf("🎧 Serveur en attente sur le port %d...\n", LISTEN_PORT);

    // Boucle d'écoute et d'envoi
    while (1) {
        recv_len = recvfrom(sockfd, buffer, BUFFER_SIZE - 1, 0, NULL, NULL);
        if (recv_len > 0) {
            buffer[recv_len] = '\0'; // Assurer la terminaison
            printf("📩 Événement reçu : %s\n", buffer);

            // Parse JSON et stocker dans event_data
            parse_json(buffer, &event_data);
            printf("➡ ID: %d, Message: %s\n", event_data.id, event_data.message);

            // Envoyer l'événement au joueur B
            if (sendto(sockfd, buffer, strlen(buffer), 0, (struct sockaddr*)&dest_addr, sizeof(dest_addr)) < 0) {
                perror("Erreur lors de l'envoi de l'événement");
            } else {
                printf("📤 Événement envoyé à %s:%d\n", DEST_IP, DEST_PORT);
            }
        }
    }

    closesocket(sockfd);
    WSACleanup();
    return 0;
}
