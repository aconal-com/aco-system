#!/usr/bin/env python3
"""
Agent Runner - Start all ACO agents and keep them running.

This script runs all 6 agents in parallel processes so they can
continuously poll for work and process stories as they come in.

Usage:
    python run_agents.py
"""
import multiprocessing
import signal
import sys
import time

from agents.project_manager import ProjectManagerAgent
from agents.planner import PlannerAgent
from agents.architect import ArchitectAgent
from agents.developer import DeveloperAgent
from agents.qa import QAAgent
from agents.human_reviewer import HumanReviewerAgent


def run_agent(agent_class, agent_name):
    """Run a single agent in its own process."""
    print(f"[{agent_name}] Starting...")
    try:
        agent = agent_class()
        agent.run()
    except KeyboardInterrupt:
        print(f"[{agent_name}] Stopping (interrupted)...")
    except Exception as e:
        print(f"[{agent_name}] Error: {e}")
    finally:
        print(f"[{agent_name}] Stopped")


def main():
    """Start all agents in parallel."""
    print("=" * 60)
    print("  ACO AGENTS - Starting all agents")
    print("=" * 60)
    print("\nPress Ctrl+C to stop all agents\n")

    # Create processes for each agent
    processes = [
        multiprocessing.Process(target=run_agent, args=(ProjectManagerAgent, "aco-pm")),
        multiprocessing.Process(target=run_agent, args=(PlannerAgent, "aco-planner")),
        multiprocessing.Process(target=run_agent, args=(ArchitectAgent, "aco-architect")),
        multiprocessing.Process(target=run_agent, args=(DeveloperAgent, "aco-dev")),
        multiprocessing.Process(target=run_agent, args=(QAAgent, "aco-qa")),
        multiprocessing.Process(target=run_agent, args=(HumanReviewerAgent, "aco-human")),
    ]

    # Start all processes
    for proc in processes:
        proc.start()

    # Wait for all processes
    try:
        for proc in processes:
            proc.join()
    except KeyboardInterrupt:
        print("\n\nStopping all agents...")
        for proc in processes:
            proc.terminate()
        for proc in processes:
            proc.join(timeout=5)

    print("\n" + "=" * 60)
    print("  All agents stopped")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
