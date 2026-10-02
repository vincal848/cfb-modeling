"""P02: college expected points (EP) and EPA (methodology §3).

Next-scoring-event model: a regularized multinomial logistic regression over the seven
next-score outcomes in the half (P01 labels), with additive linear-spline features of the
preplay state. EP is the expected signed value of the next score:

    EP = sum_k P(k | state) * v_k,  v_TD = touchdown + learned try value, v_FG = field_goal,
    v_SAFETY = safety, with "_AGAINST" outcomes negative and NONE zero.

The try value is learned per fold as the mean try points on training touchdowns (clipped
to the legal 0-2), not fixed at 1 (methodology §3).

EPA for a play i with next scrimmage row j in the same game and half:

- a play with points (either side, try included): EPA = points - EP_i. The next state's
  value is 0: the ensuing kickoff is not modeled, so the score is never counted twice;
- no further scrimmage row in the half: EPA = -EP_i;
- otherwise EPA = sign * EP_j - EP_i, sign = +1 if j's offense is i's offense, else -1.

Everything here is fit inside a fold: callers pass training rows from earlier seasons only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from cfb.state.scoring import ScoringRules
from cfb.state.table import LABELS

YTG_KNOTS = (5, 10, 15, 20, 30, 40, 50, 60, 70, 80, 90)
SEC_KNOTS = (30, 60, 120, 300, 600, 900, 1200, 1500)
MARGIN_KNOTS = (-2, -1, 0, 1, 2)  # in touchdowns (score margin / 7)


def features(df: pd.DataFrame, kind: str = "full") -> np.ndarray:
    """Design matrix (no intercept). `kind="yardline"` is the yard-line-only baseline."""
    ytg = df["yards_to_goal"].clip(1, 99).to_numpy(float)
    cols = [ytg] + [np.maximum(0, ytg - k) for k in YTG_KNOTS]
    if kind == "yardline":
        return np.column_stack(cols)
    down = df["down"].to_numpy()
    dist = np.log(df["distance"].clip(1, 30).to_numpy(float))
    secs = df["seconds_left_half"].clip(0, 1800).to_numpy(float)
    margin = df["score_margin"].clip(-28, 28).to_numpy(float) / 7
    tos = df["offense_timeouts"].fillna(3).clip(0, 3).to_numpy(float)
    cols += [(down == d).astype(float) for d in (2, 3, 4)]
    cols += [dist * (down == d) for d in (1, 2, 3, 4)]
    cols.append((df["distance"].to_numpy(float) >= ytg).astype(float))
    cols += [secs] + [np.maximum(0, secs - k) for k in SEC_KNOTS]
    cols += [margin] + [np.maximum(0, margin - k) for k in MARGIN_KNOTS]
    cols.append((df["half"].to_numpy() == 2).astype(float))
    cols.append(tos)
    return np.column_stack(cols)


def label_index(df: pd.DataFrame) -> np.ndarray:
    lookup = {lab: i for i, lab in enumerate(LABELS)}
    return df["next_score"].map(lookup).to_numpy()


def learned_try_value(train: pd.DataFrame) -> float:
    tries = train["try_points"].dropna().clip(0, 2)
    if tries.empty:
        raise ValueError("no training touchdowns to learn the try value from")
    return float(tries.mean())


def label_values(rules: ScoringRules, try_value: float) -> np.ndarray:
    td = rules.touchdown + try_value
    values = {"TD_FOR": td, "FG_FOR": rules.field_goal, "SAFETY_FOR": rules.safety,
              "TD_AGAINST": -td, "FG_AGAINST": -rules.field_goal, "SAFETY_AGAINST": -rules.safety, "NONE": 0.0}
    return np.array([values[lab] for lab in LABELS])


@dataclass
class EPModel:
    kind: str
    penalty: float
    mean: np.ndarray
    scale: np.ndarray
    coef: np.ndarray  # (features + 1, classes); row 0 is the intercept
    values: np.ndarray
    try_value: float
    train_rows: int
    converged: bool

    def probabilities(self, df: pd.DataFrame) -> np.ndarray:
        x = (features(df, self.kind) - self.mean) / self.scale
        z = self.coef[0] + x @ self.coef[1:]
        z -= z.max(axis=1, keepdims=True)
        p = np.exp(z)
        return p / p.sum(axis=1, keepdims=True)

    def expected_points(self, df: pd.DataFrame) -> np.ndarray:
        return self.probabilities(df) @ self.values


def fit(train: pd.DataFrame, rules: ScoringRules, *, kind: str = "full", penalty: float = 1e-3,
        max_iter: int = 3000) -> EPModel:
    """L2-penalized multinomial logistic regression (intercepts unpenalized), L-BFGS."""
    x_raw = features(train, kind)
    mean, scale = x_raw.mean(axis=0), x_raw.std(axis=0)
    scale[scale == 0] = 1.0
    x = np.column_stack([np.ones(len(x_raw)), (x_raw - mean) / scale])
    y = label_index(train)
    n, f = x.shape
    k = len(LABELS)
    onehot = np.zeros((n, k))
    onehot[np.arange(n), y] = 1.0
    mask = np.ones((f, k))
    mask[0] = 0.0

    def loss_grad(w_flat: np.ndarray) -> tuple[float, np.ndarray]:
        w = w_flat.reshape(f, k)
        z = x @ w
        z -= z.max(axis=1, keepdims=True)
        log_norm = np.log(np.exp(z).sum(axis=1, keepdims=True))
        logp = z - log_norm
        loss = -(onehot * logp).sum() / n + penalty * ((w * mask) ** 2).sum()
        grad = x.T @ (np.exp(logp) - onehot) / n + 2 * penalty * w * mask
        return loss, grad.ravel()

    res = minimize(loss_grad, np.zeros(f * k), jac=True, method="L-BFGS-B",
                   options={"maxiter": max_iter, "gtol": 1e-6})
    return EPModel(kind, penalty, mean, scale, res.x.reshape(f, k),
                   label_values(rules, learned_try_value(train)), learned_try_value(train), n, bool(res.success))


def log_loss(model: EPModel, df: pd.DataFrame) -> np.ndarray:
    p = model.probabilities(df)
    return -np.log(np.clip(p[np.arange(len(df)), label_index(df)], 1e-15, 1.0))


def realized_points(df: pd.DataFrame, values: np.ndarray) -> np.ndarray:
    return values[label_index(df)]


def epa(df: pd.DataFrame, ep: np.ndarray) -> np.ndarray:
    """EPA per row. `df` holds one or more games' scrimmage rows in game order, with
    game_id, half, offense and play_points; `ep` is EP for those rows."""
    out = np.empty(len(df))
    game = df["game_id"].to_numpy()
    half = df["half"].to_numpy()
    off = df["offense"].to_numpy()
    pts = df["play_points"].fillna(0).to_numpy(float)
    for i in range(len(df)):
        if pts[i] != 0:
            out[i] = pts[i] - ep[i]
        elif i + 1 < len(df) and game[i + 1] == game[i] and half[i + 1] == half[i]:
            sign = 1.0 if off[i + 1] == off[i] else -1.0
            out[i] = sign * ep[i + 1] - ep[i]
        else:
            out[i] = -ep[i]
    return out


def save(model: EPModel, path) -> None:
    """Persist a fitted EP model (coefficients, scaling, values) as .npz."""
    np.savez(path, kind=model.kind, penalty=model.penalty, mean=model.mean, scale=model.scale, coef=model.coef,
             values=model.values, try_value=model.try_value, train_rows=model.train_rows, converged=model.converged)


def load(path) -> EPModel:
    d = np.load(path, allow_pickle=False)
    return EPModel(str(d["kind"]), float(d["penalty"]), d["mean"], d["scale"], d["coef"], d["values"],
                   float(d["try_value"]), int(d["train_rows"]), bool(d["converged"]))
