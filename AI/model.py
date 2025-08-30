# ai/model.py
from __future__ import annotations
from typing import Optional
import torch
import torch.nn as nn
from torch import optim

class NeuralNet(nn.Module):
    def __init__(self, input_size: int = 4):
        super().__init__()
        self.fc1 = nn.Linear(input_size, 16)
        self.fc2 = nn.Linear(16, 8)
        self.fc3 = nn.Linear(8, 1)
        self.relu = nn.ReLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        return self.fc3(x)  # logits

def train_tiny_model(X: torch.Tensor, y: torch.Tensor, *, epochs: int = 50, lr: float = 1e-2) -> Optional[NeuralNet]:
    if X.shape[0] == 0:
        return None
    model = NeuralNet(input_size=X.shape[1])
    crit = nn.BCEWithLogitsLoss()
    opt = optim.Adam(model.parameters(), lr=lr)
    model.train()
    for _ in range(epochs):
        opt.zero_grad()
        logits = model(X)
        loss = crit(logits, y)
        loss.backward()
        opt.step()
    model.eval()
    return model

@torch.no_grad()
def predict_probs(model: NeuralNet, X_new: torch.Tensor) -> torch.Tensor:
    """Returns probabilities ∈ [0,1] of shape (M,1)."""
    return torch.sigmoid(model(X_new))
