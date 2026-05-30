/**
 * ALAS Chat Module — WebSocket streaming + message rendering.
 */

class ALASChat {
  constructor() {
    this.ws = null;
    this.sessionId = this._generateId();
    this.mode = 'casual';
    this.userId = 'default';
    this.history = [];
    this.isStreaming = false;
    this.voiceOutputEnabled = false;
    this.onStatusChange = null;
    this.onMemoryUpdate = null;
    this._reconnectAttempts = 0;
    this._maxReconnectDelay = 15000;
    this._useRestFallback = false;
  }

  connect() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${location.host}/api/chat/ws`;

    try {
      this.ws = new WebSocket(url);
    } catch (e) {
      console.warn('WebSocket creation failed, using REST fallback:', e);
      this._useRestFallback = true;
      this._setStatus('connected', 'Connected (REST)');
      return;
    }

    this.ws.onopen = () => {
      this._reconnectAttempts = 0;
      this._useRestFallback = false;
      this._setStatus('connected', 'Connected');
    };

    this.ws.onclose = (e) => {
      this._setStatus('disconnected', 'Disconnected');
      // Exponential backoff: 1s, 2s, 4s, 8s, max 15s
      this._reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this._reconnectAttempts - 1), this._maxReconnectDelay);
      console.log(`WebSocket closed. Reconnecting in ${delay}ms (attempt ${this._reconnectAttempts})`);
      setTimeout(() => this.connect(), delay);
    };

    this.ws.onerror = (e) => {
      console.error('WebSocket error:', e);
      // After 3 failed attempts, switch to REST fallback
      if (this._reconnectAttempts >= 3) {
        console.warn('WebSocket unstable. Switching to REST API fallback.');
        this._useRestFallback = true;
        this._setStatus('connected', 'Connected (REST)');
      } else {
        this._setStatus('error', 'Connection error');
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this._handleMessage(data);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };
  }

  send(message) {
    if (this.isStreaming) return;

    // Hide welcome message
    const welcome = document.getElementById('welcome-message');
    if (welcome) welcome.style.display = 'none';

    // Add user message to UI
    this._addMessage('user', message);
    this.history.push({ role: 'user', content: message });

    // Show typing indicator
    this.isStreaming = true;
    document.getElementById('typing-indicator').style.display = 'flex';
    document.getElementById('stop-generation-container').style.display = 'flex';

    // Create assistant message placeholder
    this._currentAssistant = this._addMessage('assistant', '', true);

    // Use REST fallback if WebSocket is not available
    if (this._useRestFallback || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this._sendViaRest(message);
      return;
    }

    // Send via WebSocket
    try {
      this.ws.send(JSON.stringify({
        message,
        session_id: this.sessionId,
        mode: this.mode,
        user_id: this.userId,
        history: this.history.slice(-10),
      }));
    } catch (e) {
      console.error('WebSocket send failed, falling back to REST:', e);
      this._sendViaRest(message);
    }
  }

  async _sendViaRest(message) {
    /**
     * REST API fallback for when WebSocket is unavailable.
     * Critical for ngrok/tunnel deployments where WSS may not work.
     */
    this.currentController = new AbortController();
    try {
      const res = await fetch('/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: this.currentController.signal,
        body: JSON.stringify({
          message,
          session_id: this.sessionId,
          mode: this.mode,
          user_id: this.userId,
        }),
      });

      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`);
      }

      const data = await res.json();

      // Simulate the streaming completion flow
      if (this._currentAssistant) {
        const textEl = this._currentAssistant.querySelector('.message-text');
        const cursor = this._currentAssistant.querySelector('.cursor-blink');
        if (cursor) cursor.remove();

        textEl.innerHTML = this._formatMarkdown(data.response || 'No response received.');
        this.history.push({ role: 'assistant', content: data.response || '' });

        // Add feedback and copy buttons
        const rawContent = data.response || '';
        const feedbackHtml = `
          <div class="message-feedback">
            <button class="feedback-btn" onclick="window.alasChat.submitFeedback(this, 'positive', \`${rawContent.replace(/`/g, '\\`').replace(/'/g, "\\'")}\`)">👍</button>
            <button class="feedback-btn" onclick="window.alasChat.submitFeedback(this, 'negative', \`${rawContent.replace(/`/g, '\\`').replace(/'/g, "\\'")}\`)">👎</button>
            <button class="feedback-btn" style="margin-left:8px;" onclick="navigator.clipboard.writeText(\`${rawContent.replace(/`/g, '\\`').replace(/'/g, "\\'").replace(/\n/g, '\\n')}\`); this.textContent='Copied!'; setTimeout(()=>this.textContent='📋', 2000)" title="Copy Response">📋</button>
          </div>
        `;
        this._currentAssistant.querySelector('.message-time').insertAdjacentHTML('afterend', feedbackHtml);
      }

      this.isStreaming = false;
      document.getElementById('typing-indicator').style.display = 'none';
      document.getElementById('stop-generation-container').style.display = 'none';
      if (this.onMemoryUpdate) this.onMemoryUpdate(data.memory_count || 0);
      this._scrollToBottom();

    } catch (err) {
      if (err.name === 'AbortError') return;
      this.isStreaming = false;
      document.getElementById('typing-indicator').style.display = 'none';
      document.getElementById('stop-generation-container').style.display = 'none';
      this._showError(`Failed to get response: ${err.message}`);
    }
  }

  _handleMessage(data) {
    switch (data.type) {
      case 'token':
        if (this._currentAssistant) {
          this._appendToken(this._currentAssistant, data.content);
        }
        break;

      case 'done':
        this.isStreaming = false;
        document.getElementById('typing-indicator').style.display = 'none';
        document.getElementById('stop-generation-container').style.display = 'none';
        if (this._currentAssistant) {
          const cursor = this._currentAssistant.querySelector('.cursor-blink');
          if (cursor) cursor.remove();
          
          // Render markdown properly after completion
          const textEl = this._currentAssistant.querySelector('.message-text');
          const rawContent = textEl.textContent;
          textEl.innerHTML = this._formatMarkdown(rawContent);
          
          this.history.push({ role: 'assistant', content: rawContent });

          // Add feedback and copy buttons
          const feedbackHtml = `
            <div class="message-feedback">
              <button class="feedback-btn" onclick="window.alasChat.submitFeedback(this, 'positive', \`${rawContent.replace(/`/g, '\\`').replace(/'/g, "\\'")}\`)">👍</button>
              <button class="feedback-btn" onclick="window.alasChat.submitFeedback(this, 'negative', \`${rawContent.replace(/`/g, '\\`').replace(/'/g, "\\'")}\`)">👎</button>
              <button class="feedback-btn" style="margin-left:8px;" onclick="navigator.clipboard.writeText(\`${rawContent.replace(/`/g, '\\`').replace(/'/g, "\\'").replace(/\n/g, '\\n')}\`); this.textContent='Copied!'; setTimeout(()=>this.textContent='📋', 2000)" title="Copy Response">📋</button>
            </div>
          `;
          this._currentAssistant.querySelector('.message-time').insertAdjacentHTML('afterend', feedbackHtml);

          // TTS if enabled
          if (this.voiceOutputEnabled && window.alasVoice) {
            window.alasVoice.speak(rawContent, this.mode);
          }
        }
        if (this.onMemoryUpdate) this.onMemoryUpdate(data.memory_count || 0);
        this._scrollToBottom();
        break;

      case 'error':
        this.isStreaming = false;
        document.getElementById('typing-indicator').style.display = 'none';
        document.getElementById('stop-generation-container').style.display = 'none';
        this._showError(data.content);
        break;
    }
  }

  /**
   * Public method — safe to call from app.js and other modules.
   * Wraps the internal _addMessage so external code can render messages.
   */
  addMessage(role, content) {
    return this._addMessage(role, content, false);
  }

  stopGeneration() {
    if (!this.isStreaming) return;
    this.isStreaming = false;
    document.getElementById('typing-indicator').style.display = 'none';
    document.getElementById('stop-generation-container').style.display = 'none';
    
    // Stop REST call if any
    if (this.currentController) {
      this.currentController.abort();
      this.currentController = null;
    }
    
    // Stop WebSocket call by reconnecting
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.close();
      this.connect(); // Reconnect immediately
    }
    
    if (this._currentAssistant) {
      const cursor = this._currentAssistant.querySelector('.cursor-blink');
      if (cursor) cursor.remove();
      const textEl = this._currentAssistant.querySelector('.message-text');
      textEl.innerHTML += ' <i>[Generation stopped by user]</i>';
    }
  }

  _addMessage(role, content, isStreaming = false) {
    const container = document.getElementById('messages');
    const msg = document.createElement('div');
    msg.className = `message ${role}`;

    const avatar = role === 'assistant' ? '✦' : '🧑';
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    msg.innerHTML = `
      <div class="message-avatar">${avatar}</div>
      <div>
        <div class="message-content"><span class="message-text">${isStreaming ? '' : this._formatMarkdown(content)}</span>${isStreaming ? '<span class="cursor-blink">▊</span>' : ''}</div>
        <div class="message-time">${time}</div>
      </div>
    `;

    container.appendChild(msg);
    this._scrollToBottom();
    return msg;
  }

  _appendToken(msgEl, token) {
    const textEl = msgEl.querySelector('.message-text');
    textEl.textContent += token;
    this._scrollToBottom();
  }

  _formatMarkdown(text) {
    if (!text) return '';
    return text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
          const escapedCode = code.replace(/`/g, '\\`').replace(/'/g, "\\'").replace(/"/g, '&quot;').replace(/\n/g, '\\n');
          return `<div style="position:relative"><pre><code>${code}</code></pre><button onclick="navigator.clipboard.writeText('${escapedCode}'); this.textContent='Copied!'; setTimeout(()=>this.textContent='Copy', 2000)" style="position:absolute; top:4px; right:4px; background:rgba(255,255,255,0.1); color:var(--text-secondary); border:none; border-radius:4px; padding:2px 6px; font-size:0.7rem; cursor:pointer;">Copy</button></div>`;
      })
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');
  }

  _showError(msg) {
    const container = document.getElementById('messages');
    const el = document.createElement('div');
    el.className = 'message assistant';
    el.innerHTML = `<div class="message-avatar" style="background:var(--danger)">!</div><div><div class="message-content" style="border-color:var(--danger);color:var(--danger)">${msg}</div></div>`;
    container.appendChild(el);
    this._scrollToBottom();
  }

  _scrollToBottom() {
    const c = document.getElementById('messages-container');
    requestAnimationFrame(() => { c.scrollTop = c.scrollHeight; });
  }

  _setStatus(state, text) {
    const dot = document.querySelector('.status-dot');
    const textEl = document.getElementById('status-text');
    dot.className = `status-dot ${state}`;
    textEl.textContent = text;
    if (this.onStatusChange) this.onStatusChange(state);
  }

  newSession() {
    this.sessionId = this._generateId();
    this.history = [];
    const container = document.getElementById('messages');
    container.innerHTML = '';
    const welcome = document.getElementById('welcome-message');
    if (welcome) { welcome.style.display = 'flex'; container.appendChild(welcome); }
    document.getElementById('header-session').textContent = `Session: ${this.sessionId.slice(0, 8)}`;
    document.getElementById('stat-session').textContent = '0';
    if (window.loadChatHistory) window.loadChatHistory();
  }

  async loadHistory(sessionId) {
    this.sessionId = sessionId;
    this.history = [];
    document.getElementById('header-session').textContent = `Session: ${this.sessionId.slice(0, 8)}`;
    const container = document.getElementById('messages');
    container.innerHTML = ''; 
    const welcome = document.getElementById('welcome-message');
    if (welcome) welcome.style.display = 'none';

    try {
      const res = await fetch(`/api/memory/recent?n=200&session_id=${sessionId}`);
      if (!res.ok) return;
      const data = await res.json();
      
      if (!data.memories || data.memories.length === 0) {
        container.innerHTML = '<div style="text-align:center; margin-top:20px; color:var(--text-muted);">No history found for this session.</div>';
        return;
      }
      
      // Memories are returned sorted descending (newest first). 
      // We want to render them in chronological order (oldest first).
      const chronological = data.memories.reverse();
      
      chronological.forEach(mem => {
        const role = mem.metadata.role || 'user';
        this._addMessage(role, mem.content, false);
      });
      this._scrollToBottom();
    } catch (e) {
      console.error('Error loading history:', e);
      this._showError('Failed to load chat history.');
    }
  }

  async submitFeedback(btnEl, type, content) {
    // Visual feedback
    const container = btnEl.parentElement;
    container.innerHTML = type === 'positive' ? '<span style="color:var(--success);font-size:0.8rem">Thanks! 👍</span>' : '<span style="color:var(--danger);font-size:0.8rem">Noted 👎</span>';
    
    try {
      await fetch('/api/memory/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: this.sessionId,
          feedback_type: type,
          message_content: content
        })
      });
    } catch (e) {
      console.error('Feedback submission failed', e);
    }
  }

  _generateId() {
    return 'xxxx-xxxx'.replace(/x/g, () => Math.floor(Math.random() * 16).toString(16));
  }
}

// Cursor blink style
const style = document.createElement('style');
style.textContent = `.cursor-blink { animation: blink 0.7s infinite; color: var(--accent-primary); } @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }`;
document.head.appendChild(style);

window.alasChat = new ALASChat();
