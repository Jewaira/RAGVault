from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_aws import BedrockEmbeddings,ChatBedrock 
from datetime import datetime
import boto3
import os
import uuid
from chromadb.config import Settings



load_dotenv()

bedrock_client = boto3.client(service_name="bedrock-runtime", region_name="us-east-1")

embeddings_model = BedrockEmbeddings(client=bedrock_client, model_id="amazon.titan-embed-text-v2:0")

llm = ChatBedrock(
    model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    client=bedrock_client,
    provider="anthropic",
    model_kwargs={"temperature": 0.0},
)
chroma_path="./chroma_db"  
file_path="System_design.pdf"    


def load_documents(file_path:str):
    """
    Load documwnts from the specified file path using the pdfLoader.
    Args:
    file_path(str): The path to the file containing the documents to load.
    returns:
    List: A list of documents loaded from the specified file path using the PdfLoader."""
    loader=PyPDFLoader(file_path)
    return loader.load()

def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    return splitter.split_documents(documents)

def create_or_load_vectorstore(docs):
    client_settings = Settings(anonymized_telemetry=False)
    if os.path.exists(chroma_path):
        return Chroma(
            persist_directory=chroma_path,
            embedding_function=embeddings_model,
            client_settings=client_settings
        )

    vectorstore = Chroma.from_documents(
        docs,
        embedding=embeddings_model,
        persist_directory=chroma_path,
        client_settings=client_settings
    )
    vectorstore.persist()
    return vectorstore


async def store_chat_history(query:str,response:str,vectorstore,session_id:str):
    """stores the chat history of the session in the chroma database the user query,the response from the model and the timestamp of the query."""
    doc_id = str(uuid.uuid4())
    document=Document(
        page_content=query,
        metadata={
            "session_id":session_id,
            "query":query,
            "response":response,
            "timestamp":datetime.utcnow().isoformat()
        }
    )
    vectorstore.add_documents([document], ids=[str(doc_id)])
    vectorstore.persist()
    return doc_id

async def retrieve_session(session_id: str, vectorstore):
    # Use the where clause to filter at the DB level instead of loading everything
    results = vectorstore.get(where={"session_id": session_id})

    if not results or not results.get("metadatas"):
        return []

    session_data = []

    for meta in results["metadatas"]:
        session_data.append({
            "query": meta.get("query"),
            "response": meta.get("response"),
            "timestamp": meta.get("timestamp"),
        })

    # sort by time (important!)
    session_data.sort(key=lambda x: x.get("timestamp", ""))

    return session_data


def main():
    vectorstore, qa_chain = init_rag("System_design.pdf")
    session_id = str(uuid.uuid4())
    print("Session ID:", session_id)

    while True:
        user_input = input("\n>> ")

        if user_input.lower() == "exit":
            break
        if user_input.startswith("session "):
            sid = user_input.split(" ")[1]
            history = retrieve_session(sid, vectorstore)

            if not history:
                print("No session found")
            else:
                print("\n Full Chat History:\n")
                for item in history:
                    print("Q:", item["query"])
                    print("A:", item["response"])

            continue

        answer = query_rag(user_input, qa_chain)

        store_chat_history(user_input, answer, vectorstore, session_id)

        print("\nAnswer:", answer)

def create_qa_chain(vectorstore):
    # Notice: NO 'async' on this outer function
    retriever = vectorstore.as_retriever()

    async def rag_pipeline(question: str):
        # Notice: 'async' IS on this inner function
        
        # Using aget_relevant_documents for proper async behavior
        docs = await retriever.aget_relevant_documents(question) 
        context = "\n".join([doc.page_content for doc in docs])

        prompt = f"""
        Answer the question based on context below:

        {context}

        Question: {question}
        """

        # Using ainvoke for proper async behavior
        response = await llm.ainvoke(prompt)
        return response.content

    # We return the function itself, without parentheses
    return rag_pipeline


async def query_rag(question: str, qa_chain):
    # Since qa_chain is now the rag_pipeline function, we await it
    response = await qa_chain(question)
    return response


def init_rag(file_path: str):
    documents = load_documents(file_path)
    split_docs = split_documents(documents)
    vectorstore = create_or_load_vectorstore(split_docs)
    
    # This now safely returns the async function, NOT a coroutine
    qa_chain = create_qa_chain(vectorstore) 

    return vectorstore, qa_chain








