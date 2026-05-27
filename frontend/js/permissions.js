/**
 * ALAS Permissions Panel — Frontend for the Permission Tier System.
 *
 * Features:
 *   - Summary dashboard (auto/notify/blocked/overrides counts)
 *   - Command classifier (test how any command would be treated)
 *   - Override manager (add/remove permanent rules)
 *   - Action log (live audit trail)
 */

(function () {
  const modal = document.getElementById('permissions-modal');
  const openBtn = document.getElementById('btn-view-permissions');
  const closeBtn = document.getElementById('btn-close-permissions-modal');

  // --- Open / Close ---
  openBtn?.addEventListener('click', () => {
    modal.style.display = 'flex';
    loadPermissionsData();
  });

  closeBtn?.addEventListener('click', () => {
    modal.style.display = 'none';
  });

  modal?.addEventListener('click', (e) => {
    if (e.target === modal) modal.style.display = 'none';
  });

  // --- Load all data ---
  async function loadPermissionsData() {
    await Promise.all([
      loadSummary(),
      loadOverrides(),
      loadActions(),
    ]);
  }

  // --- Summary ---
  async function loadSummary() {
    try {
      const res = await fetch('/api/permissions/summary');
      const data = await res.json();
      document.getElementById('perm-auto-count').textContent = data.auto_approved || 0;
      document.getElementById('perm-notify-count').textContent = data.notify_executed || 0;
      document.getElementById('perm-blocked-count').textContent = data.blocked || 0;
      document.getElementById('perm-overrides-count').textContent = data.user_overrides || 0;
    } catch (e) {
      console.error('Failed to load permission summary:', e);
    }
  }

  // --- Command Classifier ---
  const classifyBtn = document.getElementById('btn-classify-cmd');
  const classifyInput = document.getElementById('perm-classify-input');
  const classifyResult = document.getElementById('perm-classify-result');

  classifyBtn?.addEventListener('click', classifyCommand);
  classifyInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') classifyCommand();
  });

  async function classifyCommand() {
    const cmd = classifyInput?.value.trim();
    if (!cmd) return;

    classifyResult.style.display = 'block';
    classifyResult.innerHTML = '<span style="opacity:0.6">Classifying...</span>';

    try {
      const res = await fetch('/api/permissions/classify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd }),
      });
      const data = await res.json();

      const tierColors = {
        auto: '#22c55e',
        notify: '#eab308',
        ask: '#ef4444',
      };
      const tierLabels = {
        auto: '🟢 AUTO — Will execute silently',
        notify: '🟡 NOTIFY — Will execute with notification',
        ask: '🔴 ASK — Will be BLOCKED until you approve',
      };

      classifyResult.innerHTML = `
        <div style="display:flex;align-items:center;gap:10px;padding:10px;border-radius:8px;background:rgba(255,255,255,0.05);border-left:3px solid ${tierColors[data.tier] || '#888'};">
          <div>
            <div style="font-weight:600;color:${tierColors[data.tier] || '#888'}">${tierLabels[data.tier] || data.tier}</div>
            <div style="font-size:0.8rem;opacity:0.7;margin-top:4px;">
              <code style="color:var(--accent-primary)">${data.command}</code>
            </div>
            <div style="font-size:0.75rem;opacity:0.5;margin-top:2px;">Reason: ${data.reason || 'Pattern match'}</div>
          </div>
        </div>
      `;
    } catch (e) {
      classifyResult.innerHTML = '<span style="color:var(--danger)">Failed to classify command.</span>';
    }
  }

  // --- Overrides Manager ---
  const addOverrideBtn = document.getElementById('btn-add-override');
  addOverrideBtn?.addEventListener('click', addOverride);

  async function addOverride() {
    const pattern = document.getElementById('perm-override-pattern')?.value.trim();
    const tier = document.getElementById('perm-override-tier')?.value;

    if (!pattern) return;

    try {
      const res = await fetch('/api/permissions/overrides', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pattern, tier }),
      });
      const data = await res.json();

      if (data.status === 'success') {
        document.getElementById('perm-override-pattern').value = '';
        loadOverrides();
        loadSummary();
      }
    } catch (e) {
      console.error('Failed to add override:', e);
    }
  }

  async function loadOverrides() {
    const container = document.getElementById('perm-overrides-list');
    try {
      const res = await fetch('/api/permissions/overrides');
      const data = await res.json();
      const overrides = data.overrides || {};

      if (Object.keys(overrides).length === 0) {
        container.innerHTML = '<div class="perm-empty">No custom overrides set.</div>';
        return;
      }

      const tierIcons = { auto: '🟢', notify: '🟡', ask: '🔴' };

      container.innerHTML = Object.entries(overrides).map(([pattern, tier]) => `
        <div class="perm-override-item">
          <span class="perm-override-icon">${tierIcons[tier] || '❓'}</span>
          <code class="perm-override-pattern">${pattern}</code>
          <span class="perm-override-tier">${tier.toUpperCase()}</span>
          <button class="perm-override-remove" data-pattern="${pattern}" title="Remove override">×</button>
        </div>
      `).join('');

      // Attach remove handlers
      container.querySelectorAll('.perm-override-remove').forEach(btn => {
        btn.addEventListener('click', async () => {
          const p = btn.dataset.pattern;
          try {
            await fetch(`/api/permissions/overrides/${encodeURIComponent(p)}`, { method: 'DELETE' });
            loadOverrides();
            loadSummary();
          } catch (e) {
            console.error('Failed to remove override:', e);
          }
        });
      });
    } catch (e) {
      container.innerHTML = '<div class="perm-empty">Failed to load overrides.</div>';
    }
  }

  // --- Action Log ---
  async function loadActions() {
    const container = document.getElementById('perm-actions-list');
    try {
      const res = await fetch('/api/permissions/actions?limit=20');
      const data = await res.json();
      const actions = data.actions || [];

      if (actions.length === 0) {
        container.innerHTML = '<div class="perm-empty">No actions recorded yet. Actions appear here when ALAS uses system tools.</div>';
        return;
      }

      container.innerHTML = actions.map(a => {
        const tierIcons = { auto: '🟢', notify: '🟡', ask: '🔴' };
        const resultColors = {
          EXECUTED: '#22c55e',
          BLOCKED: '#ef4444',
          NOTIFIED: '#eab308',
        };
        const time = a.timestamp ? new Date(a.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

        return `
          <div class="perm-action-item">
            <div class="perm-action-top">
              <span>${tierIcons[a.tier] || '❓'}</span>
              <code class="perm-action-cmd">${(a.command || '').slice(0, 60)}${(a.command || '').length > 60 ? '...' : ''}</code>
              <span class="perm-action-result" style="color:${resultColors[a.result] || '#888'}">${a.result || ''}</span>
              <span class="perm-action-time">${time}</span>
            </div>
          </div>
        `;
      }).join('');
    } catch (e) {
      container.innerHTML = '<div class="perm-empty">Failed to load action history.</div>';
    }
  }
})();
