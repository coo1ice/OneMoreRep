from datetime import date, datetime, time, timedelta
import config

def _time(value):
    return time.fromisoformat(value) if isinstance(value, str) else value

def activity_period(start_time):
    value = _time(start_time)
    if _time(config.MORNING_START) <= value <= _time(config.MORNING_END): return "morning"
    if _time(config.EVENING_START) <= value <= _time(config.EVENING_END): return "evening"
    return None

def qualifies_for_period(duration, start_time):
    seconds = duration.total_seconds() if isinstance(duration, timedelta) else float(duration)
    return seconds > 1800 and activity_period(start_time) is not None

def calculate_exp(duration, start_time):
    period = activity_period(start_time)
    return (30 if period == "morning" else 20) if period and qualifies_for_period(duration, start_time) else 0

def get_daily_exp(records):
    return min(50, sum(int(r["exp_amount"] if isinstance(r, dict) else r) for r in records))

def award_exp(conn, user_id, workout_id, workout_date, start_time, duration):
    amount = calculate_exp(duration, start_time)
    period = activity_period(start_time)
    if not amount or period is None: return 0
    row = conn.execute("""INSERT INTO exp_records(user_id,workout_id,activity_date,activity_period,exp_amount)
        VALUES (%s,%s,%s,%s,%s) ON CONFLICT (user_id,activity_date,activity_period) DO NOTHING RETURNING id""",
        (user_id, workout_id, workout_date, period, amount)).fetchone()
    return amount if row else 0
