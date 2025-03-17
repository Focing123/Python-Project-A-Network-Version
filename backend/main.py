import os
import sys
import argparse

import config

# Ajouter le chemin du projet à sys.path pour ne pas avoir à le faire dans le terminal
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from backend.Starter_File import start_menu

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Launch game with or without save and debug mode.")
    parser.add_argument(
        "-s", "--save", 
        type=str, 
        help="Path to save file (optional)."
    )
    parser.add_argument(
        "-d", "--debug", 
        action="store_true", 
        default=False, 
        help="Enable debug mode (default=False)."
    )
    args = parser.parse_args()
    config.debug_mode = args.debug
    start_menu(save_file=args.save)
