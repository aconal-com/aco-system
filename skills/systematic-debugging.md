# Systematic Debugging

## Philosophy
Process over guessing. When an error occurs, do not blindly attempt fixes.

## Methodology
1. **Analyze**: Read error logs carefully. Trace the root cause backwards.
2. **Reproduce**: Create a minimal reproducible example or test that isolates the bug.
3. **Hypothesize**: Form a hypothesis for why the issue occurs.
4. **Test Fix**: Implement a fix and run tests to verify it solves the issue.
5. **Defense in Depth**: Can this happen elsewhere? Are there other edge cases? Add tests for those.
6. **Condition-Based Waiting**: Avoid hardcoded sleep timers; wait for specific states or events instead.

## Principles
- Verify before declaring success.
- Ensure the fix doesn't break other features.
- Provide a clear explanation of what went wrong and how it was fixed in the commit.

## When to use
Activates whenever an error occurs during implementation or QA.
