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

#define LISTEN_PORT 12346   // Listen on this port (from Python)
#define FORWARD_PORT 12345  // Forward to this port (to C receiver)
#define BUFFER_SIZE 65535   // Max UDP packet size

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

int main(int argc, char *argv[]) {
    initialize_socket_library();
    
    if (argc < 2) {
        printf("Usage: %s <destination_ip>\n", argv[0]);
        return 1;
    }
    
    const char* destination_ip = argv[1];
    int sock;
    struct sockaddr_in local_addr, forward_addr;
    socklen_t addr_len = sizeof(struct sockaddr_in);
    char buffer[BUFFER_SIZE];

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

    // Configure socket to listen for events
    memset(&local_addr, 0, sizeof(local_addr));
    local_addr.sin_family = AF_INET;
    local_addr.sin_addr.s_addr = INADDR_ANY;
    local_addr.sin_port = htons(LISTEN_PORT);

    // Configure destination for forwarding
    memset(&forward_addr, 0, sizeof(forward_addr));
    forward_addr.sin_family = AF_INET;
    forward_addr.sin_port = htons(FORWARD_PORT);
    
    // Convert IP address from string to binary form
    if (inet_pton(AF_INET, destination_ip, &forward_addr.sin_addr) <= 0) {
        printf("Invalid address: %s\n", destination_ip);
        close_socket(sock);
        cleanup_socket_library();
        return 1;
    }

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

    printf("UDP forwarder listening on port %d, forwarding to %s:%d\n", 
           LISTEN_PORT, destination_ip, FORWARD_PORT);

    // Listen for and forward events
    while (1) {
        struct sockaddr_in client_addr;
        int recv_len = recvfrom(sock, buffer, BUFFER_SIZE - 1, 0, 
                              (struct sockaddr *)&client_addr, &addr_len);
        
        if (recv_len > 0) {
            buffer[recv_len] = '\0';
            printf("Received data from %s:%d (%d bytes)\n", 
                   inet_ntoa(client_addr.sin_addr), 
                   ntohs(client_addr.sin_port), 
                   recv_len);
            
            // Forward the data as-is (no need to parse since we're just forwarding)
            if (sendto(sock, buffer, recv_len, 0, 
                      (struct sockaddr *)&forward_addr, sizeof(forward_addr)) < 0) {
                perror("Forward failed");
            } else {
                printf("Data forwarded to %s:%d\n", 
                       destination_ip, FORWARD_PORT);
            }
        }
    }

    close_socket(sock);
    cleanup_socket_library();
    return 0;
}