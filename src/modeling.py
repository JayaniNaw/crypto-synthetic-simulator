
from __future__ import annotations

import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, average_precision_score, confusion_matrix,
    f1_score, precision_score, recall_score, roc_auc_score
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split


FEATURE_COLUMNS = [
    "amount_btc",
    "transaction_fee_btc",
    "sender_balance_before",
    "sender_balance_after",
    "receiver_balance_before",
    "receiver_balance_after",
    "sender_wallet_age_days",
    "receiver_wallet_age_days",
    "sender_tx_count_before",
    "receiver_tx_count_before",
    "sender_unique_counterparties_before",
    "receiver_unique_counterparties_before",
    "time_since_last_tx_seconds",
    "hour_sin",
    "hour_cos",
]


def make_model_frame(df: pd.DataFrame):
    x = df.copy()
    ts = pd.to_datetime(x["timestamp"])
    hour = ts.dt.hour + ts.dt.minute / 60.0
    x["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    x["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)

    X = x[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y = x["fraud_label"].astype(int)

    # Deliberately excluded to prevent target leakage:
    # initiating_agent_type, sender_agent_type, receiver_agent_type,
    # behaviour, scenario_id, label, transaction_type, wallet IDs.
    return X, y


def split_70_15_15(X, y, mode="Temporal"):
    if mode == "Temporal":
        n = len(X)
        a = max(1, int(n * 0.70))
        b = max(a + 1, int(n * 0.85))
        return (
            X.iloc[:a], X.iloc[a:b], X.iloc[b:],
            y.iloc[:a], y.iloc[a:b], y.iloc[b:],
        )

    X_train, X_tmp, y_train, y_tmp = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_tmp, y_tmp, test_size=0.50, random_state=42, stratify=y_tmp
    )
    return X_train, X_val, X_test, y_train, y_val, y_test


def build_model(name: str):
    if name == "Logistic Regression":
        return Pipeline([
            ("scale", StandardScaler()),
            ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)),
        ])
    if name == "Random Forest":
        return RandomForestClassifier(
            n_estimators=250,
            max_depth=12,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
    if name == "XGBoost":
        try:
            from xgboost import XGBClassifier
        except Exception as e:
            raise RuntimeError(
                "XGBoost is unavailable in this environment. Use Random Forest or "
                "Logistic Regression, or ensure xgboost is installed."
            ) from e
        return XGBClassifier(
            n_estimators=250,
            max_depth=5,
            learning_rate=0.06,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            random_state=42,
            n_jobs=2,
        )
    raise ValueError(name)


def evaluate_model(name: str, df: pd.DataFrame, split_mode: str = "Temporal"):
    X, y = make_model_frame(df)
    if y.nunique() < 2:
        raise ValueError("The dataset must contain both genuine and fraud labels.")

    Xtr, Xv, Xte, ytr, yv, yte = split_70_15_15(X, y, split_mode)
    model = build_model(name)
    model.fit(Xtr, ytr)

    pred = model.predict(Xte)
    if hasattr(model, "predict_proba"):
        score = model.predict_proba(Xte)[:, 1]
    else:
        score = model.decision_function(Xte)

    metrics = {
        "Accuracy": accuracy_score(yte, pred),
        "Precision": precision_score(yte, pred, zero_division=0),
        "Recall": recall_score(yte, pred, zero_division=0),
        "F1": f1_score(yte, pred, zero_division=0),
        "ROC-AUC": roc_auc_score(yte, score) if yte.nunique() > 1 else float("nan"),
        "PR-AUC": average_precision_score(yte, score) if yte.nunique() > 1 else float("nan"),
    }
    cm = confusion_matrix(yte, pred, labels=[0, 1])

    importance = None
    if name == "Logistic Regression":
        coefs = model.named_steps["model"].coef_[0]
        importance = pd.DataFrame(
            {"feature": FEATURE_COLUMNS, "importance": np.abs(coefs)}
        ).sort_values("importance", ascending=False)
    elif hasattr(model, "feature_importances_"):
        importance = pd.DataFrame(
            {"feature": FEATURE_COLUMNS, "importance": model.feature_importances_}
        ).sort_values("importance", ascending=False)

    return {
        "model": model,
        "metrics": metrics,
        "confusion_matrix": cm,
        "importance": importance,
        "sizes": {"train": len(Xtr), "validation": len(Xv), "test": len(Xte)},
    }
