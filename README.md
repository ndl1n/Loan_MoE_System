# Loan-MoE: A Neuro-Symbolic Mixture of Experts Architecture for Intelligent Financial Risk Assessment

<div align="center">
  
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![Transformers](https://img.shields.io/badge/🤗_Transformers-4.36%2B-FFD21E?style=for-the-badge)
![PEFT](https://img.shields.io/badge/PEFT-LoRA-FF6F00?style=for-the-badge)
![Redis](https://img.shields.io/badge/Redis-7.0%2B-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**A Domain-Specific Large Language Model System for Automated Loan Processing, Verification, and Credit Decisioning**

</div>

## 📋 Table of Contents

- [Abstract](#-abstract)
- [Introduction](#-introduction)
- [Related Work](#-related-work)
- [System Architecture](#-system-architecture)
- [Methodology: The Three Experts](#-methodology-the-three-experts)
- [Gating Network Design](#-gating-network-design)
- [Data Flow & State Management](#-data-flow--state-management)
- [Key Technical Innovations](#-key-technical-innovations)
- [Tech Stack](#-tech-stack)
- [Installation & Setup](#-installation--setup)
- [Usage](#-usage)
- [Evaluation & Benchmarks](#-evaluation--benchmarks)
- [Limitations & Future Work](#-limitations--future-work)
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

## 🏗 System Architecture

The core of Loan-MoE is a **dynamic routing mechanism** that orchestrates specialized experts. The architecture employs a **Neuro-Symbolic** approach, ensuring that "Hard Logic" (financial calculations) and "Soft Logic" (conversational nuances) are handled by appropriate modules.

### High-Level Workflow
To be edited...

## 🧠 Methodology: The Experts

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

| Category | Technologies |
| :--- | :--- |
| **Core Framework** | Python 3.10, PyTorch |
| **LLM & Fine-tuning** | Hugging Face Transformers, PEFT (LoRA), Unsloth (Optimization) |
| **Architecture** | Mixture of Experts (MoE), RAG (Retrieval-Augmented Generation) |
| **Backend & API** | Flask (Planned), Redis (State Management) |
| **Environment** | Docker, WSL2 (Ubuntu), NVIDIA CUDA |
| **Tools** | Git, SourceTree, Google Colab (Training), Kaggle (Training) |

---

## 💻 Installation & Setup

### Prerequisites
* OS: Linux (Ubuntu 20.04+) or Windows WSL2
* GPU: NVIDIA GPU with CUDA support (Recommended)
* Python: 3.10+

---

## ⚠️ Limitations & Future Work

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
