from onemorerep.services.friend_group_service import member_ids


def leaderboard(conn, user_id, group_id=None):
    visible_ids = member_ids(conn, user_id, group_id)
    return conn.execute("""WITH exp_rows AS (
        SELECT user_id,activity_date::timestamptz earned_at,exp_amount,0 weekly_amount,0 monthly_amount
        FROM exp_records
        UNION ALL
        SELECT user_id,created_at,amount,weekly_amount,monthly_amount FROM exp_adjustments
      ), exp_totals AS (
        SELECT user_id,sum(exp_amount) total_exp,
          sum(exp_amount+weekly_amount) FILTER(WHERE earned_at::date>=current_date-6) weekly_exp,
          sum(exp_amount+monthly_amount) FILTER(WHERE date_trunc('month',earned_at)=date_trunc('month',current_timestamp)) monthly_exp
        FROM exp_rows GROUP BY user_id
      ), workout_totals AS (
        SELECT u.id user_id,count(w.id)+coalesce(a.workout_delta,0) total_workouts,
          CASE WHEN s.last_workout_date>=current_date-1 THEN coalesce(s.current_streak,0) ELSE 0 END+
            coalesce(a.current_streak_delta,0) current_streak,
          coalesce(s.longest_streak,0)+coalesce(a.longest_streak_delta,0) longest_streak
        FROM users u LEFT JOIN workouts w ON w.user_id=u.id
        LEFT JOIN streaks s ON s.user_id=u.id
        LEFT JOIN (SELECT user_id,sum(workout_delta) workout_delta,
          sum(current_streak_delta) current_streak_delta,sum(longest_streak_delta) longest_streak_delta
          FROM exp_adjustments GROUP BY user_id) a ON a.user_id=u.id
        GROUP BY u.id,s.current_streak,s.longest_streak,s.last_workout_date,
          a.workout_delta,a.current_streak_delta,a.longest_streak_delta
      )
      SELECT u.id,u.display_name,coalesce(e.total_exp,0) total_exp,
        coalesce(e.weekly_exp,0) weekly_exp,coalesce(e.monthly_exp,0) monthly_exp,
        w.current_streak,w.longest_streak,w.total_workouts
      FROM users u LEFT JOIN exp_totals e ON e.user_id=u.id
      LEFT JOIN workout_totals w ON w.user_id=u.id
      WHERE u.id=ANY(%s) ORDER BY total_exp DESC,u.display_name""", (visible_ids,)).fetchall()
