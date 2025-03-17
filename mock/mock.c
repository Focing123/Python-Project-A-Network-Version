#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include "cJSON.h"

#define PORT 5000
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
    int server_fd, new_socket;
    struct sockaddr_in address;
    char buffer[BUFFER_SIZE] = {0};
    EventData event_data;

    // Création du socket
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        perror("Erreur de socket");
        exit(EXIT_FAILURE);
    }

    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);

    // Liaison du socket
    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        perror("Erreur de bind");
        exit(EXIT_FAILURE);
    }

    // Écoute des connexions entrantes
    if (listen(server_fd, 3) < 0) {
        perror("Erreur de listen");
        exit(EXIT_FAILURE);
    }

    printf("Serveur en attente sur le port %d...\n", PORT);
    if ((new_socket = accept(server_fd, NULL, NULL)) < 0) {
        perror("Erreur d'accept");
        exit(EXIT_FAILURE);
    }

    // Réception des événements en boucle
    while (1) {
        int valread = read(new_socket, buffer, BUFFER_SIZE - 1);
        if (valread > 0) {
            buffer[valread] = '\0'; // S'assurer que la chaîne est terminée correctement
            printf("Événement reçu : %s\n", buffer);

            // Parse JSON and store in event_data
            parse_json(buffer, &event_data);
            printf("ID: %d, Message: %s\n", event_data.id, event_data.message);
        }
    }
    close(new_socket);
    close(server_fd);
    

    return 0;
}