
# Crypto Transaction Simulator — Version 1

A browser-based prototype for the **AI Multi-Agent Cyber Transaction Simulator / Approach 2** workflow.

## Included in V1

- Five agent types only:
  - Normal User
  - Merchant
  - Exchange
  - Scammer
  - Money Launderer
- Agent-specific behaviours
- Synthetic transaction generation
- Automatic simulation ground-truth labels
- Transactions, wallets and scenarios datasets
- Interactive transaction network graph
- EDA dashboard
- Baseline modelling:
  - Logistic Regression
  - Random Forest
  - XGBoost
- Leakage protection: simulation-only fields are excluded from ML predictors
- ZIP/CSV dataset download

## Important research note

This V1 is a **transparent agent-based behavioural simulator**. It intentionally does **not**
claim that the agent decision policy is PPO.

The simulator is structured so that `CryptoSimulator.choose_behaviour()` can later be replaced
with a genuine PPO/MARL policy while preserving the web interface, output schema, EDA and
modelling pipeline. This avoids presenting rule/probability-based behaviour as reinforcement
learning.

## Data tables

### transactions.csv
One row per transaction. Includes observable transaction/wallet features plus simulation
provenance (`behaviour`, agent type, scenario and ground-truth label).

### wallets.csv
Wallet metadata and activity summary.

### scenarios.csv
Simulation episode/scenario provenance and ground-truth category.

## ML leakage protection

The modelling page does **not** use these fields as predictors:

- initiating_agent_type
- sender_agent_type
- receiver_agent_type
- behaviour
- scenario_id
- fraud_label / label
- sender_wallet / receiver_wallet
- transaction_type

They remain available for audit and EDA only.

## Fully-online deployment

See `DEPLOY_ONLINE.md`. Once deployed to Streamlit Community Cloud, simulation, EDA,
network visualisation and model training run on the cloud service. You do not need Python,
VS Code, a database or a local server on your computer.

## Persistence

V1 stores generated datasets in the active Streamlit session. Download the ZIP if you need
to keep a run. Persistent cloud storage (for example a managed database) can be added in V2.

## Research-source alignment

The project specification defines Approach 2 as a simulated cryptocurrency ecosystem with
autonomous agents and lists Normal User, Merchant, Exchange, Scammer and Money Launderer
behaviours. V1 follows that terminology and keeps the wider fraud-detection pipeline separate
from simulation provenance.
