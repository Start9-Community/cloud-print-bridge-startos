# TODO

## Before public registry submission

- Make the GitHub repository public when Cloud Print Bridge is ready for publication.
- Review `THIRD_PARTY_NOTICES.md` against the exact packages in the final built image.
- Review `icon.svg` and other user-facing assets.
- Configure and test GitHub Actions signing and registry/S3 variables before enabling release automation.
- Run the final release regression matrix and StartOS package validation.
- Test clean install, uninstall, reinstall, backup, and restore behavior on StartOS.
- Decide the first public-release version and tag.

## Upstream/tooling follow-up

- Recheck `@start9labs/start-sdk` transitive npm audit findings when Start9 publishes an SDK update.
