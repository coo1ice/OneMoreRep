def leaderboard(conn, user_id=None):
    return conn.execute("""WITH exp_totals AS (
        SELECT user_id,sum(exp_amount) total_exp,
          sum(exp_amount) FILTER(WHERE activity_date>=current_date-6) weekly_exp,
          sum(exp_amount) FILTER(WHERE date_trunc('month',activity_date)=date_trunc('month',current_date)) monthly_exp
        FROM exp_records GROUP BY user_id
      ), workout_totals AS (
        SELECT user_id,count(*) total_workouts FROM workouts GROUP BY user_id
      )
      SELECT u.id,u.display_name,coalesce(e.total_exp,0) total_exp,
        coalesce(e.weekly_exp,0) weekly_exp,coalesce(e.monthly_exp,0) monthly_exp,
        coalesce(s.current_streak,0) current_streak,coalesce(s.longest_streak,0) longest_streak,
        coalesce(w.total_workouts,0) total_workouts
      FROM users u LEFT JOIN exp_totals e ON e.user_id=u.id
      LEFT JOIN streaks s ON s.user_id=u.id LEFT JOIN workout_totals w ON w.user_id=u.id
      ORDER BY total_exp DESC,u.display_name""").fetchall()
