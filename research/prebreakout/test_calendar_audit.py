import unittest
from calendar_audit import audit_event_calendar

SESSIONS=["2025-01-02","2025-01-03","2025-01-06","2025-01-07"]
def event(start=1,end=3):
    return {"issuer_id":"I1","episode_id":"E1",
            "signal_date":SESSIONS[start],"label_end_date":SESSIONS[end],
            "signal_session":start,"label_end_session":end}

class CalendarTests(unittest.TestCase):
    def test_matches_reference_sessions(self):
        r=audit_event_calendar([event()],SESSIONS)
        self.assertEqual(r["episodes"],1)
    def test_mismatched_ordinal_rejected(self):
        row=event();row["signal_session"]=2
        with self.assertRaises(ValueError):
            audit_event_calendar([row],SESSIONS)
    def test_unsorted_sessions_rejected(self):
        with self.assertRaises(ValueError):
            audit_event_calendar([],[SESSIONS[1],SESSIONS[0]])
    def test_duplicate_episode_rejected(self):
        with self.assertRaises(ValueError):
            audit_event_calendar([event(),event()],SESSIONS)
    def test_outside_calendar_rejected(self):
        row=event();row["label_end_date"]="2025-01-08"
        with self.assertRaises(ValueError):
            audit_event_calendar([row],SESSIONS)

if __name__=="__main__":
    unittest.main()
