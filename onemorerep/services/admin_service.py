"""Administrative, role-protected read-only access to account data."""
from onemorerep.database import connect, transaction
from onemorerep.services.media_service import read_stored_image, remove_stored_image
from onemorerep.services.exp_service import activity_period, calculate_exp
from onemorerep.services.streak_service import update_streak
from onemorerep.services.achievement_service import award_achievements


def list_users():
    with connect() as conn:
        return conn.execute("""SELECT u.id,u.username,u.display_name,u.role,u.created_at,
            (SELECT count(*) FROM workouts w WHERE w.user_id=u.id) workout_count,
            (SELECT count(*) FROM progress_reports r WHERE r.user_id=u.id) progress_count,
            (SELECT count(*) FROM feed_posts p WHERE p.user_id=u.id) post_count
            FROM users u ORDER BY u.created_at DESC,u.id DESC LIMIT 1000""").fetchall()


def user_report(user_id):
    with connect() as conn:
        user=conn.execute("""SELECT u.id,u.username,u.display_name,u.role,u.created_at,
            (SELECT count(*) FROM workouts w WHERE w.user_id=u.id) workout_count,
            (SELECT count(*) FROM progress_reports r WHERE r.user_id=u.id) progress_count,
            (SELECT count(*) FROM feed_posts p WHERE p.user_id=u.id) post_count
            FROM users u WHERE u.id=%s""",(user_id,)).fetchone()
        if not user:
            return None
        workouts=conn.execute("""SELECT w.id,w.workout_type,w.workout_date,w.start_time,w.end_time,w.duration,w.notes,
            e.exp_amount,s.sport_name,(wi.workout_id IS NOT NULL) has_image
            FROM workouts w LEFT JOIN exp_records e ON e.workout_id=w.id
            LEFT JOIN sports s ON s.workout_id=w.id LEFT JOIN workout_images wi ON wi.workout_id=w.id
            WHERE w.user_id=%s ORDER BY w.workout_date DESC,w.start_time DESC,w.id DESC""",(user_id,)).fetchall()
        progress=conn.execute("""SELECT r.id,r.report_date,r.weight_kg,r.notes,r.created_at,
            (pi.report_id IS NOT NULL) has_image FROM progress_reports r
            LEFT JOIN progress_images pi ON pi.report_id=r.id WHERE r.user_id=%s
            ORDER BY r.report_date DESC,r.id DESC""",(user_id,)).fetchall()
        posts=conn.execute("""SELECT p.id,p.caption,p.created_at,p.workout_id,p.achievement_id,a.badge_name achievement_name,
            (fi.post_id IS NOT NULL) has_image,(SELECT count(*) FROM feed_likes l WHERE l.post_id=p.id) likes_count,
            (SELECT count(*) FROM feed_comments c WHERE c.post_id=p.id) comments_count
            FROM feed_posts p LEFT JOIN achievements a ON a.id=p.achievement_id LEFT JOIN feed_images fi ON fi.post_id=p.id
            WHERE p.user_id=%s ORDER BY p.created_at DESC,p.id DESC""",(user_id,)).fetchall()
        comments=conn.execute("""SELECT c.id,p.id post_id,u.display_name commenter,c.body,c.created_at
            FROM feed_comments c JOIN feed_posts p ON p.id=c.post_id JOIN users u ON u.id=c.user_id
            WHERE p.user_id=%s ORDER BY c.created_at DESC""",(user_id,)).fetchall()
        likes=conn.execute("""SELECT p.id post_id,u.display_name liker,l.created_at
            FROM feed_likes l JOIN feed_posts p ON p.id=l.post_id JOIN users u ON u.id=l.user_id
            WHERE p.user_id=%s ORDER BY l.created_at DESC""",(user_id,)).fetchall()
    for row in workouts:
        row["image_url"]=f"/api/admin/users/{user_id}/workouts/{row['id']}/image" if row.pop("has_image") else None
        row["exercises"]=[]
        row["walking"]=None
        if row["workout_type"]=="Strength":
            with connect() as conn:
                row["exercises"]=conn.execute("SELECT exercise_name,weight,reps,sets FROM exercises WHERE workout_id=%s ORDER BY id",(row["id"],)).fetchall()
        elif row["workout_type"]=="Walking":
            with connect() as conn:
                row["walking"]=conn.execute("SELECT distance,steps,calories,avg_speed FROM walking WHERE workout_id=%s",(row["id"],)).fetchone()
    for row in progress:
        row["image_url"]=f"/api/admin/users/{user_id}/progress/{row['id']}/image" if row.pop("has_image") else None
    for row in posts:
        row["image_url"]=f"/api/admin/users/{user_id}/posts/{row['id']}/image" if row.pop("has_image") else None
    return {"user":user,"workouts":workouts,"progress_reports":progress,"posts":posts,
        "comments":comments,"likes":likes}


