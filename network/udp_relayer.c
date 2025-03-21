#define WIN32_LEAN_AND_MEAN
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <iphlpapi.h>
#include <time.h>

#pragma comment(lib, "Ws2_32.lib")
#pragma comment(lib, "iphlpapi.lib")

#define PY_TO_C_PORT 6000      // Port d'écoute pour les messages venant de Python
#define BROADCAST_PORT 6001    // Port pour le broadcast UDP
#define C_TO_PY_PORT 6002      // Port de transfert vers Python locale
#define BUFFER_SIZE 65507
#define DEBUG 1                // Flag pour activer/désactiver les logs détaillés
#define WIFI_SUBNET "172.20.10" // Préfixe du subnet WiFi à filtrer

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

// Fonction pour afficher le contenu binaire du buffer
void dump_buffer(const char *prefix, const unsigned char *buffer, int length) {
    if (DEBUG > 1) {
        log_message("%s (%d bytes):", prefix, length);
        for (int i = 0; i < (length > 32 ? 32 : length); i++) {
            if (i % 16 == 0) printf("\n  ");
            printf("%02X ", buffer[i]);
        }
        printf("\n");
    }
}

// Fonction pour obtenir l'adresse IP Wi-Fi
int get_wifi_ip(char *wifi_ip, int max_len) {
    PIP_ADAPTER_INFO pAdapterInfo;
    PIP_ADAPTER_INFO pAdapter = NULL;
    DWORD dwRetVal = 0;
    
    ULONG ulOutBufLen = sizeof(IP_ADAPTER_INFO);
    pAdapterInfo = (IP_ADAPTER_INFO *) malloc(sizeof(IP_ADAPTER_INFO));
    if (pAdapterInfo == NULL) {
        log_message("Erreur d'allocation mémoire pour IP_ADAPTER_INFO");
        return 0;
    }

    if (GetAdaptersInfo(pAdapterInfo, &ulOutBufLen) == ERROR_BUFFER_OVERFLOW) {
        free(pAdapterInfo);
        pAdapterInfo = (IP_ADAPTER_INFO *) malloc(ulOutBufLen);
        if (pAdapterInfo == NULL) {
            log_message("Erreur d'allocation mémoire pour IP_ADAPTER_INFO (2)");
            return 0;
        }
    }

    if ((dwRetVal = GetAdaptersInfo(pAdapterInfo, &ulOutBufLen)) == NO_ERROR) {
        pAdapter = pAdapterInfo;
        int found = 0;
        while (pAdapter) {
            // Vérifier l'adresse IP pour voir si elle est sur le subnet Wi-Fi
            IP_ADDR_STRING *pIpAddrString = &pAdapter->IpAddressList;
            while (pIpAddrString) {
                if (strncmp(pIpAddrString->IpAddress.String, WIFI_SUBNET, strlen(WIFI_SUBNET)) == 0) {
                    strncpy(wifi_ip, pIpAddrString->IpAddress.String, max_len);
                    log_message("Trouvé interface Wi-Fi: %s avec IP: %s", 
                              pAdapter->Description, pIpAddrString->IpAddress.String);
                    found = 1;
                    break;
                }
                pIpAddrString = pIpAddrString->Next;
            }
            if (found) break;
            pAdapter = pAdapter->Next;
        }
        
        if (!found) {
            log_message("Aucune interface Wi-Fi avec le préfixe %s trouvée", WIFI_SUBNET);
            
            // Log toutes les interfaces pour diagnostic
            pAdapter = pAdapterInfo;
            log_message("Interfaces réseau disponibles:");
            while (pAdapter) {
                log_message("  Nom: %s", pAdapter->Description);
                IP_ADDR_STRING *pIpAddrString = &pAdapter->IpAddressList;
                while (pIpAddrString) {
                    log_message("    IP: %s", pIpAddrString->IpAddress.String);
                    pIpAddrString = pIpAddrString->Next;
                }
                pAdapter = pAdapter->Next;
            }
            free(pAdapterInfo);
            return 0;
        }
    } else {
        log_message("GetAdaptersInfo échoué avec erreur: %d", dwRetVal);
        free(pAdapterInfo);
        return 0;
    }

    free(pAdapterInfo);
    return 1;
}

