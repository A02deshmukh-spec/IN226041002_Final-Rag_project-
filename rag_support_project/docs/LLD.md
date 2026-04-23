# Deliverable 2: Low-Level Design (LLD)
**Project**: RAG-Based Customer Support Assistant

## 1. Module-Level Design

### Document Processing & Chunking Module
- **Purpose**: Intake unstructured PDFs and prepare normalized text.
- **Process**: Extends `PyPDFLoader` to iterate through pages.
- **Chunking Logic**: Implements `RecursiveCharacterTextSplitter`. Target chunk size is `1000` tokens/characters, with an overlap of `150` characters to maintain contiguous thought across document page breaks.

### Embedding & Vector Storage Module
- **Purpose**: Transform semantically dense chunks into computational floats.
- **Implementation**: Utilizes `GoogleGenerativeAIEmbeddings`.
- **Vector DB**: `Chroma` instance initialized persistently. Contains dynamic insertion loops for large documents preventing API rate constraints.

### Retrieval & Query Processing Module
- **Sequence**: Validates querying texts, sanitizes inputs, and runs `.similarity_search_with_score()` over the Chroma DB. 
- **Filters**: Enforces a cosine-distance threshold (e.g., threshold < 0.2 rejected).

### Graph Execution & HITL Module
- **Engine**: Orchestrated strictly via **LangGraph**.
- **State Object**: Utilizing `TypedDict` to pass context iteratively between Nodes.
- **HITL Integration**: A node strictly configured via LangGraph's `interrupt_before` or `interrupt_after` to force the workflow to suspend execution and request interactive terminal override. 

---

## 2. Data Structures

### Document Representation
```json
{
  "page_content": "Extracted paragraph body detailing return policies.",
  "metadata": {
    "source": "FAQ_Document.pdf",
    "page_number": 3,
    "chunk_id": "ab39cf2"
  }
}
```

### Response \& State Schema
Used by the StateGraph to track context transitions along nodes.
```python
from typing import TypedDict, List
class WorkflowState(TypedDict):
    input_query: str
    intent: str
    retrieved_chunks: List[str]
    generated_answer: str
    needs_escalation: bool
    human_override: str
```

---

## 3. Workflow Design (LangGraph)

### Nodes
- **node_route_intent**: Evaluates the `input_query` string.
- **node_retrieve**: Performs embedding and DB fetch.
- **node_generate**: Uses the LLM to format the `retrieved_chunks` into `generated_answer`.
- **node_hitl**: Pauses execution; waits for human text input to populate `human_override`.

### Edges
- Graph begins at `__start__` → `node_route_intent`
- Depending on the State's `intent` property, a **Conditional Edge** routes either to `node_retrieve` (Standard) or `node_hitl` (Angry/Complex).
- `node_retrieve` → `node_generate`
- A final checking Conditional Edge on `node_generate`. If confidence score is too low → `node_hitl`
- `node_hitl` → `__end__` OR `node_generate` (re-generation with human hint).

---

## 4. Conditional Routing Logic

The **Routing Classifier** utilizes an initial fast LLM prompt (e.g. `gpt-3.5-turbo` or prompt heuristic) to categorize intent:
- **Answer Generation Criteria**: Objective, factual criteria matching predefined keywords (e.g., "refund", "password", "hours").
- **Escalation / Complex Query**: Immediate HITL trigger for sentiments expressing explicit frustration or nuanced, multi-step administrative failures (e.g., "I am suing", "I've tried 4 times to speak with a manager").
- **Missing Context / Low Confidence**: If the ChromaDB fails to return items spanning above the minimum Cosine Similarity constraint, set `needs_escalation = True`.

---

## 5. HITL Design

1. **Triggering Escalation**: The Graph execution encounters an edge routed to the `node_hitl`. 
2. **Interrupt**: Using LangGraph's snapshot state checkpointing, the system pauses execution and yields to the application frontend.
3. **Integration**: The Human Support Agent accesses the `WorkflowState`, reads the `input_query` and the failed `generated_answer` (if applicable), and optionally types a manual response.
4. **Resolution**: The system commits the `human_override` string into the Graph, and resolves the node to Output.

---

## 6. API / Interface Design

### Input Format
```json
{
    "user_id": "u_948",
    "query": "How do I reset my administrator dashboard password?",
    "session_id": "sesh_992"
}
```

### Output Format
```json
{
    "status": "success",
    "response": "To reset your password, navigate to the settings gear and click 'Security'.",
    "escalated": false,
    "confidence": 0.94
}
```

---

## 7. Error Handling

- **Missing Data**: Application raises a specific runtime Warning. ChromaDB initialization catches empty PDF paths locally.
- **No Relevant Chunks Found**: `retrieved_chunks` array evaluates to length 0. Bypasses the Generator node directly to a predefined "We don't have this in our documentation" response or escalating to HITL.
- **LLM Failure**: Built-in retry loops (e.g., Tenacity backoff) covering Rate Limits or 502 Bad Gateway responses from OpenAI's endpoint.
