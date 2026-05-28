#!/usr/bin/env python3
"""
ALAS Wake Word Engine (Phase 3.5)

Runs in the background and continuously listens for the wake word using OpenWakeWord
(completely offline, <2% CPU). When detected, it records the user's command, sends it 
to the ALAS backend, and plays the response out loud.

It also supports a global Push-to-Talk hotkey (Ctrl+Shift+Space).

Requirements:
pip install openwakeword pyaudio pynput requests SpeechRecognition
"""

import io
import time
import requests
import logging
import threading
import subprocess
import numpy as np

try:
    import pyaudio
    from openwakeword.model import Model
    from pynput import keyboard
    import speech_recognition as sr
except ImportError:
    print("Please install requirements: pip install openwakeword pyaudio pynput requests SpeechRecognition")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | WAKE | %(message)s")
logger = logging.getLogger("alas.wake")

ALAS_API_URL = "http://localhost:8000/api"

# --- Audio Playback Utils ---

def play_audio_from_bytes(audio_bytes):
    """Play MP3 audio bytes using the system player (ffplay or mpv)."""
    try:
        process = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-i", "pipe:0"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        process.communicate(input=audio_bytes)
    except Exception as e:
        logger.error(f"Could not play audio: {e}")

def play_chime(type="wake"):
    """Play a short chime sound to indicate listening or processing using ffplay."""
    try:
        if type == "wake":
            subprocess.run(["ffplay", "-f", "lavfi", "-i", "sine=frequency=880:duration=0.1", "-autoexit", "-nodisp"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        else:
            subprocess.run(["ffplay", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.1", "-autoexit", "-nodisp"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    except Exception:
        pass


# --- Command Processing ---

is_processing = False

def process_command(audio_data):
    """Send the recorded audio to ALAS for transcription and response."""
    global is_processing
    try:
        logger.info("Transcribing command...")
        
        # 1. Transcribe the audio
        files = {'audio': ('command.wav', audio_data.get_wav_data(), 'audio/wav')}
        res = requests.post(f"{ALAS_API_URL}/voice/transcribe", files=files, timeout=10)
        
        if not res.ok:
            logger.error("Transcription failed.")
            return
            
        text = res.json().get("text", "").strip()
        if not text:
            logger.info("No speech detected.")
            return
            
        logger.info(f"User: {text}")
        
        # 2. Send to Chat API
        logger.info("Generating response...")
        chat_res = requests.post(
            f"{ALAS_API_URL}/chat/message",
            json={"message": text, "mode": "casual"},
            timeout=60
        )
        
        if not chat_res.ok:
            logger.error("Chat generation failed.")
            return
            
        response_text = chat_res.json().get("response", "")
        logger.info(f"ALAS: {response_text}")
        
        # 3. Synthesize the response
        tts_res = requests.post(
            f"{ALAS_API_URL}/voice/synthesize",
            json={"text": response_text, "mode": "casual"},
            timeout=30
        )
        
        if tts_res.ok and tts_res.headers.get("content-type") == "audio/mpeg":
            play_audio_from_bytes(tts_res.content)
            
    except Exception as e:
        logger.error(f"Error processing command: {e}")
    finally:
        is_processing = False

def trigger_listening():
    """Triggered by wake word or hotkey. Stops continuous listening and records command."""
    global is_processing
    if is_processing:
        return
        
    is_processing = True
    logger.info("!!! ALAS ACTIVATED !!!")
    play_chime("wake")
    
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True

    with sr.Microphone() as source:
        logger.info("Listening for command...")
        try:
            # Listen for up to 15 seconds
            command_audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
            play_chime("done")
            
            # Process in thread
            threading.Thread(target=process_command, args=(command_audio,)).start()
        except sr.WaitTimeoutError:
            logger.info("Command timeout. Nobody spoke.")
            is_processing = False
        except Exception as e:
            logger.error(f"Mic error: {e}")
            is_processing = False

# --- Hotkey Listener ---
def on_activate_h():
    logger.info("Hotkey detected!")
    if not is_processing:
        threading.Thread(target=trigger_listening).start()

def setup_hotkey():
    # Ctrl + Shift + Space
    hotkey = keyboard.GlobalHotKeys({
        '<ctrl>+<shift>+<space>': on_activate_h
    })
    hotkey.start()
    logger.info("⌨️  Push-to-Talk Hotkey registered: Ctrl+Shift+Space")


# --- Main Loop ---

def main():
    # Setup hotkey
    setup_hotkey()
    
    # Audio configuration for OpenWakeWord
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 1280

    audio = pyaudio.PyAudio()
    mic_stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    
    logger.info("Loading OpenWakeWord model (offline)...")
    # Using 'hey_jarvis' as default until 'hey_alas' model is generated by the user
    # Other options: 'alexa', 'hey_mycroft'
    oww_model = Model(wakeword_models=["hey_jarvis"])
    
    logger.info("✅ Wake Word Engine Active. Say 'Hey Jarvis' or press Ctrl+Shift+Space to trigger ALAS.")

    try:
        while True:
            if is_processing:
                # Sleep while ALAS is talking/listening to command
                time.sleep(0.5)
                # Flush the stream so old audio doesn't trigger wake word instantly again
                if mic_stream.is_active():
                    mic_stream.stop_stream()
                continue
                
            if not mic_stream.is_active():
                mic_stream.start_stream()

            # Read audio chunk
            audio_data = np.frombuffer(mic_stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
            
            # Predict
            prediction = oww_model.predict(audio_data)
            
            # Check for trigger
            for mdl in oww_model.models.keys():
                if prediction[mdl] > 0.5:
                    logger.info(f"Wake word '{mdl}' detected!")
                    threading.Thread(target=trigger_listening).start()
                    break
                    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        mic_stream.stop_stream()
        mic_stream.close()
        audio.terminate()

if __name__ == "__main__":
    main()
