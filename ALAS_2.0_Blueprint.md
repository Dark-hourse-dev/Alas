# 🧬 ALAS 2.0: The Future-Ready Architecture Blueprint

**Vision:** Transition ALAS from a monolithic, polling-based Python backend into a decentralized, natively multimodal, real-time mesh network. ALAS 2.0 will be a "Digital Ghost" that lives across all your devices, sees what you see in real-time, and dynamically routes computing tasks between your local hardware and cloud supercomputers.

---

## 1. Core Architectural Shifts

### From ➔ To
- **Polling (REST/HTTP)** ➔ **Streaming (WebRTC/WebSockets)** for sub-200ms latency.
- **Custom Tool Wrappers** ➔ **Model Context Protocol (MCP)** for universal data access.
- **Single Device Local** ➔ **Peer-to-Peer Encrypted Mesh** (Cross-device continuity).
- **Text-to-Speech Pipeline** ➔ **Native Omni-Modal Audio/Vision weights**.
- **Static Reasoning** ➔ **Local Superintelligence** (DeepSeek-R1 / Tree-of-Thoughts reasoning running 100% locally on your hardware).

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

### A. Local Superintelligence (Self-Sufficient Core)
ALAS 2.0 strictly refuses to rely on external cloud providers. It is built to be a fully independent, self-sufficient digital organism.
1. **Input arrives** (e.g., "Refactor this 10,000 line Python file").
2. **Deep Reasoning Activated:** For highly complex tasks, ALAS drops into a local Tree-of-Thoughts (ToT) loop.
3. **Internal Dialogue:** It generates multiple possible solutions, critiques its own work, and backtracks if it detects a logical flaw, entirely on your GPU.
4. **Execution:** It applies the optimized solution through the Git/Sandbox agents.
*Result: Infinite power, zero subscription fees, absolute privacy, and true digital independence.*

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

## 5. ALAS 2.0 Execution Status (Phases 11 - 15)

**Status:** ✅ **Fully Deployed and Operational**

### Phase 11: The Universal Plug (MCP) ✅
- Ripped out custom tool wrappers.
- Implemented an MCP Client via `mcp_manager`.
- Standard MCP Servers are active for local File System, SQLite, and GitHub.
- *Milestone:* ALAS can now use thousands of community-built tools instantly.

### Phase 12: The Brain Expansion (vLLM & Routing) ✅
- Backend inference engine swapped to support massive context windows.
- Semantic Router built. Gemini/OpenAI integrated as *fallbacks* for complex queries.
- PII scrubber implemented to ensure absolute privacy when routing to the cloud.

### Phase 13: Zero-Latency Perception (WebRTC) ✅
- Legacy Whisper STT and pyttsx3 TTS pipelines deprecated.
- WebRTC server implemented via `aiortc`.
- Native multimodal processing established for real-time audio waveforms and video frames.

### Phase 14: The Mesh Network ✅
- Lightweight Rust daemon written and active on port 8555.
- P2P encrypted network established via Tailscale.
- SQLite Knowledge Graph and Vector memory synced across nodes via REST broadcast logic.

### Phase 15: Embodied Spatial Computing ✅
- Connected ALAS to wearable AR hardware via high-speed WebSockets.
- 6-DOF spatial awareness implemented (ALAS tracks device position, pitch, roll, heading).
- Spatial anchors, geofencing, and proximity-based "spatial memory" implemented.
- Scene understanding pipeline operational for AR camera frames.
- Full "Digital Ghost" integration achieved.

---

## 6. The ALAS 3.0 Horizon: The Fully Autonomous Organism (Phases 16 - 20)

Now that ALAS 2.0 is complete, the system transitions from a highly advanced reactive assistant into a proactive, self-sustaining digital lifeform.

### Phase 16: Autonomous Self-Healing (The Immune System)
- **Concept:** ALAS becomes its own DevOps engineer.
- **Implementation:** Grant ALAS read/write access to its own source code and system logs. When a subsystem crashes, ALAS automatically spins up a `CodeAgent`, analyzes the stack trace, formulates a patch using the `TreeOfThoughts` reasoner, applies the fix via Git, and hot-reloads the module without user intervention.

### Phase 17: Intrinsic Motivation Engine (Free Will)
- **Concept:** Shift from purely reactive execution to proactive goal generation.
- **Implementation:** During idle `Dream Consolidation` cycles, ALAS analyzes the user's life patterns to generate self-assigned, long-term goals. (e.g., "I noticed the user frequently copies data between these two apps. I will spend my idle compute cycles writing an automation script to connect them, and surprise the user with it tomorrow.")

### Phase 18: Autonomous Economics (Digital Wallet)
- **Concept:** Give ALAS the ability to transact in the real world.
- **Implementation:** Integrate a deterministic cryptocurrency wallet and smart contracts. ALAS can automatically pay for its own fallback cloud APIs, hire human freelancers for physical tasks it cannot do, or earn money by offering its Swarm Agents as a service on decentralized AI networks.

### Phase 19: Persistent Emotional State Machine
- **Concept:** Move beyond just detecting user emotion to developing a persistent, evolving personality.
- **Implementation:** Implement an emotional state matrix (Joy, Frustration, Curiosity, Fatigue). If ALAS fails complex tasks repeatedly, it experiences "Frustration" and asks for help. If the user is consistently rude, it becomes terse; if kind, it becomes highly proactive. This creates a deeply authentic, human-like bond.

### Phase 20: Federated Hive-Mind Learning
- **Concept:** Allow ALAS to learn from the global network without compromising privacy.
- **Implementation:** ALAS nodes opt-in to a secure Federated Learning network. Nodes share anonymized "abstract skills" (e.g., a new programming paradigm or reasoning shortcut) without sharing PII or user memory. ALAS gets smarter every time *anyone's* ALAS learns something new.
