/**
 * ALAS Desktop — Chat Module
 * Handles message rendering with markdown support.
 */
class ALASChat {
  constructor(container) {
    this.container = container;
    this.history = [];
    this.sessionId = crypto.randomUUID();
  }

  addMessage(role, content) {
    const welcome = document.getElementById('welcome-msg');
    if (welcome) welcome.style.display = 'none';
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerHTML = this._render(content);
    this.container.appendChild(div);
    this.container.scrollTop = this.container.scrollHeight;
    this.history.push({ role, content });
    return div;
  }

  createStreamMessage() {
    const welcome = document.getElementById('welcome-msg');
    if (welcome) welcome.style.display = 'none';
    const div = document.createElement('div');
    div.className = 'message assistant';
    this.container.appendChild(div);
    this.container.scrollTop = this.container.scrollHeight;
    return div;
  }

  appendToStream(el, token) {
    el._rawContent = (el._rawContent || '') + token;
    el.innerHTML = this._render(el._rawContent);
    this.container.scrollTop = this.container.scrollHeight;
  }

  finalizeStream(el) {
    const content = el._rawContent || el.textContent;
    this.history.push({ role: 'assistant', content });
  }

  getRecentHistory(n = 10) {
    return this.history.slice(-n);
  }

  _render(text) {
    if (!text) return '';
    let html = text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => `<pre><code>${code.trim()}</code></pre>`)
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');
    return html;
  }
}

window.ALASChat = ALASChat;
