from datetime import timedelta

def streak_lengths(dates):
    """Return (current trailing run, all-time best) from unique calendar dates."""
    ordered = sorted(set(dates)); run = best = 0; previous = None
    for day in ordered:
        run = run + 1 if previous is not None and day == previous + timedelta(days=1) else 1
        best = max(best, run); previous = day
    return run, best

def update_streak(conn, user_id):
    """Recompute streaks from eligible workout days, excluding backfilled logs."""
    conn.execute("SELECT user_id FROM streaks WHERE user_id=%s FOR UPDATE", (user_id,)).fetchone()
    dates = [r["activity_date"] for r in conn.execute(
        "SELECT DISTINCT workout_date activity_date FROM workouts WHERE user_id=%s AND streak_eligible=TRUE ORDER BY workout_date", (user_id,)).fetchall()]
    today = conn.execute("SELECT current_date today").fetchone()["today"]
    trailing, longest = streak_lengths(dates)
    current = trailing if dates and dates[-1] >= today - timedelta(days=1) else 0
    last = dates[-1] if dates else None
    conn.execute("INSERT INTO streaks(user_id,current_streak,longest_streak,last_workout_date) VALUES(%s,%s,%s,%s) "
                 "ON CONFLICT(user_id) DO UPDATE SET current_streak=EXCLUDED.current_streak,longest_streak=EXCLUDED.longest_streak,last_workout_date=EXCLUDED.last_workout_date",
                 (user_id,current,longest,last))
    return current
