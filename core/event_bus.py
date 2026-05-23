"""
Event bus — the "what are the agents doing right now?" window.

Emits channel messages to the DB so any part of the system (runner script,
human monitoring via Telegram, dashboards) can subscribe to the feed.

Usage:
    from core.event_bus import emit, get_feed

    # Agent doing something noteworthy
    emit("aco-developer", "created_pr", story_id=3,
         content="PR #47 opened for Story #3: User authentication",
         metadata={"pr_number": 47, "files_changed": 8})

    # Read the conversation feed
    feed = get_feed(limit=20)
    for msg in feed:
        print(f"[{msg['agent_id']}] {msg['verb']} → {msg['content']}")
"""

from datetime import datetime, timezone
from typing import List, Optional

from core.database import get_session, ChannelMessage


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def emit(
    agent_id: str,
    verb: str,
    story_id: Optional[int] = None,
    content: str = "",
    metadata: Optional[dict] = None,
) -> ChannelMessage:
    """
    Broadcast a message from an agent to the shared channel.

    Args:
        agent_id:  Name of the agent (e.g. "aco-architect")
        verb:      What happened — use one of the standard verbs so
                   consumers can filter reliably:
                     picked_up | approved | rejected | returned
                     | created_pr | tests_passed | tests_failed
                     | escalated | commented | done | started | finished
        story_id:  Which story this relates to (optional)
        content:  Human-readable summary (used in the live feed display)
        metadata: Structured data consumers can parse (PR number, etc.)

    Returns:
        The created ChannelMessage row.
    """
    session = get_session()
    try:
        msg = ChannelMessage(
            agent_id=agent_id,
            verb=verb,
            story_id=story_id,
            content=content,
            extra_data=metadata or {},
            timestamp=datetime.now(timezone.utc),
        )
        session.add(msg)
        session.commit()
        session.refresh(msg)

        # Log to structlog for server-side debugging
        import structlog
        logger = structlog.get_logger()
        logger.debug(
            "channel_message",
            agent=agent_id,
            verb=verb,
            story_id=story_id,
        )

        return msg
    finally:
        session.close()


def get_feed(
    story_id: Optional[int] = None,
    agent_id: Optional[str] = None,
    verb: Optional[str] = None,
    limit: int = 50,
) -> List[dict]:
    """
    Retrieve the agent conversation feed, newest first.

    All filters are AND-combined and are optional.

    Returns:
        List of dicts with keys: id, agent_id, verb, story_id,
        content, metadata, timestamp (ISO string).
    """
    session = get_session()
    try:
        q = session.query(ChannelMessage)

        if story_id is not None:
            q = q.filter(ChannelMessage.story_id == story_id)
        if agent_id is not None:
            q = q.filter(ChannelMessage.agent_id == agent_id)
        if verb is not None:
            q = q.filter(ChannelMessage.verb == verb)

        messages = (
            q.order_by(ChannelMessage.timestamp.desc())
            .limit(limit)
            .all()
        )

        return [_msg_to_dict(m) for m in messages]
    finally:
        session.close()


def get_story_timeline(story_id: int) -> List[dict]:
    """
    Full timeline of events for a single story, oldest → newest.
    """
    return list(reversed(get_feed(story_id=story_id, limit=200)))


def print_feed(limit: int = 50):
    """Pretty-print the live feed to terminal."""
    feed = get_feed(limit=limit)
    if not feed:
        print("(no messages yet)")
        return

    # Column widths
    ts_w = 8   # HH:MM:SS
    agent_w = 14
    verb_w = 14

    header = f"{'Time':<{ts_w}} {'Agent':<{agent_w}} {'Verb':<{verb_w}} Content"
    print()
    print(header)
    print("-" * len(header))
    for msg in feed:
        ts = msg["timestamp"][11:19]  # just HH:MM:SS
        agent = msg["agent_id"].replace("aco-", "")
        verb = msg["verb"]
        content = msg["content"]
        print(f"{ts:<{ts_w}} {agent:<{agent_w}} {verb:<{verb_w}} {content}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _msg_to_dict(msg: ChannelMessage) -> dict:
    return {
        "id": msg.id,
        "agent_id": msg.agent_id,
        "verb": msg.verb,
        "story_id": msg.story_id,
        "content": msg.content,
        "metadata": msg.extra_data,
        "timestamp": msg.timestamp.isoformat(),
    }
