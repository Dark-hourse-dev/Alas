/**
 * ALAS Knowledge Graph Module — Interactive graph visualization with canvas rendering.
 */

class ALASKnowledge {
    constructor() {
        this.modal = document.getElementById('knowledge-graph-modal');
        this.canvas = document.getElementById('kg-canvas');
        this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
        this.entityList = document.getElementById('kg-entity-list');
        this.statsEl = document.getElementById('kg-stats');
        this.searchInput = document.getElementById('kg-search-input');
        this.nodes = [];
        this.edges = [];
        this.animFrame = null;

        // Entity type colors
        this.typeColors = {
            person: '#6366f1',
            concept: '#06b6d4',
            topic: '#8b5cf6',
            skill: '#10b981',
            goal: '#f59e0b',
            event: '#ef4444',
            place: '#ec4899',
            preference: '#14b8a6',
        };

        this._bindEvents();
    }

    _bindEvents() {
        document.getElementById('btn-view-knowledge')?.addEventListener('click', () => this.open());
        document.getElementById('btn-close-kg-modal')?.addEventListener('click', () => this.close());
        document.getElementById('btn-consolidate')?.addEventListener('click', () => this.consolidate());

        this.modal?.addEventListener('click', (e) => {
            if (e.target === this.modal) this.close();
        });

        this.searchInput?.addEventListener('input', (e) => {
            this._filterEntities(e.target.value);
        });
    }

    async open() {
        this.modal.style.display = 'flex';
        await this.loadGraph();
    }

    close() {
        this.modal.style.display = 'none';
        if (this.animFrame) {
            cancelAnimationFrame(this.animFrame);
            this.animFrame = null;
        }
    }

    async loadGraph() {
        try {
            const res = await fetch('/api/knowledge/graph');
            const data = await res.json();

            this.nodes = data.nodes || [];
            this.edges = data.edges || [];

            this._renderStats(data.stats || {});
            this._renderEntityList(this.nodes);
            this._renderCanvas();

            // Update sidebar stat
            const kgEl = document.getElementById('stat-kg-entities');
            if (kgEl) kgEl.textContent = this.nodes.length;

        } catch (err) {
            console.error('Failed to load knowledge graph:', err);
        }
    }

    async consolidate() {
        const btn = document.getElementById('btn-consolidate');
        if (btn) {
            btn.disabled = true;
            btn.textContent = '⏳ Processing...';
        }

        try {
            const res = await fetch('/api/knowledge/consolidate', { method: 'POST' });
            const data = await res.json();

            const msg = `Extracted ${data.entities_extracted} entities and ${data.relationships_extracted} relationships from ${data.processed} conversations.`;

            if (btn) btn.textContent = '✅ Done!';
            setTimeout(() => { if (btn) { btn.textContent = '🌙 Consolidate'; btn.disabled = false; } }, 2000);

            // Refresh graph if modal is open
            if (this.modal.style.display !== 'none') {
                await this.loadGraph();
            }

            // Update memory stats
            this.updateStats();

        } catch (err) {
            console.error('Consolidation failed:', err);
            if (btn) { btn.textContent = '❌ Failed'; btn.disabled = false; }
        }
    }

    async updateStats() {
        try {
            const res = await fetch('/api/knowledge/stats');
            const stats = await res.json();
            const kgEl = document.getElementById('stat-kg-entities');
            if (kgEl) kgEl.textContent = stats.total_entities || 0;
        } catch (err) {
            // Silent fail
        }
    }

    _renderStats(stats) {
        if (!this.statsEl) return;

        const types = stats.entity_types || {};
        const typeHtml = Object.entries(types)
            .map(([type, count]) => {
                const color = this.typeColors[type] || '#888';
                return `<span class="kg-type-badge" style="background:${color}20;color:${color};border:1px solid ${color}40">${type}: ${count}</span>`;
            })
            .join(' ');

        this.statsEl.innerHTML = `
            <div class="kg-stat-row">
                <span class="kg-stat">🔵 ${stats.total_entities || 0} entities</span>
                <span class="kg-stat">🔗 ${stats.total_relationships || 0} relationships</span>
            </div>
            <div class="kg-type-badges">${typeHtml}</div>
        `;
    }

    _renderEntityList(entities) {
        if (!this.entityList) return;

        this.entityList.innerHTML = entities.slice(0, 30).map(e => {
            const color = this.typeColors[e.type] || '#888';
            return `
                <div class="kg-entity-card">
                    <span class="kg-entity-dot" style="background:${color}"></span>
                    <span class="kg-entity-name">${e.label}</span>
                    <span class="kg-entity-type" style="color:${color}">${e.type}</span>
                    <span class="kg-entity-mentions">${e.mention_count}×</span>
                </div>
            `;
        }).join('');
    }

