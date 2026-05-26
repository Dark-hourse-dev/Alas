/**
 * ALAS Voice Module — Browser-based speech I/O with server TTS fallback.
 */

class ALASVoice {
  constructor() {
    this.recognition = null;
    this.isRecording = false;
    this.sttAvailable = false;
    this._initSTT();
  }

  _initSTT() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    this.recognition = new SpeechRecognition();
    this.recognition.continuous = false;
    this.recognition.interimResults = true;
    this.recognition.lang = 'en-US';
    this.sttAvailable = true;

    this.recognition.onresult = (event) => {
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      const input = document.getElementById('message-input');
      input.value = transcript;
      input.dispatchEvent(new Event('input'));

      if (event.results[event.results.length - 1].isFinal) {
        this.stopRecording();
      }
    };

    this.recognition.onerror = () => this.stopRecording();
    this.recognition.onend = () => this.stopRecording();
  }

  startRecording() {
    if (!this.recognition || this.isRecording) return;
    this.isRecording = true;
    this.recognition.start();
    document.getElementById('btn-voice-input').classList.add('recording');
  }

  stopRecording() {
    if (!this.isRecording) return;
    this.isRecording = false;
    try { this.recognition?.stop(); } catch (e) {}
    document.getElementById('btn-voice-input').classList.remove('recording');
  }

  toggleRecording() {
    this.isRecording ? this.stopRecording() : this.startRecording();
  }

  async speak(text, mode = 'casual') {
    // Try server TTS first
    try {
      const res = await fetch('/api/voice/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.slice(0, 500), mode }),
      });
      if (res.ok && res.headers.get('content-type')?.includes('audio')) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.play();
        audio.onended = () => URL.revokeObjectURL(url);
        return;
      }
    } catch (e) {}

    // Fallback to browser Speech Synthesis
    if ('speechSynthesis' in window) {
      const utter = new SpeechSynthesisUtterance(text.slice(0, 300));
      utter.rate = mode === 'calm' ? 0.85 : mode === 'work' ? 1.1 : 1;
      speechSynthesis.speak(utter);
    }
  }
}

window.alasVoice = new ALASVoice();
