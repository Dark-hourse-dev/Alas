---
tags:
  - project
  - ai
  - python
  - architecture
aliases:
  - ALAS
  - Adaptive Living AI System
---

# 🧬 ALAS: Adaptive Living AI System

## Overview
**ALAS** is not just a chatbot; it is a **persistent digital lifeform** integrated natively into your system environment. Designed to be highly modular, privacy-preserving, and continuously learning, ALAS bridges the gap between a standard LLM agent and an autonomous, evolving assistant.

## 🛠 Architecture & Tech Stack

ALAS is built on a highly modular, local-first architecture:

- **Brain (LLM):** Meta's `llama3.2:3b` running locally via [[Ollama]]. Fast, efficient, and fully private.
- **Backend / Nervous System:** A `FastAPI` server managed by `uvicorn`. It runs continuously as a background `systemd` daemon.
- **Short-Term Memory:** Handled via WebSockets for real-time streaming of conversational context.
- **Long-Term Memory:** 
  - **Vector Database:** `ChromaDB` (using `nomic-embed-text`) for semantic, associative memory.
  - **Relational DB:** `SQLite` for exact factual recall and user profile tracking.
  - **Knowledge Graph:** `NetworkX` mapping complex relationships between entities.
- **Senses:**
  - **Vision:** `llava` or `moondream` models process uploaded images.
  - **Ears (STT):** `faster-whisper` converts speech to text, with browser-based Web Speech API fallback. Includes a continuous background **Wake Word Engine**.
  - **Voice (TTS):** `edge-tts` provides high-quality, emotionally adaptive voice synthesis.
- **Agentic Actions (Hands):** A tool execution engine capable of running bash commands, managing files, and checking system info.

---

## 🧠 The Evolution Engine

ALAS is designed to mimic biological evolution. Instead of relying on manual configuration, ALAS learns your preferences through **Implicit Feedback**. 

### The Behavioral Genome
ALAS's personality is defined by four core DNA parameters (ranging from 0.0 to 1.0):
1. **Verbosity Weight:** How long the responses should be.
2. **Formality Index:** How casual or professional the tone is.
3. **Empathy Multiplier:** How strongly ALAS mirrors your detected emotional state.
4. **Proactivity Threshold:** How likely ALAS is to execute actions or volunteer information without explicit instruction.

### The Feedback Loop
1. **Interaction:** You interact with ALAS.
2. **Fitness Calculation:** The `FeedbackTracker` calculates a "Fitness Score" for the session based on:
   - *Corrections:* (e.g., saying "stop", "wrong") → massive penalty.
   - *Monologuing:* (e.g., ALAS talking too much when you speak too little) → penalty.
   - *Positive Sentiment:* → reward.
3. **Mutation:** Every 5 sessions, if the average fitness drops below `0.7`, ALAS **mutates**. It randomly adjusts one of its genome parameters up or down by 15%. Over time, the traits that result in high fitness scores (i.e., you being happy) survive.

---

## 🛡️ Safety & Permission Tiers

Because ALAS runs bash commands on your machine, it utilizes a strict, fail-safe security protocol:

| Tier | Status | Action | Example Commands |
| :--- | :---: | :--- | :--- |
| **🟢 AUTO** | Safe | Executes silently. | `ls`, `cat`, `echo`, `pwd` |
| **🟡 NOTIFY** | Warning | Executes but sends a desktop notification. | `pip install`, `cp`, `mv` |
| **🔴 ASK** | Danger | Blocked. Requires your manual approval. | `rm`, `sudo`, `chmod` |

---

## 🚀 Deployment & Usage

### 1. The Daemon
ALAS runs permanently in the background. It is installed via `install_daemon.sh` which sets up:
- `alas.service`: The core brain.
- `alas-tray.service`: The UI system tray indicator.
- `alas-wake.service`: The Wake Word engine listening for "Hey ALAS".

### 2. The Wake Word
You don't need a browser open. Because of the `wake_daemon.py`, you can simply say **"Hey ALAS"** out loud. ALAS will beep, listen to your command, and speak the answer back.

### 3. Web UI
The UI (`http://localhost:8000`) provides a rich chat interface, file/image upload functionality, and a real-time status sidebar showing the system's current phase.

---
## Related Links
*You can create new notes by clicking these links in Obsidian!*
- [[Ollama Setup Guide]]
- [[Systemd Service Logs]]
- [[Evolution Algorithm Ideas]]
