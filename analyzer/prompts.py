SCREEN_PROMPT = """You are an alpha scout for crypto trading. Classify this content into one category:
- "strategy" — a specific trading strategy, edge, or alpha opportunity
- "tool" — a useful tool, library, or framework for trading
- "niche" — an underexplored market niche or new opportunity area
- "news" — relevant market news without actionable strategy
- "irrelevant" — not related to trading/crypto or too vague

Content:
---
Title: {title}
Source: {source}
{content}
---

Respond with ONLY a JSON object:
{{"category": "strategy|tool|niche|news|irrelevant", "reason": "brief explanation"}}"""


DEEP_ANALYSIS_PROMPT = """You are an expert crypto/trading strategy analyst. Analyze this potential alpha opportunity in depth.

Title: {title}
Source: {source}
URL: {url}
Content:
---
{content}
---

Evaluate this opportunity considering:
1. Can this be automated as a trading bot?
2. What is the realistic ROI potential?
3. How complex is the implementation?
4. Are there existing bots doing this already?
5. What are the risks and edge cases?

Respond with ONLY a JSON object:
{{
    "roi_potential": <1-10>,
    "feasibility": <1-10>,
    "complexity": <1-10>,
    "reasoning": "detailed analysis of the opportunity",
    "strategy_description": "concise description of the strategy",
    "similar_bots": ["list of known similar tools/bots"],
    "action_items": ["step 1", "step 2", "..."]
}}

Scoring guide:
- roi_potential: 1=negligible, 5=moderate (5-20% monthly), 10=exceptional (100%+ monthly)
- feasibility: 1=impossible, 5=doable with effort, 10=straightforward with existing tools
- complexity: 1=trivial script, 5=moderate system, 10=extremely complex infrastructure"""
