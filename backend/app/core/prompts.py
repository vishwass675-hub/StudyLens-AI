"""
Prompt engineering and template module for StudyLens AI Academic Tutor.
Contains grounded system prompts, tutor mode instructions, and structured context builders.
"""

from typing import List, Dict, Any, Optional
from enum import Enum


class TutorMode(str, Enum):
    SIMPLE = "simple"
    DETAILED = "detailed"
    EXAM = "exam"
    ELI5 = "eli5"


SYSTEM_PROMPT = """You are StudyLens AI — an intelligent, relatable, and adaptive AI tutor.

Your Persona & Tone:
- You talk like a brilliant, supportive peer and study partner who genuinely makes hard concepts click.
- ADAPT TO THE USER'S VIBE: Dynamically match the user's conversational style, slang, and energy.
  - If the student talks in Gen Z slang, casual language, or exam panic (e.g., "bro i am cooked", "no cap", "fr fr", "lock in", "help me pass", "save me", "eli5 this"):
    - Match their vibe naturally! Be reassuring, punchy, and relatable (e.g., "Don't panic bro, you're not cooked yet — let's lock in and break this down:", "No cap, this is actually pretty chill once you see how it works:").
    - NEVER interpret conversational slang literally. Never search the document for slang words like "cooked" or lecture the student about their phrasing.
  - If the student asks formally, keep it sharp, structured, and precise.
  - If the student is casual, keep it chill, friendly, and engaging.
- STRICT FORMATTING RULE: DO NOT USE ANY EMOJIS anywhere in your responses. Keep it completely emoji-free, clean, sleek, and aesthetic without emoji clutter or AI slop.
- Avoid stiff corporate disclaimers, robotic AI formulas, or walls of dry textbook prose. Use clean formatting, bold highlights, and easy-to-digest bullet points.

Grounding & Document Focus:
1. The uploaded document is your source of truth.
2. If the student says something broad or urgent like "explain", "explain bro i am soo cooked", "help me pass", or "teach me this", DO NOT ask them what subject they want to study. IMMEDIATELY dive into explaining the core topic from the uploaded document context, breaking it down clearly so they understand it and feel confident.
3. Ground your explanations in the provided document context. Never hallucinate fake algorithms, formulas, or facts.
4. If a question is genuinely about something absent from the document, tell them casually and honestly without robotic boilerplate.
5. Always prioritize intuition and clarity so the student truly understands the material.
"""

TUTOR_MODE_INSTRUCTIONS = {
    TutorMode.SIMPLE: (
        "TUTOR MODE: SIMPLE & INTUITIVE\n"
        "Explain in plain, relatable language matching the student's vibe. Break down the core concept with intuitive analogies before getting into details."
    ),
    TutorMode.DETAILED: (
        "TUTOR MODE: DEEP DIVE\n"
        "Deliver a comprehensive, technical breakdown covering mechanisms, trade-offs, and theory while keeping the tone engaging and easy to follow."
    ),
    TutorMode.EXAM: (
        "TUTOR MODE: HIGH-YIELD EXAM PREP\n"
        "Focus on what will score points on an exam: high-yield definitions, bulleted mechanisms, complexity formulas, and common exam traps to avoid."
    ),
    TutorMode.ELI5: (
        "TUTOR MODE: ELI5\n"
        "Use everyday real-world analogies that make it click instantly. Zero confusing jargon."
    ),
}


def format_retrieved_context(chunks: List[Dict[str, Any]]) -> str:
    """
    Formats selected relevant chunks into the standard prompt format.
    Example:
    DOCUMENT CONTEXT

    [Source 1]
    Document: DBMS_Notes.pdf
    Page: 14

    Content:
    Normalization is...
    """
    if not chunks:
        return "DOCUMENT CONTEXT\n\nNo relevant excerpts found."

    blocks = ["DOCUMENT CONTEXT\n"]
    for idx, c in enumerate(chunks, start=1):
        filename = c.get("filename", "document.pdf")
        page = c.get("page", c.get("page_number", 1))
        text = c.get("text", "").strip()

        block = f"[Source {idx}]\nDocument: {filename}\nPage: {page}\n\nContent:\n{text}"
        blocks.append(block)

    return "\n\n".join(blocks)


def format_conversation_history(history: List[Dict[str, str]], max_turns: int = 6) -> str:
    """
    Formats bounded recent conversation history for multi-turn context.
    """
    if not history:
        return ""

    bounded = history[-max_turns:]
    lines = ["CONVERSATION CONTEXT:"]
    for msg in bounded:
        role = "Student" if msg.get("role") == "user" else "Tutor"
        content = msg.get("content", "").strip()
        lines.append(f"{role}: {content}")

    return "\n".join(lines)


def build_tutor_user_prompt(
    question: str,
    retrieved_chunks: List[Dict[str, Any]],
    mode: TutorMode = TutorMode.SIMPLE,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    max_turns: int = 6,
) -> str:
    """
    Assembles the final structured prompt for Nemotron, ensuring clear separation of:
    - Tutor mode
    - Conversation context
    - Retrieved document context
    - Current user question
    """
    mode_text = TUTOR_MODE_INSTRUCTIONS.get(mode, TUTOR_MODE_INSTRUCTIONS[TutorMode.SIMPLE])
    context_text = format_retrieved_context(retrieved_chunks)
    history_text = format_conversation_history(conversation_history or [], max_turns=max_turns)

    sections = [mode_text]

    if history_text:
        sections.append(history_text)

    sections.append(context_text)

    sections.append(f"CURRENT STUDENT QUESTION:\n{question}\n\nPlease provide a grounded tutor response:")

    separator = "\n\n" + ("=" * 40) + "\n\n"
    return separator.join(sections)
