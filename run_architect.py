#!/usr/bin/env python3
"""
Run Architect Agent - Approve planner's work
"""
import sys
sys.path.insert(0, '/home/ubuntu/.openclaw/workspace/aco-system')

from config.settings import get_settings
from core.database import init_database, get_session

print("="*70)
print("  RUNNING ARCHITECT AGENT")
print("="*70)
print()

# Initialize database
settings = get_settings()
init_database(settings.DATABASE_URL)
print("✓ Database initialized\n")

# Import and run architect agent
from agents.architect import ArchitectAgent

agent = ArchitectAgent()
agent.run()

print()
print("="*70)
print("  ARCHITECT AGENT COMPLETE")
print("="*70)
