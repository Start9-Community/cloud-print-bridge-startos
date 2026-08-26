# Third-Party Notices

Cloud Print Bridge's runtime image installs and uses third-party open-source software.

This file is a concise inventory of major directly installed runtime components. It is not a replacement for the complete copyright notices and license texts shipped by the respective Debian and Python packages.

The exact versions below were audited from the Cloud Print Bridge runtime image built for version 0.6.0:0.

## Ghostscript

Cloud Print Bridge invokes Ghostscript for PDF processing and PWG Raster generation.

Audited Debian package:

- `ghostscript` — `10.0.0~dfsg-11+deb12u8`

The Debian package's copyright metadata identifies Ghostscript material under GNU Affero General Public License version 3 terms, together with bundled components under additional compatible open-source licenses.

The package-level license reflected by Cloud Print Bridge is:

`AGPL-3.0-only`

Detailed Debian copyright and license information is retained in the runtime image at:

`/usr/share/doc/ghostscript/copyright`

## LibreOffice

Cloud Print Bridge invokes LibreOffice in headless mode to convert Office and OpenDocument files to PDF.

Audited Debian packages:

- `libreoffice-core-nogui` — `4:7.4.7-1+deb12u14`
- `libreoffice-writer-nogui` — `4:7.4.7-1+deb12u14`
- `libreoffice-calc-nogui` — `4:7.4.7-1+deb12u14`
- `libreoffice-impress-nogui` — `4:7.4.7-1+deb12u14`

LibreOffice and its bundled components are distributed under multiple open-source licenses, including MPL, LGPL, GPL, Apache, BSD, MIT/Expat, Creative Commons, and other terms as identified by Debian's package metadata.

Detailed Debian copyright and license information is retained under:

`/usr/share/doc/libreoffice-*/copyright`

## ReportLab

Cloud Print Bridge uses ReportLab to render text files to PDF.

Audited Python package:

- `reportlab` — `4.4.2`

ReportLab's installed package metadata identifies it as BSD licensed.

## Pillow

Cloud Print Bridge uses Pillow for image handling.

Audited Python package:

- `Pillow` — `12.3.0`

Pillow's installed package metadata identifies its license expression as:

`MIT-CMU`

## Fonts

Cloud Print Bridge installs several font packages to improve document-conversion fidelity.

Audited Debian packages:

- `fonts-dejavu-core` — `2.37-6`
- `fonts-liberation2` — `2.1.5-1`
- `fonts-crosextra-carlito` — `20220224-1`
- `fonts-crosextra-caladea` — `20200211-1`

Their Debian copyright metadata identifies material under licenses including:

- Bitstream Vera
- GNU GPL version 2 or later
- SIL Open Font License 1.1
- Apache License 2.0

Detailed copyright and license information is retained in the runtime image under each package's corresponding `/usr/share/doc/.../copyright` file.

## Base image and transitive dependencies

The Docker image is based on the official Python 3.12 slim Bookworm image.

Debian packages, Python runtime components, and transitive dependencies installed into the image retain their own copyright notices and license terms. Their package-manager metadata remains present in the distributed runtime image.

This notice summarizes the major directly installed components and does not supersede those authoritative notices.
