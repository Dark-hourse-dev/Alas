/**
 * ALAS Memory Module — Memory panel and search UI.
 */

class ALASMemory {
  constructor() {
    this.totalMemories = 0;
  }

  async fetchStats() {
    try {
      const res = await fetch('/api/memory/stats');
      if (!res.ok) return;
      const data = await res.json();
      this.totalMemories = data.episodic?.total_memories || 0;
      document.getElementById('stat-episodic').textContent = this.totalMemories;
      document.getElementById('memory-count').textContent = this.totalMemories;
    } catch (e) {}
  }

  async search(query) {
    try {
      const res = await fetch('/api/memory/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, n_results: 10 }),
      });
      if (!res.ok) return [];
      const data = await res.json();
      return data.memories || [];
    } catch (e) { return []; }
  }

  renderSearchResults(memories) {
    const container = document.getElementById('memory-results');
    if (!memories.length) {
      container.innerHTML = '<div class="memory-result-item" style="text-align:center;color:var(--text-muted)">No memories found</div>';
      return;
    }
    container.innerHTML = memories.map(m => `
      <div class="memory-result-item">
        <div class="mem-role">${m.metadata?.role || 'unknown'}</div>
        <div>${(m.content || '').slice(0, 200)}${m.content?.length > 200 ? '...' : ''}</div>
        <div class="mem-time">${m.metadata?.timestamp ? new Date(m.metadata.timestamp).toLocaleString() : ''}</div>
      </div>
    `).join('');
  }

  updateCount(count) {
    this.totalMemories = count;
    document.getElementById('stat-episodic').textContent = count;
    document.getElementById('memory-count').textContent = count;
  }

  updateSessionCount(count) {
    document.getElementById('stat-session').textContent = count;
  }
}

window.alasMemory = new ALASMemory();
