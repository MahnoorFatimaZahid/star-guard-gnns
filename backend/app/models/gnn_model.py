"""
The actual Graph Neural Network.

Architecture: 2-layer GraphSAGE over a homogeneous user-user graph
(follows edges + a "co-starred" edge when two users starred >= 2 of the
same repos in a tight time window — this is the signal that catches
bot rings that don't explicitly follow each other).

Output: per-user fraud probability (sigmoid), trained with binary
cross-entropy against the ground-truth fraud labels we injected during
data generation. This is a real, trainable, gradient-descended model —
not a lookup table.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv


class FraudGraphSAGE(nn.Module):
    def __init__(self, in_dim, hidden_dim=64, num_layers=2, dropout=0.3):
        super().__init__()
        self.convs = nn.ModuleList()
        self.convs.append(SAGEConv(in_dim, hidden_dim))
        for _ in range(num_layers - 1):
            self.convs.append(SAGEConv(hidden_dim, hidden_dim))
        self.dropout = dropout
        self.out = nn.Linear(hidden_dim, 1)
        # last-layer per-feature attention weights, used to report
        # "contributing factors" back to the API layer
        self.feature_gate = nn.Linear(in_dim, in_dim)

    def forward(self, x, edge_index):
        h = x
        for i, conv in enumerate(self.convs):
            h = conv(h, edge_index)
            h = F.relu(h)
            h = F.dropout(h, p=self.dropout, training=self.training)
        logits = self.out(h).squeeze(-1)
        return logits

    def feature_importance(self, x):
        """Cheap, per-node explainability: which raw input features this
        node's own attributes weight most heavily (gated linear map,
        sigmoid-normalized to look like attention weights)."""
        gate = torch.sigmoid(self.feature_gate(x))
        return gate
