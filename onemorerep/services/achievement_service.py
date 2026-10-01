def award_achievements(conn,user_id):
    stats=conn.execute("""SELECT (SELECT count(*) FROM workouts WHERE user_id=%s) workouts,
      (SELECT coalesce(sum(exp_amount),0) FROM exp_records WHERE user_id=%s) exp""",(user_id,user_id)).fetchone()
    streak=conn.execute("SELECT longest_streak FROM streaks WHERE user_id=%s",(user_id,)).fetchone()
    earned=[]
    if stats["workouts"]>=1: earned.append("First Workout")
    if stats["workouts"]>=100: earned.append("100 Workouts")
    if stats["exp"]>=1000: earned.append("1,000 EXP")
    if stats["exp"]>=10000: earned.append("10,000 EXP")
    if stats["exp"]>=100000: earned.append("100,000 EXP")
    if streak:
        for days in (7,30,100):
            if streak["longest_streak"]>=days: earned.append(f"{days} Day Streak")
    for badge in earned:
        conn.execute("INSERT INTO achievements(user_id,badge_name) VALUES(%s,%s) ON CONFLICT(user_id,badge_name) DO NOTHING",(user_id,badge))


def list_achievements(user_id):
    from onemorerep.database import connect
    with connect() as conn:
        return conn.execute(
            "SELECT id,badge_name,earned_at FROM achievements WHERE user_id=%s ORDER BY earned_at DESC,id DESC",
            (user_id,),
        ).fetchall()
