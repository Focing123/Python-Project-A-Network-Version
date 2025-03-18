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

#define LISTEN_PORT 1234   // Port d'écoute des événements entrants
#define FORWARD_PORT 12345  // Port où on envoie les événements
#define BUFFER_SIZE 65535   // Taille max d'un paquet UDP
#define BROADCAST_IP "255.255.255.255" // Adresse de broadcast

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

int main() {
    initialize_socket_library();

    int sock_listen, sock_receive;
    struct sockaddr_in local_addr, forward_addr, response_addr;
    socklen_t addr_len = sizeof(struct sockaddr_in);
    char buffer[BUFFER_SIZE];

    // Création du socket d'écoute
    if ((sock_listen = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("Erreur création socket écoute");
        cleanup_socket_library();
        exit(EXIT_FAILURE);
    }

    // Création du socket pour recevoir les réponses
    if ((sock_receive = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("Erreur création socket réponse");
        cleanup_socket_library();
        exit(EXIT_FAILURE);
    }

    // Activation du mode broadcast
    int broadcastEnable = 1;
    if (setsockopt(sock_listen, SOL_SOCKET, SO_BROADCAST, (const char*) &broadcastEnable, sizeof(broadcastEnable)) < 0) {
        perror("Erreur activation broadcast");
        close_socket(sock_listen);
        cleanup_socket_library();
        exit(EXIT_FAILURE);
    }

    // Configuration de l'adresse locale d'écoute
    memset(&local_addr, 0, sizeof(local_addr));
    local_addr.sin_family = AF_INET;
    local_addr.sin_addr.s_addr = INADDR_ANY;
    local_addr.sin_port = htons(LISTEN_PORT);

    // Configuration de l'adresse locale pour recevoir les réponses
    memset(&response_addr, 0, sizeof(response_addr));
    response_addr.sin_family = AF_INET;
    response_addr.sin_addr.s_addr = INADDR_ANY;
    response_addr.sin_port = htons(FORWARD_PORT);

    // Configuration de l'adresse de broadcast
    memset(&forward_addr, 0, sizeof(forward_addr));
    forward_addr.sin_family = AF_INET;
    forward_addr.sin_port = htons(FORWARD_PORT);
    forward_addr.sin_addr.s_addr = inet_addr(BROADCAST_IP);

    int opt = 1;
    setsockopt(sock_listen, SOL_SOCKET, SO_REUSEADDR, (const char*) &opt, sizeof(opt));
    // Lier le socket d'écoute
    if (bind(sock_listen, (struct sockaddr *)&local_addr, sizeof(local_addr)) < 0) {
        perror("Échec du bind (écoute)");
        close_socket(sock_listen);
        cleanup_socket_library();
        exit(EXIT_FAILURE);
    }

    

    // Lier le socket de réception des réponses
    if (bind(sock_receive, (struct sockaddr *)&response_addr, sizeof(response_addr)) < 0) {
        perror("Échec du bind (réception)");
        close_socket(sock_listen);
        close_socket(sock_receive);
        cleanup_socket_library();
        exit(EXIT_FAILURE);
    }

    printf("Proxy UDP actif : écoute sur %d, envoie en broadcast sur %s:%d, reçoit sur %d\n", 
           LISTEN_PORT, BROADCAST_IP, FORWARD_PORT, FORWARD_PORT);

    // Boucle de réception et transmission bidirectionnelle
    while (1) {
        struct sockaddr_in sender_addr;
        int recv_len;
        
        // Écoute des événements entrants
        recv_len = recvfrom(sock_listen, buffer, BUFFER_SIZE - 1, 0, 
                            (struct sockaddr *)&sender_addr, &addr_len);
        printf("%i \n", recv_len);
        if (recv_len > 0) {
            buffer[recv_len] = '\0';
            printf("Reçu de %s:%d (%d bytes)\n", 
                   inet_ntoa(sender_addr.sin_addr), ntohs(sender_addr.sin_port), recv_len);

            // Transmission en broadcast
            if (sendto(sock_listen, buffer, recv_len, 0, 
                       (struct sockaddr *)&forward_addr, sizeof(forward_addr)) < 0) {
                perror("Erreur envoi en broadcast");
            } else {
                printf("Transmis en broadcast sur %s:%d\n", BROADCAST_IP, FORWARD_PORT);
            }
        }

        // Écoute des événements renvoyés
        recv_len = recvfrom(sock_receive, buffer, BUFFER_SIZE - 1, 0, 
                            (struct sockaddr *)&sender_addr, &addr_len);
        if (recv_len > 0) {
            buffer[recv_len] = '\0';
            printf("Réponse reçue de %s:%d (%d bytes)\n", 
                   inet_ntoa(sender_addr.sin_addr), ntohs(sender_addr.sin_port), recv_len);

            // Renvoyer au client d'origine
            if (sendto(sock_listen, buffer, recv_len, 0, 
                       (struct sockaddr *)&sender_addr, sizeof(sender_addr)) < 0) {
                perror("Erreur renvoi vers client");
            } else {
                printf("Renvoi à %s:%d\n", inet_ntoa(sender_addr.sin_addr), ntohs(sender_addr.sin_port));
            }
        }
    }

    close_socket(sock_listen);
    close_socket(sock_receive);
    cleanup_socket_library();
    return 0;
}
