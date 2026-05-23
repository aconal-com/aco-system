#!/usr/bin/env python3
"""
Run PM Agent - Initializes database first
"""
import sys
sys.path.insert(0, '/home/ubuntu/.openclaw/workspace/aco-system')

from config.settings import get_settings
from core.database import init_database, get_session

print("Step 1: Initializing database...")
settings = get_settings()
init_database(settings.DATABASE_URL)
print("✓ Database initialized\n")

print("Step 2: Running PM Agent...")
print("="*60)
print()

# Import and run PM agent
from agents.project_manager import ProjectManagerAgent

agent = ProjectManagerAgent()
agent.run()
