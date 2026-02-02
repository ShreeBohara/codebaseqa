from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.services.learning_service import LearningService
from src.models.learning import Syllabus, Persona, LessonContent
from src.dependencies import get_learning_service

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
    from src.models.learning import LessonContent
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
    from src.models.learning import Quiz
    try:
        quiz = await service.generate_quiz(repo_id, lesson_id, request.context_content)
        if not quiz:
            raise HTTPException(status_code=500, detail="Failed to generate quiz")
        return quiz
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
