/**
 * ALAS Desktop — Security Module
 * Manages API tokens and secure communication.
 */
class ALASSecurity {
  constructor() {
    this.token = null;
  }

  async init() {
    this.token = await window.alas.getApiToken();
  }

  async regenerate() {
    this.token = await window.alas.regenerateToken();
    return this.token;
  }

  getHeaders() {
    return this.token ? { 'Authorization': `Bearer ${this.token}` } : {};
  }

  async fetchSecure(url, options = {}) {
    const headers = { ...this.getHeaders(), ...(options.headers || {}) };
    return fetch(url, { ...options, headers });
  }
}

window.ALASSecurity = ALASSecurity;
