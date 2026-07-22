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
from typing import List, Optional, Dict, Any
# add near the top
import time

# helper: pretty print
def _fmt_ms(ms: float) -> str:
    return f"{ms:.2f} ms"

def _fmt_us(us: float) -> str:
    return f"{us:.1f} mus"

def _print_timing(tag: str, total_s: float, n: int):
    total_ms = total_s * 1000.0
    per_samp_us = (total_s / max(1, n)) * 1e6
    print(f"[Timing] {tag:<24} total={_fmt_ms(total_ms):>10} | per-sample={_fmt_us(per_samp_us):>10}")


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

# ---------------- Scalers ----------------
REQUIRED_KEYS_AL = ['scaler_X', 'scaler_dd0', 'scaler_H2', 'scaler_Y',
                    'lambda_h2', 'shift', 'min_h2', 'max_h2']

def load_scalers(path: str) -> Dict[str, Any]:
    scalers = joblib.load(path)
    missing = [k for k in REQUIRED_KEYS_AL if k not in scalers]
    if missing:
        raise ValueError(f"Missing scaler keys in {path}: {missing}")
    return scalers

# ---------------- Inversion ----------------
def invert_h2(h2_scaled_1d: np.ndarray,
              scalers: Dict[str, Any],
              use_scaling_fallback: bool = False,
              use_boxcox_fallback: bool = False) -> np.ndarray:
    scaler_H2 = scalers['scaler_H2']
    lambda_h2 = scalers['lambda_h2']
    shift     = scalers['shift']
    mn        = scalers['min_h2']
    mx        = scalers['max_h2']
    use_scaling = scalers.get('use_scaling', use_scaling_fallback)
    use_boxcox  = scalers.get('use_boxcox',  use_boxcox_fallback)

    h2_scaled = scaler_H2.inverse_transform(h2_scaled_1d.reshape(-1, 1)).flatten()
    if use_boxcox:
        bc = mn + (h2_scaled / 0.01) * (mx - mn)
        inv_log = (bc * lambda_h2 + 1.0) ** (1.0 / lambda_h2) - shift
    elif use_scaling:
        inv_log = h2_scaled * 100.0
    else:
        inv_log = h2_scaled

    inv_log = np.nan_to_num(inv_log, nan=0.0, posinf=1e10, neginf=-1e10)
    inv_log = np.clip(inv_log, -308, 308)
    return 10.0 ** inv_log

