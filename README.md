<p align="center">
  <img src="icon.webp" alt="Cloud Print Bridge Logo" width="21%">
</p>

# Cloud Print Bridge on StartOS

> Everything not listed in this document should behave the same as upstream
> Cloud Print Bridge. If a feature, setting, or behavior is not mentioned here,
> the upstream documentation is accurate and fully applicable — see the
> Documentation section of `instructions.md` for links.

Cloud Print Bridge watches a folder in Nextcloud and prints what lands there on an IPP network printer. The application has no repository of its own: it is written and versioned in this packaging repository, so the upstream project and the StartOS package are the same thing.

---

## Table of Contents

- [Image and Container Runtime](#image-and-container-runtime)
- [Volume and Data Layout](#volume-and-data-layout)
- [File Models](#file-models)
- [Dependencies](#dependencies)
- [Network Access and Interfaces](#network-access-and-interfaces)
- [Installation and First-Run Flow](#installation-and-first-run-flow)
- [Actions](#actions)
- [Tasks](#tasks)
- [Health Checks](#health-checks)
- [Backups and Restore](#backups-and-restore)
- [Limitations and Differences](#limitations-and-differences)
- [Quick Reference for AI Consumers](#quick-reference-for-ai-consumers)

---

## Image and Container Runtime

One image, built from this repository's `Dockerfile`, running one long-lived Python worker.

| What          | Value                                                                       |
| ------------- | --------------------------------------------------------------------------- |
| Image source  | Custom Dockerfile on `python:3.12-slim-bookworm`                            |
| Architectures | x86_64, aarch64                                                             |
| Entrypoint    | Default — `python3 /app/worker.py`                                          |
| Runs as       | `cloudprint`, an unprivileged account created in the image                  |

The package runs one subcontainer, `main`, which hosts the `main` daemon; attach to it with `start-cli package attach cloud-print-bridge -n main`. The `discover-printers` action runs its own short-lived subcontainer from the same image and exits when the scan finishes.

Ghostscript, LibreOffice (headless, no GUI) and ReportLab live in the image because every print job is converted locally: LibreOffice renders Office and OpenDocument files to PDF, ReportLab renders plain text and images to PDF, and Ghostscript rasterizes the resulting PDF to PWG Raster. Nothing is sent to a third-party conversion service.

Those three parse whatever the user drops in the queue, so both the daemon and the discovery action name `user: 'cloudprint'` in their exec — StartOS does not read the image's `USER`, and would otherwise run them as root. The worker needs no privilege: it reads `/data/config.json`, writes under `/tmp`, and opens outbound connections.

The worker resolves Nextcloud through two environment variables StartOS supplies at daemon start:

| Variable                   | What it carries                                                                          |
| -------------------------- | ---------------------------------------------------------------------------------------- |
| `NEXTCLOUD_BRIDGE_ADDRESS` | The container-reachable `host:port` of Nextcloud's `main` host                            |
| `NEXTCLOUD_HOST_HEADER`    | A hostname Nextcloud already lists in `trusted_domains`, sent as the `Host` header        |

Both are resolved with `.const()`, so the daemon restarts when either changes. Neither is set while Nextcloud is absent, and the worker waits rather than failing.

## Volume and Data Layout

One volume holds one file. The print queue itself lives in Nextcloud and is never copied here.

| Volume | Mount   | Contents                                    |
| ------ | ------- | ------------------------------------------- |
| `main` | `/data` | `config.json` — the whole of the settings   |

Job data is transient: a claimed file is downloaded, converted under a per-job temporary directory in the container, and discarded when the job ends. No `store.json`.

## File Models

The package owns exactly one configuration file, and the user never edits it by hand.

| Model              | File                | Format |
| ------------------ | ------------------- | ------ |
| `config.json.ts`   | `/data/config.json` | JSON   |

It is seeded at install with schema defaults (`merge` with an empty object) and rewritten in full by the **Configure Cloud Print Bridge** action. Nothing re-asserts a value behind the user's back — the worker only reads it, once per poll, so a hand edit survives and takes effect on the next cycle. Every field carries a schema fallback, so an edit that sets a value to an unsupported type is replaced by that field's default rather than failing the read.

Nextcloud credentials are stored here in plaintext, on the encrypted service volume, because WebDAV Basic authentication needs them on every request.

## Dependencies

One required dependency, which supplies the queue.

| Dependency  | Required | Health check gate | Mounted volume | Why                                                          |
| ----------- | -------- | ----------------- | -------------- | ------------------------------------------------------------ |
| `nextcloud` | Yes      | `nextcloud`       | None           | Hosts the `Cloud Print` folders the bridge watches over WebDAV |

The bridge talks to Nextcloud over the StartOS service bridge as an ordinary WebDAV client. It mounts nothing from Nextcloud and needs no Nextcloud app installed.

## Network Access and Interfaces

The package exposes nothing. It binds no port, publishes no host, and creates no interface — `setInterfaces` returns an empty list, so the service has no address panel and cannot be reached from the LAN, Tor, or a domain.

All of its traffic is outbound: WebDAV to Nextcloud over the service bridge, and IPP to a printer on a network the StartOS server can route to. Printer discovery opens a TCP connection to port 631 on each address in the ranges the user supplies.

## Installation and First-Run Flow

Install leaves the service held on a setup prompt rather than running.

Init seeds `config.json` with defaults and raises a `critical` task pointing at **Configure Cloud Print Bridge** (see [Tasks](#tasks)). Because the task is critical, the service does not start and the ordinary Start control is replaced by the prompt until the user completes it. Nextcloud must be installed and running first — StartOS enforces that as a dependency.

The first time the worker reaches Nextcloud with working credentials it creates the queue tree itself — `Cloud Print/` and the `Inbox`, `Processing`, `Printed` and `Failed` folders under it. That first authenticated write is also the credential check: readiness is not reported until it succeeds, so a wrong username or app password shows as an unhealthy service rather than as a silently idle one.

## Actions

Two actions, both user-facing, both safe to run repeatedly and at any service status.

### Configure Cloud Print Bridge

Run it after install, and whenever the Nextcloud account, printer, or print settings change. It rewrites `/data/config.json` in full. Takes effect on the next poll — the daemon is not restarted, no job in flight is disturbed, and running it twice with the same input changes nothing. Returns no output. It rejects a printer URL that does not begin with `ipp://` or `ipps://`, and rejects UUID mode without a discovery network, rather than letting the mistake surface later as a failed print.

### Discover Printers

Run it during setup, or after a printer moves, to learn a printer's permanent UUID. It opens a TCP connection to port 631 on every address in the ranges given — up to 4096 addresses, 64 at a time — and asks each responder for its IPP identity, so a `/24` takes a few seconds and a range near the limit can take a minute. It changes nothing on disk and prints nothing; it returns each printer's name, model, UUID and IPP URL as copyable values. Safe to repeat, and safe to run while jobs are printing.

## Tasks

One task, raised by the package itself against its own Configure action.

| Task                           | Severity   | Raised when                                              | Cleared when          |
| ------------------------------ | ---------- | -------------------------------------------------------- | --------------------- |
| `cloud-print-bridge:configure` | `critical` | The Nextcloud account or printer fields are unset         | Configure runs        |

It is raised by an init watcher holding a reactive read of `config.json`, so it can return: empty a required field through Configure and the watcher re-raises it. StartOS clears an unconditional task itself once its target action runs, so the action does not clear it. Because it is `critical`, it blocks the service from starting and hides the ordinary controls while it stands — a service that appears to have no Start button is showing this task, not a fault. "Required" depends on the printer mode: manual mode needs a printer URL; UUID mode needs a discovery network and a UUID. Both modes need the Nextcloud username and app password.

## Health Checks

One check, `Print Queue`, attached to the `main` daemon.

It passes when the worker's readiness marker is present, which the worker writes only while the configuration is complete, both Nextcloud environment variables are set, and the queue folders have been created under the configured account. So a failure means the bridge cannot reach the queue — in practice a wrong Nextcloud username or app password, a revoked app password, or Nextcloud still starting. It is not a printer check: the printer is contacted only when a job is claimed, and a printer fault appears as a job in `Failed`, not as a failed health check.

The default grace period applies. A restart normally clears the check within a few seconds; a check that stays red for longer than Nextcloud's own startup is a credential problem, and the service log names it.

## Backups and Restore

The `main` volume is copied wholesale — `Backups.ofVolumes('main')` — so the backup is `config.json` and nothing else.

Nothing is deliberately excluded, because nothing else is kept: queued, printed and failed documents live in Nextcloud and are covered by Nextcloud's own backup. A restored instance is immediately usable provided the Nextcloud account and app password it holds still exist; if the app password was revoked in the meantime, the health check fails until Configure is run with a new one. Files that were mid-flight in `Processing` when the backup was taken are swept to `Failed` on the next start, unprinted.

## Limitations and Differences

1. Printer discovery and UUID-based location handle IPv4 only.
2. The printer must be reachable from the StartOS server over IPP, and must accept PWG Raster — the format IPP Everywhere and AirPrint printers advertise. A printer that only accepts vendor formats such as PCL or PostScript is not supported.
3. `ipps://` printer URLs are verified against the system trust store, so a printer with a self-signed certificate — most of them — is only reachable over `ipp://`. Traffic to it stays on the local network.
4. A job is rasterized at 600 dpi; the printer's advertised resolution is not queried. Output is capped at 2 GiB of raster and 200 pages, and the source file at 100 MiB. A job over any of those limits goes to `Failed` without printing.
5. Copies are submitted as separate IPP jobs, so a printer fault partway through leaves the earlier copies printed and the source in `Failed`.
6. Filename page-selection directives apply only to files that arrive as PDFs, not to Office documents converted into one.
7. Office conversion fidelity is LibreOffice's, and depends on the fonts in the image.
8. A job whose printer outcome cannot be confirmed goes to `Failed` and is never retried automatically, because some pages may already have printed. Check the physical output before reprinting.
9. One job is claimed per polling cycle, so a queue drains at the polling interval.
10. There is no web interface. Everything is done through Nextcloud folders, the two actions, and the service log.

---

## Quick Reference for AI Consumers

```yaml
package_id: cloud-print-bridge
architectures: [x86_64, aarch64]
subcontainers: [main]
volumes:
  main: /data
file_models:
  - /data/config.json
startos_managed_env_vars:
  - NEXTCLOUD_BRIDGE_ADDRESS
  - NEXTCLOUD_HOST_HEADER
dependencies:
  - nextcloud
interfaces: none
actions:
  - configure
  - discover-printers
tasks:
  - { action: configure, severity: critical }
health_checks:
  - main
```
