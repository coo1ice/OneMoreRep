"""Web-only sessions and friend-scoped feed operations."""
from hashlib import sha256
from secrets import token_urlsafe

from onemorerep.database import connect, transaction
from onemorerep.services.media_service import read_stored_image, remove_stored_image, store_image_file


def new_session(user_id):
    token = token_urlsafe(40)
    token_hash = sha256(token.encode("utf-8")).hexdigest()
    with transaction() as conn:
        conn.execute("DELETE FROM web_sessions WHERE expires_at <= now()")
        conn.execute("INSERT INTO web_sessions(user_id,token_hash,expires_at) VALUES(%s,%s,now()+interval '30 days')",(user_id,token_hash))
    return token


def session_user(token):
    if not token: return None
    digest=sha256(token.encode("utf-8")).hexdigest()
    with connect() as conn:
        return conn.execute("""SELECT u.id,u.username,u.display_name,u.role FROM web_sessions s
            JOIN users u ON u.id=s.user_id WHERE s.token_hash=%s AND s.expires_at>now()""",(digest,)).fetchone()


def end_session(token):
    if not token: return
    digest=sha256(token.encode("utf-8")).hexdigest()
    with transaction() as conn:
        conn.execute("DELETE FROM web_sessions WHERE token_hash=%s",(digest,))


def _is_friend(conn, viewer_id, owner_id):
    return bool(conn.execute("""SELECT 1 FROM friendships WHERE status='accepted'
        AND ((user1_id=%s AND user2_id=%s) OR (user1_id=%s AND user2_id=%s))""",
        (viewer_id,owner_id,owner_id,viewer_id)).fetchone())


def create_feed_post(user_id, caption, workout_id=None, image_bytes=None, mime_type=None,
                     achievement_id=None, include_workout_image=False):
    caption=(caption or "").strip()
    if len(caption)>500: raise ValueError("Caption must be 500 characters or fewer.")
    if not workout_id and not image_bytes and not achievement_id: raise ValueError("Share a workout, achievement, or screenshot.")
    if include_workout_image and (not workout_id or image_bytes):
        raise ValueError("Choose either the workout's saved photo or a new screenshot.")
    if include_workout_image:
        with connect() as conn:
            source=conn.execute("""SELECT i.storage_key,i.mime_type FROM workout_images i
                JOIN workouts w ON w.id=i.workout_id WHERE i.workout_id=%s AND w.user_id=%s""",
                (workout_id,user_id)).fetchone()
        if not source:
            raise ValueError("That workout has no saved photo to share.")
        image_bytes=read_stored_image(source["storage_key"])
        if image_bytes is None:
            raise ValueError("The saved workout photo is unavailable.")
        mime_type=source["mime_type"]
    if image_bytes and len(image_bytes)>8*1024*1024: raise ValueError("Screenshots must be 8 MB or smaller.")
    storage_key=store_image_file(image_bytes,mime_type) if image_bytes else None
    try:
        with transaction() as conn:
            if workout_id:
                own=conn.execute("SELECT id FROM workouts WHERE id=%s AND user_id=%s",(workout_id,user_id)).fetchone()
                if not own: raise ValueError("That workout is not available to share.")
                if conn.execute("SELECT id FROM feed_posts WHERE workout_id=%s",(workout_id,)).fetchone():
                    raise ValueError("That workout has already been shared.")
            if achievement_id and not conn.execute("SELECT id FROM achievements WHERE id=%s AND user_id=%s",(achievement_id,user_id)).fetchone():
                raise ValueError("That achievement is not available to share.")
            post=conn.execute("INSERT INTO feed_posts(user_id,workout_id,achievement_id,caption) VALUES(%s,%s,%s,%s) RETURNING id",
                               (user_id,workout_id,achievement_id,caption)).fetchone()
            if storage_key:
                conn.execute("INSERT INTO feed_images(post_id,storage_key,mime_type,size_bytes) VALUES(%s,%s,%s,%s)",
                             (post["id"],storage_key,mime_type,len(image_bytes)))
        return post["id"]
    except Exception:
        if storage_key: remove_stored_image(storage_key)
        raise


