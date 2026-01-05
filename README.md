# Loan-MoE: Intelligent Financial Risk Assessment System via Mixture of Experts

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-red) ![PEFT](https://img.shields.io/badge/PEFT-LoRA-orange) ![License](https://img.shields.io/badge/License-MIT-green)

> **A Neuro-Symbolic Architecture for Automated Loan Processing, Verification, and Decision Making.**

## 📖 Abstract

**Loan-MoE** is a domain-specific Large Language Model (LLM) system designed to automate the end-to-end loan application process. Traditional monolithic models often struggle to balance the diverse requirements of conversational fluency, strict fact-checking, and mathematical risk assessment. Loan-MoE addresses this challenge by leveraging a **Mixture of Experts (MoE)** architecture.

The system decomposes the complex lending workflow into three specialized experts: **LDE (Loan Default Expert)** for interaction, **DVE (Data Verification Expert)** for fraud detection, and **FRE (Financial Risk Expert)** for credit decisioning. A state-aware **Gating Network** dynamically routes tasks based on user intent and application status, ensuring high precision, interpretability, and safety in financial decision-making.

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
| **Tools** | Git, SourceTree, Google Colab (Training) |

---

## 💻 Installation & Setup

### Prerequisites
* OS: Linux (Ubuntu 20.04+) or Windows WSL2
* GPU: NVIDIA GPU with CUDA support (Recommended)
* Python: 3.10+
