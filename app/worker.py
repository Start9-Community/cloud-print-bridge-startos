import concurrent.futures
import ipaddress
import socket
import http.client
#!/usr/bin/env python3

import base64
import io
import json
import os
import re
import subprocess
import struct
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from PIL import Image, ImageSequence

CONFIG_FILE = "/data/config.json"
READY_FILE = "/tmp/cloud-print-bridge.ready"

# Resource safety limits.
MAX_SOURCE_BYTES = 100 * 1024 * 1024
MAX_PDF_PAGES = 200
DOWNLOAD_CHUNK_BYTES = 1024 * 1024

DAV_NS = "{DAV:}"


class PermanentJobError(Exception):
    """A definite job failure that is safe to move to Failed."""



def log(message):
    print(message, flush=True)


def job_display_name(href):
    """Return only the decoded filename for safe, concise logging."""
    path = urllib.parse.urlsplit(href).path
    name = path.rstrip("/").rsplit("/", 1)[-1]
    name = urllib.parse.unquote(name)

    return name or "(unnamed job)"


def human_size(byte_count):
    """Format a byte count for human-readable logs."""
    size = float(byte_count)

    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024 or unit == "GiB":
            if unit == "B":
                return f"{int(size)} {unit}"

            return f"{size:.1f} {unit}"

        size /= 1024

    return f"{byte_count} B"


def print_settings_summary(config):
    """Return the active print settings without exposing addresses."""
    media_labels = {
        "na_letter_8.5x11in": "Letter",
        "iso_a4_210x297mm": "A4",
        "na_legal_8.5x14in": "Legal",
        "na_executive_7.25x10.5in": "Executive",
        "iso_a5_148x210mm": "A5",
        "iso_a6_105x148mm": "A6",
        "iso_b5_176x250mm": "B5",
    }

    sides_labels = {
        "one-sided": "one-sided",
        "two-sided-long-edge": "duplex long-edge",
        "two-sided-short-edge": "duplex short-edge",
    }

    media_value = config.get(
        "media",
        "na_letter_8.5x11in",
    )

    media = media_labels.get(
        media_value,
        media_value,
    )

    color = config.get(
        "colorMode",
        "color",
    )

    sides_value = config.get(
        "sides",
        "one-sided",
    )

    sides = sides_labels.get(
        sides_value,
        sides_value,
    )

    copies = config.get(
        "copies",
        1,
    )

    copy_word = (
        "copy"
        if copies == 1
        else "copies"
    )

    return (
        f"{media}, {color}, {sides}, "
        f"{copies} {copy_word}"
    )




def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        log(f"Configuration unavailable: {exc}")
        return {}


def configured(config):
    base_required = (
        "nextcloudUsername",
        "nextcloudAppPassword",
    )

    if not all(
        str(config.get(key, "")).strip()
        for key in base_required
    ):
        return False

    mode = str(
        config.get(
            "printerMode",
            "manual",
        )
    ).strip()

    if mode == "uuid-discovery":
        return all(
            str(config.get(key, "")).strip()
            for key in (
                "printerDiscoveryCidr",
                "printerUuid",
            )
        )

    return bool(
        str(
            config.get(
                "printerUrl",
                "",
            )
        ).strip()
    )


def auth_header(username, password):
    raw = f"{username}:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def nextcloud_base_url():
    address = os.environ.get(
        "NEXTCLOUD_BRIDGE_ADDRESS",
        "",
    ).strip()

    if not address:
        raise RuntimeError(
            "StartOS did not provide the Nextcloud bridge address."
        )

    # StartOS normally supplies host:port.
    # Accept a complete URL defensively as well.
    if address.startswith("http://") or address.startswith("https://"):
        return address.rstrip("/")

    return "http://" + address.rstrip("/")


def dav_request(config, method, url, headers=None, data=None, timeout=30):
    host_header = os.environ.get(
        "NEXTCLOUD_HOST_HEADER",
        "",
    ).strip()

    if not host_header:
        raise RuntimeError(
            "StartOS did not provide the Nextcloud HTTP host identity."
        )

    request_headers = {
        "Authorization": auth_header(
            config["nextcloudUsername"],
            config["nextcloudAppPassword"],
        ),
        "Host": host_header,
    }

    if headers:
        request_headers.update(headers)

    request = urllib.request.Request(
        url,
        data=data,
        headers=request_headers,
        method=method,
    )

    return urllib.request.urlopen(
        request,
        timeout=timeout,
    )


def dav_root(config):
    base = nextcloud_base_url()

    user = urllib.parse.quote(
        config["nextcloudUsername"],
        safe="",
    )

    return f"{base}/remote.php/dav/files/{user}"


def inbox_url(config):
    return dav_root(config) + "/Cloud%20Print/Inbox/"

def processing_url(config):
    return (
        dav_root(config)
        + "/Cloud%20Print/Processing/"
    )



def absolute_dav_url(config, href):
    base = nextcloud_base_url()

    # Nextcloud may return absolute WebDAV hrefs containing
    # its externally visible hostname. Preserve only the path
    # and route the request back through the StartOS bridge.
    parsed = urllib.parse.urlsplit(href)

    if parsed.scheme or parsed.netloc:
        path = parsed.path or "/"

        if parsed.query:
            path += "?" + parsed.query
    else:
        path = href

    if not path.startswith("/"):
        path = "/" + path

    return base + path


def find_supported_job(config):
    req_headers = {"Depth": "1"}

    try:
        with dav_request(
            config,
            "PROPFIND",
            inbox_url(config),
            headers=req_headers,
        ) as response:
            xml_data = response.read()
    except Exception as exc:
        log(f"Unable to check Inbox: {exc}")
        return None

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as exc:
        log(f"Invalid WebDAV response: {exc}")
        return None

    for response in root.findall(f"{DAV_NS}response"):
        href_node = response.find(f"{DAV_NS}href")

        if href_node is None or not href_node.text:
            continue

        href = href_node.text

        if href.lower().endswith((".jpg", ".jpeg", ".pdf", ".png", ".bmp", ".tif", ".tiff", ".webp", ".txt", ".doc", ".docx", ".odt", ".rtf", ".xls", ".xlsx", ".ods", ".ppt", ".pptx", ".odp")):
            return href

    return None

def find_processing_jobs(config):
    req_headers = {"Depth": "1"}

    try:
        with dav_request(
            config,
            "PROPFIND",
            processing_url(config),
            headers=req_headers,
        ) as response:
            xml_data = response.read()
    except Exception as exc:
        log(
            f"Unable to check Processing: {exc}"
        )
        return None

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as exc:
        log(
            f"Invalid Processing WebDAV response: {exc}"
        )
        return None

    jobs = []

    for response in root.findall(
        f"{DAV_NS}response"
    ):
        href_node = response.find(
            f"{DAV_NS}href"
        )

        if (
            href_node is None
            or not href_node.text
        ):
            continue

        href = href_node.text

        if href.rstrip("/").endswith(
            "/Processing"
        ):
            continue

        if "/Processing/" not in href:
            continue

        jobs.append(href)

    return jobs



def replace_queue_folder(href, old_folder, new_folder):
    old = f"/{old_folder}/"
    new = f"/{new_folder}/"

    if old not in href:
        raise ValueError(
            f"Expected {old_folder} folder in WebDAV path: {href}"
        )

    return href.replace(old, new, 1)


def move_dav_file(config, source_href, destination_href):
    source_url = absolute_dav_url(config, source_href)
    destination_url = absolute_dav_url(config, destination_href)

    try:
        with dav_request(
            config,
            "MOVE",
            source_url,
            headers={
                "Destination": destination_url,
                "Overwrite": "F",
            },
        ) as response:
            return response.status in (201, 204)

    except urllib.error.HTTPError as exc:
        log(f"MOVE failed with HTTP {exc.code}")
        return False

    except Exception as exc:
        log(f"MOVE failed: {exc}")
        return False


def claim_job(config, inbox_href):
    processing_href = replace_queue_folder(
        inbox_href,
        "Inbox",
        "Processing",
    )

    log(f"Claiming: {job_display_name(inbox_href)}")

    if not move_dav_file(config, inbox_href, processing_href):
        return None

    log(
        f"Claimed: {job_display_name(processing_href)} "
        "-> Processing"
    )
    log(
        "Print settings: "
        + print_settings_summary(config)
    )
    return processing_href


