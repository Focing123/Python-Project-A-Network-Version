#define WIN32_LEAN_AND_MEAN
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <time.h>
#include <stdarg.h>

#pragma comment(lib, "Ws2_32.lib")

#define PY_TO_C_PORT 6000
#define BROADCAST_PORT 6001
#define C_TO_PY_PORT 6002
#define BUFFER_SIZE 65507
#define MAX_FRAGMENTS 100

// Flag for quiet mode
int quiet_mode = 0;

// Debug print function that respects quiet mode
void debug_print(const char* format, ...) {
    if (!quiet_mode) {
        va_list args;
        va_start(args, format);
        vprintf(format, args);
        va_end(args);
    }
}

// Structure pour stocker les fragments
typedef struct {
    char* data;
    int size;
    int received;
} Fragment;

// Structure pour gérer les fragments en cours de réception
typedef struct {
    Fragment fragments[MAX_FRAGMENTS];
    int total_fragments;
    time_t last_update;
} FragmentManager;

// Initialisation du gestionnaire de fragments
void init_fragment_manager(FragmentManager* manager) {
    for (int i = 0; i < MAX_FRAGMENTS; i++) {
        manager->fragments[i].data = NULL;
        manager->fragments[i].size = 0;
        manager->fragments[i].received = 0;
    }
    manager->total_fragments = 0;
    manager->last_update = time(NULL);
}

// Libération de la mémoire des fragments
void clear_fragments(FragmentManager* manager) {
    for (int i = 0; i < MAX_FRAGMENTS; i++) {
        if (manager->fragments[i].data) {
            free(manager->fragments[i].data);
            manager->fragments[i].data = NULL;
        }
        manager->fragments[i].size = 0;
        manager->fragments[i].received = 0;
    }
    manager->total_fragments = 0;
}

// Fonction pour transférer un message fragmenté
void forward_message(SOCKET sock, const char* buffer, int length, struct sockaddr* dest_addr, int addr_len) {
    int sent = 0;
    while (sent < length) {
        int chunk_size = min(16384, length - sent);
        int result = sendto(sock, buffer + sent, chunk_size, 0, dest_addr, addr_len);
        if (result == SOCKET_ERROR) {
            debug_print("Erreur d'envoi: %d\n", WSAGetLastError());
            break;
        }
        sent += result;
        Sleep(1);
    }
}

// Fonction pour recevoir tous les fragments d'un message
int receiveComplete(SOCKET sock, char* buffer, int maxSize, struct sockaddr* from, int* fromlen) {
    int total = 0;
    int tries = 0;
    const int MAX_TRIES = 10;
    
    while (tries < MAX_TRIES) {
        int received = recvfrom(sock, buffer + total, maxSize - total, 0, from, fromlen);
        if (received == SOCKET_ERROR) {
            if (WSAGetLastError() == WSAEWOULDBLOCK) {
                Sleep(10); // Attendre un peu avant de réessayer
                tries++;
                continue;
            }
            return SOCKET_ERROR;
        }
        total += received;
        if (received < (maxSize - total)) { // Si on reçoit moins que la taille max, c'est probablement la fin
            break;
        }
        tries++;
    }
    return total;
}

