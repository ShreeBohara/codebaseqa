from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.dependencies import get_gamification_service, get_learning_service
from src.models.codetour_schemas import CodeTour
from src.models.learning import LessonContent, Persona, Syllabus
from src.services.gamification import GamificationService, UserStats
from src.services.learning_service import LearningService

router = APIRouter(tags=["learning"])

class GenerateCurriculumRequest(BaseModel):
    persona: str

@router.get("/personas", response_model=List[Persona])
async def get_personas(
    service: LearningService = Depends(get_learning_service)
):
    """Get available learning personas."""
    return service.get_personas()

@router.post("/{repo_id}/curriculum", response_model=Syllabus)
async def generate_curriculum(
    repo_id: str,
    request: GenerateCurriculumRequest,
    service: LearningService = Depends(get_learning_service)
):
    """Generate a personalized learning curriculum for a repository."""
    try:
        return await service.generate_curriculum(repo_id, request.persona)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class GenerateLessonRequest(BaseModel):
    title: str

@router.post("/{repo_id}/lessons/{lesson_id}", response_model=LessonContent)
async def generate_lesson(
    repo_id: str,
    lesson_id: str,
    request: GenerateLessonRequest,
    service: LearningService = Depends(get_learning_service)
):
    """Generate content for a specific lesson."""
    try:
        content = await service.generate_lesson(repo_id, lesson_id, request.title)
        if not content:
            raise HTTPException(status_code=500, detail="Failed to generate lesson content")
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class GenerateQuizRequest(BaseModel):
    context_content: str

@router.post("/{repo_id}/lessons/{lesson_id}/quiz")
async def generate_quiz(
    repo_id: str,
    lesson_id: str,
    request: GenerateQuizRequest,
    service: LearningService = Depends(get_learning_service)
):
    """Generate a quiz for a lesson."""
    try:
        quiz = await service.generate_quiz(repo_id, lesson_id, request.context_content)
        if not quiz:
            raise HTTPException(status_code=500, detail="Failed to generate quiz")
        return quiz
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{repo_id}/lessons/{lesson_id}/export/codetour", response_model=CodeTour)
async def export_codetour(
    repo_id: str,
    lesson_id: str,
    service: LearningService = Depends(get_learning_service)
):
    """Export a lesson as a VS Code CodeTour file (.tour)."""
    try:
        tour = await service.export_lesson_to_codetour(repo_id, lesson_id)
        if not tour:
            raise HTTPException(status_code=404, detail="Lesson not found or could not be generated")
        return tour
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{repo_id}/graph")
async def generate_graph(
    repo_id: str,
    service: LearningService = Depends(get_learning_service)
):
    """Generate repository dependency graph."""
    try:
        graph = await service.generate_graph(repo_id)
        if not graph:
            raise HTTPException(status_code=500, detail="Failed to generate graph")
        return graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Gamification & Progress Endpoints
# =============================================================================

