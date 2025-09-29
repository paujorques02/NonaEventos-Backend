from sentence_transformers import SentenceTransformer
import numpy as np
import firebase_admin
from firebase_admin import credentials, firestore

class EmbeddingsManager:
    def __init__(self, firebase_credentials_path):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.firestore_client = self.initialize_firestore(firebase_credentials_path)

    def initialize_firestore(self, firebase_credentials_path):
        cred = credentials.Certificate(firebase_credentials_path)
        firebase_admin.initialize_app(cred)
        return firestore.client()

    def create_embeddings(self, documents):
        embeddings = self.model.encode(documents)
        return embeddings

    def store_embeddings(self, embeddings, document_ids):
        db = self.firestore_client
        for doc_id, embedding in zip(document_ids, embeddings):
            db.collection('embeddings').document(doc_id).set({
                'embedding': embedding.tolist()
            })

    def retrieve_embedding(self, document_id):
        db = self.firestore_client
        doc_ref = db.collection('embeddings').document(document_id)
        doc = doc_ref.get()
        if doc.exists:
            return np.array(doc.to_dict()['embedding'])
        else:
            return None

    def search_similar_documents(self, query, top_k=5):
        query_embedding = self.model.encode([query])[0]
        all_embeddings = self.retrieve_all_embeddings()
        similarities = np.dot(all_embeddings, query_embedding)
        top_k_indices = np.argsort(similarities)[-top_k:][::-1]
        return top_k_indices

    def retrieve_all_embeddings(self):
        db = self.firestore_client
        embeddings = []
        docs = db.collection('embeddings').stream()
        for doc in docs:
            embeddings.append(np.array(doc.to_dict()['embedding']))
        return np.array(embeddings)