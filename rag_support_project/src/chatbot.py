import os
from typing import TypedDict, List, Literal
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

load_dotenv()

# 1. Define State
class GraphState(TypedDict):
    """
    Represents the state of our graph workflow.
    """
    question: str
    intent: str
    documents: List[str]
    generation: str
    hitl_response: str

# 2. Vector DB Helper
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_retriever():
    persist_dir = os.path.join(PROJECT_ROOT, "chroma_db")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2-preview")
    vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
    return vectorstore.as_retriever(search_kwargs={"k": 3})

# 3. Node Functions
def intent_router_node(state: GraphState):
    """Evaluates the user's intent. Routes to HITL if angry or complex."""
    print("...[Node] Routing Intent...")
    question = state["question"].lower()
    
    # A heuristic-based routing. In production, this can be an LLM classification call.
    escalation_keywords = ["manager", "sue", "angry", "human", "representative", "emergency", "stuck"]
    
    intent = "retrieve"
    if any(word in question for word in escalation_keywords):
        intent = "escalate"
    
    return {"intent": intent}

def retrieve_node(state: GraphState):
    """Queries ChromaDB for chunks matching the question."""
    print("...[Node] Retrieving Context from DB...")
    question = state["question"]
    retriever = get_retriever()
    docs = retriever.invoke(question)
    
    str_docs = [d.page_content for d in docs]
    return {"documents": str_docs}

def generate_node(state: GraphState):
    """Formats the answer using retrieved context and an LLM."""
    print("...[Node] Generating Output...")
    question = state["question"]
    documents = state.get("documents", [])
    hitl_response = state.get("hitl_response", None)

    # If the human agent injected an override, bypass the LLM generation entirely.
    if hitl_response:
        print("...[Node] Using Human Override.")
        return {"generation": hitl_response}

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    context = "\n\n".join(documents) if documents else "No context found."
    
    prompt = PromptTemplate(
        template="""You are an expert customer support agent.
        Answer the following user question factually using ONLY the provided context. 
        If the context does not contain the answer, reply strictly with: "I don't know the answer to that."
        
        # CONTEXT:
        {context}
        
        # USER QUESTION:
        {question}
        
        Answer:""",
        input_variables=["question", "context"],
    )
    
    chain = prompt | llm
    res = chain.invoke({"question": question, "context": context})
    return {"generation": res.content}

def hitl_node(state: GraphState):
    """Intercept Node. LangGraph pauses execution right before this."""
    print("...[Node] Escalated to Human Support.")
    # Execution pauses here waiting for manual update.
    return state

# 4. Conditional Edge Checking
def route_after_intent(state: GraphState) -> Literal["retrieve_node", "hitl_node"]:
    if state["intent"] == "escalate":
        return "hitl_node"
    return "retrieve_node"

def check_confidence(state: GraphState) -> Literal["hitl_node", "__end__"]:
    # If the LLM failed to answer, escalate to human automatically
    if "I don't know the answer" in state.get("generation", ""):
        return "hitl_node"
    return "__end__"

# 5. Build and Compile the Graph
def build_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node("intent_router_node", intent_router_node)
    workflow.add_node("retrieve_node", retrieve_node)
    workflow.add_node("generate_node", generate_node)
    workflow.add_node("hitl_node", hitl_node)

    # Flow Engine
    workflow.add_edge(START, "intent_router_node")
    
    workflow.add_conditional_edges(
        "intent_router_node",
        route_after_intent,
        {
            "retrieve_node": "retrieve_node",
            "hitl_node": "hitl_node"
        }
    )
    
    workflow.add_edge("retrieve_node", "generate_node")
    
    workflow.add_conditional_edges(
        "generate_node",
        check_confidence,
        {
            "hitl_node": "hitl_node",
            "__end__": END
        }
    )
    
    # If a human intervenes, loop back to generation so it can output the override
    workflow.add_edge("hitl_node", "generate_node")
    
    # A checkpointer is mandatory for interrupt states
    memory = MemorySaver()
    # Interrupt *before* executing the hitl_node to allow state modifications
    app = workflow.compile(checkpointer=memory, interrupt_before=["hitl_node"])
    
    return app
