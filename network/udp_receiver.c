#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
    #define close_socket closesocket
#else
    #include <arpa/inet.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <unistd.h>
    #define close_socket close
#endif

#define LOCAL_PORT 12345    // Port to receive events from Python
#define BUFFER_SIZE 65535   // Max UDP packet size

// New structure to match the custom format
typedef struct {
    int turn;
    char map[1024];
    // Dynamic array of players could be added here for a real implementation
    char raw_data[BUFFER_SIZE]; // Store the original raw data
} GameState;

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

// Parse the custom string format: turn=X||map=Y||player:name=Z|units=...|...
void parse_game_state(const char *data, GameState *state) {
    // Store the original data
    strncpy(state->raw_data, data, BUFFER_SIZE - 1);
    state->raw_data[BUFFER_SIZE - 1] = '\0';
    
    // Default values
    state->turn = -1;
    strcpy(state->map, "unknown");
    
    // Parse the main sections (separated by ||)
    char *data_copy = strdup(data);
    char *section = strtok(data_copy, "||");
    
    while (section != NULL) {
        // Parse each section
        if (strncmp(section, "turn=", 5) == 0) {
            state->turn = atoi(section + 5);
        }
        else if (strncmp(section, "map=", 4) == 0) {
            strncpy(state->map, section + 4, sizeof(state->map) - 1);
            state->map[sizeof(state->map) - 1] = '\0';
        }
        // For player sections, we'd need more complex parsing for a full implementation
        
        section = strtok(NULL, "||");
    }
    
    free(data_copy);
}

// Process the game state
void process_game_state(GameState *state) {
    printf("Processing game state - Turn: %d, Map: %s\n", state->turn, state->map);
    // Add game-specific processing logic here
}

int main() {
    initialize_socket_library();
    
    int sock;
    struct sockaddr_in local_addr, remote_addr;
    socklen_t addr_len = sizeof(struct sockaddr_in);
    char buffer[BUFFER_SIZE];
    GameState game_state;

    // Create UDP socket
    #ifdef _WIN32
    if ((sock = socket(AF_INET, SOCK_DGRAM, 0)) == INVALID_SOCKET) {
    #else
    if ((sock = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
    #endif
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
    #ifdef _WIN32
    if (bind(sock, (struct sockaddr *)&local_addr, sizeof(local_addr)) == SOCKET_ERROR) {
    #else
    if (bind(sock, (struct sockaddr *)&local_addr, sizeof(local_addr)) < 0) {
    #endif
        perror("Bind failed");
        close_socket(sock);
        cleanup_socket_library();
        exit(EXIT_FAILURE);
    }

    printf("UDP receiver listening on port %d...\n", LOCAL_PORT);

    while (1) {
        int recv_len = recvfrom(sock, buffer, BUFFER_SIZE - 1, 0, 
                               (struct sockaddr *)&remote_addr, &addr_len);
        
        if (recv_len > 0) {
            buffer[recv_len] = '\0';
            printf("Received data from %s:%d (%d bytes)\n", 
                   inet_ntoa(remote_addr.sin_addr), ntohs(remote_addr.sin_port), recv_len);
            
            // Parse and process the data
            parse_game_state(buffer, &game_state);
            process_game_state(&game_state);
        }
    }

    close_socket(sock);
    cleanup_socket_library();
    return 0;
}