import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os
load_dotenv()
"""
The point of this file is to create a simple db Connection class for the chroma DB we are using
"""


class chromadbConnector():
    def __init__(self, path, collection):
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.get_collection(collection)
        self.embedding_model =  SentenceTransformer(model_name_or_path=os.environ("EMBED_MODEL"), trust_remote_code=True)


    def get_collection(self,name):
        if name in self.client.list_collections():
            return self.client.get_collection(name)
        else:
            pass
            #return self.client.create_collection(name)

    def perform_vector_search(self, query, n_results):
        embeddings = self.embedding_model.encode([query])
        results = self.collection.query(query_embeddings=embeddings, n_results=n_results)
        return results

    def get_file(self, file_path):
        try:
            with open(file_path, 'r') as file:
                contents = file.read()
            return contents
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