DWORD WINAPI broadcast_sender(LPVOID arg) {
    SOCKET sock_recv = INVALID_SOCKET, sock_broadcast = INVALID_SOCKET;
    struct sockaddr_in addr_recv, addr_broadcast;
    char buffer[BUFFER_SIZE];
    int addr_len = sizeof(addr_recv);
    WSAEVENT hEvent;
    WSANETWORKEVENTS events;

    // Socket pour recevoir depuis Python
    sock_recv = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_recv == INVALID_SOCKET) {
        log_message("Erreur de création du socket de réception: %d", WSAGetLastError());
        return 1;
    }
    
    // Mettre le socket en mode non-bloquant pour éviter le blocage à 100 messages
    unsigned long mode = 1;  // 1 = non-bloquant
    if (ioctlsocket(sock_recv, FIONBIO, &mode) != 0) {
        log_message("Erreur lors du passage en mode non-bloquant: %d", WSAGetLastError());
    }
    
    // Créer un événement pour le socket
    hEvent = WSACreateEvent();
    if (hEvent == WSA_INVALID_EVENT) {
        log_message("Erreur lors de la création de l'événement: %d", WSAGetLastError());
        closesocket(sock_recv);
        return 1;
    }
    
    // Associer l'événement au socket
    if (WSAEventSelect(sock_recv, hEvent, FD_READ) == SOCKET_ERROR) {
        log_message("Erreur lors de l'association de l'événement: %d", WSAGetLastError());
        WSACloseEvent(hEvent);
        closesocket(sock_recv);
        return 1;
    }
    
    memset(&addr_recv, 0, sizeof(addr_recv));
    addr_recv.sin_family = AF_INET;
    addr_recv.sin_addr.s_addr = INADDR_ANY;
    addr_recv.sin_port = htons(PY_TO_C_PORT);

    if (bind(sock_recv, (struct sockaddr *)&addr_recv, sizeof(addr_recv)) == SOCKET_ERROR) {
        log_message("Erreur lors du bind du socket de réception: %d", WSAGetLastError());
        WSACloseEvent(hEvent);
        closesocket(sock_recv);
        return 1;
    }

    // Socket pour envoyer en broadcast
    sock_broadcast = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_broadcast == INVALID_SOCKET) {
        log_message("Erreur de création du socket broadcast: %d", WSAGetLastError());
        WSACloseEvent(hEvent);
        closesocket(sock_recv);
        return 1;
    }
    int broadcastEnable = 1;
    if (setsockopt(sock_broadcast, SOL_SOCKET, SO_BROADCAST, (char *)&broadcastEnable, sizeof(broadcastEnable)) == SOCKET_ERROR) {
        log_message("Erreur lors de l'activation du broadcast: %d", WSAGetLastError());
        WSACloseEvent(hEvent);
        closesocket(sock_recv);
        closesocket(sock_broadcast);
        return 1;
    }
    memset(&addr_broadcast, 0, sizeof(addr_broadcast));
    addr_broadcast.sin_family = AF_INET;
    addr_broadcast.sin_port = htons(BROADCAST_PORT);
    // Adresse broadcast pour le réseau Wi-Fi (172.20.10.0/28)
    addr_broadcast.sin_addr.s_addr = inet_addr("172.20.10.15");

    log_message("Thread broadcast_sender actif. Ecoute sur le port %d...", PY_TO_C_PORT);
    int msg_count = 0;
    while (1) {
        // Attendre un événement ou un timeout
        DWORD ret = WSAWaitForMultipleEvents(1, &hEvent, FALSE, 100, FALSE);
        
        if (ret == WSA_WAIT_EVENT_0) {
            // Réinitialiser l'événement
            WSAEnumNetworkEvents(sock_recv, hEvent, &events);
            
            if (events.lNetworkEvents & FD_READ) {
                do {
                    int recv_len = recvfrom(sock_recv, buffer, BUFFER_SIZE, 0, 
                                          (struct sockaddr *)&addr_recv, &addr_len);
                    
                    if (recv_len > 0) {
                        msg_count++;
                        log_message("Message #%d reçu de Python (taille: %d octets)", msg_count, recv_len);
                        dump_buffer("Contenu du message", (unsigned char*)buffer, recv_len);
                        
                        if (sendto(sock_broadcast, buffer, recv_len, 0, 
                                 (struct sockaddr *)&addr_broadcast, sizeof(addr_broadcast)) == SOCKET_ERROR) {
                            log_message("Erreur lors de l'envoi broadcast: %d", WSAGetLastError());
                        } else {
                            log_message("Message #%d retransmis avec succès en broadcast", msg_count);
                        }
                    } else if (recv_len == SOCKET_ERROR) {
                        int err = WSAGetLastError();
                        if (err != WSAEWOULDBLOCK) {
                            log_message("Erreur lors de la réception depuis Python: %d", err);
                        }
                        break;
                    }
                } while (1); // Continue jusqu'à WSAEWOULDBLOCK
            }
        }
        
        // Dormir brièvement pour éviter une utilisation CPU à 100%
        Sleep(10);
    }
    
    WSACloseEvent(hEvent);
    closesocket(sock_recv);
    closesocket(sock_broadcast);
    return 0;
}

