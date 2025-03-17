#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
#else
    #include <arpa/inet.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
#endif
#include "../mock/cJSON.h"

#define LOCAL_PORT 12345    // Port to receive events from Python
#define BUFFER_SIZE 65535   // Max UDP packet size

typedef struct {
    int id;
    int type;
    char message[BUFFER_SIZE];
    // Add other fields as needed for your game events
} GameEvent;

void initialize_socket_library() {
    #ifdef _WIN32
        WSADATA wsaData;
        if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
            fprintf(stderr, "WSAStartup failed\n");
            exit(EXIT_FAILURE);
        }
    #endif
}

void cleanup_socket_library() {
    #ifdef _WIN32
        WSACleanup();
    #endif
}

void parse_json_event(const char *json_str, GameEvent *game_event) {
    cJSON *json = cJSON_Parse(json_str);
    if (json == NULL) {
        fprintf(stderr, "Error parsing JSON\n");
        return;
    }

    cJSON *id = cJSON_GetObjectItemCaseSensitive(json, "id");
    cJSON *type = cJSON_GetObjectItemCaseSensitive(json, "type");
    cJSON *message = cJSON_GetObjectItemCaseSensitive(json, "message");

    if (cJSON_IsNumber(id)) {
        game_event->id = id->valueint;
    }
    
    if (cJSON_IsNumber(type)) {
        game_event->type = type->valueint;
    }

    if (cJSON_IsString(message) && (message->valuestring != NULL)) {
        strncpy(game_event->message, message->valuestring, BUFFER_SIZE - 1);
        game_event->message[BUFFER_SIZE - 1] = '\0';
    }

    cJSON_Delete(json);
}

// Process the game event according to game logic
void process_game_event(GameEvent *event) {
    printf("Processing event ID: %d, Type: %d\n", event->id, event->type);
    // Add game-specific processing logic here
    
    // For example, modify the message
    strcat(event->message, " [Processed]");
}

int main() {
    initialize_socket_library();
    
    int sock;
    struct sockaddr_in local_addr, remote_addr;
    socklen_t addr_len = sizeof(struct sockaddr_in);
    char buffer[BUFFER_SIZE];
    GameEvent game_event;

    // Create UDP socket
    if ((sock = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("Socket creation failed");
        cleanup_socket_library();
        exit(EXIT_FAILURE);
    }

    // Configure socket to listen for local Python events
    memset(&local_addr, 0, sizeof(local_addr));
    local_addr.sin_family = AF_INET;
    local_addr.sin_addr.s_addr = INADDR_ANY;
    local_addr.sin_port = htons(LOCAL_PORT);

    // Bind to local port
    if (bind(sock, (struct sockaddr *)&local_addr, sizeof(local_addr)) < 0) {
        perror("Bind failed");
        cleanup_socket_library();
        exit(EXIT_FAILURE);
    }

    printf("UDP receiver listening on port %d...\n", LOCAL_PORT);

    while (1) {
        int recv_len = recvfrom(sock, buffer, BUFFER_SIZE - 1, 0, 
                               (struct sockaddr *)&remote_addr, &addr_len);
        
        if (recv_len > 0) {
            buffer[recv_len] = '\0';
            printf("Received data from %s:%d: %s\n", 
                   inet_ntoa(remote_addr.sin_addr), ntohs(remote_addr.sin_port), buffer);
            
            // Parse and process the event
            parse_json_event(buffer, &game_event);
            process_game_event(&game_event);
            
            // The processed event will be sent by the forwarder
        }
    }

    #ifdef _WIN32
        closesocket(sock);
    #else
        close(sock);
    #endif
    
    cleanup_socket_library();
    return 0;
}