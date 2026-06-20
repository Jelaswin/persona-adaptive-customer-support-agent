# AdSparkX Persona-Adaptive Customer Support System

A production-quality AI-powered customer support system that detects user personas, retrieves relevant documentation via RAG, and generates persona-tailored responses using Google Gemini and ChromaDB.

## Problem Statement

Customer support teams handle diverse users with different needs, technical expertise, and emotional states. A one-size-fits-all response frustrates technical users who want details, overwhelms frustrated users who need empathy, and bores executives who need brevity. This system solves that by:

- **Detecting the user's persona** in real-time from their query text
- **Tailoring responses** to match each persona's communication preferences
- **Escalating intelligently** when issues are sensitive or confidence is low
- **Generating structured handoff summaries** for human agents when escalation is needed

## Features

- **Persona Classification**: Detects whether a user is a Technical Expert, Frustrated User, or Business Executive using keyword analysis and sentiment detection.
- **RAG Pipeline**: Loads support documents (TXT, MD, PDF), chunks them, generates embeddings via Sentence Transformers (`all-MiniLM-L6-v2`), and stores them in ChromaDB for efficient retrieval.
- **Adaptive Response Generation**: Generates responses tailored to each persona:
  - *Technical Expert* → detailed technical explanations with code snippets and API references.
  - *Frustrated User* → empathetic, simple, action-oriented guidance.
  - *Business Executive* → concise, impact-focused summaries with ROI and timeline.
- **Escalation Engine**: Automatically escalates when:
  - Retrieval confidence is low (< 40%)
  - Billing issues, refund requests, legal concerns, or account-sensitive requests are detected
  - Repeated user frustration is identified
- **Human Handoff Summaries**: Generates structured handoff documents with full context for support agents.
- **Conversation Memory**: Maintains session-level chat history for context-aware responses.
- **Sentiment Detection**: Analyzes user sentiment (positive, negative, neutral) to inform persona classification and escalation.
- **Analytics Dashboard**: Tracks total queries, escalations, and persona distribution per session.

## Architecture

```
User Query
    │
    ▼
┌─────────────────────┐
│  Persona Classifier │  ← Keyword analysis + sentiment detection
│  (classifier.py)    │
└─────────┬───────────┘
          │ persona + confidence
          ▼
┌─────────────────────┐
│   RAG Pipeline      │  ← ChromaDB retrieval (top-k chunks)
│  (rag_pipeline.py)  │
└─────────┬───────────┘
          │ retrieved chunks + metadata
          ▼
┌─────────────────────┐
│  Response Generator │  ← Persona-adaptive prompt → Gemini API
│   (generator.py)    │
└─────────┬───────────┘
          │ generated response
          ▼
┌─────────────────────┐
│  Escalation Engine  │  ← Rule-based + confidence-based check
│   (escalator.py)    │
└─────────┬───────────┘
          │ escalate? → handoff summary
          ▼
┌─────────────────────┐
│   Streamlit UI      │  ← Display query, persona, sources,
│     (app.py)        │     response, escalation, handoff
└─────────────────────┘
```

## Project Structure

```
persona_adaptive_customer_service/
├── src/
│   ├── __init__.py          # Package marker
│   ├── config.py            # Settings, env vars, logging
│   ├── classifier.py        # Persona classification + sentiment
│   ├── rag_pipeline.py      # Document loading, embedding, retrieval
│   ├── generator.py         # Persona-adaptive Gemini prompt/response
│   ├── escalator.py         # Escalation logic + handoff + analytics
│   └── app.py               # Streamlit UI (main entry point)
├── knowledge_base/
│   ├── password_reset.md
│   ├── login_issues.md
│   ├── api_authentication.txt
│   ├── payment_failures.md
│   ├── subscription_upgrades.md
│   ├── refund_policy.md
│   ├── billing_disputes.md
│   ├── account_lockouts.md
│   ├── email_verification.md
│   ├── two_factor_auth.md
│   ├── service_outages.md
│   ├── database_integration.md
│   ├── api_rate_limits.md
│   ├── user_onboarding.md
│   ├── security_best_practices.md
│   └── refund_policy.pdf
├── chroma_db/               # Created at runtime (gitignored)
├── .gitignore
├── requirements.txt
├── .env.example
└── README.md
```

## Tech Stack

| Component            | Technology                          |
|----------------------|-------------------------------------|
| Programming Language | Python 3.11+                        |
| LLM Provider         | Google Gemini 1.5 Flash             |
| Embedding Model      | Sentence Transformers (all-MiniLM-L6-v2) |
| Vector Database      | ChromaDB (persistent)               |
| Frontend             | Streamlit                           |
| Text Splitting       | LangChain RecursiveCharacter        |
| PDF Parsing          | pypdf                               |
| Configuration        | python-dotenv (.env)                |

