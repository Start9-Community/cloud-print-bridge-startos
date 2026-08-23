# Updating Cloud Print Bridge

Cloud Print Bridge is developed in this repository together with its StartOS packaging. There is currently no separately versioned upstream Cloud Print Bridge repository, Docker image, or git submodule.

## Determining the upstream version

The upstream portion of the StartOS ExVer version represents the Cloud Print Bridge application version maintained in this repository.

The current package version is defined in:

`startos/versions/current.ts`

For application releases, choose the next appropriate Cloud Print Bridge semantic version and reset the StartOS downstream revision to `0`.

For StartOS packaging-only changes that do not change the Cloud Print Bridge application version, keep the upstream version and increment the downstream revision.

Examples:

`0.6.0:0` — new Cloud Print Bridge application release

`0.6.0:1` — StartOS packaging-only revision of Cloud Print Bridge 0.6.0

## Applying the bump

1. Update `version` and localized `releaseNotes` in `startos/versions/current.ts`.
2. Add a historical version node only when a real migration requires one.
3. Update `README.md` and `instructions.md` when behavior or user workflow changes.
4. Run:

   `python3 -m py_compile app/worker.py`

   `npx tsc --noEmit`

5. Build and validate the supported architectures:

   `make x86`

   `make arm`

6. Install and test the resulting package on StartOS before creating a release tag.

StartOS release tags use the package version with the colon replaced by an underscore.

Example:

`0.6.0:0` -> `v0.6.0_0`

Push release tags individually rather than using `git push --tags`.
