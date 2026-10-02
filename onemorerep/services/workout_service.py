from datetime import datetime, timedelta
from onemorerep.database import transaction
from onemorerep.services.exp_service import award_exp
from onemorerep.services.streak_service import update_streak
from onemorerep.services.achievement_service import sync_achievements
from onemorerep.services.media_service import remove_stored_image, store_image_file

def save_activity(user_id, kind, activity_date, start_time, end_time, notes="", exercises=None, walking=None,
                  sport_name=None, workout_image_bytes=None, workout_image_mime=None):
    if kind not in ("Strength","Walking","Sports"): raise ValueError("Choose Strength, Walking, or Sports.")
    start=datetime.strptime(start_time,"%H:%M").time(); end=datetime.strptime(end_time,"%H:%M").time()
    start_dt=datetime.combine(activity_date,start); end_dt=datetime.combine(activity_date,end)
    if end_dt<=start_dt: raise ValueError("End time must be after start time.")
    duration=end_dt-start_dt
    if duration.total_seconds()<=0: raise ValueError("Duration must be positive.")
    if kind=="Sports" and not (sport_name or "").strip(): raise ValueError("Enter the sport you played.")
    storage_key=store_image_file(workout_image_bytes,workout_image_mime) if workout_image_bytes else None
    try:
        with transaction() as conn:
            row=conn.execute("""INSERT INTO workouts(user_id,workout_type,workout_date,start_time,end_time,duration,notes)
              VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id""",(user_id,kind,activity_date,start,end,int(duration.total_seconds()),notes.strip())).fetchone()
            workout_id=row["id"]
            if kind=="Strength":
                if not exercises: raise ValueError("Add at least one exercise.")
                for item in exercises:
                    name=item["exercise_name"].strip(); weight=float(item["weight"]); reps=int(item["reps"]); sets=int(item["sets"])
                    if not name or min(weight,reps,sets)<0 or reps==0 or sets==0: raise ValueError("Exercise values must be valid and non-negative.")
                    conn.execute("INSERT INTO exercises(workout_id,exercise_name,weight,reps,sets) VALUES(%s,%s,%s,%s,%s)",(workout_id,name,weight,reps,sets))
            elif kind=="Walking":
                w=walking or {}; distance=float(w["distance"]); steps=int(w["steps"]); calories=float(w["calories"]); speed=float(w["avg_speed"])
                if min(distance,steps,calories,speed)<0: raise ValueError("Walking values cannot be negative.")
                conn.execute("INSERT INTO walking(workout_id,distance,steps,calories,avg_speed) VALUES(%s,%s,%s,%s,%s)",(workout_id,distance,steps,calories,speed))
            else:
                conn.execute("INSERT INTO sports(workout_id,sport_name) VALUES(%s,%s)",(workout_id,sport_name.strip()))
            if storage_key:
                conn.execute("INSERT INTO workout_images(workout_id,storage_key,mime_type,size_bytes) VALUES(%s,%s,%s,%s)",
                             (workout_id,storage_key,workout_image_mime,len(workout_image_bytes)))
            exp=award_exp(conn,user_id,workout_id,activity_date,start,duration)
            if exp: update_streak(conn,user_id)
            sync_achievements(conn,user_id)
    except Exception:
        if storage_key: remove_stored_image(storage_key)
        raise
    return workout_id,exp,int(duration.total_seconds())
