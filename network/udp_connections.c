#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>

#define BUFFER_SIZE 1024
#define LISTEN_PORT 8080      // Port d'écoute pour les événements UDP
#define DEST_PORT 9090        // Port de destination (où envoyer la réponse)
#define DEST_IP "127.0.0.1"   // Adresse IP cible pour la réponse

int main() {
    int sockfd;
    struct sockaddr_in server_addr, client_addr, dest_addr;
    char buffer[BUFFER_SIZE];
    socklen_t addr_len = sizeof(client_addr);

    // Création du socket UDP
    if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("Erreur lors de la création du socket");
        exit(EXIT_FAILURE);
    }

    // Configuration de l'adresse du serveur
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(LISTEN_PORT);

    // Attachement du socket à l'adresse et au port
    if (bind(sockfd, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        perror("Erreur lors du bind");
        close(sockfd);
        exit(EXIT_FAILURE);
    }

    printf("🔄 Serveur en écoute sur le port %d...\n", LISTEN_PORT);

    // Configuration de l'adresse de destination (pour envoyer des événements)
    memset(&dest_addr, 0, sizeof(dest_addr));
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port = htons(DEST_PORT);
    inet_pton(AF_INET, DEST_IP, &dest_addr.sin_addr);

    while (1) {
        // Réception d'un message UDP
        ssize_t recv_len = recvfrom(sockfd, buffer, BUFFER_SIZE, 0,
                                    (struct sockaddr*)&client_addr, &addr_len);
        if (recv_len < 0) {
            perror("Erreur lors de la réception");
            continue;
        }

        buffer[recv_len] = '\0'; // Ajout du caractère de fin de chaîne
        printf("📩 Message reçu : %s\n", buffer);

        // Envoi de la réponse vers un autre hôte
        const char *response = "✅ Événement traité";
        if (sendto(sockfd, response, strlen(response), 0,
                   (struct sockaddr*)&dest_addr, sizeof(dest_addr)) < 0) {
            perror("Erreur lors de l'envoi de la réponse");
        } else {
            printf("📤 Réponse envoyée à %s:%d\n", DEST_IP, DEST_PORT);
        }
    }

    close(sockfd);
    return 0;
}
