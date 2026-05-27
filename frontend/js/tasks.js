/**
 * ALAS Tasks & Reminders Panel.
 */

(function () {
  const modal = document.getElementById('tasks-modal');
  const openBtn = document.getElementById('btn-view-tasks');
  const closeBtn = document.getElementById('btn-close-tasks-modal');

  // --- Open / Close ---
  openBtn?.addEventListener('click', () => {
    modal.style.display = 'flex';
    loadTasks();
  });

  closeBtn?.addEventListener('click', () => {
    modal.style.display = 'none';
  });

  modal?.addEventListener('click', (e) => {
    if (e.target === modal) modal.style.display = 'none';
  });

  async function loadTasks() {
    const container = document.getElementById('tasks-list');
    try {
      const res = await fetch('/api/tasks');
      const data = await res.json();
      const tasks = data.tasks || [];

      if (tasks.length === 0) {
        container.innerHTML = '<div class="perm-empty">No active tasks or reminders. Ask ALAS to set a reminder!</div>';
        return;
      }

      container.innerHTML = tasks.map(t => {
        let title = '';
        let subtitle = '';
        let icon = '⏰';

        if (t.type === 'reminder') {
          title = `Reminder: ${t.message}`;
          const date = new Date(t.run_at);
          subtitle = `Runs at: ${date.toLocaleString()}`;
          icon = '🔔';
        } else if (t.type === 'recurring') {
          title = `Recurring: ${t.name}`;
          if (t.interval_minutes) {
              subtitle = `Every ${t.interval_minutes} minutes`;
          } else if (t.cron) {
              subtitle = `Cron: ${t.cron}`;
          }
          icon = '🔄';
        }

        return `
          <div class="perm-override-item">
            <span class="perm-override-icon">${icon}</span>
            <div style="flex: 1;">
              <div class="perm-override-pattern" style="font-size: 0.85rem; margin-bottom: 2px">${title}</div>
              <div class="perm-override-tier" style="font-size: 0.7rem; font-weight: normal">${subtitle}</div>
            </div>
            <span class="perm-override-tier" style="margin-right: 10px; color: var(--success)">${t.status.toUpperCase()}</span>
            <button class="perm-override-remove" data-id="${t.id}" title="Cancel Task">×</button>
          </div>
        `;
      }).join('');

      // Attach cancel handlers
      container.querySelectorAll('.perm-override-remove').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = btn.dataset.id;
          try {
            await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
            loadTasks(); // reload
          } catch (e) {
            console.error('Failed to cancel task:', e);
          }
        });
      });
    } catch (e) {
      container.innerHTML = '<div class="perm-empty">Failed to load scheduled tasks.</div>';
    }
  }
})();
