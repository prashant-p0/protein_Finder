import os
import chromadb
# This is the line you are likely missing:
from chromadb.utils import  embedding_functions
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv ()

GEMNI_API_KEY = os.getenv("GOOGLE_API_KEY")

if  GEMNI_API_KEY:
    os.environ["CHROMA_GOOGLE_GENAI_API_KEY"] = GEMNI_API_KEY
else:
    print("Error: GOOGLE_API_KEY not found in .env file")

embed_fn = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
    api_key= GEMNI_API_KEY,
    model_name = "models/text-embedding-004"
)

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(
    name = "Nutrition_Knowledge",
    embedding_function = embed_fn
)

def get_scientific_context(query):
    """
    Finds the top 2 most relevant facts from your uploaded PDFs
    based on the meaning of the user's question.
    """
    result = collection.query(
        query_texts = [query],
        n_results = 2
    )

    return " ".join(result['documents'][0]) if result ['documents'] else ""

def ask_rag_assistant(question):
    """
    The primary function used by app.py to get grounded answers.
    """
    context = get_scientific_context(question)

    if not context:
        return "I haven't been trained on any scientific documents yet. Please run the ingestion script."
    
    
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"""
    You are a professional Nutrition Scientist. 
    Use the provided Scientific Context to answer the User Question.
    
    Scientific Context: 
    {context}
    
    User Question: 
    {question}
    
    Instruction: If the answer is not in the context, say you don't know based on the current database. 
    Keep the answer concise and factual.
    """

    response = model.generate_content(prompt)
    return response.text