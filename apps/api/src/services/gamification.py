"""
Gamification Service for Learning Path.
Handles XP rewards, levels, streaks, and achievements.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.models.database import Achievement, GraphNodeInteraction, LessonProgress, UserXP

logger = logging.getLogger(__name__)


# =============================================================================
# XP Configuration
# =============================================================================

XP_REWARDS = {
    "lesson_complete": 50,
    "quiz_pass": 50,           # ≥70%
    "quiz_perfect": 100,       # 100%
    "module_complete": 200,
    "challenge_complete": 75,
    "challenge_perfect": 150,  # No hints
    "first_graph_view": 75,
    "streak_bonus_multiplier": 25,  # × streak_days
}

LEVEL_THRESHOLDS = [
    (1, 0, "Newcomer", "🌱"),
    (2, 200, "Explorer", "🔍"),
    (3, 500, "Contributor", "⚡"),
    (4, 1000, "Architect", "🏗️"),
    (5, 2000, "Master", "🎓"),
    (6, 5000, "Legend", "👑"),
]


# =============================================================================
# Pydantic Models
# =============================================================================

class XPGain(BaseModel):
    amount: int
    reason: str
    bonus: int = 0
    bonus_reason: Optional[str] = None


class LevelInfo(BaseModel):
    level: int
    title: str
    icon: str
    current_xp: int
    xp_for_next_level: int
    xp_progress: float  # 0.0 - 1.0


class StreakInfo(BaseModel):
    current: int
    longest: int
    active_today: bool


class UserStats(BaseModel):
    total_xp: int
    level: LevelInfo
    streak: StreakInfo
    lessons_completed: int
    quizzes_passed: int
    challenges_completed: int
    perfect_quizzes: int


class AchievementDef(BaseModel):
    key: str
    name: str
    description: str
    icon: str
    category: str
    xp_reward: int
    requirement: Optional[int] = None


# =============================================================================
# Achievement Definitions
# =============================================================================

ACHIEVEMENTS: List[AchievementDef] = [
    # Learning
    AchievementDef(key="first_lesson", name="First Steps", description="Complete your first lesson", icon="🌟", category="learning", xp_reward=25),
    AchievementDef(key="lessons_5", name="Quick Learner", description="Complete 5 lessons", icon="📖", category="learning", xp_reward=50, requirement=5),
    AchievementDef(key="lessons_10", name="Bookworm", description="Complete 10 lessons", icon="📚", category="learning", xp_reward=100, requirement=10),
    AchievementDef(key="quiz_perfect", name="Perfect Score", description="Get 100% on a quiz", icon="🎯", category="learning", xp_reward=50),
    AchievementDef(key="quiz_master", name="Quiz Master", description="Pass 5 quizzes perfectly", icon="🏆", category="learning", xp_reward=150, requirement=5),
    AchievementDef(key="module_complete", name="Module Master", description="Complete an entire module", icon="🎓", category="learning", xp_reward=75),

    # Streaks
    AchievementDef(key="streak_3", name="Warming Up", description="Maintain a 3-day streak", icon="🔥", category="streak", xp_reward=50, requirement=3),
    AchievementDef(key="streak_7", name="On Fire", description="Maintain a 7-day streak", icon="🔥🔥", category="streak", xp_reward=100, requirement=7),
    AchievementDef(key="streak_30", name="Unstoppable", description="Maintain a 30-day streak", icon="🔥🔥🔥", category="streak", xp_reward=500, requirement=30),

    # Explorer
    AchievementDef(key="graph_first_view", name="Cartographer", description="View the dependency graph", icon="🗺️", category="explorer", xp_reward=25),
    AchievementDef(key="graph_nodes_10", name="Deep Diver", description="Explore 10 graph nodes", icon="🔬", category="explorer", xp_reward=50, requirement=10),
    AchievementDef(key="graph_focus_25", name="System Mapper", description="Explore 25 unique graph nodes", icon="🧭", category="explorer", xp_reward=75, requirement=25),

    # Challenges
    AchievementDef(key="challenge_first", name="Challenger", description="Complete your first challenge", icon="⚔️", category="challenge", xp_reward=25),
    AchievementDef(key="challenge_5", name="Bug Squasher", description="Complete 5 challenges", icon="🐛", category="challenge", xp_reward=75, requirement=5),
    AchievementDef(key="challenge_perfect_5", name="Perfectionist", description="Complete 5 challenges without hints", icon="💯", category="challenge", xp_reward=150, requirement=5),
]

ACHIEVEMENT_MAP = {a.key: a for a in ACHIEVEMENTS}


# =============================================================================
# Gamification Service
# =============================================================================

class GamificationService:
    """Service for managing XP, levels, streaks, and achievements."""

    def __init__(self, db: Session):
        self._db = db

    # -------------------------------------------------------------------------
    # XP & Level Methods
    # -------------------------------------------------------------------------

    def get_or_create_user_xp(self, repo_id: str) -> UserXP:
        """Get or create XP record for a repository."""
        user_xp = self._db.query(UserXP).filter(UserXP.repository_id == repo_id).first()
        if not user_xp:
            user_xp = UserXP(repository_id=repo_id)
            self._db.add(user_xp)
            self._db.commit()
            self._db.refresh(user_xp)
        return user_xp

    def calculate_level(self, total_xp: int) -> Tuple[int, str, str, int]:
        """Calculate level from total XP. Returns (level, title, icon, xp_for_next)."""
        current_level = LEVEL_THRESHOLDS[0]
        next_threshold = LEVEL_THRESHOLDS[1][1] if len(LEVEL_THRESHOLDS) > 1 else float('inf')

        for i, (level, threshold, title, icon) in enumerate(LEVEL_THRESHOLDS):
            if total_xp >= threshold:
                current_level = (level, title, icon, threshold)
                if i + 1 < len(LEVEL_THRESHOLDS):
                    next_threshold = LEVEL_THRESHOLDS[i + 1][1]
                else:
                    next_threshold = threshold  # Max level

        return (*current_level[:3], next_threshold)

    def award_xp(self, repo_id: str, reason: str, amount: Optional[int] = None) -> XPGain:
        """Award XP for an action."""
        user_xp = self.get_or_create_user_xp(repo_id)

        # Get base XP amount
        base_xp = amount if amount else XP_REWARDS.get(reason, 0)

        # Calculate streak bonus
        streak_bonus = 0
        if user_xp.streak_days > 0 and reason in ["lesson_complete", "quiz_pass", "quiz_perfect"]:
            streak_bonus = min(user_xp.streak_days * XP_REWARDS["streak_bonus_multiplier"], 250)

        total_gained = base_xp + streak_bonus

        # Update user XP
        user_xp.total_xp += total_gained

        # Recalculate level
        level, _, _, _ = self.calculate_level(user_xp.total_xp)
        user_xp.level = level

        self._db.commit()

        return XPGain(
            amount=base_xp,
            reason=reason,
            bonus=streak_bonus,
            bonus_reason=f"Streak bonus (×{user_xp.streak_days})" if streak_bonus > 0 else None
        )

    def get_user_stats(self, repo_id: str) -> UserStats:
        """Get complete user stats including XP, level, streak."""
        user_xp = self.get_or_create_user_xp(repo_id)

        level, title, icon, next_threshold = self.calculate_level(user_xp.total_xp)

        # Find current level's threshold
        current_threshold = 0
        for lvl, thresh, _, _ in LEVEL_THRESHOLDS:
            if lvl == level:
                current_threshold = thresh
                break

        # Calculate progress to next level
        xp_in_level = user_xp.total_xp - current_threshold
        xp_needed = next_threshold - current_threshold
        progress = min(xp_in_level / xp_needed, 1.0) if xp_needed > 0 else 1.0

        # Check if active today
        today = datetime.utcnow().date()
        active_today = bool(
            user_xp.last_activity_date and
            user_xp.last_activity_date.date() == today
        )

        return UserStats(
            total_xp=user_xp.total_xp,
            level=LevelInfo(
                level=level,
                title=title,
                icon=icon,
                current_xp=user_xp.total_xp,
                xp_for_next_level=next_threshold,
                xp_progress=progress
            ),
            streak=StreakInfo(
                current=user_xp.streak_days,
                longest=user_xp.longest_streak,
                active_today=active_today
            ),
            lessons_completed=user_xp.lessons_completed,
            quizzes_passed=user_xp.quizzes_passed,
            challenges_completed=user_xp.challenges_completed,
            perfect_quizzes=user_xp.perfect_quizzes
        )

    def get_activity_history(self, repo_id: str) -> Dict[str, int]:
        """Get activity heatmap data (date -> count)."""
        # Count lesson completions per day
        results = self._db.query(
            LessonProgress.completed_at
        ).filter(
            LessonProgress.repository_id == repo_id,
            LessonProgress.status == "completed",
            LessonProgress.completed_at.isnot(None)
        ).all()

        history = {}
        for (completed_at,) in results:
            date_str = completed_at.strftime("%Y-%m-%d")
            history[date_str] = history.get(date_str, 0) + 1

        return history

    # -------------------------------------------------------------------------
    # Streak Methods
    # -------------------------------------------------------------------------

    def update_streak(self, repo_id: str) -> int:
        """Update streak based on activity. Call this when user completes any action."""
        user_xp = self.get_or_create_user_xp(repo_id)
        today = datetime.utcnow().date()

        if user_xp.last_activity_date:
            last_date = user_xp.last_activity_date.date()

            if last_date == today:
                # Already active today
                return user_xp.streak_days
            elif last_date == today - timedelta(days=1):
                # Continued streak
                user_xp.streak_days += 1
            else:
                # Streak broken
                user_xp.streak_days = 1
        else:
            # First activity
            user_xp.streak_days = 1

        # Update longest streak
        if user_xp.streak_days > user_xp.longest_streak:
            user_xp.longest_streak = user_xp.streak_days

        user_xp.last_activity_date = datetime.utcnow()
        self._db.commit()

        # Check streak achievements
        self._check_streak_achievements(repo_id, user_xp.streak_days)

        return user_xp.streak_days

    # -------------------------------------------------------------------------
    # Achievement Methods
    # -------------------------------------------------------------------------

    def get_unlocked_achievements(self, repo_id: str) -> List[str]:
        """Get list of unlocked achievement keys."""
        achievements = self._db.query(Achievement).filter(
            Achievement.repository_id == repo_id
        ).all()
        return [a.achievement_key for a in achievements]

    def get_all_achievements(self, repo_id: str) -> List[Dict]:
        """Get all achievements with unlock status."""
        unlocked = set(self.get_unlocked_achievements(repo_id))

        return [
            {
                **a.model_dump(),
                "unlocked": a.key in unlocked
            }
            for a in ACHIEVEMENTS
        ]

    def unlock_achievement(self, repo_id: str, achievement_key: str) -> Optional[AchievementDef]:
        """Unlock an achievement if not already unlocked. Returns achievement if newly unlocked."""
        # Check if already unlocked
        existing = self._db.query(Achievement).filter(
            Achievement.repository_id == repo_id,
            Achievement.achievement_key == achievement_key
        ).first()

        if existing:
            return None  # Already unlocked

        achievement_def = ACHIEVEMENT_MAP.get(achievement_key)
        if not achievement_def:
            logger.warning(f"Unknown achievement key: {achievement_key}")
            return None

        # Create achievement record
        achievement = Achievement(
            repository_id=repo_id,
            achievement_key=achievement_key,
            category=achievement_def.category,
            xp_awarded=achievement_def.xp_reward
        )
        self._db.add(achievement)

        # Award XP
        self.award_xp(repo_id, f"achievement_{achievement_key}", achievement_def.xp_reward)

        self._db.commit()
        logger.info(f"Achievement unlocked: {achievement_key} for repo {repo_id}")

        return achievement_def

    def _check_streak_achievements(self, repo_id: str, streak: int):
        """Check and unlock streak-based achievements."""
        if streak >= 3:
            self.unlock_achievement(repo_id, "streak_3")
        if streak >= 7:
            self.unlock_achievement(repo_id, "streak_7")
        if streak >= 30:
            self.unlock_achievement(repo_id, "streak_30")

    def check_lesson_achievements(self, repo_id: str):
        """Check and unlock lesson-based achievements."""
        user_xp = self.get_or_create_user_xp(repo_id)

        if user_xp.lessons_completed >= 1:
            self.unlock_achievement(repo_id, "first_lesson")
        if user_xp.lessons_completed >= 5:
            self.unlock_achievement(repo_id, "lessons_5")
        if user_xp.lessons_completed >= 10:
            self.unlock_achievement(repo_id, "lessons_10")

    def check_quiz_achievements(self, repo_id: str, is_perfect: bool):
        """Check and unlock quiz-based achievements."""
        user_xp = self.get_or_create_user_xp(repo_id)

        if is_perfect:
            self.unlock_achievement(repo_id, "quiz_perfect")

        if user_xp.perfect_quizzes >= 5:
            self.unlock_achievement(repo_id, "quiz_master")

    def check_challenge_achievements(self, repo_id: str, is_perfect: bool):
        """Check and unlock challenge-based achievements."""
        user_xp = self.get_or_create_user_xp(repo_id)

        if user_xp.challenges_completed >= 1:
            self.unlock_achievement(repo_id, "challenge_first")
        if user_xp.challenges_completed >= 5:
            self.unlock_achievement(repo_id, "challenge_5")
        if user_xp.challenges_completed >= 5 and is_perfect:
            # Check if they have 5 perfect challenges
            progress = self._db.query(LessonProgress).filter(
                LessonProgress.repository_id == repo_id,
                LessonProgress.challenges_perfect >= 1
            ).count()
            if progress >= 5:
                self.unlock_achievement(repo_id, "challenge_perfect_5")

    def record_graph_node_view(self, repo_id: str, node_id: str) -> Dict:
        """Track unique graph nodes viewed and unlock exploration achievements."""
        node_id = (node_id or "").strip()
        if not node_id:
            return {"unique_nodes_viewed": 0, "new_view": False, "achievements_unlocked": []}

        existing = self._db.query(GraphNodeInteraction).filter(
            GraphNodeInteraction.repository_id == repo_id,
            GraphNodeInteraction.node_id == node_id
        ).first()

        new_view = False
        if not existing:
            self._db.add(GraphNodeInteraction(repository_id=repo_id, node_id=node_id))
            self._db.commit()
            new_view = True

        unique_nodes_viewed = self._db.query(GraphNodeInteraction).filter(
            GraphNodeInteraction.repository_id == repo_id
        ).count()

        unlocked: List[Dict] = []
        if unique_nodes_viewed >= 10:
            achievement = self.unlock_achievement(repo_id, "graph_nodes_10")
            if achievement:
                unlocked.append(achievement.model_dump())

        if unique_nodes_viewed >= 25:
            achievement = self.unlock_achievement(repo_id, "graph_focus_25")
            if achievement:
                unlocked.append(achievement.model_dump())

        return {
            "unique_nodes_viewed": unique_nodes_viewed,
            "new_view": new_view,
            "achievements_unlocked": unlocked,
        }

    # -------------------------------------------------------------------------
    # Progress Recording
    # -------------------------------------------------------------------------

    def record_lesson_complete(
        self,
        repo_id: str,
        lesson_id: str,
        time_seconds: int,
        persona: Optional[str] = None,
        module_id: Optional[str] = None,
    ) -> XPGain:
        """Record lesson completion and award XP."""
        from datetime import datetime

        # Check if already completed (prevent double XP)
        existing_query = self._db.query(LessonProgress).filter(
            LessonProgress.repository_id == repo_id,
            LessonProgress.lesson_id == lesson_id,
            LessonProgress.status == "completed",
        )
        if persona is None:
            existing_query = existing_query.filter(LessonProgress.persona.is_(None))
        else:
            existing_query = existing_query.filter(LessonProgress.persona == persona)
        existing = existing_query.first()

        if existing:
            # Already completed, return 0 XP
            return XPGain(amount=0, reason="already_completed")

        # Create or update lesson progress
        progress_query = self._db.query(LessonProgress).filter(
            LessonProgress.repository_id == repo_id,
            LessonProgress.lesson_id == lesson_id,
        )
        if persona is None:
            progress_query = progress_query.filter(LessonProgress.persona.is_(None))
        else:
            progress_query = progress_query.filter(LessonProgress.persona == persona)
        progress = progress_query.first()

        if not progress:
            progress = LessonProgress(
                repository_id=repo_id,
                lesson_id=lesson_id,
                persona=persona,
                module_id=module_id,
                status="completed",
                completed_at=datetime.utcnow(),
                time_spent_seconds=time_seconds
            )
            self._db.add(progress)
        else:
            progress.status = "completed"
            progress.completed_at = datetime.utcnow()
            progress.time_spent_seconds += time_seconds
            if module_id:
                progress.module_id = module_id

        # Update user XP stats
        user_xp = self.get_or_create_user_xp(repo_id)
        user_xp.lessons_completed += 1
        self._db.commit()

        # Update streak
        self.update_streak(repo_id)

        # Check achievements
        self.check_lesson_achievements(repo_id)

        # Award XP
        return self.award_xp(repo_id, "lesson_complete")

    def get_completed_lessons(self, repo_id: str, persona: Optional[str] = None) -> list[str]:
        """Get list of completed lesson IDs for a repository."""
        query = self._db.query(LessonProgress.lesson_id).filter(
            LessonProgress.repository_id == repo_id,
            LessonProgress.status == "completed"
        )
        if persona is not None:
            query = query.filter(LessonProgress.persona == persona)
        results = query.all()
        return [r[0] for r in results]

    def record_quiz_complete(self, repo_id: str, lesson_id: str, score: float) -> XPGain:
        """Record quiz completion and award XP based on score."""
        user_xp = self.get_or_create_user_xp(repo_id)

        is_perfect = score >= 1.0
        is_pass = score >= 0.7

        if is_pass:
            user_xp.quizzes_passed += 1
        if is_perfect:
            user_xp.perfect_quizzes += 1

        self._db.commit()

        # Update streak
        self.update_streak(repo_id)

        # Check achievements
        self.check_quiz_achievements(repo_id, is_perfect)

        # Award XP
        if is_perfect:
            return self.award_xp(repo_id, "quiz_perfect")
        elif is_pass:
            return self.award_xp(repo_id, "quiz_pass")
        else:
            return XPGain(amount=0, reason="quiz_fail")

    def record_challenge_complete(self, repo_id: str, used_hint: bool) -> XPGain:
        """Record challenge completion and award XP."""
        user_xp = self.get_or_create_user_xp(repo_id)
        user_xp.challenges_completed += 1
        self._db.commit()

        is_perfect = not used_hint

        # Check achievements
        self.check_challenge_achievements(repo_id, is_perfect)

        # Award XP
        if is_perfect:
            return self.award_xp(repo_id, "challenge_perfect")
        else:
            return self.award_xp(repo_id, "challenge_complete")
