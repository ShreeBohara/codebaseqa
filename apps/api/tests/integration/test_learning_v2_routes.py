from __future__ import annotations

from unittest.mock import MagicMock

from src.dependencies import get_gamification_service, get_learning_service
from src.models.codetour_schemas import CodeTour
from src.models.learning import Lesson, LessonContent, Module, Persona, Syllabus
from src.services.gamification import LevelInfo, StreakInfo, UserStats, XPGain


class DummyLearningService:
    def __init__(self):
        self._db = MagicMock()
        self.curriculum_calls = []
        self.lesson_calls = []
        self.lesson_get_calls = []

    def get_personas(self):
        return [Persona(id="new_hire", name="The New Hire", description="Onboarding", icon="🎓")]

    async def generate_curriculum(self, repo_id: str, persona: str, force_regenerate: bool = False, include_quality_meta: bool = False):
        self.curriculum_calls.append((repo_id, persona, force_regenerate, include_quality_meta))
        return Syllabus(
            repo_id=repo_id,
            persona=persona,
            title="Demo Track",
            description="desc",
            modules=[
                Module(
                    title="Module 1",
                    description="desc",
                    lessons=[
                        Lesson(
                            id="lesson-1",
                            title="Lesson 1",
                            description="desc",
                            type="concept",
                            estimated_minutes=10,
                        ),
                        Lesson(
                            id="lesson-2",
                            title="Lesson 2",
                            description="desc",
                            type="concept",
                            estimated_minutes=10,
                        ),
                    ],
                )
            ],
        )

    async def generate_lesson(
        self,
        repo_id: str,
        lesson_id: str,
        title: str,
        persona_id: str | None = None,
        module_id: str | None = None,
        force_regenerate: bool = False,
    ):
        self.lesson_calls.append((repo_id, lesson_id, title, persona_id, module_id, force_regenerate))
        return LessonContent(
            id=lesson_id,
            title=title,
            content_markdown="## Mission Brief\n## Objectives\n## Architecture Walkthrough\n## Code Deep Dive\n## Pitfalls\n## Recap",
            code_references=[],
            persona=persona_id,
            module_id=module_id,
        )

    async def get_or_generate_lesson(
        self,
        repo_id: str,
        lesson_id: str,
        persona_id: str,
        module_id: str | None = None,
        force_regenerate: bool = False,
    ):
        self.lesson_get_calls.append((repo_id, lesson_id, persona_id, module_id, force_regenerate))
        return LessonContent(
            id=lesson_id,
            title="Generated Lesson",
            content_markdown="## Mission Brief\n## Objectives\n## Architecture Walkthrough\n## Code Deep Dive\n## Pitfalls\n## Recap",
            code_references=[],
            persona=persona_id,
            module_id=module_id,
        )

    async def export_lesson_to_codetour(self, repo_id: str, lesson_id: str, persona_id: str | None = None):
        _ = repo_id, lesson_id, persona_id
        return CodeTour(title="Demo", steps=[])


class DummyGamificationService:
    def __init__(self):
        self._db = MagicMock()
        self.completed_calls = []
        self.record_calls = []

    def get_completed_lessons(self, repo_id: str, persona: str | None = None):
        self.completed_calls.append((repo_id, persona))
        return ["lesson-1"]

    def record_lesson_complete(
        self,
        repo_id: str,
        lesson_id: str,
        time_seconds: int,
        persona: str | None = None,
        module_id: str | None = None,
    ):
        self.record_calls.append((repo_id, lesson_id, time_seconds, persona, module_id))
        return XPGain(amount=50, reason="lesson_complete")

    def get_user_stats(self, repo_id: str):
        _ = repo_id
        return UserStats(
            total_xp=50,
            level=LevelInfo(
                level=1,
                title="Newcomer",
                icon="🌱",
                current_xp=50,
                xp_for_next_level=200,
                xp_progress=0.25,
            ),
            streak=StreakInfo(current=1, longest=1, active_today=True),
            lessons_completed=1,
            quizzes_passed=0,
            challenges_completed=0,
            perfect_quizzes=0,
        )


def test_learning_routes_accept_v2_optional_params(client):
    learning = DummyLearningService()
    gamification = DummyGamificationService()
    app = client.app
    app.dependency_overrides[get_learning_service] = lambda: learning
    app.dependency_overrides[get_gamification_service] = lambda: gamification

    old_payload = {"persona": "new_hire"}
    response = client.post("/api/learning/repo-1/curriculum", json=old_payload)
    assert response.status_code == 200
    assert learning.curriculum_calls[-1] == ("repo-1", "new_hire", False, False)

    new_payload = {"persona": "auditor", "force_regenerate": True, "include_quality_meta": True}
    response = client.post("/api/learning/repo-1/curriculum", json=new_payload)
    assert response.status_code == 200
    assert learning.curriculum_calls[-1] == ("repo-1", "auditor", True, True)

    response = client.post(
        "/api/learning/repo-1/lessons/lesson-1",
        json={"title": "L1", "persona": "auditor", "module_id": "module-1", "force_regenerate": True},
    )
    assert response.status_code == 200
    assert learning.lesson_calls[-1] == ("repo-1", "lesson-1", "L1", "auditor", "module-1", True)

    app.dependency_overrides.clear()


def test_learning_routes_get_endpoints_and_progress_persona_scoping(client):
    learning = DummyLearningService()
    gamification = DummyGamificationService()
    app = client.app
    app.dependency_overrides[get_learning_service] = lambda: learning
    app.dependency_overrides[get_gamification_service] = lambda: gamification

    response = client.get("/api/learning/repo-2/curriculum", params={"persona": "auditor", "refresh": "true"})
    assert response.status_code == 200
    assert learning.curriculum_calls[-1] == ("repo-2", "auditor", True, False)

    response = client.get(
        "/api/learning/repo-2/lessons/lesson-9",
        params={"persona": "auditor", "refresh": "true", "module_id": "module-2"},
    )
    assert response.status_code == 200
    assert learning.lesson_get_calls[-1] == ("repo-2", "lesson-9", "auditor", "module-2", True)

    response = client.get("/api/learning/repo-2/progress", params={"persona": "auditor"})
    assert response.status_code == 200
    assert gamification.completed_calls[-1] == ("repo-2", "auditor")

    response = client.post(
        "/api/learning/repo-2/lessons/lesson-9/complete",
        json={"time_spent_seconds": 42, "persona": "auditor", "module_id": "module-2"},
    )
    assert response.status_code == 200
    assert gamification.record_calls[-1] == ("repo-2", "lesson-9", 42, "auditor", "module-2")

    app.dependency_overrides.clear()
