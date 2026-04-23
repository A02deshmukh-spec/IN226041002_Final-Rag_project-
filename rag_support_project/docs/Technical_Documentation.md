# Deliverable 3: Technical Documentation
**Project**: RAG-Based Customer Support Assistant

## 1. Introduction

### What is RAG?
Retrieval-Augmented Generation (RAG) is a system architecture that pairs arbitrary context searching with large language model prompt engineering. By appending specific data to an LLM runtime window, it strictly bounds the AI to accurate context rather than hallucinating answers from broader, potentially polluted training data.

### Why it is needed
Generative models do not inherently "know" an organization's specific proprietary data configurations (e.g., precise return instructions from a newly amended 2024 policy PDF). RAG systems bridge the gap by letting organizations dynamically alter facts without expensive LLM fine-tuning.

### Use Case Overview
We target automated customer support: a sector heavily bottlenecked by high-volume, low-complexity inquiries.

---

## 2. System Architecture Explanation

The High-Level layout pairs an offline document-ingestion phase with a highly reactive real-time API.
1. Documents are chunked and converted into embeddings stored persistently by **ChromaDB**.
2. When a user sends a string query, **LangGraph** initializes a Stateful Workflow.
3. The Workflow identifies the query's underlying intent, fetching matching semantic text from ChromaDB if needed.
4. The generation node assembles the retrieved context into a friendly answer, handing errors off via interrupt states strictly.

---

## 3. Design Decisions

- **Chunk Size Choice**:
    - **1000 characters** per chunk is utilized alongside a 100-character overlap.
    - *Rationale*: For FAQs and operational manuals, standalone thoughts rarely span multiple pages. 1k characters adequately encapsulate a whole answer concept while preventing token saturation at the Generative LLM level.
- **Embedding Strategy**:
    - `gemini-embedding-2-preview`. Optimized for low-latency batch processing and high retention of semantic hierarchy.
- **Retrieval Approach**:
    - Semantic Search thresholding. We pull $k=3$ nodes. If our distance scoring returns higher than a set error probability threshold, we flag the retriever node state as "Empty".
- **Prompt Design Logic**:
    - Utilizing strict separation between `# CONTEXT:` blocks and `# USER QUERY:` blocks within the system message prompt, ensuring robust prompt-injection immunity and factual rigidness.
- **2-Node Flow Logic**:
    - The system adheres to the required `Input -> Process -> Output` paradigm. Each node represents a discrete phase of this 2-node logical grouping within the StateGraph.

---

## 4. Workflow Explanation (LangGraph Focus)

A StateGraph operates as a Finite State Machine specifically geared towards cyclic NLP routing.
- **Node Responsibilities**: Nodes are discrete python methods accepting a dict, modifying it, and returning modifications. No monolithic codeblocks exist.
- **State Transitions**: Returning `retrieve` from the Router edge inherently forces the execution engine to move the state variable to the Retriever Node. This enforces predictable software limits on the AI.

---

## 5. Conditional Logic

- **Intent Detection**: The router parses strings explicitly. A user complaining: "This service is garbage, let me talk to someone" is caught via semantic sentiment mappings rather than rigid Regex, forcing immediate State Transition away from Generation and towards Human Overrides.

---

## 6. HITL Implementation

- **Role of Human Intervention**: Allows an operator to oversee confused systems. It safeguards AI systems from repeatedly answering complex logistical failures with unhelpful standard protocols.
- **Benefits**: Perfect reliability fallback.
- **Limitations**: Requires asynchronous UX on the front end. Once a State hits HITL, the end user must be notified ("Hold on, transferring to agent..."), and the process hangs waiting indefinitely.

---

## 7. Challenges & Trade-offs

- **Retrieval Accuracy vs. Speed**: Exhaustive vector searching models (k-NN) take significantly longer on large datasets than Hierarchical Navigable Small World (HNSW). We opted for ChromeDB defaults (HNSW approximated bounds) to bias towards sub-50ms query fetch times.
- **Chunk Size vs. Context Quality**: Larger chunks mean the model has better context but suffers from "lost in the middle" syndrome. 1000 characters was identified as our optimal tradeoff constraint.
- **Cost vs. Performance**: Deploying `Gemini-2.5-Flash` provides the reasoning capabilities of a flagship model with the pricing and speed of a lightweight edge model.

---

## 8. Testing Strategy

- **Testing Approach**: 
    - Construct an isolated ChromaDB holding explicit dummy facts (e.g., "The sky is colored purple on Tuesdays"). 
    - Evaluate LLM Generative responses confirming that standard factual queries successfully retrieve augmented data.
- **Sample Queries**:
    - *Standard Query*: "What are your operating hours?" -> Expect standard RAG Retrieval.
    - *Out-of-Bounds Query*: "What is the capital of France?" -> Expect System rejection or polite failure.
    - *HITL Escalation Query*: "I need a manager immediately to cancel my flight." -> Expect LangGraph node termination waiting for human override.

---

## 9. Future Enhancements

- **Multi-document Support**: Implementing Namespaces within vector metadata to filter queries down to specific categories (e.g., Query="HR issue" -> Retrieve only from HR Namespace).
- **Memory Integration**: Attaching `langgraph.checkpoint.memory` to track conversations linearly across a session list.
- **Deployment**: Shifting from local disk Python deployment towards an AWS Lambda function handling incoming REST calls while a persistent Redis stack handles caching operations.