    _filterEntities(query) {
        if (!query) {
            this._renderEntityList(this.nodes);
            return;
        }
        const q = query.toLowerCase();
        const filtered = this.nodes.filter(n =>
            n.label.toLowerCase().includes(q) || n.type.includes(q)
        );
        this._renderEntityList(filtered);
    }

    _renderCanvas() {
        if (!this.canvas || !this.ctx || this.nodes.length === 0) return;

        const W = this.canvas.width = this.canvas.parentElement?.offsetWidth || 700;
        const H = this.canvas.height = 400;
        const ctx = this.ctx;

        // Assign positions using force-directed layout (simplified)
        const positions = this._layoutNodes(W, H);

        // Animation loop
        const draw = () => {
            ctx.clearRect(0, 0, W, H);

            // Draw edges
            ctx.lineWidth = 1;
            for (const edge of this.edges) {
                const srcPos = positions[edge.source];
                const tgtPos = positions[edge.target];
                if (!srcPos || !tgtPos) continue;

                ctx.strokeStyle = 'rgba(99, 102, 241, 0.25)';
                ctx.beginPath();
                ctx.moveTo(srcPos.x, srcPos.y);
                ctx.lineTo(tgtPos.x, tgtPos.y);
                ctx.stroke();

                // Relation label at midpoint
                const mx = (srcPos.x + tgtPos.x) / 2;
                const my = (srcPos.y + tgtPos.y) / 2;
                ctx.fillStyle = 'rgba(148, 163, 184, 0.5)';
                ctx.font = '9px Inter, sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText(edge.relation, mx, my - 4);
            }

            // Draw nodes
            for (const node of this.nodes) {
                const pos = positions[node.id];
                if (!pos) continue;

                const color = this.typeColors[node.type] || '#888';
                const radius = 6 + Math.min(node.mention_count * 2, 12);

                // Glow
                ctx.shadowColor = color;
                ctx.shadowBlur = 12;

                // Node circle
                ctx.fillStyle = color + '80';
                ctx.beginPath();
                ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
                ctx.fill();

                ctx.shadowBlur = 0;

                // Inner circle
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(pos.x, pos.y, radius * 0.6, 0, Math.PI * 2);
                ctx.fill();

                // Label
                ctx.fillStyle = '#e2e8f0';
                ctx.font = '11px Inter, sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText(node.label, pos.x, pos.y + radius + 14);
            }
        };

        draw();
    }

    _layoutNodes(W, H) {
        const positions = {};
        const padding = 50;
        const count = this.nodes.length;

        if (count === 0) return positions;

        // Simple circular layout with jitter
        const cx = W / 2;
        const cy = H / 2;
        const radius = Math.min(W, H) / 2 - padding;

        this.nodes.forEach((node, i) => {
            const angle = (2 * Math.PI * i) / count - Math.PI / 2;
            const r = radius * (0.5 + 0.5 * (node.mention_count / (Math.max(...this.nodes.map(n => n.mention_count)) || 1)));
            positions[node.id] = {
                x: cx + Math.cos(angle) * r,
                y: cy + Math.sin(angle) * r,
            };
        });

        return positions;
    }
}

// Emotion display helpers
const EMOTION_ICONS = {
    joy: '😊',
    sadness: '😢',
    anger: '😡',
    fear: '😰',
    stress: '😩',
    curiosity: '🤔',
    confusion: '😕',
    neutral: '😐',
};

function updateEmotionIndicator(emotionData) {
    const indicator = document.getElementById('emotion-indicator');
    const iconEl = document.getElementById('emotion-icon');
    const labelEl = document.getElementById('emotion-label');

    if (!indicator || !emotionData || emotionData.emotion === 'neutral') {
        if (indicator) indicator.style.display = 'none';
        return;
    }

    const emotion = emotionData.emotion;
    const intensity = emotionData.intensity || 0;

    iconEl.textContent = EMOTION_ICONS[emotion] || '😐';
    labelEl.textContent = `${emotion} (${Math.round(intensity * 100)}%)`;
    indicator.style.display = 'flex';

    // Auto-hide after 10 seconds
    setTimeout(() => {
        indicator.style.opacity = '0';
        setTimeout(() => { indicator.style.display = 'none'; indicator.style.opacity = '1'; }, 300);
    }, 10000);
}