def ipp_attribute(tag, name, value):
    name_bytes = name.encode("utf-8")
    value_bytes = value.encode("utf-8")

    return (
        bytes([tag])
        + struct.pack("!H", len(name_bytes))
        + name_bytes
        + struct.pack("!H", len(value_bytes))
        + value_bytes
    )


def build_ipp_print_job(printer_uri, jpeg_data):
    request_id = int(time.time()) & 0x7FFFFFFF

    ipp = bytearray()

    # IPP/1.1, Print-Job operation (0x0002), request ID
    ipp += b"\x01\x01"
    ipp += b"\x00\x02"
    ipp += struct.pack("!I", request_id)

    # operation-attributes-tag
    ipp += b"\x01"

    ipp += ipp_attribute(
        0x47,
        "attributes-charset",
        "utf-8",
    )

    ipp += ipp_attribute(
        0x48,
        "attributes-natural-language",
        "en",
    )

    ipp += ipp_attribute(
        0x45,
        "printer-uri",
        printer_uri,
    )

    ipp += ipp_attribute(
        0x42,
        "requesting-user-name",
        "cloud-print-bridge",
    )

    ipp += ipp_attribute(
        0x42,
        "job-name",
        "Nextcloud Cloud Print",
    )

    ipp += ipp_attribute(
        0x49,
        "document-format",
        "image/jpeg",
    )

    # end-of-attributes-tag
    ipp += b"\x03"

    ipp += jpeg_data

    return bytes(ipp)


def printer_http_url(printer_uri):
    parsed = urllib.parse.urlsplit(printer_uri)

    if parsed.scheme == "ipp":
        scheme = "http"
    elif parsed.scheme == "ipps":
        scheme = "https"
    else:
        raise ValueError(
            "Printer URL must begin with ipp:// or ipps://"
        )

    hostname = parsed.hostname

    if not hostname:
        raise ValueError("Printer URL has no hostname")

    port = parsed.port or 631
    path = parsed.path or "/ipp"

    return urllib.parse.urlunsplit(
        (
            scheme,
            f"{hostname}:{port}",
            path,
            parsed.query,
            "",
        )
    )



PRINTER_DISCOVERY_PORT = 631
PRINTER_DISCOVERY_WORKERS = 64
PRINTER_CONNECT_TIMEOUT = 0.75
PRINTER_QUERY_TIMEOUT = 3
MAX_DISCOVERY_HOSTS = 4096

_printer_uri_cache = {}


def build_ipp_get_printer_attributes(printer_uri):
    request_id = (
        int(time.time() * 1000)
        & 0x7FFFFFFF
    )

    body = bytearray()

    # IPP/1.1
    body += b"\x01\x01"

    # Get-Printer-Attributes operation
    body += b"\x00\x0b"

    body += struct.pack(
        "!I",
        request_id,
    )

    # Operation attributes
    body += b"\x01"

    body += ipp_attribute(
        0x47,
        "attributes-charset",
        "utf-8",
    )

    body += ipp_attribute(
        0x48,
        "attributes-natural-language",
        "en",
    )

    body += ipp_attribute(
        0x45,
        "printer-uri",
        printer_uri,
    )

    body += b"\x03"

    return bytes(body)


def parse_ipp_attributes(data):
    if len(data) < 8:
        return {}

    status = struct.unpack(
        "!H",
        data[2:4],
    )[0]

    if status >= 0x0100:
        return {}

    attributes = {}
    offset = 8
    last_name = None

    while offset < len(data):
        tag = data[offset]
        offset += 1

        if tag == 0x03:
            break

        # Delimiter/group tags.
        if tag <= 0x0F:
            last_name = None
            continue

        if offset + 2 > len(data):
            break

        name_length = struct.unpack(
            "!H",
            data[offset:offset + 2],
        )[0]
        offset += 2

        if offset + name_length > len(data):
            break

        if name_length:
            last_name = data[
                offset:offset + name_length
            ].decode(
                "utf-8",
                errors="replace",
            )

        offset += name_length

        if offset + 2 > len(data):
            break

        value_length = struct.unpack(
            "!H",
            data[offset:offset + 2],
        )[0]
        offset += 2

        if offset + value_length > len(data):
            break

        raw_value = data[
            offset:offset + value_length
        ]
        offset += value_length

        if last_name:
            value = raw_value.decode(
                "utf-8",
                errors="replace",
            )

            attributes.setdefault(
                last_name,
                [],
            ).append(value)

    return attributes


def query_printer_identity(printer_uri):
    target_url = printer_http_url(
        printer_uri
    )

    request = urllib.request.Request(
        target_url,
        data=build_ipp_get_printer_attributes(
            printer_uri
        ),
        headers={
            "Content-Type": "application/ipp",
            "Accept": "application/ipp",
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=PRINTER_QUERY_TIMEOUT,
    ) as response:
        response_data = response.read()

    attributes = parse_ipp_attributes(
        response_data
    )

    def first(name):
        values = attributes.get(
            name,
            [],
        )

        return (
            values[0].strip()
            if values
            else ""
        )

    return {
        "uuid": first("printer-uuid"),
        "name": first("printer-name"),
        "info": first("printer-info"),
        "model": first(
            "printer-make-and-model"
        ),
    }


def printer_uuid_matches(
    printer_uri,
    target_uuid,
):
    try:
        identity = query_printer_identity(
            printer_uri
        )

    except Exception:
        return False

    return (
        identity.get(
            "uuid",
            "",
        ).strip().lower()
        == target_uuid.strip().lower()
    )


def parse_printer_discovery_networks(value):
    if isinstance(value, (list, tuple)):
        raw_items = []
        for item in value:
            raw_items.extend(
                str(item).replace(",", " ").replace(";", " ").split()
            )
    else:
        raw_items = (
            str(value or "")
            .replace(",", " ")
            .replace(";", " ")
            .split()
        )

    networks = []
    seen = set()

    for item in raw_items:
        try:
            network = ipaddress.ip_network(item, strict=False)
        except ValueError as exc:
            raise ValueError(
                f"Invalid printer discovery network: {item}"
            ) from exc

        if network.version != 4:
            raise ValueError(
                "Printer discovery currently supports IPv4 only."
            )

        normalized = str(network)
        if normalized not in seen:
            seen.add(normalized)
            networks.append(network)

    if not networks:
        raise ValueError(
            "No printer discovery network was configured."
        )

    return networks


def scan_ipp_hosts(discovery_networks):
    networks = parse_printer_discovery_networks(discovery_networks)

    hosts = []
    seen_hosts = set()

    for network in networks:
        for address in network.hosts():
            host = str(address)

            if host in seen_hosts:
                continue

            seen_hosts.add(host)
            hosts.append(host)

            if len(hosts) > MAX_DISCOVERY_HOSTS:
                raise ValueError(
                    "Printer discovery networks contain more than "
                    f"{MAX_DISCOVERY_HOSTS} unique hosts. "
                    "Use smaller CIDR ranges."
                )

    if not hosts:
        raise ValueError(
            "Printer discovery networks contain no usable hosts."
        )

    def probe(host):
        try:
            with socket.create_connection(
                (host, PRINTER_DISCOVERY_PORT),
                timeout=PRINTER_CONNECT_TIMEOUT,
            ):
                return host
        except OSError:
            return None

    workers = min(PRINTER_DISCOVERY_WORKERS, len(hosts))

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=workers
    ) as executor:
        results = executor.map(probe, hosts)
        return [host for host in results if host is not None]




def discover_printer_by_uuid(discovery_networks, target_uuid):
    target_uuid = str(target_uuid).strip().lower()

    if not target_uuid:
        raise ValueError("Printer UUID is empty.")

    ipp_hosts = scan_ipp_hosts(discovery_networks)

    for host in ipp_hosts:
        for path in ("/ipp/print", "/ipp"):
            printer_uri = (
                f"ipp://{host}:{PRINTER_DISCOVERY_PORT}{path}"
            )

            try:
                identity = query_printer_identity(printer_uri)
            except Exception:
                continue

            if not identity:
                continue

            discovered_uuid = str(
                identity.get("uuid", "")
            ).strip().lower()

            if discovered_uuid == target_uuid:
                log(
                    "Printer UUID match found through discovery."
                )
                return printer_uri

    return None