## Setup Instructions

### Prerequisites

- Python 3.11+
- A Google Gemini API key ([get one free](https://aistudio.google.com/app/apikey))

### Local Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd persona_adaptive_customer_service
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate    # Linux/Mac
   .\venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set your `GEMINI_API_KEY`.

5. **Run the application**:
   ```bash
   streamlit run src/app.py
   ```

6. **Open in browser**: Navigate to http://localhost:8501

   > **First run**: The Sentence Transformers model (`all-MiniLM-L6-v2`, ~80 MB) will download automatically. ChromaDB will create the `chroma_db/` directory and index all 15+ knowledge base documents into 61 chunks.

## Deployment

### Streamlit Cloud (Recommended)

1. Push the repository to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-repo-url>
   git push -u origin main
   ```
2. Log in to [share.streamlit.io](https://share.streamlit.io).
3. Click "New app" → select your repository.
4. Set main file path: `src/app.py`.
5. In **Secrets** → add:
   ```toml
   GEMINI_API_KEY = "your_gemini_api_key_here"
   ```
6. Click "Deploy".

### Render

1. Push the repository to GitHub.
2. Log in to [render.com](https://render.com).
3. Click "New" → "Web Service".
4. Connect your repository.
5. Configure:
   - **Runtime**: Python 3.11
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run src/app.py --server.port $PORT`
   - **Environment Variables**: Add `GEMINI_API_KEY`
6. Click "Create Web Service".

> **Note**: On ephemeral storage (Render free tier), the ChromaDB index will not persist across restarts. The knowledge base will re-index on each cold start. This is acceptable for the assignment; for production, mount a persistent volume or use ChromaDB Cloud.

## Usage

Type a support query in the chat input. The system will:
1. Detect your persona and confidence.
2. Retrieve relevant documents from the knowledge base.
3. Generate a persona-adaptive response.
4. Check if escalation is needed.
5. Display everything in the Streamlit UI.

## Demo Test Queries

### Technical Expert
1. "How do I authenticate with the AdSparkX API using OAuth 2.0 client credentials?"
2. "What are the rate limits for the Pro plan and how should I implement exponential backoff?"
3. "I'm getting a 401 error on my API calls. What could be wrong with my token?"

### Frustrated User
4. "Where is the password reset page? I've been trying for an hour and nothing is working!"
5. "I was charged twice this month and no one is helping me fix it. This is unacceptable!"
6. "The password reset email keeps failing and I'm locked out AGAIN. Fix this now!"

### Business Executive
7. "What's the ROI of upgrading to the Enterprise plan and what's the implementation timeline?"
8. "Our team needs a summary of the recent service outage and its business impact."
9. "How does the Pro plan support SLA compare to the Free tier?"

### Escalation Triggers
10. "I need a refund for my annual subscription. What's the process?"

## Confidence Scoring

- **Persona Confidence (0.0 – 1.0)**: Each keyword match contributes 0.15, capped at 1.0. Pattern-based matches contribute 0.20 each. Sentiment analysis provides a 40% boost for negative sentiment above 0.3 threshold. The persona with the highest score is selected; a minimum confidence floor of 0.1 ensures no query goes unclassified (defaults to Frustrated User).
- **Retrieval Confidence (0.0 – 1.0)**: Computed as `1.0 - cosine_distance` from ChromaDB results. Higher values indicate stronger semantic similarity between query and retrieved document chunks.
- **Escalation Threshold**: Retrieval confidence < 0.40 triggers automatic low-confidence escalation.

## Screenshots

<!-- Add screenshots here after running the application:
    1. Main chat interface with a Technical Expert response
    2. Frustrated User response with escalation warning
    3. Business Executive concise response
    4. Human Handoff Summary expanded view
-->

(Screenshots to be added after deployment)

## Future Improvements

- **LLM-based classifier**: Replace keyword matching with Gemini classification for higher accuracy
- **Reranking**: Add cross-encoder reranking (e.g., Cohere Rerank) after initial ChromaDB retrieval
- **Streaming responses**: Implement token-by-token streaming in the Streamlit UI
- **User feedback**: Add thumbs-up/thumbs-down buttons to collect training data
- **Multi-language**: Support queries in languages other than English
- **Persistent ChromaDB**: Use ChromaDB Cloud or a mounted volume for production persistence
- **A/B testing**: Framework for testing prompt variants and measuring response quality
- **Admin dashboard**: Separate view for monitoring analytics, reviewing escalations, and managing the knowledge base
- **CI/CD pipeline**: Automated testing and deployment via GitHub Actions

## License

MIT — see LICENSE file for details.
