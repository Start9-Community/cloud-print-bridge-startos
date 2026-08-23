# Cloud Print Bridge

Cloud Print Bridge turns a Nextcloud folder into a private print queue for an IPP printer reachable from your StartOS server.

## What you get on StartOS

Cloud Print Bridge:

- uses Nextcloud as the queue
- communicates with Nextcloud through StartOS service-to-service networking
- converts common document formats when necessary
- submits jobs directly to an IPP printer
- tracks jobs through `Inbox`, `Processing`, `Printed`, and `Failed`
- supports manual printer URLs or UUID-based rediscovery

It does not provide a web interface.

## Requirements

- Nextcloud installed and running on the same StartOS server
- a Nextcloud account and dedicated app password for Cloud Print Bridge
- an IPP-compatible printer reachable from StartOS

## Getting set up

### 1. Create the Nextcloud folders

Create:

```text
Cloud Print/
├── Inbox/
├── Processing/
├── Printed/
└── Failed/
```

### 2. Create a Nextcloud app password

Create a dedicated Nextcloud app password for Cloud Print Bridge. Use that app password rather than the account's normal password.

### 3. Open the Configure action

Enter:

- **Nextcloud Username**
- **Nextcloud App Password**
- **Printer Mode**
- printer fields appropriate for the selected mode
- **PDF Paper Size**
- **PDF Color Mode**
- **PDF Sides**
- **PDF Copies**
- **Polling Interval**

You do not enter a Nextcloud URL. StartOS supplies the service-to-service connection automatically.

## Printer setup

### Automatic UUID Discovery

Use this mode when you want Cloud Print Bridge to find the same printer even if its IP address changes.

Configure:

- **Printer Discovery Network(s)** — one or more IPv4 CIDRs separated by commas, semicolons, or spaces
- **Printer UUID** — the printer's persistent IPP UUID
- **Printer IPP URL** — optional fallback/last-known address

Example discovery networks:

```text
192.168.1.0/24
```

or:

```text
192.168.1.0/24, 10.20.30.0/24
```

The combined discovery configuration may contain at most 4096 unique hosts.

### Manual IPP URL

Use this mode when the printer has a stable address.

Example:

```text
ipp://192.168.1.50/ipp/print
```

A static address or DHCP reservation is recommended for manual mode.

## Printing

Place a supported file in:

```text
Cloud Print/Inbox
```

Cloud Print Bridge claims it into `Processing`, converts it when necessary, submits it to the printer, and moves a confirmed successful job to `Printed`.

Supported formats:

- PDF, TXT
- JPG, JPEG, PNG, BMP, TIF, TIFF, WebP
- DOC, DOCX, ODT, RTF
- XLS, XLSX, ODS
- PPT, PPTX, ODP

## Printing selected PDF pages

For native PDF files, add a page directive to the filename.

Single page:

```text
Report [pages=8].pdf
```

Contiguous range:

```text
Report [pages=3-4].pdf
```

Non-contiguous pages:

```text
Report [pages=1-3,8,12-15].pdf
```

Selections must:

- start at page 1 or later
- use ascending ranges
- remain strictly ascending
- not overlap or duplicate pages
- stay within the source PDF's page count

An invalid selection fails without printing.

The original filename, including the directive, is retained when the source is moved to `Printed` or `Failed`.

## Duplex printing

Choose:

- **One-sided**
- **Two-sided - Long Edge**
- **Two-sided - Short Edge**

Selected-page PDFs are normalized into a temporary PDF before rasterization so they use the same duplex path as a complete PDF.

## Queue safety

Normal successful flow:

```text
Inbox -> Processing -> Printed
```

Definite failure:

```text
Inbox -> Processing -> Failed
```

If Cloud Print Bridge cannot safely confirm the final printer outcome, the job is moved to `Failed` and is **not automatically retried**. Some pages or copies may already have printed.

Before manually retrying any such job, inspect the physical printer/output first.

If Cloud Print Bridge starts and finds files that were already in `Processing`, it treats them as orphaned/unconfirmed jobs and moves them to `Failed` without printing them.

## Resource limits

- maximum source file size: 100 MiB
- maximum PDF page count: 200
- maximum UUID-discovery scan: 4096 unique IPv4 hosts

## Troubleshooting

### Waiting for configuration

Open **Configure Cloud Print Bridge** and verify the required fields for the selected printer mode.

### Waiting for Nextcloud

Confirm Nextcloud is installed, running, and healthy in StartOS.

### Cannot check Inbox / authentication failures

Verify the Nextcloud username and app password. If a previously working app password stops authenticating, create a fresh dedicated app password and update Cloud Print Bridge.

### File stays in Inbox

Check the Cloud Print Bridge logs and confirm the file extension is supported.

### File moves to Failed

Read the nearby log entries. Common causes include invalid page selection, conversion failure, an unreachable printer, or an unconfirmed print outcome.

If the printer may have received part of the job, check the physical output before retrying.

### Printer discovery fails

Verify:

- the printer is powered on
- StartOS can route to the configured IPv4 network
- TCP port 631/IPP is reachable
- the configured UUID matches the printer
- the discovery ranges are correct and do not exceed the host limit

### Manual printer URL fails

Verify the printer address and IPP path. If its address changed, update the URL or switch to UUID discovery.
