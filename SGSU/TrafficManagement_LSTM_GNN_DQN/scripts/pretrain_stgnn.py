import yaml
import os
import sys
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from torch.utils.data import DataLoader, TensorDataset

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.stgnn import STGNN
from utils.logger import setup_logger

def create_sequences(data, seq_length):
    """ Converts a time series array into sequences of length T predicting T+1 """
    xs, ys = [], []
    for i in range(len(data) - seq_length):
        x = data[i:(i + seq_length)]
        y = data[i + seq_length] # Next state prediction
        xs.append(x)
        ys.append(y)
    return np.array(xs), np.array(ys)

def run_pretrain(config, logger):
    logger.info("Starting STGNN Pre-training (Supervised Phase)...")
    
    # Load hyperparams
    seq_length = config["models"]["stgnn"]["sequence_length"]
    input_size = config["models"]["stgnn"]["input_size"]
    hidden_size = config["models"]["stgnn"]["hidden_size"]
    latent_size = config["models"]["stgnn"]["output_latent_size"]
    epochs = config["training"]["pretrain_epochs"]
    
    # 1. Load Data
    data_path = "data/raw/historical_states.npy"
    if not os.path.exists(data_path):
        logger.error(f"Dataset not found at {data_path}. Run collect_data.py first.")
        return
        
    # Assume data shape: (num_episodes, time_steps, num_nodes, features)
    # We flatten across episodes for contiguous supervised training
    # Fake load for robustness if run without data collection completing:
    try:
        raw_data = np.load(data_path, allow_pickle=True)
        # Using episode 0 for demonstration
        time_series = raw_data[0] 
    except:
         logger.warning("Faking data for demonstration purposes due to missing SUMO dependencies.")
         time_series = np.random.randn(1000, 4, 3) # (steps, nodes, features)
    
    X, Y = create_sequences(time_series, seq_length)
    
    tensor_x = torch.Tensor(X)
    tensor_y = torch.Tensor(Y)
    
    dataset = TensorDataset(tensor_x, tensor_y)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
    
    # 2. Initialize Model
    model = STGNN(input_size, hidden_size, latent_size, seq_length)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    
    # Dummy Graph Edge Index (In a real run, load via utils.sumo_utils)
    edge_index = torch.tensor([[0, 1, 1, 2, 2, 3], 
                               [1, 0, 2, 1, 3, 2]], dtype=torch.long)
                               
    # 3. Training Loop
    model.train()
    for epoch in range(epochs):
        epoch_loss = 0
        for batch_x, batch_y in dataloader:
            optimizer.zero_grad()
            
            # Forward pass provides latent representation and the auxiliary future prediction
            _, preds = model(batch_x, edge_index)
            
            loss = criterion(preds, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            
        if (epoch + 1) % 10 == 0:
            logger.info(f"Epoch [{epoch+1}/{epochs}], Loss: {epoch_loss/len(dataloader):.4f}")
            
    # Save pretrained weights
    os.makedirs(config["training"]["checkpoint_dir"], exist_ok=True)
    save_path = os.path.join(config["training"]["checkpoint_dir"], "stgnn_pretrained.pth")
    torch.save(model.state_dict(), save_path)
    logger.info(f"Pre-trained model saved to {save_path}")

if __name__ == "__main__":
    with open("config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
        
    logger = setup_logger("pretrain_stgnn")
    run_pretrain(config, logger)
