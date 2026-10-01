"""Private workout, progress, and feed image storage."""
from datetime import date
from pathlib import Path
from uuid import uuid4

import config
from onemorerep.database import connect, transaction


def _supabase_storage():
    if config.MEDIA_STORAGE != "supabase":
        return None
    if not config.SUPABASE_URL or not config.SUPABASE_SECRET_KEY:
        raise RuntimeError("Supabase media storage requires SUPABASE_URL and SUPABASE_SECRET_KEY.")
    from supabase import create_client
    client = create_client(config.SUPABASE_URL, config.SUPABASE_SECRET_KEY)
    return client.storage.from_(config.SUPABASE_STORAGE_BUCKET)


def store_image_file(image_bytes, mime_type):
    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(mime_type)
    if not extension or not image_bytes or len(image_bytes) > 8 * 1024 * 1024:
        raise ValueError("Use a JPEG, PNG, or WebP image up to 8 MB.")
    key = f"{uuid4().hex}.{extension}"
    bucket = _supabase_storage()
    if bucket:
        bucket.upload(key, image_bytes, {"content-type": mime_type, "upsert": False})
    else:
        path = Path(config.UPLOAD_DIR) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image_bytes)
    return key


def read_stored_image(key):
    if not key:
        return None
    bucket = _supabase_storage()
    if bucket:
        try:
            return bucket.download(key)
        except Exception:
            return None
    path = Path(config.UPLOAD_DIR) / Path(key).name
    return path.read_bytes() if path.is_file() else None


def remove_stored_image(key):
    if not key:
        return
    bucket = _supabase_storage()
    if bucket:
        try:
            bucket.remove([key])
        except Exception:
            pass
    else:
        path = Path(config.UPLOAD_DIR) / Path(key).name
        if path.is_file():
            path.unlink()


def save_workout_image(user_id, workout_id, image_bytes, mime_type):
    storage_key = store_image_file(image_bytes, mime_type)
    previous_key = None
    try:
        with transaction() as conn:
            if not conn.execute("SELECT id FROM workouts WHERE id=%s AND user_id=%s", (workout_id, user_id)).fetchone():
                raise ValueError("That workout is not available.")
            previous = conn.execute("SELECT storage_key FROM workout_images WHERE workout_id=%s", (workout_id,)).fetchone()
            previous_key = previous["storage_key"] if previous else None
            conn.execute("""INSERT INTO workout_images(workout_id,storage_key,mime_type,size_bytes)
                VALUES(%s,%s,%s,%s) ON CONFLICT(workout_id) DO UPDATE SET
                storage_key=EXCLUDED.storage_key,mime_type=EXCLUDED.mime_type,
                size_bytes=EXCLUDED.size_bytes,created_at=now()""",
                (workout_id, storage_key, mime_type, len(image_bytes)))
    except Exception:
        remove_stored_image(storage_key)
        raise
    if previous_key and previous_key != storage_key:
        remove_stored_image(previous_key)


def _authorized_image(sql, params):
    with connect() as conn:
        row = conn.execute(sql, params).fetchone()
    if not row:
        return None
    image = read_stored_image(row["storage_key"])
    return (image, row["mime_type"]) if image is not None else None


def get_workout_image(user_id, workout_id):
    return _authorized_image("""SELECT i.storage_key,i.mime_type FROM workout_images i
        JOIN workouts w ON w.id=i.workout_id WHERE i.workout_id=%s AND w.user_id=%s""",
        (workout_id, user_id))


def save_progress_report(user_id, report_date: date, weight_kg: float, notes: str, image_bytes=None, mime_type=None):
    notes = (notes or "").strip()
    if not 0 < float(weight_kg) <= 500:
        raise ValueError("Weight must be greater than 0 and no more than 500 kg.")
    if len(notes) > 1000:
        raise ValueError("Notes must be 1,000 characters or fewer.")
    storage_key = store_image_file(image_bytes, mime_type) if image_bytes else None
    previous_key = None
    try:
        with transaction() as conn:
            report = conn.execute("""INSERT INTO progress_reports(user_id,report_date,weight_kg,notes)
                VALUES(%s,%s,%s,%s) ON CONFLICT(user_id,report_date) DO UPDATE SET
                weight_kg=EXCLUDED.weight_kg,notes=EXCLUDED.notes,updated_at=now()
                RETURNING id""", (user_id, report_date, weight_kg, notes)).fetchone()
            if storage_key:
                previous = conn.execute("SELECT storage_key FROM progress_images WHERE report_id=%s", (report["id"],)).fetchone()
                previous_key = previous["storage_key"] if previous else None
                conn.execute("""INSERT INTO progress_images(report_id,storage_key,mime_type,size_bytes)
                    VALUES(%s,%s,%s,%s) ON CONFLICT(report_id) DO UPDATE SET
                    storage_key=EXCLUDED.storage_key,mime_type=EXCLUDED.mime_type,
                    size_bytes=EXCLUDED.size_bytes,created_at=now()""",
                    (report["id"], storage_key, mime_type, len(image_bytes)))
    except Exception:
        remove_stored_image(storage_key)
        raise
    if previous_key and previous_key != storage_key:
        remove_stored_image(previous_key)
    return report["id"]


def list_progress_reports(user_id):
    with connect() as conn:
        rows = conn.execute("""SELECT r.id,r.report_date,r.weight_kg,r.notes,r.created_at,r.updated_at,
            (i.report_id IS NOT NULL) has_image FROM progress_reports r
            LEFT JOIN progress_images i ON i.report_id=r.id
            WHERE r.user_id=%s ORDER BY r.report_date DESC,r.id DESC""", (user_id,)).fetchall()
    reports = []
    for row in rows:
        item = dict(row)
        item["image_url"] = f"/api/progress/{item['id']}/image" if item.pop("has_image") else None
        reports.append(item)
    return reports


def get_progress_image(user_id, report_id):
    return _authorized_image("""SELECT i.storage_key,i.mime_type FROM progress_images i
        JOIN progress_reports r ON r.id=i.report_id WHERE r.id=%s AND r.user_id=%s""",
        (report_id, user_id))
