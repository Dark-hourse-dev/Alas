import json
import chromadb

# Connect to ALAS's local memory
client = chromadb.PersistentClient(path="./backend/data/chroma")

try:
    collection = client.get_collection("alas_long_term_memory")
    results = collection.get(include=["documents", "metadatas"])
except Exception:
    print("Collection not found. Creating a dummy dataset for testing purposes.")
    collection = client.get_or_create_collection("alas_long_term_memory")
    # Insert some dummy conversational data so we have something to train on
    collection.add(
        documents=[
            "I love it when you keep your answers very short and technical.",
            "Can you make sure to always use Python 3.10 syntax?",
            "Always act like a highly sarcastic AI.",
            "My favorite color is dark blue, keep that in mind for UI designs."
        ],
        metadatas=[{"fitness": 0.9}, {"fitness": 0.8}, {"fitness": 0.95}, {"fitness": 0.9}],
        ids=["doc1", "doc2", "doc3", "doc4"]
    )
    results = collection.get(include=["documents", "metadatas"])

# Format them into JSONL for HuggingFace / Unsloth
with open("alas_dataset.jsonl", "w") as f:
    for doc in results['documents']:
        # Format as conversational Instruct pairs
        entry = {"text": f"<|user|>\n{doc}\n<|assistant|>\nUnderstood. I have adapted my neural pathways accordingly."}
        f.write(json.dumps(entry) + "\n")

print(f"Generated alas_dataset.jsonl with {len(results['documents'])} training samples.")
