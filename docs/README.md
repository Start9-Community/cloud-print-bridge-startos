# Cloud Print Bridge

Cloud Print Bridge watches a folder in Nextcloud and prints whatever lands there on an IPP network printer. It is a single Python worker with no interface of its own: you interact with it entirely through the queue folders and its configuration file.

This is the reference for the application. If you are running it as a StartOS service, the quick-start is on the service's **Instructions** tab and the packaging details are in [`../README.md`](../README.md).

## Contents

- [How printing works](#how-printing-works)
- [The queue folders](#the-queue-folders)
- [Supported file types](#supported-file-types)
- [Choosing pages from a PDF](#choosing-pages-from-a-pdf)
- [Finding your printer](#finding-your-printer)
- [Configuration reference](#configuration-reference)
- [Printer requirements](#printer-requirements)
- [Limits](#limits)
- [When a job fails](#when-a-job-fails)
- [Running it outside StartOS](#running-it-outside-startos)

## How printing works

Every file takes the same route, whatever it started as:

```
source file → PDF → PWG Raster → IPP Create-Job + Send-Document
```

Office and OpenDocument files are converted to PDF by LibreOffice; plain text and images are laid out into a PDF by ReportLab; PDFs are already there. Ghostscript then rasterizes that PDF at 600 dpi onto the paper size you configured, and the result is streamed to the printer.

Because everything converges on one path, your paper size, colour mode, duplex setting and copy count apply to every file type equally. Conversion happens entirely on your own machine — no file is sent anywhere except to your printer.

The worker checks the Inbox on a fixed interval and takes **one job per cycle**, so a batch of ten files drains over ten cycles.

## The queue folders

Cloud Print Bridge creates and owns this tree in the Nextcloud account you configure:

```text
Cloud Print/
├── Inbox/        you put files here
├── Processing/   the job currently being printed
├── Printed/      finished, confirmed at the printer
└── Failed/       everything else
```

A file moves `Inbox → Processing` the moment it is claimed, which is what stops two cycles picking up the same file. It then lands in `Printed` or `Failed`. Nothing is ever deleted — clearing out `Printed` and `Failed` is yours to do.

**Reprinting the same filename is fine.** If `Printed/invoice.pdf` already exists, the next one lands beside it as `Printed/invoice (2).pdf`.

Anything sitting in `Processing` when the worker starts is treated as an interrupted job: it is moved to `Failed` without printing, because there is no way to know how much of it reached the printer.

Subfolders are ignored. Only files directly in `Inbox` are printed, and a folder whose name happens to end in `.pdf` is left alone.

## Supported file types

| Kind | Extensions | Converted by |
| --- | --- | --- |
| PDF | `.pdf` | — (already a PDF) |
| Plain text | `.txt` | ReportLab |
| Images | `.jpg` `.jpeg` `.png` `.bmp` `.tif` `.tiff` `.webp` | Pillow + ReportLab |
| Word processing | `.doc` `.docx` `.odt` `.rtf` | LibreOffice |
| Spreadsheets | `.xls` `.xlsx` `.ods` | LibreOffice |
| Presentations | `.ppt` `.pptx` `.odp` | LibreOffice |

A file with any other extension is left in `Inbox` untouched. Extensions are matched case-insensitively.

**Text files** are rendered in DejaVu Sans Mono at 10 pt with 12 pt line spacing and half-inch margins. Tabs expand to four spaces, long lines wrap at the character that no longer fits, and a form feed (`\f`) starts a new page. The file is read as UTF-8 (a byte-order mark is fine) and falls back to Windows-1252.

**Images** are scaled to fit the page with their aspect ratio intact and centred, with a quarter-inch margin. Every frame of a multi-page TIFF becomes its own page.

**Office documents** are converted by headless LibreOffice, so fidelity is LibreOffice's — a document using fonts that are not installed will be substituted.

## Choosing pages from a PDF

Put the page selection in the filename:

```text
Report [pages=8].pdf              one page
Report [pages=3-4].pdf            a range
Report [pages=1-3,8,12-15].pdf    several
```

The rules:

- Page numbers start at 1.
- Ranges must ascend (`3-4`, never `4-3`).
- Selections must ascend across the whole list and must not overlap or repeat a page.
- Every page must exist in the document.
- One directive per filename.

Anything else fails the job rather than guessing — including a directive that was started but not closed, so a typo never silently prints all 200 pages. The filename keeps the directive when the file moves to `Printed`.

This applies to files that arrive as PDFs. A `.docx` converted into a PDF cannot be page-selected, because the directive is read from the name before conversion.

## Finding your printer

There are two ways to point Cloud Print Bridge at a printer.

**By address.** Set `printerMode` to `manual` and give `printerUrl` the printer's IPP address, for example `ipp://192.168.1.50/ipp/print`. Simplest, and right whenever the printer has a static address or a DHCP reservation. If the address changes, printing stops until you update it.

**By UUID.** Set `printerMode` to `uuid-discovery` and give both `printerUuid` and `printerDiscoveryCidr`. Every printer advertises a UUID that never changes, so the worker can find the same physical printer again after its address moves. It tries the last known address first and only searches when that fails, so the normal case costs nothing.

Discovery opens a TCP connection to port 631 on every address in the ranges you give — 64 at a time, with a 0.75 s connect timeout — and asks whatever answers for its identity, trying the `/ipp/print` path before `/ipp`. It only searches IPv4, and refuses more than 4096 addresses in total, so keep the ranges tight: a `/24` is 254 addresses and takes a few seconds.

## Configuration reference

The worker reads `/data/config.json` at the start of every cycle, so a change takes effect on the next one without a restart.

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `nextcloudUsername` | string | `""` | The Nextcloud account holding the queue folders. Required. |
| `nextcloudAppPassword` | string | `""` | An app password for that account. Required. |
| `printerMode` | `manual` \| `uuid-discovery` | `manual` | How the printer is located. |
| `printerUrl` | string | `""` | `ipp://` or `ipps://` address. Required in `manual` mode; a first-try shortcut in `uuid-discovery`. |
| `printerDiscoveryCidr` | string | `""` | IPv4 networks to search, separated by commas, semicolons or spaces. Required in `uuid-discovery`. |
| `printerUuid` | string | `""` | The printer's permanent UUID. Required in `uuid-discovery`. |
| `media` | see below | `na_letter_8.5x11in` | Paper size every job is rendered onto. |
| `colorMode` | `color` \| `monochrome` | `color` | Colour or greyscale. |
| `sides` | `one-sided` \| `two-sided-long-edge` \| `two-sided-short-edge` | `one-sided` | Duplex, if the printer supports it. |
| `copies` | 1–99 | `1` | Each copy is submitted as its own print job, for printer compatibility. |
| `pollSeconds` | 5–3600 | `30` | How often the Inbox is checked. |

Paper sizes: `na_letter_8.5x11in`, `iso_a4_210x297mm`, `na_legal_8.5x14in`, `na_executive_7.25x10.5in`, `iso_a5_148x210mm`, `iso_a6_105x148mm`, `iso_b5_176x250mm`.

Use an app password rather than the account's own password: it can be revoked on its own, and it is what a WebDAV client is meant to authenticate with.

## Printer requirements

The printer must speak IPP and accept **PWG Raster** (`image/pwg-raster`) through `Create-Job` and `Send-Document`. That is what AirPrint and IPP Everywhere printers advertise, which covers most network printers made in the last decade. A printer that only accepts its manufacturer's own language — PCL, PostScript, a vendor raster format — will reject the job.

Pages are rasterized at 600 × 600 dpi; the printer's advertised resolution is not queried. Colour is sent as 8-bit sRGB and greyscale as 8-bit grey.

`ipps://` addresses are verified against the system trust store, so a printer using its own self-signed certificate is only reachable over `ipp://`. Either way the traffic stays on your local network.

## Limits

| Limit | Value | What happens past it |
| --- | --- | --- |
| Source file size | 100 MiB | Rejected before download completes |
| PDF pages | 200 | Job fails without printing |
| Rasterized output | 2 GiB | Job fails without printing |
| Conversion time | 180 s per step | Job fails without printing |
| Discovery addresses | 4096 | Discovery refuses to start |

The raster is the one worth knowing about: a page of dense colour artwork is around 28 MiB at 600 dpi, while an ordinary page of text is about 1 MiB, so the ceiling is generous for documents and deliberately tight for large photographic jobs.

## When a job fails

A failed job is moved to `Failed` and is **never reprinted automatically**. It stays there until you move it back to `Inbox` yourself.

The log distinguishes two kinds of failure, and the difference matters:

- **Definite** — nothing was printed. An unsupported file, a document that would not convert, an invalid page selection, a printer that refused the job or could not be reached at all.
- **Unconfirmed** — the connection broke partway and the outcome is unknown. The log says so explicitly, and warns that some pages or copies may already have come out. Check the paper before you retry.

Because copies are separate print jobs, a printer fault partway through a multi-copy job leaves the earlier copies printed. That is reported as unconfirmed.

## Running it outside StartOS

The worker is an ordinary Python program. It needs Python 3, Pillow, ReportLab, Ghostscript and — for Office documents — LibreOffice; the `Dockerfile` at the repository root is the reference environment.

It reads three things from its surroundings:

| | |
| --- | --- |
| `/data/config.json` | The settings above. Read-only as far as the worker is concerned. |
| `NEXTCLOUD_BRIDGE_ADDRESS` | Where Nextcloud is, as `host:port` or a full URL. |
| `NEXTCLOUD_HOST_HEADER` | The hostname to send as the HTTP `Host` header. |

The last one exists because Nextcloud rejects any request whose `Host` is not one of its `trusted_domains`, and the address you reach it on internally usually is not one. Set it to a hostname Nextcloud already trusts.

While it is running, the worker keeps `/tmp/cloud-print-bridge.ready` present exactly when it is configured, has both variables, and has successfully created the queue folders — so testing for that file is a complete readiness check. It needs no privileges: give it read access to the configuration, a writable `/tmp`, and outbound network access.

Start it with `python3 app/worker.py`. It logs to standard output and runs until stopped.

Printer discovery is also available on its own, which is what the StartOS action calls:

```console
$ python3 app/discover_printers.py 192.168.1.0/24
[{"name":"Office Laser","model":"…","info":"…","uuid":"urn:uuid:…","uri":"ipp://192.168.1.50:631/ipp/print","host":"192.168.1.50"}]
```

It writes JSON to standard output and needs no configuration file.
