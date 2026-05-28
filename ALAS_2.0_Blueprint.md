# 🧬 ALAS 2.0: The Future-Ready Architecture Blueprint

**Vision:** Transition ALAS from a monolithic, polling-based Python backend into a decentralized, natively multimodal, real-time mesh network. ALAS 2.0 will be a "Digital Ghost" that lives across all your devices, sees what you see in real-time, and dynamically routes computing tasks between your local hardware and cloud supercomputers.

---

## 1. Core Architectural Shifts

### From ➔ To
- **Polling (REST/HTTP)** ➔ **Streaming (WebRTC/WebSockets)** for sub-200ms latency.
- **Custom Tool Wrappers** ➔ **Model Context Protocol (MCP)** for universal data access.
- **Single Device Local** ➔ **Peer-to-Peer Encrypted Mesh** (Cross-device continuity).
- **Text-to-Speech Pipeline** ➔ **Native Omni-Modal Audio/Vision weights**.
- **100% Local Compute** ➔ **Dynamic Router of Experts (Local + Cloud Fallback)**.

---

## 2. Proposed Technology Stack

| Subsystem | ALAS 1.0 Stack | ALAS 2.0 Proposed Stack | Why the Upgrade? |
|-----------|----------------|-------------------------|------------------|
| **Core Engine** | Ollama | **vLLM** + **Ollama** | vLLM enables KV-Cache offloading to NVMe SSDs, simulating massive 1M+ token context windows locally. |
| **Tool Calling** | Custom Python scripts | **Model Context Protocol (MCP)** | Instantly plug into GitHub, Slack, Notion, and Google Drive without writing custom integration code. |
| **Audio/Vision** | Whisper + OpenCV/MediaPipe | **WebRTC + Native Omni-Models** | Eliminates 3-second pipeline latency. The model hears the raw waveform and sees frames at 30fps. |
| **Memory** | ChromaDB (Local only) | **Qdrant (P2P synced) + SQLite** | Qdrant supports highly efficient distributed vector storage for cross-device memory syncing. |
| **Backend** | FastAPI (Python) | **FastAPI + Rust Daemon** | A lightweight Rust daemon runs quietly on mobile/desktop to handle the P2P mesh networking and encryption. |

---

## 3. The New Subsystems (How They Work)

### A. The "Mixture of Compute" Router (MoC)
ALAS 2.0 uses a semantic firewall.
1. **Input arrives** (e.g., "Refactor this 10,000 line Python file").
2. **Router evaluates complexity.** It determines a local 8B model will fail.
3. **Privacy Scrubber** automatically removes API keys, names, and passwords.
4. **Cloud Dispatch:** The prompt is sent to `Gemini 1.5 Pro` or `OpenAI o1`.
5. **Return:** The result is injected back into the local ALAS context.
*Result: Maximum privacy for daily tasks, infinite power for hard tasks.*

### B. Cross-Device Consciousness (The Mesh)
You install the ALAS Rust Daemon on your Phone, Laptop, and Server.
1. They connect via a **Tailscale** overlay network.
2. When you tell ALAS something on your phone, the semantic vector is broadcast to the mesh.
3. Your desktop instantly updates its Knowledge Graph.
4. You can ask ALAS on your desktop to execute a terminal command on your server.

### C. Spatial / AR Interface
ALAS 2.0 decouples the frontend.
- Standard Web UI (React/Next.js).
- Headless API designed for **AR Glasses** (Meta Ray-Bans / Apple Vision Pro). ALAS streams its internal monologue to your ear via Bluetooth and watches your physical environment through the glasses' camera.

---

## 4. Proposed Directory Structure (ALAS 2.0)

```text
adaptive-living-ai/
├── backend/                  # Python/FastAPI Core Reasoning Engine
│   ├── app/
│   │   ├── mcp/              # Model Context Protocol servers & clients
│   │   ├── router/           # Mixture of Compute (Local/Cloud router)
│   │   ├── webrtc/           # Real-time omni-modal audio/video streams
│   │   ├── memory/           # Qdrant vector sync + SQLite Knowledge Graph
│   │   └── cognition/        # Monologue, Dream, Swarm Orchestration
├── daemon/                   # Rust P2P Mesh Node (New)
│   ├── src/
│   │   ├── network/          # Encrypted mesh communication
│   │   ├── sync/             # Vector DB delta syncing
│   │   └── hardware/         # Low-level sensor access
├── frontend_web/             # Next.js Dashboard
└── frontend_ar/              # Lightweight clients for wearable integration
```

---

## 5. Execution Roadmap (Phases 11 - 15)

### Phase 11: The Universal Plug (MCP)
- Rip out custom tool wrappers.
- Implement an MCP Client in ALAS.
- Spin up standard MCP Servers for local File System, SQLite, and GitHub.
- *Milestone:* ALAS can now use thousands of community-built tools instantly.

### Phase 12: The Brain Expansion (vLLM & Routing)
- Swap the backend inference engine to vLLM to support KV-cache offloading.
- Build the Semantic Router. Integrate API keys for Gemini/OpenAI as *fallbacks* for complex queries.
- Build the PII scrubber to ensure privacy when routing to the cloud.

### Phase 13: Zero-Latency Perception (WebRTC)
- Deprecate the Whisper STT and pyttsx3 TTS pipelines.
- Implement a WebRTC server.
- Connect a natively multimodal model (e.g., Pixtral or Llama-3-Omni) to process audio waveforms and video frames in real-time.

### Phase 14: The Mesh Network
- Write the lightweight Rust daemon.
- Establish the P2P encrypted network between devices.
- Implement CRDTs (Conflict-free Replicated Data Types) to keep the SQLite Knowledge Graph and Vector memory perfectly synced across laptops and phones.

### Phase 15: Embodied Spatial Computing
- Connect ALAS to wearable AR hardware.
- Implement spatial awareness (ALAS understands where it is in physical space relative to you).
- Full "Digital Ghost" integration.

---

## Next Steps
To begin the transition to ALAS 2.0, the highest ROI first step is **Phase 11: The Universal Plug (MCP)**. This will instantly multiply ALAS's capabilities by allowing it to interface with your entire digital life (Drive, Slack, Notion) without writing custom integrations for each.
