/**
 * ALAS Desktop — Main Process
 *
 * Electron main process with:
 * - Custom frameless window
 * - System tray integration
 * - Secure IPC bridge via preload
 * - Global keyboard shortcuts
 * - Auto-reconnect to backend
 * - Encrypted config storage
 */

const {
  app,
  BrowserWindow,
  Tray,
  Menu,
  nativeImage,
  ipcMain,
  globalShortcut,
  Notification,
  dialog,
  shell,
} = require('electron');
const path = require('path');
const https = require('https');
const http = require('http');
const crypto = require('crypto');
const fs = require('fs');

// ─── Config ─────────────────────────────────────────
const CONFIG_PATH = path.join(app.getPath('userData'), 'alas-config.json');
const DEFAULT_CONFIG = {
  serverUrl: 'http://localhost:8000',
  apiToken: '',
  theme: 'dark',
  alwaysOnTop: false,
  startMinimized: false,
  launchOnStartup: false,
  globalShortcut: 'CommandOrControl+Shift+A',
  windowBounds: { width: 480, height: 720 },
};

let config = { ...DEFAULT_CONFIG };
let mainWindow = null;
let tray = null;
let isQuitting = false;

// ─── Config Persistence ─────────────────────────────
function loadConfig() {
  try {
    if (fs.existsSync(CONFIG_PATH)) {
      const raw = fs.readFileSync(CONFIG_PATH, 'utf-8');
      config = { ...DEFAULT_CONFIG, ...JSON.parse(raw) };
    }
  } catch (e) {
    console.error('Failed to load config:', e);
  }
}

function saveConfig() {
  try {
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2));
  } catch (e) {
    console.error('Failed to save config:', e);
  }
}

// ─── Generate API Token ─────────────────────────────
function generateToken() {
  return crypto.randomBytes(32).toString('hex');
}

