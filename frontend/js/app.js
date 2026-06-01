/**
 * ALAS App — Main application orchestrator.
 * Wires up all modules and UI event listeners.
 */

document.addEventListener('DOMContentLoaded', () => {
  const chat = window.alasChat;
  const voice = window.alasVoice;
  const memory = window.alasMemory;
  const modes = window.alasModes;
  const knowledge = new ALASKnowledge();

  // --- Connect WebSocket ---
  chat.connect();
  chat.onMemoryUpdate = (count) => {
    memory.updateCount(count);
    memory.updateSessionCount(chat.history.length);
  };

  // --- Message Input ---
  const input = document.getElementById('message-input');
  const sendBtn = document.getElementById('btn-send');
  const charCount = document.getElementById('char-count');

  input.addEventListener('input', () => {
    // Auto-resize
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 150) + 'px';
    sendBtn.disabled = !input.value.trim();
    charCount.textContent = input.value.length > 0 ? input.value.length : '';
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  sendBtn.addEventListener('click', sendMessage);

  const stopBtn = document.getElementById('btn-stop-generation');
  if (stopBtn) {
    stopBtn.addEventListener('click', () => {
      chat.stopGeneration();
    });
  }

  function sendMessage() {
    const msg = input.value.trim();
    if (!msg && !document.getElementById('file-input')?.files?.length) return;
    if (chat.isStreaming) return;

    // Check for attached file
    const fileInput = document.getElementById('file-input');
    if (fileInput && fileInput.files.length > 0) {
      const file = fileInput.files[0];
      if (file.type.startsWith('image/')) {
        sendImageMessage(msg, file);
      } else {
        sendFileMessage(msg, file);
      }
    } else if (msg) {
      chat.send(msg);
    }

    input.value = '';
    input.style.height = 'auto';
    sendBtn.disabled = true;
    charCount.textContent = '';
    clearFilePreview();
  }

  // --- File Upload (supports ALL file types) ---
  const attachBtn = document.getElementById('btn-attach-file');
  const fileInput = document.getElementById('file-input');

  // Fallback: also check old IDs for backwards compat
  const attachBtnAlt = attachBtn || document.getElementById('btn-attach-image');
  const fileInputAlt = fileInput || document.getElementById('image-input');

  attachBtnAlt?.addEventListener('click', () => fileInputAlt?.click());

  fileInputAlt?.addEventListener('change', () => {
    if (fileInputAlt.files.length > 0) {
      const file = fileInputAlt.files[0];
      attachBtnAlt.classList.add('has-image');

      // Show preview
      const preview = document.createElement('div');
      preview.className = 'image-preview';
      preview.id = 'file-preview';

      if (file.type.startsWith('image/')) {
        const img = document.createElement('img');
        img.src = URL.createObjectURL(file);
        preview.appendChild(img);
      } else {
        const icon = document.createElement('span');
        icon.textContent = '📄';
        icon.style.fontSize = '24px';
        preview.appendChild(icon);
      }

      const label = document.createElement('span');
      label.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      const removeBtn = document.createElement('button');
      removeBtn.className = 'remove-image';
      removeBtn.textContent = '×';
      removeBtn.onclick = clearFilePreview;
      preview.appendChild(label);
      preview.appendChild(removeBtn);

      // Remove any existing preview
      const existing = document.getElementById('file-preview');
      if (existing) existing.remove();
      document.querySelector('.input-area').appendChild(preview);

      // Enable send button when file is attached
      sendBtn.disabled = false;
    }
  });

  function clearFilePreview() {
    const preview = document.getElementById('file-preview');
    if (preview) preview.remove();
    if (fileInputAlt) fileInputAlt.value = '';
    attachBtnAlt?.classList.remove('has-image');
  }

  async function sendImageMessage(prompt, file) {
    // Show user message with image indicator
    const welcome = document.getElementById('welcome-message');
    if (welcome) welcome.style.display = 'none';

    chat.addMessage('user', `📷 [Image: ${file.name}] ${prompt || 'Describe this image'}`);

    // Show typing indicator
    chat.isStreaming = true;
    document.getElementById('typing-indicator').style.display = 'flex';

    const formData = new FormData();
    formData.append('image', file);
    if (prompt) formData.append('prompt', prompt);
    formData.append('task', 'describe');

    try {
      const res = await fetch('/api/chat/vision', { method: 'POST', body: formData });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();

      chat.isStreaming = false;
      document.getElementById('typing-indicator').style.display = 'none';

      if (data.status === 'success' && data.description) {
        chat.addMessage('assistant', data.description);
      } else if (data.status === 'unavailable') {
        chat.addMessage('assistant', `⚠️ Vision model not available. ${data.error || 'Install a vision model with: ollama pull llava'}`);
      } else {
        chat.addMessage('assistant', `⚠️ ${data.error || 'Vision analysis returned no result. Make sure a vision model (llava/moondream) is installed.'}`);
      }
    } catch (err) {
      chat.isStreaming = false;
      document.getElementById('typing-indicator').style.display = 'none';
      chat.addMessage('assistant', `❌ Image analysis failed: ${err.message}`);
    }
  }

  async function sendFileMessage(prompt, file) {
    /**
     * Handle non-image file uploads.
     * Reads the file content and sends it to the chat as context.
     */
    const welcome = document.getElementById('welcome-message');
    if (welcome) welcome.style.display = 'none';

    // Check file size (max 100KB for text injection)
    if (file.size > 100 * 1024) {
      chat.addMessage('user', `📄 [File: ${file.name}] ${prompt || 'Analyze this file'}`);
      chat.addMessage('assistant', `⚠️ File is too large (${(file.size / 1024).toFixed(1)} KB). Maximum size for inline analysis is 100KB. Try uploading a smaller file or copy-paste the relevant section.`);
      return;
    }

    try {
      const fileContent = await file.text();
      const fileMsg = prompt
        ? `📄 [File: ${file.name}] ${prompt}`
        : `📄 [File: ${file.name}] Please analyze this file.`;

      // Build a message that includes the file content
      const fullMessage = `${prompt || 'Please analyze this file.'}\n\n--- File: ${file.name} ---\n\`\`\`\n${fileContent}\n\`\`\`\n--- End of File ---`;

      chat.addMessage('user', fileMsg);
      chat.send(fullMessage);
    } catch (err) {
      chat.addMessage('user', `📄 [File: ${file.name}]`);
      chat.addMessage('assistant', `❌ Could not read file: ${err.message}. This file type may not be supported for direct reading.`);
    }
  }

  // --- Voice ---
  document.getElementById('btn-voice-input').addEventListener('click', () => {
    voice.toggleRecording();
  });

  document.getElementById('btn-voice-toggle').addEventListener('click', function() {
    chat.voiceOutputEnabled = !chat.voiceOutputEnabled;
    this.classList.toggle('active', chat.voiceOutputEnabled);
  });

  // --- Mode Switching ---
  document.querySelectorAll('.mode-btn').forEach(btn => {
    if (btn.dataset.mode) {
      btn.addEventListener('click', () => modes.setMode(btn.dataset.mode));
    }
  });

  // --- Sidebar Navigation ---
  const settingsModal = document.getElementById('settings-modal');
  const openSettings = async () => {
    settingsModal.style.display = 'flex';
    
    // Load Profile
    try {
      const res = await fetch('/api/profile/default');
      if (res.ok) {
        const p = await res.json();
        document.getElementById('profile-input-name').value = p.name || '';
        document.getElementById('profile-input-preferred').value = p.preferred_name || '';
        document.getElementById('profile-input-style').value = p.communication_style || 'balanced';
        document.getElementById('profile-input-topics').value = (p.topics_of_interest || []).join(', ');
      }
    } catch (e) {}

    // Load IDE Settings
    const ideSettings = JSON.parse(localStorage.getItem('alas_ide_settings')) || { theme: 'vs-dark', fontSize: 14, wordWrap: 'off' };
    document.getElementById('ide-input-theme').value = ideSettings.theme;
    document.getElementById('ide-input-fontsize').value = ideSettings.fontSize;
    document.getElementById('ide-input-wordwrap').value = ideSettings.wordWrap;
  };

  const btnSettings = document.getElementById('btn-nav-settings');
  const btnFeedback = document.getElementById('btn-nav-feedback');
  const btnHelp = document.getElementById('btn-nav-help');

  if (btnSettings) btnSettings.addEventListener('click', openSettings);
  if (btnFeedback) btnFeedback.addEventListener('click', openSettings);
  if (btnHelp) btnHelp.addEventListener('click', () => {
      chat.addMessage('assistant', 'Here are some tips:\\n- **Settings**: Click the Settings button to configure your profile.\\n- **Modes**: Switch modes (Work, Casual, etc) to change how I respond.\\n- **Voice**: Click the microphone icon to speak to me!\\n- **Uploads**: Use the paperclip to upload code or text files for me to read.');
      if (window.innerWidth <= 768) {
          document.getElementById('sidebar').classList.remove('open');
      }
  });

  // --- Sidebar Toggle ---
  document.getElementById('btn-sidebar-toggle').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('collapsed');
    document.getElementById('sidebar').classList.toggle('open');
  });

  // --- New Session ---
  document.getElementById('btn-new-session').addEventListener('click', () => chat.newSession());

  // --- Memory Search Modal ---
  const memModal = document.getElementById('memory-search-modal');
  document.getElementById('btn-search-memory').addEventListener('click', () => {
    memModal.style.display = 'flex';
    document.getElementById('memory-search-input').focus();
  });
  document.getElementById('btn-close-memory-modal').addEventListener('click', () => {
    memModal.style.display = 'none';
  });

  let searchTimeout;
  document.getElementById('memory-search-input').addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
      const q = e.target.value.trim();
      if (q.length < 2) return;
      const results = await memory.search(q);
      memory.renderSearchResults(results);
    }, 400);
  });

  // --- Unified Settings Modal ---
  const btnSettingsNav = document.getElementById('btn-nav-settings');
  if (btnSettingsNav) btnSettingsNav.addEventListener('click', openSettings);
  
  const btnEditProfile = document.getElementById('btn-edit-profile');
  if (btnEditProfile) btnEditProfile.addEventListener('click', openSettings);

  document.getElementById('btn-close-settings-modal').addEventListener('click', () => {
    settingsModal.style.display = 'none';
  });

  // Settings Tabs Logic
  document.querySelectorAll('.settings-tab').forEach(tab => {
      tab.addEventListener('click', () => {
          document.querySelectorAll('.settings-tab').forEach(t => {
              t.classList.remove('active');
              t.style.borderLeftColor = 'transparent';
              t.style.color = 'var(--text-secondary)';
          });
          document.querySelectorAll('.settings-pane').forEach(p => p.style.display = 'none');
          
          tab.classList.add('active');
          tab.style.borderLeftColor = 'var(--accent-primary)';
          tab.style.color = 'var(--text-primary)';
          document.getElementById('pane-' + tab.dataset.tab).style.display = 'block';
      });
  });

  document.getElementById('btn-save-settings').addEventListener('click', async () => {
    const btn = document.getElementById('btn-save-settings');
    const oldText = btn.textContent;
    btn.textContent = "Saving...";
    btn.disabled = true;

    try {
        // Save Profile
        const profileData = {
          name: document.getElementById('profile-input-name').value || null,
          preferred_name: document.getElementById('profile-input-preferred').value || null,
          communication_style: document.getElementById('profile-input-style').value,
          topics_of_interest: document.getElementById('profile-input-topics').value
            .split(',').map(t => t.trim()).filter(Boolean),
        };
        
        await fetch('/api/profile/default', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(profileData),
        });
        loadProfile();

        // Save IDE Settings
        const ideSettings = {
            theme: document.getElementById('ide-input-theme').value,
            fontSize: parseInt(document.getElementById('ide-input-fontsize').value, 10) || 14,
            wordWrap: document.getElementById('ide-input-wordwrap').value
        };
        localStorage.setItem('alas_ide_settings', JSON.stringify(ideSettings));
        
        // Broadcast IDE event for Monaco
        window.dispatchEvent(new CustomEvent('alas_ide_settings_updated', { detail: ideSettings }));

        btn.textContent = "Saved!";
        setTimeout(() => {
            btn.textContent = oldText;
            btn.disabled = false;
            settingsModal.style.display = 'none';
        }, 800);

    } catch (e) {
        console.error("Failed to save settings:", e);
        btn.textContent = "Error Saving";
        setTimeout(() => {
            btn.textContent = oldText;
            btn.disabled = false;
        }, 2000);
    }
  });

  // Close modals on overlay click
  [memModal, settingsModal].forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.style.display = 'none';
    });
  });

  // --- Load initial data ---
  async function loadProfile() {
    try {
      const res = await fetch('/api/profile/default');
      if (!res.ok) return;
      const p = await res.json();
      const name = p.preferred_name || p.name || 'New User';
      document.getElementById('profile-name').textContent = name;
      document.getElementById('profile-style').textContent = p.communication_style || 'balanced';
      
      const savedAvatar = localStorage.getItem('alas_custom_avatar');
      document.getElementById('profile-avatar').querySelector('span').textContent = savedAvatar || name[0]?.toUpperCase() || '?';
      
      document.getElementById('stat-interactions').textContent = p.interaction_count || 0;
    } catch (e) {}
  }

  // --- Custom Avatar ---
  document.getElementById('profile-avatar').addEventListener('click', () => {
    const current = document.getElementById('profile-avatar').querySelector('span').textContent;
    const newAvatar = prompt("Enter a custom emoji or initial for your avatar:", current);
    if (newAvatar) {
        localStorage.setItem('alas_custom_avatar', newAvatar);
        document.getElementById('profile-avatar').querySelector('span').textContent = newAvatar;
    }
  });

  loadProfile();
  memory.fetchStats();
  knowledge.updateStats();
  document.getElementById('header-session').textContent = `Session: ${chat.sessionId.slice(0, 8)}`;
  
  // Load sidebar chat history
  async function loadChatHistory() {
    try {
      const res = await fetch('/api/memory/sessions');
      if (!res.ok) return;
      const data = await res.json();
      
      const historyList = document.getElementById('chat-history-list');
      if (!historyList) return;
      
      historyList.innerHTML = '';
      if (!data.sessions || data.sessions.length === 0) {
        historyList.innerHTML = '<span style="color: var(--text-muted); font-size: 12px; padding: 8px;">No past chats found.</span>';
        return;
      }
      
      data.sessions.forEach(session => {
        const btn = document.createElement('button');
        btn.className = 'mode-btn';
        btn.title = new Date(session.latest_timestamp).toLocaleString();
        btn.style.width = '100%';
        btn.style.justifyContent = 'flex-start';
        
        const icon = document.createElement('span');
        icon.className = 'mode-icon';
        icon.textContent = '💬';
        
        const label = document.createElement('span');
        label.className = 'mode-label';
        label.textContent = session.title;
        label.style.whiteSpace = 'nowrap';
        label.style.overflow = 'hidden';
        label.style.textOverflow = 'ellipsis';
        
        btn.appendChild(icon);
        btn.appendChild(label);
        
        btn.addEventListener('click', () => {
          chat.loadHistory(session.session_id);
          // Highlight active
          Array.from(historyList.children).forEach(c => c.classList.remove('active'));
          btn.classList.add('active');
        });
        
        historyList.appendChild(btn);
      });
    } catch (e) {
      console.error('Failed to load chat history', e);
    }
  }
  
  loadChatHistory();
  window.loadChatHistory = loadChatHistory; // expose globally to update it on new session
});
