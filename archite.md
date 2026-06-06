# SMART WAREHOUSE ORCHESTRATION SYSTEM (SWOS)

## Architecture détaillée du projet

### 1. Vision du projet
Le projet consiste à développer un système intelligent d'orchestration logistique pour un entrepôt connecté.
L'objectif principal n'est pas de développer les robots eux-mêmes mais de développer le système intelligent qui coordonne :

* les camions
* les quais
* les zones de stockage
* les missions logistiques
* les robots existants

Le système doit être capable de :

* prédire l'heure d'arrivée des camions (ETA)
* affecter les quais de manière dynamique
* choisir le robot optimal
* préparer les zones de stockage
* générer les missions logistiques
* assurer la traçabilité complète des décisions

---

### 2. Périmètre du projet

**Inclus**
* Architecture Multi-Agent
* Intelligence décisionnelle
* Prédiction ETA
* Gestion des quais
* Gestion des missions
* Gestion des robots
* Dashboard temps réel
* Base de données
* Traçabilité

**Exclus**
* Navigation robotique
* SLAM
* Contrôle bas niveau des robots
* Vision robotique
* Gazebo
* ROS2 interne

Les robots sont considérés comme des ressources externes déjà opérationnelles.

---

### 3. Architecture Multi-Agent

**Agent Coordinateur**
* Responsabilité : coordonner tous les agents, recevoir les événements, prendre les décisions finales et créer les missions
* Technologie : Python, FastAPI

**Agent ETA**
* Responsabilité : prédire l'heure d'arrivée des camions
* Entrées : distance, trafic, météo, historique, type de route
* Sortie : ETA estimée
* Technologie : Scikit-Learn, XGBoost
* Note : Seul agent utilisant du Machine Learning

**Agent Truck**
* Responsabilité : gérer les informations des camions
* Données : ID, fournisseur, ETA, cargaison, priorité

**Agent Dock**
* Responsabilité : gérer les quais
* Fonctions : occupation, disponibilité, compatibilité

**Agent Storage**
* Responsabilité : gérer les zones de stockage
* Fonctions : capacité, saturation, disponibilité

**Agent Robot**
* Responsabilité : gérer la flotte robotique
* Informations : position, batterie, disponibilité, mission
* Exemple : Robot R2 (Position: Zone_2, Batterie: 87%, Statut: AVAILABLE)

**Agent Mission**
* Responsabilité : créer, suivre, clôturer les missions
* Exemple : Transport Palette_001 (Zone_2 -> Zone_4), Robot: R2, Statut: COMPLETED

---

### 4. Architecture Technique

* **Frontend :** Next.js, React, Tailwind
* **Backend :** FastAPI
* **Base de données :** PostgreSQL
* **Communication :** MQTT
* **Monitoring :** Grafana (optionnel)
* **Conteneurisation :** Docker

---

### 5. Communication

**Topics MQTT :**
* truck/arrival
* truck/status
* dock/status
* robot/status
* mission/create
* mission/update
* mission/completed
* alert/new

---

### 6. Base de données

**Tables :**
* **trucks :** truck_id, supplier, cargo_type, eta, priority, status
* **docks :** dock_id, status, current_truck
* **robots :** robot_id, battery, position, status
* **zones :** zone_id, capacity, occupied
* **missions :** mission_id, robot_id, source_zone, destination_zone, status, created_at, completed_at
* **decision_logs :** decision_id, timestamp, decision_type, decision_reason, agent_source

---

### 7. Dashboard

* **Page Camions :** ETA, retard, priorité
* **Page Robots :** batterie, position, mission
* **Page Quais :** état, disponibilité
* **Page Stockage :** occupation, capacité
* **Page Historique :** décisions, missions, événements

---

### 8. Intelligence Artificielle

**Agent ETA**
* Modèle recommandé : XGBoost Regressor
* Entrées : distance, trafic, météo, historique, heure départ
* Sortie : ETA
* Métriques : MAE, RMSE

---

### 9. Datasets recommandés

* **Dataset principal :** Logistics and Supply Chain Dataset (Utilisation: simulation globale, trafic, livraisons, fournisseurs, entrepôts) - Lien: https://www.kaggle.com/datasets/datasetengineer/logistics-and-supply-chain-dataset
* **Dataset ETA :** Logistics Operations and Risk Dataset (Utilisation: entraînement Agent ETA, Variables utiles: Traffic_Level, ETA_Variation, Route_Risk, Driver_Fatigue, Delivery_Time_Deviation) - Lien: https://www.kaggle.com/datasets/programmer3/logistics-operations-and-risk-dataset
* **Dataset opérations logistiques :** Logistics Operations Database (Utilisation: simulation du système, génération des événements, création des camions, scénarios logistiques) - Lien: https://www.kaggle.com/datasets/yogape/logistics-operations-database

---

### 10. Stratégie d'entraînement

**Agent ETA**
* Dataset : Logistics Operations and Risk Dataset
* Prétraitement : suppression valeurs manquantes, encodage catégories, normalisation
* Séparation : 80% train, 20% test
* Modèle : XGBoost Regressor
* Sauvegarde : eta_model.pkl

---

### 11. Agents sans IA

Les autres agents utilisent : Rules + Scoring + Optimization
* **Agent Dock - Score :** Disponibilité quai + Distance zone stockage + Compatibilité cargaison
* **Agent Robot - Score :** Disponibilité + Batterie + Distance mission
* **Agent Storage - Score :** Capacité libre + Compatibilité produit + Charge actuelle

---

### 12. Roadmap

* **Phase 1 :** Architecture, Base PostgreSQL, MQTT, FastAPI
* **Phase 2 :** Intégration datasets, Nettoyage, Préparation, Simulation
* **Phase 3 :** Développement Agent ETA, Entraînement, Évaluation, Déploiement
* **Phase 4 :** Développement agents métiers (Truck, Dock, Storage, Robot, Mission)
* **Phase 5 :** Développement Dashboard, Visualisation, Traçabilité, Monitoring
* **Phase 6 :** Intégration flotte robotique, Réception missions, Retour statut, Validation mission
* **Phase 7 :** Tests globaux, Scénarios, Mesures KPI, Validation finale

---

### 13. KPI

* Temps moyen attente camion
* Taux occupation quais
* Temps traitement réception
* Temps exécution mission
* Taux utilisation robots
* Précision ETA
* Nombre conflits évités
* Temps total de traitement logistique

---

### 14. Résultat final attendu

Le système doit être capable de :
1. Prédire l'arrivée d'un camion.
2. Choisir le meilleur quai.
3. Choisir la meilleure zone.
4. Sélectionner le robot optimal.
5. Créer automatiquement la mission.
6. Recevoir le retour d'exécution.
7. Mettre à jour l'état global de l'entrepôt.
8. Conserver une traçabilité complète de toutes les décisions.