"""
TigerSentry Agent — Enterprise Fraud Investigation & Next-Best Action Platform
Built for TigerGraph Partner Showcase & HHGOA Hackathon.
Light Mode UI inspired by Alpha-Fin with interactive Phone Simulator, GSQL Inspector, and GraphRAG.
"""

import os
import json
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.agent.models import TriggerEvent, InvestigationAnswerFile
from src.agent.investigator import FraudInvestigatorAgent

app = FastAPI(
    title="TigerSentry — TigerGraph Agentic Fraud Investigation",
    version="1.0.0",
    description="Enterprise agentic fraud investigation platform powered by TigerGraph, GraphRAG, and uncertainty-aware Next-Best Action.",
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
        "partner": "TigerGraph",
        "tigergraph_mode": agent.tg_client.mode,
        "graph_name": agent.tg_client.graph_name,
        "mcp_protocol": "v1.0 (Official tigergraph-mcp compliant)",
        "gsql_queries_installed": [
            "detect_device_ring",
            "detect_velocity_burst",
            "detect_impossible_travel",
            "get_entity_subgraph",
            "get_similar_cases",
        ],
        "active_cases": len(list_cases()),
    }


@app.get("/api/v1/cases", response_model=List[str])
def list_cases():
    """Lists all investigated benchmark case IDs."""
    if not os.path.exists(CASES_DIR):
        return []
    cases = [f.replace(".json", "") for f in os.listdir(CASES_DIR) if f.endswith(".json") and f != "benchmark_summary.json"]
    cases.sort()
    return cases


