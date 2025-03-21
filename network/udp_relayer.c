#define WIN32_LEAN_AND_MEAN
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <time.h>

#pragma comment(lib, "Ws2_32.lib")

#define PY_TO_C_PORT 6000      // Port d'écoute pour les messages venant de Python
#define BROADCAST_PORT 6001    // Port pour le broadcast UDP
#define C_TO_PY_PORT 6002      // Port de transfert vers Python locale
#define BUFFER_SIZE 65507
#define DEBUG 1                // Flag pour activer/désactiver les logs détaillés

// Fonction pour loguer avec horodatage et niveau de détail
void log_message(const char *format, ...) {
    if (DEBUG) {
        time_t current_time;
        char time_string[20];
        time(&current_time);
        strftime(time_string, sizeof(time_string), "%H:%M:%S", localtime(&current_time));
        
        printf("[%s] ", time_string);
        
        va_list args;
        va_start(args, format);
        vprintf(format, args);
        va_end(args);
        
        printf("\n");
        fflush(stdout);  // S'assurer que les logs sont écrits immédiatement
    }
}

// Fonction pour afficher le contenu binaire du buffer (utile pour débogage)
void dump_buffer(const char *prefix, const unsigned char *buffer, int length) {
    if (DEBUG > 1) {  // Activer seulement pour débogage avancé
        log_message("%s (%d bytes):", prefix, length);
        for (int i = 0; i < (length > 32 ? 32 : length); i++) {
            if (i % 16 == 0) printf("\n  ");
            printf("%02X ", buffer[i]);
        }
        printf("\n");
    }
}

DWORD WINAPI broadcast_sender(LPVOID arg) {
    SOCKET sock_recv = INVALID_SOCKET, sock_broadcast = INVALID_SOCKET;
    struct sockaddr_in addr_recv, addr_broadcast;
    char buffer[BUFFER_SIZE];
    int addr_len = sizeof(addr_recv);

    // Socket pour recevoir depuis Python
    sock_recv = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_recv == INVALID_SOCKET) {
        log_message("Erreur de création du socket de réception: %d", WSAGetLastError());
        return 1;
    }
    memset(&addr_recv, 0, sizeof(addr_recv));
    addr_recv.sin_family = AF_INET;
    addr_recv.sin_addr.s_addr = INADDR_ANY;
    addr_recv.sin_port = htons(PY_TO_C_PORT);

    if (bind(sock_recv, (struct sockaddr *)&addr_recv, sizeof(addr_recv)) == SOCKET_ERROR) {
        log_message("Erreur lors du bind du socket de réception: %d", WSAGetLastError());
        closesocket(sock_recv);
        return 1;
    }

    // Socket pour envoyer en broadcast
    sock_broadcast = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_broadcast == INVALID_SOCKET) {
        log_message("Erreur de création du socket broadcast: %d", WSAGetLastError());
        closesocket(sock_recv);
        return 1;
    }
    int broadcastEnable = 1;
    if (setsockopt(sock_broadcast, SOL_SOCKET, SO_BROADCAST, (char *)&broadcastEnable, sizeof(broadcastEnable)) == SOCKET_ERROR) {
        log_message("Erreur lors de l'activation du broadcast: %d", WSAGetLastError());
        closesocket(sock_recv);
        closesocket(sock_broadcast);
        return 1;
    }
    memset(&addr_broadcast, 0, sizeof(addr_broadcast));
    addr_broadcast.sin_family = AF_INET;
    addr_broadcast.sin_port = htons(BROADCAST_PORT);
    // Adaptation : utiliser le broadcast correspondant à l'interface Wi-Fi (pour 172.20.10.0/28, broadcast=172.20.10.15)
    addr_broadcast.sin_addr.s_addr = inet_addr("172.20.10.15");

    log_message("Thread broadcast_sender actif. Ecoute sur le port %d...", PY_TO_C_PORT);
    int msg_count = 0;
    while (1) {
        int recv_len = recvfrom(sock_recv, buffer, BUFFER_SIZE, 0, (struct sockaddr *)&addr_recv, &addr_len);
        if (recv_len > 0) {
            msg_count++;
            log_message("Message #%d reçu de Python (taille: %d octets)", msg_count, recv_len);
            dump_buffer("Contenu du message", (unsigned char*)buffer, recv_len);
            
            if (sendto(sock_broadcast, buffer, recv_len, 0, (struct sockaddr *)&addr_broadcast, sizeof(addr_broadcast)) == SOCKET_ERROR) {
                log_message("Erreur lors de l'envoi broadcast: %d", WSAGetLastError());
            } else {
                log_message("Message #%d retransmis avec succès en broadcast", msg_count);
            }
        } else if (recv_len == SOCKET_ERROR) {
            log_message("Erreur lors de la réception depuis Python: %d", WSAGetLastError());
        }
    }
    closesocket(sock_recv);
    closesocket(sock_broadcast);
    return 0;
}

