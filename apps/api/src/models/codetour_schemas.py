"""
Pydantic schemas for VS Code CodeTour export format.
Reference: https://github.com/microsoft/codetour
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class CodeTourStep(BaseModel):
    """A single step in a CodeTour."""
    file: str = Field(..., description="The file path relative to the workspace root")
    line: int = Field(..., description="The 1-based line number")
    description: str = Field(..., description="The content of the step (supports Markdown)")
    title: Optional[str] = Field(None, description="Optional title for the step")

class CodeTour(BaseModel):
    """Representation of a .tour file."""
    title: str = Field(..., description="The title of the tour")
    steps: List[CodeTourStep] = Field(default_factory=list)
    ref: Optional[str] = Field(None, description="Optional git commit hash or tag")
