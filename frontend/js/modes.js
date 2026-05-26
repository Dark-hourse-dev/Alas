/**
 * ALAS Modes Module — Mode switching with theme transitions.
 */

class ALASModes {
  constructor() {
    this.currentMode = 'casual';
    this.modeNames = {
      casual: 'Casual Mode', work: 'Work Mode', creative: 'Creative Mode',
      learning: 'Learning Mode', calm: 'Calm Mode', emergency: 'Emergency Mode',
    };
  }

  setMode(mode) {
    if (!this.modeNames[mode]) return;
    this.currentMode = mode;

    // Update data attribute for CSS theming
    document.body.setAttribute('data-mode', mode);

    // Update mode buttons
    document.querySelectorAll('.mode-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    // Update header
    document.getElementById('current-mode-name').textContent = this.modeNames[mode];

    // Update chat engine mode
    if (window.alasChat) window.alasChat.mode = mode;

    // Animate orbs based on mode
    this._updateAmbience(mode);
  }

  _updateAmbience(mode) {
    const orbs = document.querySelectorAll('.orb');
    const configs = {
      casual: [0.15, '20s'], work: [0.08, '30s'], creative: [0.25, '15s'],
      learning: [0.12, '25s'], calm: [0.1, '35s'], emergency: [0.3, '10s'],
    };
    const [opacity, duration] = configs[mode] || configs.casual;
    orbs.forEach(orb => {
      orb.style.opacity = opacity;
      orb.style.animationDuration = duration;
    });
  }
}

window.alasModes = new ALASModes();