DWORD WINAPI forwarder(LPVOID arg) {
    SOCKET sock_broadcast = INVALID_SOCKET, sock_forward = INVALID_SOCKET;
    struct sockaddr_in addr_broadcast, addr_forward, addr_src;
    char buffer[BUFFER_SIZE];
    int addr_len = sizeof(addr_src);

    // Récupérer l'IP locale
    char localHostname[256];
    char localIP[INET_ADDRSTRLEN] = "";
    if (gethostname(localHostname, sizeof(localHostname)) == 0) {
        struct hostent *host = gethostbyname(localHostname);
        if (host && host->h_addr_list[0]) {
            inet_ntop(AF_INET, host->h_addr_list[0], localIP, sizeof(localIP));
            log_message("IP locale détectée: %s", localIP);
        } else {
            log_message("Impossible de déterminer l'IP locale via gethostbyname");
        }
    } else {
        log_message("Échec de gethostname: %d", WSAGetLastError());
    }

    // Socket pour recevoir les broadcasts
    sock_broadcast = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_broadcast == INVALID_SOCKET) {
        log_message("Erreur de création du socket broadcast (recep): %d", WSAGetLastError());
        return 1;
    }
    int reuse = 1;
    if (setsockopt(sock_broadcast, SOL_SOCKET, SO_REUSEADDR, (char *)&reuse, sizeof(reuse)) == SOCKET_ERROR) {
        log_message("Erreur lors de la configuration SO_REUSEADDR: %d", WSAGetLastError());
        closesocket(sock_broadcast);
        return 1;
    }
    memset(&addr_broadcast, 0, sizeof(addr_broadcast));
    addr_broadcast.sin_family = AF_INET;
    addr_broadcast.sin_addr.s_addr = INADDR_ANY;
    addr_broadcast.sin_port = htons(BROADCAST_PORT);
    if (bind(sock_broadcast, (struct sockaddr *)&addr_broadcast, sizeof(addr_broadcast)) == SOCKET_ERROR) {
        log_message("Erreur lors du bind du socket broadcast (recep): %d", WSAGetLastError());
        closesocket(sock_broadcast);
        return 1;
    }

    // Socket pour forwarder vers Python
    sock_forward = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_forward == INVALID_SOCKET) {
        log_message("Erreur de création du socket forward: %d", WSAGetLastError());
        closesocket(sock_broadcast);
        return 1;
    }
    memset(&addr_forward, 0, sizeof(addr_forward));
    addr_forward.sin_family = AF_INET;
    addr_forward.sin_port = htons(C_TO_PY_PORT);
    addr_forward.sin_addr.s_addr = inet_addr("127.0.0.1");

    log_message("Thread forwarder actif. Ecoute des broadcasts sur le port %d...", BROADCAST_PORT);
    int msg_count = 0;
    int local_filtered = 0;
    while (1) {
        int recv_len = recvfrom(sock_broadcast, buffer, BUFFER_SIZE, 0, (struct sockaddr *)&addr_src, &addr_len);
        if (recv_len > 0) {
            msg_count++;
            char src_ip[INET_ADDRSTRLEN];
            strcpy(src_ip, inet_ntoa(addr_src.sin_addr));
            
            log_message("Broadcast #%d reçu de %s:%d (taille: %d octets)", 
                       msg_count, src_ip, ntohs(addr_src.sin_port), recv_len);
            
            // Vérifier si le message provient de la machine locale
            if (strcmp(src_ip, localIP) == 0) {
                local_filtered++;
                log_message("Message #%d filtré (IP locale), total filtré: %d", msg_count, local_filtered);
                continue;
            }
            
            dump_buffer("Contenu du broadcast", (unsigned char*)buffer, recv_len);
            
            if (sendto(sock_forward, buffer, recv_len, 0, (struct sockaddr *)&addr_forward, sizeof(addr_forward)) == SOCKET_ERROR) {
                log_message("Erreur lors du forwarding vers Python: %d", WSAGetLastError());
            } else {
                log_message("Message #%d transféré à Python avec succès", msg_count);
            }
        } else if (recv_len == SOCKET_ERROR) {
            log_message("Erreur lors de la réception de broadcast: %d", WSAGetLastError());
        }
    }
    closesocket(sock_broadcast);
    closesocket(sock_forward);
    return 0;
}

int main() {
    WSADATA wsaData;
    HANDLE hThread1, hThread2;
    DWORD threadId1, threadId2;

    log_message("Démarrage du relais UDP...");

    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        log_message("WSAStartup échoué: %d", WSAGetLastError());
        return 1;
    }

    // Récupération et affichage de l'adresse IP pour vérification
    char localHostname[256];
    struct hostent *host;
    if (gethostname(localHostname, sizeof(localHostname)) == 0) {
        log_message("Nom d'hôte local: %s", localHostname);
        host = gethostbyname(localHostname);
        if (host && host->h_addr_list[0]) {
            char localIP[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, host->h_addr_list[0], localIP, sizeof(localIP));
            log_message("Adresse IP locale: %s", localIP);
        }
    }

    hThread1 = CreateThread(NULL, 0, broadcast_sender, NULL, 0, &threadId1);
    if (hThread1 == NULL) {
        log_message("Erreur lors de la création du thread broadcast_sender: %d", GetLastError());
        WSACleanup();
        return 1;
    }
    hThread2 = CreateThread(NULL, 0, forwarder, NULL, 0, &threadId2);
    if (hThread2 == NULL) {
        log_message("Erreur lors de la création du thread forwarder: %d", GetLastError());
        TerminateThread(hThread1, 0);
        WSACleanup();
        return 1;
    }

    log_message("Relais UDP actif. En attente de messages...");

    WaitForSingleObject(hThread1, INFINITE);
    WaitForSingleObject(hThread2, INFINITE);
    CloseHandle(hThread1);
    CloseHandle(hThread2);
    
    WSACleanup();
    return 0;
}