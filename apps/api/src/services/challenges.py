"""
Challenge Generation Service for Learning Path.
Generates interactive challenges: Bug Hunt, Code Trace, Fill in Blank.
"""

import json
import logging
import random
from typing import Any, Dict, List

from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models
# =============================================================================

class BugHuntChallenge(BaseModel):
    """Find the bug in the code."""
    type: str = "bug_hunt"
    description: str
    code_snippet: str
    bug_line: int
    bug_description: str
    hint: str
    xp_reward: int = 75


class CodeTraceChallenge(BaseModel):
    """Trace through code to predict output."""
    type: str = "code_trace"
    description: str
    code_snippet: str
    question: str
    options: List[str]
    correct_index: int
    explanation: str
    xp_reward: int = 75


class FillBlankChallenge(BaseModel):
    """Fill in missing code parts."""
    type: str = "fill_blank"
    description: str
    code_with_blanks: str  # Uses ___ for blanks
    blanks: List[Dict[str, str]]  # {"id": "1", "answer": "get", "options": [...]}
    xp_reward: int = 75


class Challenge(BaseModel):
    """Union type for any challenge."""
    id: str
    lesson_id: str
    challenge_type: str
    data: Dict[str, Any]
    completed: bool = False
    used_hint: bool = False


# =============================================================================
# Challenge Service
# =============================================================================

