import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()

# Define project root relative to this script (src/ingest.py)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def ingest_pdf(pdf_path=None, persist_dir=None):
    if pdf_path is None:
        pdf_path = os.path.join(PROJECT_ROOT, "faq.pdf")
    if persist_dir is None:
        persist_dir = os.path.join(PROJECT_ROOT, "chroma_db")
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found. Please run create_dummy_pdf.py first.")
        return

    print(f"Loading {pdf_path}...")
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()

    print("Splitting text into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    splits = text_splitter.split_documents(docs)

    print(f"Generated {len(splits)} chunks. Compiling into ChromaDB...")
    
    if not os.environ.get("GOOGLE_API_KEY"):
        print("WARNING: GOOGLE_API_KEY not found in environment. The embedding process requires it.")
        print("Please create a .env file with GOOGLE_API_KEY=your-key in the root directory.")
        return

    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2-preview")
        vectorstore = Chroma(embedding_function=embeddings, persist_directory=persist_dir)
        for split in splits:
            vectorstore.add_documents([split])
        print("Ingestion complete. Vector database created at:", persist_dir)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Database ingestion failed due to: {e}")

if __name__ == "__main__":
    ingest_pdf()
