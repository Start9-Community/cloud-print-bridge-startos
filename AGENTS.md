# AGENTS.md

This is a StartOS service-package repository — it builds a `.s9pk` for StartOS.

Develop it inside a StartOS packaging workspace created by `start-cli s9pk init-workspace`,
which provides the packaging guide and agent context one level up. If you're reading this in a
bare clone with no workspace, the full guide is at <https://docs.start9.com/packaging>.

**Start every task at the recipe index** — `../start-technologies/projects/start-sdk/docs/src/recipes.md`
(or <https://docs.start9.com/packaging/recipes.html>). It maps an intent ("prompt the user to create
admin credentials", "expose a web UI") to the constructs, the reference pages, and a named production
package to copy. Find the recipe before you read this package's neighbours: a package you reach by
grepping may be non-conformant, and the recipe outranks it.

Freshly scaffolded? Work the
[New Package Checklist](../start-technologies/projects/start-sdk/docs/src/new-package-checklist.md)
(or <https://docs.start9.com/packaging/new-package-checklist.html>) from top to bottom. It is a
guide page, not a file in this repo — read it, don't copy it in.

Keep `README.md` (technical reference for an AI support or administering agent),
`instructions.md` (the StartOS quick-start) and `docs/README.md` (the application's own
reference, linked from `instructions.md`) in sync with your changes. A change to `app/`
usually lands in `docs/README.md`; a change to `startos/` usually does not.

**Bugs and feature requests are GitHub issues on this repo** — file them as you find them.
Don't record work in the repo instead: no `TODO.md`, no `NOTES.md`, no `PLAN.md`. What you
verified, tried, and decided belongs in the commit message and the PR body.

## This repo

- **The worker in `app/` is this project's upstream, not a vendored copy.** A behavior change there is an
  application change and needs a new upstream version, not just a downstream revision — see `UPDATING.md`.
- **Route a new input format to PDF.** Every format converges on one print path (source → PDF → PWG Raster →
  IPP Create-Job/Send-Document); a second path is how the configured paper size, colour mode, duplex and copy
  count stop applying to some of them.
- **Never hold the raster in memory.** One 600-dpi sRGB Letter page is ~100 MB before PWG's line encoding.
- **`Overwrite: F` on the Inbox→Processing MOVE is what makes claiming a job atomic** — don't relax it to
  resolve a name collision. `finalize_job` retries under a suffixed name instead.
