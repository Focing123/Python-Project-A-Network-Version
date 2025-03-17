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

#define FORWARDER_PORT 12346  // Port for the forwarder to listen on
#define REMOTE_PORT 12347     // Port to send events to the other player
#define PYTHON_PORT 12345     // Port to send events back to Python
#define BUFFER_SIZE 65535     // Max UDP packet size

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

// Create JSON string from event data
char* create_json_event(int id, int type, const char* message) {
    cJSON *json = cJSON_CreateObject();
    cJSON_AddNumberToObject(json, "id", id);
    cJSON_AddNumberToObject(json, "type", type);
    cJSON_AddStringToObject(json, "message", message);
    
    char *json_str = cJSON_Print(json);
    cJSON_Delete(json);
    
    return json_str;
}

int main(int argc, char *argv[]) {
    initialize_socket_library();
    
    if (argc < 2) {
        printf("Usage: %s <remote_ip>\n", argv[0]);
        printf("Example: %s 192.168.1.5\n", argv[0]);
        cleanup_socket_library();
        return 1;
    }
    
    char *remote_ip = argv[1];
    int sock;
    struct sockaddr_in local_addr, remote_addr, python_addr;
    socklen_t addr_len = sizeof(struct sockaddr_in);
    char buffer[BUFFER_SIZE];

    // Create UDP socket
    if ((sock = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("Socket creation failed");
        cleanup_socket_library();
        exit(EXIT_FAILURE);
    }

    // Configure socket to listen for events
    memset(&local_addr, 0, sizeof(local_addr));
    local_addr.sin_family = AF_INET;
    local_addr.sin_addr.s_addr = INADDR_ANY;
    local_addr.sin_port = htons(FORWARDER_PORT);

    // Bind to local port
    if (bind(sock, (struct sockaddr *)&local_addr, sizeof(local_addr)) < 0) {
        perror("Bind failed");
        cleanup_socket_library();
        exit(EXIT_FAILURE);
    }

    // Configure remote player address
    memset(&remote_addr, 0, sizeof(remote_addr));
    remote_addr.sin_family = AF_INET;
    remote_addr.sin_addr.s_addr = inet_addr(remote_ip);
    remote_addr.sin_port = htons(REMOTE_PORT);
    
    // Configure Python address (local)
    memset(&python_addr, 0, sizeof(python_addr));
    python_addr.sin_family = AF_INET;
    python_addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    python_addr.sin_port = htons(PYTHON_PORT);

    printf("UDP forwarder listening on port %d...\n", FORWARDER_PORT);
    printf("Ready to forward events to %s:%d\n", remote_ip, REMOTE_PORT);

    while (1) {
        int recv_len = recvfrom(sock, buffer, BUFFER_SIZE - 1, 0, 
                               (struct sockaddr *)&local_addr, &addr_len);
        
        if (recv_len > 0) {
            buffer[recv_len] = '\0';
            printf("Received data: %s\n", buffer);
            
            // Forward to remote player
            sendto(sock, buffer, strlen(buffer), 0, 
                  (struct sockaddr *)&remote_addr, sizeof(remote_addr));
            printf("Forwarded to remote player at %s:%d\n", 
                   remote_ip, REMOTE_PORT);
                   
            // Also send back to local Python if needed
            sendto(sock, buffer, strlen(buffer), 0, 
                  (struct sockaddr *)&python_addr, sizeof(python_addr));
            printf("Sent back to local Python at 127.0.0.1:%d\n", PYTHON_PORT);
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