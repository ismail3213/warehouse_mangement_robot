# PLAN DE DÉVELOPPEMENT DU SYSTÈME D'ORCHESTRATION LOGISTIQUE INTELLIGENT (SWOS)

## 1. Vue d'ensemble du projet
Le projet consiste à développer un système intelligent d'orchestration logistique pour un entrepôt connecté, basé sur l'architecture décrite dans `archite.md`.

**Objectif principal** : Développer le système intelligent qui coordonne :
- les camions
- les quais
- les zones de stockage
- les missions logistiques
- les robots existants (considérés comme des ressources externes déjà opérationnelles)

Le système doit être capable de :
1. Prédire l'heure d'arrivée des camions (ETA)
2. Affecter les quais de manière dynamique
3. Choisir le robot optimal
4. Préparer les zones de stockage
5. Générer les missions logistiques
6. Assurer la traçabilité complète des décisions

## 2. Architecture Multi-Agent détaillée

### Agents et leurs responsabilités
- **Agent Coordinateur** : Coordonne tous les agents, reçoit les événements, prend les décisions finales et crée les missions. (Technologie : Python, FastAPI)
- **Agent ETA** : Prédit l'heure d'arrivée des camions. Utilise du Machine Learning (XGBoost Regressor). Entrées : distance, trafic, météo, historique, type de route. Sortie : ETA estimée.
- **Agent Truck** : Gère les informations des camions (ID, fournisseur, ETA, cargaison, priorité).
- **Agent Dock** : Gère les quais (occupation, disponibilité, compatibilité).
- **Agent Storage** : Gère les zones de stockage (capacité, saturation, disponibilité).
- **Agent Robot** : Gère la flotte robotique (position, batterie, disponibilité, mission).
- **Agent Mission** : Crée, suit, clôture les missions.

### Règles de scoring pour les agents sans IA
- **Agent Dock** : Score = Disponibilité quai + Distance zone stockage + Compatibilité cargaison
- **Agent Robot** : Score = Disponibilité + Batterie + Distance mission
- **Agent Storage** : Score = Capacité libre + Compatibilité produit + Charge actuelle

## 3. Architecture Technique
- **Frontend** : Next.js, React, Tailwind
- **Backend** : FastAPI
- **Base de données** : PostgreSQL
- **Communication** : MQTT (topics définis dans archite.md)
- **Monitoring** : Grafana (optionnel)
- **Conteneurisation** : Docker

## 4. Stratégie de données

### 4.1 Données réelles pour l'Agent ETA
- **Dataset principal** : Logistics Operations and Risk Dataset (Kaggle)
  - Variables utiles : Traffic_Level, ETA_Variation, Route_Risk, Driver_Fatigue, Delivery_Time_Deviation
  - Utilisation : Entraînement du modèle XGBoost Regressor pour prédire l'ETA.
- **Prétraitement** : Suppression des valeurs manquantes, encodage des variables catégorielles, normalisation.
- **Séparation** : 80% train, 20% test.
- **Sauvegarde du modèle** : `eta_model.pkl`

### 4.2 Génération de données synthétiques pour les autres agents
Pour alimenter les agents Dock, Storage, Robot et Mission, nous générerons un dataset synthétique d'entrepôt basé sur les flux logistiques réels des autres datasets Kaggle mentionnés.

#### Sources d'inspiration pour la génération synthétique :
1. **Logistics and Supply Chain Dataset** (Kaggle) : Pour la simulation globale du trafic, des livraisons, des fournisseurs et des entrepôts.
2. **Logistics Operations Database** (Kaggle) : Pour la simulation du système, génération des événements, création des camions et scénarios logistiques.