@router.get("/{repo_id}/stats", response_model=UserStats)
async def get_user_stats(
    repo_id: str,
    service: GamificationService = Depends(get_gamification_service)
):
    """Get user XP, level, streak, and statistics."""
    try:
        return service.get_user_stats(repo_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{repo_id}/activity")
async def get_user_activity(
    repo_id: str,
    service: GamificationService = Depends(get_gamification_service)
):
    """Get user activity history for heatmap."""
    try:
        return service.get_activity_history(repo_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{repo_id}/achievements")
async def get_achievements(
    repo_id: str,
    service: GamificationService = Depends(get_gamification_service)
):
    """Get all achievements with unlock status."""
    try:
        return service.get_all_achievements(repo_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{repo_id}/progress")
async def get_lesson_progress(
    repo_id: str,
    service: GamificationService = Depends(get_gamification_service)
):
    """Get list of completed lesson IDs."""
    try:
        completed = service.get_completed_lessons(repo_id)
        return {"completed_lessons": completed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CompleteLessonRequest(BaseModel):
    time_spent_seconds: int = 0


@router.post("/{repo_id}/lessons/{lesson_id}/complete")
async def complete_lesson(
    repo_id: str,
    lesson_id: str,
    request: CompleteLessonRequest,
    service: GamificationService = Depends(get_gamification_service)
):
    """Mark a lesson as complete and award XP."""
    try:
        xp_gain = service.record_lesson_complete(repo_id, lesson_id, request.time_spent_seconds)
        stats = service.get_user_stats(repo_id)
        return {
            "xp_gained": xp_gain.model_dump(),
            "stats": stats.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SubmitQuizResultRequest(BaseModel):
    score: float  # 0.0 - 1.0


@router.post("/{repo_id}/lessons/{lesson_id}/quiz/result")
async def submit_quiz_result(
    repo_id: str,
    lesson_id: str,
    request: SubmitQuizResultRequest,
    service: GamificationService = Depends(get_gamification_service)
):
    """Submit quiz result and award XP based on score."""
    try:
        xp_gain = service.record_quiz_complete(repo_id, lesson_id, request.score)
        stats = service.get_user_stats(repo_id)

        # Check for newly unlocked achievements (future: include in response)
        _ = service.get_unlocked_achievements(repo_id)

        return {
            "xp_gained": xp_gain.model_dump(),
            "stats": stats.model_dump(),
            "is_pass": request.score >= 0.7,
            "is_perfect": request.score >= 1.0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CompleteChallengeRequest(BaseModel):
    used_hint: bool = False


@router.post("/{repo_id}/challenges/complete")
async def complete_challenge(
    repo_id: str,
    request: CompleteChallengeRequest,
    service: GamificationService = Depends(get_gamification_service)
):
    """Record challenge completion and award XP."""
    try:
        xp_gain = service.record_challenge_complete(repo_id, request.used_hint)
        stats = service.get_user_stats(repo_id)
        return {
            "xp_gained": xp_gain.model_dump(),
            "stats": stats.model_dump(),
            "is_perfect": not request.used_hint
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{repo_id}/graph/viewed")
async def record_graph_view(
    repo_id: str,
    service: GamificationService = Depends(get_gamification_service)
):
    """Record graph view for achievements."""
    try:
        achievement = service.unlock_achievement(repo_id, "graph_first_view")
        if achievement:
            return {
                "achievement_unlocked": achievement.model_dump(),
                "xp_awarded": achievement.xp_reward
            }
        return {"already_viewed": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Challenge Endpoints
# =============================================================================

class GenerateChallengeRequest(BaseModel):
    challenge_type: str  # "bug_hunt", "code_trace", "fill_blank"
    context: str = ""
    code_references: Optional[List[Dict]] = None


@router.post("/{repo_id}/lessons/{lesson_id}/challenge")
async def generate_challenge(
    repo_id: str,
    lesson_id: str,
    request: GenerateChallengeRequest,
    learning_service: LearningService = Depends(get_learning_service)
):
    """Generate an interactive challenge for a lesson."""
    from src.dependencies import get_db
    from src.services.challenges import ChallengeService

    try:
        # Create challenge service with LLM from learning service
        db = next(get_db())
        challenge_service = ChallengeService(db, learning_service._llm)

        challenge = await challenge_service.generate_challenge(
            repo_id=repo_id,
            lesson_id=lesson_id,
            challenge_type=request.challenge_type,
            context=request.context,
            code_references=request.code_references
        )
        return challenge
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ValidateBugHuntRequest(BaseModel):
    challenge: Dict
    selected_line: int
    used_hint: bool = False


@router.post("/{repo_id}/challenges/validate/bug_hunt")
async def validate_bug_hunt(
    repo_id: str,
    request: ValidateBugHuntRequest,
    gamification: GamificationService = Depends(get_gamification_service)
):
    """Validate a bug hunt challenge answer."""
    from src.dependencies import get_db
    from src.services.challenges import ChallengeService

    try:
        db = next(get_db())
        challenge_service = ChallengeService(db)
        result = challenge_service.validate_bug_hunt(request.challenge, request.selected_line)

        # Award XP if correct
        if result["correct"]:
            xp_gain = gamification.record_challenge_complete(repo_id, request.used_hint)
            result["xp_gained"] = xp_gain.model_dump()

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ValidateCodeTraceRequest(BaseModel):
    challenge: Dict
    selected_index: int
    used_hint: bool = False


@router.post("/{repo_id}/challenges/validate/code_trace")
async def validate_code_trace(
    repo_id: str,
    request: ValidateCodeTraceRequest,
    gamification: GamificationService = Depends(get_gamification_service)
):
    """Validate a code trace challenge answer."""
    from src.dependencies import get_db
    from src.services.challenges import ChallengeService

    try:
        db = next(get_db())
        challenge_service = ChallengeService(db)
        result = challenge_service.validate_code_trace(request.challenge, request.selected_index)

        # Award XP if correct
        if result["correct"]:
            xp_gain = gamification.record_challenge_complete(repo_id, request.used_hint)
            result["xp_gained"] = xp_gain.model_dump()

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ValidateFillBlankRequest(BaseModel):
    challenge: Dict
    answers: List[str]
    used_hint: bool = False


@router.post("/{repo_id}/challenges/validate/fill_blank")
async def validate_fill_blank(
    repo_id: str,
    request: ValidateFillBlankRequest,
    gamification: GamificationService = Depends(get_gamification_service)
):
    """Validate a fill in the blank challenge answer."""
    from src.dependencies import get_db
    from src.services.challenges import ChallengeService

    try:
        db = next(get_db())
        challenge_service = ChallengeService(db)
        result = challenge_service.validate_fill_blank(request.challenge, request.answers)

        # Award XP if correct
        if result["correct"]:
            xp_gain = gamification.record_challenge_complete(repo_id, request.used_hint)
            result["xp_gained"] = xp_gain.model_dump()

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
