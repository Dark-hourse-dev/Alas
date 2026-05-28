/**
 * ALAS Evolution Dashboard — JS Module
 * Fetches and displays behavioral genome and adapter statuses.
 */

class ALASEvolution {
    constructor() {
        this.modal = document.getElementById('evolution-modal');
        this.btnOpen = document.getElementById('btn-nav-evolution');
        this.btnClose = document.getElementById('btn-close-evolution-modal');
        
        if (this.btnOpen && this.btnClose) {
            this.btnOpen.addEventListener('click', () => this.openDashboard());
            this.btnClose.addEventListener('click', () => this.closeDashboard());
        }

        // Close on outside click
        if (this.modal) {
            this.modal.addEventListener('click', (e) => {
                if (e.target === this.modal) this.closeDashboard();
            });
        }
    }

    async openDashboard() {
        if (!this.modal) return;
        this.modal.style.display = 'flex';
        await this.loadEvolutionStatus();
        await this.loadAdapters();
        await this.loadFitness();
    }

    closeDashboard() {
        if (this.modal) this.modal.style.display = 'none';
    }

    async loadEvolutionStatus() {
        try {
            const res = await fetch('/api/learning/evolution/status');
            if (res.ok) {
                const genome = await res.json();
                
                document.getElementById('evo-generation').textContent = genome.generation || 1;
                
                // Update bars (assuming values are 0.0 to 1.0, map to 0-100%)
                const setBar = (id, val) => {
                    const el = document.getElementById(id);
                    if (el) {
                        el.style.width = `${Math.min(100, Math.max(0, val * 100))}%`;
                        // Change color based on value
                        if (val > 0.7) el.style.background = 'var(--accent)';
                        else if (val < 0.3) el.style.background = 'var(--text-dim)';
                        else el.style.background = 'var(--primary)';
                    }
                };

                setBar('trait-verbosity', genome.verbosity_weight || 0.5);
                setBar('trait-formality', genome.formality_index || 0.5);
                setBar('trait-proactivity', genome.proactivity_threshold || 0.5);
                
                // Empathy is 0.0 to 2.0, so divide by 2 for percentage
                setBar('trait-empathy', (genome.empathy_multiplier || 1.0) / 2.0);
            }
        } catch (e) {
            console.error('Failed to load evolution status', e);
        }
    }

    async loadFitness() {
        // Fetch fitness for the current session
        const sessionId = window.alasChat?.sessionId;
        if (!sessionId) return;
        try {
            const res = await fetch(`/api/learning/feedback/${sessionId}`);
            if (res.ok) {
                const data = await res.json();
                const fitnessSpan = document.getElementById('evo-fitness');
                if (fitnessSpan) {
                    fitnessSpan.textContent = data.fitness ? data.fitness.toFixed(2) : '0.00';
                    if (data.fitness > 0.7) fitnessSpan.style.color = 'var(--success)';
                    else if (data.fitness < 0.4) fitnessSpan.style.color = '#ef4444';
                    else fitnessSpan.style.color = 'var(--text)';
                }
            }
        } catch(e) {}
    }

    async loadAdapters() {
        try {
            const res = await fetch('/api/learning/adapters');
            if (res.ok) {
                const adapters = await res.json();
                const container = document.getElementById('adapter-list');
                if (!container) return;
                
                container.innerHTML = '';
                
                for (const [name, info] of Object.entries(adapters)) {
                    const el = document.createElement('div');
                    el.className = 'adapter-item';
                    el.style.display = 'flex';
                    el.style.justifyContent = 'space-between';
                    el.style.alignItems = 'center';
                    el.style.padding = '8px';
                    el.style.marginBottom = '8px';
                    el.style.background = 'rgba(255,255,255,0.05)';
                    el.style.borderRadius = '6px';
                    
                    const isLoaded = info.status === 'loaded';
                    const color = isLoaded ? 'var(--success)' : 'var(--text-dim)';
                    
                    el.innerHTML = `
                        <span style="font-weight: 500">${name}</span>
                        <span style="color: ${color}; font-size: 0.9em">${info.status}</span>
                    `;
                    container.appendChild(el);
                }
            }
        } catch (e) {
            console.error('Failed to load adapters', e);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.alasEvolution = new ALASEvolution();
});
