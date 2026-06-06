# LISTE DES TÂCHES DE DÉVELOPPEMENT - SWOS

## Phase 1 : Fondations
- [ ] Configurer l'architecture du projet (dossiers backend/frontend, fichiers de configuration)
- [ ] Installer et configurer PostgreSQL
- [ ] Créer le schéma de la base de données (tables: trucks, docks, robots, zones, missions, decision_logs)
- [ ] Mettre en place le serveur MQTT (ex: Mosquitto) ou configurer le client MQTT
- [ ] Initialiser le backend FastAPI avec les endpoints de base
- [ ] Tester la connexion entre FastAPI, PostgreSQL et MQTT

## Phase 2 : Intégration des datasets et simulation
- [ ] Télécharger le dataset "Logistics Operations and Risk Dataset" depuis Kaggle
- [ ] Nettoyer et préparer le dataset pour l'entraînement de l'Agent ETA (gestion des valeurs manquantes, encodage, normalisation)
- [ ] Générer les données synthétiques initiales pour l'entrepôt:
    - [ ] Créer un script de génération de camions (ID, fournisseur, type de cargaison, ETA simulé, priorité)
    - [ ] Créer un script de génération de quais (ID, statut, compatibilité)
    - [ ] Créer un script de génération de zones de stockage (ID, capacité, type de produit, occupation)
    - [ ] Créer un script de génération de flotte robotique (ID, position, batterie, statut)
    - [ ] Créer un script de génération de missions initiales (source, destination, robot assigné, statut)
- [ ] Mettre en place la simulation d'événements d'arrivée de camions (via un générateur ou en utilisant les données synthétiques)
- [ ] Intégrer les données générées dans la base de données PostgreSQL

## Phase 3 : Développement de l'Agent ETA
- [ ] Sélectionner et implémenter le modèle XGBoost Regressor pour la prédiction d'ETA
- [ ] Entraîner le modèle sur le dataset préparé (Logistics Operations and Risk Dataset)
- [ ] Évaluer le modèle (calculer MAE, RMSE) sur l'ensemble de test
- [ ] Sauvegarder le modèle entraîné sous la forme `eta_model.pkl`
- [ ] Créer l'Agent ETA en tant que service FastAPI avec un endpoint `/predict_eta` qui accepte les caractéristiques d'entrée et retourne l'ETA prédit
- [ ] Tester l'Agent ETA avec des données d'entrée variées

## Phase 4 : Développement des agents métiers
- [ ] Agent Truck:
    - [ ] Implémenter la gestion des informations des camions (CRUD basique)
    - [ ] Intégrer avec la base de données et les topics MQTT (`truck/arrival`, `truck/status`)
- [ ] Agent Dock:
    - [ ] Implémenter le score de disponibilité (disponibilité quai + distance zone stockage + compatibilité cargaison)
    - [ ] Gérer l'occupation et la disponibilité des quais
    - [ ] Intégrer avec la base de données et le topic MQTT `dock/status`
- [ ] Agent Storage:
    - [ ] Implémenter le score de zone de stockage (capacité libre + compatibilité produit + charge actuelle)
    - [ ] Gérer la capacité et l'occupation des zones
    - [ ] Intégrer avec la base de données
- [ ] Agent Robot:
    - [ ] Implémenter le score de robot (disponibilité + batterie + distance mission)
    - [ ] Gérer la position, la batterie, la disponibilité et la mission actuelle des robots
    - [ ] Intégrer avec la base de données et le topic MQTT `robot/status`
- [ ] Agent Mission:
    - [ ] Implémenter la création, le suivi et la clôture des missions logistiques
    - [ ] Gérer le statut des missions (à faire, en cours, complétée)
    - [ ] Intégrer avec la base de données et les topics MQTT (`mission/create`, `mission/update`, `mission/completed`)
- [ ] Assurer la cohérence des données entre les agents via la base de données partagée

