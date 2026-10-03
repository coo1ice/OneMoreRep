import unittest
from datetime import date, time, timedelta
from onemorerep.services.exp_service import activity_period, award_exp, calculate_exp, get_daily_exp, qualifies_for_period
from onemorerep.services.streak_service import streak_lengths

class ExpTests(unittest.TestCase):
    def test_cutoff(self):
        self.assertEqual(calculate_exp(timedelta(minutes=29),time(7)),0)
        self.assertEqual(calculate_exp(timedelta(minutes=30),time(7)),0)
        self.assertTrue(qualifies_for_period(timedelta(minutes=30,seconds=1),time(7)))
        self.assertEqual(calculate_exp(timedelta(minutes=30,seconds=1),time(7)),30)
    def test_periods(self):
        self.assertEqual(calculate_exp(timedelta(minutes=31),time(7)),30)
        self.assertEqual(calculate_exp(timedelta(minutes=31),time(19)),20)
        self.assertEqual(calculate_exp(timedelta(minutes=31),time(13)),0)
        self.assertEqual(get_daily_exp([30,20]),50)
    def test_daily_caps(self):
        self.assertEqual(get_daily_exp([30]),30)
        self.assertEqual(get_daily_exp([]),0)
        # The database unique constraint admits only one record per period/day.
        self.assertEqual(activity_period(time(7)),"morning")
        self.assertEqual(activity_period(time(19)),"evening")

    def test_period_boundaries(self):
        self.assertEqual(activity_period(time(5,0)),"morning")
        self.assertEqual(activity_period(time(10,0)),"morning")
        self.assertIsNone(activity_period(time(10,0,1)))
        self.assertIsNone(activity_period(time(16,59,59)))
        self.assertEqual(activity_period(time(17,0)),"evening")
        self.assertEqual(activity_period(time(22,0)),"evening")
        self.assertIsNone(activity_period(time(22,0,1)))

    def test_duplicate_period_award_is_ignored(self):
        class FakeConnection:
            def __init__(self): self.awards=set(); self.sql=[]
            def execute(self,sql,params):
                self.sql.append(sql)
                key=(params[0],params[2],params[3])
                if key in self.awards: return self
                self.awards.add(key)
                self.row={"id":len(self.awards)}
                return self
            def fetchone(self): return getattr(self,"row",None)

        conn=FakeConnection(); day=date(2026,1,1); duration=timedelta(minutes=45)
        self.assertEqual(award_exp(conn,1,10,day,time(7),duration),30)
        conn.row=None
        self.assertEqual(award_exp(conn,1,11,day,time(8),duration),0)
        self.assertIn("ON CONFLICT (user_id,activity_date,activity_period) DO NOTHING",conn.sql[0])

class StreakTests(unittest.TestCase):
    def test_one_consecutive_gap_and_duplicate_dates(self):
        d=date(2026,1,1)
        self.assertEqual(streak_lengths([d]),(1,1))
        self.assertEqual(streak_lengths([d,d+timedelta(days=1)]),(2,2))
        self.assertEqual(streak_lengths([d,d+timedelta(days=2)]),(1,1))
        self.assertEqual(streak_lengths([d,d+timedelta(days=1),d+timedelta(days=3)]),(1,2))
        self.assertEqual(streak_lengths([d,d,d+timedelta(days=1)]),(2,2))

if __name__=="__main__": unittest.main()
