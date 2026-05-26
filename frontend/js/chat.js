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
  }

  connect() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${location.host}/api/chat/ws`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this._setStatus('connected', 'Connected');
    };

    this.ws.onclose = () => {
      this._setStatus('disconnected', 'Disconnected');
      setTimeout(() => this.connect(), 3000);
    };

    this.ws.onerror = () => {
      this._setStatus('error', 'Connection error');
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this._handleMessage(data);
    };
  }

  send(message) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this._showError('Not connected to ALAS. Reconnecting...');
      this.connect();
      return;
    }
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

    // Create assistant message placeholder
    this._currentAssistant = this._addMessage('assistant', '', true);

    // Send via WebSocket
    this.ws.send(JSON.stringify({
      message,
      session_id: this.sessionId,
      mode: this.mode,
      user_id: this.userId,
      history: this.history.slice(-10),
    }));
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
        if (this._currentAssistant) {
          const cursor = this._currentAssistant.querySelector('.cursor-blink');
          if (cursor) cursor.remove();
          
          // Render markdown properly after completion
          const textEl = this._currentAssistant.querySelector('.message-text');
          const rawContent = textEl.textContent;
          textEl.innerHTML = this._formatMarkdown(rawContent);
          
          this.history.push({ role: 'assistant', content: rawContent });

          // Add feedback buttons
          const feedbackHtml = `
            <div class="message-feedback">
              <button class="feedback-btn" onclick="window.alasChat.submitFeedback(this, 'positive', \`${rawContent.replace(/`/g, '\\`').replace(/'/g, "\\'")}\`)">👍</button>
              <button class="feedback-btn" onclick="window.alasChat.submitFeedback(this, 'negative', \`${rawContent.replace(/`/g, '\\`').replace(/'/g, "\\'")}\`)">👎</button>
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
        this._showError(data.content);
        break;
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
      .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
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
