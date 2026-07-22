#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib

# ---------------- Model ----------------
class ResMLPWithAttn(nn.Module):
    def __init__(self,
                 in_dim: int = 4,
                 hidden_dim: int = 4096,
                 depth: int = 8,
                 dropout_p: float = 0.3,
                 n_heads: int = 8,
                 out_dim: int = 2):
        super().__init__()
        self.input_lin = nn.Linear(in_dim, hidden_dim)
        self.attn = nn.MultiheadAttention(embed_dim=hidden_dim,
                                          num_heads=n_heads,
                                          dropout=dropout_p,
                                          batch_first=True)
        self.blocks = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.GELU(),
                nn.Dropout(dropout_p)
            ) for _ in range(depth)
        ])
        self.head = nn.Linear(hidden_dim, out_dim)

    def forward(self, x):
        h = F.gelu(self.input_lin(x))
        h_seq = h.unsqueeze(1)
        attn_out, _ = self.attn(h_seq, h_seq, h_seq)
        h = h + attn_out.squeeze(1)
        for blk in self.blocks:
            h = blk(h) + h
        return self.head(h)

def load_scalers_al(path: str):
    scalers = joblib.load(path)
    required = ['scaler_X', 'scaler_dd0', 'scaler_H2', 'scaler_Y',
                'lambda_h2', 'shift', 'min_h2', 'max_h2']
    miss = [k for k in required if k not in scalers]
    if miss:
        raise ValueError(f"Missing scaler keys for AlterBBN: {miss}")
    return scalers

def invert_h2(h2_scaled, scaler_H2, lambda_h2, shift, mn, mx,
              use_scaling=False, use_boxcox=False):
    h2_scaled = scaler_H2.inverse_transform(h2_scaled.reshape(-1, 1)).flatten()
    if use_boxcox:
        bc = mn + (h2_scaled / 0.01) * (mx - mn)
        inv_log = (bc * lambda_h2 + 1) ** (1 / lambda_h2) - shift
    elif use_scaling:
        inv_log = h2_scaled * 100.0
    else:
        inv_log = h2_scaled
    inv_log = np.nan_to_num(inv_log, nan=0.0, posinf=1e10, neginf=-1e10)
    inv_log = np.clip(inv_log, -308, 308)
    return 10.0 ** inv_log

