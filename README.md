# Loan-MoE: A Neuro-Symbolic Mixture of Experts Architecture for Intelligent Financial Risk Assessment

<div align="center">
  
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![Transformers](https://img.shields.io/badge/🤗_Transformers-4.36%2B-FFD21E?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7.0%2B-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![LINE](https://img.shields.io/badge/LINE_Bot-SDK_3.5-00C300?style=for-the-badge&logo=line&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**A Domain-Specific Large Language Model System for Automated Loan Processing, Verification, and Credit Decisioning with LINE Bot Integration**

</div>

## 📋 Table of Contents

- [Abstract](#-abstract)
- [Introduction](#-introduction)
- [Related Work](#-related-work)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Methodology: The Three Experts](#-methodology-the-three-experts)
- [Gating Network Design](#-gating-network-design)
- [Data Flow & State Management](#-data-flow--state-management)
- [Key Technical Innovations](#-key-technical-innovations)
- [Tech Stack](#-tech-stack)
- [Installation & Setup](#-installation--setup)
- [Usage](#-usage)
- [Evaluation & Benchmarks](#-evaluation--benchmarks)
- [Limitations & Expectation](#-limitations--expectation)
- [Citation](#-citation)
- [License](#-license)

## 📖 Abstract

**Loan-MoE** is a domain-specific Large Language Model (LLM) system designed to automate the end-to-end loan application process. Traditional monolithic models often struggle to balance the diverse requirements of conversational fluency, strict fact-checking, and mathematical risk assessment. Loan-MoE addresses this challenge by leveraging a **Mixture of Experts (MoE)** architecture.

The system decomposes the complex lending workflow into three specialized experts: **LDE (Loan Desk Expert)** for interaction, **DVE (Data Verification Expert)** for fraud detection, and **FRE (Financial Risk Expert)** for credit decisioning. A state-aware **Gating Network** dynamically routes tasks based on user intent and application status, ensuring high precision, interpretability, and safety in financial decision-making.

| Expert | Role | Primary Function |
|--------|------|------------------|
| **LDE** (Loan Desk Expert) | Front-End Interface | Customer interaction & data collection |
| **DVE** (Data Verification Expert) | Auditor | Fraud detection via RAG-based verification |
| **FRE** (Financial Risk Expert) | Decision Maker | Credit scoring & final approval |

A **state-aware Gating Network** dynamically routes tasks based on user intent, verification status, and profile completeness. The architecture employs a **Neuro-Symbolic** paradigm that delegates "hard logic" (financial calculations) to deterministic Python modules while reserving "soft logic" (conversational understanding) for fine-tuned LLMs.

---

## 🎯 Introduction

### Problem Statement

The financial services industry processes millions of loan applications annually, requiring:

1. **Natural Language Understanding** — Parsing unstructured customer inputs
2. **Data Consistency Verification** — Detecting fraudulent or inconsistent information
3. **Quantitative Risk Assessment** — Computing debt ratios and credit scores
4. **Regulatory Compliance** — Ensuring decisions meet legal requirements

Existing approaches fall into two categories, each with critical limitations:

| Approach | Limitation |
|----------|------------|
| **Rule-Based Systems** | Brittle; cannot handle linguistic variation |
| **End-to-End LLMs** | Hallucination-prone; unreliable at arithmetic |

### Solution

Loan-MoE introduces a **hybrid Neuro-Symbolic architecture** that:

- **Specializes** different aspects of the task to dedicated expert modules
- **Routes** dynamically based on application state and user intent
- **Guarantees** mathematical correctness through deterministic computation
- **Enforces** safety constraints via post-inference circuit breakers

### Contributions

1. **Novel MoE Architecture** for financial domain with state-aware routing
2. **Neuro-Symbolic Integration** separating soft reasoning from hard computation
3. **RAG-Enhanced Verification** for fraud detection against historical records
4. **Safety Guard Framework** ensuring regulatory compliance
5. **Open-Source Implementation** with comprehensive test suite

---

## 📚 Related Work

This project bridges the gap between traditional financial credit assessment and modern Large Language Model (LLM) technologies. Our methodology is informed by several key research areas:

### 1. Traditional Credit Risk Assessment
* **Expert Systems**: Early methods relied on rigid, rule-based (If-Then) logic. While highly interpretable, these systems struggle with unstructured data and lack the flexibility required for dynamic conversation.
* **Machine Learning Models**: State-of-the-art tabular models such as **XGBoost, Random Forest, and Gradient Boosting Machines (GBM)** are widely used for structured data (e.g., income, age). However, they are incapable of processing the nuanced semantic information found in credit interview transcripts (phone verification).

### 2. Large Language Models for Finance (FinLLMs)
Recent advancements in domain-specific LLMs have demonstrated superior reasoning in financial contexts:
* **DISC-FinLLM & FinGPT**: These models utilize instruction tuning and reinforcement learning to handle financial consultation and knowledge retrieval.
* **Xuan Yuan (軒轅) & CALM**: These frameworks focus on enhancing logical reasoning for financial decision-making. While they excel at risk assessment, research also highlights the ongoing challenge of mitigating data bias and ensuring fairness in automated lending.

### 3. Retrieval-Augmented Generation (RAG)
To address the "hallucination" problem in LLMs, we incorporate **RAG** techniques. By retrieving historical credit cases and internal banking guidelines, the system can:
* Provide evidence-based responses.
* Reduce factual errors in risk evaluation.
* Enhance transparency for audit purposes.

### 4. Mixture of Experts in NLP

The MoE paradigm, introduced by Jacobs et al. (1991) and recently popularized by Shazeer et al. (2017) in the context of neural networks, enables conditional computation by activating only relevant subnetworks. Recent work includes:

- **GShard** (Lepikhin et al., 2021): Scaling MoE to 600B parameters
- **Switch Transformer** (Fedus et al., 2022): Simplified routing with top-1 selection
- **Mixtral** (Mistral AI, 2024): Open-weight MoE achieving SOTA efficiency

---

## ✨ Key Features

### 🎯 Intelligent Routing
- **State-aware MoE** routes entire conversations (not tokens) to specialized experts
- **Guardrail system** ensures compliance with business rules before AI inference
- **Dynamic expert switching** based on verification status

### 🛡️ Neuro-Symbolic Safety
- **Hard Math Layer**: Deterministic Python for DBR, credit scoring
- **Soft Logic Layer**: Fine-tuned LLMs for qualitative assessment
- **Circuit Breakers**: Post-inference validation prevents unsafe approvals

### 🔍 RAG-Enhanced Verification
- **MongoDB Atlas Vector Search** for historical record retrieval
- **Mismatch detection** compares current input with historical data
- **Risk classification** (LOW/MEDIUM/HIGH) drives routing decisions

### 🔌 Production Ready
- **FastAPI** REST API with OpenAPI documentation
- **LINE Bot** integration with Flex Messages
- **Docker Compose** for easy deployment
- **Redis** session management with TTL

---

## 🏗 System Architecture

The core of Loan-MoE is a **dynamic routing mechanism** that orchestrates specialized experts. The architecture employs a **Neuro-Symbolic** approach, ensuring that "Hard Logic" (financial calculations) and "Soft Logic" (conversational nuances) are handled by appropriate modules.

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LOAN-MOE SYSTEM ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌──────────────────────────────────────────────────┐   │
│  │             │    │              CONVERSATION LAYER                   │   │
│  │    USER     │───▶│  ┌─────────────┐  ┌─────────┐  ┌──────────────┐  │   │
│  │   INPUT     │    │  │   Gemini    │  │  Redis  │  │    Field     │  │   │
│  │             │    │  │   Client    │  │ Session │  │   Schema     │  │   │
│  └─────────────┘    │  └──────┬──────┘  └────┬────┘  └──────┬───────┘  │   │
│                     │         │              │              │          │   │
│                     │         └──────────────┼──────────────┘          │   │
│                     │                        ▼                         │   │
│                     │              ┌─────────────────┐                 │   │
│                     │              │  Conversation   │                 │   │
│                     │              │    Manager      │                 │   │
│                     └──────────────┴────────┬────────┴─────────────────┘   │
│                                             │                              │
│                                             │ profile_state                │
│                                             │ verification_status          │
│                                             ▼                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         MOE ROUTING LAYER                            │  │
│  │                                                                      │  │
│  │   ┌────────────────┐    ┌─────────────────────────────────────┐     │  │
│  │   │    Profile     │    │         GATING NETWORK              │     │  │
│  │   │    Adapter     │───▶│  ┌─────────────────────────────┐   │     │  │
│  │   │                │    │  │   StateFirstGatingModel     │   │     │  │
│  │   │ loan_purpose   │    │  │                             │   │     │  │
│  │   │      ↓         │    │  │  BERT + Structured Features │   │     │  │
│  │   │   purpose      │    │  │         ↓                   │   │     │  │
│  │   └────────────────┘    │  │  Softmax → [LDE, DVE, FRE]  │   │     │  │
│  │                         │  └─────────────────────────────┘   │     │  │
│  │   ┌────────────────┐    │                                    │     │  │
│  │   │  Verification  │    │  ┌─────────────────────────────┐   │     │  │
│  │   │    Status      │───▶│  │      GUARDRAILS             │   │     │  │
│  │   │   Manager      │    │  │  • unknown  → LDE           │   │     │  │
│  │   │                │    │  │  • pending  → DVE           │   │     │  │
│  │   │ unknown/pending│    │  │  • verified → FRE           │   │     │  │
│  │   │ verified/mismatch   │  │  • mismatch → LDE           │   │     │  │
│  │   └────────────────┘    │  └─────────────────────────────┘   │     │  │
│  │                         └─────────────────────────────────────┘     │  │
│  └──────────────────────────────────────────┬───────────────────────────┘  │
│                                             │                              │
│                          ┌──────────────────┼──────────────────┐           │
│                          ▼                  ▼                  ▼           │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                          EXPERT LAYER                                │  │
│  │                                                                      │  │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐     │  │
│  │  │       LDE        │ │       DVE        │ │       FRE        │     │  │
│  │  │  (Loan Desk)     │ │ (Data Verify)    │ │ (Financial Risk) │     │  │
│  │  ├──────────────────┤ ├──────────────────┤ ├──────────────────┤     │  │
│  │  │                  │ │                  │ │                  │     │  │
│  │  │  Mode A: Consult │ │  RAG Engine      │ │  Hard Math Layer │     │  │
│  │  │  ┌────────────┐  │ │  ┌────────────┐  │ │  ┌────────────┐  │     │  │
│  │  │  │ Fine-tuned │  │ │  │  MongoDB   │  │ │  │   Python   │  │     │  │
│  │  │  │   LLaMA    │  │ │  │  Vector    │  │ │  │    DBR     │  │     │  │
│  │  │  └────────────┘  │ │  │  Search    │  │ │  │  Calculator│  │     │  │
│  │  │                  │ │  └────────────┘  │ │  └────────────┘  │     │  │
│  │  │  Mode B: Guide   │ │                  │ │                  │     │  │
│  │  │  ┌────────────┐  │ │  Mismatch        │ │  Soft Logic Layer│     │  │
│  │  │  │  Gemini    │  │ │  Detection       │ │  ┌────────────┐  │     │  │
│  │  │  │   API      │  │ │  ┌────────────┐  │ │  │ Fine-tuned │  │     │  │
│  │  │  └────────────┘  │ │  │ Rule-based │  │ │  │   LLaMA    │  │     │  │
│  │  │                  │ │  │ + AI Model │  │ │  └────────────┘  │     │  │
│  │  │                  │ │  └────────────┘  │ │                  │     │  │
│  │  │                  │ │                  │ │  Safety Guards   │     │  │
│  │  │                  │ │  Risk Labeling   │ │  ┌────────────┐  │     │  │
│  │  │                  │ │  LOW/MEDIUM/HIGH │ │  │  Circuit   │  │     │  │
│  │  │                  │ │                  │ │  │  Breaker   │  │     │  │
│  │  │                  │ │                  │ │  └────────────┘  │     │  │
│  │  └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘     │  │
│  │           │                    │                    │               │  │
│  └───────────┼────────────────────┼────────────────────┼───────────────┘  │
│              │                    │                    │                  │
│              │    ┌───────────────┴───────────────┐    │                  │
│              │    │      TRANSFER_TO_FRE          │    │                  │
│              │    │      FORCE_LDE_CLARIFY        │    │                  │
│              │    └───────────────────────────────┘    │                  │
│              │                                         │                  │
│              ▼                                         ▼                  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         OUTPUT LAYER                                 │  │
│  │                                                                      │  │
│  │   ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐     │  │
│  │   │  CONTINUE   │    │   APPROVED  │    │      REJECTED       │     │  │
│  │   │ COLLECTING  │    │             │    │                     │     │  │
│  │   └─────────────┘    └─────────────┘    └─────────────────────┘     │  │
│  │                                                                      │  │
│  │                      ┌─────────────────────┐                        │  │
│  │                      │   HUMAN_HANDOVER    │                        │  │
│  │                      │   (Escalation)      │                        │  │
│  │                      └─────────────────────┘                        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Interaction Diagram

```
                                    ┌─────────────────┐
                                    │   User Input    │
                                    │  "我叫王小明，   │
                                    │   想借50萬買車"  │
                                    └────────┬────────┘
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                        CONVERSATION MANAGER                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  1. GeminiClient.extract_slots()                                     │  │
│  │     → {"name": "王小明", "amount": 500000, "loan_purpose": "購車"}    │  │
│  │                                                                      │  │
│  │  2. FieldSchema.get_missing_fields()                                 │  │
│  │     → ["id", "phone", "job", "income"]                               │  │
│  │                                                                      │  │
│  │  3. UserSessionManager.update_profile()                              │  │
│  │     → Redis: HSET user:001:profile name "王小明" ...                 │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  if missing_fields.empty():                                                │
│      status = "READY_FOR_MOE"                                              │
│  else:                                                                     │
│      status = "COLLECTING"                                                 │
│      return ask_next_question()                                            │
└────────────────────────────────────────────────────────────────────────────┘
                                             │
                                             │ status == "READY_FOR_MOE"
                                             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                            MOE ROUTER                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  1. ProfileAdapter.adapt(profile)                                    │  │
│  │     → {"name": "王小明", "purpose": "購車", ...}  # 欄位映射           │  │
│  │                                                                      │  │
│  │  2. VerificationStatusManager.infer_status()                         │  │
│  │     → "pending"                                                      │  │
│  │                                                                      │  │
│  │  3. Guardrails.check()                                               │  │
│  │     → pending → DVE (override AI prediction)                         │  │
│  │                                                                      │  │
│  │  4. MoEGateKeeper.predict() [if no guardrail match]                  │  │
│  │     → BERT encoding + structured features → softmax                  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  return (expert="DVE", confidence=0.95, reason="Guardrail: pending→DVE")   │
└────────────────────────────────────────────────────────────────────────────┘
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                           DVE EXPERT                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  1. RAGService.get_user_history_by_id("A123456789")                  │  │
│  │     → [{"hist_job": "工程師", "hist_income": "70000", ...}]          │  │ 
│  │                                                                      │  │
│  │  2. Compare: Current vs Historical                                   │  │
│  │     ┌─────────────────┬─────────────────┬─────────────┐              │  │
│  │     │     Field       │    Current      │  Historical │              │  │
│  │     ├─────────────────┼─────────────────┼─────────────┤              │  │
│  │     │     Job         │    工程師       │    工程師   │  ✓ Match      │  │
│  │     │     Income      │    70,000       │    70,000   │  ✓ Match    │  │
│  │     │     Phone       │  0912-345-678   │ 0912-345-678│  ✓ Match   │  │
│  │     └─────────────────┴─────────────────┴─────────────┘             │  │
│  │                                                                      │  │
│  │  3. Risk Assessment: LOW (0 mismatches)                              │  │
│  │                                                                      │  │
│  │  4. Archive to MongoDB for future verification                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  return {risk_level: "LOW", next_step: "TRANSFER_TO_FRE"}                  │
└────────────────────────────────────────────────────────────────────────────┘
                                             │
                                             │ next_step == "TRANSFER_TO_FRE"
                                             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                           FRE EXPERT                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  ═══════════════════ HARD MATH LAYER (Python) ═══════════════════   │  │
│  │                                                                      │  │
│  │  loan_amount = 500,000                                               │  │
│  │  monthly_income = 70,000                                             │  │
│  │  loan_term = 84 months (7 years)                                     │  │
│  │  interest_rate = 3%                                                  │  │
│  │                                                                      │  │
│  │  monthly_payment = (500,000 × 1.03) / 84 = 6,131                     │  │
│  │  DBR = 6,131 / 70,000 × 100 = 8.76%                                  │  │
│  │  credit_score = 700 (income > 40,000)                                │  │
│  │                                                                      │  │
│  │  ═══════════════════ SOFT LOGIC LAYER (LLM) ════════════════════    │  │
│  │                                                                      │  │
│  │  Fine-tuned LLaMA analyzes:                                          │  │
│  │  • Job stability: "工程師" → Stable                                  │  │
│  │  • DVE risk flag: LOW                                                │  │
│  │  • Purpose reasonability: "購車" → Standard                          │  │
│  │                                                                      │  │
│  │  LLM Decision: "核准_PASS"                                           │  │
│  │                                                                      │  │
│  │  ═══════════════════ SAFETY GUARDS ═════════════════════════════    │  │
│  │                                                                      │  │
│  │  ✓ DBR (8.76%) < 60%  → PASS                                         │  │
│  │  ✓ Credit Score (700) ≥ 650 → PASS                                   │  │
│  │  ✓ Critical data present → PASS                                      │  │
│  │                                                                      │  │
│  │  Final Decision: APPROVED (no override needed)                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  return {decision: "核准_PASS", next_step: "CASE_CLOSED_SUCCESS"}          │
└────────────────────────────────────────────────────────────────────────────┘
                                             │
                                             ▼
                              ┌──────────────────────────┐
                              │   "恭喜！您的信用評分     │
                              │   (700分) 符合標準。     │
                              │   初審額度: 500,000 元"  │
                              └──────────────────────────┘
```

## 🧠 Methodology: The Three Experts

### 1. LDE (Loan Default Expert) - The Front-End Interface
**Role:** Customer Service & Data Collection  
**Mechanism:** Dual-Mode Processing
* **Mode A (Consultation):** Uses a local LLM fine-tuned on financial Q&A to answer general inquiries (e.g., "What is the interest rate for teachers?").
* **Mode B (Guidance):** Uses advanced extraction logic to parse user input into structured JSON profiles (Name, ID, Income, etc.).
* **Objective:** To reduce friction in the application process and ensure profile completeness before risk assessment.

### 2. DVE (Data Verification Expert) - The Auditor
**Role:** Fraud Detection & Consistency Check  
**Mechanism:** RAG-Based Verification & Rule-Based Filtering
* **RAG Integration:** Compares *Current User Input (Query)* against *Historical Records (Context)* retrieved from the vector database.
* **Semantic Matching:** Identifies inconsistencies (e.g., "Freelancer" vs. "Teacher") while tolerating semantic equivalents.
* **Schema Alignment:** Ensures input data strictly matches the training schema to prevent model hallucinations.
* **Output:** Generates a structured **Risk Report** (LOW/MEDIUM/HIGH) with specific mismatch details.

### 3. FRE (Financial Risk Expert) - The Decision Maker
**Role:** Final Credit Approval & Pricing  
**Mechanism:** Neuro-Symbolic Hybrid Architecture
* **Hard Math Layer (Python):** Deterministically calculates DBR (Debt Burden Ratio), available income, and monthly payments. LLMs are notoriously unreliable at arithmetic; this architecture outsources calculation to Python.
* **Soft Logic Layer (LLM):** Analyzes the *qualitative* aspects (Job stability, DVE risk flags) combined with the quantitative metrics.
* **Safety Guards:** A post-inference Python layer acts as a "Circuit Breaker." It overrides the LLM's decision if hard rules are violated (e.g., DBR > 60% MUST Reject), ensuring regulatory compliance.

---

## 🚀 Key Features

* **State-Aware Routing:** The Gatekeeper doesn't just look at keywords; it analyzes `verification_status` and `profile_completeness` to determine the precise next step (e.g., escalating from LDE to DVE).
* **Input Schema Alignment:** Advanced preprocessing ensures that Python-generated JSON inputs strictly match the expert's training data schema, minimizing Out-Of-Distribution (OOD) errors.
* **Streamed Inference:** Real-time token streaming (`TextStreamer`) provides immediate visual feedback, enhancing User Experience (UX) even on resource-constrained hardware.
* **Prompt Injection Defense:** Robust system prompts and output parsing logic prevent users from manipulating the risk scoring engine.

---

## 🛠 Tech Stack

| Category | Technology | Purpose |
|----------|------------|---------|
| **Language** | Python 3.10+ | Core runtime |
| **Deep Learning** | PyTorch 2.0+ | Model training & inference |
| **LLM Framework** | Hugging Face Transformers | Model loading & tokenization |
| **Fine-tuning** | PEFT (LoRA) | Parameter-efficient fine-tuning |
| **Optimization** | Unsloth, bitsandbytes | 4-bit quantization, faster training |
| **Embeddings** | sentence-transformers | Semantic similarity for RAG |
| **LLM API** | Google Gemini | Slot extraction, fallback generation |
| **Vector DB** | MongoDB Atlas | Vector search for RAG |
| **Cache** | Redis | Session state management |
| **Testing** | pytest | Unit, integration, E2E tests |
| **Environment** | Docker, WSL2 | Containerization |

### Model Specifications

| Model | Base | Parameters | Quantization | VRAM |
|-------|------|------------|--------------|------|
| Gating Network | bert-base-chinese | 102M | None | ~400MB |
| LDE Adapter | LLaMA-3.1-8B | 8B (LoRA: 4M) | 4-bit | ~6GB |
| DVE Adapter | LLaMA-3.1-8B | 8B (LoRA: 4M) | 4-bit | ~6GB |
| FRE Adapter | LLaMA-3.1-8B | 8B (LoRA: 4M) | 4-bit | ~6GB |

---

## 💻 Installation & Setup

### Prerequisites
* OS: Linux (Ubuntu 20.04+) or Windows WSL2
* GPU: NVIDIA GPU with CUDA support (Recommended)
* Python: 3.10+

---

## ⚠️ Limitations & Expectation

### Current Limitations

1. **Single Language:** Currently supports Traditional Chinese only
2. **Simplified Credit Model:** Uses heuristic scoring vs. full bureau integration
3. **No Document OCR:** Requires manual data entry (no ID card scanning)
4. **GPU Dependency:** Full functionality requires NVIDIA GPU

### Planned Enhancements

| Feature | Priority | Status |
|---------|----------|--------|
| Multi-language support (EN, ZH-CN) | High | Planned |
| Integration with credit bureaus | High | Planned |
| Document OCR pipeline | Medium | Research |
| Web UI (React + FastAPI) | Medium | In Progress |
| Kubernetes deployment | Low | Planned |
| Model distillation for CPU | Low | Research |

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
