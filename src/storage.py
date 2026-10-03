from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd


# Cloud-session persistence. This survives normal page navigation and browser
# refreshes while the Streamlit runtime stays alive. Streamlit Community Cloud
# may restart/sleep the runtime, so long-term persistence still needs a managed
# database/object store in a later version.
DATA_DIR = Path(os.environ.get("CRYPTO_SIM_DATA_DIR", "/tmp/crypto_simulator_v1_1"))


def save_latest_run(
    transactions: pd.DataFrame,
    wallets: pd.DataFrame,
    scenarios: pd.DataFrame,
    config: dict,
) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    transactions.to_csv(DATA_DIR / "transactions.csv", index=False)
    wallets.to_csv(DATA_DIR / "wallets.csv", index=False)
    scenarios.to_csv(DATA_DIR / "scenarios.csv", index=False)
    with open(DATA_DIR / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def load_latest_run():
    tx_path = DATA_DIR / "transactions.csv"
    wallet_path = DATA_DIR / "wallets.csv"
    scenario_path = DATA_DIR / "scenarios.csv"
    config_path = DATA_DIR / "config.json"

    if not (tx_path.exists() and wallet_path.exists() and scenario_path.exists()):
        return None

    try:
        tx = pd.read_csv(tx_path)
        wallets = pd.read_csv(wallet_path)
        scenarios = pd.read_csv(scenario_path)

        if "timestamp" in tx.columns:
            tx["timestamp"] = pd.to_datetime(tx["timestamp"], errors="coerce")
        if "start_time" in scenarios.columns:
            scenarios["start_time"] = pd.to_datetime(scenarios["start_time"], errors="coerce")

        config = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

        return tx, wallets, scenarios, config
    except Exception:
        return None
