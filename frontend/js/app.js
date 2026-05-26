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

  function sendMessage() {
    const msg = input.value.trim();
    if (!msg || chat.isStreaming) return;

    // Check for attached image
    const imageInput = document.getElementById('image-input');
    if (imageInput.files.length > 0) {
      sendImageMessage(msg, imageInput.files[0]);
    } else {
      chat.send(msg);
    }

    input.value = '';
    input.style.height = 'auto';
    sendBtn.disabled = true;
    charCount.textContent = '';
    clearImagePreview();
  }

  // --- Image Upload ---
  const attachBtn = document.getElementById('btn-attach-image');
  const imageInput = document.getElementById('image-input');

  attachBtn?.addEventListener('click', () => imageInput?.click());

  imageInput?.addEventListener('change', () => {
    if (imageInput.files.length > 0) {
      const file = imageInput.files[0];
      attachBtn.classList.add('has-image');

      // Show preview
      const preview = document.createElement('div');
      preview.className = 'image-preview';
      preview.id = 'image-preview';
      const img = document.createElement('img');
      img.src = URL.createObjectURL(file);
      const label = document.createElement('span');
      label.textContent = file.name;
      const removeBtn = document.createElement('button');
      removeBtn.className = 'remove-image';
      removeBtn.textContent = '×';
      removeBtn.onclick = clearImagePreview;
      preview.appendChild(img);
      preview.appendChild(label);
      preview.appendChild(removeBtn);

      const existing = document.getElementById('image-preview');
      if (existing) existing.remove();
      document.querySelector('.input-area').appendChild(preview);
    }
  });

  function clearImagePreview() {
    const preview = document.getElementById('image-preview');
    if (preview) preview.remove();
    const imageInput = document.getElementById('image-input');
    if (imageInput) imageInput.value = '';
    attachBtn?.classList.remove('has-image');
  }

  async function sendImageMessage(prompt, file) {
    // Show user message with image indicator
    chat.addMessage('user', `📷 [Image: ${file.name}] ${prompt || 'Describe this image'}`);

    const formData = new FormData();
    formData.append('image', file);
    if (prompt) formData.append('prompt', prompt);
    formData.append('task', 'describe');

    try {
      const res = await fetch('/api/chat/vision', { method: 'POST', body: formData });
      const data = await res.json();

      if (data.status === 'success') {
        chat.addMessage('assistant', data.description);
      } else {
        chat.addMessage('assistant', `⚠️ ${data.error || 'Vision analysis unavailable'}`);
      }
    } catch (err) {
      chat.addMessage('assistant', `❌ Image analysis failed: ${err.message}`);
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
    btn.addEventListener('click', () => modes.setMode(btn.dataset.mode));
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

  // --- Profile Modal ---
  const profModal = document.getElementById('profile-edit-modal');
  document.getElementById('btn-edit-profile').addEventListener('click', async () => {
    profModal.style.display = 'flex';
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
  });
  document.getElementById('btn-close-profile-modal').addEventListener('click', () => {
    profModal.style.display = 'none';
  });

  document.getElementById('btn-save-profile').addEventListener('click', async () => {
    const data = {
      name: document.getElementById('profile-input-name').value || null,
      preferred_name: document.getElementById('profile-input-preferred').value || null,
      communication_style: document.getElementById('profile-input-style').value,
      topics_of_interest: document.getElementById('profile-input-topics').value
        .split(',').map(t => t.trim()).filter(Boolean),
    };
    try {
      await fetch('/api/profile/default', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      profModal.style.display = 'none';
      loadProfile();
    } catch (e) {}
  });

  // Close modals on overlay click
  [memModal, profModal].forEach(modal => {
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
      document.getElementById('profile-avatar').querySelector('span').textContent = name[0]?.toUpperCase() || '?';
      document.getElementById('stat-interactions').textContent = p.interaction_count || 0;
    } catch (e) {}
  }

  loadProfile();
  memory.fetchStats();
  knowledge.updateStats();
  document.getElementById('header-session').textContent = `Session: ${chat.sessionId.slice(0, 8)}`;
});
