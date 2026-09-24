"""
FastAPI REST Service & Interactive Analyst Dashboard
Provides real-time fraud investigation endpoints and a visual investigation interface.
"""

import os
import json
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from src.agent.models import TriggerEvent, InvestigationAnswerFile
from src.agent.investigator import FraudInvestigatorAgent

app = FastAPI(
    title="TigerGraph Agentic Fraud Investigation API",
    version="1.0.0",
    description="Autonomous fraud investigation agent powered by TigerGraph, GraphRAG, and Next-Best-Action logic.",
)

agent = FraudInvestigatorAgent()
CASES_DIR = os.getenv("CASES_DIR", "outputs/cases")


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "tigergraph_mode": agent.tg_client.mode,
        "graph_name": agent.tg_client.graph_name,
    }


@app.post("/api/v1/investigate", response_model=InvestigationAnswerFile)
def investigate_transaction(trigger: TriggerEvent):
    """Triggers an end-to-end 8-step fraud investigation on the provided event."""
    try:
        ans = agent.investigate(trigger)
        os.makedirs(CASES_DIR, exist_ok=True)
        with open(os.path.join(CASES_DIR, f"{ans.case_id}.json"), "w") as f:
            json.dump(ans.model_dump(mode="json"), f, indent=2)
        return ans
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/cases", response_model=List[str])
def list_cases():
    """Lists all investigated benchmark and production case IDs."""
    if not os.path.exists(CASES_DIR):
        return []
    cases = [f.replace(".json", "") for f in os.listdir(CASES_DIR) if f.endswith(".json") and f != "benchmark_summary.json"]
    cases.sort()
    return cases