int main(int argc, char* argv[]) {
    // Check for quiet mode flag
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-q") == 0 || strcmp(argv[i], "--quiet") == 0) {
            quiet_mode = 1;
            break;
        }
    }

    WSADATA wsaData;
    SOCKET sock_recv, sock_broadcast, sock_forward;
    struct sockaddr_in addr_recv, addr_broadcast_send, addr_broadcast_recv, addr_forward, addr_src;
    char buffer[BUFFER_SIZE];
    int addr_len = sizeof(addr_src);
    fd_set readfds;
    
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        debug_print("WSAStartup échoué.\n");
        return 1;
    }

    // Socket pour recevoir depuis Python
    sock_recv = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_recv == INVALID_SOCKET) {
        debug_print("Erreur de création du socket de réception: %d\n", WSAGetLastError());
        return 1;
    }

    int reuse = 1;
    setsockopt(sock_recv, SOL_SOCKET, SO_REUSEADDR, (char*)&reuse, sizeof(reuse));

    memset(&addr_recv, 0, sizeof(addr_recv));
    addr_recv.sin_family = AF_INET;
    addr_recv.sin_addr.s_addr = INADDR_ANY;
    addr_recv.sin_port = htons(PY_TO_C_PORT);

    if (bind(sock_recv, (struct sockaddr*)&addr_recv, sizeof(addr_recv)) == SOCKET_ERROR) {
        debug_print("Erreur lors du bind du socket de réception: %d\n", WSAGetLastError());
        closesocket(sock_recv);
        WSACleanup();
        return 1;
    }

    // Socket pour envoyer en broadcast
    sock_broadcast = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_broadcast == INVALID_SOCKET) {
        debug_print("Erreur de création du socket broadcast: %d\n", WSAGetLastError());
        closesocket(sock_recv);
        WSACleanup();
        return 1;
    }

    int broadcastEnable = 1;
    setsockopt(sock_broadcast, SOL_SOCKET, SO_BROADCAST, (char*)&broadcastEnable, sizeof(broadcastEnable));

    memset(&addr_broadcast_send, 0, sizeof(addr_broadcast_send));
    addr_broadcast_send.sin_family = AF_INET;
    addr_broadcast_send.sin_port = htons(BROADCAST_PORT);
    char default_broadcast_addr[] = "192.168.141.255";
    char user_input[INET_ADDRSTRLEN];

    printf("Entrez l'adresse de broadcast (par défaut: %s): ", default_broadcast_addr);
    fgets(user_input, INET_ADDRSTRLEN, stdin);

    size_t len = strlen(user_input);
    if (len > 0 && user_input[len - 1] == '\n') {
        user_input[len - 1] = '\0';
    }

    if (strlen(user_input) == 0) {
        strcpy(user_input, default_broadcast_addr);
    }

    addr_broadcast_send.sin_addr.s_addr = inet_addr(user_input);

    // Socket pour recevoir les broadcasts
    sock_forward = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_forward == INVALID_SOCKET) {
        debug_print("Erreur de création du socket forward: %d\n", WSAGetLastError());
        closesocket(sock_recv);
        closesocket(sock_broadcast);
        WSACleanup();
        return 1;
    }

    setsockopt(sock_forward, SOL_SOCKET, SO_REUSEADDR, (char*)&reuse, sizeof(reuse));
    setsockopt(sock_forward, SOL_SOCKET, SO_BROADCAST, (char*)&reuse, sizeof(reuse));

    memset(&addr_broadcast_recv, 0, sizeof(addr_broadcast_recv));
    addr_broadcast_recv.sin_family = AF_INET;
    addr_broadcast_recv.sin_addr.s_addr = INADDR_ANY;
    addr_broadcast_recv.sin_port = htons(BROADCAST_PORT);

    if (bind(sock_forward, (struct sockaddr*)&addr_broadcast_recv, sizeof(addr_broadcast_recv)) == SOCKET_ERROR) {
        debug_print("Erreur lors du bind du socket broadcast: %d\n", WSAGetLastError());
        closesocket(sock_recv);
        closesocket(sock_broadcast);
        closesocket(sock_forward);
        WSACleanup();
        return 1;
    }

    // Configuration de l'adresse pour forward vers Python
    memset(&addr_forward, 0, sizeof(addr_forward));
    addr_forward.sin_family = AF_INET;
    addr_forward.sin_port = htons(C_TO_PY_PORT);
    addr_forward.sin_addr.s_addr = inet_addr("127.0.0.1");

    // Configuration des sockets en mode non-bloquant
    u_long mode = 1;
    ioctlsocket(sock_recv, FIONBIO, &mode);
    ioctlsocket(sock_forward, FIONBIO, &mode);
    ioctlsocket(sock_broadcast, FIONBIO, &mode);

    printf("Relais UDP actif.\n");
    
    FragmentManager recv_fragments;
    FragmentManager forward_fragments;
    init_fragment_manager(&recv_fragments);
    init_fragment_manager(&forward_fragments);

    while (1) {
        time_t current_time = time(NULL);
        
        // Nettoyer les fragments obsolètes (plus de 5 secondes)
        if (current_time - recv_fragments.last_update > 5) {
            clear_fragments(&recv_fragments);
        }
        if (current_time - forward_fragments.last_update > 5) {
            clear_fragments(&forward_fragments);
        }

        // Traitement des messages depuis Python
        int recv_len = receiveComplete(sock_recv, buffer, BUFFER_SIZE, (struct sockaddr*)&addr_src, &addr_len);
        if (recv_len > 0) {
            debug_print("Reçu %d octets depuis Python et transféré en broadcast\n", recv_len);
            // Transférer tel quel vers le broadcast
            forward_message(sock_broadcast, buffer, recv_len, 
                          (struct sockaddr*)&addr_broadcast_send, 
                          sizeof(addr_broadcast_send));
        }

        // Traitement des messages broadcast
        recv_len = receiveComplete(sock_forward, buffer, BUFFER_SIZE, (struct sockaddr*)&addr_src, &addr_len);
        if (recv_len > 0) {
            debug_print("Reçu %d octets en broadcast et transféré vers Python\n", recv_len);
            // Transférer tel quel vers Python
            forward_message(sock_forward, buffer, recv_len,
                          (struct sockaddr*)&addr_forward,
                          sizeof(addr_forward));
        }

        Sleep(1);
    }

    clear_fragments(&recv_fragments);
    clear_fragments(&forward_fragments);

    closesocket(sock_recv);
    closesocket(sock_broadcast);
    closesocket(sock_forward);
    WSACleanup();
    return 0;
}