class ChallengeService:
    """Service for generating and validating interactive challenges."""

    def __init__(self, db: Session, llm=None):
        self._db = db
        self._llm = llm

    async def generate_challenge(
        self,
        repo_id: str,
        lesson_id: str,
        challenge_type: str,
        context: str,
        code_references: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate an AI-powered interactive challenge from lesson context.

        Args:
            repo_id: Repository ID
            lesson_id: Lesson ID to base challenge on
            challenge_type: "bug_hunt", "code_trace", or "fill_blank"
            context: Lesson content/context
            code_references: Code snippets from the lesson
        """
        if not self._llm:
            # Return a mock challenge for testing
            return self._generate_mock_challenge(challenge_type, lesson_id)

        # Build prompt based on challenge type
        prompt = self._build_challenge_prompt(challenge_type, context, code_references)

        try:
            response = await self._llm.generate(prompt)
            challenge_data = self._parse_challenge_response(response, challenge_type)

            return {
                "id": f"{lesson_id}_{challenge_type}_{random.randint(1000, 9999)}",
                "lesson_id": lesson_id,
                "challenge_type": challenge_type,
                "data": challenge_data,
                "completed": False,
                "used_hint": False
            }
        except Exception as e:
            logger.error(f"Failed to generate challenge: {e}")
            return self._generate_mock_challenge(challenge_type, lesson_id)

    def _build_challenge_prompt(
        self,
        challenge_type: str,
        context: str,
        code_references: List[Dict] = None
    ) -> str:
        """Build LLM prompt for challenge generation."""

        code_context = ""
        if code_references:
            for ref in code_references[:2]:  # Limit to 2 references
                code_context += f"\n```\n{ref.get('content', '')}\n```\n"

        if challenge_type == "bug_hunt":
            return f"""Based on this lesson context, create a "Bug Hunt" challenge where the user must find a bug in code.

CONTEXT:
{context}

CODE REFERENCES:
{code_context}

Generate a JSON response with:
{{
  "description": "Brief description of the challenge",
  "code_snippet": "Code with a subtle bug (15-25 lines)",
  "bug_line": <line number with the bug>,
  "bug_description": "What the bug is",
  "hint": "A helpful hint without giving away the answer"
}}

Make the bug realistic but findable - common mistakes like off-by-one errors, missing null checks, wrong comparison operators, etc."""

        elif challenge_type == "code_trace":
            return f"""Based on this lesson context, create a "Code Trace" challenge where the user must predict what code will output/return.

CONTEXT:
{context}

CODE REFERENCES:
{code_context}

Generate a JSON response with:
{{
  "description": "Brief description",
  "code_snippet": "Code to trace (10-15 lines)",
  "question": "What will this function return/output?",
  "options": ["option1", "option2", "option3", "option4"],
  "correct_index": <0-3>,
  "explanation": "Why the correct answer is right"
}}

Make the code tracing require understanding of the lesson concepts."""

        elif challenge_type == "fill_blank":
            return f"""Based on this lesson context, create a "Fill in the Blank" challenge where the user must complete code.

CONTEXT:
{context}

CODE REFERENCES:
{code_context}

Generate a JSON response with:
{{
  "description": "Brief description",
  "code_with_blanks": "Code with ___ for blanks (max 3 blanks)",
  "blanks": [
    {{"id": "1", "answer": "correct_answer", "options": ["correct_answer", "wrong1", "wrong2", "wrong3"]}}
  ]
}}

Focus on key concepts from the lesson that the user should know."""

        return ""

    def _parse_challenge_response(self, response: str, challenge_type: str) -> Dict[str, Any]:
        """Parse LLM response into challenge data."""
        try:
            # Extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to parse challenge response: {e}")

        # Return mock if parsing fails
        return self._generate_mock_challenge(challenge_type, "unknown")["data"]

    def _generate_mock_challenge(self, challenge_type: str, lesson_id: str) -> Dict[str, Any]:
        """Generate a mock challenge for testing or fallback."""

        if challenge_type == "bug_hunt":
            mock_data = {
                "description": "Find the authentication bug in this login handler",
                "code_snippet": """async function handleLogin(email, password) {
  const user = await db.users.findOne({ email });

  if (!user) {
    return { error: "User not found" };
  }

  // Bug: Using == instead of secure comparison
  if (password == user.passwordHash) {
    const token = generateToken(user.id);
    return { success: true, token };
  }

  return { error: "Invalid password" };
}""",
                "bug_line": 9,
                "bug_description": "Comparing plain password with hash using ==, should use bcrypt.compare()",
                "hint": "Think about how passwords should be securely compared...",
            }

        elif challenge_type == "code_trace":
            mock_data = {
                "description": "Trace through this array manipulation",
                "code_snippet": """function processItems(items) {
  let result = [];

  for (let i = 0; i < items.length; i++) {
    if (items[i] % 2 === 0) {
      result.push(items[i] * 2);
    }
  }

  return result.length;
}

// What does processItems([1, 2, 3, 4, 5, 6]) return?""",
                "question": "What does processItems([1, 2, 3, 4, 5, 6]) return?",
                "options": ["3", "6", "12", "24"],
                "correct_index": 0,
                "explanation": "The function filters even numbers (2,4,6), doubles them, and returns the count (3).",
            }

        elif challenge_type == "fill_blank":
            mock_data = {
                "description": "Complete this API route handler",
                "code_with_blanks": """app.___('/api/users/:id', async (req, res) => {
  const user = await User.___(___.params.id);

  if (!user) {
    return res.status(404).json({ error: 'Not found' });
  }

  res.json(user);
});""",
                "blanks": [
                    {"id": "1", "answer": "get", "options": ["get", "post", "put", "delete"]},
                    {"id": "2", "answer": "findById", "options": ["findById", "find", "findOne", "get"]},
                    {"id": "3", "answer": "req", "options": ["req", "res", "params", "body"]}
                ]
            }
        else:
            mock_data = {"error": "Unknown challenge type"}

        return {
            "id": f"{lesson_id}_{challenge_type}_{random.randint(1000, 9999)}",
            "lesson_id": lesson_id,
            "challenge_type": challenge_type,
            "data": mock_data,
            "completed": False,
            "used_hint": False
        }

    def validate_bug_hunt(self, challenge: Dict, selected_line: int) -> Dict[str, Any]:
        """Validate bug hunt answer."""
        correct_line = challenge["data"].get("bug_line", 0)
        is_correct = selected_line == correct_line

        return {
            "correct": is_correct,
            "correct_line": correct_line,
            "explanation": challenge["data"].get("bug_description", ""),
            "xp_earned": 75 if is_correct else 0
        }

    def validate_code_trace(self, challenge: Dict, selected_index: int) -> Dict[str, Any]:
        """Validate code trace answer."""
        correct_index = challenge["data"].get("correct_index", 0)
        is_correct = selected_index == correct_index

        return {
            "correct": is_correct,
            "correct_index": correct_index,
            "correct_answer": challenge["data"]["options"][correct_index],
            "explanation": challenge["data"].get("explanation", ""),
            "xp_earned": 75 if is_correct else 0
        }

    def validate_fill_blank(self, challenge: Dict, answers: List[str]) -> Dict[str, Any]:
        """Validate fill in the blank answers."""
        blanks = challenge["data"].get("blanks", [])
        results = []
        all_correct = True

        for i, blank in enumerate(blanks):
            user_answer = answers[i] if i < len(answers) else ""
            correct = user_answer.lower() == blank["answer"].lower()
            if not correct:
                all_correct = False
            results.append({
                "id": blank["id"],
                "correct": correct,
                "correct_answer": blank["answer"],
                "user_answer": user_answer
            })

        return {
            "correct": all_correct,
            "results": results,
            "xp_earned": 75 if all_correct else 0
        }
