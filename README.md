## AWS Documentation Agent Assistant

An intelligent AWS Documentation Assistant that combines Retrieval-Augmented Generation (RAG), Agentic Reasoning, AWS Bedrock, OpenSearch, and conversational memory to provide accurate, source-grounded answers from AWS documentation.

The assistant supports:

+ Conversational chat experience
+ AWS-only domain expertise
+ Context-aware follow-up questions
+ Query rewriting and expansion
+ Semantic retrieval using OpenSearch
+ Cross-encoder reranking
+ Conditional web search fallback
+ Source-grounded responses
+ Infrastructure-as-Code provisioning with Terraform

---

## Table of Contents

1. Solution Overview
2. Solution Architecture
3. Infrastructure Architecture
4. Agentic Workflow
5. RAG Pipeline
6. Technology Stack
7. Project Structure
8. Infrastructure Provisioning
9. Local Setup
10. Deployment Guide
11. Usage Examples
12. Design Decisions & Trade-offs
13. Assumptions
15. Future Enhancements
16. Solution Overview

---
## Solution Overview

The AWS Documentation Assistant enables users to interact with AWS documentation through natural language.

Instead of keyword search, the system:

1. Understands user intent
2. Rewrites ambiguous follow-up questions
3. Retrieves relevant AWS documentation
4. Reranks results for relevance
5. Generates grounded responses using Amazon Bedrock
6. Returns citations for transparency

The solution follows an Agentic RAG architecture where retrieval and reasoning are orchestrated through a lightweight LangGraph workflow.

---

## Solution Architecture

```bash
┌──────────────────────┐
│      Streamlit UI    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│      FastAPI API     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────┐
│      LangGraph Agent         │
└──────────┬───────────────────┘
           │
           ▼
 ┌─────────────────────────┐
 │ Intent Classification   │
 └──────────┬──────────────┘
            │
            ▼
 ┌─────────────────────────┐
 │ Query Rewriting         │
 └──────────┬──────────────┘
            │
            ▼
 ┌─────────────────────────┐
 │ Query Expansion         │
 └──────────┬──────────────┘
            │
            ▼
 ┌─────────────────────────┐
 │ OpenSearch Retrieval    │
 └──────────┬──────────────┘
            │
            ▼
 ┌─────────────────────────┐
 │ Cross Encoder Reranker  │
 └──────────┬──────────────┘
            │
            ▼
 ┌─────────────────────────┐
 │ Tool Decision Node      │
 └──────────┬──────────────┘
            │
            ▼
      Tavily Search
          (Optional)
            │
            ▼
 ┌─────────────────────────┐
 │ Claude Sonnet           │
 │ Generation              │
 └──────────┬──────────────┘
            │
            ▼
       Final Response
```
---

## Infrastructure Architecture
<img width="921" height="711" alt="infra drawio" src="https://github.com/user-attachments/assets/ab46146e-c75b-453d-861c-608dea54ddfa" />

---

## Application Architecture

<img width="3796" height="5784" alt="diagram" src="https://github.com/user-attachments/assets/8817cdbd-d7cf-44cb-b1d9-1e098e64df4f" />

---

## Agentic Workflow

The application implements a lightweight agentic workflow.

Step 1: Domain Validation

Validate whether the question belongs to AWS.

Example:

```bash
What is Amazon S3?
```

Allowed.

```
What is the capital of France?
```

Rejected.

***

Step 2: Query Rewriting

Resolve conversational references.

Example:

```bash
User:
What is Amazon S3?

User:
How is it different from EFS?
```

Rewritten to:

```
How does Amazon S3 differ from Amazon EFS?
```
---

Step 3: Query Expansion

Generate AWS-specific search variations.

Example:

```bash
Secure S3
```

Expanded into:

```
Amazon S3 security
S3 bucket policy
S3 encryption
S3 access control
```
---

Step 4: Retrieval
Retrieve Top 20 semantic matches from OpenSearch.

---

Step 5: Reranking

Cross Encoder reranks retrieved chunks.

Model:

```bash
BAAI/bge-reranker-base
```
Top 20 → Top 5

