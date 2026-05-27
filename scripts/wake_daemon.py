#!/usr/bin/env python3
"""
ALAS Wake Word Engine

Runs in the background and continuously listens for the wake word "ALAS".
When detected, it records the user's command, sends it to the ALAS backend,
and plays the response out loud.

Requirements:
pip install SpeechRecognition PyAudio requests
"""

import io
import time
import requests
import logging
import threading
import subprocess

try:
    import speech_recognition as sr
except ImportError:
    print("Please install SpeechRecognition and PyAudio: pip install SpeechRecognition PyAudio")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | WAKE | %(message)s")
logger = logging.getLogger("alas.wake")

ALAS_API_URL = "http://localhost:8000/api"
WAKE_WORDS = ["alas", "atlas", "alice", "dallas", "hey alas", "ok alas"]

def play_audio_from_bytes(audio_bytes):
    """Play MP3 audio bytes using the system player (ffplay or mpg123)."""
    try:
        # We'll use ffplay (part of ffmpeg) which is usually installed
        process = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-i", "pipe:0"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        process.communicate(input=audio_bytes)
    except Exception as e:
        logger.error(f"Could not play audio: {e}")
        # Fallback to mpv
        try:
            process = subprocess.Popen(
                ["mpv", "--no-video", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            process.communicate(input=audio_bytes)
        except Exception:
            pass

def play_chime(type="wake"):
    """Play a short chime sound to indicate listening or processing using ffplay."""
    try:
        if type == "wake":
            # high pitch
            subprocess.run(["ffplay", "-f", "lavfi", "-i", "sine=frequency=880:duration=0.1", "-autoexit", "-nodisp"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        else:
            # low pitch
            subprocess.run(["ffplay", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.1", "-autoexit", "-nodisp"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    except Exception:
        pass

def process_command(audio_data):
    """Send the recorded audio to ALAS for transcription and response."""
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

def main():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True

    with sr.Microphone() as source:
        logger.info("Adjusting for ambient noise... Please wait.")
        recognizer.adjust_for_ambient_noise(source, duration=2)
        logger.info("✅ Wake Word Engine Active. Say 'Hey ALAS' to trigger.")

        while True:
            try:
                # Listen in short chunks for the wake word
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=3)
                
                # We use Google's free API for fast wake-word detection because it's highly optimized for short phrases
                try:
                    transcript = recognizer.recognize_google(audio).lower()
                except sr.UnknownValueError:
                    continue
                except sr.RequestError:
                    # Fallback to local whisper for wake word
                    files = {'audio': ('wake.wav', audio.get_wav_data(), 'audio/wav')}
                    try:
                        res = requests.post(f"{ALAS_API_URL}/voice/transcribe", files=files, timeout=2)
                        transcript = res.json().get("text", "").lower()
                    except Exception:
                        continue
                        
                logger.debug(f"Heard: {transcript}")
                
                # Check if wake word is in transcript
                if any(ww in transcript for ww in WAKE_WORDS):
                    logger.info("!!! WAKE WORD DETECTED !!!")
                    play_chime("wake")
                    
                    # Now listen for the actual command
                    logger.info("Listening for command...")
                    try:
                        command_audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
                        play_chime("done")
                        
                        # Process the command in a separate thread so we can resume listening quickly
                        threading.Thread(target=process_command, args=(command_audio,)).start()
                        
                    except sr.WaitTimeoutError:
                        logger.info("Command timeout.")
                        
            except sr.WaitTimeoutError:
                pass
            except Exception as e:
                logger.error(f"Microphone error: {e}")
                time.sleep(1)

if __name__ == "__main__":
    main()