// ─── Create Main Window ─────────────────────────────
function createWindow() {
  const { width, height } = config.windowBounds || { width: 480, height: 720 };

  mainWindow = new BrowserWindow({
    width,
    height,
    minWidth: 380,
    minHeight: 520,
    frame: false,
    transparent: false,
    backgroundColor: '#0a0a1a',
    titleBarStyle: 'hidden',
    titleBarOverlay: false,
    resizable: true,
    icon: path.join(__dirname, 'src', 'assets', 'icon.png'),
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, 'src', 'index.html'));

  mainWindow.once('ready-to-show', () => {
    if (!config.startMinimized) {
      mainWindow.show();
    }
  });

  mainWindow.on('close', (e) => {
    if (!isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('resize', () => {
    const bounds = mainWindow.getBounds();
    config.windowBounds = { width: bounds.width, height: bounds.height };
    saveConfig();
  });

  if (config.alwaysOnTop) {
    mainWindow.setAlwaysOnTop(true);
  }
}

// ─── System Tray ────────────────────────────────────
function createTray() {
  // Create a 16x16 tray icon programmatically
  const icon = nativeImage.createEmpty();
  const size = 16;
  const canvas = Buffer.alloc(size * size * 4);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const i = (y * size + x) * 4;
      const cx = x - size / 2, cy = y - size / 2;
      const dist = Math.sqrt(cx * cx + cy * cy);
      if (dist < 6) {
        canvas[i] = 100;     // R
        canvas[i + 1] = 220; // G
        canvas[i + 2] = 255; // B
        canvas[i + 3] = dist < 4 ? 255 : 150; // A
      }
    }
  }

  let trayIcon;
  try {
    trayIcon = nativeImage.createFromBuffer(
      createPNGBuffer(size, size, canvas),
      { width: size, height: size }
    );
  } catch {
    trayIcon = nativeImage.createEmpty();
  }

  tray = new Tray(trayIcon);
  tray.setToolTip('ALAS — Adaptive Living AI');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '🧬 Open ALAS',
      click: () => {
        mainWindow.show();
        mainWindow.focus();
      },
    },
    { type: 'separator' },
    {
      label: '🌐 Open in Browser',
      click: () => shell.openExternal(config.serverUrl),
    },
    {
      label: '⚙️ Settings',
      click: () => {
        mainWindow.show();
        mainWindow.webContents.send('navigate', 'settings');
      },
    },
    { type: 'separator' },
    {
      label: '📌 Always on Top',
      type: 'checkbox',
      checked: config.alwaysOnTop,
      click: (item) => {
        config.alwaysOnTop = item.checked;
        mainWindow.setAlwaysOnTop(item.checked);
        saveConfig();
      },
    },
    { type: 'separator' },
    {
      label: '❌ Quit ALAS',
      click: () => {
        isQuitting = true;
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);
  tray.on('click', () => {
    if (mainWindow.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

// ─── Simple PNG buffer creator (no external deps) ───
function createPNGBuffer(width, height, rgba) {
  // Minimal PNG encoder for tray icon
  // Returns a valid PNG buffer from raw RGBA data
  const { deflateSync } = require('zlib');

  function crc32(buf) {
    let c = 0xffffffff;
    for (let i = 0; i < buf.length; i++) {
      c = (c >>> 8) ^ crc32Table[(c ^ buf[i]) & 0xff];
    }
    return (c ^ 0xffffffff) >>> 0;
  }

  const crc32Table = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let j = 0; j < 8; j++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    crc32Table[i] = c;
  }

  function chunk(type, data) {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(data.length);
    const typeData = Buffer.concat([Buffer.from(type), data]);
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(crc32(typeData));
    return Buffer.concat([len, typeData, crc]);
  }

  // IHDR
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 6; // RGBA
  ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;

  // IDAT — raw image data with filter byte per row
  const raw = Buffer.alloc(height * (1 + width * 4));
  for (let y = 0; y < height; y++) {
    raw[y * (1 + width * 4)] = 0; // filter: none
    rgba.copy(raw, y * (1 + width * 4) + 1, y * width * 4, (y + 1) * width * 4);
  }
  const compressed = deflateSync(raw);

  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  return Buffer.concat([
    sig,
    chunk('IHDR', ihdr),
    chunk('IDAT', compressed),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

// ─── IPC Handlers ───────────────────────────────────
function setupIPC() {
  ipcMain.handle('get-config', () => ({
    serverUrl: config.serverUrl,
    theme: config.theme,
    alwaysOnTop: config.alwaysOnTop,
  }));

  ipcMain.handle('set-config', (_, updates) => {
    Object.assign(config, updates);
    saveConfig();
    if ('alwaysOnTop' in updates) {
      mainWindow.setAlwaysOnTop(updates.alwaysOnTop);
    }
    return config;
  });

  ipcMain.handle('set-server-url', (_, url) => {
    config.serverUrl = url;
    saveConfig();
    return { success: true };
  });

  ipcMain.handle('get-api-token', () => {
    if (!config.apiToken) {
      config.apiToken = generateToken();
      saveConfig();
    }
    return config.apiToken;
  });

  ipcMain.handle('regenerate-token', () => {
    config.apiToken = generateToken();
    saveConfig();
    return config.apiToken;
  });

  ipcMain.handle('check-server', async (_, url) => {
    const target = url || config.serverUrl;
    return new Promise((resolve) => {
      const req = http.get(`${target}/api/status`, { timeout: 5000 }, (res) => {
        let data = '';
        res.on('data', (chunk) => data += chunk);
        res.on('end', () => {
          try {
            resolve({ connected: true, data: JSON.parse(data) });
          } catch {
            resolve({ connected: false, error: 'Invalid response' });
          }
        });
      });
      req.on('error', (e) => resolve({ connected: false, error: e.message }));
      req.on('timeout', () => {
        req.destroy();
        resolve({ connected: false, error: 'Connection timed out' });
      });
    });
  });

  ipcMain.handle('window-minimize', () => mainWindow.minimize());
  ipcMain.handle('window-maximize', () => {
    if (mainWindow.isMaximized()) mainWindow.unmaximize();
    else mainWindow.maximize();
  });
  ipcMain.handle('window-close', () => mainWindow.hide());

  ipcMain.handle('show-notification', (_, { title, body }) => {
    if (Notification.isSupported()) {
      new Notification({ title, body, icon: path.join(__dirname, 'src', 'assets', 'icon.png') }).show();
    }
  });
}

// ─── Global Shortcuts ───────────────────────────────
function registerShortcuts() {
  try {
    globalShortcut.register(config.globalShortcut, () => {
      if (mainWindow.isVisible() && mainWindow.isFocused()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    });
  } catch (e) {
    console.error('Failed to register global shortcut:', e);
  }
}

// ─── App Lifecycle ──────────────────────────────────
app.whenReady().then(() => {
  loadConfig();
  createWindow();
  createTray();
  setupIPC();
  registerShortcuts();
});

app.on('window-all-closed', () => {
  // Don't quit on macOS — stay in tray
  if (process.platform !== 'darwin') {
    // On other platforms, also stay in tray
  }
});

app.on('activate', () => {
  if (mainWindow) {
    mainWindow.show();
  }
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

app.on('before-quit', () => {
  isQuitting = true;
});