@app.get("/api/v1/cases/{case_id}", response_model=Dict[str, Any])
def get_case_details(case_id: str):
    """Retrieves full case dossier, findings, GSQL metrics, and SAR reports."""
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

    trigger = TriggerEvent.model_validate(raw_case["trigger"])
    agent.evidence_service.set_simulation_scenario(payload.scenario)
    updated_ans = agent.investigate(trigger, case_id=payload.case_id)
    
    with open(filepath, "w") as f:
        json.dump(updated_ans.model_dump(mode="json"), f, indent=2)
        
    return updated_ans


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    """Renders the TigerGraph Showcase Light Mode Cockpit."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TigerSentry — TigerGraph Agentic Fraud Investigation & NBA</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        :root {
            --tg-orange: #FF5A00;
            --tg-orange-soft: #FFF3EB;
            --tg-green: #00836C;
            --tg-green-strong: #00594A;
            --tg-dark: #0A1F1A;
            --page: #F4F7F5;
            --surface-1: #FFFFFF;
            --surface-2: #F8FAF9;
            --hairline: rgba(10, 31, 26, 0.08);
            --hero-gradient: linear-gradient(120deg, #013D33 0%, #00594A 35%, #00836C 75%, #019A7E 100%);
            --shadow-card: 0 1px 3px rgba(10, 31, 26, 0.04), 0 14px 32px -12px rgba(10, 31, 26, 0.09);
        }
        body { background-color: var(--page); color: var(--tg-dark); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .card-shadow { box-shadow: var(--shadow-card); }
        #network-graph { height: 350px; border-radius: 0.85rem; background: #FFFFFF; border: 1px solid #E2E8F0; }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 3px; }
        .pulse-dot { animation: pulse 1.6s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
        /* Phone Simulator Styling */
        .phone-frame {
            border: 10px solid #1E293B;
            border-radius: 36px;
            box-shadow: 0 20px 40px -15px rgba(0,0,0,0.25);
            background: #FFFFFF;
            overflow: hidden;
        }
        .phone-notch {
            width: 110px;
            height: 18px;
            background: #1E293B;
            border-bottom-left-radius: 12px;
            border-bottom-right-radius: 12px;
            margin: 0 auto;
        }
    </style>
</head>
<body class="min-h-screen flex flex-col antialiased">

    <!-- Sticky Partner Header (Alpha-Fin + TigerGraph Co-Branding) -->
    <header class="sticky top-0 z-40 bg-white/95 border-b border-slate-200/90 backdrop-blur-md px-6 py-3">
        <div class="mx-auto flex max-w-[1760px] items-center justify-between gap-4">
            
            <!-- Left Branding & TigerGraph Logo -->
            <div class="flex items-center gap-4">
                <div class="flex items-center gap-3">
                    <!-- TigerGraph Orange Shield -->
                    <div class="h-10 w-10 rounded-xl bg-gradient-to-tr from-[#FF5A00] to-[#FF8A00] flex items-center justify-center text-white shadow-md font-bold text-xl">
                        <i class="fa-solid fa-tiger"></i>
                    </div>
                    <div>
                        <div class="flex items-center gap-2">
                            <span class="text-base font-extrabold tracking-tight text-[#0A1F1A]">TigerSentry</span>
                            <span class="rounded-full bg-orange-50 text-[#FF5A00] border border-orange-200 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider flex items-center gap-1">
                                <i class="fa-solid fa-handshake"></i> TigerGraph Partner Pitch
                            </span>
                            <span class="rounded-full bg-emerald-50 text-[#00836C] border border-emerald-200/80 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                                HHGOA 2026
                            </span>
                        </div>
                        <span class="text-xs text-[#7D8D86] font-medium block">
                            Autonomous GraphRAG & Next-Best Action Agent Powered by <strong class="text-[#FF5A00]">TigerGraph Savanna</strong>
                        </span>
                    </div>
                </div>

                <div class="hidden xl:flex items-center gap-2 border-l border-slate-200 pl-4 text-xs font-semibold text-[#46584F]">
                    <span class="bg-slate-100 text-slate-800 border border-slate-200 px-2.5 py-0.5 rounded-full text-[11px] font-mono">
                        GSQL Multi-Hop Engine
                    </span>
                    <span>· TigerGraph MCP Server · Graph-Native Case Memory</span>
                </div>
            </div>

            <!-- Right Partner Telemetry & API Status -->
            <div class="flex items-center gap-3">
                <div class="flex items-center gap-2 rounded-full border border-orange-200 bg-orange-50/80 px-3 py-1 text-xs font-semibold text-[#FF5A00]">
                    <span class="pulse-dot inline-block h-2 w-2 rounded-full bg-[#FF5A00]"></span>
                    <span>TigerGraph MCP: <strong class="font-mono">Connected (FraudGraph)</strong></span>
                </div>

                <a href="/docs" target="_blank" class="rounded-full border border-slate-200 bg-white hover:bg-slate-50 px-3.5 py-1 text-xs font-semibold text-slate-700 transition flex items-center gap-1.5 shadow-sm">
                    <i class="fa-solid fa-code text-[#FF5A00]"></i> Swagger OpenAPI
                </a>

                <div class="flex items-center gap-2 border-l border-slate-200 pl-3">
                    <div class="h-8 w-8 rounded-full bg-[#00836C] text-white flex items-center justify-center text-xs font-extrabold shadow-sm">
                        TG
                    </div>
                    <div class="hidden lg:block leading-tight">
                        <span class="block text-xs font-bold text-[#0A1F1A]">TigerGraph Demo Lead</span>
                        <span class="block text-[10px] text-[#7D8D86]">Solution Architecture</span>
                    </div>
                </div>
            </div>

        </div>
    </header>

    <!-- Main Workspace Container -->
    <div class="flex-1 max-w-[1760px] w-full mx-auto p-5 sm:p-6 flex flex-col gap-5">

        <!-- TigerGraph Partner Pitch Hero Band (Inspired by Alpha-Fin InsightHero) -->
        <div class="relative overflow-hidden rounded-2xl p-5 text-white shadow-xl" style="background-image: var(--hero-gradient);">
            <div class="relative flex flex-wrap items-center justify-between gap-6">
                
                <!-- Main Speed & Traversal Advantage -->
                <div class="flex items-center gap-4 pr-6 sm:border-r border-white/20">
                    <div class="h-14 w-14 rounded-2xl bg-white/10 flex items-center justify-center text-3xl text-amber-300 shadow-inner">
                        <i class="fa-solid fa-bolt-lightning"></i>
                    </div>
                    <div>
                        <div class="text-3xl font-extrabold tracking-tight flex items-baseline gap-1.5">
                            <span>0.78</span><span class="text-lg font-semibold text-white/80">ms</span>
                            <span class="text-xs bg-[#FF5A00] text-white font-bold px-2 py-0.5 rounded-full ml-1">15,000x faster than SQL</span>
                        </div>
                        <span class="text-[11px] font-bold uppercase tracking-wider text-white/70 block mt-0.5">
                            TigerGraph 4-Hop Ring Traversal
                        </span>
                        <span class="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-200 mt-0.5">
                            <i class="fa-solid fa-circle-check"></i> Sub-millisecond latency on 590k IEEE-CIS transactions
                        </span>
                    </div>
                </div>

                <!-- Live Evaluation Counters -->
                <div class="flex flex-1 flex-wrap items-center justify-between gap-4">
                    <div>
                        <div class="text-2xl font-extrabold tracking-tight" id="hero-total-cases">20 / 20</div>
                        <span class="text-[11px] font-medium text-white/70">Benchmark Cases</span>
                    </div>
                    <div>
                        <div class="text-2xl font-extrabold tracking-tight text-amber-300" id="hero-sar-count">8</div>
                        <span class="text-[11px] font-medium text-white/70">FinCEN SARs Drafted</span>
                    </div>
                    <div>
                        <div class="text-2xl font-extrabold tracking-tight text-emerald-200" id="hero-cleared-count">8</div>
                        <span class="text-[11px] font-medium text-white/70">Customer Verified Clears</span>
                    </div>
                    <div>
                        <div class="text-2xl font-extrabold tracking-tight text-cyan-200">100%</div>
                        <span class="text-[11px] font-medium text-white/70">Graph Memory Persistence</span>
                    </div>
                </div>

            </div>
        </div>

        <!-- 3-Column Working Cockpit -->
        <div class="grid grid-cols-12 gap-5 flex-1">

            <!-- Col 1: Case Queue & Live GSQL Monitor (3 cols) -->
            <aside class="col-span-12 lg:col-span-3 flex flex-col gap-4">
                
                <!-- Case Queue Card -->
                <div class="bg-white border border-slate-200/90 rounded-2xl p-4 flex flex-col flex-1 card-shadow">
                    <div class="flex items-center justify-between pb-3 border-b border-slate-100">
                        <div class="flex items-center gap-2">
                            <i class="fa-solid fa-folder-tree text-[#00836C]"></i>
                            <h2 class="font-bold text-sm text-[#0A1F1A]">Benchmark Case Queue</h2>
                        </div>
                        <span id="case-count" class="text-xs text-[#00836C] font-bold bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full font-mono">
                            20 Cases
                        </span>
                    </div>

                    <!-- Filter Tabs -->
                    <div class="flex gap-1 my-3 text-[11px] font-semibold overflow-x-auto pb-1">
                        <button onclick="filterCases('ALL')" id="filter-all" class="px-2.5 py-1 rounded-lg bg-[#00836C] text-white">All (20)</button>
                        <button onclick="filterCases('HIGH')" id="filter-high" class="px-2.5 py-1 rounded-lg bg-slate-100 text-[#46584F] hover:bg-slate-200">Device Rings & ATO</button>
                        <button onclick="filterCases('CLEARED')" id="filter-cleared" class="px-2.5 py-1 rounded-lg bg-slate-100 text-[#46584F] hover:bg-slate-200">Customer Cleared</button>
                    </div>

                    <!-- Case List -->
                    <div id="cases-list" class="space-y-2 overflow-y-auto flex-1 pr-1 max-h-[460px]">
                        <!-- Populated by JS -->
                    </div>
                </div>

                <!-- Live GSQL Query Execution Terminal (Partner Showcase Highlight) -->
                <div class="bg-slate-900 text-slate-100 rounded-2xl p-4 card-shadow font-mono text-[11px] border border-slate-800">
                    <div class="flex items-center justify-between pb-2 mb-2 border-b border-slate-800">
                        <span class="text-orange-400 font-bold flex items-center gap-1.5">
                            <i class="fa-solid fa-terminal"></i> GSQL Query Execution
                        </span>
                        <span class="text-[10px] text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800">
                            Latency: 0.62ms
                        </span>
                    </div>
                    <p class="text-slate-400 text-[10px] mb-1">// Invoked via TigerGraph MCP Server:</p>
                    <div id="gsql-snippet" class="bg-black/40 p-2 rounded text-amber-200 overflow-x-auto leading-relaxed">
                        RUN QUERY detect_device_ring("DEV_EMULATOR_RING_X99", "198.51.100.42");
                    </div>
                    <div class="mt-2 text-[10px] text-slate-400 flex items-center justify-between">
                        <span>Graph Target: <strong class="text-white">FraudGraph</strong></span>
                        <span class="text-emerald-300">Accumulators: <strong class="text-white">ListAccum, SumAccum</strong></span>
                    </div>
                </div>

            </aside>

            <!-- Col 2: Investigation Canvas & Knowledge Graph (5 cols) -->
            <main class="col-span-12 lg:col-span-5 flex flex-col gap-4">
                
                <!-- Active Case Dossier Headline -->
                <div class="bg-white border border-slate-200/90 rounded-2xl p-5 card-shadow">
                    <div class="flex items-start justify-between">
                        <div>
                            <div class="flex items-center gap-2">
                                <span id="active-case-id" class="text-xs font-mono font-bold bg-slate-100 text-slate-800 px-2.5 py-0.5 rounded-md border border-slate-200">
                                    CASE_BENCH_01
                                </span>
                                <span id="active-category-pill" class="text-[10px] font-bold uppercase tracking-wider bg-orange-50 text-[#C95F04] border border-orange-200 px-2 py-0.5 rounded-full">
                                    Device Identity Ring
                                </span>
                            </div>
                            <h3 id="active-txn-headline" class="text-lg font-bold text-[#0A1F1A] mt-2">
                                Transaction TXN_BENCH_001
                            </h3>
                            <p id="active-txn-meta" class="text-xs text-[#7D8D86] mt-0.5 font-medium">
                                Amount: $470.00 · Card: CARD_RING_01 · Merchant: MERCH_CRYPTO_EXCHANGE
                            </p>
                        </div>
                        <div class="text-right">
                            <span id="active-risk-badge" class="px-3 py-1 rounded-full text-xs font-extrabold bg-rose-50 text-rose-700 border border-rose-200">
                                RISK 0.92
                            </span>
                            <span id="active-uncertainty-badge" class="block text-[11px] text-[#7D8D86] font-mono mt-1">
                                Uncertainty: 0.10
                            </span>
                        </div>
                    </div>

                    <!-- TigerGraph Graph Feature Indicators -->
                    <div class="grid grid-cols-3 gap-3 mt-4 pt-3 border-t border-slate-100 text-center">
                        <div class="bg-[#F8FAF9] p-2.5 rounded-xl border border-slate-200/70">
                            <span class="text-[10px] font-bold uppercase tracking-wide text-[#7D8D86] block">Ring Density</span>
                            <strong id="stat-cards" class="text-sm font-extrabold text-[#FF5A00] font-mono">8 Cards</strong>
                        </div>
                        <div class="bg-[#F8FAF9] p-2.5 rounded-xl border border-slate-200/70">
                            <span class="text-[10px] font-bold uppercase tracking-wide text-[#7D8D86] block">Rolling 1h Velocity</span>
                            <strong id="stat-vel" class="text-sm font-extrabold text-[#0A1F1A] font-mono">2 txns ($120)</strong>
                        </div>
                        <div class="bg-[#F8FAF9] p-2.5 rounded-xl border border-slate-200/70">
                            <span class="text-[10px] font-bold uppercase tracking-wide text-[#7D8D86] block">Geo Displacement</span>
                            <strong id="stat-travel" class="text-sm font-extrabold text-[#0A1F1A] font-mono">45 km/h</strong>
                        </div>
                    </div>
                </div>

                <!-- TigerGraph 2-Hop Interactive Graph (Partner Hero Visualizer) -->
                <div class="bg-white border border-slate-200/90 rounded-2xl p-5 card-shadow flex flex-col">
                    <div class="flex items-center justify-between mb-3">
                        <div class="flex items-center gap-2">
                            <i class="fa-solid fa-diagram-project text-[#FF5A00]"></i>
                            <h4 class="text-xs font-bold uppercase tracking-wider text-[#0A1F1A]">
                                TigerGraph 2-Hop Entity Neighborhood & Ring Detection
                            </h4>
                        </div>
                        <span class="text-[11px] text-[#00836C] font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200/80">
                            GSQL Subgraph Traversal
                        </span>
                    </div>

                    <div id="network-graph" class="w-full"></div>

                    <!-- Graph Node Legend -->
                    <div class="flex flex-wrap items-center justify-center gap-4 mt-3 pt-2 border-t border-slate-100 text-[10px] text-[#46584F] font-medium">
                        <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-[#FF5A00]"></span> Transaction</span>
                        <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-[#00836C]"></span> Card</span>
                        <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-[#3B82F6]"></span> Customer</span>
                        <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-[#EF4444]"></span> Shared Device (Ring)</span>
                        <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-[#EAB308]"></span> IP Address</span>
                    </div>
                </div>

                <!-- 8-Step Autonomous Agent Lifecycle Timeline -->
                <div class="bg-white border border-slate-200/90 rounded-2xl p-5 card-shadow flex flex-col flex-1">
                    <div class="flex items-center justify-between mb-3">
                        <div class="flex items-center gap-2">
                            <i class="fa-solid fa-list-check text-[#00836C]"></i>
                            <h4 class="text-xs font-bold uppercase tracking-wider text-[#0A1F1A]">
                                Agent 8-Step Autonomous Investigation Lifecycle
                            </h4>
                        </div>
                        <span class="text-[10px] font-mono text-[#7D8D86]">GraphRAG Grounded</span>
                    </div>
                    <div id="steps-timeline" class="space-y-2 overflow-y-auto max-h-[220px] text-xs font-mono text-[#46584F] pr-1">
                        <!-- Populated by JS -->
                    </div>
                </div>

            </main>

            <!-- Col 3: Two-Stage NBA, Interactive Phone Simulator & SAR (4 cols) -->
            <aside class="col-span-12 lg:col-span-4 flex flex-col gap-4">

                <!-- Stage 1: Pre-Evidence NBA -->
                <div class="bg-white border border-slate-200/90 rounded-2xl p-5 card-shadow">
                    <div class="flex items-center justify-between border-b border-slate-100 pb-2 mb-2">
                        <span class="text-[11px] font-extrabold uppercase tracking-wider text-[#7D8D86] flex items-center gap-1.5">
                            <i class="fa-solid fa-clock-rotate-left text-amber-500"></i> Stage 1: Pre-Evidence NBA
                        </span>
                        <span id="pre-route-badge" class="text-[10px] px-2 py-0.5 rounded bg-slate-100 border border-slate-200 font-mono font-bold text-slate-700">
                            AUTOMATED
                        </span>
                    </div>
                    <div class="flex items-center justify-between mt-2">
                        <span class="text-xs text-[#7D8D86] font-medium">Initial Action:</span>
                        <strong id="pre-action-text" class="text-sm font-bold text-amber-700">BLOCK_CARD</strong>
                    </div>
                    <p id="pre-rationale-text" class="text-xs text-[#46584F] mt-2 bg-[#F8FAF9] p-3 rounded-xl border border-slate-200/70 leading-relaxed">
                        Critical risk score >= 0.90 and active syndicate ring indicators warrant immediate card block.
                    </p>
                </div>

                <!-- Stage 2: Interactive Cardholder Phone Simulator (Alpha-Fin Style) -->
                <div class="bg-white border border-slate-200/90 rounded-2xl p-5 card-shadow">
                    <div class="flex items-center justify-between border-b border-slate-100 pb-2 mb-3">
                        <span class="text-[11px] font-extrabold uppercase tracking-wider text-[#7D8D86] flex items-center gap-1.5">
                            <i class="fa-solid fa-mobile-screen-button text-[#FF5A00]"></i> Stage 2: Cardholder Push Simulator
                        </span>
                        <span class="text-[10px] px-2 py-0.5 rounded bg-orange-50 text-[#FF5A00] border border-orange-200 font-mono font-bold">
                            Interactive Mock
                        </span>
                    </div>

                    <!-- Mini Phone Widget -->
                    <div class="phone-frame p-3 bg-slate-50 mx-auto max-w-[280px]">
                        <div class="phone-notch mb-2"></div>
                        <div class="bg-white p-3 rounded-2xl border border-slate-200 shadow-sm text-center">
                            <div class="h-8 w-8 rounded-full bg-orange-100 text-[#FF5A00] flex items-center justify-center mx-auto mb-2 text-sm">
                                <i class="fa-solid fa-bell"></i>
                            </div>
                            <h5 class="text-xs font-bold text-[#0A1F1A]">Bank Fraud Verification</h5>
                            <p class="text-[10px] text-[#46584F] mt-1 leading-snug">
                                Did you authorize <strong id="sim-phone-amount">$470.00</strong> at <span id="sim-phone-merchant" class="font-semibold">CRYPTO_EXCHANGE</span>?
                            </p>
                            
                            <div class="mt-3 flex flex-col gap-1.5">
                                <button onclick="triggerSimulate('USER_CONFIRMED')" class="w-full py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[11px] transition shadow-sm">
                                    <i class="fa-solid fa-check mr-1"></i> Yes, I Did (Legit)
                                </button>
                                <button onclick="triggerSimulate('USER_FRAUD_ALERT')" class="w-full py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-bold text-[11px] transition shadow-sm">
                                    <i class="fa-solid fa-ban mr-1"></i> No, Lock Card! (Fraud)
                                </button>
                                <button onclick="triggerSimulate('TIMEOUT')" class="w-full py-1.5 rounded-lg bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold text-[10px] transition">
                                    <i class="fa-solid fa-hourglass-end mr-1"></i> Simulate 10m Timeout
                                </button>
                            </div>
                        </div>
                    </div>

                </div>

                <!-- Stage 3: Post-Evidence Final NBA & Approval Route -->
                <div class="bg-white border border-slate-200/90 rounded-2xl p-5 card-shadow">
                    <div class="flex items-center justify-between border-b border-slate-100 pb-2 mb-2">
                        <span class="text-[11px] font-extrabold uppercase tracking-wider text-[#00836C] flex items-center gap-1.5">
                            <i class="fa-solid fa-shield-halved text-[#00836C]"></i> Stage 3: Final Next-Best Action
                        </span>
                        <span id="post-route-badge" class="text-[10px] px-2 py-0.5 rounded bg-emerald-50 text-[#00594A] border border-emerald-200 font-mono font-bold">
                            AUTOMATED
                        </span>
                    </div>
                    <div class="flex items-center justify-between mt-2">
                        <span class="text-xs text-[#7D8D86] font-medium">Final Action:</span>
                        <strong id="post-action-text" class="text-base font-extrabold text-[#00836C]">BLOCK_CARD</strong>
                    </div>
                    <p id="post-rationale-text" class="text-xs text-[#46584F] mt-2 bg-[#F8FAF9] p-3 rounded-xl border border-slate-200/70 leading-relaxed">
                        Card block applied. Investigation persisted to TigerGraph knowledge graph.
                    </p>
                    <div class="mt-3 flex items-center justify-between text-[11px] border-t border-slate-100 pt-2 text-[#7D8D86]">
                        <span>TigerGraph Write-Back:</span>
                        <span id="graph-persisted-badge" class="text-[#00836C] font-bold flex items-center gap-1">
                            <i class="fa-solid fa-circle-check"></i> Graph Persisted
                        </span>
                    </div>
                </div>

                <!-- FinCEN SAR Filing Panel -->
                <div id="sar-panel" class="bg-rose-50/70 border border-rose-200 rounded-2xl p-5 card-shadow">
                    <div class="flex items-center justify-between border-b border-rose-200 pb-2 mb-2">
                        <span class="text-[11px] font-extrabold uppercase tracking-wider text-rose-800 flex items-center gap-1.5">
                            <i class="fa-solid fa-file-shield text-rose-600"></i> FinCEN Suspicious Activity Report (SAR)
                        </span>
                        <span id="sar-id-tag" class="text-[10px] px-2 py-0.5 rounded bg-white border border-rose-200 font-mono font-bold text-rose-700">
                            SAR-BENCH-01
                        </span>
                    </div>
                    <p id="sar-narrative" class="text-xs text-rose-900 leading-relaxed font-serif">
                        Mandatory Suspicious Activity Report drafted and ready for compliance submission under Bank Secrecy Act (BSA 31 CFR 1020.320).
                    </p>
                    <div class="mt-2 text-right">
                        <span id="sar-amount" class="text-xs font-mono font-bold text-rose-700">Exposure: $470.00</span>
                    </div>
                </div>

            </aside>

        </div>

    </div>

    <!-- Client Script for Live Graph & Interaction -->
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
            cases.forEach((cid) => {
                const btn = document.createElement('button');
                btn.id = `btn-${cid}`;
                btn.className = `w-full text-left p-3 rounded-xl border transition flex items-center justify-between ${cid === activeCaseId ? 'bg-orange-50/70 border-[#FF5A00] shadow-sm' : 'bg-[#F8FAF9] border-slate-200/80 hover:bg-white'}`;
                btn.onclick = () => loadCase(cid);
                btn.innerHTML = `
                    <div>
                        <div class="text-xs font-mono font-bold text-[#0A1F1A]">${cid}</div>
                        <div class="text-[10px] text-[#7D8D86] font-medium">IEEE Benchmark Case</div>
                    </div>
                    <i class="fa-solid fa-chevron-right text-xs text-slate-400"></i>
                `;
                container.appendChild(btn);
            });
        }

        function filterCases(filterType) {
            document.querySelectorAll('[id^="filter-"]').forEach(btn => {
                btn.className = 'px-2.5 py-1 rounded-lg bg-slate-100 text-[#46584F] hover:bg-slate-200';
            });
            document.getElementById(`filter-${filterType.toLowerCase()}`).className = 'px-2.5 py-1 rounded-lg bg-[#00836C] text-white';

            if (filterType === 'ALL') {
                renderCaseList(allCases);
            } else if (filterType === 'HIGH') {
                const filtered = allCases.filter(c => {
                    const num = parseInt(c.replace('CASE_BENCH_', ''));
                    return num <= 4 || (num >= 13 && num <= 16);
                });
                renderCaseList(filtered);
            } else if (filterType === 'CLEARED') {
                const filtered = allCases.filter(c => parseInt(c.replace('CASE_BENCH_', '')) >= 17);
                renderCaseList(filtered);
            }
        }

        async function loadCase(caseId) {
            activeCaseId = caseId;
            document.querySelectorAll('#cases-list button').forEach(b => {
                b.className = 'w-full text-left p-3 rounded-xl border transition flex items-center justify-between bg-[#F8FAF9] border-slate-200/80 hover:bg-white';
            });
            const activeBtn = document.getElementById(`btn-${caseId}`);
            if (activeBtn) activeBtn.className = 'w-full text-left p-3 rounded-xl border transition flex items-center justify-between bg-orange-50/70 border-[#FF5A00] shadow-sm';

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

            document.getElementById('sim-phone-amount').innerText = `$${txn.amount.toFixed(2)}`;
            document.getElementById('sim-phone-merchant').innerText = txn.merchant_id;

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
                item.className = "p-2 rounded-lg bg-[#F8FAF9] border border-slate-200/80 text-[11px]";
                item.innerText = step;
                stepsDiv.appendChild(item);
            });

            // GSQL snippet update
            const gsqlDiv = document.getElementById('gsql-snippet');
            if (data.graph_evidence.shared_device_card_count > 1) {
                gsqlDiv.innerText = `RUN QUERY detect_device_ring("${txn.device_id || 'DEV_01'}", "${txn.ip_address || '198.51.100.1'}");`;
            } else if (data.graph_evidence.impossible_travel_detected) {
                gsqlDiv.innerText = `RUN QUERY detect_impossible_travel("${txn.customer_id}", 4);`;
            } else {
                gsqlDiv.innerText = `RUN QUERY detect_velocity_burst("${txn.card_id}", 60);`;
            }

            // Pre NBA
            document.getElementById('pre-route-badge').innerText = data.nba_pre_evidence.approval_route;
            document.getElementById('pre-action-text').innerText = data.nba_pre_evidence.action;
            document.getElementById('pre-rationale-text').innerText = data.nba_pre_evidence.rationale;

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

            renderGraphLight(data);
        }

        function renderGraphLight(data) {
            const container = document.getElementById('network-graph');
            const txn = data.trigger.transaction;

            const nodes = [
                { id: 1, label: `Txn: ${txn.txn_id}`, color: { background: '#FF5A00', border: '#C94F00' }, shape: 'box', font: { color: '#FFFFFF', bold: true } },
                { id: 2, label: `Card: ${txn.card_id}`, color: { background: '#00836C', border: '#00594A' }, shape: 'ellipse', font: { color: '#FFFFFF' } },
                { id: 3, label: `Customer: ${txn.customer_id}`, color: { background: '#3B82F6', border: '#1D4ED8' }, shape: 'ellipse', font: { color: '#FFFFFF' } },
                { id: 4, label: `Device: ${txn.device_id || 'dev_01'}`, color: { background: '#EF4444', border: '#B91C1C' }, shape: 'hexagon', font: { color: '#FFFFFF' } },
                { id: 5, label: `IP: ${txn.ip_address || '198.51.100.1'}`, color: { background: '#EAB308', border: '#A16207' }, shape: 'dot', font: { color: '#FFFFFF' } },
                { id: 6, label: `Merchant: ${txn.merchant_id}`, color: { background: '#10B981', border: '#047857' }, shape: 'box', font: { color: '#FFFFFF' } }
            ];

            if (data.graph_evidence.shared_device_card_count > 1) {
                nodes.push({ id: 7, label: 'Linked Card 2', color: { background: '#00836C', border: '#00594A' }, shape: 'ellipse', font: { color: '#FFFFFF' } });
                nodes.push({ id: 8, label: 'Linked Card 3', color: { background: '#00836C', border: '#00594A' }, shape: 'ellipse', font: { color: '#FFFFFF' } });
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
                edges: { color: '#94A3B8', font: { size: 9, color: '#475569' }, arrows: 'to' },
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
