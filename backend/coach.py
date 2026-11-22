"""All Claude API calls live here, so the rest of the app never touches the SDK directly."""

from functools import lru_cache
from typing import List, Literal

import anthropic
from pydantic import BaseModel

# The model that does the coaching itself.
COACH_MODEL = "claude-opus-5-5"

# Models the user can run their prompt on. Prices are USD per million tokens.
# Check https://claude.com/pricing for the latest prices.
MODELS = {
    "claude-haiku-5-5": {
        "label": "Claude Haiku 5.5",
        "input": 0.10,
        "output": 0.50,
        # Haiku costs more for prompts over 100K tokens.
        "long_threshold": 100_000,
        "long_input": 0.50,
        "long_output": 2.50,
        "best_for": "Fast, very cheap. Simple Q&A, classification, extraction, short rewrites.",
        "fallback": False,  # refusals on Haiku have no server-side fallback
    },
    "claude-sonnet-5-5": {
        "label": "Claude Sonnet 5.5",
        "input": 2.00,
        "output": 10.00,
        "best_for": "Everyday writing, coding, analysis, and most multi-step tasks.",
        "fallback": True,
    },
    "claude-opus-5-5": {
        "label": "Claude Opus 5.5",
        "input": 4.00,
        "output": 20.00,
        "best_for": "Complex reasoning, nuanced long-form writing, hard coding problems.",
        "fallback": True,
    },
    "claude-fable-5-2": {
        "label": "Claude Fable 5.2",
        "input": 8.00,
        "output": 40.00,
        "best_for": "The most demanding research, reasoning, and long agentic tasks.",
        "fallback": True,
    },
}
ModelId = Literal["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-2"]

# If Claude declines a request for safety reasons, the API automatically retries
# it on a suitable fallback model inside the same call.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

_MODEL_GUIDE = "\n".join(
    f"- {mid} ({m['label']}, ${m['input']}/${m['output']} per million input/output tokens): {m['best_for']}"
    for mid, m in MODELS.items()
)

COACH_SYSTEM = f"""You are Prompt Coach, an expert at writing prompts for Claude.
The user gives you a prompt they plan to send to an AI assistant. Evaluate it on these criteria:

1. Clarity - is the task unambiguous?
2. Context - does it give the background, audience, and purpose the model needs?
3. Specificity - are constraints, scope, and success criteria stated?
4. Output format - does it say what shape the answer should take (length, structure, tone)?
5. Examples - would examples help, and are they provided where useful?

Score each criterion 1-10 with one or two sentences of concrete, friendly feedback.
Give an overall score of 1-100. Then write an improved version of the prompt that keeps
the user's intent and voice; where you need facts only the user knows, use clearly marked
placeholders like [your audience]. Finally, list the key changes you made and why, so the
user learns the technique rather than just copying the result.

Also recommend which model should run the improved prompt. Pick the cheapest model that
will do the task well - do not recommend a more expensive model unless the task really
needs it - and explain the choice in one or two sentences. Available models:
{_MODEL_GUIDE}"""


class Criterion(BaseModel):
    name: str
    score: int
    feedback: str


class CoachReport(BaseModel):
    overall_score: int
    summary: str
    criteria: List[Criterion]
    improved_prompt: str
    key_changes: List[str]
    recommended_model: ModelId
    recommendation_reason: str


class Usage(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class CoachError(Exception):
    """A problem we can show to the user in plain language."""


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    prices = MODELS.get(model)
    if prices is None:  # e.g. a fallback model not in our list
        return 0.0
    if input_tokens > prices.get("long_threshold", float("inf")):
        in_price, out_price = prices["long_input"], prices["long_output"]
    else:
        in_price, out_price = prices["input"], prices["output"]
    return (input_tokens * in_price + output_tokens * out_price) / 1_000_000


def _usage_of(response) -> Usage:
    u = response.usage
    # Count any prompt-cache tokens as input too, so the token total is complete.
    input_tokens = (
        u.input_tokens
        + (getattr(u, "cache_creation_input_tokens", 0) or 0)
        + (getattr(u, "cache_read_input_tokens", 0) or 0)
    )
    # response.model is the model that actually answered (it differs if a fallback ran).
    return Usage(
        model=response.model,
        input_tokens=input_tokens,
        output_tokens=u.output_tokens,
        cost_usd=calculate_cost(response.model, input_tokens, u.output_tokens),
    )


@lru_cache(maxsize=1)
def get_client() -> anthropic.Anthropic:
    # Reads ANTHROPIC_API_KEY from the environment (loaded from .env in main.py).
    return anthropic.Anthropic()


def _call(method: str, model: str, **kwargs):
    if MODELS.get(model, {}).get("fallback"):
        kwargs.update(betas=[FALLBACK_BETA], fallbacks="default")
    try:
        fn = getattr(get_client().beta.messages, method)  # inside try: a missing key raises here
        response = fn(model=model, **kwargs)
    except anthropic.AuthenticationError:
        raise CoachError("Your API key was rejected. Check ANTHROPIC_API_KEY in your .env file.")
    except anthropic.RateLimitError:
        raise CoachError("Rate limited by the API. Wait a moment and try again.")
    except anthropic.APIStatusError as e:
        raise CoachError(f"Claude API error ({e.status_code}): {e.message}")
    except anthropic.APIConnectionError:
        raise CoachError("Could not reach the Claude API. Check your internet connection.")
    except anthropic.AnthropicError as e:
        raise CoachError(str(e))
    except TypeError as e:
        # The SDK raises TypeError when it can't find any credentials.
        if "authentication" in str(e):
            raise CoachError("No API key found. Copy .env.example to .env and add your ANTHROPIC_API_KEY.")
        raise

    if response.stop_reason == "refusal":
        raise CoachError("Claude declined to respond to this prompt.")
    return response


def coach_prompt(prompt: str) -> "tuple[CoachReport, Usage]":
    response = _call(
        "parse",
        model=COACH_MODEL,
        max_tokens=16000,
        output_config={"effort": "medium"},
        system=COACH_SYSTEM,
        messages=[{"role": "user", "content": f"<prompt>\n{prompt}\n</prompt>"}],
        output_format=CoachReport,
    )
    if response.parsed_output is None:
        raise CoachError("Claude's answer could not be read. Please try again.")
    return response.parsed_output, _usage_of(response)


def run_prompt(prompt: str, model: str) -> "tuple[str, Usage]":
    """Send a prompt as-is, so the user can compare original vs. improved output."""
    response = _call(
        "create",
        model=model,
        max_tokens=16000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return text, _usage_of(response)
