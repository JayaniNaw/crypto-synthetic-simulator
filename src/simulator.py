
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import math
import random
import uuid

import numpy as np
import pandas as pd


AGENT_BEHAVIOURS = {
    "Normal User": ["send_receive", "payment", "daily_transaction"],
    "Merchant": ["accept_payment", "refund", "issue_invoice"],
    "Exchange": ["deposit", "withdrawal", "wallet_creation"],
    "Scammer": ["fake_wallet", "rug_pull", "phishing"],
    "Money Launderer": ["wallet_hopping", "chain_peeling", "mixer_interaction", "smurfing"],
}

LEGITIMATE_ROLES = {"Normal User", "Merchant", "Exchange"}
MALICIOUS_ROLES = {"Scammer", "Money Launderer"}


@dataclass
class Wallet:
    wallet_id: str
    agent_id: str
    agent_type: str
    wallet_age_days: int
    balance: float
    initial_balance: float
    tx_count: int = 0
    last_tx_time: datetime | None = None
    counterparties: set = field(default_factory=set)


@dataclass
class Agent:
    agent_id: str
    agent_type: str
    wallets: List[str]


def _wallet_prefix(role: str) -> str:
    return {
        "Normal User": "U",
        "Merchant": "M",
        "Exchange": "E",
        "Scammer": "S",
        "Money Launderer": "L",
    }[role]


def _new_wallet_id(prefix: str, n: int) -> str:
    return f"{prefix}_{n:04d}"