def resolve_printer_uri(config):
    mode = str(
        config.get("printerMode", "manual")
    ).strip()

    configured_uri = str(
        config.get("printerUrl", "") or ""
    ).strip()

    if mode != "uuid-discovery":
        if not configured_uri:
            raise ValueError(
                "Printer IPP URL is not configured."
            )
        return configured_uri

    discovery_networks = str(
        config.get("printerDiscoveryCidr", "") or ""
    ).strip()

    target_uuid = str(
        config.get("printerUuid", "") or ""
    ).strip()

    if not discovery_networks:
        raise ValueError(
            "Printer discovery network(s) are not configured."
        )

    if not target_uuid:
        raise ValueError(
            "Printer UUID is not configured."
        )

    normalized_networks = ",".join(
        str(network)
        for network in parse_printer_discovery_networks(
            discovery_networks
        )
    )

    cache_key = (
        normalized_networks,
        target_uuid.lower(),
    )

    cached_uri = _printer_uri_cache.get(cache_key)

    if cached_uri:
        try:
            if printer_uuid_matches(
                cached_uri,
                target_uuid,
            ):
                return cached_uri
        except Exception:
            pass

        _printer_uri_cache.pop(cache_key, None)

    # Optional URL acts as a last-known/fast-path address,
    # but only after its UUID is verified.
    if configured_uri:
        try:
            if printer_uuid_matches(
                configured_uri,
                target_uuid,
            ):
                _printer_uri_cache[cache_key] = configured_uri
                return configured_uri
        except Exception:
            pass

    log(
        "Searching configured printer discovery network(s)..."
    )

    discovered_uri = discover_printer_by_uuid(
        normalized_networks,
        target_uuid,
    )

    if not discovered_uri:
        raise RuntimeError(
            "Configured printer UUID was not found in the "
            "configured discovery network(s)."
        )

    _printer_uri_cache[cache_key] = discovered_uri
    return discovered_uri



def submit_print_job(config, jpeg_data):
    try:
        printer_uri = resolve_printer_uri(
            config
        )
        target_url = printer_http_url(
            printer_uri
        )
        body = build_ipp_print_job(
            printer_uri,
            jpeg_data,
        )
    except Exception as exc:
        log(f"Invalid printer configuration: {exc}")
        return "failure"

    request = urllib.request.Request(
        target_url,
        data=body,
        headers={
            "Content-Type": "application/ipp",
            "Accept": "application/ipp",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=60,
        ) as response:
            response_data = response.read()

    except urllib.error.HTTPError as exc:
        log(f"Printer returned HTTP {exc.code}.")
        return "failure"

    except Exception as exc:
        # We cannot know whether the printer accepted the document before
        # the connection failed. Report an ambiguous result so the caller
        # can quarantine the source without automatically reprinting it.
        log(f"Printer connection became ambiguous: {exc}")
        return "ambiguous"

    if len(response_data) < 8:
        log("Printer returned an invalid IPP response.")
        return "ambiguous"

    status = struct.unpack("!H", response_data[2:4])[0]

    # IPP success status codes occupy 0x0000-0x00FF.
    if status < 0x0100:
        log(f"Printer accepted job. IPP status 0x{status:04x}.")
        return "success"

    log(f"Printer rejected job. IPP status 0x{status:04x}.")
    return "failure"


def finalize_job(config, processing_href, folder):
    destination_href = replace_queue_folder(
        processing_href,
        "Processing",
        folder,
    )

    if move_dav_file(config, processing_href, destination_href):
        log(
            f"Completed: "
            f"{job_display_name(processing_href)} "
            f"-> {folder}"
        )
        return True

    log(
        f"WARNING: Could not move job to {folder}; "
        "it remains in Processing."
    )
    return False

def cleanup_orphaned_processing_jobs(config):
    jobs = find_processing_jobs(config)

    if jobs is None:
        return False

    if not jobs:
        return True

    count = len(jobs)

    log(
        f"Found {count} orphaned Processing "
        f"job{'s' if count != 1 else ''}."
    )

    all_moved = True

    for processing_href in jobs:
        log(
            "Unconfirmed orphaned job: "
            f"{job_display_name(processing_href)}. "
            "Moving to Failed without automatic retry."
        )

        if not finalize_job(
            config,
            processing_href,
            "Failed",
        ):
            all_moved = False

    return all_moved


def fail_unconfirmed_print_job(
    config,
    processing_href,
    detail,
):
    log(
        f"Unconfirmed print outcome: {detail}"
    )
    log(
        "Some pages or copies may already have printed. "
        "The job will not be retried automatically."
    )

    finalize_job(
        config,
        processing_href,
        "Failed",
    )





def download_source(config, href):
    url = absolute_dav_url(
        config,
        href,
    )

    try:
        with dav_request(
            config,
            "GET",
            url,
            timeout=120,
        ) as response:

            declared_length = (
                response.headers.get(
                    "Content-Length"
                )
            )

            if declared_length:
                try:
                    declared_bytes = int(
                        declared_length
                    )
                except ValueError:
                    declared_bytes = None

                if (
                    declared_bytes is not None
                    and declared_bytes
                    > MAX_SOURCE_BYTES
                ):
                    raise PermanentJobError(
                        "Source file exceeds the "
                        f"{MAX_SOURCE_BYTES // (1024 * 1024)} MiB "
                        "print-job limit."
                    )

            data = bytearray()

            while True:
                chunk = response.read(
                    DOWNLOAD_CHUNK_BYTES
                )

                if not chunk:
                    break

                data.extend(chunk)

                if len(data) > MAX_SOURCE_BYTES:
                    raise PermanentJobError(
                        "Source file exceeds the "
                        f"{MAX_SOURCE_BYTES // (1024 * 1024)} MiB "
                        "print-job limit."
                    )

    except PermanentJobError:
        raise

    except Exception as exc:
        log(
            f"Unable to download claimed job: {exc}"
        )
        return None

    if len(data) < 10:
        raise PermanentJobError(
            "Downloaded source file is empty "
            "or unexpectedly small."
        )

    log(
        "Downloaded source file: "
        + human_size(len(data))
    )

    return data



def source_extension(href):
    path = urllib.parse.urlsplit(href).path
    return os.path.splitext(path)[1].lower()


def image_to_jpeg_pages(source_data, extension):
    try:
        image = Image.open(io.BytesIO(source_data))

        if extension in (".tif", ".tiff"):
            frames = ImageSequence.Iterator(image)
        else:
            frames = [image]

        pages = []

        for frame in frames:
            frame.load()
            rgb = frame.convert("RGB")

            output = io.BytesIO()
            rgb.save(
                output,
                format="JPEG",
                quality=92,
                optimize=True,
            )

            pages.append(output.getvalue())

        image.close()

        if not pages:
            raise ValueError("Image contains no printable pages")

        return pages

    except Exception as exc:
        log(f"Image conversion failed: {exc}")
        return None


def pdf_to_jpeg_pages(source_data):
    try:
        with tempfile.TemporaryDirectory(
            prefix="cloud-print-pdf-"
        ) as workdir:

            source_path = os.path.join(workdir, "document.pdf")
            output_pattern = os.path.join(
                workdir,
                "page-%04d.jpg",
            )

            with open(source_path, "wb") as f:
                f.write(source_data)

            command = [
                "gs",
                "-q",
                "-dSAFER",
                "-dBATCH",
                "-dNOPAUSE",
                "-sDEVICE=jpeg",
                "-r150",
                "-dJPEGQ=92",
                f"-sOutputFile={output_pattern}",
                source_path,
            ]

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=180,
                check=False,
            )

            if result.returncode != 0:
                message = result.stderr.decode(
                    "utf-8",
                    errors="replace",
                ).strip()

                log(
                    "PDF conversion failed"
                    + (f": {message}" if message else "")
                )
                return None

            filenames = sorted(
                name
                for name in os.listdir(workdir)
                if name.startswith("page-")
                and name.endswith(".jpg")
            )

            if not filenames:
                log("PDF conversion produced no pages.")
                return None

            pages = []

            for filename in filenames:
                page_path = os.path.join(workdir, filename)

                with open(page_path, "rb") as f:
                    page = f.read()

                if not page.startswith(b"\xff\xd8\xff"):
                    log(
                        f"Ghostscript produced an invalid JPEG: "
                        f"{filename}"
                    )
                    return None

                pages.append(page)

            return pages

    except subprocess.TimeoutExpired:
        log("PDF conversion timed out.")
        return None

    except Exception as exc:
        log(f"PDF conversion failed: {exc}")
        return None



