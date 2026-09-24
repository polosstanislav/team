# Code standards

What engineers write to and `code-reviewer` checks. Functional style is the
default. The repo's own `AGENTS.md` / `CLAUDE.md` wins wherever it is more
specific; linters and formatters (eslint, prettier, phpstan, psalm,
php-cs-fixer, ruff, …) own formatting — never re-litigate what they already
enforce.

Apply to **changed code only**. Existing code is not flagged unless the change
touches it; mark issues seen there with a `TODO:` suggestion, don't demand a
rewrite.

## Functional style

1. **Pure core, effects at the edges.** Decisions, parsing, mapping and
   validation are pure functions of their inputs. I/O (page, network, Redis,
   stats, logging, clock, randomness) happens in a thin shell that calls them.
   Inject the clock and other effects instead of reading them inside logic.
   When decisions interleave with I/O, a generator that yields I/O requests
   and returns the decision keeps the core pure without reordering effects.
2. **No mutation of inputs or shared state.** `const` by default; return new
   values instead of editing arguments; no module-level mutable state. Local
   mutation inside a function is fine when it is the clearest way — the rule is
   about observable mutation, not dogma.
3. **Transform, don't accumulate.** Prefer `map` / `filter` / `reduce` /
   `flatMap` (PHP: `array_map`, `array_filter`) over loops that push into
   outer variables — unless the functional form is harder to read.
4. **Data in, data out.** Plain data types and `readonly` value objects
   (TS `readonly`, PHP `readonly class` / `readonly` props) over objects that
   change state after construction.
5. **Early returns** instead of nested conditions.
6. **Framework classes stay.** NestJS services, PHP controllers and processors
   are classes by necessity; keep their methods thin and push logic into pure
   functions or value objects they call.
7. **Clarity wins.** Functional when it does not make the code verbose. A
   clever point-free chain nobody can debug is a defect.

## Comments

- Explain **why** — a constraint, an upstream quirk, a measured number — never
  restate what the code says.
- Only for non-obvious logic; match the surrounding file's density.
- DocBlocks / JSDoc only when they add information beyond the signature
  (PHP: array element types like `int[]` belong in PHPDoc).
- No commented-out code, no narration of the change ("fixed in TEAM-12",
  "now we also…") — that belongs in the commit and the ticket.
- Issues noticed in existing code: `TODO:` prefix.
- English only.

## Also checked

- Descriptive names; event/callback handlers prefixed `handle`.
- Constants over magic numbers; one source per constant.
- No duplication a helper would remove (DRY), and no speculative abstraction
  either — the simplest design that meets the ticket.
- Minimal diff: nothing unrelated to the ticket.
- Tests: new logic has specs; specs test behaviour, not implementation
  details; fixtures follow the repo's convention.
- Error handling: no swallowed errors; error classes follow the repo's
  existing convention.
