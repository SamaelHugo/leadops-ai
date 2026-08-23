from __future__ import annotations

import io
import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from ..config import get_settings


SEPARATORS = ("\n\n", "\n", ". ", " ", "")


def _recursive_split(text: str, separators: tuple[str, ...], size: int) -> list[str]:
    if len(text) <= size:
        return [text] if text else []
    separator = separators[0]
    if separator == "":
        return [text[index : index + size] for index in range(0, len(text), size)]
    remainder = separators[1:]
    output: list[str] = []
    pieces = text.split(separator)
    for index, piece in enumerate(pieces):
        fragment = piece + (separator if index < len(pieces) - 1 else "")
        if len(fragment) <= size:
            if fragment:
                output.append(fragment)
        else:
            output.extend(_recursive_split(fragment, remainder, size))
    return output


def split_text(text: str, size: int, overlap: int) -> list[str]:
    clean = " ".join(text.replace("\x00", " ").split())
    if not clean:
        return []
    pieces = _recursive_split(clean, SEPARATORS, size)
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if len(current) + len(piece) <= size:
            current += piece
            continue
        if current.strip():
            chunks.append(current.strip())
        current = (current[-overlap:] if overlap else "") + piece
    if current.strip():
        chunks.append(current.strip())
    return chunks


def extract_pdf(raw: bytes) -> tuple[str, list[int | None]]:
    reader = PdfReader(io.BytesIO(raw))
    page_texts: list[str] = []
    pages: list[int | None] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            page_texts.append(text)
            pages.append(index)
    return "\n\n".join(page_texts), pages


def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only public HTTP and HTTPS URLs are accepted.")
    if get_settings().allow_private_url_sources:
        return
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443)
    except socket.gaierror as exc:
        raise ValueError("The URL host could not be resolved.") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ValueError("Private and local network URLs are not accepted.")


def fetch_url_text(url: str) -> tuple[str, str]:
    validate_public_url(url)
    settings = get_settings()
    with httpx.Client(follow_redirects=True, timeout=20.0) as client:
        with client.stream(
            "GET",
            url,
            headers={"User-Agent": "LeadOpsAI-KnowledgeIndexer/1.0"},
        ) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                raise ValueError("The URL must return an HTML or plain text page.")
            data = bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > settings.max_url_bytes:
                    raise ValueError("The page is too large to index.")
    soup = BeautifulSoup(bytes(data), "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else url
    text = soup.get_text("\n", strip=True)
    if len(text) < 20:
        raise ValueError("No readable text was found on this page.")
    return title[:255], text

