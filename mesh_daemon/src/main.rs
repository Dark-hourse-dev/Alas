use axum::{
    extract::{State, Json},
    routing::{post, get},
    Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{info, error, warn};
use reqwest::Client;

/// Represents a unit of memory to be synced across the mesh.
#[derive(Debug, Serialize, Deserialize, Clone)]
struct MemoryPacket {
    id: String,
    timestamp: u64,
    source_device: String,
    content: String,
    vector_hash: Option<String>,
}

/// The internal state of our Mesh Node
struct MeshState {
    device_id: String,
    // IPs or hostnames of other ALAS instances on the Tailscale mesh
    peers: RwLock<Vec<String>>,
    http_client: Client,
}

#[tokio::main]
async fn main() {
    // Initialize logging
    tracing_subscriber::fmt::init();
    info!("🚀 Starting ALAS Cross-Device Mesh Daemon (Phase 4)");

    let state = Arc::new(MeshState {
        device_id: "alas-host-primary".to_string(),
        peers: RwLock::new(vec![
            // Hardcoded Tailscale IPs for prototype (e.g., phone, laptop)
            // "100.x.y.z:8555".to_string(),
        ]),
        http_client: Client::new(),
    });

    // Build the Axum router
    let app = Router::new()
        .route("/health", get(health_check))
        .route("/sync/receive", post(handle_receive_memory))
        .route("/sync/broadcast", post(handle_broadcast_memory))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:8555").await.unwrap();
    info!("🌐 Mesh Node listening on 0.0.0.0:8555");
    
    axum::serve(listener, app).await.unwrap();
}

async fn health_check() -> &'static str {
    "ALAS Mesh Node is online."
}

/// Endpoint: Called by other Tailscale peers when they have a new memory.
async fn handle_receive_memory(
    State(_state): State<Arc<MeshState>>,
    Json(packet): Json<MemoryPacket>,
) -> &'static str {
    info!(
        "📥 Received memory from {}: '{}' (ID: {})",
        packet.source_device, packet.content, packet.id
    );
    
    // TODO: In a full implementation, we would write this directly into the 
    // local SQLite/ChromaDB instances or ping the Python backend via webhook.
    
    "Memory ingested."
}

/// Endpoint: Called by the LOCAL Python backend when a new memory is formed.
/// This daemon then broadcasts it to all known Tailscale peers.
async fn handle_broadcast_memory(
    State(state): State<Arc<MeshState>>,
    Json(mut packet): Json<MemoryPacket>,
) -> &'static str {
    packet.source_device = state.device_id.clone();
    info!("📤 Broadcasting new memory to mesh: '{}'", packet.content);

    let peers = state.peers.read().await;
    
    for peer_ref in peers.iter() {
        let peer = peer_ref.clone();
        let url = format!("http://{}/sync/receive", peer);
        let client = state.http_client.clone();
        let payload = packet.clone();
        
        // Broadcast asynchronously without blocking
        tokio::spawn(async move {
            match client.post(&url).json(&payload).send().await {
                Ok(resp) => {
                    if !resp.status().is_success() {
                        warn!("⚠️ Peer {} rejected memory sync: {}", peer, resp.status());
                    } else {
                        info!("✅ Synced to peer {}", peer);
                    }
                }
                Err(e) => {
                    error!("❌ Failed to sync to peer {}: {}", peer, e);
                }
            }
        });
    }

    "Broadcast initiated."
}
