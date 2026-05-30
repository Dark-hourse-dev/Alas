import logging
import json
from fastapi import APIRouter
from pydantic import BaseModel
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole

logger = logging.getLogger("alas.api.webrtc")
router = APIRouter(prefix="/api/webrtc", tags=["webrtc"])

# Keep track of active peer connections
pcs = set()

class OfferRequest(BaseModel):
    sdp: str
    type: str

@router.post("/offer")
async def offer(request: OfferRequest):
    """
    WebRTC Signaling Endpoint.
    Receives an SDP offer from the browser, creates a PeerConnection,
    and returns an SDP answer to establish the stream.
    """
    logger.info("📡 [WebRTC] Received connection offer from client.")
    
    offer_sdp = RTCSessionDescription(sdp=request.sdp, type=request.type)
    pc = RTCPeerConnection()
    pcs.add(pc)
    
    # We use a MediaBlackhole to consume the incoming tracks 
    # without playing them back through the server's speakers.
    recorder = MediaBlackhole()

    @pc.on("datachannel")
    def on_datachannel(channel):
        logger.info(f"📡 [WebRTC] Data channel established: {channel.label}")
        @channel.on("message")
        def on_message(message):
            logger.info(f"📡 [WebRTC] Message from client: {message}")

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"📡 [WebRTC] Connection state is {pc.connectionState}")
        if pc.connectionState == "failed" or pc.connectionState == "closed":
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    def on_track(track):
        logger.info(f"📡 [WebRTC] Track received: {track.kind}")
        
        if track.kind == "video":
            logger.info("📡 [WebRTC] Video track attached to perception engine.")
            
            async def consume_video(t):
                from backend.app.sensors.webcam import get_webcam_sensor
                sensor = get_webcam_sensor()
                import time
                last_processed = 0
                while True:
                    try:
                        frame = await t.recv()
                        now = time.time()
                        # Only push frames ~6 fps to save CPU
                        if now - last_processed >= 0.15:
                            img = frame.to_ndarray(format="bgr24")
                            sensor.push_frame(img)
                            last_processed = now
                    except Exception as e:
                        logger.warning(f"📡 [WebRTC] Video track ended: {e}")
                        break
            
            import asyncio
            asyncio.create_task(consume_video(track))
            
        elif track.kind == "audio":
            logger.info("📡 [WebRTC] Audio track attached to perception engine (VAD).")
            
            async def consume_audio(t):
                from backend.app.sensors.mic import get_mic_sensor
                sensor = get_mic_sensor()
                while True:
                    try:
                        frame = await t.recv()
                        audio_data = frame.to_ndarray()
                        sensor.push_frame(audio_data)
                    except Exception as e:
                        logger.warning(f"📡 [WebRTC] Audio track ended: {e}")
                        break
                        
            import asyncio
            asyncio.create_task(consume_audio(track))
            
        @track.on("ended")
        async def on_ended():
            logger.info(f"📡 [WebRTC] Track ended: {track.kind}")
            await recorder.stop()

    # Start the recorder to consume frames
    await recorder.start()

    # Handle the SDP negotiation
    await pc.setRemoteDescription(offer_sdp)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    logger.info("📡 [WebRTC] Sending connection answer to client.")
    return {
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    }
