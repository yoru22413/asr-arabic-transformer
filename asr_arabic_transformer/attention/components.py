import math

import torch
import torch.nn.functional as F
from torch import nn

device = 'cuda' if torch.cuda.is_available() else 'cpu'


class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, n_heads):
        super().__init__()
        self.q_linear = nn.Linear(d_model, d_model, bias=False)
        self.v_linear = nn.Linear(d_model, d_model, bias=False)
        self.k_linear = nn.Linear(d_model, d_model, bias=False)
        self.project = nn.Linear(d_model, d_model, bias=False)
        self.n_heads = n_heads
        self.d_model = d_model
        self.d_k = d_model // n_heads
        self.d_v = self.d_k

    def forward(self, q, k, v, mask=None):
        # (bs, sl, d_model)
        bs, sl_q, _ = q.shape
        sl_k = k.shape[-2]
        sl_v = v.shape[-2]
        q = self.q_linear(q).view(bs, sl_q, self.n_heads, self.d_k)
        k = self.k_linear(k).view(bs, sl_k, self.n_heads, self.d_k)
        v = self.v_linear(v).view(bs, sl_v, self.n_heads, self.d_k)

        q = q.transpose(1, 2)
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)

        z = (q @ k.transpose(-2, -1)) / math.sqrt(self.d_k)
        if mask is not None:
            if len(mask.shape) == 3:
                mask = mask.unsqueeze(1)
            z = z.masked_fill(mask, -1e10)

        z = F.softmax(z, dim=-1)
        z = z @ v

        z = self.project(z.transpose(1, 2).contiguous().view(bs, sl_q, -1))
        return z


class FeedForward(nn.Module):
    def __init__(self, d_model, d_ff):
        super().__init__()
        self.linear1 = nn.Linear(d_model, d_ff)
        self.linear2 = nn.Linear(d_ff, d_model)

    def forward(self, x):
        x = F.relu(self.linear1(x))
        x = self.linear2(x)
        return x


class Norm(nn.Module):
    def __init__(self, d_model, eps=1e-6):
        super().__init__()

        self.size = d_model
        self.alpha = nn.Parameter(torch.ones(self.size), requires_grad=True)
        self.bias = nn.Parameter(torch.zeros(self.size), requires_grad=True)
        self.eps = eps

    def forward(self, x):
        norm = self.alpha * (x - x.mean(dim=-1, keepdim=True)) / (x.std(dim=-1, keepdim=True) + self.eps) + self.bias
        return norm


class PositionalEncoder(nn.Module):
    def __init__(self, d_model, dropout, max_seq_len=1024):
        super().__init__()
        self.d_model = d_model
        self.dropout = nn.Dropout(dropout)

        pe = torch.zeros(max_seq_len, d_model)
        position = torch.arange(0, max_seq_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)

    def forward(self, x):
        seq_len = x.size(1)
        p = self.pe[:, :seq_len]
        x = x + p
        x = self.dropout(x)
        return x
