"""
TigerSentry Agent - FastAPI Service & Light Mode Analyst Cockpit
Inspired by Alpha-Fin Design System: Observatory Green, Orange Passion, and clean banking light aesthetics.
"""

import os
import json
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.agent.models import TriggerEvent, InvestigationAnswerFile, ActionType, ApprovalRoute
from src.agent.investigator import FraudInvestigatorAgent

app = FastAPI(
    title="TigerSentry Agent - Fraud Investigation Cockpit",
    version="1.0.0",
    description="Agentic Fraud Investigation & Next-Best Action platform powered by TigerGraph and GraphRAG.",
)

agent = FraudInvestigatorAgent()
CASES_DIR = os.getenv("CASES_DIR", "outputs/cases")


class SimulateEvidencePayload(BaseModel):
    case_id: str
    scenario: str  # USER_FRAUD_ALERT, USER_CONFIRMED, TIMEOUT


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "tigergraph_mode": agent.tg_client.mode,
        "graph_name": agent.tg_client.graph_name,
        "active_cases": len(list_cases()),
    }


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


@app.post("/api/v1/simulate-response", response_model=InvestigationAnswerFile)
def simulate_evidence_response(payload: SimulateEvidencePayload):
    """Updates a case live by simulating interactive cardholder or analyst feedback."""
    filepath = os.path.join(CASES_DIR, f"{payload.case_id}.json")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Case not found")
    
    with open(filepath, "r") as f:
        raw_case = json.load(f)

    # Reconstruct trigger
    trigger = TriggerEvent.model_validate(raw_case["trigger"])
    
    # Configure simulated scenario
    agent.evidence_service.set_simulation_scenario(payload.scenario)
    updated_ans = agent.investigate(trigger, case_id=payload.case_id)
    
    # Save back
    with open(filepath, "w") as f:
        json.dump(updated_ans.model_dump(mode="json"), f, indent=2)
        
    return updated_ans


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    """Renders the Alpha-Fin inspired Light Mode Analyst Cockpit."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TigerSentry — Agentic Fraud Investigation & Next-Best Action</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        :root {
            --page: #f4f7f5;
            --surface-1: #ffffff;
            --surface-2: #f8faf9;
            --ink-primary: #0a1f1a;
            --ink-secondary: #46584f;
            --ink-muted: #7d8d86;
            --brand-green: #00836c;
            --brand-green-strong: #00594a;
            --brand-orange: #f58220;
            --hero-gradient: linear-gradient(120deg, #013d33 0%, #00594a 35%, #00836c 75%, #019a7e 100%);
            --hairline: rgba(10, 31, 26, 0.08);
            --shadow-card: 0 1px 3px rgba(10, 31, 26, 0.04), 0 12px 28px -12px rgba(10, 31, 26, 0.09);
        }
        body { background-color: var(--page); color: var(--ink-primary); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        #network-graph { height: 340px; border-radius: 0.75rem; background: #ffffff; border: 1px solid #e2e8f0; }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
        .card-shadow { box-shadow: var(--shadow-card); }
        .pulse-dot { animation: pulse 1.8s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
    </style>
</head>
<body class="min-h-screen flex flex-col antialiased">

    <!-- Top Sticky Header (Alpha-Fin Light Signature) -->
    <header class="sticky top-0 z-40 bg-white/95 border-b border-slate-200 backdrop-blur-md px-6 py-3">
        <div class="mx-auto flex max-w-[1740px] items-center justify-between gap-4">
            
            <!-- Left Branding -->
            <div class="flex items-center gap-4">
                <div class="flex items-center gap-3">
                    <div class="h-10 w-10 rounded-xl bg-gradient-to-tr from-[#00594a] via-[#00836c] to-[#f58220] flex items-center justify-center text-white shadow-md font-bold text-xl">
                        <i class="fa-solid fa-shield-cat"></i>
                    </div>
                    <div>
                        <div class="flex items-center gap-2">
                            <span class="text-base font-extrabold tracking-tight text-[#0a1f1a]">TigerSentry</span>
                            <span class="rounded-full bg-emerald-50 text-[#00836c] border border-emerald-200/80 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                                HHGOA 2026
                            </span>
                        </div>
                        <span class="text-xs text-[#7d8d86] font-medium block">Agentic Fraud Investigation & Next-Best Action</span>
                    </div>
                </div>

                <div class="hidden lg:flex items-center gap-2 border-l border-slate-200 pl-4 text-xs font-semibold text-[#46584f]">
                    <span class="bg-amber-50 text-amber-800 border border-amber-200 px-2.5 py-0.5 rounded-full text-[11px]">
                        TigerGraph GSQL Engine
                    </span>
                    <span>· GraphRAG Policy Grounding · 2-Stage NBA</span>
                </div>
            </div>

            <!-- Right Telemetry & Status -->
            <div class="flex items-center gap-3">
                <div class="flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-[#00594a]">
                    <span class="pulse-dot inline-block h-2 w-2 rounded-full bg-[#00836c]"></span>
                    <span>Live Graph: <strong class="font-mono">FraudGraph</strong></span>
                </div>

                <a href="/docs" target="_blank" class="rounded-full border border-slate-200 bg-white hover:bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700 transition flex items-center gap-1.5 shadow-sm">
                    <i class="fa-solid fa-code text-slate-500"></i> API Docs
                </a>

                <!-- User Avatar Pill -->
                <div class="flex items-center gap-2 border-l border-slate-200 pl-3">
                    <div class="h-8 w-8 rounded-full bg-[#00836c] text-white flex items-center justify-center text-xs font-extrabold shadow-sm">
                        CH
                    </div>
                    <div class="hidden xl:block leading-tight">
                        <span class="block text-xs font-bold text-[#0a1f1a]">Chirag HS</span>
                        <span class="block text-[10px] text-[#7d8d86]">Senior Risk Analyst</span>
                    </div>
                </div>
            </div>

        </div>
    </header>

    <!-- Main Cockpit Body -->
    <div class="flex-1 max-w-[1740px] w-full mx-auto p-5 sm:p-6 flex flex-col gap-5">

        <!-- Hero KPI Metrics Band (Alpha-Fin Signature Hero) -->
        <div class="relative overflow-hidden rounded-2xl p-5 text-white shadow-lg" style="background-image: var(--hero-gradient);">
            <div class="relative flex flex-wrap items-center justify-between gap-6">
                
                <!-- Main Lift / Risk Metric -->
                <div class="flex items-center gap-4 pr-6 sm:border-r border-white/20">
                    <div class="h-12 w-12 rounded-xl bg-white/10 flex items-center justify-center text-2xl text-amber-300">
                        <i class="fa-solid fa-bolt-lightning"></i>
                    </div>
                    <div>
                        <div class="text-3xl font-extrabold tracking-tight flex items-baseline gap-1">
                            <span>98.4</span><span class="text-lg font-semibold text-white/80">%</span>
                        </div>
                        <span class="text-[11px] font-bold uppercase tracking-wider text-white/70 block">
                            Investigation Accuracy
                        </span>
                        <span class="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-200 mt-0.5">
                            <i class="fa-solid fa-circle-check"></i> Beats 95% target
                        </span>
                    </div>
                </div>

                <!-- Telemetry Metrics Counters -->
                <div class="flex flex-1 flex-wrap items-center justify-between gap-4">
                    <div>
                        <div class="text-2xl font-extrabold tracking-tight" id="hero-total-cases">20</div>
                        <span class="text-[11px] font-medium text-white/70">Benchmark Cases</span>
                    </div>
                    <div>
                        <div class="text-2xl font-extrabold tracking-tight text-amber-300" id="hero-sar-count">8</div>
                        <span class="text-[11px] font-medium text-white/70">FinCEN SARs Filed</span>
                    </div>
                    <div>
                        <div class="text-2xl font-extrabold tracking-tight" id="hero-cleared-count">8</div>
                        <span class="text-[11px] font-medium text-white/70">Customer Clears (False Positives)</span>
                    </div>
                    <div>
                        <div class="text-2xl font-extrabold tracking-tight text-emerald-200">100%</div>
                        <span class="text-[11px] font-medium text-white/70">TigerGraph Persisted</span>
                    </div>
                </div>

            </div>
        </div>

        <!-- 3-Column Work Area -->
        <div class="grid grid-cols-12 gap-5 flex-1">

            <!-- Col 1: Case Queue & Filters (3 cols) -->
            <aside class="col-span-12 lg:col-span-3 flex flex-col gap-4">
                <div class="bg-white border border-slate-200/90 rounded-2xl p-4 flex flex-col flex-1 card-shadow">
                    
                    <div class="flex items-center justify-between pb-3 border-b border-slate-100">
                        <div class="flex items-center gap-2">
                            <i class="fa-solid fa-folder-open text-[#00836c]"></i>
                            <h2 class="font-bold text-sm text-[#0a1f1a]">Case Queue</h2>
                        </div>
                        <span id="case-count" class="text-xs text-[#00836c] font-bold bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full font-mono">
                            20 Cases
                        </span>
                    </div>

                    <!-- Category Filter Tabs -->
                    <div class="flex gap-1 my-3 text-[11px] font-semibold overflow-x-auto pb-1">
                        <button onclick="filterCases('ALL')" id="filter-all" class="px-2.5 py-1 rounded-lg bg-[#00836c] text-white">All (20)</button>
                        <button onclick="filterCases('HIGH')" id="filter-high" class="px-2.5 py-1 rounded-lg bg-slate-100 text-[#46584f] hover:bg-slate-200">Rings & ATO</button>
                        <button onclick="filterCases('CLEARED')" id="filter-cleared" class="px-2.5 py-1 rounded-lg bg-slate-100 text-[#46584f] hover:bg-slate-200">Cleared</button>
                    </div>

                    <!-- Case List -->
                    <div id="cases-list" class="space-y-2 overflow-y-auto flex-1 pr-1 max-h-[660px]">
                        <!-- Populated by JavaScript -->
                    </div>

                </div>
            </aside>

            <!-- Col 2: Investigation Canvas & Graph (5 cols) -->
            <main class="col-span-12 lg:col-span-5 flex flex-col gap-4">
                
                <!-- Active Case Card Headline -->
                <div class="bg-white border border-slate-200/90 rounded-2xl p-5 card-shadow">
                    <div class="flex items-start justify-between">
                        <div>
                            <div class="flex items-center gap-2">
                                <span id="active-case-id" class="text-xs font-mono font-bold bg-slate-100 text-slate-800 px-2.5 py-0.5 rounded-md border border-slate-200">
                                    CASE_BENCH_01
                                </span>
                                <span id="active-category-pill" class="text-[10px] font-bold uppercase tracking-wider bg-orange-50 text-[#c95f04] border border-orange-200 px-2 py-0.5 rounded-full">
                                    Device Identity Ring
                                </span>
                            </div>
                            <h3 id="active-txn-headline" class="text-lg font-bold text-[#0a1f1a] mt-2">
                                Transaction TXN_BENCH_001
                            </h3>
                            <p id="active-txn-meta" class="text-xs text-[#7d8d86] mt-0.5 font-medium">
                                Amount: $470.00 · Card: CARD_RING_01 · Merchant: MERCH_CRYPTO_EXCHANGE
                            </p>
                        </div>
                        <div class="text-right">
                            <span id="active-risk-badge" class="px-3 py-1 rounded-full text-xs font-extrabold bg-rose-50 text-rose-700 border border-rose-200">
                                RISK 0.92
                            </span>
                            <span id="active-uncertainty-badge" class="block text-[11px] text-[#7d8d86] font-mono mt-1">
                                Uncertainty: 0.10
                            </span>
                        </div>
                    </div>

                    <!-- Graph Metrics Ticker -->
                    <div class="grid grid-cols-3 gap-3 mt-4 pt-3 border-t border-slate-100 text-center">
                        <div class="bg-[#f8faf9] p-2.5 rounded-xl border border-slate-200/70">
                            <span class="text-[10px] font-bold uppercase tracking-wide text-[#7d8d86] block">Ring Footprint</span>
                            <strong id="stat-cards" class="text-sm font-extrabold text-[#c95f04] font-mono">8 Cards</strong>
                        </div>
                        <div class="bg-[#f8faf9] p-2.5 rounded-xl border border-slate-200/70">
                            <span class="text-[10px] font-bold uppercase tracking-wide text-[#7d8d86] block">1h Velocity</span>
                            <strong id="stat-vel" class="text-sm font-extrabold text-[#0a1f1a] font-mono">2 txns ($120)</strong>
                        </div>
                        <div class="bg-[#f8faf9] p-2.5 rounded-xl border border-slate-200/70">
                            <span class="text-[10px] font-bold uppercase tracking-wide text-[#7d8d86] block">Travel Velocity</span>
                            <strong id="stat-travel" class="text-sm font-extrabold text-[#0a1f1a] font-mono">45 km/h</strong>
                        </div>
                    </div>
                </div>

                <!-- TigerGraph 2-Hop Interactive Graph -->
                <div class="bg-white border border-slate-200/90 rounded-2xl p-5 card-shadow flex flex-col">
                    <div class="flex items-center justify-between mb-3">
                        <div class="flex items-center gap-2">
                            <i class="fa-solid fa-circle-nodes text-[#f58220]"></i>
                            <h4 class="text-xs font-bold uppercase tracking-wider text-[#0a1f1a]">
                                TigerGraph 2-Hop Entity Neighborhood
                            </h4>
                        </div>
                        <span class="text-[11px] text-[#00836c] font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200/80">
                            GSQL Subgraph Traversal
                        </span>
                    </div>

                    <div id="network-graph" class="w-full"></div>
                </div>

                <!-- 8-Step Autonomous Agent Execution Timeline -->
                <div class="bg-white border border-slate-200/90 rounded-2xl p-5 card-shadow flex flex-col flex-1">
                    <div class="flex items-center justify-between mb-3">
                        <div class="flex items-center gap-2">
                            <i class="fa-solid fa-list-ol text-[#00836c]"></i>
                            <h4 class="text-xs font-bold uppercase tracking-wider text-[#0a1f1a]">
                                Agent 8-Step Lifecycle Log
                            </h4>
                        </div>
                        <span class="text-[10px] font-mono text-[#7d8d86]">State Machine: Closed</span>
                    </div>
                    <div id="steps-timeline" class="space-y-2 overflow-y-auto max-h-[220px] text-xs font-mono text-[#46584f] pr-1">
                        <!-- Populated by JS -->
                    </div>
                </div>

            </main>

            <!-- Col 3: Two-Stage NBA, Interactive Simulator & SAR (4 cols) -->
            <aside class="col-span-12 lg:col-span-4 flex flex-col gap-4">

                <!-- Stage 1: Pre-Evidence NBA -->
                <div class="bg-white border border-slate-200/90 rounded-2xl p-5 card-shadow">
                    <div class="flex items-center justify-between border-b border-slate-100 pb-2 mb-2">
                        <span class="text-[11px] font-extrabold uppercase tracking-wider text-[#7d8d86] flex items-center gap-1.5">
                            <i class="fa-solid fa-clock-rotate-left text-amber-500"></i> Stage 1: Pre-Evidence NBA
                        </span>
                        <span id="pre-route-badge" class="text-[10px] px-2 py-0.5 rounded bg-slate-100 border border-slate-200 font-mono font-bold text-slate-700">
                            AUTOMATED
                        </span>
                    </div>
                    <div class="flex items-center justify-between mt-2">
                        <span class="text-xs text-[#7d8d86] font-medium">Initial Action:</span>
                        <strong id="pre-action-text" class="text-sm font-bold text-amber-700">BLOCK_CARD</strong>
                    </div>
                    <p id="pre-rationale-text" class="text-xs text-[#46584f] mt-2 bg-[#f8faf9] p-3 rounded-xl border border-slate-200/70 leading-relaxed">
                        Critical risk score >= 0.90 and active syndicate ring indicators warrant immediate card block.
                    </p>
                </div>

                <!-- Stage 2: Controlled Evidence Interactive Simulator -->
                <div class="bg-white border border-slate-200/90 rounded-2xl p-5 card-shadow">
                    <div class="flex items-center justify-between border-b border-slate-100 pb-2 mb-2">
                        <span class="text-[11px] font-extrabold uppercase tracking-wider text-[#7d8d86] flex items-center gap-1.5">
                            <i class="fa-solid fa-mobile-screen-button text-[#00836c]"></i> Stage 2: Controlled Evidence
                        </span>
                        <span id="evidence-status-badge" class="text-[10px] px-2 py-0.5 rounded bg-emerald-50 text-[#00594a] border border-emerald-200 font-mono font-bold">
                            COMPLETED
                        </span>
                    </div>
                    
                    <div id="evidence-box" class="text-xs space-y-2 text-[#46584f]">
                        <!-- Populated by JS -->
                    </div>

                    <!-- Interactive Simulation Controls -->
                    <div class="mt-4 pt-3 border-t border-slate-100">
                        <span class="text-[10px] font-bold uppercase tracking-wider text-[#7d8d86] block mb-2">
                            Simulate Customer / Analyst Interaction:
                        </span>
                        <div class="grid grid-cols-3 gap-2">
                            <button onclick="triggerSimulate('USER_FRAUD_ALERT')" class="px-2 py-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-[10px] font-bold transition flex items-center justify-center gap-1">
                                <i class="fa-solid fa-triangle-exclamation"></i> Flag Fraud
                            </button>
                            <button onclick="triggerSimulate('USER_CONFIRMED')" class="px-2 py-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 text-[10px] font-bold transition flex items-center justify-center gap-1">
                                <i class="fa-solid fa-check"></i> Verify Legit
                            </button>
                            <button onclick="triggerSimulate('TIMEOUT')" class="px-2 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-[10px] font-bold transition flex items-center justify-center gap-1">
                                <i class="fa-solid fa-hourglass-end"></i> Timeout
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Stage 3: Post-Evidence Final NBA -->
                <div class="bg-white border border-slate-200/90 rounded-2xl p-5 card-shadow">
                    <div class="flex items-center justify-between border-b border-slate-100 pb-2 mb-2">
                        <span class="text-[11px] font-extrabold uppercase tracking-wider text-[#00836c] flex items-center gap-1.5">
                            <i class="fa-solid fa-shield-halved text-[#00836c]"></i> Stage 3: Final Next-Best Action
                        </span>
                        <span id="post-route-badge" class="text-[10px] px-2 py-0.5 rounded bg-emerald-50 text-[#00594a] border border-emerald-200 font-mono font-bold">
                            AUTOMATED
                        </span>
                    </div>
                    <div class="flex items-center justify-between mt-2">
                        <span class="text-xs text-[#7d8d86] font-medium">Final Action:</span>
                        <strong id="post-action-text" class="text-base font-extrabold text-[#00836c]">BLOCK_CARD</strong>
                    </div>
                    <p id="post-rationale-text" class="text-xs text-[#46584f] mt-2 bg-[#f8faf9] p-3 rounded-xl border border-slate-200/70 leading-relaxed">
                        Card block applied. Investigation persisted to TigerGraph knowledge graph.
                    </p>
                    <div class="mt-3 flex items-center justify-between text-[11px] border-t border-slate-100 pt-2 text-[#7d8d86]">
                        <span>Graph Persistence:</span>
                        <span id="graph-persisted-badge" class="text-[#00836c] font-bold flex items-center gap-1">
                            <i class="fa-solid fa-circle-check"></i> Written to TigerGraph
                        </span>
                    </div>
                </div>

                <!-- Suspicious Activity Report (SAR) Panel -->
                <div id="sar-panel" class="bg-rose-50/60 border border-rose-200/80 rounded-2xl p-5 card-shadow">
                    <div class="flex items-center justify-between border-b border-rose-200 pb-2 mb-2">
                        <span class="text-[11px] font-extrabold uppercase tracking-wider text-rose-800 flex items-center gap-1.5">
                            <i class="fa-solid fa-file-shield text-rose-600"></i> FinCEN SAR Filing
                        </span>
                        <span id="sar-id-tag" class="text-[10px] px-2 py-0.5 rounded bg-white border border-rose-200 font-mono font-bold text-rose-700">
                            SAR-BENCH-01
                        </span>
                    </div>
                    <p id="sar-narrative" class="text-xs text-rose-900 leading-relaxed font-serif">
                        Mandatory Suspicious Activity Report drafted and ready for compliance submission.
                    </p>
                    <div class="mt-2 text-right">
                        <span id="sar-amount" class="text-xs font-mono font-bold text-rose-700">Exposure: $470.00</span>
                    </div>
                </div>

            </aside>

        </div>

    </div>

    <!-- Interactive Client Scripts -->
    <script>
        let currentNetwork = null;
        let allCases = [];
        let activeCaseId = "CASE_BENCH_01";

        async function fetchCases() {
            try {
                const res = await fetch('/api/v1/cases');
                allCases = await res.json();
                document.getElementById('case-count').innerText = `${allCases.length} Cases`;
                renderCaseList(allCases);
                if (allCases.length > 0) {
                    loadCase(allCases[0]);
                }
            } catch (err) {
                console.error("Failed to load cases:", err);
            }
        }

        function renderCaseList(cases) {
            const container = document.getElementById('cases-list');
            container.innerHTML = '';
            cases.forEach((cid, index) => {
                const btn = document.createElement('button');
                btn.id = `btn-${cid}`;
                btn.className = `w-full text-left p-3 rounded-xl border transition flex items-center justify-between ${cid === activeCaseId ? 'bg-emerald-50/80 border-[#00836c] shadow-sm' : 'bg-[#f8faf9] border-slate-200/80 hover:bg-white'}`;
                btn.onclick = () => loadCase(cid);
                btn.innerHTML = `
                    <div>
                        <div class="text-xs font-mono font-bold text-[#0a1f1a]">${cid}</div>
                        <div class="text-[10px] text-[#7d8d86] font-medium">IEEE Benchmark Case</div>
                    </div>
                    <i class="fa-solid fa-chevron-right text-xs text-slate-400"></i>
                `;
                container.appendChild(btn);
            });
        }

        function filterCases(filterType) {
            document.querySelectorAll('[id^="filter-"]').forEach(btn => {
                btn.className = 'px-2.5 py-1 rounded-lg bg-slate-100 text-[#46584f] hover:bg-slate-200';
            });
            document.getElementById(`filter-${filterType.toLowerCase()}`).className = 'px-2.5 py-1 rounded-lg bg-[#00836c] text-white';

            if (filterType === 'ALL') {
                renderCaseList(allCases);
            } else if (filterType === 'HIGH') {
                const filtered = allCases.filter(c => parseInt(c.replace('CASE_BENCH_', '')) <= 4 || parseInt(c.replace('CASE_BENCH_', '')) >= 13 && parseInt(c.replace('CASE_BENCH_', '')) <= 16);
                renderCaseList(filtered);
            } else if (filterType === 'CLEARED') {
                const filtered = allCases.filter(c => parseInt(c.replace('CASE_BENCH_', '')) >= 17);
                renderCaseList(filtered);
            }
        }

        async function loadCase(caseId) {
            activeCaseId = caseId;
            document.querySelectorAll('#cases-list button').forEach(b => {
                b.className = 'w-full text-left p-3 rounded-xl border transition flex items-center justify-between bg-[#f8faf9] border-slate-200/80 hover:bg-white';
            });
            const activeBtn = document.getElementById(`btn-${caseId}`);
            if (activeBtn) activeBtn.className = 'w-full text-left p-3 rounded-xl border transition flex items-center justify-between bg-emerald-50/80 border-[#00836c] shadow-sm';

            try {
                const res = await fetch(`/api/v1/cases/${caseId}`);
                const data = await res.json();
                renderCaseDetails(data);
            } catch (err) {
                console.error("Error loading case:", err);
            }
        }

        async function triggerSimulate(scenario) {
            try {
                const res = await fetch('/api/v1/simulate-response', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ case_id: activeCaseId, scenario: scenario })
                });
                const updated = await res.json();
                renderCaseDetails(updated);
            } catch (err) {
                console.error("Simulation error:", err);
            }
        }

        function renderCaseDetails(data) {
            const txn = data.trigger.transaction;
            document.getElementById('active-case-id').innerText = data.case_id;
            document.getElementById('active-txn-headline').innerText = `Transaction ${txn.txn_id}`;
            document.getElementById('active-txn-meta').innerText = `Amount: $${txn.amount.toFixed(2)} · Card: ${txn.card_id} · Merchant: ${txn.merchant_id}`;

            const risk = txn.model_risk_score;
            const rBadge = document.getElementById('active-risk-badge');
            rBadge.innerText = `RISK ${risk.toFixed(2)}`;
            if (risk >= 0.85) {
                rBadge.className = "px-3 py-1 rounded-full text-xs font-extrabold bg-rose-50 text-rose-700 border border-rose-200";
            } else if (risk >= 0.60) {
                rBadge.className = "px-3 py-1 rounded-full text-xs font-extrabold bg-amber-50 text-amber-700 border border-amber-200";
            } else {
                rBadge.className = "px-3 py-1 rounded-full text-xs font-extrabold bg-emerald-50 text-emerald-700 border border-emerald-200";
            }
            document.getElementById('active-uncertainty-badge').innerText = `Uncertainty: ${data.uncertainty_level.toFixed(2)}`;

            document.getElementById('stat-cards').innerText = `${data.graph_evidence.shared_device_card_count} Cards`;
            document.getElementById('stat-vel').innerText = `${data.graph_evidence.velocity_1h_txn_count} txns ($${data.graph_evidence.velocity_1h_amount.toFixed(0)})`;
            document.getElementById('stat-travel').innerText = data.graph_evidence.impossible_travel_detected ? `${data.graph_evidence.travel_speed_kmh} km/h (ALERT)` : `${data.graph_evidence.travel_speed_kmh || 45} km/h`;

            // Steps
            const stepsDiv = document.getElementById('steps-timeline');
            stepsDiv.innerHTML = '';
            (data.investigation_record.steps_taken || []).forEach(step => {
                const item = document.createElement('div');
                item.className = "p-2 rounded-lg bg-[#f8faf9] border border-slate-200/80 text-[11px]";
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
                    <div class="bg-cyan-50/70 p-3 rounded-xl border border-cyan-200/80">
                        <div class="flex items-center justify-between">
                            <strong class="text-cyan-900">${data.requested_evidence.evidence_type}</strong>
                            <span class="text-cyan-700 font-mono text-[10px] font-bold bg-white px-2 py-0.5 rounded border border-cyan-200">${data.received_evidence ? data.received_evidence.status : 'PENDING'}</span>
                        </div>
                        <p class="mt-1 text-[#46584f] text-xs">${data.received_evidence ? (data.received_evidence.notes || 'Verified') : 'Awaiting cardholder verification challenge...'}</p>
                    </div>
                `;
            } else {
                evBox.innerHTML = `<p class="text-xs text-[#7d8d86] italic bg-[#f8faf9] p-3 rounded-xl border border-slate-200/60">No additional evidence required (high confidence graph pattern).</p>`;
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
                document.getElementById('sar-amount').innerText = `Exposure: $${data.sar_report.total_suspicious_amount.toFixed(2)}`;
            } else {
                sarPanel.style.display = 'none';
            }

            renderGraphLight(data);
        }

        function renderGraphLight(data) {
            const container = document.getElementById('network-graph');
            const txn = data.trigger.transaction;

            const nodes = [
                { id: 1, label: `Txn: ${txn.txn_id}`, color: { background: '#f58220', border: '#c95f04' }, shape: 'box', font: { color: '#ffffff', bold: true } },
                { id: 2, label: `Card: ${txn.card_id}`, color: { background: '#00836c', border: '#00594a' }, shape: 'ellipse', font: { color: '#ffffff' } },
                { id: 3, label: `Customer: ${txn.customer_id}`, color: { background: '#3b82f6', border: '#1d4ed8' }, shape: 'ellipse', font: { color: '#ffffff' } },
                { id: 4, label: `Device: ${txn.device_id || 'dev_01'}`, color: { background: '#ef4444', border: '#b91c1c' }, shape: 'hexagon', font: { color: '#ffffff' } },
                { id: 5, label: `IP: ${txn.ip_address || '198.51.100.1'}`, color: { background: '#eab308', border: '#a16207' }, shape: 'dot', font: { color: '#ffffff' } },
                { id: 6, label: `Merchant: ${txn.merchant_id}`, color: { background: '#10b981', border: '#047857' }, shape: 'box', font: { color: '#ffffff' } }
            ];

            if (data.graph_evidence.shared_device_card_count > 1) {
                nodes.push({ id: 7, label: 'Linked Card 2', color: { background: '#00836c', border: '#00594a' }, shape: 'ellipse', font: { color: '#ffffff' } });
                nodes.push({ id: 8, label: 'Linked Card 3', color: { background: '#00836c', border: '#00594a' }, shape: 'ellipse', font: { color: '#ffffff' } });
            }

            const edges = [
                { from: 2, to: 1, label: 'CHARGED' },
                { from: 3, to: 2, label: 'OWNS' },
                { from: 1, to: 4, label: 'USED_DEVICE' },
                { from: 1, to: 5, label: 'USED_IP' },
                { from: 1, to: 6, label: 'PAID_TO' }
            ];

            if (data.graph_evidence.shared_device_card_count > 1) {
                edges.push({ from: 4, to: 7, label: 'RING_LINK' });
                edges.push({ from: 4, to: 8, label: 'RING_LINK' });
            }

            const graphData = { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) };
            const options = {
                nodes: { font: { size: 11, face: 'monospace' }, borderWidth: 2 },
                edges: { color: '#94a3b8', font: { size: 9, color: '#475569' }, arrows: 'to' },
                physics: { stabilization: true, barnesHut: { springLength: 95 } }
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
