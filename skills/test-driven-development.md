# Test-Driven Development (TDD)

## Philosophy
Write tests first, always. Enforces a strict RED-GREEN-REFACTOR cycle.

## Methodology
1. **RED**: Write a failing test for the next bit of functionality you want to add.
2. **GREEN**: Watch it fail, then write the minimal code to make it pass.
3. **REFACTOR**: Improve the code without changing behavior, running the tests constantly to ensure they pass.
4. Delete any code written before its corresponding test exists.

## Benefits
- Prevents regressions.
- Self-documenting code.
- Forces code to be testable, inherently making it more modular and decoupled.

## When to use
Activates during the implementation phase. All tasks must include tests as part of their verification steps.