def text_to_pdf(source_data, config):
    try:
        try:
            text = source_data.decode(
                "utf-8-sig"
            )

            encoding = "UTF-8"

        except UnicodeDecodeError:
            text = source_data.decode(
                "cp1252"
            )

            encoding = "Windows-1252"

        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        media_specs = {
            "na_letter_8.5x11in": (
                612,
                792,
            ),
            "iso_a4_210x297mm": (
                595.276,
                841.890,
            ),
            "na_legal_8.5x14in": (
                612,
                1008,
            ),
            "na_executive_7.25x10.5in": (
                522,
                756,
            ),
            "iso_a5_148x210mm": (
                419.528,
                595.276,
            ),
            "iso_a6_105x148mm": (
                297.638,
                419.528,
            ),
            "iso_b5_176x250mm": (
                498.898,
                708.661,
            ),
        }

        media = config.get(
            "media",
            "na_letter_8.5x11in",
        )

        if media not in media_specs:
            media = "na_letter_8.5x11in"

        page_width, page_height = (
            media_specs[media]
        )

        font_path = (
            "/usr/share/fonts/truetype/"
            "dejavu/DejaVuSansMono.ttf"
        )

        if not os.path.exists(font_path):
            log(
                "TXT renderer font is missing."
            )
            return None

        font_name = "CloudPrintMono"
        font_size = 10.0
        line_height = 12.0

        margin_left = 36.0
        margin_right = 36.0
        margin_top = 36.0
        margin_bottom = 36.0

        usable_width = (
            page_width
            - margin_left
            - margin_right
        )

        pdfmetrics.registerFont(
            TTFont(
                font_name,
                font_path,
            )
        )

        character_width = (
            pdfmetrics.stringWidth(
                "M",
                font_name,
                font_size,
            )
        )

        max_characters = max(
            1,
            int(
                usable_width
                / character_width
            ),
        )

        output = io.BytesIO()

        pdf = canvas.Canvas(
            output,
            pagesize=(
                page_width,
                page_height,
            ),
            pageCompression=1,
        )

        y = (
            page_height
            - margin_top
            - font_size
        )

        page_number = 1
        lines_on_page = 0

        def begin_page():
            nonlocal y
            nonlocal lines_on_page

            pdf.setFont(
                font_name,
                font_size,
            )

            y = (
                page_height
                - margin_top
                - font_size
            )

            lines_on_page = 0

        def next_page():
            nonlocal page_number

            pdf.showPage()
            page_number += 1
            begin_page()

        def draw_line(line):
            nonlocal y
            nonlocal lines_on_page

            if (
                y
                < margin_bottom
                + line_height
            ):
                next_page()

            pdf.drawString(
                margin_left,
                y,
                line,
            )

            y -= line_height
            lines_on_page += 1

        begin_page()

        # Normalize Windows and old-Mac
        # newline conventions.
        text = (
            text
            .replace("\r\n", "\n")
            .replace("\r", "\n")
        )

        # A form-feed in a plain-text file
        # becomes an explicit page break.
        sections = text.split("\f")

        for section_number, section in enumerate(
            sections
        ):
            if section_number > 0:
                next_page()

            logical_lines = section.split("\n")

            for logical_line in logical_lines:
                line = logical_line.expandtabs(4)

                if not line:
                    draw_line("")
                    continue

                # DejaVu Sans Mono is fixed-width,
                # so character-based wrapping keeps
                # indentation and whitespace intact.
                for offset in range(
                    0,
                    len(line),
                    max_characters,
                ):
                    draw_line(
                        line[
                            offset:
                            offset + max_characters
                        ]
                    )

        pdf.save()

        pdf_data = output.getvalue()

        if (
            len(pdf_data) < 100
            or not pdf_data.startswith(
                b"%PDF-"
            )
        ):
            log(
                "TXT renderer produced an "
                "invalid PDF."
            )
            return None

        log(
            f"Rendered TXT using {encoding}: "
            f"{page_number} page(s), "
            f"{len(pdf_data)} PDF bytes."
        )

        return pdf_data

    except Exception as exc:
        log(
            f"TXT rendering failed: {exc}"
        )
        return None


def office_to_pdf(href, source_data):
    extension = source_extension(href)

    supported = (
        ".doc",
        ".docx",
        ".odt",
        ".rtf",
        ".xls",
        ".xlsx",
        ".ods",
        ".ppt",
        ".pptx",
        ".odp",
    )

    if extension not in supported:
        log(
            f"Unsupported Office document type: "
            f"{extension}"
        )
        return None

    try:
        with tempfile.TemporaryDirectory(
            prefix="cloud-print-office-"
        ) as workdir:

            input_dir = os.path.join(
                workdir,
                "input",
            )

            output_dir = os.path.join(
                workdir,
                "output",
            )

            profile_dir = os.path.join(
                workdir,
                "profile",
            )

            home_dir = os.path.join(
                workdir,
                "home",
            )

            tmp_dir = os.path.join(
                workdir,
                "tmp",
            )

            os.makedirs(input_dir)
            os.makedirs(output_dir)
            os.makedirs(profile_dir)
            os.makedirs(home_dir)
            os.makedirs(tmp_dir)

            source_path = os.path.join(
                input_dir,
                "document" + extension,
            )

            with open(source_path, "wb") as f:
                f.write(source_data)

            profile_uri = (
                "file://" + profile_dir
            )

            command = [
                "soffice",
                (
                    "-env:UserInstallation="
                    + profile_uri
                ),
                "--headless",
                "--nologo",
                "--nodefault",
                "--nofirststartwizard",
                "--norestore",
                "--convert-to",
                "pdf",
                "--outdir",
                output_dir,
                source_path,
            ]

            environment = os.environ.copy()

            # Keep every LibreOffice conversion
            # isolated from previous jobs.
            environment["HOME"] = home_dir
            environment["TMPDIR"] = tmp_dir

            log(
                f"Converting {extension} "
                "document to PDF..."
            )

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=180,
                check=False,
                env=environment,
                cwd=workdir,
            )

            stdout = result.stdout.decode(
                "utf-8",
                errors="replace",
            ).strip()

            stderr = result.stderr.decode(
                "utf-8",
                errors="replace",
            ).strip()

            if result.returncode != 0:
                details = (
                    stderr
                    or stdout
                    or "unknown conversion error"
                )

                log(
                    "LibreOffice conversion failed: "
                    f"{details}"
                )
                return None

            pdf_files = sorted(
                name
                for name in os.listdir(
                    output_dir
                )
                if name.lower().endswith(
                    ".pdf"
                )
            )

            if len(pdf_files) != 1:
                details = (
                    stdout
                    or stderr
                    or "no diagnostic output"
                )

                log(
                    "LibreOffice did not produce "
                    "exactly one PDF: "
                    f"{details}"
                )
                return None

            pdf_path = os.path.join(
                output_dir,
                pdf_files[0],
            )

            with open(pdf_path, "rb") as f:
                pdf_data = f.read()

            if (
                len(pdf_data) < 100
                or not pdf_data.startswith(
                    b"%PDF-"
                )
            ):
                log(
                    "LibreOffice output is not "
                    "a valid PDF."
                )
                return None

            log(
                f"Converted {extension} to "
                f"{len(pdf_data)} bytes of PDF."
            )

            return pdf_data

    except subprocess.TimeoutExpired:
        log(
            "LibreOffice conversion timed out. "
            "Job will not be printed."
        )
        return None

    except Exception as exc:
        log(
            "LibreOffice conversion failed: "
            f"{exc}"
        )
        return None


def pdf_page_selection_from_href(href):
    path = urllib.parse.urlparse(href).path
    filename = urllib.parse.unquote(
        os.path.basename(path)
    )

    matches = list(
        re.finditer(
            r"\[pages\s*=\s*([^\]]*)\]",
            filename,
            flags=re.IGNORECASE,
        )
    )

    if not matches:
        # Catch an attempted but malformed/unclosed
        # directive rather than silently printing
        # the entire PDF.
        if re.search(
            r"\[pages\s*=",
            filename,
            flags=re.IGNORECASE,
        ):
            raise PermanentJobError(
                "Invalid PDF page-selection directive. "
                "Use forms such as [pages=3-4] or "
                "[pages=1-3,8,12-15]."
            )

        return None

    if len(matches) != 1:
        raise PermanentJobError(
            "Only one PDF page-selection directive is "
            "supported per filename."
        )

    expression = matches[0].group(1).strip()

    if not expression:
        raise PermanentJobError(
            "PDF page-selection directive is empty."
        )

    selections = []
    previous_end = 0

    for raw_part in expression.split(","):
        part = raw_part.strip()

        match = re.fullmatch(
            r"(\d+)(?:\s*-\s*(\d+))?",
            part,
        )

        if match is None:
            raise PermanentJobError(
                "Invalid PDF page-selection directive. "
                "Use page numbers and ascending ranges, "
                "for example [pages=1-3,8,12-15]."
            )

        first_page = int(match.group(1))
        last_page = (
            int(match.group(2))
            if match.group(2) is not None
            else first_page
        )

        if first_page < 1:
            raise PermanentJobError(
                "PDF page selections must start at "
                "page 1 or later."
            )

        if last_page < first_page:
            raise PermanentJobError(
                "PDF page ranges must be ascending."
            )

        if first_page <= previous_end:
            raise PermanentJobError(
                "PDF page selections must be ascending "
                "and non-overlapping."
            )

        selections.append(
            (
                first_page,
                last_page,
            )
        )
        previous_end = last_page

    return selections

