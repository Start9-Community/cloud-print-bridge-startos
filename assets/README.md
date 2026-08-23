# assets/

This directory is retained because StartOS packages require a non-empty
`assets/` directory.

Cloud Print Bridge currently does not require additional runtime assets.
The service runtime is provided by the `main` Docker image and its Python
worker.

If future versions require StartOS-mounted runtime assets, place them here
and declare the corresponding asset mount in `startos/main.ts`.
