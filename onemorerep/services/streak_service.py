from datetime import date, timedelta

def streak_lengths(dates):
    """Return (current trailing run, all-time best) from unique calendar dates."""
    ordered = sorted(set(dates)); run = best = 0; previous = None
    for day in ordered:
        run = run + 1 if previous is not None and day == previous + timedelta(days=1) else 1
        best = max(best, run); previous = day
    return run, best

def update_streak(conn, user_id, activity_date):
    """Recompute date streaks, making duplicate periods and backfills safe."""
    conn.execute("SELECT user_id FROM streaks WHERE user_id=%s FOR UPDATE", (user_id,)).fetchone()
    dates = [r["activity_date"] for r in conn.execute(
        "SELECT DISTINCT activity_date FROM exp_records WHERE user_id=%s ORDER BY activity_date", (user_id,)).fetchall()]
    trailing, longest = streak_lengths(dates)
    current = trailing
    if dates and dates[-1] >= date.today() - timedelta(days=1):
        current = trailing
    else:
        current = 0
    last = dates[-1] if dates else None
    conn.execute("INSERT INTO streaks(user_id,current_streak,longest_streak,last_workout_date) VALUES(%s,%s,%s,%s) "
                 "ON CONFLICT(user_id) DO UPDATE SET current_streak=EXCLUDED.current_streak,longest_streak=EXCLUDED.longest_streak,last_workout_date=EXCLUDED.last_workout_date",
                 (user_id,current,longest,last))
    return current

def get_current_streak(conn, user_id):
    row=conn.execute("SELECT current_streak,last_workout_date FROM streaks WHERE user_id=%s",(user_id,)).fetchone()
    if not row or row["last_workout_date"] < date.today()-timedelta(days=1): return 0
    return row["current_streak"]

def get_longest_streak(conn,user_id):
    row=conn.execute("SELECT longest_streak FROM streaks WHERE user_id=%s",(user_id,)).fetchone()
    return row["longest_streak"] if row else 0