---

Step 6: Tool Decision

If retrieved evidence is insufficient:

```
Invoke Tavily
```
Otherwise:
```bash
Use internal AWS documentation only
```
---

Step 7: Generation

Generate grounded answer using Bedrock.

Model:
```bash
anthropic.claude-3-sonnet-20240229-v1:0
```
---

## RAG Architecture

Ingestion Pipeline

```bash
AWS PDF Documents
        │
        ▼
PyMuPDF Parsing
        │
        ▼
Metadata Extraction
        │
        ▼
     Chunking
        │
        ▼
     Embeddings
        │
        ▼
    OpenSearch Index
```
---

## Chunking Strategy
Chunk Size
```bash
1000 Tokens
```

Overlap
```
125 Tokens
```

Chunking Rules
+ Preserve section boundaries
+ Avoid splitting sentences
+ Maintain semantic coherence
+ Retain document metadata

---

Embedding Model

```bash
sentence-transformers/all-MiniLM-L6-v2
```

Dimension:
```bash
384
```
---

## Vector Store

Amazon OpenSearch

Features:

+ KNN Search
+ Semantic Retrieval
+ Metadata Filtering
+ AWS SigV4 Authentication
---

## Infrastructure Provisioning

Infrastructure is provisioned entirely through Terraform.

Resources Created

Networking

+ VPC
+ Public Subnet
+ Internet Gateway
+ Route Tables
+ Security Groups

Compute
+ EC2 Instance

Storage
+ S3 Bucket
+ DynamoDB Table

Search
+ OpenSearch Domain
  
IAM
+ EC2 IAM Role
+ Instance Profile
+ Least Privilege Policies

---

## Local Setup
```bash
git clone <repo>

cd agentic-aws-docs-assistant
```

Create environment file:

```bash
cp backend/.env.example backend/.env
```

Start application:

```bash
docker compose \
-f docker-compose.yml \
up -d --build
```
---

## Deployment Guide

Provision Infrastructure
```
cd terraform

terraform init

terraform plan

terraform apply
```

SSH into EC2
```bash
ssh -i key.pem ubuntu@<ec2-ip>
```

Deploy Application
```
git clone <repo>

docker compose up -d --build
```

Usage Examples
Explanation
```bash
What is Amazon S3?
```
Comparison
```
How does Amazon S3 compare with Amazon EFS?
```

Best Practices
```bash
How should I secure an S3 bucket?
```

Conversational Follow-up
```bash
What is Amazon Bedrock?

How does it differ from SageMaker?
```
---

## Design Decisions and Trade-offs

| Decision| Reason |
| ------ | ----------- |
| OpenSearch  | Managed vector database on AWS|
|  Bedrock | Managed foundation model access |
| Claude | Sonnet	Strong reasoning and summarization |
| Cross Encoder | Reranking	Improved retrieval precision|
| LangGraph |	Lightweight orchestration|
| Tavily Fallback |	Handles missing or recent information|
| DynamoDB| Chat Memory	Supports conversational context|
---
## Assumptions

+ AWS documentation is primary source of truth.
+ Users ask AWS-related questions.
+ OpenSearch remains the primary retrieval mechanism.
+ Tavily is only used when internal documentation is insufficient.
+ Chat history is retained for session continuity.

---
## Future Enhancements

+ Hybrid Search (BM25 + Vector Search)
+ Bedrock Knowledge Bases Integration
+ Multi-document ingestion automation
+ Evaluation framework (RAGAS)
+ Guardrails for content moderation
+ Feedback collection and answer quality scoring
+ Multi-region deployment
+ CI/CD using GitHub Actions

---

## Screenshot

<img width="1884" height="979" alt="Screenshot 2026-06-01 at 2 28 49 AM" src="https://github.com/user-attachments/assets/299c4c4f-e653-458d-a881-5912cffb34f0" />

<img width="1868" height="923" alt="Screenshot 2026-06-01 at 2 30 18 AM" src="https://github.com/user-attachments/assets/275a5561-a589-446f-a21a-194ffed9795e" />