## Phase 5 : Développement du Dashboard
- [ ] Initialiser le projet Next.js avec React et Tailwind CSS
- [ ] Créer la page "Camions":
    - [ ] Afficher la liste des camions avec leur ETA, retard éventuel et priorité
    - [ ] Permettre le filtrage et le tri
- [ ] Créer la page "Robots":
    - [ ] Afficher la flotte robotique avec niveau de batterie, position actuelle et mission en cours
    - [ ] Mettre à jour en temps réel via MQTT
- [ ] Créer la page "Quais":
    - [ ] Afficher l'état de chaque quai (libre/occupé) et le camion actuellement affecté
    - [ ] Indiquer la disponibilité pour différents types de cargaison
- [ ] Créer la page "Stockage":
    - [ ] Afficher l'occupation et la capacité de chaque zone de stockage
    - [ ] Indiquer la compatibilité avec différents types de produits
- [ ] Créer la page "Historique":
    - [ ] Afficher le journal des décisions (table `decision_logs`)
    - [ ] Afficher l'historique des missions et des événements
- [ ] Implémenter la navigation entre les pages
- [ ] Appliquer le styling avec Tailwind pour une interface cohérente et responsive

## Phase 6 : Traçabilité et monitoring
- [ ] Implémenter la table `decision_logs` dans PostgreSQL avec les colonnes: decision_id, timestamp, decision_type, decision_reason, agent_source
- [ ] Modifier les agents pour qu'ils écrivent une entrée dans `decision_logs` à chaque décision importante (affectation de quai, sélection de robot, création de mission, etc.)
- [ ] Optionnel: Installer et configurer Grafana pour monitorer les métriques du système
- [ ] Optionnel: Définir des dashboard Grafana pour visualiser les KPIs en temps réel

## Phase 7 : Intégration de la flotte robotique
- [ ] Établir la communication bidirectionnelle avec les robots externes:
    - [ ] S'abonner au topic MQTT `robot/status` pour recevoir les mises à jour de position, batterie et statut
    - [ ] Publier sur le topic `mission/create` pour envoyer de nouvelles missions aux robots
    - [ ] S'abonner au topic `mission/completed` pour recevoir les confirmations d'exécution
- [ ] Implémenter la logique de validation de mission:
    - [ ] Vérifier que le robot a bien atteint la zone destination
    - [ ] Mettre à jour le statut de la mission en "COMPLETED"
    - [ ] Libérer le robot pour de nouvelles missions
- [ ] Tester le flux complet: création de mission → envoi au robot → exécution → retour de statut → mise à jour de l'état

## Phase 8 : Tests globaux et validation
- [ ] Définir des scénarios logistiques de test (ex: arrivée simultanée de plusieurs camions, pics d'activité, ruptures de stock)
- [ ] Exécuter les scénarios et collecter les données de performance
- [ ] Calculer les KPIs:
    - [ ] Temps moyen d'attente des camions
    - [ ] Taux d'occupation des quais
    - [ ] Temps de traitement de la réception (de l'affectation de quai au début de la mission)
    - [ ] Temps d'exécution des missions (du début à la fin)
    - [ ] Taux d'utilisation des robots (pourcentage de temps en mission vs disponibles)
    - [ ] Précision des prédictions ETA (comparer ETA prédit vs heure réelle d'arrivée sur les scénarios de test)
    - [ ] Nombre de conflits évités (ex: tentatives d'affectation à un quai indisponible qui ont été redirigés)
    - [ ] Temps total de traitement logistique (de l'arrivée du camion au stockage définitif)
- [ ] Analyser les résultats et identifier les goulots d'étranglement
- [ ] Ajuster les paramètres des algorithmes de scoring ou les seuils de décision basé sur les résultats des tests
- [ ] Documenter les améliorations apportées suite aux tests

## Tâches transversales
- [ ] Écrire la documentation technique du projet (architecture, API, déploiement)
- [ ] Préparer les scripts de déploiement avec Docker (Dockerfiles, docker-compose.yml)
- [ ] Mettre en place un système de logging centralisé pour le débogage
- [ ] Réviser la sécurité de base (authentification légère pour les endpoints internes si nécessaire)