from contextlib import nullcontext
from onemorerep.database import connect
from onemorerep.services.exp_service import activity_period

def dashboard(user_id, conn=None):
    with (connect() if conn is None else nullcontext(conn)) as c:
        user=c.execute("SELECT display_name FROM users WHERE id=%s",(user_id,)).fetchone()
        streak=c.execute("""SELECT CASE WHEN s.last_workout_date>=current_date-1 THEN coalesce(s.current_streak,0) ELSE 0 END+
            coalesce(x.current_streak_delta,0) current_streak,
            coalesce(s.longest_streak,0)+coalesce(x.longest_streak_delta,0) longest_streak,s.last_workout_date
            FROM (SELECT %s::bigint user_id) u LEFT JOIN streaks s ON s.user_id=u.user_id
            LEFT JOIN (SELECT user_id,sum(current_streak_delta) current_streak_delta,
                sum(longest_streak_delta) longest_streak_delta FROM exp_adjustments WHERE user_id=%s GROUP BY user_id) x
                ON x.user_id=u.user_id""",(user_id,user_id)).fetchone()
        today=c.execute("SELECT coalesce(sum(exp_amount),0) exp FROM exp_records WHERE user_id=%s AND activity_date=current_date",(user_id,)).fetchone()
        total=c.execute("""SELECT coalesce((SELECT sum(exp_amount) FROM exp_records WHERE user_id=%s),0) +
            coalesce((SELECT sum(amount) FROM exp_adjustments WHERE user_id=%s),0) exp""",
            (user_id,user_id)).fetchone()
        periods=c.execute("""SELECT e.activity_period,e.exp_amount,w.duration FROM exp_records e
            JOIN workouts w ON w.id=e.workout_id WHERE e.user_id=%s AND e.activity_date=current_date""",(user_id,)).fetchall()
        today_workouts=c.execute("""SELECT start_time,duration FROM workouts
            WHERE user_id=%s AND workout_date=current_date ORDER BY start_time DESC,id DESC""",(user_id,)).fetchall()
        ranks=c.execute("""WITH circle AS (
            SELECT %s::bigint user_id UNION
            SELECT CASE WHEN user1_id=%s THEN user2_id ELSE user1_id END
            FROM friendships WHERE status='accepted' AND (user1_id=%s OR user2_id=%s)
          ), totals AS (SELECT c.user_id,
            coalesce((SELECT sum(e.exp_amount) FROM exp_records e WHERE e.user_id=c.user_id),0) +
            coalesce((SELECT sum(x.amount) FROM exp_adjustments x WHERE x.user_id=c.user_id),0) total_exp
            FROM circle c)
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

def history(user_id,exp_only=False,conn=None,limit=None):
    with (connect() if conn is None else nullcontext(conn)) as c:
        if exp_only:
            return c.execute("""SELECT activity_date,activity_period,workout_type,duration,exp_amount,
                source,reason,admin_username FROM (
              SELECT e.activity_date,e.activity_period,w.workout_type,w.duration,e.exp_amount,
                'workout'::text source,NULL::text reason,NULL::text admin_username,e.earned_at created_at
              FROM exp_records e JOIN workouts w ON w.id=e.workout_id WHERE e.user_id=%s
              UNION ALL
              SELECT x.created_at::date,'admin_adjustment'::text,'EXP adjustment'::text,
                NULL::integer,x.amount,'admin_adjustment'::text,x.reason,x.admin_username,x.created_at
              FROM exp_adjustments x WHERE x.user_id=%s AND x.amount<>0
            ) records ORDER BY created_at DESC""",(user_id,user_id)).fetchall()
        query="""SELECT w.id,w.workout_date,w.workout_type,w.duration,w.start_time,e.exp_amount,
            EXISTS(SELECT 1 FROM workout_images i WHERE i.workout_id=w.id) has_image
            FROM workouts w LEFT JOIN exp_records e ON e.workout_id=w.id
            WHERE w.user_id=%s ORDER BY w.workout_date DESC,w.start_time DESC"""
        params=(user_id,)
        if limit is not None:
            query+=" LIMIT %s"
            params+=(max(1,int(limit)),)
        return c.execute(query,params).fetchall()

def statistics(user_id):
    with connect() as c:
        return c.execute("""SELECT (SELECT coalesce(sum(exp_amount),0) FROM exp_records WHERE user_id=%s) +
        (SELECT coalesce(sum(amount),0) FROM exp_adjustments WHERE user_id=%s) total_exp,
        (SELECT count(*) FROM workouts WHERE user_id=%s) +
        (SELECT coalesce(sum(workout_delta),0) FROM exp_adjustments WHERE user_id=%s) total_workouts,
        (SELECT count(*) FROM workouts WHERE user_id=%s AND workout_type='Strength') strength_workouts,
        (SELECT count(*) FROM workouts WHERE user_id=%s AND workout_type='Walking') walking_sessions,
        (SELECT count(*) FROM workouts WHERE user_id=%s AND workout_type='Sports') sports_sessions,
        coalesce((SELECT sum(weight*reps*sets) FROM exercises e JOIN workouts w ON w.id=e.workout_id WHERE w.user_id=%s),0) total_weight,
        coalesce((SELECT sum(distance) FROM walking x JOIN workouts w ON w.id=x.workout_id WHERE w.user_id=%s),0) total_distance,
        coalesce((SELECT sum(steps) FROM walking x JOIN workouts w ON w.id=x.workout_id WHERE w.user_id=%s),0) total_steps,
        coalesce((SELECT longest_streak FROM streaks WHERE user_id=%s),0) +
        (SELECT coalesce(sum(longest_streak_delta),0) FROM exp_adjustments WHERE user_id=%s) longest_streak,
        coalesce((SELECT CASE WHEN last_workout_date>=current_date-1 THEN current_streak ELSE 0 END FROM streaks WHERE user_id=%s),0) +
        (SELECT coalesce(sum(current_streak_delta),0) FROM exp_adjustments WHERE user_id=%s) current_streak""",
        (user_id,user_id,user_id,user_id,user_id,user_id,user_id,user_id,user_id,user_id,user_id,user_id,user_id)).fetchone()
