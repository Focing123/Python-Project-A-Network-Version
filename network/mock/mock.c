#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include "cJSON.h"

#pragma comment(lib, "ws2_32.lib")

#define PORT 12345
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
        event_data->message[BUFFER_SIZE - 1] = '\0'; // Assurer la terminaison de la chaîne
    }

    cJSON_Delete(json);
}

int main() {
    WSADATA wsaData;
    int server_fd;
    struct sockaddr_in address;
    char buffer[BUFFER_SIZE] = {0};
    EventData event_data;

    // Initialisation de Winsock
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        fprintf(stderr, "Erreur de WSAStartup\n");
        exit(EXIT_FAILURE);
    }

    // Création du socket UDP
    if ((server_fd = socket(AF_INET, SOCK_DGRAM, 0)) == INVALID_SOCKET) {
        perror("Erreur de socket");
        WSACleanup();
        exit(EXIT_FAILURE);
    }

    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY; // Listen on all interfaces
    address.sin_port = htons(PORT);

    // Liaison du socket
    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) == SOCKET_ERROR) {
        perror("Erreur de bind");
        closesocket(server_fd);
        WSACleanup();
        exit(EXIT_FAILURE);
    }

    printf("Serveur UDP en attente sur le port %d...\n", PORT);

    // Réception des événements en boucle
    while (1) {
        int valread = recvfrom(server_fd, buffer, BUFFER_SIZE - 1, 0, NULL, NULL);
        if (valread > 0) {
            buffer[valread] = '\0'; // S'assurer que la chaîne est terminée correctement
            printf("Événement reçu : %s\n", buffer);

            // Parse JSON and store in event_data
            parse_json(buffer, &event_data);
            printf("ID: %d, Message: %s\n", event_data.id, event_data.message);
        }
    }
}
