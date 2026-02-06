from unittest.mock import MagicMock

from src.dependencies import get_db, get_gamification_service
from src.services.gamification import LevelInfo, StreakInfo, UserStats, XPGain


class DummyGamificationService:
    def __init__(self):
        self.record_calls = []

    def record_challenge_complete(self, repo_id: str, used_hint: bool) -> XPGain:
        self.record_calls.append((repo_id, used_hint))
        if used_hint:
            return XPGain(amount=75, reason="challenge_complete")
        return XPGain(amount=150, reason="challenge_perfect")

    def get_user_stats(self, repo_id: str) -> UserStats:
        return UserStats(
            total_xp=225,
            level=LevelInfo(
                level=2,
                title="Explorer",
                icon="🔍",
                current_xp=225,
                xp_for_next_level=500,
                xp_progress=0.1,
            ),
            streak=StreakInfo(current=2, longest=3, active_today=True),
            lessons_completed=1,
            quizzes_passed=1,
            challenges_completed=2,
            perfect_quizzes=0,
        )


def test_validate_bug_hunt_returns_backend_scoring_payload(client):
    dummy_service = DummyGamificationService()
    mock_db = MagicMock()

    app = client.app
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_gamification_service] = lambda: dummy_service

    payload = {
        "challenge": {
            "data": {
                "bug_line": 4,
                "bug_description": "Null check missing",
            }
        },
        "selected_line": 4,
        "used_hint": True,
    }

    response = client.post("/api/learning/repo-1/challenges/validate/bug_hunt", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["correct"] is True
    assert data["xp_earned"] == 75
    assert data["xp_gained"]["amount"] == 75
    assert data["stats"]["total_xp"] == 225
    assert dummy_service.record_calls == [("repo-1", True)]

    app.dependency_overrides.clear()


def test_validate_code_trace_incorrect_does_not_award_xp(client):
    dummy_service = DummyGamificationService()
    mock_db = MagicMock()

    app = client.app
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_gamification_service] = lambda: dummy_service

    payload = {
        "challenge": {
            "data": {
                "correct_index": 1,
                "options": ["A", "B", "C", "D"],
                "explanation": "B is correct",
            }
        },
        "selected_index": 0,
        "used_hint": False,
    }

    response = client.post("/api/learning/repo-2/challenges/validate/code_trace", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["correct"] is False
    assert data["xp_earned"] == 0
    assert "xp_gained" not in data
    assert "stats" not in data
    assert dummy_service.record_calls == []

    app.dependency_overrides.clear()
