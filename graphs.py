from __future__ import annotations

import networkx as nx
import pandas as pd
import plotly.graph_objects as go

BLUE = "#2563eb"
RED = "#dc2626"


def build_graph(transactions: pd.DataFrame, wallets: pd.DataFrame) -> nx.DiGraph:
    G = nx.DiGraph()
    wallet_meta = wallets.set_index("wallet_id").to_dict("index") if not wallets.empty else {}
    malicious_roles = {"Scammer", "Money Launderer"}

    for wid, meta in wallet_meta.items():
        role = meta.get("agent_type", "Unknown")
        status = "Fraudulent" if role in malicious_roles or role == "External Service" else "Genuine"
        G.add_node(wid, agent_type=role, fraud_status=status)

    for _, row in transactions.iterrows():
        s, r = row["sender_wallet"], row["receiver_wallet"]
        for node, role_col in [(s, "sender_agent_type"), (r, "receiver_agent_type")]:
            if not G.has_node(node):
                role = row.get(role_col, "Unknown")
                status = "Fraudulent" if role in malicious_roles or role == "External Service" else "Genuine"
                G.add_node(node, agent_type=role, fraud_status=status)

        if G.has_edge(s, r):
            G[s][r]["count"] += 1
            G[s][r]["amount"] += float(row["amount_btc"])
            G[s][r]["fraud_count"] += int(row["fraud_label"])
        else:
            G.add_edge(
                s, r,
                count=1,
                amount=float(row["amount_btc"]),
                fraud_count=int(row["fraud_label"]),
            )
    return G


def network_summary(G: nx.DiGraph) -> dict:
    if G.number_of_nodes() == 0:
        return {"nodes": 0, "edges": 0, "density": 0.0, "avg_degree": 0.0}
    degrees = [d for _, d in G.degree()]
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "density": nx.density(G),
        "avg_degree": sum(degrees) / max(1, len(degrees)),
    }


def network_figure(G: nx.DiGraph, seed: int = 42, max_nodes: int = 90) -> go.Figure:
    if G.number_of_nodes() == 0:
        return go.Figure()

    if G.number_of_nodes() > max_nodes:
        ranked = sorted(G.degree, key=lambda x: x[1], reverse=True)[:max_nodes]
        H = G.subgraph([n for n, _ in ranked]).copy()
    else:
        H = G

    pos = nx.spring_layout(H, seed=seed, k=0.75)
    traces = []

    for fraud_edge, color, name in [
        (False, "#94a3b8", "Genuine relationship"),
        (True, "#f87171", "Fraud relationship"),
    ]:
        x, y = [], []
        for u, v, data in H.edges(data=True):
            is_fraud = data.get("fraud_count", 0) > 0
            if is_fraud != fraud_edge:
                continue
            x.extend([pos[u][0], pos[v][0], None])
            y.extend([pos[u][1], pos[v][1], None])
        if x:
            traces.append(
                go.Scatter(
                    x=x, y=y, mode="lines",
                    line=dict(width=1.3 if fraud_edge else 0.9, color=color),
                    hoverinfo="none", name=name, showlegend=True,
                )
            )

    # Only two node colors; every node uses the same circle shape.
    for status, color in [("Genuine", BLUE), ("Fraudulent", RED)]:
        xs, ys, hover, custom, sizes = [], [], [], [], []
        for node, attrs in H.nodes(data=True):
            if attrs.get("fraud_status") != status:
                continue
            degree = H.degree(node)
            role = attrs.get("agent_type", "Unknown")
            xs.append(pos[node][0])
            ys.append(pos[node][1])
            sizes.append(13 + min(22, degree * 1.5))
            hover.append(
                f"<b>{node}</b><br>Agent type: {role}<br>Status: {status}"
                f"<br>Connections: {degree}<br><i>Click to inspect relationships</i>"
            )
            custom.append([node, role, status])

        if xs:
            traces.append(
                go.Scatter(
                    x=xs, y=ys, mode="markers",
                    marker=dict(symbol="circle", size=sizes, color=color,
                                line=dict(width=1.4, color="white")),
                    text=hover, customdata=custom, hoverinfo="text", name=status,
                )
            )

    fig = go.Figure(data=traces)
    fig.update_layout(
        height=680,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        hovermode="closest",
        clickmode="event+select",
        dragmode="pan",
    )
    return fig


