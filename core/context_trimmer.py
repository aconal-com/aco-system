"""
Context Trimmer - Manage context size for long-running stories.

Phase 4: Implement context trimming strategy to prevent token bloat.
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class ContextTrimmer:
    """
    Manage context size for long-running stories.

    Strategy:
    - Keep recent N comments unsummarized
    - Summarize older comments using LLM
    - Inject summary into context instead of full comment list
    """

    def __init__(self, recent_count: int = 10):
        """
        Initialize context trimmer.

        Args:
            recent_count: Number of recent comments to keep unsummarized
        """
        self.recent_count = recent_count

    def trim_comments(self, comments: List[Dict]) -> tuple[List[Dict], Optional[str]]:
        """
        Trim comments for long-running stories.

        Args:
            comments: List of comment dictionaries (with id, author, content, created_at)

        Returns:
            Tuple of (trimmed_comments, summary_text)
            - trimmed_comments: Recent N comments + summary of older ones
            - summary_text: Summary of older comments, or None if no old comments
        """
        if len(comments) <= self.recent_count:
            # No trimming needed
            return comments, None

        # Split: recent and old
        recent_comments = comments[-self.recent_count:]
        old_comments = comments[:-self.recent_count]

        # Summarize old comments
        summary = self._summarize_comments(old_comments)

        # Build trimmed list with summary
        trimmed_comments = [
            {
                "id": "summary",
                "author": "system",
                "content": f"[Summary of {len(old_comments)} older comments]",
                "comment_type": "summary",
                "created_at": old_comments[0].get("created_at") if old_comments else datetime.utcnow(),
            },
            *recent_comments,
        ]

        return trimmed_comments, summary

    def _summarize_comments(self, comments: List[Dict]) -> str:
        """
        Summarize a list of comments.

        For Phase 4, this is a placeholder. In production:
        - Use LLM to generate 2-3 sentence summary
        - Focus on: decisions made, requirements clarified, changes requested
        - Return plain text

        Args:
            comments: List of comment dictionaries

        Returns:
            Summary string (2-3 sentences)
        """
        if not comments:
            return ""

        # Placeholder: Extract key info without LLM
        # In production, call: llm_client.chat([...]) with prompt
        authors = set(c.get("author") for c in comments)
        question_comments = [c for c in comments if c.get("comment_type") == "question"]
        answer_comments = [c for c in comments if c.get("comment_type") == "answer"]

        summary_parts = []
        summary_parts.append(f"Conversation between {', '.join(sorted(authors))}")

        if question_comments:
            summary_parts.append(f"{len(question_comments)} questions asked")

        if answer_comments:
            summary_parts.append(f"{len(answer_comments)} answers provided")

        return ". ".join(summary_parts) + "."

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count (4 chars ≈ 1 token for English)
        """
        return len(text) // 4

    def should_trim(self, context_size: int, max_size: int) -> bool:
        """
        Check if context needs trimming.

        Args:
            context_size: Current context size in tokens
            max_size: Maximum allowed context size

        Returns:
            True if trimming needed
        """
        return context_size > max_size


# Global trimmer instance
_trimmer: Optional[ContextTrimmer] = None


def get_trimmer() -> ContextTrimmer:
    """Get or create the global trimmer instance."""
    global _trimmer
    if _trimmer is None:
        _trimmer = ContextTrimmer()
    return _trimmer


def trim_story_context(story_comments: List[Dict], max_tokens: int = 128000) -> tuple[List[Dict], bool]:
    """
    Trim story comments to fit within token limit.

    Args:
        story_comments: List of story comments
        max_tokens: Maximum allowed tokens

    Returns:
        Tuple of (trimmed_comments, was_trimmed)
    """
    trimmer = get_trimmer()

    # Estimate current context size
    # Rough estimate: 100 chars per comment average
    estimated_size = trimmer.estimate_tokens(str(story_comments))

    if not trimmer.should_trim(estimated_size, max_tokens):
        return story_comments, False

    # Trim comments
    trimmed, summary = trimmer.trim_comments(story_comments)
    return trimmed, True