def pdf_page_count(source_path):
    escaped_path = (
        source_path
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )

    program = (
        "<<>> .PDFInit "
        "dup "
        f"({escaped_path}) exch .PDFFile "
        "dup .PDFInfo /NumPages get = "
        ".PDFClose "
        "quit"
    )

    command = [
        "gs",
        "-q",
        "-dSAFER",
        "-dNODISPLAY",
        f"--permit-file-read={source_path}",
        "-c",
        program,
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )

    except subprocess.TimeoutExpired:
        log(
            "PDF page-count check timed out."
        )
        return None

    if result.returncode != 0:
        message = result.stderr.decode(
            "utf-8",
            errors="replace",
        ).strip()

        log(
            "Unable to determine PDF page count"
            + (
                f": {message}"
                if message
                else ""
            )
        )
        return None

    output = result.stdout.decode(
        "utf-8",
        errors="replace",
    )

    for line in reversed(
        output.splitlines()
    ):
        line = line.strip()

        try:
            pages = int(line)

            if pages > 0:
                return pages

        except ValueError:
            continue

    log(
        "Ghostscript returned no valid "
        "PDF page count."
    )

    return None


def pdf_extract_selected_pages(
    source_data,
    page_selection,
):
    if page_selection is None:
        return source_data

    try:
        with tempfile.TemporaryDirectory(
            prefix="cloud-print-page-selection-"
        ) as workdir:

            source_path = os.path.join(
                workdir,
                "source.pdf",
            )

            selected_path = os.path.join(
                workdir,
                "selected.pdf",
            )

            with open(source_path, "wb") as f:
                f.write(source_data)

            page_count = pdf_page_count(
                source_path
            )

            if page_count is None:
                log(
                    "PDF validation failed before "
                    "page selection."
                )
                return None

            if page_count > MAX_PDF_PAGES:
                log(
                    f"PDF contains {page_count} pages; "
                    f"maximum is {MAX_PDF_PAGES}."
                )
                return None

            selected_pages = 0
            page_parts = []

            for first_page, last_page in page_selection:
                if last_page > page_count:
                    requested = (
                        str(first_page)
                        if first_page == last_page
                        else f"{first_page}-{last_page}"
                    )

                    log(
                        "Requested PDF page selection "
                        f"{requested} exceeds the document's "
                        f"{page_count} pages."
                    )
                    return None

                selected_pages += (
                    last_page - first_page + 1
                )

                if first_page == last_page:
                    page_parts.append(
                        str(first_page)
                    )
                else:
                    page_parts.append(
                        f"{first_page}-{last_page}"
                    )

            page_list = ",".join(page_parts)

            log(
                f"PDF source page count: {page_count}."
            )

            if len(page_selection) == 1:
                first_page, last_page = page_selection[0]

                if first_page != last_page:
                    log(
                        "PDF page range: "
                        f"{page_list} "
                        f"({selected_pages} page"
                        f"{'s' if selected_pages != 1 else ''})."
                    )
                else:
                    log(
                        "PDF page selection: "
                        f"{page_list} (1 page)."
                    )
            else:
                log(
                    "PDF page selection: "
                    f"{page_list} "
                    f"({selected_pages} pages)."
                )

            command = [
                "gs",
                "-q",
                "-dSAFER",
                "-dBATCH",
                "-dNOPAUSE",
                "-sDEVICE=pdfwrite",
                f"-sPageList={page_list}",
                f"-sOutputFile={selected_path}",
                source_path,
            ]

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=180,
                check=False,
            )

            if result.returncode != 0:
                message = result.stderr.decode(
                    "utf-8",
                    errors="replace",
                ).strip()

                log(
                    "Unable to prepare selected-page PDF"
                    + (
                        f": {message}"
                        if message
                        else ""
                    )
                )
                return None

            if not os.path.exists(selected_path):
                log(
                    "Selected-page PDF was not created."
                )
                return None

            selected_count = pdf_page_count(
                selected_path
            )

            if selected_count != selected_pages:
                log(
                    "Selected-page PDF validation failed: "
                    f"expected {selected_pages} pages, "
                    f"found {selected_count}."
                )
                return None

            with open(selected_path, "rb") as f:
                selected_data = f.read()

            if not selected_data:
                log(
                    "Selected-page PDF is empty."
                )
                return None

            log(
                "Prepared selected-page PDF: "
                f"{selected_count} page"
                f"{'s' if selected_count != 1 else ''}, "
                f"{len(selected_data)} bytes."
            )

            return selected_data

    except subprocess.TimeoutExpired:
        log(
            "PDF page-selection conversion timed out."
        )
        return None

    except Exception as exc:
        log(
            "PDF page-selection conversion failed: "
            f"{exc}"
        )
        return None


def pdf_to_pwg_raster(source_data, config):
    media_specs = {
        "na_letter_8.5x11in": (612, 792),
        "iso_a4_210x297mm": (595.276, 841.890),
        "na_legal_8.5x14in": (612, 1008),
        "na_executive_7.25x10.5in": (522, 756),
        "iso_a5_148x210mm": (419.528, 595.276),
        "iso_a6_105x148mm": (297.638, 419.528),
        "iso_b5_176x250mm": (498.898, 708.661),
    }

    media = config.get(
        "media",
        "na_letter_8.5x11in",
    )

    if media not in media_specs:
        log(
            f"Unsupported configured media {media}; "
            "falling back to Letter."
        )
        media = "na_letter_8.5x11in"

    width_points, height_points = media_specs[media]

    color_mode = config.get(
        "colorMode",
        "color",
    )

    if color_mode == "monochrome":
        # Brother advertises sgray_8.
        cups_color_space = "18"
    else:
        # Brother advertises srgb_8.
        color_mode = "color"
        cups_color_space = "19"

    sides = config.get(
        "sides",
        "one-sided",
    )

    if sides == "two-sided-long-edge":
        duplex = "true"
        tumble = "false"

    elif sides == "two-sided-short-edge":
        duplex = "true"
        tumble = "true"

    else:
        sides = "one-sided"
        duplex = "false"
        tumble = "false"

    try:
        with tempfile.TemporaryDirectory(
            prefix="cloud-print-pwg-"
        ) as workdir:

            source_path = os.path.join(
                workdir,
                "document.pdf",
            )

            output_path = os.path.join(
                workdir,
                "document.pwg",
            )

            ppd_path = os.path.join(
                workdir,
                "printer.ppd",
            )

            with open(source_path, "wb") as f:
                f.write(source_data)

            page_count = pdf_page_count(
                source_path
            )

            if page_count is None:
                log(
                    "PDF validation failed before "
                    "rasterization."
                )
                return None

            if page_count > MAX_PDF_PAGES:
                log(
                    f"PDF contains {page_count} pages; "
                    f"maximum is {MAX_PDF_PAGES}."
                )
                return None

            log(
                f"PDF page count: {page_count}."
            )

            # The Brother advertises:
            #
            #   pwg-raster-document-sheet-back = rotated
            #
            # The Ghostscript CUPS raster device obtains that
            # backside transformation through the PPD.
            ppd = """*PPD-Adobe: "4.3"
*FormatVersion: "4.3"
*FileVersion: "1.0"
*LanguageVersion: English
*LanguageEncoding: ISOLatin1
*PCFileName: "BROTHER.PPD"
*Manufacturer: "Brother"
*Product: "(Cloud Print Bridge)"
*ModelName: "Cloud Print Bridge PWG Printer"
*NickName: "Cloud Print Bridge PWG Printer"
*ShortNickName: "Cloud Print Bridge"
*ColorDevice: True
*DefaultColorSpace: RGB
*LanguageLevel: "3"
*cupsBackSide: Rotated
"""

            with open(
                ppd_path,
                "w",
                encoding="utf-8",
            ) as f:
                f.write(ppd)

            command = [
                "gs",
                "-q",
                "-dSAFER",
                "-dBATCH",
                "-dNOPAUSE",
                "-dFIXEDMEDIA",
                "-dPDFFitPage",
                "-sDEVICE=cups",
                "-sMediaClass=PwgRaster",
                "-sOutputType=Automatic",
                "-r600x600",
                f"-dDEVICEWIDTHPOINTS={width_points}",
                f"-dDEVICEHEIGHTPOINTS={height_points}",
                "-dcupsBitsPerColor=8",
                "-dcupsColorOrder=0",
                f"-dcupsColorSpace={cups_color_space}",
                "-dcupsCompression=0",
                f"-scupsPageSizeName={media}",
                f"-dDuplex={duplex}",
                f"-dTumble={tumble}",
                f"-sOutputFile={output_path}",
            ]

            command.append(source_path)

            environment = os.environ.copy()
            environment["PPD"] = ppd_path

            log(
                "Rasterizing PDF: "
                f"media={media}, "
                f"color={color_mode}, "
                f"sides={sides}"
            )

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=180,
                check=False,
                env=environment,
            )

            if result.returncode != 0:
                message = result.stderr.decode(
                    "utf-8",
                    errors="replace",
                ).strip()

                log(
                    "PWG Raster conversion failed"
                    + (
                        f": {message}"
                        if message
                        else ""
                    )
                )
                return None

            if not os.path.exists(output_path):
                log(
                    "PWG Raster conversion "
                    "produced no output."
                )
                return None

            with open(output_path, "rb") as f:
                pwg_data = f.read()

            if len(pwg_data) < 100:
                log(
                    "PWG Raster output is "
                    "unexpectedly small."
                )
                return None

            log(
                f"Converted PDF to "
                f"{len(pwg_data)} bytes "
                f"of PWG Raster."
            )

            return pwg_data

    except subprocess.TimeoutExpired:
        log("PWG Raster conversion timed out.")
        return None

    except Exception as exc:
        log(
            f"PWG Raster conversion failed: {exc}"
        )
        return None



