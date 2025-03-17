#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>

#define MESSAGE "EVENT_A_TO_B"

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s <IP_C_B> <PORT>\n", argv[0]);
        exit(1);
    }

    char *server_ip = argv[1];
    int port = atoi(argv[2]);

    int sockfd;
    struct sockaddr_in server_addr;

    // Création du socket UDP
    if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("Erreur socket");
        exit(1);
    }

    // Configuration de l'adresse du destinataire (C_B)
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    if (inet_pton(AF_INET, server_ip, &server_addr.sin_addr) <= 0) {
        perror("Adresse IP invalide");
        exit(1);
    }

    // Envoi du message
    if (sendto(sockfd, MESSAGE, strlen(MESSAGE), 0, 
               (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        perror("Erreur sendto");
        exit(1);
    }

    printf("Message envoyé à %s:%d\n", server_ip, port);

    close(sockfd);
    return 0;
}
