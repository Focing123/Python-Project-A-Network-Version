# 🌟 **Projet Python Réseau : Simulateur Multi-Joueurs Réparti** 🌟

---

## 🚀 **Introduction**

Bienvenue dans le projet **Simulateur Multi-Joueurs Réparti** ! Ce projet vise à étendre un simulateur existant en permettant à plusieurs joueurs de s'affronter dans un environnement réparti à grande échelle. L'objectif est de créer un système où chaque joueur possède une copie locale de la simulation, interagit avec son IA, et partage les changements d'état avec les autres joueurs sans passer par un serveur centralisé. 🎮

---

## 🎯 **Objectifs du Projet**

- **Répartition des Simulations** : Chaque joueur a une copie locale de la simulation et peut interagir avec son IA.
- **Cohérence Répartie** : Les changements d'état sont partagés entre les joueurs sans serveur centralisé.
- **Concurrence et Interaction** : Les joueurs peuvent interagir de manière concurrente sur des objets partagés.
- **Jouabilité** : Offrir une expérience de jeu fluide et attrayante avec des règles de simulation bien définies.

---

## 🛠️ **Technologies Utilisées**

- **Python** : Pour l'algorithmique de simulation et la gestion des IA.
- **C** : Pour la partie réseau et la communication entre les processus.
- **API Socket** : Pour la communication réseau entre les joueurs.
- **Mécanismes de Synchronisation** : Pour garantir la cohérence des données partagées.
- **Git** : Pour la gestion de version et la collaboration en équipe.

---

## 🎮 **Fonctionnalités**

### **1. Simulation Répartie**
- Chaque joueur a une copie locale de la simulation.
- Les changements d'état sont partagés en temps réel entre les joueurs.

### **2. Intelligence Artificielle**
- Chaque joueur a une IA qui interagit avec les éléments de la simulation.
- Les IA peuvent attaquer, coopérer ou interagir avec les ressources des autres joueurs.

### **3. Concurrence et Cohérence**
- Les joueurs peuvent interagir de manière concurrente sur des objets partagés.
- La cohérence est garantie par des mécanismes de synchronisation et de propriété réseau.

### **4. Jouabilité**
- Règles de simulation communes à tous les joueurs.
- Création dynamique de mondes et de ressources.
- Gestion des édifices et des ressources par les joueurs.

---

## 📜 **Licence**

Ce projet est sous **licence MIT**. Pour plus d'informations, consultez le fichier **LICENSE**.

---