def compute_and_print_metrics(label, y_true, y_pred):
    eps = 0.0
    err = y_pred - y_true
    ape = np.abs(err / (y_true + eps)) * 100.0
    mse = mean_squared_error(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    r2  = r2_score(y_true, y_pred)
    rmse = float(np.sqrt(mse))
    rmspe = float(np.sqrt(np.mean(ape * ape)))
    mape  = float(np.nanmean(ape))
    mpe   = float(np.mean((err / (y_true + eps)) * 100.0))

    print(f"\n== {label} ==")
    print(f"   MAE   = {mae:.3e}")
    print(f"   RMSE  = {rmse:.3e}")
    print(f"   R2    = {r2:.6f}")
    print(f"   MAPE  = {mape:.4f}%")
    print(f"   RMSPE = {rmspe:.4f}%")
    print(f"   MPE   = {mpe:.4f}%")

def evaluate_alterbbn(df, input_cols, y_cols, model, scalers, batch_size=256,
                      dataset_name="AlterBBN", h2h_min=None, h2h_max=None,
                      yp_min=None, yp_max=None):

    X = df[input_cols].values.astype(np.float32)
    Y_true = df[y_cols].values.astype(np.float32)

    eps = 1e-7
    log0 = np.log10(np.maximum(X[:, 0], eps)).reshape(-1, 1)  # kappa10 in log10 then minmax
    X[:, 0] = scalers['scaler_dd0'].transform(log0).flatten()
    X_scaled = scalers['scaler_X'].transform(X)

    device = next(model.parameters()).device
    model.eval()
    preds = []
    with torch.no_grad():
        for i in range(0, len(X_scaled), batch_size):
            xb = torch.from_numpy(X_scaled[i:i + batch_size]).to(device)
            preds.append(model(xb).cpu().numpy())
    P = np.vstack(preds)

    H2_pred = invert_h2(P[:, 0],
                        scalers['scaler_H2'],
                        scalers['lambda_h2'],
                        scalers['shift'],
                        scalers['min_h2'],
                        scalers['max_h2'],
                        scalers.get('use_scaling', False),
                        scalers.get('use_boxcox', False))
    Yp_pred = scalers['scaler_Y'].inverse_transform(P[:, 1].reshape(-1, 1)).flatten()
    Y_pred  = np.vstack([H2_pred, Yp_pred]).T
    if np.any(~np.isfinite(Y_pred)):
        print("Warning: NaN/Inf in predictions; replacing with finite values.")
        Y_pred = np.nan_to_num(Y_pred, nan=0.0, posinf=1e10, neginf=-1e10)

    # overall
    compute_and_print_metrics(f"H2/H (all) - {dataset_name}", Y_true[:, 0], Y_pred[:, 0])
    compute_and_print_metrics(f"Yp   (all) - {dataset_name}", Y_true[:, 1], Y_pred[:, 1])

    # optional subset: combine H2/H and Yp range filters (all specified constraints must hold)
    if (h2h_min is not None) or (h2h_max is not None) or (yp_min is not None) or (yp_max is not None):
        mask = np.ones(len(Y_true), dtype=bool)
        if h2h_min is not None:
            mask &= (Y_true[:, 0] >= h2h_min)
        if h2h_max is not None:
            mask &= (Y_true[:, 0] <= h2h_max)
        if yp_min is not None:
            mask &= (Y_true[:, 1] >= yp_min)
        if yp_max is not None:
            mask &= (Y_true[:, 1] <= yp_max)

        n_sub = int(mask.sum())
        # pretty range text
        h2h_range_txt = []
        if h2h_min is not None: h2h_range_txt.append(f"H2/H>={h2h_min:g}")
        if h2h_max is not None: h2h_range_txt.append(f"H2/H<={h2h_max:g}")
        yp_range_txt = []
        if yp_min is not None: yp_range_txt.append(f"Yp>={yp_min:g}")
        if yp_max is not None: yp_range_txt.append(f"Yp<={yp_max:g}")
        cond_txt = ", ".join(h2h_range_txt + yp_range_txt) if (h2h_range_txt or yp_range_txt) else "None"

        print(f"\n[{dataset_name}] Subset ({cond_txt}) : {n_sub} samples")
        if n_sub > 0:
            compute_and_print_metrics(f"H2/H (subset) - {dataset_name}",
                                      Y_true[mask, 0], Y_pred[mask, 0])
            compute_and_print_metrics(f"Yp   (subset) - {dataset_name}",
                                      Y_true[mask, 1], Y_pred[mask, 1])

def parse_args():
    p = argparse.ArgumentParser(
        description="Evaluate an AlterBBN sub-model on its dataset; "
                    "optionally report metrics on H2/H and/or Yp subranges."
    )
    p.add_argument('--data_csv', required=True, help="CSV path for this sub-model's dataset")
    p.add_argument('--model_path', required=True, help="Path to trained .pth")
    p.add_argument('--scaler_path', required=True, help="Path to scalers .pkl for this sub-model")
    p.add_argument('--batch_size', type=int, default=256)
    p.add_argument('--device', default='auto', choices=['auto','cpu','cuda'])
    p.add_argument('--h2h_min', type=float, default=None, help="Min true H2/H to include (optional)")
    p.add_argument('--h2h_max', type=float, default=None, help="Max true H2/H to include (optional)")
    p.add_argument('--yp_min', type=float, default=None, help="Min true Yp to include (optional)")
    p.add_argument('--yp_max', type=float, default=None, help="Max true Yp to include (optional)")
    return p.parse_args()

def main():
    args = parse_args()

    df = pd.read_csv(args.data_csv)
    input_cols = ['kappa10', 'DN_eff', 'tau', 'omegabn']
    y_cols     = ['H2/H', 'Yp']
    missing = [c for c in (input_cols + y_cols) if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in CSV: {missing}")

    scalers = load_scalers_al(args.scaler_path)
    if args.device == 'auto':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    else:
        device = torch.device(args.device)

    model = ResMLPWithAttn(hidden_dim=4096).to(device)
    model.load_state_dict(torch.load(args.model_path, map_location=device), strict=False)

    dataset_name = "AlterBBN"
    evaluate_alterbbn(df, input_cols, y_cols, model, scalers,
                      batch_size=args.batch_size,
                      dataset_name=dataset_name,
                      h2h_min=args.h2h_min, h2h_max=args.h2h_max,
                      yp_min=args.yp_min, yp_max=args.yp_max)

if __name__ == '__main__':
    main()