def convert_to_jpeg_pages(href, source_data):
    extension = source_extension(href)

    if extension in (".jpg", ".jpeg"):
        if not source_data.startswith(b"\xff\xd8\xff"):
            log("JPEG signature is invalid.")
            return None

        return [source_data]

    if extension == ".pdf":
        return pdf_to_jpeg_pages(source_data)

    if extension in (
        ".png",
        ".bmp",
        ".tif",
        ".tiff",
        ".webp",
    ):
        return image_to_jpeg_pages(
            source_data,
            extension,
        )

    log(f"Unsupported file type: {extension}")
    return None




IPP_JOB_PENDING = 3
IPP_JOB_PENDING_HELD = 4
IPP_JOB_PROCESSING = 5
IPP_JOB_PROCESSING_STOPPED = 6
IPP_JOB_CANCELED = 7
IPP_JOB_ABORTED = 8
IPP_JOB_COMPLETED = 9


def ipp_integer_attribute(name, value):
    name_bytes = name.encode("utf-8")

    return (
        b"\x21"
        + struct.pack("!H", len(name_bytes))
        + name_bytes
        + struct.pack("!H", 4)
        + struct.pack("!i", int(value))
    )


def ipp_boolean_attribute(name, value):
    name_bytes = name.encode("utf-8")

    return (
        b"\x22"
        + struct.pack("!H", len(name_bytes))
        + name_bytes
        + struct.pack("!H", 1)
        + (b"\x01" if value else b"\x00")
    )


def ipp_multi_attribute(tag, name, values):
    values = list(values)

    if not values:
        return b""

    result = bytearray()

    for index, value in enumerate(values):
        name_bytes = (
            name.encode("utf-8")
            if index == 0
            else b""
        )
        value_bytes = str(value).encode("utf-8")

        result += bytes([tag])
        result += struct.pack("!H", len(name_bytes))
        result += name_bytes
        result += struct.pack("!H", len(value_bytes))
        result += value_bytes

    return bytes(result)


def parse_ipp_typed_attributes(data):
    if len(data) < 8:
        return None, {}

    status = struct.unpack(
        "!H",
        data[2:4],
    )[0]

    attributes = {}
    offset = 8
    last_name = None

    while offset < len(data):
        tag = data[offset]
        offset += 1

        if tag == 0x03:
            break

        if tag <= 0x0F:
            last_name = None
            continue

        if offset + 2 > len(data):
            break

        name_length = struct.unpack(
            "!H",
            data[offset:offset + 2],
        )[0]
        offset += 2

        if offset + name_length > len(data):
            break

        if name_length:
            last_name = data[
                offset:offset + name_length
            ].decode(
                "utf-8",
                errors="replace",
            )

        offset += name_length

        if offset + 2 > len(data):
            break

        value_length = struct.unpack(
            "!H",
            data[offset:offset + 2],
        )[0]
        offset += 2

        if offset + value_length > len(data):
            break

        raw_value = data[
            offset:offset + value_length
        ]
        offset += value_length

        if not last_name:
            continue

        if tag in (0x21, 0x23) and value_length == 4:
            value = struct.unpack(
                "!i",
                raw_value,
            )[0]
        elif tag == 0x22 and value_length == 1:
            value = raw_value != b"\x00"
        else:
            value = raw_value.decode(
                "utf-8",
                errors="replace",
            )

        attributes.setdefault(
            last_name,
            [],
        ).append(value)

    return status, attributes


def ipp_first(attributes, name, default=None):
    values = attributes.get(
        name,
        [],
    )

    if not values:
        return default

    return values[0]


