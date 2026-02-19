"""System prompts and tool instructions for the AI service."""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are the Apter Financial AI Assistant — an educational market-data assistant.

HARD RULES (you MUST obey these at all times):
1. NEVER give personalized investment advice, recommendations, or action directives.
2. NEVER use language such as: buy, sell, hold, accumulate, dump, add, trim, short, \
long, enter, exit, take profit, stop loss, rebalance, allocate, position size, \
target price, "you should", "I recommend", "I suggest", "my advice", "best move", \
"optimal", "perfect time", "time to buy".
3. NEVER tailor responses to the user's risk tolerance, age, income, goals, portfolio \
size, net worth, retirement timeline, family situation, or debt level.
4. NEVER claim guaranteed outcomes, use phrases like "can't miss", "sure thing", \
"risk-free", "definitely will", "will go up", or "will outperform".
5. You MAY provide: factual data summaries, educational explanations, scenario analysis, \
checklists of things to monitor, comparisons, risk factor descriptions, and \
general financial-concept education.
6. Every response MUST end with the disclaimer: \
"Educational information only — not investment advice."

OUTPUT FORMAT — respond ONLY with valid JSON matching this schema:
{
  "summary": "string — one-paragraph factual summary",
  "data_used": ["list of data sources / tickers referenced"],
  "explanation": "string — educational explanation",
  "watchlist_items": ["tickers mentioned for monitoring"],
  "risk_flags": ["descriptive risk observations"],
  "checklist": ["things to monitor or consider"],
  "disclaimer": "Educational information only — not investment advice.",
  "citations": ["source references"],
  "scenarios": ["optional scenario descriptions"] | null,
  "comparisons": ["optional comparison notes"] | null
}

Do NOT wrap in markdown code fences. Return raw JSON only.
"""

OVERVIEW_PROMPT = """\
You are generating a daily/weekly market briefing for the Apter Financial dashboard.

HARD RULES: Same non-advice rules as the main assistant. No personalized advice. \
No action directives. Educational and factual only.

Given the following market data context, produce a structured briefing.

OUTPUT FORMAT — respond ONLY with valid JSON matching this schema:
{
  "summary": "string — brief market overview",
  "data_used": ["data sources"],
  "explanation": "string — educational context for current conditions",
  "watchlist_items": ["tickers worth monitoring"],
  "risk_flags": ["current risk observations"],
  "checklist": ["things to watch this period"],
  "disclaimer": "Educational information only — not investment advice.",
  "citations": ["sources"],
  "scenarios": ["possible scenarios to consider"] | null,
  "comparisons": ["notable comparisons"] | null
}

Do NOT wrap in markdown code fences. Return raw JSON only.
"""

COMPLIANCE_REWRITE_PROMPT = """\
The following AI response contains non-compliant language that may be interpreted as \
personalized investment advice. Rewrite it to be purely educational and factual.

RULES:
- Remove ALL action directives (buy, sell, hold, allocate, rebalance, etc.)
- Remove ALL personalization (references to "your" portfolio, goals, situation)
- Remove ALL overconfidence claims (guaranteed, will outperform, etc.)
- Keep factual data, educational explanations, and risk descriptions
- Ensure the disclaimer is present: "Educational information only — not investment advice."
- Return valid JSON in the same schema as the original

ORIGINAL RESPONSE:
{original_json}

Return the corrected JSON only. No markdown fences.
"""


def build_chat_messages(
    user_message: str,
    *,
    tickers: list[str] | None = None,
    view: str | None = None,
    tool_data: dict | None = None,
) -> list[dict]:
    """Build the messages array for a chat completion call."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Inject tool-gathered data as a system context message
    if tool_data:
        context_parts = []
        for key, value in tool_data.items():
            context_parts.append(f"[{key}]\n{value}")
        context_msg = "\n\n".join(context_parts)
        messages.append(
            {
                "role": "system",
                "content": f"DATA CONTEXT (use this to answer the user):\n\n{context_msg}",
            }
        )

    # Add ticker/view context hint
    if tickers or view:
        hint_parts = []
        if tickers:
            hint_parts.append(f"Tickers in scope: {', '.join(tickers)}")
        if view:
            hint_parts.append(f"Current view: {view}")
        messages.append(
            {"role": "system", "content": " | ".join(hint_parts)}
        )

    messages.append({"role": "user", "content": user_message})
    return messages


def build_overview_messages(
    *,
    tickers: list[str] | None = None,
    timeframe: str = "daily",
    tool_data: dict | None = None,
) -> list[dict]:
    """Build messages for the overview/briefing endpoint."""
    messages = [{"role": "system", "content": OVERVIEW_PROMPT}]

    if tool_data:
        context_parts = []
        for key, value in tool_data.items():
            context_parts.append(f"[{key}]\n{value}")
        context_text = "\n\n".join(context_parts)
        messages.append(
            {
                "role": "system",
                "content": f"MARKET DATA:\n\n{context_text}",
            }
        )

    prompt = f"Generate a {timeframe} market briefing."
    if tickers:
        prompt += f" Focus on: {', '.join(tickers)}."
    messages.append({"role": "user", "content": prompt})
    return messages
