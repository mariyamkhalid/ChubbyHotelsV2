#!/usr/bin/env python3
"""
For each row in ``hotel_images`` whose ``image_url`` is ``http``/``https``,
download the image and upload it to your S3 bucket, then set ``s3_url`` to the
public object URL.

Prerequisites
-------------
- Column ``hotel_images.s3_url`` (run ``migrate_add_hotel_image_s3_url_column.py``).
- ``pip install boto3`` (see ``requirements.txt``).
- Env: ``CHUBBY_S3_BUCKET`` (bucket name), ``AWS_REGION`` or ``AWS_DEFAULT_REGION``.
- AWS credentials (env vars, ``~/.aws/credentials``, or EC2 instance role).
- Bucket policy (or similar) so the returned HTTPS URLs are readable by your app
  (``public-read`` ACLs are often blocked; use a bucket policy on ``hotels/*``).

Usage (from ``API/``)::

    export CHUBBY_S3_BUCKET=chubbyhotels
    export AWS_REGION=us-east-2
    ./venv/bin/python upload_remote_hotel_images_to_s3.py
    ./venv/bin/python upload_remote_hotel_images_to_s3.py --db chubby.db --limit 5
    ./venv/bin/python upload_remote_hotel_images_to_s3.py --dry-run
"""

from __future__ import annotations

import argparse
import mimetypes
import os
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def _bucket() -> str:
    b = (os.getenv("CHUBBY_S3_BUCKET") or "").strip()
    if not b:
        raise SystemExit("Set CHUBBY_S3_BUCKET to your S3 bucket name.")
    return b


def _region() -> str:
    return (
        (os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1")
        .strip()
    )


def _public_s3_url(bucket: str, region: str, key: str) -> str:
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def _guess_extension(url: str, content_type: str | None) -> str:
    parsed = urlparse(url)
    path_ext = Path(parsed.path).suffix.lower()
    if path_ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".svg"}:
        return path_ext
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            return ".jpg" if ext == ".jpe" else ext
    return ".jpg"


def _safe_key_fragment(name: str) -> str:
    base = Path(name).name
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", base).strip("._") or "image"
    return cleaned[:180]


def _download(url: str, timeout: int) -> tuple[bytes, str | None]:
    req = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; chubby-s3-uploader/1.0)"},
    )
    with urlopen(req, timeout=timeout) as resp:  # nosec - URLs from our DB
        data = resp.read()
        return data, resp.headers.get("Content-Type")


def _upload_bytes(key: str, body: bytes, content_type: str) -> str:
    try:
        import boto3
    except ImportError as exc:
        raise SystemExit("Install boto3: pip install boto3") from exc

    bucket = _bucket()
    region = _region()
    client = boto3.client("s3", region_name=region)
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType=content_type or "application/octet-stream",
    )
    return _public_s3_url(bucket, region, key)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload remote hotel_images.image_url files to S3; set s3_url."
    )
    parser.add_argument("--db", default="chubby.db", help="SQLite database path")
    parser.add_argument(
        "--limit", type=int, default=0, help="Max rows to process (0 = no limit)"
    )
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without uploading or updating the DB",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-upload even when s3_url is already set",
    )
    args = parser.parse_args()

    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cols = {row[1] for row in cur.execute("PRAGMA table_info(hotel_images)").fetchall()}
    if "s3_url" not in cols:
        conn.close()
        raise SystemExit(
            "Missing column hotel_images.s3_url — run "
            "migrate_add_hotel_image_s3_url_column.py first."
        )

    rows = cur.execute(
        """
        SELECT id, hotel_id, image_url, s3_url
        FROM hotel_images
        ORDER BY id ASC
        """
    ).fetchall()

    candidates = []
    for r in rows:
        url = (r["image_url"] or "").strip()
        if not url.startswith(("http://", "https://")):
            continue
        s3 = (r["s3_url"] or "").strip()
        if s3 and not args.force:
            continue
        candidates.append(r)

    if args.limit > 0:
        candidates = candidates[: args.limit]

    if not args.dry_run:
        _bucket()  # fail fast if unset

    print(f"DB: {db_path}")
    print(f"Remote rows to process: {len(candidates)}")
    if args.dry_run:
        for r in candidates[:20]:
            print(f"  [dry-run] id={r['id']} hotel_id={r['hotel_id']} url={r['image_url'][:80]}...")
        if len(candidates) > 20:
            print(f"  ... and {len(candidates) - 20} more")
        conn.close()
        return

    ok = 0
    failed = 0
    for r in candidates:
        image_id = int(r["id"])
        hotel_id = int(r["hotel_id"])
        src_url = (r["image_url"] or "").strip()
        try:
            data, ct = _download(src_url, timeout=args.timeout)
            ext = _guess_extension(src_url, ct)
            out_ct = (
                ct.split(";")[0].strip()
                if ct
                else (mimetypes.guess_type(f"x{ext}")[0] or "application/octet-stream")
            )
            key = f"hotels/{hotel_id}/{image_id}{ext}"
            public = _upload_bytes(key, data, out_ct)
            cur.execute(
                "UPDATE hotel_images SET s3_url = ? WHERE id = ?",
                (public, image_id),
            )
            conn.commit()
            ok += 1
            print(f"[ok] id={image_id} -> {public}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            conn.rollback()
            print(f"[err] id={image_id} url={src_url[:120]}... -> {exc}")

    conn.close()
    print(f"\nDone. Uploaded: {ok}, failed: {failed}")


if __name__ == "__main__":
    main()
