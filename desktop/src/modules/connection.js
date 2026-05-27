/**
 * ALAS Desktop — Connection Module
 * Manages WebSocket connection to the ALAS backend.
 */
class ALASConnection {
  constructor() {
    this.ws = null;
    this.serverUrl = 'http://localhost:8000';
    this.connected = false;
    this.reconnectTimer = null;
    this.onMessage = null;
    this.onStatusChange = null;
    this.onToken = null;
    this.onDone = null;
  }

  async checkServer(url) {
    try {
      return await window.alas.checkServer(url || this.serverUrl);
    } catch {
      return { connected: false, error: 'Bridge unavailable' };
    }
  }

  connect(url) {
    if (url) this.serverUrl = url;
    const wsUrl = this.serverUrl.replace(/^http/, 'ws') + '/api/chat/ws';
    this._setStatus('connecting');

    try {
      this.ws = new WebSocket(wsUrl);
      this.ws.onopen = () => { this.connected = true; this._setStatus('online'); };
      this.ws.onclose = () => { this.connected = false; this._setStatus('offline'); this._scheduleReconnect(); };
      this.ws.onerror = () => { this.connected = false; this._setStatus('offline'); };
      this.ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.type === 'token' && this.onToken) this.onToken(data.content);
          if (data.type === 'done' && this.onDone) this.onDone(data);
          if (data.type === 'error' && this.onMessage) this.onMessage('error', data.content);
        } catch {}
      };
    } catch {
      this._setStatus('offline');
      this._scheduleReconnect();
    }
  }

  send(message, sessionId, mode, history) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return false;
    this.ws.send(JSON.stringify({ message, session_id: sessionId, mode, history }));
    return true;
  }

  disconnect() {
    clearTimeout(this.reconnectTimer);
    if (this.ws) this.ws.close();
  }

  _setStatus(status) {
    if (this.onStatusChange) this.onStatusChange(status);
  }

  _scheduleReconnect() {
    clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => this.connect(), 5000);
  }
}

window.ALASConnection = ALASConnection;
