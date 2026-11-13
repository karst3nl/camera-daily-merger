# Codex project instructions — Camera Daily Merger

Read `docs/SPECIFICATION.md` and `docs/CODEX_IMPLEMENTATION_PLAN.md` **before making changes**. They define the product and phase-by-phase execution plan.

## Mandatory Git policy

- **ALL development changes go to branch `alpha` only.** Never commit, push, merge or open an auto-merge into `main`.
- At the start of every session: inspect git status, fetch origin, switch to `alpha`, pull the latest changes. If `alpha` does not exist locally, track `origin/alpha`. Stop instead of force-pushing or overwriting unexpected remote changes.
- Work phase by phase. Make focused commits with conventional messages; after each completed/tested step push `alpha` and report commit SHA, tests run, pass/fail, and next task.
- A failing test must be fixed in the same phase before moving on; never report an unrun test as passed.
- If GitHub network/authentication prevents pushing, state that explicitly and provide the local commit SHA; do not imply the push succeeded.
- **No changes to `main` without the owner's explicit instruction after successful end-to-end testing.**

## Quality and security

- No recording files, secrets, tokens, credentials, local NAS addresses or personal home-network settings in tracked files.
- Use example placeholders such as `NAS_HOST`; maintain a strict .gitignore and document configuration through environment/add-on options.
- Treat camera filenames, recording metadata and files on NAS as untrusted. Prevent path traversal, command injection, symlink escapes, accidental source writes and scanning the output folder as input.
- Original video clips MUST remain untouched forever. No automatic deletion, move, overwrite or modification of source material.
- Default to lossless FFmpeg stream copying. Never silently transcode incompatible source streams. Record a diagnostic instead.
- Ensure temporary outputs can never be mistaken for completed ones; protect existing valid output during retries.
- Keep package/dependency versions pinned where practical. Run lint, type-check where adopted, unit tests, integration tests and add-on image validation for relevant phases.
- Update documentation, tests and changelog alongside functional changes. Keep English public docs and MIT license intact.

## Agent behavior

- Start with Phase 0 of the plan and implement sequentially. Use mocks/fixtures for NAS and camera input until real sample filenames and codecs are provided.
- Avoid guessing actual Reolink directory naming or date formats; implement configurable adapters and keep assumptions documented.
- Avoid changing architecture without noting rationale and updating the plan.
- Never claim an add-on is fully working based only on unit tests; actual Home Assistant OS and NAS tests are mandatory for release.
