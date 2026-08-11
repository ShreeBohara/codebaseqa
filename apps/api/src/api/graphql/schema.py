"""
GraphQL schema, mounted alongside the REST routes rather than replacing them.

WHY THIS EXISTS
The learn page has a measured request waterfall. Completing a lesson is five round
trips: the POST already returns {xp_gained, stats}, the client discards the stats and
then calls refreshStats(), which fires four more GETs (stats, achievements, activity,
completed lessons). Every one of those hits the same SQLite file for the same repository.
`learnerDashboard` collapses the four reads into one request, and `completeLesson`
returns the post-mutation dashboard inline so the client never needs the refresh.

WHAT STAYS ON REST
Chat. It is SSE token streaming (routes/chat.py), and GraphQL's incremental delivery
(@defer/@stream) is not ratified -- it is absent from the September 2025 spec edition,
its RFC has been open since 2024-09-18, and Strawberry's support is experimental and
requires graphql-core>=3.3.0a9 while the installed stable is 3.2.11. Streaming tokens
over GraphQL here would mean betting on an unratified extension for no gain.

THE THREADING RULE -- READ BEFORE ADDING A RESOLVER
Strawberry documents that it "processes sync and async fields using the event loop, which
means that using a sync def will block the entire worker". Unlike FastAPI, there is NO
automatic threadpool for sync resolvers. dependencies.get_db hands out a synchronous
SQLAlchemy Session, so every resolver that touches the database MUST go through
run_in_threadpool. A single sync resolver here would serialize blocking SQLite calls on
the event loop and stall in-flight chat streams.

Switching to AsyncSession is not the fix: a single AsyncSession is documented as unsafe
across concurrent tasks, which is exactly how a DataLoader batches, and greenlet (which
SQLAlchemy's async bridge requires) is not installed.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import strawberry
from starlette.concurrency import run_in_threadpool

from src.core.demo_mode import assert_demo_repo_access
from src.dependencies import get_session_factory
from src.models.database import Repository
from src.services.gamification import GamificationService

# --- types -----------------------------------------------------------------------

@strawberry.type
class Level:
    level: int
    title: str
    icon: str
    current_xp: int
    xp_for_next_level: int
    xp_progress: float


@strawberry.type
class Streak:
    current: int
    longest: int
    active_today: bool


@strawberry.type
class UserStats:
    total_xp: int
    level: Level
    streak: Streak
    lessons_completed: int
    quizzes_passed: int
    challenges_completed: int
    perfect_quizzes: int


@strawberry.type
class Achievement:
    key: str
    name: str
    description: str
    icon: str
    category: str
    xp_reward: int
    unlocked: bool
    requirement: Optional[int] = None


@strawberry.type
class ActivityDay:
    """Activity history as a list rather than a map: GraphQL has no arbitrary-key type."""
    date: str
    count: int


@strawberry.type
class XPGain:
    amount: int
    reason: str
    bonus: Optional[int] = None
    bonus_reason: Optional[str] = None


@strawberry.type
class RepoSummary:
    id: str
    github_owner: str
    github_name: str
    status: str
    total_files: int
    total_chunks: int
    primary_language: Optional[str] = None


@strawberry.type
class LearnerDashboard:
    """
    Everything the learn page needs after any progress event.

    This is the shape that replaces four separate GETs. Keeping it one type (rather than
    four top-level fields) means the mutation can return it inline, which is what removes
    the fifth round trip.
    """
    repo_id: str
    stats: UserStats
    achievements: List[Achievement]
    activity: List[ActivityDay]
    completed_lessons: List[str]


@strawberry.type
class CompleteLessonResult:
    xp_gained: XPGain
    dashboard: LearnerDashboard


# --- mapping from the existing service layer -------------------------------------
# Deliberately reuses GamificationService so GraphQL and REST cannot diverge in
# behaviour. These are pure functions over already-fetched data -- no I/O.

def _to_stats(raw) -> UserStats:
    d = raw if isinstance(raw, dict) else raw.model_dump()
    lvl, stk = d["level"], d["streak"]
    return UserStats(
        total_xp=d["total_xp"],
        level=Level(
            level=lvl["level"], title=lvl["title"], icon=lvl["icon"],
            current_xp=lvl["current_xp"], xp_for_next_level=lvl["xp_for_next_level"],
            xp_progress=lvl["xp_progress"],
        ),
        streak=Streak(
            current=stk["current"], longest=stk["longest"], active_today=stk["active_today"]
        ),
        lessons_completed=d["lessons_completed"],
        quizzes_passed=d["quizzes_passed"],
        challenges_completed=d["challenges_completed"],
        perfect_quizzes=d["perfect_quizzes"],
    )


def _to_achievements(raw) -> List[Achievement]:
    out = []
    for a in raw:
        d = a if isinstance(a, dict) else a.model_dump()
        out.append(Achievement(
            key=d["key"], name=d["name"], description=d["description"], icon=d["icon"],
            category=d["category"], xp_reward=d["xp_reward"],
            unlocked=bool(d.get("unlocked", False)), requirement=d.get("requirement"),
        ))
    return out


def _to_activity(raw: Dict[str, int]) -> List[ActivityDay]:
    return [ActivityDay(date=k, count=v) for k, v in sorted((raw or {}).items())]


def _to_xp_gain(raw) -> XPGain:
    d = raw if isinstance(raw, dict) else raw.model_dump()
    return XPGain(
        amount=d["amount"], reason=d["reason"],
        bonus=d.get("bonus"), bonus_reason=d.get("bonus_reason"),
    )


# --- blocking work, always off the event loop ------------------------------------

def _load_dashboard_sync(repo_id: str, persona: Optional[str]) -> LearnerDashboard:
    """
    All four reads in one session, on a worker thread.

    A fresh Session per call, not a request-scoped one: Session is not thread-safe, and
    this runs on a threadpool worker.
    """
    db = get_session_factory()()
    try:
        assert_demo_repo_access(db, repo_id)
        service = GamificationService(db)
        return LearnerDashboard(
            repo_id=repo_id,
            stats=_to_stats(service.get_user_stats(repo_id)),
            achievements=_to_achievements(service.get_all_achievements(repo_id)),
            activity=_to_activity(service.get_activity_history(repo_id)),
            completed_lessons=list(service.get_completed_lessons(repo_id, persona=persona)),
        )
    finally:
        db.close()


def _complete_lesson_sync(
    repo_id: str, lesson_id: str, time_spent_seconds: int,
    persona: Optional[str], module_id: Optional[str],
) -> CompleteLessonResult:
    db = get_session_factory()()
    try:
        assert_demo_repo_access(db, repo_id)
        service = GamificationService(db)
        xp_gain = service.record_lesson_complete(
            repo_id, lesson_id, time_spent_seconds, persona=persona, module_id=module_id
        )
        # Read the dashboard back in the SAME session, after the write, so the client
        # cannot observe a state that predates its own mutation.
        dashboard = LearnerDashboard(
            repo_id=repo_id,
            stats=_to_stats(service.get_user_stats(repo_id)),
            achievements=_to_achievements(service.get_all_achievements(repo_id)),
            activity=_to_activity(service.get_activity_history(repo_id)),
            completed_lessons=list(service.get_completed_lessons(repo_id, persona=persona)),
        )
        return CompleteLessonResult(xp_gained=_to_xp_gain(xp_gain), dashboard=dashboard)
    finally:
        db.close()


def _load_repo_sync(repo_id: str) -> Optional[RepoSummary]:
    db = get_session_factory()()
    try:
        assert_demo_repo_access(db, repo_id)
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            return None
        return RepoSummary(
            id=repo.id,
            github_owner=repo.github_owner,
            github_name=repo.github_name,
            status=repo.status.value if hasattr(repo.status, "value") else str(repo.status),
            total_files=repo.total_files or 0,
            total_chunks=repo.total_chunks or 0,
            primary_language=repo.primary_language,
        )
    finally:
        db.close()


# --- schema ----------------------------------------------------------------------

@strawberry.type
class Query:
    @strawberry.field(description="Repository summary.")
    async def repo(self, repo_id: str) -> Optional[RepoSummary]:
        return await run_in_threadpool(_load_repo_sync, repo_id)

    @strawberry.field(
        description=(
            "Stats, achievements, activity and completed lessons in one request. "
            "Replaces four separate REST GETs."
        )
    )
    async def learner_dashboard(
        self, repo_id: str, persona: Optional[str] = None
    ) -> LearnerDashboard:
        return await run_in_threadpool(_load_dashboard_sync, repo_id, persona)


@strawberry.type
class Mutation:
    @strawberry.mutation(
        description=(
            "Complete a lesson and return the post-mutation dashboard inline, so the "
            "client does not need a follow-up refresh."
        )
    )
    async def complete_lesson(
        self,
        repo_id: str,
        lesson_id: str,
        time_spent_seconds: int = 0,
        persona: Optional[str] = None,
        module_id: Optional[str] = None,
    ) -> CompleteLessonResult:
        return await run_in_threadpool(
            _complete_lesson_sync, repo_id, lesson_id, time_spent_seconds, persona, module_id
        )


schema = strawberry.Schema(query=Query, mutation=Mutation)
