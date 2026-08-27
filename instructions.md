# Cloud Print Bridge

## Documentation

- [Cloud Print Bridge reference](https://github.com/Start9-Community/cloud-print-bridge-startos/blob/main/docs/README.md) — the project's own documentation: every setting, the full page-selection syntax, printer requirements and limits.
- [Nextcloud app passwords](https://docs.nextcloud.com/server/latest/user_manual/en/session_management.html#managing-devices) — the upstream guide to creating the dedicated password you will enter below.

## What you get on StartOS

Cloud Print Bridge adds a **Cloud Print** folder to your Nextcloud, and prints anything you drop into it.

Save a file into `Cloud Print/Inbox` from your phone, laptop, or the Nextcloud web page, and it comes out of your printer. Each file moves through `Processing` while it prints, then into `Printed` or `Failed`, so the folders themselves tell you what happened to every job.

It handles PDFs, plain text, images (JPG, PNG, BMP, TIFF, WebP) and Office and OpenDocument files (DOC, DOCX, ODT, RTF, XLS, XLSX, ODS, PPT, PPTX, ODP) — converting each one on your server, never through an outside service.

There is no web page to open. Everything is done from Nextcloud and from the two actions under **Actions & Config**.

## Getting set up

Nextcloud must be installed and running first; StartOS will not start Cloud Print Bridge without it. Until you finish step 3, Cloud Print Bridge shows a setup prompt in place of its usual controls.

1. **Create a Nextcloud app password.** In Nextcloud, open your personal **Security** settings and create an app password named for Cloud Print Bridge. Copy it — Nextcloud shows it only once. Use this rather than your account password, so you can revoke it on its own later.

2. **Find your printer.** Open **Actions & Config** and run **Discover Printers**. Enter the network your printer is on — usually something like `192.168.1.0/24` — and it lists every printer that answers, with a UUID and an address you can copy.

   If you already know your printer's address and it will not change, you can skip this.

3. **Run Configure Cloud Print Bridge.** Enter your Nextcloud username and the app password from step 1, then choose how to reach the printer:

   - **Manual IPP URL** — paste the printer's address, for example `ipp://192.168.1.50/ipp/print`. Best when your printer has a fixed address or a DHCP reservation.
   - **Locate Printer by UUID** — paste the UUID from step 2 and the network to search. Cloud Print Bridge finds the printer again by UUID even after its address changes. You can also give an address here; it is tried first, before searching.

   Set the paper size, colour, one- or two-sided printing, and how many copies each job should produce, then save.

The **Cloud Print** folder and its `Inbox`, `Processing`, `Printed` and `Failed` subfolders appear in Nextcloud a moment later — Cloud Print Bridge creates them for you. Once they do, the **Print Queue** health check turns green and you are ready to print.

## Printing

Put a file in `Cloud Print/Inbox`. Cloud Print Bridge picks it up on its next check — every 30 seconds by default — moves it to `Processing`, prints it, and moves it to `Printed`. One file is printed at a time, so a batch drains one job per check.

Printing the same filename twice is fine: the second copy lands in `Printed` beside the first, with a number added.

### Printing only some pages of a PDF

Add a page directive to the filename:

```text
Report [pages=8].pdf
Report [pages=3-4].pdf
Report [pages=1-3,8,12-15].pdf
```

Pages must ascend and must exist in the document; an invalid directive fails the job rather than printing the whole thing. The [reference](https://github.com/Start9-Community/cloud-print-bridge-startos/blob/main/docs/README.md#choosing-pages-from-a-pdf) has the exact rules.

This works on files that are already PDFs, not on Office documents converted into one.

### When a job fails

A job that fails moves to `Failed` and is **never reprinted automatically** — if the printer stopped partway, some pages may already be out. Look at the paper before you move the file back to `Inbox`.

The same applies to anything found in `Processing` when the service starts: it is treated as interrupted, moved to `Failed`, and not printed.

## Actions

### Configure Cloud Print Bridge

Sets your Nextcloud account, your printer, and how jobs are printed. Run it again any time — a change takes effect on the next check, without interrupting a job that is already printing.

### Discover Printers

Searches the networks you give it for printers and shows each one's name, permanent UUID and address, ready to copy. It changes nothing and prints nothing, so it is safe to run whenever you need it. A single `/24` network takes a few seconds.

## Troubleshooting

### The Print Queue check is red

Cloud Print Bridge cannot reach your Nextcloud print folders. Almost always the username or app password is wrong, or the app password has been revoked — create a fresh one and run **Configure Cloud Print Bridge** again. The service log names the error.

### A file stays in Inbox

Check that the file type is one of the supported ones, and look at the log. A file with an unsupported extension is left where it is.

### A file goes to Failed

The log entries around the job say why: an invalid page directive, a document that would not convert, a printer that could not be reached, or a print whose outcome could not be confirmed.

### Discover Printers finds nothing

Check that the printer is switched on, that the network you entered is the one it is on, and that your StartOS server can reach it. Printers must speak IPP on port 631, which most network printers made in the last decade do.

### The printer is found but the job fails

Cloud Print Bridge sends PWG Raster, the format used by AirPrint and IPP Everywhere. A printer that only understands its manufacturer's own format will reject the job — see [printer requirements](https://github.com/Start9-Community/cloud-print-bridge-startos/blob/main/docs/README.md#printer-requirements). If your printer's address begins `ipps://` and it uses its own self-signed certificate, use `ipp://` instead; the traffic stays on your own network either way.
