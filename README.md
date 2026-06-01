# 🧬 ALAS 2.0 — Adaptive Living AI System

> A persistent digital lifeform that learns, adapts, and evolves through continuous experience.

[![Phase](https://img.shields.io/badge/Phase-15%20Spatial%20Computing-blueviolet)]()
[![Version](https://img.shields.io/badge/Version-2.0.0-cyan)]()
[![License](https://img.shields.io/badge/License-MIT-green)]()

---

## ✨ Features (ALAS 2.0)

### 🚀 ALAS 2.0 Paradigm Shift ✅
- 🧠 **Local Superintelligence** — 100% local Tree-of-Thoughts (ToT) reasoning engine. No cloud API keys required.
- 👁️ **Zero-Latency Perception** — Peer-to-Peer WebRTC pipeline streaming 15fps webcam & 16kHz audio directly into MediaPipe Face Mesh & VAD.
- 🕸️ **Cross-Device Mesh (Rust)** — High-performance Rust daemon for P2P Tailscale memory synchronization across all your devices.

### Core (Phase 1-4) ✅
- 🧠 **Persistent Memory** — ChromaDB episodic memory with semantic RAG retrieval
- 🤖 **Agentic Autonomy** — ReAct tool execution (time, weather, code execution, web search)
- 🎙️ **Voice I/O** — Speech-to-text (Whisper) + Text-to-speech (Edge-TTS)
- 🕸️ **Knowledge Graph** — NetworkX-powered entity/relationship memory (L2)
- 🧬 **Behavioral Evolution** — Genetic algorithm mutating personality parameters
- 🐍 **Code Sandbox & Git** — Execute Python/Bash safely and manage repositories

### Advanced Cognition & Safety (Phase 5-6) ✅
- 🔮 **Vision Engine** — Multimodal image understanding & MediaPipe webcam integration
- 🏰 **Fortress System** — Immutable action audit trails & AES-256 memory encryption
- 🛡️ **Dynamic Permissions** — Tiered execution permissions (AUTO, NOTIFY, ASK)

### Embodiment & Swarm (Phase 7-9) ✅
- 🚁 **Embodied Intelligence** — PyBullet physics simulation and MAVLink drone control
- 🐝 **Swarm Intelligence** — Multi-agent orchestrator with a Pub/Sub Blackboard
- 👥 **Sub-Agents** — Specialized `CodeAgent` and `SafetyAgent` working in parallel

### Meta-Intelligence (Phase 10) ✅
- 💭 **Internal Monologue** — Background thread simulating continuous conscious thought
- 🌙 **Dream Consolidation** — Nightly synthesis of episodic memory into Knowledge Graph insights
- 🚀 **Automated Self-Improvement** — LoRA extraction and dynamic PEFT adapter training

### Spatial Computing & AR (Phase 15) ✅
- 👓 **AR Wearable HUD** — High-speed WebSocket API for Meta Ray-Bans / Apple Vision Pro
- 🌐 **Spatial Awareness Engine** — 6-DOF device tracking, geofencing, and location-based intelligence
- 📌 **Spatial Anchors** — Pin digital knowledge to physical GPS coordinates
- 🗝️ **Spatial Memory** — Location-tagged memory storage and proximity recall ("what happened here?")
- 🔍 **Scene Understanding** — Real-time AR camera analysis with contextual HUD overlays
- 🧭 **Movement Analysis** — Activity detection (walking/running/driving) from GPS breadcrumb trails

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.ai) installed and running

### Setup
```bash
# 1. Enter project
cd adaptive-living-ai

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Copy env config
cp .env.example .env

# 5. Pull models
ollama pull llama3.2:3b
ollama pull nomic-embed-text

# 6. (Optional) Build the Rust Mesh Daemon for P2P memory sync
# Requires Rust to be installed (https://rustup.rs/)
cd mesh_daemon && cargo build && cd ..

# 7. Start the server (Backend, Mesh, and Desktop App)
./start_alas.sh

# 7. Open http://localhost:8000
```

### Docker (One Command)
```bash
docker compose up -d
docker exec alas-ollama ollama pull llama3.2:3b
docker exec alas-ollama ollama pull nomic-embed-text
# Open http://localhost:8000
```

### Access from Anywhere
```bash
# Install ngrok, then:
ngrok http 8000
# Open the URL on your phone → "Add to Home Screen" → ALAS is an app!
```

### Desktop App & Daemons (Linux/Mac/Win)
```bash
# 1. Start everything (Backend, Desktop App, and Rust Mesh Daemon)
./start_alas.sh

# 2. To build standalone executables
cd desktop
npm run dist:all
# Outputs AppImage, DMG, and EXE to desktop/dist/
```

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for cloud deployment options (Railway, Render, VPS).

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────┐
│  Frontend (PWA)          HTML/CSS/JS                   │
│  ├── Chat (WebSocket streaming)                        │
│  ├── Knowledge Graph (Canvas visualization)            │
│  ├── Evolution Dashboard (Genome traits)               │
│  └── Voice I/O (Web Speech API + server TTS/STT)       │
└──────────────────┬─────────────────────────────────────┘
                   │ WebSocket / REST API
┌──────────────────▼─────────────────────────────────────┐
│  FastAPI Backend                                       │
│  ├── LLM Engine (Ollama + ReAct tools + streaming)     │
│  ├── Agentic Autonomy (Phase 4)                        │
│  │   ├── Code Sandbox (subprocess isolation)           │
│  │   ├── Task Planner & Executor                       │
│  │   ├── Background Task Queue                         │
│  │   └── Specialized Agents (Git, Research)            │
│  ├── Memory                                            │
│  │   ├── L1 Episodic  (ChromaDB vector store)          │
│  │   ├── L2 Semantic  (NetworkX knowledge graph)       │
│  │   ├── L3 Profile   (SQLite + SQLAlchemy)            │
│  │   └── L5 Skills    (JSON procedural memory)         │
│  ├── Learning                                          │
│  │   ├── Self-Reflection Engine                        │
│  │   ├── Behavioral Evolution (genetic algorithm)      │
│  │   ├── Implicit Feedback Tracker                     │
│  │   └── LoRA Adapter Manager                          │
│  ├── Safety Filter (constitutional constraints)        │
│  ├── Emotion & Attention (WebRTC + MediaPipe)          │
│  └── Voice (WebRTC VAD + Whisper + Edge-TTS)           │
└──────────────────┬─────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────┐
│  Mesh Daemon (Rust)                                    │
│  └── P2P Memory Sync over Tailscale / Local Area       │
└──────────────────┬─────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────┐
│  Ollama                LLM inference server             │
│  ├── llama3.2:3b       (chat + reasoning)              │
│  ├── nomic-embed-text  (memory embeddings)             │
│  └── moondream/llava   (vision, optional)              │
└────────────────────────────────────────────────────────┘
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| WS | `/api/chat/ws` | Streaming chat WebSocket |
| POST | `/api/chat/message` | Non-streaming chat |
| POST | `/api/chat/vision` | Image analysis |
| GET | `/api/chat/health` | LLM health check |
| POST | `/api/memory/search` | Search episodic memories |
| GET | `/api/memory/stats` | Memory statistics |
| POST | `/api/memory/feedback` | Submit implicit feedback |
| GET | `/api/profile/{id}` | Get user profile |
| PUT | `/api/profile/{id}` | Update profile |
| GET | `/api/knowledge/graph` | Full knowledge graph data |
| GET | `/api/knowledge/stats` | Knowledge graph stats |
| POST | `/api/knowledge/consolidate` | Trigger memory consolidation |
| POST | `/api/learning/reflect` | Trigger self-reflection |
| GET | `/api/learning/evolution/status` | Evolution genome status |
| GET | `/api/learning/adapters` | List LoRA adapters |
| POST | `/api/voice/synthesize` | Text-to-speech |
| POST | `/api/voice/transcribe` | Speech-to-text |
| POST | `/api/tasks/submit` | Submit background task |
| GET | `/api/tasks/queue` | List background tasks |
| GET | `/api/tasks/plans` | List execution plans |
| GET | `/api/schedules` | List scheduled jobs |
| GET | `/api/status` | System health check |
| WS | `/api/ar/ws/{device_id}` | AR wearable bidirectional stream |
| GET | `/api/ar/status` | AR subsystem status |
| POST | `/api/ar/anchors` | Create spatial anchor |
| GET | `/api/ar/anchors` | List spatial anchors |
| DELETE | `/api/ar/anchors/{id}` | Delete spatial anchor |
| POST | `/api/ar/anchors/nearby` | Find nearby anchors |
| POST | `/api/ar/geofences` | Create geofence zone |
| GET | `/api/ar/geofences` | List geofences |
| DELETE | `/api/ar/geofences/{id}` | Delete geofence |
| POST | `/api/ar/memories` | Store spatial memory |
| POST | `/api/ar/memories/nearby` | Recall nearby memories |
| GET | `/api/ar/location/{device_id}` | Device location & context |
| GET | `/api/ar/devices` | List tracked devices |
| GET | `/api/ar/scene` | Current scene analysis |

---

## 📁 Project Structure

```
adaptive-living-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Pydantic settings
│   │   ├── api/                 # REST/WS endpoints
│   │   ├── llm/                 # LLM engine, tools, prompts, vision
│   │   ├── memory/              # Episodic, graph, profile, retrieval
│   │   ├── learning/            # Reflection, evolution, feedback, LoRA
│   │   ├── emotion/             # Emotion detection
│   │   ├── safety/              # Constitutional safety filter
│   │   └── voice/               # STT + TTS
│   ├── data/                    # Persistent data (ChromaDB, SQLite, KG)
│   └── requirements.txt
├── frontend/                    # Web Client (PWA)
│   ├── index.html               # Main UI
│   ├── manifest.json            # PWA manifest
│   ├── sw.js                    # Service worker
│   ├── css/styles.css           # Premium dark theme
│   └── js/                      # Chat, voice, memory, modes, KG, evolution
├── desktop/                     # Electron Desktop App (NEW)
│   ├── package.json             # Build config for Linux/Mac/Win
│   ├── main.js                  # Main process & tray integration
│   ├── preload.js               # Context isolation security bridge
│   └── src/                     # App UI, modules, and bio-inspired styles
├── docs/                        # Project documentation
│   ├── ALAS_Project_Documentation.md
│   ├── DEPLOYMENT.md
│   └── FUTURE_FEATURES.md
├── deploy/                      # Cloud deployment configurations
│   ├── railway.toml
│   └── render.yaml
├── scripts/                     # Utility and daemon scripts
│   ├── install_daemon.sh
│   ├── wake_daemon.py
│   └── train_evolution.py
├── Dockerfile                   # Container image
├── docker-compose.yml           # Full stack (ALAS + Ollama)
└── .env.example                 # Environment template
```

> **Phase 15 Modules:**
> - `backend/app/embodied/spatial.py` — 6-DOF Spatial Awareness Engine
> - `backend/app/embodied/spatial_memory.py` — Location-tagged Memory Layer
> - `backend/app/embodied/scene_understanding.py` — AR Scene Analysis
> - `backend/app/api/ar_hud.py` — Full AR Wearable API (WebSocket + REST)

---

## 🗺️ Roadmap (ALAS 2.0 Blueprint)

With the successful completion of **Phase 10**, ALAS has reached version 1.0.0.
The next frontier is **ALAS 2.0**, focusing on decentralized mesh networking and spatial computing.

### Upcoming Milestones (ALAS 2.0):
- **Phase 11** — Universal Tool Plug via **Model Context Protocol (MCP)** integration.
- **Phase 12** — Dynamic "Mixture of Compute" Router (combining local privacy with cloud supercomputer logic).
- **Phase 13** — Zero-Latency Perception via direct WebRTC multimodal streams.
- **Phase 14** — Decentralized P2P Mesh Network (Rust daemon for cross-device sync).
- **Phase 15** — Embodied Spatial Computing (AR Wearable HUD integration).

See the full [ALAS 2.0 Blueprint](ALAS_2.0_Blueprint.md) for architectural details.

---

*ALAS v2.0.0 — Phase 15: Embodied Spatial Computing | May 2026*
