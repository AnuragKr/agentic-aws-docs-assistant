## AWS Documentation Intelligence Assistant

An Agentic AI-powered chatbot that enables users to interact with AWS documentation using natural language queries.

The application leverages Retrieval-Augmented Generation (RAG), hybrid search, and agentic workflows to provide grounded, context-aware responses based on AWS official documentation.

The project is designed as a scalable AWS-native solution demonstrating modern LLM application architecture and clean engineering practices.

## Objectives

The system aims to demonstrate:

+ LLM-based application design
+ Agentic workflow orchestration
+ Retrieval-Augmented Generation (RAG)
+ Natural language query handling
+ AWS documentation integration
+ Scalable and modular architecture

## Scope

The initial version focuses on a text-based conversational experience.

### Included

+ AWS documentation ingestion pipeline
+ Vector indexing and retrieval
+ Hybrid search (semantic + keyword)
+ Query expansion and agentic retrieval workflows
+ Context-aware response generation
+ Citation support
+ Conversational memory
+ AWS-native deployment

### Out of Scope

The following capabilities are intentionally excluded from the MVP:

+ image/table understanding
+ multimodal retrieval
+ voice interaction
+ infrastructure execution
autonomous multi-agent systems

These may be added in future iterations.

## High-Level Workflow

```
User Query
    ↓
Query Understanding
    ↓
Agentic Retrieval Orchestrator
    ↓
Hybrid Retrieval Layer
    ↓
Context Selection & Reranking
    ↓
LLM Generation
    ↓
Grounded Response + Citations

```
