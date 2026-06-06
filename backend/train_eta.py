import os
import json
import joblib
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error

def train_model():
    print("Starting ETA model training pipeline...")
    
    # Try to locate the Kaggle dataset if it exists
    dataset_path = "logistics_operations_and_risk.csv"
    
    if os.path.exists(dataset_path):
        print(f"Found dataset at {dataset_path}. Loading...")
        df = pd.read_csv(dataset_path)
        # Parse/preprocess real dataset
        # Map categories to numbers if any
        # Assuming columns: Distance, Traffic_Level, Weather, Route_Risk, Driver_Fatigue, ETA_Minutes
    else:
        print("Dataset file 'logistics_operations_and_risk.csv' not found. Generating synthetic logistics dataset...")
        np.random.seed(42)
        n_samples = 2000
        
        # Generate synthetic features
        distance = np.random.uniform(10, 400, n_samples)  # 10 to 400 miles
        traffic_level = np.random.choice([0, 1, 2], n_samples, p=[0.5, 0.35, 0.15])  # 0: Low, 1: Medium, 2: High
        weather = np.random.choice([0, 1, 2], n_samples, p=[0.6, 0.3, 0.1])       # 0: Sunny, 1: Rainy, 2: Stormy
        route_risk = np.random.choice([0, 1, 2], n_samples, p=[0.7, 0.2, 0.1])     # 0: Low, 1: Medium, 2: High
        driver_fatigue = np.random.choice([0, 1], n_samples, p=[0.85, 0.15])       # 0: No, 1: Yes
        
        # Base travel time at 55 mph
        base_time_mins = (distance / 55.0) * 60.0
        
        # Delays
        traffic_delay = traffic_level * 25.0  # up to 50 mins delay
        weather_delay = weather * 20.0        # up to 40 mins delay
        risk_delay = route_risk * 15.0        # up to 30 mins delay
        fatigue_delay = driver_fatigue * 10.0  # up to 10 mins delay
        
        # Noise
        noise = np.random.normal(0, 8, n_samples)
        
        # Target ETA in minutes
        eta_minutes = base_time_mins + traffic_delay + weather_delay + risk_delay + fatigue_delay + noise
        # Make sure no negative values
        eta_minutes = np.clip(eta_minutes, 10, None)
        
        df = pd.DataFrame({
            'distance': distance,
            'traffic_level': traffic_level,
            'weather': weather,
            'route_risk': route_risk,
            'driver_fatigue': driver_fatigue,
            'eta_minutes': eta_minutes
        })
        
        # Save synthetic dataset for reference
        df.to_csv("synthetic_logistics_data.csv", index=False)
        print("Generated synthetic dataset and saved as 'synthetic_logistics_data.csv'.")
    
    # Split features and target
    X = df[['distance', 'traffic_level', 'weather', 'route_risk', 'driver_fatigue']]
    y = df['eta_minutes']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print(f"Training set size: {len(X_train)} samples")
    print(f"Testing set size: {len(X_test)} samples")
    
    # Define XGBoost model
    model = XGBRegressor(
        n_estimators=100,
        learning_rate=0.08,
        max_depth=5,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    
    # Train
    print("Training XGBoost Regressor...")
    model.fit(X_train, y_train)
    
    # Evaluate
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    
    print("\n--- Model Evaluation ---")
    print(f"Mean Absolute Error (MAE): {mae:.2f} minutes")
    print(f"Root Mean Squared Error (RMSE): {rmse:.2f} minutes")
    print("------------------------\n")
    
    # Save the model
    model_path = "eta_model.pkl"
    joblib.dump(model, model_path)
    print(f"Model successfully saved to '{model_path}'.")
    
    # Save metrics metadata for display
    metrics = {
        "mae": float(mae),
        "rmse": float(rmse),
        "train_samples": len(X_train),
        "test_samples": len(X_test)
    }
    with open("model_metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)
        
    print("Saved evaluation metrics metadata to 'model_metrics.json'.")

if __name__ == "__main__":
    train_model()
