import yaml
import torch
import torch.nn as nn
import numpy as np
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.traffic_lstm import TrafficLSTM

def pretrain():
    with open("config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    params = config["training"]
    device = torch.device(params["device"])
    
    # Load raw traffic data
    data_path = "data/raw/traffic_data_50k.npy"
    if not os.path.exists(data_path):
        print("No data found. Run collect_data.py first.")
        return
        
    data = np.load(data_path)
    print(f"Loaded data: {data.shape}")  # Expected: (50000, 9)
    
    # Create sliding window sequences
    seq_len = params["sequence_len"]
    X, y = [], []
    for i in range(len(data) - seq_len):
        X.append(data[i:i+seq_len])
        # Target: total queue at next step (sum of first 4 features)
        y.append(data[i+seq_len][0:4].sum())
    
    X = torch.FloatTensor(np.array(X)).to(device)
    y = torch.FloatTensor(np.array(y)).unsqueeze(1).to(device)
    print(f"Training sequences: {X.shape}, Targets: {y.shape}")
    
    # Model
    model = TrafficLSTM(
        input_size=params["input_size"],
        hidden_size=params["hidden_size"]
    ).to(device)
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.MSELoss()
    
    # Train
    batch_size = params["batch_size"]
    for epoch in range(params["epochs"]):
        total_loss = 0
        n_batches = 0
        indices = torch.randperm(len(X))
        
        for i in range(0, len(X), batch_size):
            batch_idx = indices[i:i+batch_size]
            batch_x = X[batch_idx]
            batch_y = y[batch_idx]
            
            pred = model(batch_x)
            loss = criterion(pred, batch_y)
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            n_batches += 1
        
        avg_loss = total_loss / n_batches
        print(f"Epoch {epoch+1}/{params['epochs']}, Loss: {avg_loss:.4f}")
    
    # Save
    os.makedirs(params["checkpoint_dir"], exist_ok=True)
    save_path = os.path.join(params["checkpoint_dir"], "lstm_weights.pth")
    torch.save(model.state_dict(), save_path)
    print(f"LSTM weights saved: {save_path}")

if __name__ == "__main__":
    pretrain()
