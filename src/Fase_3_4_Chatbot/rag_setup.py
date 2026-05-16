import os
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Configuration
RAG_DIR = r"C:\Users\Luis\Downloads\TFG\RAG"
CHROMA_DB_DIR = r"C:\Users\Luis\Downloads\TFG\Chatbot\chroma_db"

def build_vector_database():
    print(f"Looking for PDF documents in: {RAG_DIR}")
    if not os.path.exists(RAG_DIR):
        print(f"Error: Directory {RAG_DIR} does not exist.")
        return

    # Load PDFs
    loader = PyPDFDirectoryLoader(RAG_DIR)
    documents = loader.load()
    
    if not documents:
        print("No PDF documents found in the directory.")
        return
        
    print(f"Loaded {len(documents)} pages. Processing text...")

    # Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    docs = text_splitter.split_documents(documents)
    print(f"Split documents into {len(docs)} text chunks.")

    # Initialize Embeddings
    print("Generating Embeddings locally with HuggingFace and saving to ChromaDB...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Store in Chroma
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=CHROMA_DB_DIR
    )
    
    vectorstore.persist()
    print(f"Vector database successfully created at {CHROMA_DB_DIR}!")

if __name__ == "__main__":
    # Ensure GOOGLE_API_KEY is set in environment before running
    build_vector_database()
