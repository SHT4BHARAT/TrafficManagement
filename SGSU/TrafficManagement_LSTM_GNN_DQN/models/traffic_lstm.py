import torch
import torch.nn as nn

class TrafficLSTM(nn.Module):
    """
    Lightweight LSTM (PyTorch CPU) — India 5-Phase variant.
    Input features (9): q_N, q_S, q_E, q_W, q_NR, q_SR, q_ER, q_WR, ped
    Hidden: 64, Layers: 2
    Output: predicted next total queue length
    """
    def __init__(self, input_size=9, hidden_size=64, num_layers=2):
        super(TrafficLSTM, self).__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True
        )
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])

if __name__ == "__main__":
    device = torch.device("cpu")
    model = TrafficLSTM().to(device)
    dummy = torch.randn(32, 10, 9)  # (batch, seq=10, features=9)
    output = model(dummy)
    print(f"LSTM Output Shape: {output.shape}")  # (32, 1)
