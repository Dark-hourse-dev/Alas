/**
 * ALAS Voice Module — Robust speech I/O for desktop & mobile.
 *
 * STT Strategy:
 *   1. Try browser Web Speech API (Chrome, Edge, Safari 14.1+)
 *   2. Fallback to MediaRecorder → send audio to /api/voice/transcribe (Whisper)
 *
 * TTS Strategy:
 *   1. Try server Edge-TTS (/api/voice/synthesize)
 *   2. Fallback to browser SpeechSynthesis
 */

class ALASVoice {
  constructor() {
    this.recognition = null;
    this.isRecording = false;
    this.sttAvailable = false;
    this.sttMethod = 'none'; // 'browser', 'whisper', or 'none'
    this.autoSend = true; // Auto-send after voice input completes

    // MediaRecorder fallback state
    this._mediaRecorder = null;
    this._audioChunks = [];

    this._initSTT();
  }

  _initSTT() {
    // Try browser Speech Recognition first
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
      try {
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';
        this.sttAvailable = true;
        this.sttMethod = 'browser';

        this.recognition.onresult = (event) => {
          let transcript = '';
          let isFinal = false;
          for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
            if (event.results[i].isFinal) isFinal = true;
          }

          const input = document.getElementById('message-input');
          input.value = transcript;
          input.dispatchEvent(new Event('input'));

          // Update visual indicator with live transcript
          this._updateLiveTranscript(transcript, isFinal);

          if (isFinal) {
            this.stopRecording();
            // Auto-send the transcribed message
            if (this.autoSend && transcript.trim()) {
              setTimeout(() => {
                document.getElementById('btn-send')?.click();
              }, 300);
            }
          }
        };

        this.recognition.onerror = (event) => {
          console.warn('Speech recognition error:', event.error);

          if (event.error === 'not-allowed' || event.error === 'service-not-available') {
            // Browser STT not available, try Whisper fallback
            this.sttMethod = 'none';
            this._showVoiceToast('🎤 Mic permission denied or STT unavailable. Trying Whisper...');
            this._initWhisperFallback();
          } else if (event.error === 'no-speech') {
            this._showVoiceToast('🎤 No speech detected. Try again.');
          } else if (event.error === 'network') {
            this._showVoiceToast('🎤 Network error. Trying offline mode...');
            this._initWhisperFallback();
          }

          this.stopRecording();
        };

        this.recognition.onend = () => {
          if (this.isRecording) {
            // Stopped unexpectedly — don't leave UI in recording state
            this.stopRecording();
          }
        };

        console.log('✅ Voice: Browser Speech Recognition available');
        return;
      } catch (e) {
        console.warn('Browser Speech Recognition failed to init:', e);
      }
    }

    // Browser STT not available — try Whisper fallback
    this._initWhisperFallback();
  }

  async _initWhisperFallback() {
    /**
     * Whisper fallback: record audio with MediaRecorder,
     * then POST to /api/voice/transcribe for server-side Whisper transcription.
     */
    if (this.sttMethod === 'whisper') return; // Already initialized

    try {
      // Check if server-side Whisper is available
      const res = await fetch('/api/voice/stt/status');
      if (res.ok) {
        const data = await res.json();
        if (data.available) {
          this.sttMethod = 'whisper';
          this.sttAvailable = true;
          console.log('✅ Voice: Whisper STT fallback available');
          return;
        }
      }
    } catch (e) {
      console.warn('Whisper STT status check failed:', e);
    }

    // Check if at least MediaRecorder is available (we can still try to send audio)
    if (typeof MediaRecorder !== 'undefined' && navigator.mediaDevices) {
      this.sttMethod = 'whisper';
      this.sttAvailable = true;
      console.log('✅ Voice: MediaRecorder available, will attempt Whisper transcription');
    } else {
      this.sttMethod = 'none';
      this.sttAvailable = false;
      console.warn('⚠️ Voice: No STT method available');
    }
  }

  async startRecording() {
    if (this.isRecording) return;

    const btn = document.getElementById('btn-voice-input');

    if (this.sttMethod === 'browser' && this.recognition) {
      // Browser Speech Recognition
      try {
        this.recognition.start();
        this.isRecording = true;
        btn?.classList.add('recording');
        const indicator = document.getElementById('listening-indicator');
        if (indicator) indicator.style.display = 'flex';
        this._showVoiceToast('🎤 Listening...');
      } catch (e) {
        console.error('Failed to start browser STT:', e);
        this.isRecording = false;
        btn?.classList.remove('recording');
        // Try Whisper fallback
        this.sttMethod = 'none';
        await this._initWhisperFallback();
        if (this.sttMethod === 'whisper') {
          this.startRecording();
        } else {
          this._showVoiceToast('❌ Voice input not available on this device.');
        }
      }
    } else if (this.sttMethod === 'whisper') {
      // MediaRecorder → Whisper server
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,
            sampleRate: 16000,
            echoCancellation: true,
            noiseSuppression: true,
          }
        });

        this.isRecording = true;
        btn?.classList.add('recording');
        const indicator = document.getElementById('listening-indicator');
        if (indicator) indicator.style.display = 'flex';
        this._showVoiceToast('🎤 Recording... (tap again to stop)');

        this._audioChunks = [];
        this._mediaRecorder = new MediaRecorder(stream, {
          mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
            ? 'audio/webm;codecs=opus'
            : 'audio/webm'
        });

        this._mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) this._audioChunks.push(e.data);
        };

        this._mediaRecorder.onstop = async () => {
          // Stop all tracks
          stream.getTracks().forEach(t => t.stop());

          if (this._audioChunks.length === 0) {
            this._showVoiceToast('🎤 No audio captured.');
            return;
          }

          const audioBlob = new Blob(this._audioChunks, { type: 'audio/webm' });
          this._showVoiceToast('⏳ Transcribing...');
          await this._transcribeWithWhisper(audioBlob);
        };

        this._mediaRecorder.start();
      } catch (e) {
        console.error('MediaRecorder failed:', e);
        this.isRecording = false;
        btn?.classList.remove('recording');

        if (e.name === 'NotAllowedError') {
          this._showVoiceToast('❌ Microphone access denied. Please allow mic permission in your browser settings.');
        } else {
          this._showVoiceToast(`❌ Failed to access microphone: ${e.message}`);
        }
      }
    } else {
      this._showVoiceToast('❌ Voice input not available. Install a browser with Speech Recognition or enable Whisper on the server.');
    }
  }

  stopRecording() {
    if (!this.isRecording) return;
    this.isRecording = false;

    const btn = document.getElementById('btn-voice-input');
    btn?.classList.remove('recording');
    const indicator = document.getElementById('listening-indicator');
    if (indicator) indicator.style.display = 'none';

    if (this.sttMethod === 'browser' && this.recognition) {
      try { this.recognition.stop(); } catch (e) {}
    } else if (this._mediaRecorder && this._mediaRecorder.state === 'recording') {
      this._mediaRecorder.stop();
    }

    this._hideLiveTranscript();
  }

  toggleRecording() {
    this.isRecording ? this.stopRecording() : this.startRecording();
  }

  async _transcribeWithWhisper(audioBlob) {
    /**
     * Send recorded audio to the Whisper backend for transcription.
     */
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      const res = await fetch('/api/voice/transcribe', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);

      const data = await res.json();

      if (data.error) {
        this._showVoiceToast(`⚠️ ${data.error}`);
        return;
      }

      const transcript = data.text?.trim();
      if (!transcript) {
        this._showVoiceToast('🎤 No speech detected. Try speaking louder or closer to the mic.');
        return;
      }

      // Fill the input with the transcribed text
      const input = document.getElementById('message-input');
      input.value = transcript;
      input.dispatchEvent(new Event('input'));

      this._showVoiceToast(`✅ "${transcript.slice(0, 50)}${transcript.length > 50 ? '...' : ''}"`);

      // Auto-send
      if (this.autoSend) {
        setTimeout(() => {
          document.getElementById('btn-send')?.click();
        }, 500);
      }

    } catch (err) {
      console.error('Whisper transcription failed:', err);
      this._showVoiceToast(`❌ Transcription failed: ${err.message}`);
    }
  }

  // --- TTS (Text-to-Speech) ---

  async speak(text, mode = 'casual') {
    // Try server TTS first (Edge-TTS, high quality)
    try {
      const res = await fetch('/api/voice/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.slice(0, 500), mode }),
      });
      if (res.ok && res.headers.get('content-type')?.includes('audio')) {
        const blob = await res.blob();
        if (blob.size > 0) {
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          audio.play();
          audio.onended = () => URL.revokeObjectURL(url);
          return;
        }
      }
    } catch (e) {
      console.warn('Server TTS failed, falling back to browser:', e);
    }

    // Fallback to browser Speech Synthesis
    if ('speechSynthesis' in window) {
      const utter = new SpeechSynthesisUtterance(text.slice(0, 300));
      utter.rate = mode === 'calm' ? 0.85 : mode === 'work' ? 1.1 : 1;
      speechSynthesis.speak(utter);
    }
  }

  // --- UI Helpers ---

  _showVoiceToast(message) {
    // Remove existing toast
    const existing = document.getElementById('voice-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'voice-toast';
    toast.textContent = message;
    toast.style.cssText = `
      position: fixed;
      bottom: 100px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(0,0,0,0.85);
      color: white;
      padding: 10px 20px;
      border-radius: 20px;
      font-size: 0.85rem;
      z-index: 10000;
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255,255,255,0.1);
      animation: fadeInUp 0.3s ease;
      max-width: 90vw;
      text-align: center;
    `;
    document.body.appendChild(toast);

    // Auto-remove after 3s
    setTimeout(() => toast.remove(), 3000);
  }

  _updateLiveTranscript(text, isFinal) {
    let el = document.getElementById('live-transcript');
    if (!el) {
      el = document.createElement('div');
      el.id = 'live-transcript';
      el.style.cssText = `
        position: fixed;
        bottom: 80px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(99, 102, 241, 0.9);
        color: white;
        padding: 8px 16px;
        border-radius: 12px;
        font-size: 0.9rem;
        z-index: 10000;
        max-width: 80vw;
        text-align: center;
        backdrop-filter: blur(10px);
      `;
      document.body.appendChild(el);
    }
    el.textContent = `🎤 ${text}`;
    el.style.opacity = isFinal ? '0.6' : '1';
  }

  _hideLiveTranscript() {
    const el = document.getElementById('live-transcript');
    if (el) {
      setTimeout(() => el.remove(), 500);
    }
  }
}

// Inject animation keyframes
const voiceStyle = document.createElement('style');
voiceStyle.textContent = `
  @keyframes fadeInUp {
    from { opacity: 0; transform: translateX(-50%) translateY(10px); }
    to { opacity: 1; transform: translateX(-50%) translateY(0); }
  }
  #btn-voice-input.recording {
    background: #ef4444 !important;
    animation: pulse-recording 1.5s infinite;
  }
  @keyframes pulse-recording {
    0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.5); }
    50% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
  }
`;
document.head.appendChild(voiceStyle);

window.alasVoice = new ALASVoice();
