#!/usr/bin/env python3
"""
Run Planner Agent - Initialize database first
"""
import sys
sys.path.insert(0, '/home/ubuntu/.openclaw/workspace/aco-system')

from config.settings import get_settings
from core.database import init_database, get_session

print("="*70)
print("  RUNNING PLANNER AGENT")
print("="*70)
print()

# Initialize database
settings = get_settings()
init_database(settings.DATABASE_URL)
print("✓ Database initialized\n")

# Import and run planner agent
from agents.planner import PlannerAgent

agent = PlannerAgent()
agent.run()

print()
print("="*70)
print("  PLANNER AGENT COMPLETE")
print("="*70)
