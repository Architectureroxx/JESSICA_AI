import os
import chromadb
from chromadb.utils import embedding_functions

# Ensure the database storage path exists
db_dir = "jarvis_memory"
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

print("[*] Initializing local semantic memory database...")
chroma_client = chromadb.PersistentClient(path=db_dir)

# Using a lightweight, completely local sentence transformer embedding engine
default_ef = embedding_functions.DefaultEmbeddingFunction()
collection = chroma_client.get_or_create_collection(name="jarvis_knowledge", embedding_function=default_ef)

# Add your personal notes, project schedules, or local knowledge base rows here
my_notes = [
    "Archit's current project is upgrading the Mark III JARVIS terminal system with biometric firewalls.",
    "The plant care protocol dictates that plants must be watered every single Monday morning.",
    "Archit successfully completed the Cyber Safe Uttar Pradesh quiz certification.",
    "The internship campus media production project involves documenting laboratory and library architecture."
]

ids = [f"note_{i}" for i in range(len(my_notes))]

print("[*] Vectorizing knowledge fragments and indexing local collection...")
collection.upsert(documents=my_notes, ids=ids)
print("[SUCCESS] Local semantic memory pool active and secured!")