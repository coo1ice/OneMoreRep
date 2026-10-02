def sync_achievements(conn,user_id):
    stats=conn.execute("""SELECT (SELECT count(*) FROM workouts WHERE user_id=%s) +
      (SELECT coalesce(sum(workout_delta),0) FROM exp_adjustments WHERE user_id=%s) workouts,
      (SELECT coalesce(sum(exp_amount),0) FROM exp_records WHERE user_id=%s) +
      (SELECT coalesce(sum(amount),0) FROM exp_adjustments WHERE user_id=%s) exp,
      coalesce((SELECT longest_streak FROM streaks WHERE user_id=%s),0) +
      (SELECT coalesce(sum(longest_streak_delta),0) FROM exp_adjustments WHERE user_id=%s) longest""",
      (user_id,user_id,user_id,user_id,user_id,user_id)).fetchone()
    earned=set()
    if stats["workouts"]>=1: earned.add("First Workout")
    if stats["workouts"]>=100: earned.add("100 Workouts")
    for amount in (1000,10000,100000):
        if stats["exp"]>=amount: earned.add(f"{amount:,} EXP")
    for days in (7,30,100):
        if stats["longest"]>=days: earned.add(f"{days} Day Streak")
    for badge in conn.execute("SELECT id,badge_name FROM achievements WHERE user_id=%s",(user_id,)).fetchall():
        if badge["badge_name"] not in earned:
            conn.execute("DELETE FROM achievements WHERE id=%s",(badge["id"],))
    for badge in earned:
        conn.execute("INSERT INTO achievements(user_id,badge_name) VALUES(%s,%s) ON CONFLICT(user_id,badge_name) DO NOTHING",(user_id,badge))


def list_achievements(user_id):
    from onemorerep.database import connect
    with connect() as conn:
        return conn.execute(
            "SELECT id,badge_name,earned_at FROM achievements WHERE user_id=%s ORDER BY earned_at DESC,id DESC",
            (user_id,),
        ).fetchall()