def _image_query(sql, params):
    with connect() as conn:
        row=conn.execute(sql,params).fetchone()
    if not row:
        return None
    image=read_stored_image(row["storage_key"])
    return (image,row["mime_type"]) if image is not None else None


def workout_image(user_id,workout_id):
    return _image_query("""SELECT i.storage_key,i.mime_type FROM workout_images i
        JOIN workouts w ON w.id=i.workout_id WHERE w.user_id=%s AND w.id=%s""",(user_id,workout_id))


def progress_image(user_id,report_id):
    return _image_query("""SELECT i.storage_key,i.mime_type FROM progress_images i
        JOIN progress_reports r ON r.id=i.report_id WHERE r.user_id=%s AND r.id=%s""",(user_id,report_id))


def post_image(user_id,post_id):
    return _image_query("""SELECT i.storage_key,i.mime_type FROM feed_images i
        JOIN feed_posts p ON p.id=i.post_id WHERE p.user_id=%s AND p.id=%s""",(user_id,post_id))


def update_member(user_id, display_name):
    display_name=(display_name or "").strip()
    if not display_name or len(display_name)>80:
        raise ValueError("Display name must be between 1 and 80 characters.")
    with transaction() as conn:
        row=conn.execute("UPDATE users SET display_name=%s WHERE id=%s RETURNING id,username,display_name,role",
            (display_name,user_id)).fetchone()
    if not row:
        return None
    return row


def update_workout(user_id,workout_id,notes=None,exercises=None,walking=None,sport_name=None):
    if notes is None and exercises is None and walking is None and sport_name is None:
        raise ValueError("Provide at least one workout field to update.")
    with transaction() as conn:
        workout=conn.execute("SELECT workout_type FROM workouts WHERE id=%s AND user_id=%s",
            (workout_id,user_id)).fetchone()
        if not workout:
            return False
        kind=workout["workout_type"]
        if notes is not None:
            conn.execute("UPDATE workouts SET notes=%s WHERE id=%s",(notes.strip(),workout_id))
        if exercises is not None:
            if kind!="Strength" or not exercises:
                raise ValueError("Strength workouts require at least one exercise.")
            conn.execute("DELETE FROM exercises WHERE workout_id=%s",(workout_id,))
            for item in exercises:
                conn.execute("INSERT INTO exercises(workout_id,exercise_name,weight,reps,sets) VALUES(%s,%s,%s,%s,%s)",
                    (workout_id,item.exercise_name.strip(),item.weight,item.reps,item.sets))
        if walking is not None:
            if kind!="Walking":
                raise ValueError("Walking details can only be changed on a walking activity.")
            conn.execute("UPDATE walking SET distance=%s,steps=%s,calories=%s,avg_speed=%s WHERE workout_id=%s",
                (walking.distance,walking.steps,walking.calories,walking.avg_speed,workout_id))
        if sport_name is not None:
            if kind!="Sports" or not sport_name.strip():
                raise ValueError("Enter a sport name for a sports activity.")
            conn.execute("UPDATE sports SET sport_name=%s WHERE workout_id=%s",(sport_name.strip(),workout_id))
    return True


def update_progress(user_id,report_id,weight_kg,notes):
    notes=(notes or "").strip()
    if not 0<float(weight_kg)<=500:
        raise ValueError("Weight must be greater than 0 and no more than 500 kg.")
    if len(notes)>1000:
        raise ValueError("Notes must be 1,000 characters or fewer.")
    with transaction() as conn:
        row=conn.execute("UPDATE progress_reports SET weight_kg=%s,notes=%s,updated_at=now() WHERE id=%s AND user_id=%s RETURNING id",
            (weight_kg,notes,report_id,user_id)).fetchone()
    return bool(row)


def update_post(user_id,post_id,caption):
    caption=(caption or "").strip()
    if len(caption)>500:
        raise ValueError("Caption must be 500 characters or fewer.")
    with transaction() as conn:
        row=conn.execute("UPDATE feed_posts SET caption=%s WHERE id=%s AND user_id=%s RETURNING id",
            (caption,post_id,user_id)).fetchone()
    return bool(row)


