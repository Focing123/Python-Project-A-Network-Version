#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <fcntl.h>
#include <errno.h>
#include <signal.h>
#include <poll.h>

#define PORT_ENTREE 1234
#define PORT_BROADCAST 12346
#define BROADCAST_IP "255.255.255.255"
#define BUFFER_SIZE 1024

int sockfd_entree, sockfd_broadcast;

void set_socket_nonblocking(int sock) {
    int flags = fcntl(sock, F_GETFL, 0);
    fcntl(sock, F_SETFL, flags | O_NONBLOCK);
}

void handle_exit(int signum) {
    printf("\nFermeture des sockets...\n");
    close(sockfd_entree);
    close(sockfd_broadcast);
    exit(EXIT_SUCCESS);
}

int main() {
    struct sockaddr_in addr_local_entree, addr_remote;
    char buffer[BUFFER_SIZE];
    char local_ip[INET_ADDRSTRLEN];

    signal(SIGINT, handle_exit);

    // Récupération de l'adresse IP locale
    struct sockaddr_in temp_addr;
    int temp_sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (temp_sock < 0) {
        perror("Erreur socket temporaire");
        exit(EXIT_FAILURE);
    }
    temp_addr.sin_family = AF_INET;
    temp_addr.sin_addr.s_addr = inet_addr("8.8.8.8");
    temp_addr.sin_port = htons(53);
    connect(temp_sock, (struct sockaddr *)&temp_addr, sizeof(temp_addr));
    socklen_t temp_len = sizeof(temp_addr);
    getsockname(temp_sock, (struct sockaddr *)&temp_addr, &temp_len);
    inet_ntop(AF_INET, &temp_addr.sin_addr, local_ip, INET_ADDRSTRLEN);
    close(temp_sock);
    printf("Adresse IP locale: %s\n", local_ip);

    // Création des sockets
    if ((sockfd_entree = socket(AF_INET, SOCK_DGRAM, 0)) < 0 ||
        (sockfd_broadcast = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("Erreur socket");
        exit(EXIT_FAILURE);
    }

    // Activation de SO_REUSEADDR
    int reuse = 1;
    setsockopt(sockfd_entree, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));

    // Activation du mode broadcast
    int broadcast_enable = 1;
    setsockopt(sockfd_broadcast, SOL_SOCKET, SO_BROADCAST, &broadcast_enable, sizeof(broadcast_enable));

    // Configuration des adresses
    memset(&addr_local_entree, 0, sizeof(addr_local_entree));
    addr_local_entree.sin_family = AF_INET;
    addr_local_entree.sin_addr.s_addr = htonl(INADDR_ANY);
    addr_local_entree.sin_port = htons(PORT_ENTREE);

    if (bind(sockfd_entree, (struct sockaddr *)&addr_local_entree, sizeof(addr_local_entree)) < 0) {
        perror("Erreur bind entrée");
        exit(EXIT_FAILURE);
    }

    memset(&addr_remote, 0, sizeof(addr_remote));
    addr_remote.sin_family = AF_INET;
    addr_remote.sin_addr.s_addr = inet_addr(BROADCAST_IP);
    addr_remote.sin_port = htons(PORT_BROADCAST);

    set_socket_nonblocking(sockfd_entree);

    struct pollfd fds[1];
    fds[0].fd = sockfd_entree;
    fds[0].events = POLLIN;

    while (1) {
        int poll_result = poll(fds, 1, 100);
        if (poll_result > 0 && (fds[0].revents & POLLIN)) {
            struct sockaddr_in sender_addr;
            socklen_t sender_len = sizeof(sender_addr);
            int received_bytes = recvfrom(sockfd_entree, buffer, BUFFER_SIZE - 1, 0, (struct sockaddr *)&sender_addr, &sender_len);

            if (received_bytes > 0) {
                buffer[received_bytes] = '\0';
                printf("Reçu de Python: %s\n", buffer);
                if (sendto(sockfd_broadcast, buffer, strlen(buffer), 0, (struct sockaddr *)&addr_remote, sizeof(addr_remote)) < 0) {
                    perror("Erreur broadcast");
                } else {
                    printf("Message broadcasté avec succès !\n");
                }
            }
        }
    }

    return 0;
}
