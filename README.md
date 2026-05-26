# 🧬 ALAS — Adaptive Living AI System

> A persistent digital lifeform that learns, adapts, and evolves through continuous experience.

[![Phase](https://img.shields.io/badge/Phase-3%20Adaptive%20Learning-blueviolet)]()
[![Version](https://img.shields.io/badge/Version-0.3.0-cyan)]()
[![License](https://img.shields.io/badge/License-MIT-green)]()

---

## ✨ Features

### Core (Phase 1) ✅
- 🧠 **Persistent Memory** — ChromaDB episodic memory with semantic RAG retrieval
- 🤖 **Local LLM** — Ollama-powered streaming inference (llama3.2:3b)
- 🎙️ **Voice I/O** — Speech-to-text (Whisper) + Text-to-speech (Edge-TTS)
- 🎨 **Adaptive Modes** — Work, Casual, Creative, Learning, Calm
- 🛡️ **Safety Filter** — Constitutional constraint checking + PII detection
- 👤 **User Profile** — Persistent identity and preferences (SQLite)

### Cognitive Architecture (Phase 2) ✅
- 🕸️ **Knowledge Graph** — NetworkX-powered entity/relationship memory (L2)
- 🔮 **Vision Engine** — Multimodal image understanding (LLaVA/Moondream)
- 🧩 **Memory Consolidation** — Bio-inspired hippocampal replay
- 🔧 **Agentic Tools** — ReAct tool execution (time, weather, calculate, files)
- 📊 **Knowledge Graph UI** — Interactive canvas visualization
- 🔄 **Cross-Device Sync** — State export/import API

### Adaptive Learning (Phase 3) ✅
- 🧬 **Behavioral Evolution** — Genetic algorithm mutating personality parameters
- 🪞 **Self-Reflection** — LLM-powered session analysis updating user profile
- 📈 **Implicit Feedback** — Automatic fitness scoring from conversation metrics
- 🔌 **LoRA Adapters** — Dynamic adapter registry (coding, creative, finance)
- 📱 **PWA Support** — Installable as native app on any device
- 🐳 **Docker Deployment** — One-command cloud deployment

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

# 6. Start the server
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

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

See [DEPLOYMENT.md](DEPLOYMENT.md) for cloud deployment options (Railway, Render, VPS).

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
│  ├── Emotion Detector (7 categories)                   │
│  └── Voice (Whisper STT + Edge-TTS)                    │
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
| GET | `/api/status` | System health check |

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
├── frontend/
│   ├── index.html               # Main UI
│   ├── manifest.json            # PWA manifest
│   ├── sw.js                    # Service worker
│   ├── css/styles.css           # Premium dark theme
│   ├── js/                      # Chat, voice, memory, modes, KG, evolution
│   └── assets/                  # App icon
├── Dockerfile                   # Container image
├── docker-compose.yml           # Full stack (ALAS + Ollama)
├── railway.toml                 # Railway deployment config
├── render.yaml                  # Render deployment config
├── DEPLOYMENT.md                # Cloud deployment guide
├── FUTURE_FEATURES.md           # 155-feature roadmap
└── .env.example                 # Environment template
```

---

## 🗺️ Roadmap

See [FUTURE_FEATURES.md](FUTURE_FEATURES.md) for the full 155-feature roadmap including:
- 🔥 **Phase 3.5** — Always-On System Integration (wake word, auto-start, OS integration)
- **Phase 4** — Agentic Autonomy (web browsing, code sandbox, email/calendar)
- **Phase 5** — Cognitive Superpowers (causal reasoning, knowledge mastery)
- **Phase 6–10** — Sensory mastery, robotics, swarm intelligence, meta-learning

---

*ALAS v0.3.0 — Phase 3: Adaptive Learning | May 2026*