def delete_member(user_id,actor_id):
    if user_id==actor_id:
        raise ValueError("You cannot delete your own administrator account here.")
    with transaction() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(740921)")
        member=conn.execute("SELECT id,role FROM users WHERE id=%s FOR UPDATE",(user_id,)).fetchone()
        if not member:
            return False
        if member["role"]=="admin":
            admins=conn.execute("SELECT count(*) count FROM users WHERE role='admin'").fetchone()["count"]
            if admins<=1:
                raise ValueError("You cannot delete the last administrator account.")
        files=[]
        for query,params in (
            ("SELECT i.storage_key FROM workout_images i JOIN workouts w ON w.id=i.workout_id WHERE w.user_id=%s",(user_id,)),
            ("SELECT i.storage_key FROM progress_images i JOIN progress_reports r ON r.id=i.report_id WHERE r.user_id=%s",(user_id,)),
            ("SELECT i.storage_key FROM feed_images i JOIN feed_posts p ON p.id=i.post_id WHERE p.user_id=%s",(user_id,)),
        ):
            files.extend(r["storage_key"] for r in conn.execute(query,params).fetchall())
        conn.execute("DELETE FROM users WHERE id=%s",(user_id,))
    for key in files:
        remove_stored_image(key)
    return True


def delete_workout(user_id,workout_id):
    with transaction() as conn:
        workout=conn.execute("SELECT id FROM workouts WHERE id=%s AND user_id=%s FOR UPDATE",(workout_id,user_id)).fetchone()
        if not workout:
            return False
        image=conn.execute("SELECT storage_key FROM workout_images WHERE workout_id=%s",(workout_id,)).fetchone()
        conn.execute("DELETE FROM workouts WHERE id=%s",(workout_id,))
        conn.execute("DELETE FROM exp_records WHERE user_id=%s",(user_id,))
        rows=conn.execute("SELECT id,workout_date,start_time,duration FROM workouts WHERE user_id=%s ORDER BY workout_date,start_time,id",(user_id,)).fetchall()
        awarded=set()
        for row in rows:
            period=activity_period(row["start_time"])
            amount=calculate_exp(row["duration"],row["start_time"])
            slot=(row["workout_date"],period)
            if amount and period and slot not in awarded:
                conn.execute("INSERT INTO exp_records(user_id,workout_id,activity_date,activity_period,exp_amount) VALUES(%s,%s,%s,%s,%s)",
                    (user_id,row["id"],row["workout_date"],period,amount))
                awarded.add(slot)
        update_streak(conn,user_id,None)
        stats=conn.execute("""SELECT (SELECT count(*) FROM workouts WHERE user_id=%s) workouts,
            (SELECT coalesce(sum(exp_amount),0) FROM exp_records WHERE user_id=%s) exp,
            (SELECT longest_streak FROM streaks WHERE user_id=%s) longest""",(user_id,user_id,user_id)).fetchone()
        desired=set()
        if stats["workouts"]>=1: desired.add("First Workout")
        if stats["workouts"]>=100: desired.add("100 Workouts")
        for amount in (1000,10000,100000):
            if stats["exp"]>=amount: desired.add(f"{amount:,} EXP")
        for days in (7,30,100):
            if stats["longest"]>=days: desired.add(f"{days} Day Streak")
        for badge in conn.execute("SELECT id,badge_name FROM achievements WHERE user_id=%s",(user_id,)).fetchall():
            if badge["badge_name"] not in desired:
                conn.execute("DELETE FROM achievements WHERE id=%s",(badge["id"],))
        award_achievements(conn,user_id)
    if image:
        remove_stored_image(image["storage_key"])
    return True


def delete_progress(user_id,report_id):
    with transaction() as conn:
        image=conn.execute("SELECT i.storage_key FROM progress_images i JOIN progress_reports r ON r.id=i.report_id WHERE r.user_id=%s AND r.id=%s",(user_id,report_id)).fetchone()
        deleted=conn.execute("DELETE FROM progress_reports WHERE id=%s AND user_id=%s RETURNING id",(report_id,user_id)).fetchone()
    if not deleted:
        return False
    if image:
        remove_stored_image(image["storage_key"])
    return True


def delete_post(user_id,post_id):
    with transaction() as conn:
        image=conn.execute("SELECT i.storage_key FROM feed_images i JOIN feed_posts p ON p.id=i.post_id WHERE p.user_id=%s AND p.id=%s",(user_id,post_id)).fetchone()
        deleted=conn.execute("DELETE FROM feed_posts WHERE id=%s AND user_id=%s RETURNING id",(post_id,user_id)).fetchone()
    if not deleted:
        return False
    if image:
        remove_stored_image(image["storage_key"])
    return True


def delete_comment(user_id,comment_id):
    with transaction() as conn:
        deleted=conn.execute("""DELETE FROM feed_comments c USING feed_posts p
            WHERE c.post_id=p.id AND p.user_id=%s AND c.id=%s RETURNING c.id""",(user_id,comment_id)).fetchone()
    return bool(deleted)