#### Méthodologie de génération :
- **Camions** : Générer des entrées de camions avec ID, fournisseur, type de cargaison, ETA (prédit par l'agent ETA ou simulé pour l'initialisation), priorité, statut.
- **Quais** : Créer un ensemble de quais avec ID, statut (libre/occupé), compatibilité avec certains types de cargaison.
- **Zones de stockage** : Définir des zones avec ID, capacité, type de produit accepté, niveau d'occupation actuel.
- **Robots** : Créer une flotte de robots avec ID, position initiale, niveau de batterie, statut (disponible/en mission), capacité de charge.
- **Missions** : Générer des missions de transport (source_zone -> destination_zone) associées à un robot, avec statut (à faire, en cours, complétée).

#### Contraintes de génération :
- Les données synthétiques doivent être cohérentes avec les flux logistiques réels (ex : les temps de trajet entre zones doivent être réalistes).
- Les datasets synthétiques seront stockés sous forme de fichiers CSV ou JSON pour initialiser la base de données PostgreSQL.
- Un script de génération sera créé plus tard (mais pas maintenant, conformément aux contraintes).

## 5. Phases de développement (adaptées de la roadmap)

### Phase 1 : Fondations
- Architecture, base de données PostgreSQL, mise en place de MQTT, développement du backend FastAPI.
- Définition du schéma de la base de données (tables : trucks, docks, robots, zones, missions, decision_logs).

### Phase 2 : Intégration des datasets et simulation
- Nettoyage et préparation des datasets réels (Logistics Operations and Risk Dataset pour ETA).
- Génération initiale des données synthétiques pour l'entrepôt (robots, quais, zones, missions).
- Mise en place de la simulation d'événements (arrivée de camions, etc.).

### Phase 3 : Développement de l'Agent ETA
- Entraînement du modèle XGBoost sur le dataset réel.
- Évaluation (MAE, RMSE) et déploiement du modèle.
- Création de l'Agent ETA en tant que service FastAPI qui fournit des prédictions ETA.

### Phase 4 : Développement des agents métiers
- Agents Truck, Dock, Storage, Robot, Mission.
- Implémentation des règles de scoring et de prise de décision.
- Intégration avec la base de données et MQTT.

### Phase 5 : Développement du Dashboard
- Pages : Camions (ETA, retard, priorité), Robots (batterie, position, mission), Quais (état, disponibilité), Stockage (occupation, capacité), Historique (décisions, missions, événements).
- Technologies : Next.js, React, Tailwind.

### Phase 6 : Traçabilité et monitoring
- Implémentation de la table `decision_logs` pour tracer toutes les décisions.
- Ajout du monitoring optionnel avec Grafana.

### Phase 7 : Intégration de la flotte robotique
- Connexion avec les robots externes (via MQTT ou API) pour recevoir les mises à jour de statut et envoyer les missions.
- Validation de l'exécution des missions.

### Phase 8 : Tests globaux et validation
- Tests d'intégration sur des scénarios logistiques variés.
- Mesure des KPIs : temps moyen d'attente camion, taux d'occupation des quais, temps de traitement réception, temps d'exécution mission, taux d'utilisation des robots, précision ETA, nombre de conflits évités, temps total de traitement logistique.
- Ajustements basés sur les résultats.

## 6. KPIs à surveiller
- Temps moyen d'attente des camions
- Taux d'occupation des quais
- Temps de traitement de la réception
- Temps d'exécution des missions
- Taux d'utilisation des robots
- Précision des prédictions ETA
- Nombre de conflits évités (ex : affecté à un quai indisponible)
- Temps total de traitement logistique (de l'arrivée au stockage)

## 7. Résultat final attendu
Un système capable de :
1. Prédire l'arrivée d'un camion.
2. Choisir le meilleur quai.
3. Choisir la meilleure zone de stockage.
4. Sélectionner le robot optimal.
5. Créer automatiquement la mission de transport.
6. Recevoir le retour d'exécution du robot.
7. Mettre à jour l'état global de l'entrepôt.
8. Conserver une traçabilité complète de toutes les décisions.

## 8. Prochaine étape : TASK.md
Le fichier TASK.md contiendra la liste détaillée des tâches à réaliser, organisée par phase, que nous pourrons cocher au fur et à mesure de l'avancement.