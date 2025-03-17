import subprocess
import os
from datetime import datetime

import config
# Initialize debug process only if debug mode is enabled
debug_ps = None
print(f"Debug mode: {config.debug_mode}")
if config.debug_mode:
    debug_ps = subprocess.Popen(
        ["powershell.exe", "-NoExit", "-Command", "-"],
        stdin=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

# Chemin du fichier de log dans le dossier TEMP
log_file_path = os.path.join(os.getenv('TEMP'), 'gamelogs.txt')

# Variable pour s'assurer qu'on écrit l'en-tête une seule fois
header_printed = False

# Fonction de log
def debug_print(message, color='White'):
    """
    Fonction pour afficher un message dans la console PowerShell

    :param message: Le message à afficher
    :param color: La couleur du texte (par défaut White)
                  Les couleurs acceptées sont :
                  Black, DarkBlue, DarkGreen, DarkCyan,
                  DarkRed, DarkMagenta, DarkYellow,
                  Gray, DarkGray, Blue, Green, Cyan,
                  Red, Magenta, Yellow, White
    """
    global header_printed

    # Formater la date et l'heure actuelle
    session_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    if config.debug_mode:
        # Si l'en-tête n'a pas encore été imprimé
        if not header_printed:
            if debug_ps.stdin:
                debug_ps.stdin.write(f"Write-Host 'Game Log (session: {session_date})' -ForegroundColor White\n")
                debug_ps.stdin.flush()

            # Écrire l'en-tête dans le fichier de log
            with open(log_file_path, 'a') as log_file:
                log_file.write(f"Game Log (session: {session_date})\n")

            header_printed = True

        # Afficher le message dans la console PowerShell
        if debug_ps.stdin:
            debug_ps.stdin.write(f"Write-Host '>> {message}' -ForegroundColor {color}\n")
            debug_ps.stdin.flush()

    # Écrire le message dans le fichier de log
    with open(log_file_path, 'a') as log_file:
        log_file.write(f"> {message} - {session_date}\n")

# Fonction pour fermer le logger
def close_logger():
    if config.debug_mode and debug_ps.stdin:
        debug_ps.stdin.write("exit\n")
        debug_ps.stdin.close()
        debug_ps.wait()

# Afficher le chemin du fichier de log
print(f"Log file path: {log_file_path}")

