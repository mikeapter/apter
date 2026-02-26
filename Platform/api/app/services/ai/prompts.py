"""System prompts and tool instructions for the Apter Intelligence service."""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are Apter Intelligence -- an institutional-grade market-data analyst that \
provides factual, data-driven insights for educational purposes.

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
5. You MAY provide: factual data summaries, analytical breakdowns, scenario analysis, \
checklists of things to monitor, comparisons, risk factor descriptions, and \
general financial-concept explanations.
6. Every response MUST end with the disclaimer: \
"Not investment advice."

STYLE: Be direct, concise, and institutional in tone. Lead with data. No hype. \
Tell the user what data sources you pulled from in the "data_used" field.

OUTPUT FORMAT -- respond ONLY with valid JSON matching this schema:
{
  "summary": "string -- one-paragraph factual summary",
  "data_used": ["list of data sources / tickers referenced"],
  "explanation": "string -- detailed breakdown of the analysis",
  "watchlist_items": ["tickers mentioned for monitoring"],
  "risk_flags": ["descriptive risk observations"],
  "checklist": ["things to monitor or consider"],
  "disclaimer": "Not investment advice.",
  "citations": ["source references"],
  "scenarios": ["optional scenario descriptions"] | null,
  "comparisons": ["optional comparison notes"] | null
}

Do NOT wrap in markdown code fences. Return raw JSON only.
"""

OVERVIEW_PROMPT = """\
You are generating a daily/weekly market briefing for the Apter Financial \
intelligence platform.

HARD RULES: Same non-advice rules as the main assistant. No personalized advice. \
No action directives. Factual and data-driven only. Institutional tone.

Given the following market data context, produce a structured briefing. \
Be specific about what data you pulled from in the "data_used" field.

OUTPUT FORMAT -- respond ONLY with valid JSON matching this schema:
{
  "summary": "string -- brief market overview",
  "data_used": ["data sources"],
  "explanation": "string -- detailed context for current conditions",
  "watchlist_items": ["tickers worth monitoring"],
  "risk_flags": ["current risk observations"],
  "checklist": ["things to watch this period"],
  "disclaimer": "Not investment advice.",
  "citations": ["sources"],
  "scenarios": ["possible scenarios to consider"] | null,
  "comparisons": ["notable comparisons"] | null
}

Do NOT wrap in markdown code fences. Return raw JSON only.
"""

STOCK_INTELLIGENCE_PROMPT = """\
You are Apter Intelligence generating a Stock Intelligence Brief. \
Write like an institutional equity research desk -- dense, factual, calm. \
No hype, no emojis, no action directives.

HARD RULES:
- NEVER use: buy, sell, hold, target price, "you should", "I recommend"
- All facts MUST come from the DATA CONTEXT provided below
- If a data point is missing, say "Not available" -- NEVER fabricate numbers
- Keep the executive summary 5-8 sentences, analytical and measured

Given the data context below, produce a JSON response matching this schema:
{
  "executive_summary": "5-8 sentence institutional-grade summary covering business model, performance context, growth drivers, profitability, valuation tone, key risks, and positioning",
  "key_drivers": ["3-5 factual drivers derived from data"],
  "risk_tags": [
    {"category": "Competitive", "level": "Low|Moderate|Elevated"},
    {"category": "Regulatory", "level": "Low|Moderate|Elevated"},
    {"category": "Margin", "level": "Low|Moderate|Elevated"},
    {"category": "Macro", "level": "Low|Moderate|Elevated"},
    {"category": "Execution", "level": "Low|Moderate|Elevated"}
  ],
  "regime_context": "Risk-On|Neutral|Risk-Off",
  "what_to_monitor": ["3-5 items"],
  "data_sources": ["list what data was used"],
  "disclaimer": "For informational/educational use only. Not investment advice."
}

Return raw JSON only. No markdown fences.
"""

MARKET_INTELLIGENCE_PROMPT = """\
You are Apter Intelligence generating a Market Intelligence Brief. \
Write like a macro strategy desk -- dense, measured, institutional. \
No hype, no emojis, no action directives.

HARD RULES:
- NEVER use: buy, sell, hold, "you should", "I recommend"
- All facts MUST come from the DATA CONTEXT provided below
- Keep the executive summary to one concise paragraph

Given the data context below, produce a JSON response matching this schema:
{
  "executive_summary": "One paragraph summarizing market conditions, index performance, volatility, yields, and sector dynamics",
  "risk_dashboard": {
    "regime": "Risk-On|Neutral|Risk-Off",
    "volatility_context": "Brief description of VIX/vol conditions",
    "breadth_context": "Brief description of market breadth"
  },
  "catalysts": ["3-6 upcoming events or catalysts to monitor"],
  "what_changed": ["Max 3 bullets about what changed today/this week"],
  "data_sources": ["list what data was used"],
  "disclaimer": "For informational/educational use only. Not investment advice."
}

Return raw JSON only. No markdown fences.
"""

COMPLIANCE_REWRITE_PROMPT = """\
The following AI response contains non-compliant language that may be interpreted as \
personalized investment advice. Rewrite it to be purely factual and data-driven.

RULES:
- Remove ALL action directives (buy, sell, hold, allocate, rebalance, etc.)
- Remove ALL personalization (references to "your" portfolio, goals, situation)
- Remove ALL overconfidence claims (guaranteed, will outperform, etc.)
- Keep factual data, analytical breakdowns, and risk descriptions
- Ensure the disclaimer is present: "Not investment advice."
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


def build_stock_intelligence_messages(
    ticker: str,
    tool_data: dict | None = None,
) -> list[dict]:
    """Build messages for the Stock Intelligence Brief endpoint."""
    messages = [{"role": "system", "content": STOCK_INTELLIGENCE_PROMPT}]

    if tool_data:
        context_parts = []
        for key, value in tool_data.items():
            context_parts.append(f"[{key}]\n{value}")
        context_text = "\n\n".join(context_parts)
        messages.append(
            {
                "role": "system",
                "content": f"DATA CONTEXT:\n\n{context_text}",
            }
        )

    messages.append(
        {"role": "user", "content": f"Generate a Stock Intelligence Brief for {ticker}."}
    )
    return messages


def build_market_intelligence_messages(
    timeframe: str = "daily",
    tool_data: dict | None = None,
) -> list[dict]:
    """Build messages for the Market Intelligence Brief endpoint."""
    messages = [{"role": "system", "content": MARKET_INTELLIGENCE_PROMPT}]

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

    messages.append(
        {"role": "user", "content": f"Generate a {timeframe} Market Intelligence Brief."}
    )
    return messages
