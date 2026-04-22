# Guidelines

## Non-Negotiable Rules

- ALWAYS WORK FROM FIRST PRINCIPLES
- ALWAYS TRY TO DELETE AND SIMPLIFY
- TRY TO HAVE THE SMALLEST CODE POSSIBLE
- DELETE EVERYTHING THAT ISN'T USEFUL
- SIMPLIFY SIMPLIFY SIMPLIFY

## Coding Rules

- Keep code small.
- Prefer plain Python.
- Prefer explicitness over cleverness.
- Reduce dependencies.
- Avoid unnecessary abstractions.
- Avoid hidden state.
- Avoid overengineering.
- Remove dead code aggressively.
- Log clearly.
- Fail loudly but usefully.

## Architecture Rules

- One main pipeline entrypoint.
- Config drives scope.
- State is stored in plain JSON.
- Raw source material is preserved first.
- Parsing must be understandable from reading the file.
- If a simpler design works, use it.

## Anti-Complexity Rules

- No microservices.
- No orchestration layer.
- No generic scraping framework.
- No async unless a future phase proves it is necessary.
- No ORM.
- No classes unless they reduce complexity.

## Project Rules

- Real work runs on `kyber`.
- Local work is for tests, docs, and tiny validation only.
- `memory.md` is mandatory and append-only.
- Keep runtime artifacts out of git.
