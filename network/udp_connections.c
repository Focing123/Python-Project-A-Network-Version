#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>

#define DEST_PORT 9090          // Port du joueur B
#define DEST_IP "127.0.0.1" // Adresse IP du joueur B (remplace par la vraie IP)
#define BUFFER_SIZE 1024        // Taille max d'un événement

int main() {
    int sockfd;
    struct sockaddr_in dest_addr;
    char buffer[BUFFER_SIZE];

    // Création du socket UDP
    if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("Erreur lors de la création du socket");
        exit(EXIT_FAILURE);
    }

    // Configuration de l'adresse de destination (Joueur B)
    memset(&dest_addr, 0, sizeof(dest_addr));
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port = htons(DEST_PORT);
    if (inet_pton(AF_INET, DEST_IP, &dest_addr.sin_addr) <= 0) {
        perror("Adresse IP invalide");
        close(sockfd);
        exit(EXIT_FAILURE);
    }

    printf("📡 En attente d'événements à envoyer...\n");

    while (1) {
        // Lire un événement depuis l'entrée standard
        printf("🔹 Tape un événement (ou 'exit' pour quitter) : ");
        if (fgets(buffer, BUFFER_SIZE, stdin) == NULL) {
            perror("Erreur de lecture de l'événement");
            continue;
        }

        // Supprimer le retour à la ligne initial
        buffer[strcspn(buffer, "\n")] = 0;

        // Quitter si l'utilisateur tape "exit"
        if (strcmp(buffer, "exit") == 0) {
            printf("🚪 Fin du programme.\n");
            break;
        }

        // Ajouter un saut de ligne pour séparer chaque événement sur la réception
        strcat(buffer, "\n");

        // Envoyer l'événement au joueur B
        if (sendto(sockfd, buffer, strlen(buffer), 0, (struct sockaddr*)&dest_addr, sizeof(dest_addr)) < 0) {
            perror("Erreur lors de l'envoi de l'événement");
        } else {
            printf("📤 Événement envoyé à %s:%d -> %s", DEST_IP, DEST_PORT, buffer);  // Pas besoin de \n ici
        }
    }

    close(sockfd);
    return 0;
}
