# Third-Party Notices

Cloud Print Bridge's runtime image installs and uses third-party open-source software.

This file is a concise inventory, not a replacement for the complete license texts and copyright notices shipped by the respective Debian/Python packages.

## Ghostscript

Cloud Print Bridge invokes Ghostscript for PDF processing and PWG Raster generation.

Ghostscript is dual-licensed by Artifex under the GNU Affero General Public License version 3 and a commercial license. This package uses the open-source Ghostscript distribution installed from Debian.

Project: Ghostscript / GhostPDL
Package-level license reflected by Cloud Print Bridge: `AGPL-3.0-only`

## LibreOffice

Cloud Print Bridge invokes LibreOffice in headless mode to convert Office and OpenDocument files to PDF.

LibreOffice is distributed under MPL 2.0 / LGPLv3+ terms, with individual bundled components under additional open-source licenses.

## ReportLab

Cloud Print Bridge uses the open-source ReportLab Toolkit to render text files to PDF.

The open-source ReportLab Toolkit is distributed under a BSD-style license.

## Pillow

Cloud Print Bridge uses Pillow for image handling.

Current Pillow source identifies its license as the MIT-CMU License.

## Debian and Python runtime components

The Docker image is based on the official Python 3.12 slim Bookworm image and installs Debian packages including fonts and their transitive dependencies. Those packages retain their own copyright and license terms.

For registry publication, retain the package-manager license/copyright metadata in the resulting image and review any distribution-specific notice requirements as part of the final release audit.