def get_feed(user_id, limit=30, before_id=None):
    cursor_clause=" AND p.id<%s" if before_id is not None else ""
    cursor_params=(before_id,) if before_id is not None else ()
    with connect() as conn:
        rows=conn.execute(f"""SELECT p.id,p.user_id,u.display_name,p.workout_id,p.achievement_id,p.caption,p.created_at,
            a.badge_name achievement_name,w.workout_type,w.workout_date,w.duration,e.exp_amount,
            (i.id IS NOT NULL) has_image,
            (SELECT count(*) FROM feed_likes l WHERE l.post_id=p.id) likes_count,
            EXISTS(SELECT 1 FROM feed_likes l WHERE l.post_id=p.id AND l.user_id=%s) liked_by_me,
            (SELECT count(*) FROM feed_comments c WHERE c.post_id=p.id) comments_count
            FROM feed_posts p JOIN users u ON u.id=p.user_id
            LEFT JOIN achievements a ON a.id=p.achievement_id
            LEFT JOIN workouts w ON w.id=p.workout_id
            LEFT JOIN exp_records e ON e.workout_id=w.id
            LEFT JOIN feed_images i ON i.post_id=p.id
            WHERE (p.user_id=%s OR EXISTS(SELECT 1 FROM friendships f WHERE f.status='accepted' AND
              ((f.user1_id=p.user_id AND f.user2_id=%s) OR (f.user1_id=%s AND f.user2_id=p.user_id))))
              {cursor_clause}
            ORDER BY p.created_at DESC,p.id DESC LIMIT %s""",
            (user_id,user_id,user_id,user_id,*cursor_params,min(max(int(limit),1),50))).fetchall()
    result=[]
    for row in rows:
        item=dict(row)
        item["image_url"]=f"/api/feed/{item['id']}/image" if item.pop("has_image") else None
        result.append(item)
    return result


def _can_view_post(conn, user_id, post_id):
    owner=conn.execute("SELECT user_id FROM feed_posts WHERE id=%s",(post_id,)).fetchone()
    return bool(owner and (owner["user_id"]==user_id or _is_friend(conn,user_id,owner["user_id"])))


def change_post_like(user_id, post_id, liked):
    with transaction() as conn:
        if not _can_view_post(conn,user_id,post_id):
            raise ValueError("Post not found.")
        if liked:
            conn.execute("INSERT INTO feed_likes(post_id,user_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",(post_id,user_id))
        else:
            conn.execute("DELETE FROM feed_likes WHERE post_id=%s AND user_id=%s",(post_id,user_id))
        count=conn.execute("SELECT count(*) amount FROM feed_likes WHERE post_id=%s",(post_id,)).fetchone()["amount"]
    return {"liked":liked,"likes_count":count}


def list_post_comments(user_id, post_id):
    with connect() as conn:
        if not _can_view_post(conn,user_id,post_id):
            raise ValueError("Post not found.")
        return conn.execute("""SELECT c.id,c.user_id,u.display_name,c.body,c.created_at
            FROM feed_comments c JOIN users u ON u.id=c.user_id
            WHERE c.post_id=%s ORDER BY c.created_at,c.id""",(post_id,)).fetchall()


def add_post_comment(user_id, post_id, body):
    body=(body or "").strip()
    if not body or len(body)>500:
        raise ValueError("Comments must contain 1 to 500 characters.")
    with transaction() as conn:
        if not _can_view_post(conn,user_id,post_id):
            raise ValueError("Post not found.")
        row=conn.execute("""INSERT INTO feed_comments(post_id,user_id,body)
            VALUES(%s,%s,%s) RETURNING id,created_at""",(post_id,user_id,body)).fetchone()
        count=conn.execute("SELECT count(*) amount FROM feed_comments WHERE post_id=%s",(post_id,)).fetchone()["amount"]
    return {"id":row["id"],"created_at":row["created_at"],"comments_count":count}


def delete_own_comment(user_id, post_id, comment_id):
    with transaction() as conn:
        deleted=conn.execute("DELETE FROM feed_comments WHERE id=%s AND user_id=%s AND post_id=%s RETURNING id",
            (comment_id,user_id,post_id)).fetchone()
    return bool(deleted)


def get_feed_image(user_id, post_id):
    with connect() as conn:
        owner=conn.execute("SELECT user_id FROM feed_posts WHERE id=%s",(post_id,)).fetchone()
        if not owner or (owner["user_id"]!=user_id and not _is_friend(conn,user_id,owner["user_id"])):
            return None
        image=conn.execute("SELECT storage_key,mime_type FROM feed_images WHERE post_id=%s",(post_id,)).fetchone()
    if not image: return None
    image_bytes=read_stored_image(image["storage_key"])
    return (image_bytes,image["mime_type"]) if image_bytes is not None else None