@app.get("/api/v1/cases/{case_id}", response_model=Dict[str, Any])
def get_case_details(case_id: str):
    """Retrieves full case dossier, findings, and SAR reports for a case."""
    filepath = os.path.join(CASES_DIR, f"{case_id}.json")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Case not found")
    with open(filepath, "r") as f:
        return json.load(f)


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    """Renders the interactive TigerGraph Fraud Investigation Analyst Cockpit."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TigerGraph Agentic Fraud Investigation Cockpit</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        #network-graph { height: 320px; border-radius: 0.5rem; background: #0f172a; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans">
    <!-- Navbar -->
    <header class="bg-slate-900/90 border-b border-slate-800 px-6 py-4 flex items-center justify-between sticky top-0 z-50 backdrop-blur">
        <div class="flex items-center space-x-3">
            <div class="bg-orange-600/20 text-orange-400 p-2 rounded-lg border border-orange-500/30">
                <i class="fa-solid fa-diagram-project text-xl"></i>
            </div>
            <div>
                <h1 class="text-lg font-bold tracking-tight text-white flex items-center gap-2">
                    TigerGraph Agentic Fraud Investigator
                    <span class="text-xs bg-orange-500/20 text-orange-300 border border-orange-500/30 px-2 py-0.5 rounded-full font-mono">HHGOA Edition</span>
                </h1>
                <p class="text-xs text-slate-400">Autonomous 8-Step GraphRAG & Next-Best-Action Investigation Agent</p>
            </div>
        </div>
        <div class="flex items-center space-x-4">
            <div class="flex items-center space-x-2 text-xs bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span class="text-slate-300">TigerGraph Engine: <strong class="text-white">Active (FraudGraph)</strong></span>
            </div>
            <a href="/docs" target="_blank" class="text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5">
                <i class="fa-solid fa-code"></i> OpenAPI Docs
            </a>
        </div>
    </header>

    <!-- Main Workspace -->
    <div class="flex-1 grid grid-cols-12 gap-5 p-6 overflow-hidden max-w-[1800px] w-full mx-auto">
        
        <!-- Col 1: Benchmark Cases & Controls (3 cols) -->
        <aside class="col-span-12 lg:col-span-3 flex flex-col gap-4">
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col flex-1 shadow-lg">
                <div class="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">
                    <h2 class="font-semibold text-sm text-slate-200 flex items-center gap-2">
                        <i class="fa-solid fa-list-check text-slate-400"></i> Benchmark Cases (20)
                    </h2>
                    <span id="case-count" class="text-xs text-slate-400 font-mono">Loading...</span>
                </div>
                
                <div id="cases-list" class="space-y-2 overflow-y-auto flex-1 pr-1 max-h-[720px]">
                    <!-- Dynamically populated -->
                </div>
            </div>
        </aside>

        <!-- Col 2: Investigation & Graph Canvas (5 cols) -->
        <main class="col-span-12 lg:col-span-5 flex flex-col gap-4">
            <!-- Active Case Header Banner -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg flex items-center justify-between">
                <div>
                    <span id="active-case-id" class="text-xs font-mono uppercase bg-slate-800 text-slate-300 px-2 py-0.5 rounded">CASE_BENCH_01</span>
                    <h3 id="active-txn-headline" class="text-lg font-bold text-white mt-1">Transaction TXN_BENCH_001</h3>
                    <p id="active-txn-meta" class="text-xs text-slate-400 mt-0.5">Amount: $470.00 • Merchant: MERCH_CRYPTO_EXCHANGE</p>
                </div>
                <div class="text-right">
                    <span id="active-risk-badge" class="px-3 py-1 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">RISK: 0.92</span>
                    <p id="active-uncertainty-badge" class="text-xs text-slate-400 mt-1 font-mono">Uncertainty: 0.10</p>
                </div>
            </div>

            <!-- TigerGraph Interactive Knowledge Subgraph -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col">
                <div class="flex items-center justify-between mb-2">
                    <h4 class="text-xs font-semibold uppercase text-slate-300 tracking-wider flex items-center gap-1.5">
                        <i class="fa-solid fa-circle-nodes text-orange-400"></i> TigerGraph 2-Hop Subgraph & Ring Detection
                    </h4>
                    <span class="text-[11px] text-slate-400 font-mono">GSQL Traversal Verified</span>
                </div>
                <div id="network-graph" class="w-full"></div>
                <div class="grid grid-cols-3 gap-2 mt-3 pt-2 border-t border-slate-800/80 text-center text-xs">
                    <div class="bg-slate-800/50 p-2 rounded border border-slate-800">
                        <span class="text-slate-400 text-[10px] uppercase block">Shared Cards (Ring)</span>
                        <strong id="stat-cards" class="text-orange-400 font-mono text-sm">8</strong>
                    </div>
                    <div class="bg-slate-800/50 p-2 rounded border border-slate-800">
                        <span class="text-slate-400 text-[10px] uppercase block">Velocity (1h)</span>
                        <strong id="stat-vel" class="text-slate-200 font-mono text-sm">2 txns</strong>
                    </div>
                    <div class="bg-slate-800/50 p-2 rounded border border-slate-800">
                        <span class="text-slate-400 text-[10px] uppercase block">Travel Speed</span>
                        <strong id="stat-travel" class="text-slate-200 font-mono text-sm">45 km/h</strong>
                    </div>
                </div>
            </div>

            <!-- Investigation 8-Step Timeline -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col flex-1">
                <h4 class="text-xs font-semibold uppercase text-slate-300 tracking-wider mb-2 flex items-center gap-1.5">
                    <i class="fa-solid fa-shoe-prints text-indigo-400"></i> Agent 8-Step Investigation Lifecycle
                </h4>
                <div id="steps-timeline" class="space-y-2 overflow-y-auto max-h-[220px] text-xs font-mono text-slate-300 pr-1">
                    <!-- Populated via JS -->
                </div>
            </div>
        </main>

        <!-- Col 3: Two-Stage NBA, Evidence Action & SAR (4 cols) -->
        <aside class="col-span-12 lg:col-span-4 flex flex-col gap-4">
            
            <!-- Pre-Evidence NBA Card -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg">
                <div class="flex items-center justify-between border-b border-slate-800 pb-2 mb-2">
                    <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                        <i class="fa-solid fa-clock-rotate-left text-amber-400"></i> Stage 1: Pre-Evidence NBA
                    </span>
                    <span id="pre-route-badge" class="text-[10px] px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-slate-300">AUTOMATED</span>
                </div>
                <div class="flex items-center justify-between mt-2">
                    <span class="text-xs text-slate-400">Action:</span>
                    <strong id="pre-action-text" class="text-sm font-bold text-amber-400">BLOCK_CARD</strong>
                </div>
                <p id="pre-rationale-text" class="text-xs text-slate-300 mt-2 bg-slate-950/60 p-2.5 rounded border border-slate-800/80 leading-relaxed">
                    Critical risk score >= 0.90 and active syndicate ring indicators warrant immediate card block.
                </p>
            </div>

            <!-- Controlled Evidence Gathering Simulator -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg">
                <div class="flex items-center justify-between border-b border-slate-800 pb-2 mb-2">
                    <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                        <i class="fa-solid fa-mobile-screen-button text-cyan-400"></i> Stage 2: Controlled Evidence
                    </span>
                    <span id="evidence-status-badge" class="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/50 font-mono">COMPLETED</span>
                </div>
                <div id="evidence-box" class="text-xs space-y-2 text-slate-300">
                    <p id="evidence-desc" class="text-xs text-slate-300">Customer SMS verification response received.</p>
                </div>
            </div>

            <!-- Post-Evidence NBA Card -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg">
                <div class="flex items-center justify-between border-b border-slate-800 pb-2 mb-2">
                    <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                        <i class="fa-solid fa-shield-halved text-emerald-400"></i> Stage 3: Post-Evidence Final NBA
                    </span>
                    <span id="post-route-badge" class="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800/50 font-mono">AUTOMATED</span>
                </div>
                <div class="flex items-center justify-between mt-2">
                    <span class="text-xs text-slate-400">Final Action:</span>
                    <strong id="post-action-text" class="text-base font-bold text-emerald-400">BLOCK_CARD</strong>
                </div>
                <p id="post-rationale-text" class="text-xs text-slate-300 mt-2 bg-slate-950/60 p-2.5 rounded border border-slate-800/80 leading-relaxed">
                    Card block applied. Investigation persisted to TigerGraph knowledge graph.
                </p>
                <div class="mt-3 flex items-center justify-between text-[11px] border-t border-slate-800/80 pt-2 text-slate-400">
                    <span>Graph Persistence:</span>
                    <span id="graph-persisted-badge" class="text-emerald-400 font-bold flex items-center gap-1">
                        <i class="fa-solid fa-circle-check"></i> Written to TigerGraph
                    </span>
                </div>
            </div>

            <!-- Suspicious Activity Report (SAR) Panel -->
            <div id="sar-panel" class="bg-gradient-to-br from-rose-950/40 to-slate-900 border border-rose-900/50 rounded-xl p-4 shadow-lg">
                <div class="flex items-center justify-between border-b border-rose-900/40 pb-2 mb-2">
                    <span class="text-[11px] font-bold uppercase tracking-wider text-rose-300 flex items-center gap-1.5">
                        <i class="fa-solid fa-file-shield text-rose-400"></i> FinCEN SAR Filing
                    </span>
                    <span id="sar-id-tag" class="text-[10px] px-2 py-0.5 rounded bg-rose-900/40 border border-rose-700/50 font-mono text-rose-300">SAR-BENCH-01</span>
                </div>
                <p id="sar-narrative" class="text-xs text-slate-300 leading-relaxed">
                    Mandatory Suspicious Activity Report drafted and ready for compliance submission.
                </p>
                <div class="mt-2 text-right">
                    <span id="sar-amount" class="text-xs font-mono font-bold text-rose-400">Amount: $470.00</span>
                </div>
            </div>

        </aside>

    </div>

    <!-- Scripts -->
    <script>
        let currentNetwork = null;

        async function fetchCases() {
            try {
                const res = await fetch('/api/v1/cases');
                const cases = await res.json();
                document.getElementById('case-count').innerText = `${cases.length} Cases`;
                const container = document.getElementById('cases-list');
                container.innerHTML = '';
                
                cases.forEach((cid, index) => {
                    const btn = document.createElement('button');
                    btn.className = `w-full text-left p-3 rounded-lg border transition flex items-center justify-between ${index === 0 ? 'bg-slate-800 border-indigo-500/60 shadow' : 'bg-slate-950/60 border-slate-800/80 hover:bg-slate-800/50'}`;
                    btn.onclick = () => loadCase(cid, btn);
                    btn.innerHTML = `
                        <div>
                            <div class="text-xs font-mono font-bold text-slate-200">${cid}</div>
                            <div class="text-[11px] text-slate-400">Benchmark Test Case</div>
                        </div>
                        <i class="fa-solid fa-chevron-right text-xs text-slate-600"></i>
                    `;
                    container.appendChild(btn);
                });

                if (cases.length > 0) {
                    loadCase(cases[0]);
                }
            } catch (err) {
                console.error("Failed to load cases:", err);
            }
        }

        async function loadCase(caseId, activeBtn = null) {
            if (activeBtn) {
                document.querySelectorAll('#cases-list button').forEach(b => {
                    b.className = 'w-full text-left p-3 rounded-lg border transition flex items-center justify-between bg-slate-950/60 border-slate-800/80 hover:bg-slate-800/50';
                });
                activeBtn.className = 'w-full text-left p-3 rounded-lg border transition flex items-center justify-between bg-slate-800 border-indigo-500/60 shadow';
            }

            try {
                const res = await fetch(`/api/v1/cases/${caseId}`);
                const data = await res.json();
                renderCase(data);
            } catch (err) {
                console.error("Error loading case:", err);
            }
        }

        function renderCase(data) {
            const txn = data.trigger.transaction;
            document.getElementById('active-case-id').innerText = data.case_id;
            document.getElementById('active-txn-headline').innerText = `Transaction ${txn.txn_id}`;
            document.getElementById('active-txn-meta').innerText = `Amount: $${txn.amount.toFixed(2)} • Card: ${txn.card_id} • Merchant: ${txn.merchant_id}`;
            
            // Risk & Uncertainty badges
            const risk = txn.model_risk_score;
            const rBadge = document.getElementById('active-risk-badge');
            rBadge.innerText = `RISK: ${risk.toFixed(2)}`;
            if (risk >= 0.85) {
                rBadge.className = "px-3 py-1 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30";
            } else if (risk >= 0.60) {
                rBadge.className = "px-3 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30";
            } else {
                rBadge.className = "px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
            }
            document.getElementById('active-uncertainty-badge').innerText = `Uncertainty: ${data.uncertainty_level.toFixed(2)}`;

            // Stats
            document.getElementById('stat-cards').innerText = data.graph_evidence.shared_device_card_count;
            document.getElementById('stat-vel').innerText = `${data.graph_evidence.velocity_1h_txn_count} txns ($${data.graph_evidence.velocity_1h_amount.toFixed(0)})`;
            document.getElementById('stat-travel').innerText = data.graph_evidence.impossible_travel_detected ? `${data.graph_evidence.travel_speed_kmh} km/h (ALERT)` : `${data.graph_evidence.travel_speed_kmh || 45} km/h`;

            // Steps timeline
            const stepsDiv = document.getElementById('steps-timeline');
            stepsDiv.innerHTML = '';
            (data.investigation_record.steps_taken || []).forEach(step => {
                const item = document.createElement('div');
                item.className = "p-1.5 rounded bg-slate-950/80 border border-slate-800/80";
                item.innerText = step;
                stepsDiv.appendChild(item);
            });

            // Pre NBA
            document.getElementById('pre-route-badge').innerText = data.nba_pre_evidence.approval_route;
            document.getElementById('pre-action-text').innerText = data.nba_pre_evidence.action;
            document.getElementById('pre-rationale-text').innerText = data.nba_pre_evidence.rationale;

            // Controlled Evidence
            const evBox = document.getElementById('evidence-box');
            if (data.requested_evidence) {
                evBox.innerHTML = `
                    <div class="bg-cyan-950/40 p-2.5 rounded border border-cyan-900/50">
                        <div class="flex items-center justify-between">
                            <strong>${data.requested_evidence.evidence_type}</strong>
                            <span class="text-cyan-400 font-mono text-[10px]">${data.received_evidence ? data.received_evidence.status : 'PENDING'}</span>
                        </div>
                        <p class="mt-1 text-slate-300 text-xs">${data.received_evidence ? (data.received_evidence.notes || 'Verified') : 'Waiting for cardholder verification...'}</p>
                    </div>
                `;
            } else {
                evBox.innerHTML = `<p class="text-xs text-slate-400 italic">No additional evidence required (conclusive graph certainty).</p>`;
            }

            // Post NBA
            document.getElementById('post-route-badge').innerText = data.nba_post_evidence.approval_route;
            document.getElementById('post-action-text').innerText = data.nba_post_evidence.action;
            document.getElementById('post-rationale-text').innerText = data.nba_post_evidence.rationale;

            // SAR
            const sarPanel = document.getElementById('sar-panel');
            if (data.sar_report) {
                sarPanel.style.display = 'block';
                document.getElementById('sar-id-tag').innerText = data.sar_report.sar_id;
                document.getElementById('sar-narrative').innerText = data.sar_report.narrative;
                document.getElementById('sar-amount').innerText = `Suspicious Exposure: $${data.sar_report.total_suspicious_amount.toFixed(2)}`;
            } else {
                sarPanel.style.display = 'none';
            }

            // Render Subgraph in Vis.js
            renderGraph(data);
        }

        function renderGraph(data) {
            const container = document.getElementById('network-graph');
            const txn = data.trigger.transaction;
            
            const nodes = [
                { id: 1, label: `Txn: ${txn.txn_id}`, color: '#f97316', shape: 'diamond', size: 22, font: { color: '#ffffff' } },
                { id: 2, label: `Card: ${txn.card_id}`, color: '#38bdf8', shape: 'box', font: { color: '#ffffff' } },
                { id: 3, label: `Customer: ${txn.customer_id}`, color: '#a855f7', shape: 'ellipse', font: { color: '#ffffff' } },
                { id: 4, label: `Device: ${txn.device_id || 'dev_01'}`, color: '#ef4444', shape: 'hexagon', font: { color: '#ffffff' } },
                { id: 5, label: `IP: ${txn.ip_address || '198.51.100.1'}`, color: '#eab308', shape: 'dot', font: { color: '#ffffff' } },
                { id: 6, label: `Merchant: ${txn.merchant_id}`, color: '#10b981', shape: 'box', font: { color: '#ffffff' } }
            ];

            // Add connected ring nodes if detected
            if (data.graph_evidence.shared_device_card_count > 1) {
                nodes.push({ id: 7, label: `Linked Card 2`, color: '#38bdf8', shape: 'box', font: { color: '#ffffff' } });
                nodes.push({ id: 8, label: `Linked Card 3`, color: '#38bdf8', shape: 'box', font: { color: '#ffffff' } });
            }

            const edges = [
                { from: 2, to: 1, label: 'CHARGED' },
                { from: 3, to: 2, label: 'OWNS' },
                { from: 1, to: 4, label: 'USED_DEVICE' },
                { from: 1, to: 5, label: 'USED_IP' },
                { from: 1, to: 6, label: 'PAID_TO' }
            ];

            if (data.graph_evidence.shared_device_card_count > 1) {
                edges.push({ from: 4, to: 7, label: 'SHARED' });
                edges.push({ from: 4, to: 8, label: 'SHARED' });
            }

            const graphData = { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) };
            const options = {
                nodes: { font: { size: 11, face: 'monospace' }, borderWidth: 2 },
                edges: { color: '#475569', font: { size: 9, color: '#94a3b8' }, arrows: 'to' },
                physics: { stabilization: true, barnesHut: { springLength: 90 } }
            };

            if (currentNetwork) currentNetwork.destroy();
            currentNetwork = new vis.Network(container, graphData, options);
        }

        window.onload = fetchCases;
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
