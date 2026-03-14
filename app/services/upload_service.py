import asyncio
from pathlib import Path
from uuid import UUID

from supabase import create_client

from app.config import settings

_client = create_client(settings.supabase_url, settings.supabase_service_key)

# Extensions allowed for evidence uploads
ALLOWED_EXTENSIONS = frozenset({
    ".jpg", ".jpeg",          # JPEG images
    ".png",                   # PNG images
    ".gif",                   # GIF images
    ".webp",                  # WebP images
    ".heic", ".heif",         # iPhone / modern camera (critical for Indian users)
    ".pdf",                   # PDF documents
    ".doc", ".docx",          # Word documents
    ".xls", ".xlsx",          # Excel (bank statements, invoices)
    ".txt",                   # Plain text
})

# Corresponding MIME types (browser-provided, paired with extension check)
ALLOWED_MIME_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/heic",
    "image/heif",
    "application/pdf",
    "application/msword",                                                        # .doc
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.ms-excel",                                                  # .xls
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",        # .xlsx
    "text/plain",
})


def _magic_ok(content: bytes, ext: str) -> bool:
    """Verify file magic bytes match the declared extension.

    This prevents files like 'malware.exe' renamed to 'proof.jpg' from
    passing validation. Each format has a unique byte signature.
    """
    n = len(content)
    if n < 4:
        return False

    if ext in {".jpg", ".jpeg"}:
        # JPEG: always starts with FF D8 FF
        return content[:3] == b"\xff\xd8\xff"

    if ext == ".png":
        # PNG: 8-byte signature
        return n >= 8 and content[:8] == b"\x89PNG\r\n\x1a\n"

    if ext == ".gif":
        # GIF87a or GIF89a
        return content[:6] in {b"GIF87a", b"GIF89a"}

    if ext == ".webp":
        # RIFF container with WEBP marker at offset 8
        return content[:4] == b"RIFF" and n >= 12 and content[8:12] == b"WEBP"

    if ext == ".pdf":
        # PDF header (sometimes preceded by BOM — check first 1024 bytes)
        return b"%PDF" in content[:1024]

    if ext in {".docx", ".xlsx"}:
        # Office Open XML: ZIP archive
        return content[:4] == b"PK\x03\x04"

    if ext in {".doc", ".xls"}:
        # Legacy OLE2 Compound Document
        return n >= 8 and content[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

    if ext == ".txt":
        # Plain text: no null bytes in first 512 bytes, valid UTF-8
        sample = content[:512]
        if b"\x00" in sample:
            return False
        try:
            sample.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False

    if ext in {".heic", ".heif"}:
        # ISOBMFF container: 4-byte box size + 'ftyp' + 4-byte brand
        # The ftyp box is almost always the first box (offset 4)
        if n < 12:
            return False
        if content[4:8] == b"ftyp":
            brand = content[8:12]
            return brand in {
                b"heic", b"heis", b"heix", b"heim",
                b"hevc", b"mif1", b"msf1", b"hevm", b"hevs",
            }
        return False

    return False


def is_valid_file(content: bytes, filename: str, content_type: str) -> bool:
    """Return True only if extension, MIME type, and magic bytes all agree.

    All three layers must pass:
    - Extension must be in ALLOWED_EXTENSIONS
    - MIME type must be in ALLOWED_MIME_TYPES
    - Magic bytes must match the declared extension
    """
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False
    mime = content_type.split(";")[0].strip().lower()
    if mime not in ALLOWED_MIME_TYPES:
        return False
    return _magic_ok(content, ext)


def _sync_upload(path: str, data: bytes, content_type: str) -> str:
    """Synchronous upload — must be called via asyncio.to_thread."""
    _client.storage.from_(settings.supabase_bucket).upload(
        path, data, file_options={"content-type": content_type, "upsert": "false"}
    )
    return _client.storage.from_(settings.supabase_bucket).get_public_url(path)


async def upload_file(problem_id: UUID, data: bytes, filename: str, content_type: str) -> str:
    """Upload bytes to Supabase Storage and return the public URL.

    All files for the same problem are stored under {problem_id}/{filename}.
    The supabase-py storage client is synchronous; we run it in a thread
    pool so it does not block the async event loop.
    """
    path = f"{problem_id}/{filename}"
    return await asyncio.to_thread(_sync_upload, path, data, content_type)


def _sync_delete_folder(problem_id: UUID) -> None:
    """Synchronous deletion of all files in a problem's Supabase folder.

    Supabase Storage organises files as: {problem_id}/{filename}
    bucket.list(folder) lists all objects directly inside that folder.
    We then call bucket.remove([...paths...]) to delete them.
    """
    bucket = _client.storage.from_(settings.supabase_bucket)
    folder = str(problem_id)
    try:
        files = bucket.list(folder)
    except Exception:
        # Folder doesn't exist or already empty — nothing to delete
        return
    if files:
        paths = [f"{folder}/{f['name']}" for f in files if f.get("name")]
        if paths:
            bucket.remove(paths)


async def delete_problem_files(problem_id: UUID) -> None:
    """Delete all files associated with a problem from Supabase Storage."""
    await asyncio.to_thread(_sync_delete_folder, problem_id)