class CryptoSimulator:
    """
    Version 1 transparent multi-agent synthetic transaction simulator.

    Important research note:
    This V1 is an agent-based behavioural simulator. It DOES NOT claim that the
    decision policy is PPO yet. Agent roles have documented allowed behaviours,
    and transactions are generated from those behaviours. A PPO/MARL policy can
    later replace `choose_behaviour()` without changing the data/EDA/model pipeline.
    """

    def __init__(
        self,
        n_transactions: int = 1000,
        duration_days: int = 30,
        normal_users: int = 10,
        merchants: int = 3,
        exchanges: int = 1,
        scammers: int = 1,
        money_launderers: int = 2,
        seed: int = 42,
    ):
        self.n_transactions = int(n_transactions)
        self.duration_days = int(duration_days)
        self.agent_counts = {
            "Normal User": int(normal_users),
            "Merchant": int(merchants),
            "Exchange": int(exchanges),
            "Scammer": int(scammers),
            "Money Launderer": int(money_launderers),
        }
        self.seed = int(seed)
        self.rng = random.Random(self.seed)
        self.nprng = np.random.default_rng(self.seed)

        self.agents: Dict[str, Agent] = {}
        self.wallets: Dict[str, Wallet] = {}
        self.external_wallets: Dict[str, Wallet] = {}
        self._wallet_serial = {k: 0 for k in self.agent_counts}
        self._create_agents()

        self.current_time = datetime(2026, 1, 1, 9, 0, 0)
        self.end_time = self.current_time + timedelta(days=self.duration_days)
        self.transactions: List[dict] = []
        self.scenarios: List[dict] = []
        self._tx_serial = 0
        self._scenario_serial = 0

    def _create_agents(self):
        for role, count in self.agent_counts.items():
            for i in range(1, count + 1):
                agent_id = f"{_wallet_prefix(role)}A_{i:03d}"
                wallet_count = 1
                # These roles may own several addresses even though they remain one agent type.
                if role == "Scammer":
                    wallet_count = 2
                if role == "Money Launderer":
                    wallet_count = 3

                wids = []
                for _ in range(wallet_count):
                    self._wallet_serial[role] += 1
                    wid = _new_wallet_id(_wallet_prefix(role), self._wallet_serial[role])
                    if role == "Exchange":
                        bal = float(self.nprng.uniform(50, 200))
                    elif role == "Merchant":
                        bal = float(self.nprng.uniform(5, 40))
                    elif role in MALICIOUS_ROLES:
                        bal = float(self.nprng.uniform(2, 25))
                    else:
                        bal = float(self.nprng.uniform(0.5, 12))

                    age = int(self.nprng.integers(5, 1200))
                    self.wallets[wid] = Wallet(
                        wallet_id=wid,
                        agent_id=agent_id,
                        agent_type=role,
                        wallet_age_days=age,
                        balance=bal,
                        initial_balance=bal,
                    )
                    wids.append(wid)

                self.agents[agent_id] = Agent(agent_id=agent_id, agent_type=role, wallets=wids)

        # Mixer is an external service endpoint, not one of the five AI agent types.
        mixer_balance = float(self.nprng.uniform(20, 100))
        self.external_wallets["MIXER_001"] = Wallet(
            wallet_id="MIXER_001",
            agent_id="EXTERNAL_MIXER",
            agent_type="External Service",
            wallet_age_days=1400,
            balance=mixer_balance,
            initial_balance=mixer_balance,
        )

    def _role_wallets(self, role: str) -> List[str]:
        return [w.wallet_id for w in self.wallets.values() if w.agent_type == role]

    def _choose_wallet(self, role: str, exclude: str | None = None) -> Wallet:
        ids = [x for x in self._role_wallets(role) if x != exclude]
        if not ids:
            ids = self._role_wallets(role)
        return self.wallets[self.rng.choice(ids)]

    def _choose_any_wallet(self, exclude: str | None = None, allowed_roles=None) -> Wallet:
        ws = list(self.wallets.values())
        if allowed_roles:
            ws = [w for w in ws if w.agent_type in allowed_roles]
        if exclude:
            ws = [w for w in ws if w.wallet_id != exclude]
        return self.rng.choice(ws)

    def choose_behaviour(self, role: str) -> str:
        """
        Transparent V1 policy. Probabilities create varied behaviour while keeping
        each agent inside the actions defined for its role.
        """
        probs = {
            "Normal User": [0.35, 0.45, 0.20],
            "Merchant": [0.60, 0.25, 0.15],
            "Exchange": [0.45, 0.45, 0.10],
            "Scammer": [0.25, 0.30, 0.45],
            "Money Launderer": [0.30, 0.22, 0.18, 0.30],
        }[role]
        return self.rng.choices(AGENT_BEHAVIOURS[role], weights=probs, k=1)[0]

    def _advance_time(self):
        # Irregular spacing creates realistic temporal variation.
        seconds = int(max(5, self.nprng.lognormal(mean=5.2, sigma=1.0)))
        self.current_time = min(self.current_time + timedelta(seconds=seconds), self.end_time)

    def _safe_amount(self, sender: Wallet, typical: Tuple[float, float]) -> float:
        lo, hi = typical
        amount = float(self.nprng.lognormal(mean=math.log(max(lo, 0.001)), sigma=0.7))
        amount = min(max(amount, lo), hi)
        # Allow simulation liquidity top-ups rather than invalid negative balances.
        if sender.balance < amount + 0.001:
            sender.balance += float(self.nprng.uniform(max(amount, 1), max(amount * 2.5, 2)))
        return round(amount, 8)

    def _record_tx(
        self,
        sender: Wallet,
        receiver: Wallet,
        amount: float,
        transaction_type: str,
        behaviour: str,
        scenario_id: str,
        label: int,
        initiator_role: str,
    ):
        if len(self.transactions) >= self.n_transactions:
            return

        fee = round(max(0.000001, amount * float(self.nprng.uniform(0.0002, 0.0012))), 8)
        sender_before = sender.balance
        receiver_before = receiver.balance
        time_since = (
            (self.current_time - sender.last_tx_time).total_seconds()
            if sender.last_tx_time is not None
            else np.nan
        )

        sender_tx_before = sender.tx_count
        receiver_tx_before = receiver.tx_count
        sender_cp_before = len(sender.counterparties)
        receiver_cp_before = len(receiver.counterparties)

        sender.balance = max(0.0, sender.balance - amount - fee)
        receiver.balance += amount
        sender.tx_count += 1
        receiver.tx_count += 1
        sender.last_tx_time = self.current_time
        receiver.last_tx_time = self.current_time
        sender.counterparties.add(receiver.wallet_id)
        receiver.counterparties.add(sender.wallet_id)

        self._tx_serial += 1
        self.transactions.append(
            {
                "transaction_id": f"TX{self._tx_serial:06d}",
                "timestamp": self.current_time,
                "sender_wallet": sender.wallet_id,
                "receiver_wallet": receiver.wallet_id,
                "amount_btc": amount,
                "transaction_fee_btc": fee,
                "transaction_type": transaction_type,
                "sender_balance_before": round(sender_before, 8),
                "sender_balance_after": round(sender.balance, 8),
                "receiver_balance_before": round(receiver_before, 8),
                "receiver_balance_after": round(receiver.balance, 8),
                "sender_wallet_age_days": sender.wallet_age_days,
                "receiver_wallet_age_days": receiver.wallet_age_days,
                "sender_tx_count_before": sender_tx_before,
                "receiver_tx_count_before": receiver_tx_before,
                "sender_unique_counterparties_before": sender_cp_before,
                "receiver_unique_counterparties_before": receiver_cp_before,
                "time_since_last_tx_seconds": time_since,
                # Simulation provenance: keep for audit/EDA but EXCLUDE from ML inputs.
                "initiating_agent_type": initiator_role,
                "sender_agent_type": sender.agent_type,
                "receiver_agent_type": receiver.agent_type,
                "behaviour": behaviour,
                "scenario_id": scenario_id,
                "fraud_label": int(label),
                "label": "Fraud" if label else "Genuine",
            }
        )
        self._advance_time()

    def _new_scenario(self, behaviour: str, role: str, label: int) -> str:
        self._scenario_serial += 1
        sid = f"SCN{self._scenario_serial:05d}"
        self.scenarios.append(
            {
                "scenario_id": sid,
                "behaviour": behaviour,
                "initiating_agent_type": role,
                "category": "Fraudulent" if label else "Legitimate",
                "ground_truth_label": int(label),
                "start_time": self.current_time,
                "transaction_count": 0,
            }
        )
        return sid

    def _increment_scenario_count(self, sid: str, n: int):
        for x in self.scenarios:
            if x["scenario_id"] == sid:
                x["transaction_count"] += n
                return

    def _generate_for_role(self, role: str):
        behaviour = self.choose_behaviour(role)
        label = 1 if role in MALICIOUS_ROLES else 0
        sid = self._new_scenario(behaviour, role, label)
        before = len(self.transactions)

        if role == "Normal User":
            sender = self._choose_wallet("Normal User")
            if behaviour == "payment":
                receiver = self._choose_wallet("Merchant")
                amount = self._safe_amount(sender, (0.002, 0.25))
                self._record_tx(sender, receiver, amount, "payment", behaviour, sid, label, role)
            elif behaviour == "send_receive":
                receiver = self._choose_wallet("Normal User", exclude=sender.wallet_id)
                amount = self._safe_amount(sender, (0.001, 0.6))
                self._record_tx(sender, receiver, amount, "transfer", behaviour, sid, label, role)
            else:
                receiver = self._choose_any_wallet(
                    exclude=sender.wallet_id,
                    allowed_roles={"Normal User", "Merchant", "Exchange"},
                )
                amount = self._safe_amount(sender, (0.001, 0.18))
                self._record_tx(sender, receiver, amount, "daily_transfer", behaviour, sid, label, role)

        elif role == "Merchant":
            merchant = self._choose_wallet("Merchant")
            user = self._choose_wallet("Normal User")
            if behaviour in {"accept_payment", "issue_invoice"}:
                amount = self._safe_amount(user, (0.003, 0.5))
                self._record_tx(user, merchant, amount, "payment", behaviour, sid, label, role)
            else:
                amount = self._safe_amount(merchant, (0.002, 0.25))
                self._record_tx(merchant, user, amount, "refund", behaviour, sid, label, role)

        elif role == "Exchange":
            exchange = self._choose_wallet("Exchange")
            user = self._choose_wallet("Normal User")
            if behaviour == "deposit":
                amount = self._safe_amount(user, (0.005, 1.2))
                self._record_tx(user, exchange, amount, "deposit", behaviour, sid, label, role)
            elif behaviour == "withdrawal":
                amount = self._safe_amount(exchange, (0.005, 1.2))
                self._record_tx(exchange, user, amount, "withdrawal", behaviour, sid, label, role)
            else:
                # Wallet creation is represented as a tiny activation transfer to a user wallet.
                amount = self._safe_amount(exchange, (0.0001, 0.005))
                self._record_tx(exchange, user, amount, "wallet_activation", behaviour, sid, label, role)

        elif role == "Scammer":
            scam = self._choose_wallet("Scammer")
            victim = self._choose_wallet("Normal User")
            if behaviour == "phishing":
                amount = self._safe_amount(victim, (0.02, 1.6))
                self._record_tx(victim, scam, amount, "transfer", behaviour, sid, label, role)
            elif behaviour == "rug_pull":
                # Several victims transfer to the scammer address.
                for _ in range(self.rng.randint(2, 5)):
                    if len(self.transactions) >= self.n_transactions:
                        break
                    victim = self._choose_wallet("Normal User")
                    amount = self._safe_amount(victim, (0.01, 1.0))
                    self._record_tx(victim, scam, amount, "transfer", behaviour, sid, label, role)
            else:  # fake_wallet
                scam_wallets = self._role_wallets("Scammer")
                receiver_id = self.rng.choice([x for x in scam_wallets if x != scam.wallet_id] or scam_wallets)
                receiver = self.wallets[receiver_id]
                amount = self._safe_amount(victim, (0.01, 0.8))
                self._record_tx(victim, receiver, amount, "transfer", behaviour, sid, label, role)

        elif role == "Money Launderer":
            launder_ids = self._role_wallets("Money Launderer")
            sender = self.wallets[self.rng.choice(launder_ids)]
            if behaviour == "wallet_hopping":
                chain = self.rng.sample(launder_ids, k=min(len(launder_ids), self.rng.randint(2, 4)))
                if chain[0] == sender.wallet_id and len(chain) > 1:
                    pass
                else:
                    chain = [sender.wallet_id] + [x for x in chain if x != sender.wallet_id]
                amt = self._safe_amount(self.wallets[chain[0]], (0.08, 2.5))
                for a, b in zip(chain[:-1], chain[1:]):
                    if len(self.transactions) >= self.n_transactions:
                        break
                    s, r = self.wallets[a], self.wallets[b]
                    amt = min(amt * float(self.nprng.uniform(0.92, 0.995)), max(s.balance * 0.8, 0.001))
                    amt = max(0.001, round(amt, 8))
                    self._record_tx(s, r, amt, "transfer", behaviour, sid, label, role)

            elif behaviour == "smurfing":
                source = sender
                receivers = self.rng.sample(
                    [x for x in launder_ids if x != source.wallet_id],
                    k=min(max(1, len(launder_ids) - 1), self.rng.randint(2, 4)),
                )
                if not receivers:
                    receivers = [self._choose_wallet("Normal User").wallet_id]
                for rid in receivers:
                    if len(self.transactions) >= self.n_transactions:
                        break
                    amount = self._safe_amount(source, (0.01, 0.18))
                    self._record_tx(source, self.wallets[rid], amount, "transfer", behaviour, sid, label, role)

            elif behaviour == "chain_peeling":
                current = sender
                hops = self.rng.randint(2, 4)
                remaining = self._safe_amount(current, (0.2, 2.5))
                for _ in range(hops):
                    if len(self.transactions) >= self.n_transactions:
                        break
                    candidates = [self.wallets[x] for x in launder_ids if x != current.wallet_id]
                    if not candidates:
                        break
                    nxt = self.rng.choice(candidates)
                    peel = max(0.005, remaining * float(self.nprng.uniform(0.10, 0.30)))
                    peel = min(peel, max(current.balance * 0.5, 0.005))
                    self._record_tx(current, nxt, round(peel, 8), "transfer", behaviour, sid, label, role)
                    current = nxt
                    remaining = max(0.005, remaining - peel)

            else:  # mixer_interaction
                mixer = self.external_wallets["MIXER_001"]
                amount = self._safe_amount(sender, (0.05, 2.0))
                self._record_tx(sender, mixer, amount, "transfer", behaviour, sid, label, role)
                if len(self.transactions) < self.n_transactions:
                    dest = self._choose_any_wallet(
                        allowed_roles={"Normal User", "Money Launderer"}
                    )
                    out_amt = min(amount * float(self.nprng.uniform(0.90, 0.98)), mixer.balance * 0.5)
                    self._record_tx(mixer, dest, round(max(out_amt, 0.001), 8), "transfer", behaviour, sid, label, role)

        after = len(self.transactions)
        self._increment_scenario_count(sid, after - before)

    def run(self):
        # Selection weights reflect how often each role initiates an episode,
        # not a hard-coded target fraud ratio.
        roles = list(self.agent_counts.keys())
        activity = {
            "Normal User": 1.00,
            "Merchant": 0.75,
            "Exchange": 0.60,
            "Scammer": 0.35,
            "Money Launderer": 0.45,
        }
        weights = [max(0.01, self.agent_counts[r] * activity[r]) for r in roles]

        while len(self.transactions) < self.n_transactions:
            role = self.rng.choices(roles, weights=weights, k=1)[0]
            self._generate_for_role(role)

        tx = pd.DataFrame(self.transactions).iloc[: self.n_transactions].copy()
        tx["timestamp"] = pd.to_datetime(tx["timestamp"])
        # First transaction per sender gets a neutral value instead of NaN for web display/modeling.
        median_gap = float(tx["time_since_last_tx_seconds"].dropna().median()) if tx["time_since_last_tx_seconds"].notna().any() else 0.0
        tx["time_since_last_tx_seconds"] = tx["time_since_last_tx_seconds"].fillna(median_gap)

        wallets = list(self.wallets.values()) + list(self.external_wallets.values())
        wallet_df = pd.DataFrame(
            [
                {
                    "wallet_id": w.wallet_id,
                    "agent_id": w.agent_id,
                    "agent_type": w.agent_type,
                    "wallet_age_days": w.wallet_age_days,
                    "initial_balance_btc": round(w.initial_balance, 8),
                    "current_balance_btc": round(w.balance, 8),
                    "transaction_count": w.tx_count,
                    "unique_counterparties": len(w.counterparties),
                }
                for w in wallets
            ]
        )
        scenario_df = pd.DataFrame(self.scenarios)
        if not scenario_df.empty:
            scenario_df["start_time"] = pd.to_datetime(scenario_df["start_time"])
        return tx, wallet_df, scenario_df
