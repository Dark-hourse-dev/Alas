/**
 * ALAS Desktop — Preload Script (Security Bridge)
 *
 * Exposes a minimal, safe API to the renderer process.
 * Context isolation is ON — no direct Node.js access from the UI.
 * Only whitelisted operations are exposed via contextBridge.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('alas', {
  // ── Config ──
  getConfig: () => ipcRenderer.invoke('get-config'),
  setConfig: (updates) => ipcRenderer.invoke('set-config', updates),
  setServerUrl: (url) => ipcRenderer.invoke('set-server-url', url),

  // ── Security ──
  getApiToken: () => ipcRenderer.invoke('get-api-token'),
  regenerateToken: () => ipcRenderer.invoke('regenerate-token'),

  // ── Server ──
  checkServer: (url) => ipcRenderer.invoke('check-server', url),

  // ── Window Controls ──
  minimize: () => ipcRenderer.invoke('window-minimize'),
  maximize: () => ipcRenderer.invoke('window-maximize'),
  close: () => ipcRenderer.invoke('window-close'),

  // ── Notifications ──
  notify: (title, body) => ipcRenderer.invoke('show-notification', { title, body }),

  // ── Navigation Events ──
  onNavigate: (callback) => {
    ipcRenderer.on('navigate', (_, page) => callback(page));
  },

  // ── Platform Info ──
  platform: process.platform,
  version: '0.5.0',
});