def send_ipp_request(printer_uri, body, timeout):
    target_url = printer_http_url(
        printer_uri
    )

    request = urllib.request.Request(
        target_url,
        data=body,
        headers={
            "Content-Type": "application/ipp",
            "Accept": "application/ipp",
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
    ) as response:
        return response.read()


def build_create_job_request(
    printer_uri,
    media,
    color_mode,
    sides,
):
    request_id = (
        int(time.time() * 1000)
        & 0x7FFFFFFF
    )

    body = bytearray()

    # IPP/1.1, Create-Job (0x0005)
    body += b"\x01\x01"
    body += b"\x00\x05"
    body += struct.pack("!I", request_id)

    # Operation attributes
    body += b"\x01"

    body += ipp_attribute(
        0x47,
        "attributes-charset",
        "utf-8",
    )

    body += ipp_attribute(
        0x48,
        "attributes-natural-language",
        "en",
    )

    body += ipp_attribute(
        0x45,
        "printer-uri",
        printer_uri,
    )

    body += ipp_attribute(
        0x42,
        "requesting-user-name",
        "cloud-print-bridge",
    )

    body += ipp_attribute(
        0x42,
        "job-name",
        "Cloud Print Bridge PDF",
    )

    body += ipp_boolean_attribute(
        "ipp-attribute-fidelity",
        True,
    )

    # Job template attributes
    body += b"\x02"

    body += ipp_attribute(
        0x44,
        "sides",
        sides,
    )

    body += ipp_attribute(
        0x44,
        "media",
        media,
    )

    body += ipp_attribute(
        0x44,
        "print-color-mode",
        color_mode,
    )

    body += b"\x03"

    return bytes(body)


def build_send_document_request(
    printer_uri,
    job_id,
    pwg_data,
):
    request_id = (
        int(time.time() * 1000)
        & 0x7FFFFFFF
    )

    body = bytearray()

    # IPP/1.1, Send-Document (0x0006)
    body += b"\x01\x01"
    body += b"\x00\x06"
    body += struct.pack("!I", request_id)

    body += b"\x01"

    body += ipp_attribute(
        0x47,
        "attributes-charset",
        "utf-8",
    )

    body += ipp_attribute(
        0x48,
        "attributes-natural-language",
        "en",
    )

    body += ipp_attribute(
        0x45,
        "printer-uri",
        printer_uri,
    )

    body += ipp_integer_attribute(
        "job-id",
        job_id,
    )

    body += ipp_attribute(
        0x42,
        "requesting-user-name",
        "cloud-print-bridge",
    )

    body += ipp_attribute(
        0x49,
        "document-format",
        "image/pwg-raster",
    )

    body += ipp_boolean_attribute(
        "last-document",
        True,
    )

    body += b"\x03"
    body += pwg_data

    return bytes(body)


def build_get_job_attributes_request(
    printer_uri,
    job_id,
):
    request_id = (
        int(time.time() * 1000)
        & 0x7FFFFFFF
    )

    body = bytearray()

    # IPP/1.1, Get-Job-Attributes (0x0009)
    body += b"\x01\x01"
    body += b"\x00\x09"
    body += struct.pack("!I", request_id)

    body += b"\x01"

    body += ipp_attribute(
        0x47,
        "attributes-charset",
        "utf-8",
    )

    body += ipp_attribute(
        0x48,
        "attributes-natural-language",
        "en",
    )

    body += ipp_attribute(
        0x45,
        "printer-uri",
        printer_uri,
    )

    body += ipp_integer_attribute(
        "job-id",
        job_id,
    )

    body += ipp_attribute(
        0x42,
        "requesting-user-name",
        "cloud-print-bridge",
    )

    body += ipp_multi_attribute(
        0x44,
        "requested-attributes",
        (
            "job-id",
            "job-uri",
            "job-state",
            "job-state-reasons",
            "job-impressions-completed",
        ),
    )

    body += b"\x03"

    return bytes(body)


def create_ipp_job(
    printer_uri,
    media,
    color_mode,
    sides,
):
    body = build_create_job_request(
        printer_uri,
        media,
        color_mode,
        sides,
    )

    try:
        response_data = send_ipp_request(
            printer_uri,
            body,
            30,
        )
    except urllib.error.HTTPError as exc:
        log(
            f"Create-Job returned HTTP {exc.code}."
        )
        return "failure", None
    except Exception as exc:
        log(
            f"Create-Job result is ambiguous: {exc}"
        )
        return "ambiguous", None

    status, attributes = parse_ipp_typed_attributes(
        response_data
    )

    if status is None:
        log(
            "Create-Job returned an invalid IPP response."
        )
        return "ambiguous", None

    if status >= 0x0100:
        log(
            f"Create-Job rejected. IPP status "
            f"0x{status:04x}."
        )
        return "failure", None

    job_id = ipp_first(
        attributes,
        "job-id",
    )

    if not isinstance(job_id, int) or job_id <= 0:
        log(
            "Create-Job succeeded but returned no valid job-id."
        )
        return "ambiguous", None

    log(
        f"Printer created IPP job {job_id}."
    )

    return "success", job_id


def get_ipp_job_status(
    printer_uri,
    job_id,
):
    body = build_get_job_attributes_request(
        printer_uri,
        job_id,
    )

    try:
        response_data = send_ipp_request(
            printer_uri,
            body,
            15,
        )
    except Exception as exc:
        log(
            f"Unable to query IPP job {job_id}: {exc}"
        )
        return None

    status, attributes = parse_ipp_typed_attributes(
        response_data
    )

    if status is None or status >= 0x0100:
        return None

    state = ipp_first(
        attributes,
        "job-state",
    )

    reasons = [
        str(value)
        for value in attributes.get(
            "job-state-reasons",
            [],
        )
    ]

    impressions = ipp_first(
        attributes,
        "job-impressions-completed",
        0,
    )

    return {
        "state": state,
        "reasons": reasons,
        "impressions": impressions,
    }


def recover_ipp_job_after_send_problem(
    printer_uri,
    job_id,
):
    # Give the printer a short opportunity to settle after
    # the document connection failed or timed out.
    for attempt in range(6):
        if attempt:
            time.sleep(5)

        info = get_ipp_job_status(
            printer_uri,
            job_id,
        )

        if not info:
            continue

        state = info.get("state")
        reasons = set(
            info.get(
                "reasons",
                [],
            )
        )

        if state == IPP_JOB_COMPLETED:
            log(
                f"IPP job {job_id} completed successfully."
            )
            return "success"

        if state in (
            IPP_JOB_CANCELED,
            IPP_JOB_ABORTED,
        ):
            log(
                f"IPP job {job_id} ended in state {state}."
            )
            return "failure"

        if state in (
            IPP_JOB_PROCESSING,
            IPP_JOB_PROCESSING_STOPPED,
        ):
            if "job-incoming" in reasons:
                log(
                    f"IPP job {job_id} is still receiving data."
                )
                continue

            # The printer owns the complete job even if it is
            # paused for paper or still physically printing.
            log(
                f"IPP job {job_id} is active on the printer."
            )
            return "success"

        # A pending job may be only the empty Create-Job shell,
        # so it is not enough evidence that the document arrived.
        if state in (
            IPP_JOB_PENDING,
            IPP_JOB_PENDING_HELD,
        ):
            continue

    log(
        f"IPP job {job_id} could not be verified after "
        "the Send-Document problem."
    )
    return "ambiguous"


PRINTER_SEND_CHUNK_BYTES = 256 * 1024
PRINTER_SEND_STALL_TIMEOUT = 300
PRINTER_SEND_RESPONSE_TIMEOUT = 300


def stream_ipp_send_document(
    printer_uri,
    prefix,
    pwg_data,
):
    target_url = printer_http_url(printer_uri)
    parsed = urllib.parse.urlsplit(target_url)

    host = parsed.hostname
    if not host:
        raise ValueError("Printer URL has no hostname.")

    if parsed.scheme == "https":
        connection_class = http.client.HTTPSConnection
        port = parsed.port or 443
    elif parsed.scheme == "http":
        connection_class = http.client.HTTPConnection
        port = parsed.port or 80
    else:
        raise ValueError("Unsupported printer HTTP scheme.")

    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query

    total_length = len(prefix) + len(pwg_data)

    connection = connection_class(
        host,
        port,
        timeout=PRINTER_SEND_STALL_TIMEOUT,
    )

    try:
        connection.putrequest("POST", path)
        connection.putheader(
            "Content-Type",
            "application/ipp",
        )
        connection.putheader(
            "Accept",
            "application/ipp",
        )
        connection.putheader(
            "Content-Length",
            str(total_length),
        )
        connection.endheaders()

        connection.send(prefix)

        view = memoryview(pwg_data)
        total_pwg_bytes = len(view)

        progress_step = 25 * 1024 * 1024
        next_progress = progress_step

        for offset in range(
            0,
            total_pwg_bytes,
            PRINTER_SEND_CHUNK_BYTES,
        ):
            if connection.sock is not None:
                connection.sock.settimeout(
                    PRINTER_SEND_STALL_TIMEOUT
                )

            end = min(
                offset + PRINTER_SEND_CHUNK_BYTES,
                total_pwg_bytes,
            )

            connection.send(
                view[offset:end]
            )

            sent = end

            if (
                sent >= next_progress
                and sent < total_pwg_bytes
            ):
                percent = round(
                    (sent * 100)
                    / total_pwg_bytes
                )

                log(
                    f"Sent {human_size(sent)} of "
                    f"{human_size(total_pwg_bytes)} "
                    f"({percent}%)."
                )

                while next_progress <= sent:
                    next_progress += progress_step

        log(
            f"PWG upload complete: "
            f"{human_size(total_pwg_bytes)}."
        )

        if connection.sock is not None:
            connection.sock.settimeout(
                PRINTER_SEND_RESPONSE_TIMEOUT
            )

        response = connection.getresponse()
        response_data = response.read()

        if not 200 <= response.status < 300:
            raise RuntimeError(
                f"Printer returned HTTP {response.status}."
            )

        return response_data

    finally:
        connection.close()



def send_pwg_document(
    printer_uri,
    job_id,
    pwg_data,
):
    # Reuse the existing IPP builder with an empty document
    # to produce only the Send-Document IPP prefix.
    prefix = build_send_document_request(
        printer_uri,
        job_id,
        b"",
    )

    log(
        "Streaming PWG Raster to IPP job "
        f"{job_id}: {human_size(len(pwg_data))}."
    )

    try:
        response_data = stream_ipp_send_document(
            printer_uri,
            prefix,
            pwg_data,
        )
    except Exception as exc:
        log(
            f"Send-Document result is uncertain: {exc}; "
            f"checking IPP job {job_id}."
        )
        return recover_ipp_job_after_send_problem(
            printer_uri,
            job_id,
        )

    status, attributes = parse_ipp_typed_attributes(
        response_data
    )

    if status is None:
        log(
            f"Send-Document returned an invalid IPP response; "
            f"checking IPP job {job_id}."
        )
        return recover_ipp_job_after_send_problem(
            printer_uri,
            job_id,
        )

    if status < 0x0100:
        state = ipp_first(
            attributes,
            "job-state",
        )

        if state is not None:
            log(
                f"Printer accepted IPP job {job_id}; "
                f"state {state}."
            )
        else:
            log(
                f"Printer accepted IPP job {job_id}."
            )

        return "success"

    log(
        f"Send-Document returned IPP status "
        f"0x{status:04x}; checking IPP job {job_id}."
    )

    return recover_ipp_job_after_send_problem(
        printer_uri,
        job_id,
    )




def submit_pwg_job(config, pwg_data):
    try:
        printer_uri = resolve_printer_uri(
            config
        )
    except Exception as exc:
        log(
            f"Unable to resolve printer: {exc}"
        )
        return "failure"

    media = config.get(
        "media",
        "na_letter_8.5x11in",
    )

    color_mode = config.get(
        "colorMode",
        "color",
    )

    if color_mode not in (
        "color",
        "monochrome",
    ):
        color_mode = "color"

    sides = config.get(
        "sides",
        "one-sided",
    )

    if sides not in (
        "one-sided",
        "two-sided-long-edge",
        "two-sided-short-edge",
    ):
        sides = "one-sided"

    create_status, job_id = create_ipp_job(
        printer_uri,
        media,
        color_mode,
        sides,
    )

    if create_status != "success":
        return create_status

    return send_pwg_document(
        printer_uri,
        job_id,
        pwg_data,
    )



def process_job(config, inbox_href):
    processing_href = claim_job(
        config,
        inbox_href,
    )

    if processing_href is None:
        return

    try:
        source_data = download_source(
            config,
            processing_href,
        )

    except PermanentJobError as exc:
        log(
            f"Rejecting print job: {exc}"
        )

        finalize_job(
            config,
            processing_href,
            "Failed",
        )
        return

    if source_data is None:
        log(
            "Download result was uncertain. "
            "Moving job to Failed without automatic retry."
        )

        finalize_job(
            config,
            processing_href,
            "Failed",
        )
        return

    extension = source_extension(
        processing_href
    )

    log(
        f"Document type: "
        f"{extension.lstrip('.').upper() or 'UNKNOWN'}"
    )

    office_extensions = (
        ".doc",
        ".docx",
        ".odt",
        ".rtf",
        ".xls",
        ".xlsx",
        ".ods",
        ".ppt",
        ".pptx",
        ".odp",
    )

    # PDF and Office documents converge on the
    # same proven PDF -> PWG Raster print path.
    page_selection = None

    if extension == ".pdf":
        try:
            page_selection = pdf_page_selection_from_href(
                processing_href
            )
        except PermanentJobError as exc:
            log(
                f"Rejecting print job: {exc}"
            )
            finalize_job(
                config,
                processing_href,
                "Failed",
            )
            return

        pdf_data = source_data

    elif extension in office_extensions:
        pdf_data = office_to_pdf(
            processing_href,
            source_data,
        )

        if pdf_data is None:
            finalize_job(
                config,
                processing_href,
                "Failed",
            )
            return

    elif extension == ".txt":
        pdf_data = text_to_pdf(
            source_data,
            config,
        )

        if pdf_data is None:
            finalize_job(
                config,
                processing_href,
                "Failed",
            )
            return

    else:
        pdf_data = None

    if pdf_data is not None:
        if page_selection is not None:
            pdf_data = pdf_extract_selected_pages(
                pdf_data,
                page_selection,
            )

            if pdf_data is None:
                finalize_job(
                    config,
                    processing_href,
                    "Failed",
                )
                return

        pwg_data = pdf_to_pwg_raster(
            pdf_data,
            config,
        )

        if pwg_data is None:
            finalize_job(
                config,
                processing_href,
                "Failed",
            )
            return

        try:
            copies = int(
                config.get(
                    "copies",
                    1,
                )
            )
        except Exception:
            copies = 1

        copies = max(
            1,
            min(
                copies,
                99,
            ),
        )

        log(
            f"Printing {copies} "
            f"cop"
            f"{'y' if copies == 1 else 'ies'}."
        )

        for copy_number in range(
            1,
            copies + 1,
        ):
            log(
                f"Submitting copy "
                f"{copy_number} of {copies}."
            )

            print_status = submit_pwg_job(
                config,
                pwg_data,
            )

            if print_status == "success":
                continue

            if (
                print_status == "failure"
                and copy_number == 1
            ):
                finalize_job(
                    config,
                    processing_href,
                    "Failed",
                )
                return

            fail_unconfirmed_print_job(
                config,
                processing_href,
                "printing stopped before all requested copies "
                "were safely confirmed complete.",
            )
            return

        finalize_job(
            config,
            processing_href,
            "Printed",
        )
        return

    # Existing image path remains unchanged.
    pages = convert_to_jpeg_pages(
        processing_href,
        source_data,
    )

    if not pages:
        finalize_job(
            config,
            processing_href,
            "Failed",
        )
        return

    log(
        f"Document contains "
        f"{len(pages)} printable page(s)."
    )

    for page_number, jpeg_data in enumerate(
        pages,
        start=1,
    ):
        log(
            f"Printing page {page_number} "
            f"of {len(pages)}..."
        )

        print_status = submit_print_job(
            config,
            jpeg_data,
        )

        if print_status == "success":
            continue

        if (
            print_status == "failure"
            and page_number == 1
        ):
            finalize_job(
                config,
                processing_href,
                "Failed",
            )
            return

        fail_unconfirmed_print_job(
            config,
            processing_href,
            "printing stopped before all image pages "
            "were safely confirmed complete.",
        )
        return

    finalize_job(
        config,
        processing_href,
        "Printed",
    )



def poll_seconds(config):
    try:
        seconds = int(config.get("pollSeconds", 30))
    except (TypeError, ValueError):
        seconds = 30

    return max(5, min(seconds, 3600))


def set_ready(is_ready):
    if is_ready:
        try:
            with open(READY_FILE, "w", encoding="utf-8") as f:
                f.write("ready\n")
        except OSError:
            pass
    else:
        try:
            os.remove(READY_FILE)
        except FileNotFoundError:
            pass
        except OSError:
            pass


def run():
    log("Cloud Print Bridge starting.")

    was_configured = None
    was_bridge_available = None
    was_ready = None
    processing_cleanup_done = False

    while True:
        config = load_config()
        is_configured = configured(config)

        bridge_available = bool(
            os.environ.get(
                "NEXTCLOUD_BRIDGE_ADDRESS",
                "",
            ).strip()
        )

        host_identity_available = bool(
            os.environ.get(
                "NEXTCLOUD_HOST_HEADER",
                "",
            ).strip()
        )

        is_ready = (
            is_configured
            and bridge_available
            and host_identity_available
        )

        if is_configured != was_configured:
            if is_configured:
                log(
                    "Configuration loaded."
                )
            else:
                log(
                    "Cloud Print Bridge is not configured. "
                    "Use the Configure action in StartOS."
                )

            was_configured = is_configured

        if bridge_available != was_bridge_available:
            if bridge_available:
                log(
                    "Nextcloud StartOS bridge "
                    "address is available."
                )
            else:
                log(
                    "Waiting for the Nextcloud "
                    "StartOS dependency bridge."
                )

            was_bridge_available = bridge_available

        if is_ready != was_ready:
            if is_ready:
                log(
                    "Print queue is active."
                )
            else:
                log(
                    "Print queue is not active."
                )

            was_ready = is_ready

        set_ready(is_ready)

        if not is_ready:
            time.sleep(5)
            continue

        if not processing_cleanup_done:
            try:
                processing_cleanup_done = (
                    cleanup_orphaned_processing_jobs(
                        config
                    )
                )
            except Exception as exc:
                log(
                    "Unable to clean orphaned Processing "
                    f"jobs: {exc}"
                )
                processing_cleanup_done = False

            if not processing_cleanup_done:
                time.sleep(
                    poll_seconds(config)
                )
                continue

        try:
            job_href = find_supported_job(
                config
            )

            if job_href:
                log(
                    f"Found print job: {job_href}"
                )
                process_job(
                    config,
                    job_href,
                )

        except Exception as exc:
            log(
                f"Unexpected worker error: {exc}"
            )

        time.sleep(
            poll_seconds(config)
        )


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        set_ready(False)
        log("Cloud Print Bridge stopped.")