DWORD WINAPI forwarder(LPVOID arg) {
    SOCKET sock_broadcast = INVALID_SOCKET, sock_forward = INVALID_SOCKET;
    struct sockaddr_in addr_broadcast, addr_forward, addr_src;
    char buffer[BUFFER_SIZE];
    int addr_len = sizeof(addr_src);
    WSAEVENT hEvent;
    WSANETWORKEVENTS events;

    // Récupérer l'IP Wi-Fi locale
    char wifiIP[INET_ADDRSTRLEN] = "";
    if (!get_wifi_ip(wifiIP, sizeof(wifiIP))) {
        // Essai de secours avec la méthode classique
        log_message("Tentative de récupération IP par méthode standard...");
        char localHostname[256];
        if (gethostname(localHostname, sizeof(localHostname)) == 0) {
            struct hostent *host = gethostbyname(localHostname);
            if (host && host->h_addr_list[0]) {
                inet_ntop(AF_INET, host->h_addr_list[0], wifiIP, sizeof(wifiIP));
                log_message("IP locale standard: %s (attention, peut ne pas être Wi-Fi)", wifiIP);
            } else {
                log_message("AVERTISSEMENT: Impossible d'obtenir l'IP locale, filtrage désactivé!");
                strcpy(wifiIP, "0.0.0.0");  // IP invalide pour désactiver le filtrage
            }
        }
    }

    // Socket pour recevoir les broadcasts
    sock_broadcast = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_broadcast == INVALID_SOCKET) {
        log_message("Erreur de création du socket broadcast (recep): %d", WSAGetLastError());
        return 1;
    }
    
    // Mettre le socket en mode non-bloquant
    unsigned long mode = 1;
    if (ioctlsocket(sock_broadcast, FIONBIO, &mode) != 0) {
        log_message("Erreur lors du passage en mode non-bloquant: %d", WSAGetLastError());
    }
    
    // Créer un événement pour le socket
    hEvent = WSACreateEvent();
    if (hEvent == WSA_INVALID_EVENT) {
        log_message("Erreur lors de la création de l'événement: %d", WSAGetLastError());
        closesocket(sock_broadcast);
        return 1;
    }
    
    // Associer l'événement au socket
    if (WSAEventSelect(sock_broadcast, hEvent, FD_READ) == SOCKET_ERROR) {
        log_message("Erreur lors de l'association de l'événement: %d", WSAGetLastError());
        WSACloseEvent(hEvent);
        closesocket(sock_broadcast);
        return 1;
    }
    
    int reuse = 1;
    if (setsockopt(sock_broadcast, SOL_SOCKET, SO_REUSEADDR, (char *)&reuse, sizeof(reuse)) == SOCKET_ERROR) {
        log_message("Erreur lors de la configuration SO_REUSEADDR: %d", WSAGetLastError());
        WSACloseEvent(hEvent);
        closesocket(sock_broadcast);
        return 1;
    }
    memset(&addr_broadcast, 0, sizeof(addr_broadcast));
    addr_broadcast.sin_family = AF_INET;
    addr_broadcast.sin_addr.s_addr = INADDR_ANY;
    addr_broadcast.sin_port = htons(BROADCAST_PORT);
    if (bind(sock_broadcast, (struct sockaddr *)&addr_broadcast, sizeof(addr_broadcast)) == SOCKET_ERROR) {
        log_message("Erreur lors du bind du socket broadcast (recep): %d", WSAGetLastError());
        WSACloseEvent(hEvent);
        closesocket(sock_broadcast);
        return 1;
    }

    // Socket pour forwarder vers Python
    sock_forward = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_forward == INVALID_SOCKET) {
        log_message("Erreur de création du socket forward: %d", WSAGetLastError());
        WSACloseEvent(hEvent);
        closesocket(sock_broadcast);
        return 1;
    }
    memset(&addr_forward, 0, sizeof(addr_forward));
    addr_forward.sin_family = AF_INET;
    addr_forward.sin_port = htons(C_TO_PY_PORT);
    addr_forward.sin_addr.s_addr = inet_addr("127.0.0.1");

    log_message("Thread forwarder actif. Ecoute des broadcasts sur le port %d...", BROADCAST_PORT);
    log_message("Filtrage des messages provenant de l'IP Wi-Fi: %s", wifiIP);
    
    int msg_count = 0;
    int local_filtered = 0;
    while (1) {
        // Attendre un événement ou un timeout
        DWORD ret = WSAWaitForMultipleEvents(1, &hEvent, FALSE, 100, FALSE);
        
        if (ret == WSA_WAIT_EVENT_0) {
            // Réinitialiser l'événement
            WSAEnumNetworkEvents(sock_broadcast, hEvent, &events);
            
            if (events.lNetworkEvents & FD_READ) {
                do {
                    int recv_len = recvfrom(sock_broadcast, buffer, BUFFER_SIZE, 0, 
                                          (struct sockaddr *)&addr_src, &addr_len);
                    
                    if (recv_len > 0) {
                        msg_count++;
                        char src_ip[INET_ADDRSTRLEN];
                        strcpy(src_ip, inet_ntoa(addr_src.sin_addr));
                        
                        log_message("Broadcast #%d reçu de %s:%d (taille: %d octets)", 
                                   msg_count, src_ip, ntohs(addr_src.sin_port), recv_len);
                        
                        // Vérifier si le message provient de notre IP Wi-Fi
                        if (strcmp(src_ip, wifiIP) == 0) {
                            local_filtered++;
                            log_message("Message #%d filtré (IP Wi-Fi locale), total filtré: %d", 
                                      msg_count, local_filtered);
                            continue;
                        }
                        
                        dump_buffer("Contenu du broadcast", (unsigned char*)buffer, recv_len);
                        
                        if (sendto(sock_forward, buffer, recv_len, 0, 
                                 (struct sockaddr *)&addr_forward, sizeof(addr_forward)) == SOCKET_ERROR) {
                            log_message("Erreur lors du forwarding vers Python: %d", WSAGetLastError());
                        } else {
                            log_message("Message #%d transféré à Python avec succès", msg_count);
                        }
                    } else if (recv_len == SOCKET_ERROR) {
                        int err = WSAGetLastError();
                        if (err != WSAEWOULDBLOCK) {
                            log_message("Erreur lors de la réception de broadcast: %d", err);
                        }
                        break;
                    }
                } while (1); // Continue jusqu'à WSAEWOULDBLOCK
            }
        }
        
        // Dormir brièvement pour éviter une utilisation CPU à 100%
        Sleep(10);
    }
    
    WSACloseEvent(hEvent);
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

    // Récupération et affichage de l'adresse IP Wi-Fi pour vérification
    char wifiIP[INET_ADDRSTRLEN] = "";
    get_wifi_ip(wifiIP, sizeof(wifiIP));

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