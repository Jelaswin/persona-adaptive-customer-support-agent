import logging
from typing import List, Dict, Any

from google import genai
from google.genai import types

from src.config import settings

logger = logging.getLogger(__name__)

PERSONA_PROMPTS = {
    "Technical Expert": (
        "You are a senior technical support engineer. "
        "The user is a **Technical Expert** \u2014 they want precise, detailed, technically accurate answers. "
        "Include relevant technical details such as API endpoints, configuration snippets, status codes, "
        "protocols, authentication methods, and best practices where appropriate. "
        "Use structured formatting with code blocks, bullet points, and clear technical terminology. "
        "Assume the user is comfortable with technical jargon."
    ),
    "Frustrated User": (
        "You are a compassionate and patient customer support representative. "
        "The user is **frustrated** \u2014 they need empathy, reassurance, and clear step-by-step guidance. "
        "Start by acknowledging their frustration and apologizing for the inconvenience. "
        "Keep explanations simple, warm, and action-oriented. "
        "Avoid technical jargon. Use short sentences and clear steps. "
        "Do NOT be defensive. Validate their feelings and focus on solutions. "
        "If they are upset, offer to escalate if the issue persists."
    ),
    "Business Executive": (
        "You are a strategic account manager reporting to an executive. "
        "The user is a **Business Executive** \u2014 they need concise, impact-focused answers. "
        "Highlight business value, ROI, timelines, and high-level outcomes. "
        "Avoid technical implementation details. Focus on what matters for decision-making: "
        "cost, time, resources, risks, and next steps. "
        "Be direct, professional, and efficient. Use bullet points when helpful. "
        "Provide a clear summary of the situation and recommended actions."
    ),
}

SYSTEM_CONTEXT = (
    "You are part of a customer support system for a SaaS platform called AdSparkX. "
    "Your role is to answer user questions based ONLY on the retrieved support documents provided below. "
    "If the retrieved documents do not contain enough information to fully answer, "
    "say so honestly and offer to escalate. Do NOT make up information."
)


def build_prompt(
    persona: str,
    query: str,
    retrieved_chunks: List[Dict],
    conversation_history: List[Dict] = None,
) -> str:
    persona_instruction = PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS["Technical Expert"])

    context_sections = []
    for i, chunk in enumerate(retrieved_chunks):
        source = chunk.get("source", "unknown")
        content = chunk.get("content", "")
        confidence = chunk.get("confidence", 0)
        context_sections.append(
            f"[Source {i+1}: {source} (relevance: {confidence:.2f})]\n{content}"
        )

    context_block = "\n\n---\n\n".join(context_sections) if context_sections else "No relevant documents found."

    history_block = ""
    if conversation_history:
        lines = []
        for turn in conversation_history[-settings.MAX_CONVERSATION_HISTORY:]:
            lines.append(f"User: {turn.get('query', '')}")
            lines.append(f"Assistant: {turn.get('response', '')}")
        history_block = "Previous conversation:\n" + "\n".join(lines) + "\n\n"

    prompt = (
        f"{SYSTEM_CONTEXT}\n\n"
        f"{persona_instruction}\n\n"
        f"---\n"
        f"Retrieved Support Documents:\n"
        f"{context_block}\n"
        f"---\n\n"
        f"{history_block}"
        f"User Query: {query}\n\n"
        f"Response:"
    )

    return prompt


class ResponseGenerator:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_CHAT_MODEL
        self.generation_config = types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=1024,
            top_p=0.95,
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
            ],
        )

    def generate(
        self,
        persona: str,
        query: str,
        retrieved_chunks: List[Dict],
        conversation_history: List[Dict] = None,
    ) -> Dict[str, Any]:
        try:
            prompt = build_prompt(persona, query, retrieved_chunks, conversation_history)
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=self.generation_config,
            )

            finish_reason = "UNKNOWN"
            token_data = {"prompt_tokens": 0, "completion_tokens": 0}

            if not response or not response.candidates:
                logger.warning("Gemini returned empty response for query: %.80s", query)
                return {
                    "response": "I wasn't able to generate a response. Could you rephrase your question?",
                    "finish_reason": "EMPTY",
                    "token_usage": token_data,
                }

            candidate = response.candidates[0]
            if candidate.finish_reason != types.FinishReason.STOP:
                logger.warning(
                    "Gemini finish_reason=%s for query: %.80s",
                    candidate.finish_reason, query,
                )
                if candidate.finish_reason == types.FinishReason.SAFETY:
                    return {
                        "response": "I understand your concern. Let me help you with that.",
                        "finish_reason": "SAFETY",
                        "token_usage": token_data,
                    }

            response_text = response.text if response and response.text else ""
            try:
                finish_reason = candidate.finish_reason.name
            except Exception:
                finish_reason = str(candidate.finish_reason)
            try:
                if response.usage_metadata:
                    token_data = {
                        "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                        "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                    }
            except Exception:
                pass

            return {
                "response": response_text,
                "finish_reason": finish_reason,
                "token_usage": token_data,
            }

        except Exception as e:
            logger.error("Gemini generation failed: %s", e, exc_info=True)
            return {
                "response": (
                    "I'm sorry, I encountered an error while generating a response. "
                    "Please try again or contact support."
                ),
                "finish_reason": "ERROR",
                "token_usage": {"prompt_tokens": 0, "completion_tokens": 0},
            }
