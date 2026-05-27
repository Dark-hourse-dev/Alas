# 🚀 ALAS — Deployment Guide

> Access ALAS from anywhere: your phone, tablet, laptop, or any browser.

---

## Quick Overview

| Method | Difficulty | Cost | Best For |
|--------|-----------|------|----------|
| **Option 1: ngrok tunnel** | ⭐ Easy | Free | Instant access from anywhere (testing) |
| **Option 2: Railway** | ⭐⭐ Easy | Free tier | Permanent cloud URL |
| **Option 3: Render** | ⭐⭐ Easy | Free tier | Permanent cloud URL |
| **Option 4: VPS (DigitalOcean)** | ⭐⭐⭐ Medium | $6/mo | Full control + GPU option |
| **Option 5: Docker anywhere** | ⭐⭐ Easy | Varies | Any server with Docker |

---

## Option 1: Instant Access via ngrok (Recommended to start)

This is the **fastest way** to access ALAS from your phone right now.

### Step 1: Install ngrok
```bash
# Linux
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok-v3-stable-linux-amd64.tgz | sudo tar xvz -C /usr/local/bin

# Or via snap
sudo snap install ngrok
```

### Step 2: Sign up (free) and authenticate
```bash
# Get your auth token from https://dashboard.ngrok.com/get-started/your-authtoken
ngrok config add-authtoken YOUR_TOKEN
```

### Step 3: Start ALAS + ngrok
```bash
# Terminal 1: Start ALAS
cd ~/workspace/adaptive-living-ai
source venv/bin/activate
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start ngrok tunnel
ngrok http 8000
```

### Step 4: Access from anywhere
ngrok gives you a URL like: `https://abc123.ngrok-free.app`
- Open it on your **phone browser** → tap "Add to Home Screen" → ALAS is now an app!
- Share the URL with anyone to let them try ALAS

---

## Option 2: Deploy to Railway (Free Tier)

Railway gives you a permanent `*.up.railway.app` URL.

### Step 1: Push to GitHub
```bash
cd ~/workspace/adaptive-living-ai
git init
git add .
git commit -m "ALAS v0.3.0 — Phase 3 Adaptive Learning"
git remote add origin https://github.com/YOUR_USERNAME/adaptive-living-ai.git
git push -u origin main
```

### Step 2: Deploy
1. Go to [railway.app](https://railway.app)
2. Click **"New Project"** → **"Deploy from GitHub Repo"**
3. Select your `adaptive-living-ai` repo
4. Railway detects the `Dockerfile` automatically
5. Add environment variables (copy from `.env.example`)
6. Click **Deploy** → get your live URL!

> ⚠️ **Note:** Railway's free tier may not have enough resources for Ollama. 
> You can keep Ollama running on your PC and set `OLLAMA_HOST` to your PC's ngrok tunnel.

---

## Option 3: Deploy to Render (Free Tier)

### Step 1: Push to GitHub (same as above)

### Step 2: Deploy
1. Go to [render.com](https://render.com)
2. Click **"New Web Service"**
3. Connect your GitHub repo
4. Render detects the `render.yaml` config automatically
5. Click **"Create Web Service"**
6. Get your `*.onrender.com` URL!

---

## Option 4: VPS with GPU (Best for Ollama)

For full Ollama support with GPU acceleration.

### Step 1: Get a VPS
- **DigitalOcean GPU Droplet** — from $6/mo (CPU) or $150/mo (GPU)
- **Hetzner** — from €4.50/mo
- **AWS EC2** — g4dn.xlarge for GPU

### Step 2: Setup
```bash
# SSH into your server
ssh root@YOUR_SERVER_IP

# Install Docker
curl -fsSL https://get.docker.com | sh

# Clone your repo
git clone https://github.com/YOUR_USERNAME/adaptive-living-ai.git
cd adaptive-living-ai

# Start everything (Ollama + ALAS)
docker compose up -d

# Pull the LLM model
docker exec alas-ollama ollama pull llama3.2:3b
docker exec alas-ollama ollama pull nomic-embed-text
```

### Step 3: Access
Your ALAS is now live at `http://YOUR_SERVER_IP:8000`

### Step 4: Add HTTPS (recommended)
```bash
# Install Caddy for automatic HTTPS
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main" | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy

# Configure Caddy (replace with your domain)
echo 'alas.yourdomain.com {
    reverse_proxy localhost:8000
}' | sudo tee /etc/caddy/Caddyfile

sudo systemctl restart caddy
```

Now access ALAS at `https://alas.yourdomain.com` with automatic SSL!

---

## Option 5: Docker on Any Machine

```bash
# Clone and run
git clone https://github.com/YOUR_USERNAME/adaptive-living-ai.git
cd adaptive-living-ai
docker compose up -d

# Pull models
docker exec alas-ollama ollama pull llama3.2:3b
docker exec alas-ollama ollama pull nomic-embed-text

# Open in browser
open http://localhost:8000
```

---

## 📱 Install as App (PWA)

Once ALAS is running (locally or in the cloud), you can install it as a native app:

### On Phone (Android/iOS)
1. Open ALAS URL in your browser
2. Tap the **Share** button (or ⋮ menu)
3. Tap **"Add to Home Screen"** / **"Install App"**
4. ALAS now appears as a standalone app with its own icon!

### On Desktop (Chrome/Edge)
1. Open ALAS URL in Chrome/Edge
2. Click the **install icon** (⊕) in the address bar
3. Click **"Install"**
4. ALAS opens as a standalone desktop app!

### Features of PWA:
- ✅ Standalone window (no browser chrome)
- ✅ Home screen icon on phone
- ✅ Offline support for cached pages
- ✅ Push notification ready
- ✅ Works on Android, iOS, Windows, macOS, Linux

---

## 🔧 Hybrid Architecture (Recommended)

The best setup is a **hybrid** where the frontend is accessible from anywhere but Ollama runs on your local machine with GPU:

```
┌─────────────────────────────┐
│   Your Phone / Tablet       │
│   (PWA installed)           │
│   alas.yourdomain.com       │
└──────────┬──────────────────┘
           │ HTTPS
           ▼
┌─────────────────────────────┐
│   Cloud VPS ($6/mo)         │
│   - ALAS Backend (FastAPI)  │
│   - ChromaDB, SQLite        │
│   - Frontend (static)       │
└──────────┬──────────────────┘
           │ API calls
           ▼
┌─────────────────────────────┐
│   Your PC (home network)    │
│   - Ollama + GPU            │
│   - ngrok tunnel            │
│   - LLaMA 3.2, Whisper      │
└─────────────────────────────┘
```

This way:
- ALAS is accessible from anywhere via cloud URL
- Heavy LLM inference runs on your GPU at home (free, fast)
- Memory and state persist in the cloud
- If your PC is off, ALAS can fall back to a smaller cloud model

---

## 🔐 Security Notes

- Always use HTTPS in production (Caddy handles this automatically)
- Set strong `CORS_ORIGINS` in `.env` to only allow your domains
- Consider adding basic auth for cloud deployments:
  ```python
  # Add to main.py for basic protection
  from fastapi.security import HTTPBasic
  ```
- Your memory data (conversations, knowledge graph) is stored on the server — ensure disk encryption

---

*ALAS Deployment Guide v1.0 | May 2026*
