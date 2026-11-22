"""All Claude API calls live here, so the rest of the app never touches the SDK directly."""

from functools import lru_cache
from typing import List

import anthropic
from pydantic import BaseModel

MODEL = "claude-opus-5-5"

# If Claude declines a request for safety reasons, the API automatically retries
# it on a suitable fallback model inside the same call.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

COACH_SYSTEM = """You are Prompt Coach, an expert at writing prompts for Claude.
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
user learns the technique rather than just copying the result."""


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


class CoachError(Exception):
    """A problem we can show to the user in plain language."""


@lru_cache(maxsize=1)
def get_client() -> anthropic.Anthropic:
    # Reads ANTHROPIC_API_KEY from the environment (loaded from .env in main.py).
    return anthropic.Anthropic()


def _call(method: str, **kwargs):
    try:
        fn = getattr(get_client().beta.messages, method)  # inside try: a missing key raises here
        response = fn(
            model=MODEL,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            **kwargs,
        )
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


def coach_prompt(prompt: str) -> CoachReport:
    response = _call(
        "parse",
        max_tokens=16000,
        output_config={"effort": "medium"},
        system=COACH_SYSTEM,
        messages=[{"role": "user", "content": f"<prompt>\n{prompt}\n</prompt>"}],
        output_format=CoachReport,
    )
    if response.parsed_output is None:
        raise CoachError("Claude's answer could not be read. Please try again.")
    return response.parsed_output


def run_prompt(prompt: str) -> str:
    """Send a prompt as-is, so the user can compare original vs. improved output."""
    response = _call(
        "create",
        max_tokens=16000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")
