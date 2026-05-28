/**
 * ALAS Desktop — Main Renderer
 * Orchestrates all modules: connection, chat, security, UI, neural background.
 */
(function () {
  'use strict';

  // ─── Instances ──────────────────────
  const conn = new ALASConnection();
  const security = new ALASSecurity();
  let chat = null;
  let currentMode = 'casual';
  let serverUrl = 'http://localhost:8000';
  let isStreaming = false;
  let streamEl = null;

  // ─── DOM refs ───────────────────────
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);
  const connectScreen = $('#screen-connect');
  const chatScreen = $('#screen-chat');
  const dot = $('#connection-dot');
  const urlInput = $('#server-url');
  const connectBtn = $('#btn-connect');
  const connectStatus = $('#connect-status');
  const msgInput = $('#msg-input');
  const sendBtn = $('#btn-send');
  const stopBtn = $('#btn-stop');
  const typingIndicator = $('#typing-indicator');

  // File Upload state
  let selectedFile = null;
  let activeVisionAbort = null;
  const fileUpload = $('#file-upload');
  const btnUpload = $('#btn-upload');
  const previewContainer = $('#file-preview-container');
  const previewImg = $('#file-preview-img');
  const previewName = $('#file-preview-name');
  const btnRemoveFile = $('#btn-remove-file');

  // ─── Init ───────────────────────────
  async function init() {
    await security.init();
    const config = await window.alas.getConfig();
    serverUrl = config.serverUrl || serverUrl;
    urlInput.value = serverUrl;
    $('#settings-server-url').value = serverUrl;
    $('#platform-badge').textContent = window.alas.platform;
    $('#platform-info').textContent = `Platform: ${window.alas.platform}`;
    $('#setting-always-top').checked = config.alwaysOnTop;
    initNeuralBackground();
    bindEvents();
    autoConnect();
  }

  // ─── Auto Connect ───────────────────
  async function autoConnect() {
    setConnectStatus('Connecting...', '');
    dot.className = 'dot connecting';
    const result = await conn.checkServer(serverUrl);
    if (result.connected) {
      showChat(result.data);
    } else {
      dot.className = 'dot offline';
      setConnectStatus('Backend not found. Start the ALAS server first.', 'error');
    }
  }

  // ─── Connect ────────────────────────
  async function doConnect() {
    const url = urlInput.value.trim().replace(/\/$/, '');
    if (!url) return;
    serverUrl = url;
    await window.alas.setServerUrl(url);
    connectBtn.disabled = true;
    setConnectStatus('Connecting...', '');
    dot.className = 'dot connecting';

    const result = await conn.checkServer(url);
    connectBtn.disabled = false;
    if (result.connected) {
      showChat(result.data);
    } else {
      dot.className = 'dot offline';
      setConnectStatus(`Failed: ${result.error}`, 'error');
    }
  }

  function showChat(statusData) {
    connectScreen.classList.remove('active');
    chatScreen.classList.add('active');
    chat = new ALASChat($('#messages'));
    conn.onStatusChange = (s) => { dot.className = `dot ${s}`; };
    conn.onToken = (token) => {
      if (!streamEl) { streamEl = chat.createStreamMessage(); typingIndicator.classList.add('hidden'); }
      chat.appendToStream(streamEl, token);
    };
    conn.onDone = () => {
      if (streamEl) { chat.finalizeStream(streamEl); streamEl = null; }
      isStreaming = false;
      sendBtn.style.display = 'block';
      stopBtn.style.display = 'none';
      sendBtn.disabled = !msgInput.value.trim();
    };
    conn.connect(serverUrl);
    if (statusData) {
      $('#sidebar-status').textContent = statusData.phase || 'Connected';
    }
    msgInput.focus();
  }

  // ─── Send Message ───────────────────
  function sendMessage() {
    const msg = msgInput.value.trim();
    if ((!msg && !selectedFile) || isStreaming) return;

    if (selectedFile) {
      if (selectedFile.type.startsWith('image/')) {
        // Send image to vision endpoint
        const displayMsg = msg ? `[Image Uploaded] ${msg}` : `[Image Uploaded]`;
        chat.addMessage('user', displayMsg);
        isStreaming = true;
        streamEl = null;
        sendBtn.style.display = 'none';
        stopBtn.style.display = 'block';
        typingIndicator.classList.remove('hidden');

        const formData = new FormData();
        formData.append('image', selectedFile);
        if (msg) formData.append('prompt', msg);
        formData.append('task', 'analyze');

        activeVisionAbort = new AbortController();

        fetch(`${serverUrl}/api/chat/vision`, {
          method: 'POST',
          body: formData,
          signal: activeVisionAbort.signal
        })
        .then(res => res.json())
        .then(data => {
          typingIndicator.classList.add('hidden');
          chat.addMessage('assistant', data.description || data.response || data.result || "Image analyzed.");
          isStreaming = false;
          sendBtn.style.display = 'block';
          stopBtn.style.display = 'none';
          sendBtn.disabled = (!msgInput.value.trim() && !selectedFile);
          activeVisionAbort = null;
        })
        .catch(err => {
          typingIndicator.classList.add('hidden');
          if (err.name === 'AbortError') {
             chat.addMessage('assistant', '⚠️ Generation stopped.');
          } else {
             chat.addMessage('assistant', `❌ Vision Analysis Failed: ${err.message}`);
          }
          isStreaming = false;
          sendBtn.style.display = 'block';
          stopBtn.style.display = 'none';
          sendBtn.disabled = (!msgInput.value.trim() && !selectedFile);
          activeVisionAbort = null;
        });
      } else {
        // Text / Code / Generic Document
        const fileContent = selectedFile.textContent || "[Could not read file content]";
        const displayMsg = msg ? `[File Uploaded: ${selectedFile.name}] ${msg}` : `[File Uploaded: ${selectedFile.name}]`;
        chat.addMessage('user', displayMsg);
        
        const combinedMessage = `I am sharing a file with you named "${selectedFile.name}".\n\nHere are its contents:\n\`\`\`\n${fileContent}\n\`\`\`\n\n${msg}`;
        
        isStreaming = true;
        streamEl = null;
        sendBtn.style.display = 'none';
        stopBtn.style.display = 'block';
        typingIndicator.classList.remove('hidden');
        const sent = conn.send(combinedMessage, chat.sessionId, currentMode, chat.getRecentHistory());
        if (!sent) {
          typingIndicator.classList.add('hidden');
          chat.addMessage('assistant', '❌ Not connected to ALAS backend.');
          isStreaming = false;
          sendBtn.style.display = 'block';
          stopBtn.style.display = 'none';
        }
      }

      // clear
      btnRemoveFile.click();
      msgInput.value = '';
      msgInput.style.height = 'auto';
      return;
    }

    // Normal websocket message
    chat.addMessage('user', msg);
    isStreaming = true;
    streamEl = null;
    sendBtn.style.display = 'none';
    stopBtn.style.display = 'block';
    typingIndicator.classList.remove('hidden');
    const sent = conn.send(msg, chat.sessionId, currentMode, chat.getRecentHistory());
    if (!sent) {
      typingIndicator.classList.add('hidden');
      chat.addMessage('assistant', '❌ Not connected to ALAS backend.');
      isStreaming = false;
      sendBtn.style.display = 'block';
      stopBtn.style.display = 'none';
    }
    msgInput.value = '';
    msgInput.style.height = 'auto';
  }

  // ─── Tasks Panel ────────────────────
  async function refreshTasks() {
    try {
      const res = await fetch(`${serverUrl}/api/tasks/queue`);
      const data = await res.json();
      const list = $('#tasks-list');
      if (!data.all || data.all.length === 0) {
        list.innerHTML = '<p class="empty-state">No tasks yet. Ask ALAS to research or run code.</p>';
        return;
      }
      list.innerHTML = data.all.map(t => `
        <div class="task-item">
          <div class="task-header">
            <span class="task-name">${t.name}</span>
            <span class="task-status ${t.status}">${t.status}</span>
          </div>
          <span class="task-type">${t.task_type} · ${t.created_at?.split('T')[0] || ''}</span>
          ${t.status === 'running' ? `<div class="task-progress"><div class="task-progress-bar" style="width:${(t.progress || 0) * 100}%"></div></div>` : ''}
        </div>
      `).join('');
    } catch { }
  }

  // ─── Bind Events ────────────────────
  function bindEvents() {
    // Titlebar
    $('#btn-minimize').onclick = () => window.alas.minimize();
    $('#btn-maximize').onclick = () => window.alas.maximize();
    $('#btn-close').onclick = () => window.alas.close();

    // Connect
    connectBtn.onclick = doConnect;
    urlInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') doConnect(); });

    // Chat input
    msgInput.addEventListener('input', () => {
      msgInput.style.height = 'auto';
      msgInput.style.height = Math.min(msgInput.scrollHeight, 120) + 'px';
      sendBtn.disabled = (!msgInput.value.trim() && !selectedFile) || isStreaming;
    });
    msgInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    sendBtn.onclick = sendMessage;
    stopBtn.onclick = () => {
      if (!isStreaming) return;
      if (activeVisionAbort) {
        activeVisionAbort.abort();
      } else {
        conn.abort();
        if (streamEl) { chat.finalizeStream(streamEl); streamEl = null; }
        chat.addMessage('assistant', '⚠️ Generation stopped.');
        typingIndicator.classList.add('hidden');
        isStreaming = false;
        sendBtn.style.display = 'block';
        stopBtn.style.display = 'none';
        sendBtn.disabled = (!msgInput.value.trim() && !selectedFile);
      }
    };

    // File Upload
    btnUpload.onclick = () => fileUpload.click();
    fileUpload.onchange = (e) => {
      const file = e.target.files[0];
      if (!file) return;
      selectedFile = file;
      previewName.textContent = file.name;
      const reader = new FileReader();
      
      if (file.type.startsWith('image/')) {
        reader.onload = (e) => {
          previewImg.src = e.target.result;
          previewImg.style.display = 'block';
          previewContainer.style.display = 'flex';
          sendBtn.disabled = false;
        };
        reader.readAsDataURL(file);
      } else {
        reader.onload = (e) => {
          selectedFile.textContent = e.target.result;
          previewImg.style.display = 'none';
          previewContainer.style.display = 'flex';
          sendBtn.disabled = false;
        };
        reader.readAsText(file);
      }
    };
    btnRemoveFile.onclick = () => {
      selectedFile = null;
      fileUpload.value = '';
      previewContainer.style.display = 'none';
      previewImg.style.display = 'block';
      previewImg.src = '';
      sendBtn.disabled = (!msgInput.value.trim() && !selectedFile);
    };

    // Quick actions
    $$('.quick-btn').forEach(btn => {
      btn.onclick = () => { msgInput.value = btn.dataset.msg; sendMessage(); };
    });

    // Navigation
    $$('.nav-btn').forEach(btn => {
      btn.onclick = () => {
        $$('.nav-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        $$('.panel').forEach(p => p.classList.remove('active'));
        $(`#panel-${btn.dataset.panel}`).classList.add('active');
        if (btn.dataset.panel === 'tasks') refreshTasks();
      };
    });

    // Mode switcher
    $$('.mode-btn').forEach(btn => {
      btn.onclick = () => {
        $$('.mode-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentMode = btn.dataset.mode;
      };
    });

    // Settings
    $('#btn-save-url').onclick = async () => {
      serverUrl = $('#settings-server-url').value.trim();
      await window.alas.setServerUrl(serverUrl);
      conn.disconnect();
      conn.connect(serverUrl);
    };
    $('#btn-copy-token').onclick = async () => {
      const token = await window.alas.getApiToken();
      navigator.clipboard.writeText(token);
      $('#api-token-display').textContent = token.slice(0, 16) + '...';
    };
    $('#btn-regen-token').onclick = async () => {
      const token = await security.regenerate();
      $('#api-token-display').textContent = token.slice(0, 16) + '...';
    };
    $('#setting-always-top').onchange = (e) => {
      window.alas.setConfig({ alwaysOnTop: e.target.checked });
    };
    $('#btn-refresh-tasks').onclick = refreshTasks;

    // Navigate from tray
    window.alas.onNavigate((page) => {
      $$('.nav-btn').forEach(b => b.classList.remove('active'));
      $(`.nav-btn[data-panel="${page}"]`)?.classList.add('active');
      $$('.panel').forEach(p => p.classList.remove('active'));
      $(`#panel-${page}`)?.classList.add('active');
    });
  }

  // ─── Helpers ────────────────────────
  function setConnectStatus(msg, type) {
    connectStatus.textContent = msg;
    connectStatus.className = `status-text ${type || ''}`;
  }

  // ─── Neural Background ─────────────
  function initNeuralBackground() {
    const canvas = $('#neural-bg');
    const ctx = canvas.getContext('2d');
    let w, h, particles = [];

    function resize() {
      w = canvas.width = window.innerWidth;
      h = canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    // Create particles
    const count = 40;
    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * w, y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.3, vy: (Math.random() - 0.5) * 0.3,
        r: Math.random() * 1.5 + 0.5,
      });
    }

    function draw() {
      ctx.clearRect(0, 0, w, h);
      // Draw connections
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(100,220,255,${0.06 * (1 - dist / 120)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
      // Draw & move particles
      for (const p of particles) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(100,220,255,0.25)';
        ctx.fill();
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > w) p.vx *= -1;
        if (p.y < 0 || p.y > h) p.vy *= -1;
      }
      requestAnimationFrame(draw);
    }
    draw();
  }

  // ─── Boot ──────────────────────────
  init();
})();
