#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/select.h>

#define PORT 1234
#define BROADCAST_IP "255.255.255.255"
#define BUFFER_SIZE 1024

int main() {
    struct sockaddr_in addr_local, addr_remote, sender_addr;
    int sockfd;
    char buffer[BUFFER_SIZE];
    socklen_t sender_len = sizeof(sender_addr);

    // Création du socket
    if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("Erreur lors de la création du socket");
        exit(EXIT_FAILURE);
    }

    // Activation de SO_REUSEADDR
    int reuse = 1;
    if (setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse)) < 0) {
        perror("Erreur lors de l'activation de SO_REUSEADDR");
        exit(EXIT_FAILURE);
    }

    // Activation du mode broadcast
    int broadcast_enable = 1;
    if (setsockopt(sockfd, SOL_SOCKET, SO_BROADCAST, &broadcast_enable, sizeof(broadcast_enable)) < 0) {
        perror("Erreur lors de l'activation du broadcast");
        exit(EXIT_FAILURE);
    }

    // Configuration de l'adresse locale
    memset(&addr_local, 0, sizeof(addr_local));
    addr_local.sin_family = AF_INET;
    addr_local.sin_addr.s_addr = htonl(INADDR_ANY);
    addr_local.sin_port = htons(PORT);

    // Liaison du socket
    if (bind(sockfd, (struct sockaddr *)&addr_local, sizeof(addr_local)) < 0) {
        perror("Erreur lors de la liaison du socket");
        exit(EXIT_FAILURE);
    }

    // Définition de l'adresse de broadcast
    memset(&addr_remote, 0, sizeof(addr_remote));
    addr_remote.sin_family = AF_INET;
    addr_remote.sin_addr.s_addr = inet_addr(BROADCAST_IP);
    addr_remote.sin_port = htons(PORT);

    printf("Serveur UDP en écoute sur le port %d...\n", PORT);

    while (1) {
        fd_set readfds;
        FD_ZERO(&readfds);
        FD_SET(sockfd, &readfds);  // Écoute sur le socket
        FD_SET(STDIN_FILENO, &readfds);  // Écoute sur l'entrée clavier

        // Attente d'une activité sur l'un des deux
        int activity = select(sockfd + 1, &readfds, NULL, NULL, NULL);
        if (activity < 0 && errno != EINTR) {
            perror("Erreur dans select()");
            exit(EXIT_FAILURE);
        }

        // Vérifier si des données sont reçues sur le socket
        if (FD_ISSET(sockfd, &readfds)) {
            int received_bytes = recvfrom(sockfd, buffer, BUFFER_SIZE - 1, 0, (struct sockaddr *)&sender_addr, &sender_len);
            if (received_bytes > 0) {
                buffer[received_bytes] = '\0';
                printf("Reçu: %s\n", buffer);
            }
        }

        // Vérifier si l'utilisateur a tapé un message
        if (FD_ISSET(STDIN_FILENO, &readfds)) {
            if (fgets(buffer, BUFFER_SIZE, stdin) != NULL) {
                size_t len = strlen(buffer);
                if (buffer[len - 1] == '\n') {
                    buffer[len - 1] = '\0';
                }

                // Envoi en broadcast
                if (sendto(sockfd, buffer, strlen(buffer), 0, (struct sockaddr *)&addr_remote, sizeof(addr_remote)) < 0) {
                    perror("Erreur lors de l'envoi du message");
                } else {
                    printf("Envoyé: %s\n", buffer);
                }
            }
        }
    }

    close(sockfd);
    return 0;
}
