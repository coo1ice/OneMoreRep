from contextlib import nullcontext
from onemorerep.database import connect
from onemorerep.services.exp_service import activity_period

def dashboard(user_id, conn=None):
    with (connect() if conn is None else nullcontext(conn)) as c:
        user=c.execute("SELECT display_name FROM users WHERE id=%s",(user_id,)).fetchone()
        streak=c.execute("SELECT current_streak,longest_streak,last_workout_date FROM streaks WHERE user_id=%s",(user_id,)).fetchone()
        today=c.execute("SELECT coalesce(sum(exp_amount),0) exp FROM exp_records WHERE user_id=%s AND activity_date=current_date",(user_id,)).fetchone()
        total=c.execute("SELECT coalesce(sum(exp_amount),0) exp FROM exp_records WHERE user_id=%s",(user_id,)).fetchone()
        periods=c.execute("""SELECT e.activity_period,e.exp_amount,w.duration FROM exp_records e
            JOIN workouts w ON w.id=e.workout_id WHERE e.user_id=%s AND e.activity_date=current_date""",(user_id,)).fetchall()
        today_workouts=c.execute("""SELECT start_time,duration FROM workouts
            WHERE user_id=%s AND workout_date=current_date ORDER BY start_time DESC,id DESC""",(user_id,)).fetchall()
        ranks=c.execute("""WITH circle AS (
            SELECT %s::bigint user_id UNION
            SELECT CASE WHEN user1_id=%s THEN user2_id ELSE user1_id END
            FROM friendships WHERE status='accepted' AND (user1_id=%s OR user2_id=%s)
          ), totals AS (SELECT c.user_id,coalesce(sum(e.exp_amount),0) total_exp
            FROM circle c LEFT JOIN exp_records e ON e.user_id=c.user_id GROUP BY c.user_id)
          SELECT user_id,rank() OVER(ORDER BY total_exp DESC) rank FROM totals""",
          (user_id,user_id,user_id,user_id)).fetchall()
    by={"morning":{"exp":0,"duration":0},"evening":{"exp":0,"duration":0}}
    for workout in today_workouts:
        period=activity_period(workout["start_time"])
        if period and by[period]["duration"]==0:
            by[period]["duration"]=workout["duration"]
    for period in periods:
        by[period["activity_period"]]={"exp":period["exp_amount"],"duration":period["duration"]}
    rank=next((r["rank"] for r in ranks if r["user_id"]==user_id),None)
    return {"name":user["display_name"],"streak":streak,"today":today["exp"],"total":total["exp"],
        "morning":by["morning"]["exp"],"morning_duration":by["morning"]["duration"],
        "evening":by["evening"]["exp"],"evening_duration":by["evening"]["duration"],"rank":rank}

def history(user_id,exp_only=False):
    with connect() as c:
        if exp_only:
            return c.execute("""SELECT e.activity_date,e.activity_period,w.workout_type,w.duration,e.exp_amount FROM exp_records e JOIN workouts w ON w.id=e.workout_id WHERE e.user_id=%s ORDER BY e.activity_date DESC,w.start_time DESC""",(user_id,)).fetchall()
        return c.execute("""SELECT w.id,w.workout_date,w.workout_type,w.duration,w.start_time,e.exp_amount,
            EXISTS(SELECT 1 FROM workout_images i WHERE i.workout_id=w.id) has_image
            FROM workouts w LEFT JOIN exp_records e ON e.workout_id=w.id
            WHERE w.user_id=%s ORDER BY w.workout_date DESC,w.start_time DESC""",(user_id,)).fetchall()

def statistics(user_id):
    with connect() as c:
        return c.execute("""SELECT (SELECT coalesce(sum(exp_amount),0) FROM exp_records WHERE user_id=%s) total_exp,
        (SELECT count(*) FROM workouts WHERE user_id=%s) total_workouts,
        (SELECT count(*) FROM workouts WHERE user_id=%s AND workout_type='Strength') strength_workouts,
        (SELECT count(*) FROM workouts WHERE user_id=%s AND workout_type='Walking') walking_sessions,
        (SELECT count(*) FROM workouts WHERE user_id=%s AND workout_type='Sports') sports_sessions,
        coalesce((SELECT sum(weight*reps*sets) FROM exercises e JOIN workouts w ON w.id=e.workout_id WHERE w.user_id=%s),0) total_weight,
        coalesce((SELECT sum(distance) FROM walking x JOIN workouts w ON w.id=x.workout_id WHERE w.user_id=%s),0) total_distance,
        coalesce((SELECT sum(steps) FROM walking x JOIN workouts w ON w.id=x.workout_id WHERE w.user_id=%s),0) total_steps,
        coalesce((SELECT longest_streak FROM streaks WHERE user_id=%s),0) longest_streak,
        coalesce((SELECT current_streak FROM streaks WHERE user_id=%s),0) current_streak""",(user_id,user_id,user_id,user_id,user_id,user_id,user_id,user_id,user_id,user_id)).fetchone()
