import os
import chromadb
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from chromadb.utils.embedding_functions import GoogleGenerativeAiEmbeddingFunction
from dotenv import load_dotenv


load_dotenv ()

GEMIN_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GEMIN_API_KEY:
    print("error")
    exit 

emeb_fn = GoogleGenerativeAiEmbeddingFunction(
    api_key = GEMIN_API_KEY,
    model_name="models/text-embedding-004"
)

client = chromadb.PersistentClient(path="./chroma_db")

# 3. Create or Get the Collection
# This is the 'shelf' where your data will live
collection = client.get_or_create_collection(
    name="Nutrition_Knowledge", 
    embedding_function=emeb_fn
)

def ingest_pdf ():
    data_path = "./data"
    if not os.path.exists(data_path):
        os.makedirs(data_path)
        print("created '{data_path}' folder..")
        return
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 1000,
        chunk_overlap = 200
    )

    for filename in os.listdir(data_path):
        if filename.endswith(".pdf"):
            print(f"processing : {filename}")
            loader = PyPDFLoader(os.path.join(data_path,filename))
            page = loader.load()


            chunks = text_splitter.split_documents(page)

            documents = [c.page_content for c in chunks]
            metadatas = [{"source": filename, "page": c.metadata['page']} for c in chunks]
            ids = [f"{filename}_{i}" for i in range(len(chunks))]


            collection.add (documents=documents,metadatas=metadatas,ids=ids)
            print(f"Added {len(documents)} chunks from {filename}")            

if __name__ == "__main__":
    ingest_pdf()
    print("Database sync complete. You can now use the App.")