def node_relationship_analysis(node_id: str, transactions: pd.DataFrame, G: nx.DiGraph) -> dict:
    if node_id not in G:
        return {}

    inbound = transactions[transactions["receiver_wallet"] == node_id].copy()
    outbound = transactions[transactions["sender_wallet"] == node_id].copy()
    related = pd.concat([inbound, outbound], ignore_index=True).drop_duplicates("transaction_id")

    predecessors = sorted(G.predecessors(node_id))
    successors = sorted(G.successors(node_id))
    indicators = []

    if len(successors) >= 3:
        indicators.append(f"Fan-out pattern: funds are sent to {len(successors)} different connected wallets.")
    if len(predecessors) >= 3:
        indicators.append(f"Fan-in / aggregation pattern: funds are received from {len(predecessors)} different connected wallets.")

    if not related.empty:
        temp = related.copy()
        temp["counterparty"] = temp.apply(
            lambda r: r["receiver_wallet"] if r["sender_wallet"] == node_id else r["sender_wallet"], axis=1
        )
        repeated = temp["counterparty"].value_counts()
        repeated = repeated[repeated >= 3]
        if not repeated.empty:
            indicators.append(
                f"Repeated relationship pattern: {len(repeated)} counterparty relationship(s) have 3+ transactions."
            )

    if G.in_degree(node_id) >= 1 and G.out_degree(node_id) >= 1:
        indicators.append("Flow-through / hopping candidate: the wallet both receives and forwards funds.")

    if not related.empty and (related["fraud_label"] == 1).any():
        indicators.append(
            f"Ground-truth link: {int((related['fraud_label'] == 1).sum())} connected transaction(s) are fraud-labelled in the simulator."
        )

    behaviours = {}
    if not related.empty and "behaviour" in related.columns:
        behaviours = (
            related.loc[related["fraud_label"] == 1, "behaviour"]
            .dropna().astype(str).value_counts().to_dict()
        )

    rows = []
    for nbr in predecessors:
        data = G[nbr][node_id]
        rows.append({
            "Direction": "Incoming",
            "Connected wallet": nbr,
            "Transactions": data.get("count", 0),
            "Total amount BTC": round(data.get("amount", 0.0), 8),
            "Fraud-labelled transactions": data.get("fraud_count", 0),
        })
    for nbr in successors:
        data = G[node_id][nbr]
        rows.append({
            "Direction": "Outgoing",
            "Connected wallet": nbr,
            "Transactions": data.get("count", 0),
            "Total amount BTC": round(data.get("amount", 0.0), 8),
            "Fraud-labelled transactions": data.get("fraud_count", 0),
        })

    return {
        "node_id": node_id,
        "agent_type": G.nodes[node_id].get("agent_type", "Unknown"),
        "fraud_status": G.nodes[node_id].get("fraud_status", "Unknown"),
        "in_degree": G.in_degree(node_id),
        "out_degree": G.out_degree(node_id),
        "predecessors": predecessors,
        "successors": successors,
        "indicators": indicators,
        "behaviours": behaviours,
        "relationship_table": pd.DataFrame(rows),
        "transactions": related.sort_values("timestamp") if not related.empty else related,
    }


def neighborhood_figure(node_id: str, G: nx.DiGraph, seed: int = 42) -> go.Figure:
    if node_id not in G:
        return go.Figure()

    neighbors = set(G.predecessors(node_id)) | set(G.successors(node_id)) | {node_id}
    H = G.subgraph(neighbors).copy()
    pos = nx.spring_layout(H, seed=seed, k=0.9)

    ex, ey = [], []
    for u, v in H.edges():
        ex.extend([pos[u][0], pos[v][0], None])
        ey.extend([pos[u][1], pos[v][1], None])

    edge = go.Scatter(
        x=ex, y=ey, mode="lines", line=dict(width=1.4, color="#94a3b8"),
        hoverinfo="none", showlegend=False,
    )

    nx_, ny_, colors, sizes, hover, labels = [], [], [], [], [], []
    for node, attrs in H.nodes(data=True):
        nx_.append(pos[node][0])
        ny_.append(pos[node][1])
        colors.append(RED if attrs.get("fraud_status") == "Fraudulent" else BLUE)
        sizes.append(28 if node == node_id else 18)
        labels.append(node_id if node == node_id else "")
        hover.append(
            f"<b>{node}</b><br>{attrs.get('agent_type','Unknown')}<br>{attrs.get('fraud_status','Unknown')}"
        )

    nodes = go.Scatter(
        x=nx_, y=ny_, mode="markers+text", text=labels, textposition="top center",
        marker=dict(size=sizes, color=colors, line=dict(width=1.5, color="white")),
        hovertext=hover, hoverinfo="text", showlegend=False,
    )

    fig = go.Figure([edge, nodes])
    fig.update_layout(
        height=420, margin=dict(l=5, r=5, t=20, b=5),
        xaxis=dict(visible=False), yaxis=dict(visible=False), dragmode="pan",
    )
    return fig
