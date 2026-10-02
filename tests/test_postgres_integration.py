"""Opt-in PostgreSQL checks; all fixture inserts are rolled back."""
import os
import unittest
from datetime import date, time, timedelta
from secrets import token_hex

from onemorerep.database import connect
from onemorerep.services.exp_service import award_exp
from onemorerep.services.report_service import dashboard
from onemorerep.services.streak_service import update_streak


@unittest.skipUnless(os.getenv("ONEMOREREP_TEST_DATABASE") == "1", "set ONEMOREREP_TEST_DATABASE=1 to run PostgreSQL integration checks")
class PostgreSQLRulesIntegrationTests(unittest.TestCase):
    def test_duplicate_period_awards_daily_cap_streaks_and_atomic_rollback(self):
        class RollBackFixture(Exception):
            pass

        conn = connect()
        username = f"codex_test_{token_hex(8)}"
        activity_day = date.today()

        def add_walking(start, end, seconds):
            workout = conn.execute(
                """INSERT INTO workouts(user_id,workout_type,workout_date,start_time,end_time,duration,notes)
                   VALUES(%s,'Walking',%s,%s,%s,%s,'temporary integration test') RETURNING id""",
                (user_id, activity_day, start, end, seconds),
            ).fetchone()
            conn.execute(
                "INSERT INTO walking(workout_id,distance,steps,calories,avg_speed) VALUES(%s,1,1000,50,4)",
                (workout["id"],),
            )
            return workout["id"]

        try:
            with self.assertRaises(RollBackFixture):
                with conn.transaction():
                    exp_constraints = conn.execute(
                        """SELECT constraint_type,count(*) amount FROM information_schema.table_constraints
                           WHERE table_schema=current_schema() AND table_name='exp_records'
                           GROUP BY constraint_type"""
                    ).fetchall()
                    by_type = {row["constraint_type"]: row["amount"] for row in exp_constraints}
                    self.assertGreaterEqual(by_type.get("FOREIGN KEY", 0), 2)
                    self.assertGreaterEqual(by_type.get("UNIQUE", 0), 2)
                    user = conn.execute(
                        "INSERT INTO users(username,password_hash,display_name) VALUES(%s,'test-hash','Temporary test') RETURNING id",
                        (username,),
                    ).fetchone()
                    user_id = user["id"]

                    morning_id = add_walking(time(7), time(7, 45), 45 * 60)
                    second_morning_id = add_walking(time(8), time(8, 50), 50 * 60)
                    noon_id = add_walking(time(12), time(12, 45), 45 * 60)
                    evening_id = add_walking(time(18), time(18, 40), 40 * 60)
                    second_evening_id = add_walking(time(20), time(20, 50), 50 * 60)

                    self.assertEqual(award_exp(conn, user_id, morning_id, activity_day, time(7), timedelta(minutes=45)), 30)
                    self.assertEqual(award_exp(conn, user_id, second_morning_id, activity_day, time(8), timedelta(minutes=50)), 0)
                    self.assertEqual(award_exp(conn, user_id, noon_id, activity_day, time(12), timedelta(minutes=45)), 0)
                    self.assertEqual(award_exp(conn, user_id, evening_id, activity_day, time(18), timedelta(minutes=40)), 20)
                    self.assertEqual(award_exp(conn, user_id, second_evening_id, activity_day, time(20), timedelta(minutes=50)), 0)
                    update_streak(conn, user_id)

                    totals = conn.execute(
                        """SELECT count(*) workout_count,
                                  (SELECT count(*) FROM exp_records WHERE user_id=%s) award_count,
                                  (SELECT coalesce(sum(exp_amount),0) FROM exp_records WHERE user_id=%s) total_exp
                           FROM workouts WHERE user_id=%s""",
                        (user_id, user_id, user_id),
                    ).fetchone()
                    streak = conn.execute("SELECT current_streak,longest_streak FROM streaks WHERE user_id=%s", (user_id,)).fetchone()
                    self.assertEqual(totals, {"workout_count": 5, "award_count": 2, "total_exp": 50})
                    self.assertEqual(streak, {"current_streak": 1, "longest_streak": 1})
                    today = dashboard(user_id, conn=conn)
                    self.assertEqual((today["morning"], today["morning_duration"]), (30, 45 * 60))
                    self.assertEqual((today["evening"], today["evening_duration"]), (20, 40 * 60))
                    raise RollBackFixture()
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