# ---------------- Metrics ----------------
def compute_and_print_metrics(label, y_true, y_pred):
    eps = 0.0
    err = y_pred - y_true
    ape = np.abs(err / (y_true + eps)) * 100.0
    mse = mean_squared_error(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    rmse = np.sqrt(mse)
    rmspe = np.sqrt(np.mean(ape * ape))
    mape = np.nanmean(ape)
    mpe = np.mean((err / (y_true + eps)) * 100.0)

    print(f"\n== {label} ==")
    print(f"   MAE   = {mae:.3e}")
    print(f"   RMSE  = {rmse:.3e}")
    print(f"   R2    = {r2:.6f}")
    print(f"   MAPE  = {mape:.4f}%")
    print(f"   RMSPE = {rmspe:.4f}%")
    print(f"   MPE   = {mpe:.4f}%")

# ---------------- Helper ----------------
def chunked_predict(model: nn.Module,
                    X_scaled: np.ndarray,
                    device: torch.device,
                    batch_size: int) -> np.ndarray:
    preds = []
    model.eval()
    with torch.no_grad():
        for i in range(0, len(X_scaled), batch_size):
            xb = torch.from_numpy(X_scaled[i:i + batch_size]).to(device)
            preds.append(model(xb).cpu().numpy())
    return np.vstack(preds)

def transform_inputs_with_scalers(X_raw: np.ndarray,
                                  scalers: Dict[str, Any],
                                  eps: float = 0) -> np.ndarray:
    X = X_raw.copy()
    log0 = np.log10(np.maximum(X[:, 0], eps)).reshape(-1, 1)  # first column log10
    X[:, 0] = scalers['scaler_dd0'].transform(log0).flatten()
    X_scaled = scalers['scaler_X'].transform(X)
    return X_scaled

# ---------------- Evaluation (2-expert routing) ----------------
def evaluate_al_two_experts(df: pd.DataFrame,
                            input_cols: List[str],
                            y_cols: List[str],
                            base_model: nn.Module,
                            base_scalers: Dict[str, Any],
                            args,
                            device: torch.device,
                            exp1_model: Optional[nn.Module] = None,   # [mid, upper]
                            exp2_model: Optional[nn.Module] = None,   # [lower, mid)
                            exp1_scalers: Optional[Dict[str, Any]] = None,
                            exp2_scalers: Optional[Dict[str, Any]] = None,
                            dataset_name: str = "AlterBBN",
                            quiet: bool = False):
    X_raw = df[input_cols].values.astype(np.float32)
    Y_true = df[y_cols].values.astype(np.float32)
    N = len(X_raw)

    if not quiet:
        thresholds = [1e-4, 1e-5, 1e-6, 1e-7]
        print(f"\n[{dataset_name}] counts of true H2/H >= threshold:")
        for t in thresholds:
            print(f"  >= {t:.0e}: {(Y_true[:, 0] >= t).sum()}")

    t0 = time.perf_counter()
    # preprocess for base
    tp0 = time.perf_counter()
    X_scaled_base = transform_inputs_with_scalers(X_raw, base_scalers, eps=1e-12)
    tp1 = time.perf_counter()

    # base predict
    tb0 = time.perf_counter()
    base_out = chunked_predict(base_model, X_scaled_base, device, args.batch_size)
    tb1 = time.perf_counter()

    # base invert
    ti0 = time.perf_counter()
    H2_pred_base = invert_h2(base_out[:, 0],
                             base_scalers,
                             use_scaling_fallback=getattr(args, 'use_scaling', False),
                             use_boxcox_fallback=getattr(args, 'use_boxcox', False))
    Yp_pred_base = base_scalers['scaler_Y'].inverse_transform(base_out[:, 1].reshape(-1, 1)).flatten()
    ti1 = time.perf_counter()

    if not args.exp:
        Y_pred = np.vstack([H2_pred_base, Yp_pred_base]).T
        Y_pred = np.nan_to_num(Y_pred, nan=0.0, posinf=0, neginf=-0)
        if not quiet:
            compute_and_print_metrics(f"H2/H (all) - {dataset_name}", Y_true[:, 0], Y_pred[:, 0])
            compute_and_print_metrics(f"Y_p  (all) - {dataset_name}", Y_true[:, 1], Y_pred[:, 1])
            mask_keep = np.ones(N, dtype=bool)
            # H2/H bounds
            if args.h2h_min is not None: mask_keep &= (Y_true[:, 0] >= args.h2h_min)
            if args.h2h_max is not None: mask_keep &= (Y_true[:, 0] <= args.h2h_max)
            # Y_p bounds
            if args.yp_min is not None:  mask_keep &= (Y_true[:, 1] >= args.yp_min)
            if args.yp_max is not None:  mask_keep &= (Y_true[:, 1] <= args.yp_max)
    
            print(f"\n[{dataset_name}] Combined subset (AND of ranges) with {mask_keep.sum()} samples")
            if mask_keep.any():
                compute_and_print_metrics(f"H2/H (combined subset) - {dataset_name}", Y_true[mask_keep, 0], Y_pred[mask_keep, 0])
                compute_and_print_metrics(f"Y_p  (combined subset) - {dataset_name}", Y_true[mask_keep, 1], Y_pred[mask_keep, 1])
            else:
                print("  (No samples remain after combined filtering)")
        

        # timing summary
        t1 = time.perf_counter()
        _print_timing("base.preprocess", tp1 - tp0, N)
        _print_timing("base.predict",    tb1 - tb0, N)
        _print_timing("base.inverse",    ti1 - ti0, N)
        _print_timing("base.total",      t1 - t0,   N)

        route = np.full(N, "base", dtype=object)
        if args.per_sample_csv:
            per_df = build_per_sample_df(df, input_cols, y_cols, Y_pred.astype(np.float64), route)
            per_df.to_csv(args.per_sample_csv, index=False)
            print(f"[PerSample] Saved: {args.per_sample_csv}  (rows={len(per_df)})")
            if args.per_sample_head > 0:
                print(per_df.head(args.per_sample_head).to_string(index=False))

        return

    # routing
    tr0 = time.perf_counter()
    lower = args.exp_lower; mid = args.exp_mid; upper = args.exp_upper
    mask_exp2 = (H2_pred_base >= lower) & (H2_pred_base <  mid)   # exp2: [lower, mid)
    mask_exp1 = (H2_pred_base >= mid)   & (H2_pred_base <= upper) # exp1: [mid, upper]
    mask_base = ~(mask_exp1 | mask_exp2)
    tr1 = time.perf_counter()

    if not quiet:
        print(f"\nRouting stats by base D/H prediction:")
        print(f"  exp2 [{lower:.0e}, {mid:.0e}): {mask_exp2.sum()}")
        print(f"  exp1 [{mid:.0e}, {upper:.0e}]: {mask_exp1.sum()}")
        print(f"  base (others):               : {mask_base.sum()}")

    # experts stage
    H2_pred_final = H2_pred_base.copy()
    Yp_pred_final = Yp_pred_base.copy()

    # exp2 timings
    te2_prep = te2_pred = te2_inv = 0.0
    if mask_exp2.any():
        if exp2_model is None or exp2_scalers is None:
            raise ValueError("exp2 is routed but exp2_model/exp2_scalers is missing.")

        e2p0 = time.perf_counter()
        X_exp2_scaled = transform_inputs_with_scalers(X_raw[mask_exp2], exp2_scalers, eps=1e-7)
        e2p1 = time.perf_counter(); te2_prep += (e2p1 - e2p0)

        e2m0 = time.perf_counter()
        out_b = chunked_predict(exp2_model, X_exp2_scaled, device, args.batch_size)
        e2m1 = time.perf_counter(); te2_pred += (e2m1 - e2m0)

        e2i0 = time.perf_counter()
        H2_b = invert_h2(out_b[:, 0], exp2_scalers,
                         use_scaling_fallback=getattr(args, 'use_scaling', False),
                         use_boxcox_fallback=getattr(args, 'use_boxcox', False))
        Yp_b = exp2_scalers['scaler_Y'].inverse_transform(out_b[:, 1].reshape(-1, 1)).flatten()
        H2_pred_final[mask_exp2] = H2_b
        Yp_pred_final[mask_exp2] = Yp_b
        e2i1 = time.perf_counter(); te2_inv += (e2i1 - e2i0)

    # exp1 timings
    te1_prep = te1_pred = te1_inv = 0.0
    if mask_exp1.any():
        if exp1_model is None or exp1_scalers is None:
            raise ValueError("exp1 is routed but exp1_model/exp1_scalers is missing.")

        e1p0 = time.perf_counter()
        X_exp1_scaled = transform_inputs_with_scalers(X_raw[mask_exp1], exp1_scalers, eps=1e-12)
        e1p1 = time.perf_counter(); te1_prep += (e1p1 - e1p0)

        e1m0 = time.perf_counter()
        out_b = chunked_predict(exp1_model, X_exp1_scaled, device, args.batch_size)
        e1m1 = time.perf_counter(); te1_pred += (e1m1 - e1m0)

        e1i0 = time.perf_counter()
        H2_b = invert_h2(out_b[:, 0], exp1_scalers,
                         use_scaling_fallback=getattr(args, 'use_scaling', False),
                         use_boxcox_fallback=getattr(args, 'use_boxcox', False))
        Yp_b = exp1_scalers['scaler_Y'].inverse_transform(out_b[:, 1].reshape(-1, 1)).flatten()
        H2_pred_final[mask_exp1] = H2_b
        Yp_pred_final[mask_exp1] = Yp_b
        e1i1 = time.perf_counter(); te1_inv += (e1i1 - e1i0)

    Y_pred = np.vstack([H2_pred_final, Yp_pred_final]).T
    Y_pred = np.nan_to_num(Y_pred, nan=0.0, posinf=1e10, neginf=-1e10)

    if not quiet:
        compute_and_print_metrics(f"H2/H (all, 2-EXP) - {dataset_name}", Y_true[:, 0], Y_pred[:, 0])
        compute_and_print_metrics(f"Y_p  (all, 2-EXP) - {dataset_name}", Y_true[:, 1], Y_pred[:, 1])
        mask_keep = np.ones(N, dtype=bool)
        # H2/H bounds
        if args.h2h_min is not None: mask_keep &= (Y_true[:, 0] >= args.h2h_min)
        if args.h2h_max is not None: mask_keep &= (Y_true[:, 0] <= args.h2h_max)
        # Y_p bounds
        if args.yp_min is not None:  mask_keep &= (Y_true[:, 1] >= args.yp_min)
        if args.yp_max is not None:  mask_keep &= (Y_true[:, 1] <= args.yp_max)

        print(f"\n[{dataset_name}] Combined subset (AND of ranges) with {mask_keep.sum()} samples")
        if mask_keep.any():
            compute_and_print_metrics(f"H2/H (combined subset, 2-EXP) - {dataset_name}", Y_true[mask_keep, 0], Y_pred[mask_keep, 0])
            compute_and_print_metrics(f"Y_p  (combined subset, 2-EXP) - {dataset_name}", Y_true[mask_keep, 1], Y_pred[mask_keep, 1])
        else:
            print("  (No samples remain after combined filtering)")

    # timing summary
    t1 = time.perf_counter()
    _print_timing("base.preprocess", tp1 - tp0, N)
    _print_timing("base.predict",    tb1 - tb0, N)
    _print_timing("base.inverse",    ti1 - ti0, N)
    _print_timing("routing",         tr1 - tr0, N)
    _print_timing("exp2.preprocess", te2_prep,  mask_exp2.sum() if mask_exp2.any() else 1)
    _print_timing("exp2.predict",    te2_pred,  mask_exp2.sum() if mask_exp2.any() else 1)
    _print_timing("exp2.inverse",    te2_inv,   mask_exp2.sum() if mask_exp2.any() else 1)
    _print_timing("exp1.preprocess", te1_prep,  mask_exp1.sum() if mask_exp1.any() else 1)
    _print_timing("exp1.predict",    te1_pred,  mask_exp1.sum() if mask_exp1.any() else 1)
    _print_timing("exp1.inverse",    te1_inv,   mask_exp1.sum() if mask_exp1.any() else 1)
    _print_timing("exp.total",       t1 - t0,   N)

    route = np.full(N, "base", dtype=object)
    route[mask_exp2] = "exp2"
    route[mask_exp1] = "exp1"
    if args.per_sample_csv:
        per_df = build_per_sample_df(df, input_cols, y_cols, Y_pred.astype(np.float64), route)
        per_df.to_csv(args.per_sample_csv, index=False)
        print(f"[PerSample] Saved: {args.per_sample_csv}  (rows={len(per_df)})")
        if args.per_sample_head > 0:
            print(per_df.head(args.per_sample_head).to_string(index=False))

    
def build_per_sample_df(df: pd.DataFrame,
                        input_cols: List[str],
                        y_cols: List[str],
                        y_pred: np.ndarray,
                        route: np.ndarray) -> pd.DataFrame:
    """
    Assemble a per-sample DataFrame with inputs, ground truth, predictions, errors, and routing.
    """
    # ground truth
    y_true = df[y_cols].to_numpy(dtype=np.float64)
    eps = 0
    err  = y_pred - y_true
    abs_err = np.abs(err)
    ape = np.abs(err / np.maximum(np.abs(y_true), eps)) * 100.0  # percentage abs error

    # columns
    out = pd.DataFrame()
    out[input_cols] = df[input_cols].reset_index(drop=True)

    # true/pred
    for j, col in enumerate(y_cols):
        out[f"true::{col}"] = y_true[:, j]
        out[f"pred::{col}"] = y_pred[:, j]
        out[f"err::{col}"]  = err[:, j]
        out[f"|err|::{col}"] = abs_err[:, j]
        out[f"APE(%)::{col}"] = ape[:, j]

    out["route"] = route
    return out



# ---------------- Args ----------------
def parse_args():
    p = argparse.ArgumentParser()
    # data & base model
    p.add_argument('--data_csv', required=True, help="CSV with AlterBBN columns")
    p.add_argument('--model_path', required=True, help="Path to base/general model (.pth)")
    p.add_argument('--scaler_path', required=True, help="Path to base scalers .pkl (incl. Box-Cox params)")

    # inference
    p.add_argument('--batch_size', type=int, default=256)
    p.add_argument('--yp_min', type=float, default=None, help="Optional min true Y_p for subset metrics")
    p.add_argument('--yp_max', type=float, default=None, help="Optional max true Y_p for subset metrics")
    p.add_argument('--h2h_min', type=float, default=None, help="Optional min true D/H for subset metrics")
    p.add_argument('--h2h_max', type=float, default=None, help="Optional max true D/H for subset metrics")
    p.add_argument('--use_scaling', action='store_true', help="Fallback flag if scaler dict lacks key")
    p.add_argument('--use_boxcox', action='store_true', help="Fallback flag if scaler dict lacks key")

    # architecture (shared here; experts can differ if you want to extend)
    p.add_argument('--hidden_dim', type=int, default=4096)
    p.add_argument('--depth', type=int, default=8)
    p.add_argument('--dropout_p', type=float, default=0.3)
    p.add_argument('--n_heads', type=int, default=8)

    # two-expert switch & boundaries
    p.add_argument('--exp', action='store_true', help="Enable two-stage, two-expert routing")
    p.add_argument('--exp1_path', type=str, default="/home/fan.zhang/h2h/best_model_alter_exp1.pth", help="exp1 model path (interval [mid, upper])")
    p.add_argument('--exp2_path', type=str, default="/home/fan.zhang/h2h/best_model_alter_exp2.pth", help="exp2 model path (interval [lower, mid))")
    p.add_argument('--exp1_scaler_path', type=str, default="/home/fan.zhang/h2h/scalers_alterbbn_exp1.pkl", help="exp1 scaler .pkl path")
    p.add_argument('--exp2_scaler_path', type=str, default="/home/fan.zhang/h2h/scalers_alterbbn_exp2.pkl", help="exp2 scaler .pkl path")
    p.add_argument('--exp_lower', type=float, default=1e-7, help="Lower bound (inclusive) for expert routing")
    p.add_argument('--exp_mid',   type=float, default=1e-5, help="Mid split; exp2 gets [lower, mid), exp1 gets [mid, upper]")
    p.add_argument('--exp_upper', type=float, default=1e-3, help="Upper bound (inclusive) for expert routing")
    
    p.add_argument('--time_compare', action='store_true',
                   help="Run base-only and then 2-EXP on the same batch to compare timings.")
    p.add_argument('--warmup', type=int, default=0,
                   help="Warm-up runs before timing (only used when --time_compare).")
    p.add_argument('--repeats', type=int, default=1,
                   help="Number of timed repeats; average is reported (only used when --time_compare).")
    p.add_argument('--quiet', action='store_true',
                   help="Suppress metric prints; keep timing summaries.")
                   
    p.add_argument('--per_sample_csv', type=str, default="/home/fan.zhang/h2h/test_exp_samples_err.csv",
               help="If set, save a per-sample CSV with inputs/ground truth/predictions/errors/routing.")
    p.add_argument('--per_sample_head', type=int, default=0,
                   help="If > 0, print the first N rows of the per-sample table.")



    return p.parse_args()

# ---------------- Main ----------------
def main():
    args = parse_args()

    # load data
    df = pd.read_csv(args.data_csv)
    input_cols = ['kappa10', 'DN_eff', 'tau', 'omegabn']
    y_cols = ['H2/H', 'Yp']
    missing = [c for c in (input_cols + y_cols) if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # base scalers & model
    t0 = time.perf_counter()
    base_scalers = load_scalers(args.scaler_path)
    t1 = time.perf_counter()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    base_model = ResMLPWithAttn(
        in_dim=len(input_cols),
        hidden_dim=args.hidden_dim,
        depth=args.depth,
        dropout_p=args.dropout_p,
        n_heads=args.n_heads,
        out_dim=len(y_cols)
    ).to(device)
    base_model.load_state_dict(torch.load(args.model_path, map_location=device), strict=False)
    t2 = time.perf_counter()
    print(f"[Timing] load.base.scalers = {(t1-t0)*1000:.2f} ms")
    print(f"[Timing] load.base.model   = {(t2-t1)*1000:.2f} ms")

    exp1_model = None
    exp2_model = None
    exp1_scalers = None
    exp2_scalers = None

    if args.exp:
        if (not args.exp1_path) or (not args.exp2_path):
            raise ValueError("With --exp enabled, provide both --exp1_path and --exp2_path.")
        if (not args.exp1_scaler_path) or (not args.exp2_scaler_path):
            raise ValueError("With --exp enabled, provide --exp1_scaler_path and --exp2_scaler_path.")

        # load expert scalers
        t3 = time.perf_counter()
        exp1_scalers = load_scalers(args.exp1_scaler_path)
        exp2_scalers = load_scalers(args.exp2_scaler_path)
        t4 = time.perf_counter()
        

        # load expert models
        exp1_model = ResMLPWithAttn(
            in_dim=len(input_cols),
            hidden_dim=args.hidden_dim,
            depth=args.depth,
            dropout_p=args.dropout_p,
            n_heads=args.n_heads,
            out_dim=len(y_cols)
        ).to(device)
        exp1_model.load_state_dict(torch.load(args.exp1_path, map_location=device), strict=False)

        exp2_model = ResMLPWithAttn(
            in_dim=len(input_cols),
            hidden_dim=args.hidden_dim,
            depth=args.depth,
            dropout_p=args.dropout_p,
            n_heads=args.n_heads,
            out_dim=len(y_cols)
        ).to(device)
        exp2_model.load_state_dict(torch.load(args.exp2_path, map_location=device), strict=False)
        t5 = time.perf_counter()
        print(f"[Timing] load.exp.scalers = {(t4-t3)*1000:.2f} ms")
        print(f"[Timing] load.exp.models  = {(t5-t4)*1000:.2f} ms")

    evaluate_al_two_experts(df, input_cols, y_cols,
                            base_model, base_scalers, args, device,
                            exp1_model=exp1_model,
                            exp2_model=exp2_model,
                            exp1_scalers=exp1_scalers,
                            exp2_scalers=exp2_scalers,
                            dataset_name="AlterBBN")
    if args.time_compare:
            if not args.exp:
                raise ValueError("--time_compare requires --exp (and expert models/scalers).")

            for _ in range(max(0, args.warmup)):

                ns = argparse.Namespace(**vars(args))
                ns.exp = False
                evaluate_al_two_experts(df, input_cols, y_cols,
                                        base_model, base_scalers, ns, device,
                                        dataset_name="AlterBBN", quiet=True)
                ns.exp = True
                evaluate_al_two_experts(df, input_cols, y_cols,
                                        base_model, base_scalers, ns, device,
                                        exp1_model=exp1_model, exp2_model=exp2_model,
                                        exp1_scalers=exp1_scalers, exp2_scalers=exp2_scalers,
                                        dataset_name="AlterBBN", quiet=True)
    
            print("\n==== Timing comparison (averaged) ====")
            t_base = 0.0
            for _ in range(max(1, args.repeats)):
                ns = argparse.Namespace(**vars(args)); ns.exp = False
                t0 = time.perf_counter()
                evaluate_al_two_experts(df, input_cols, y_cols,
                                        base_model, base_scalers, ns, device,
                                        dataset_name="AlterBBN", quiet=True)
                t_base += (time.perf_counter() - t0)
            t_base /= max(1, args.repeats)
    
            # exp timing
            t_exp = 0.0
            for _ in range(max(1, args.repeats)):
                ns = argparse.Namespace(**vars(args)); ns.exp = True
                t0 = time.perf_counter()
                evaluate_al_two_experts(df, input_cols, y_cols,
                                        base_model, base_scalers, ns, device,
                                        exp1_model=exp1_model, exp2_model=exp2_model,
                                        exp1_scalers=exp1_scalers, exp2_scalers=exp2_scalers,
                                        dataset_name="AlterBBN", quiet=True)
                t_exp += (time.perf_counter() - t0)
            t_exp /= max(1, args.repeats)
    
            # summary
            _print_timing("COMPARE.base.total", t_base, len(df))
            _print_timing("COMPARE.exp.total",  t_exp,  len(df))
            diff_ms = (t_exp - t_base) * 1000.0
            print(f"[Timing] delta(exp-base) = {_fmt_ms(diff_ms)}")
            return


if __name__ == '__main__':
    main()
