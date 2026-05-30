class WebRTCController {
    constructor() {
        this.pc = null;
        this.localStream = null;
        this.isStreaming = false;
        this.indicator = document.getElementById('perception-indicator');
    }

    async startPerception() {
        if (this.isStreaming) return;

        try {
            // Request camera and microphone access
            this.localStream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480, frameRate: 15 },
                audio: true
            });

            this.pc = new RTCPeerConnection();

            // Add local tracks to the peer connection
            this.localStream.getTracks().forEach(track => {
                this.pc.addTrack(track, this.localStream);
            });

            // Handle connection state changes
            this.pc.onconnectionstatechange = () => {
                console.log("WebRTC Connection State:", this.pc.connectionState);
                if (this.pc.connectionState === 'connected') {
                    this.isStreaming = true;
                    if (this.indicator) this.indicator.classList.add('active');
                } else if (this.pc.connectionState === 'disconnected' || this.pc.connectionState === 'failed') {
                    this.stopPerception();
                }
            };

            // Create SDP Offer
            const offer = await this.pc.createOffer();
            await this.pc.setLocalDescription(offer);

            // Send Offer to ALAS Backend via Signaling Endpoint
            const response = await fetch('/api/webrtc/offer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sdp: this.pc.localDescription.sdp,
                    type: this.pc.localDescription.type
                })
            });

            if (!response.ok) throw new Error('Failed to negotiate WebRTC connection with ALAS backend.');

            // Apply the SDP Answer from ALAS
            const answer = await response.json();
            await this.pc.setRemoteDescription(new RTCSessionDescription(answer));

        } catch (err) {
            console.error("WebRTC Error:", err);
            this.stopPerception();
            alert("Failed to start ALAS Perception: " + err.message);
        }
    }

    stopPerception() {
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }
        if (this.pc) {
            this.pc.close();
            this.pc = null;
        }
        this.isStreaming = false;
        if (this.indicator) this.indicator.classList.remove('active');
    }
    
    togglePerception() {
        if (this.isStreaming) {
            this.stopPerception();
        } else {
            this.startPerception();
        }
    }
}

// Global instance
window.alasWebRTC = new WebRTCController();
