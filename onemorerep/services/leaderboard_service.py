from onemorerep.services.friend_group_service import member_ids


def leaderboard(conn, user_id, group_id=None):
    visible_ids = member_ids(conn, user_id, group_id)
    return conn.execute("""WITH exp_rows AS (
        SELECT user_id,activity_date::timestamptz earned_at,exp_amount FROM exp_records
        UNION ALL
        SELECT user_id,created_at,amount FROM exp_adjustments
      ), exp_totals AS (
        SELECT user_id,sum(exp_amount) total_exp,
          sum(exp_amount) FILTER(WHERE earned_at::date>=current_date-6) weekly_exp,
          sum(exp_amount) FILTER(WHERE date_trunc('month',earned_at)=date_trunc('month',current_timestamp)) monthly_exp
        FROM exp_rows GROUP BY user_id
      ), workout_totals AS (
        SELECT user_id,count(*) total_workouts FROM workouts GROUP BY user_id
      )
      SELECT u.id,u.display_name,coalesce(e.total_exp,0) total_exp,
        coalesce(e.weekly_exp,0) weekly_exp,coalesce(e.monthly_exp,0) monthly_exp,
        coalesce(s.current_streak,0) current_streak,coalesce(s.longest_streak,0) longest_streak,
        coalesce(w.total_workouts,0) total_workouts
      FROM users u LEFT JOIN exp_totals e ON e.user_id=u.id
      LEFT JOIN streaks s ON s.user_id=u.id LEFT JOIN workout_totals w ON w.user_id=u.id
      WHERE u.id=ANY(%s) ORDER BY total_exp DESC,u.display_name""", (visible_ids,)).fetchall()
