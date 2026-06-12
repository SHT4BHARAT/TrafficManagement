import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv

class STGNN(nn.Module):
    """
    Spatio-Temporal Graph Neural Network (Phase 1 & 3 Unified).
    Fuses LSTM (Temporal) and GCN (Spatial) to generate a latent traffic state vector.
    """
    def __init__(self, input_size, hidden_size, output_latent_size, sequence_length):
        super(STGNN, self).__init__()
        self.hidden_size = hidden_size
        self.sequence_length = sequence_length
        
        # Temporal Component: LSTM processes the time-series history
        self.lstm = nn.LSTM(input_size=input_size, 
                            hidden_size=hidden_size, 
                            num_layers=2, 
                            batch_first=True)
                            
        # Spatial Component: GCN propagates temporal features across the road network
        self.gcn1 = GCNConv(hidden_size, hidden_size)
        self.gcn2 = GCNConv(hidden_size, output_latent_size)
        
        # Optional: Auxiliary head to predict future observable state (speed, flow)
        # This is useful for pre-training the STGNN before plugging into RL
        self.prediction_head = nn.Linear(output_latent_size, input_size)

    def forward(self, x, edge_index):
        """
        x: Tensor of shape (batch, num_nodes, sequence_length, input_size)
           E.g. A batch of historical sequences for every intersection.
        edge_index: Graph connectivity (from SUMO network)
        """
        batch_size, num_nodes, seq_len, features = x.shape
        
        # 1. Temporal Processing (LSTM)
        # We need to process each node's sequence independently through the LSTM.
        # Reshape to treat nodes as part of the batch for the LSTM: (batch * num_nodes, seq, features)
        x_reshaped = x.view(batch_size * num_nodes, seq_len, features)
        
        lstm_out, _ = self.lstm(x_reshaped)
        
        # Extract the final hidden state from the sequence
        lstm_features = lstm_out[:, -1, :] # shape: (batch * num_nodes, hidden_size)
        
        # 2. Spatial Processing (GCN)
        # Reshape back to apply GCN across the nodes for each item in the batch
        # We process GCN batch by batch
        latent_states = []
        for b in range(batch_size):
            # Extract features for this specific batch
            start_idx = b * num_nodes
            end_idx = (b + 1) * num_nodes
            node_features = lstm_features[start_idx:end_idx] # shape: (num_nodes, hidden_size)
            
            # Apply GCN
            gcn_out = self.gcn1(node_features, edge_index)
            gcn_out = F.relu(gcn_out)
            gcn_out = F.dropout(gcn_out, p=0.3, training=self.training)
            gcn_latent = self.gcn2(gcn_out, edge_index) # shape: (num_nodes, output_latent_size)
            
            latent_states.append(gcn_latent)
            
        # Stack latent states over the batch
        # shape: (batch_size, num_nodes, output_latent_size)
        latent_tensor = torch.stack(latent_states)
        
        # Auxiliary prediction (for pre-training)
        predicted_next_state = self.prediction_head(latent_tensor) # shape: (batch, num_nodes, features)
        
        return latent_tensor, predicted_next_state
