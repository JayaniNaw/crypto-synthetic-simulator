# Crypto Transaction Simulator — Version 1.1

This update applies the requested interface and network-graph improvements while preserving the Version 1 simulation, EDA and modelling pipeline.

## Navigation

The main navigation now contains only four button-style pages:

- Simulation
- Network Graph
- EDA
- Modelling

The old Transactions, Download Data and About navigation items were removed.

## Simulation page

The Simulation page now contains:

1. Simulation setup
2. Run / replace simulation button
3. Dataset summary
4. Download Dataset ZIP button immediately above the transaction table
5. Transaction table
6. Agent / Wallet table
7. Optional Scenario / ground-truth table

The large Agent Behaviour card section was removed from the page.

## Refresh / navigation persistence

The generated dataset remains in Streamlit Session State while navigating pages.

V1.1 also writes the latest run to temporary cloud-runtime storage and automatically reloads it after a normal browser refresh. This prevents the table from disappearing just because the user moves between pages or refreshes the browser.

Important: Streamlit Community Cloud can sleep/restart an app. Temporary runtime storage is not guaranteed to survive a full cloud restart. Durable long-term persistence should later use a managed database/object store.

## Network graph

- All graph nodes use the same circle shape.
- Blue = genuine
- Red = fraud-related
- The graph supports zoom/pan plus node selection.
- Clicking a node opens a relationship explorer showing:
  - agent type and status
  - incoming/outgoing connections
  - one-hop neighborhood graph
  - direct relationships and amounts
  - relationship/network pattern indicators
  - simulator ground-truth fraud behaviours involving that node
  - transactions involving the selected node

Pattern indicators are descriptive graph signals, not independent proof of fraud.

## Modelling

The existing leakage protection remains. Agent type, behaviour, scenario, wallet identity and ground-truth label are not used as ML predictors.
