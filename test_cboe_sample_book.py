import unittest
from cboe_sample_book import process_events,summarise


class BookTests(unittest.TestCase):
    def test_add_modify_delete(self):
        rows=[
            ["64","1","100","B1","B","20","X","99"],
            ["64","2","200","A1","S","25","X","101"],
            ["39","3","300","B1","20","100"],
            ["41","4","400","B1"],
        ]
        shots,quality=process_events(rows)
        self.assertEqual(len(shots),3)
        self.assertAlmostEqual(shots[0][1],99)
        self.assertAlmostEqual(shots[1][1],100)
        self.assertIsNone(shots[2][3])
        self.assertEqual(quality["deletes"],1)

    def test_weighted_spread(self):
        shots=[(0,99,101,200),(100,99.5,100.5,100),(300,99.5,100.5,100)]
        r=summarise(shots)
        self.assertAlmostEqual(r["mean_time_weighted_spread_bps"],133.333333,places=4)

    def test_invalid_book_not_time_weighted(self):
        shots=[(0,99,101,200),(100,None,None,None),(200,99.5,100.5,100),(300,99.5,100.5,100)]
        r=summarise(shots)
        self.assertAlmostEqual(r["mean_time_weighted_spread_bps"],150)
        self.assertEqual(r["invalid_state_transitions"],1)

    def test_execute_at_price_uses_remaining_shares(self):
        rows=[
            ["64","1","100","B1","B","20","X","99"],
            ["64","2","200","A1","S","25","X","101"],
            ["36","3","300","B1","10","0","EX1","98","12-H"],
        ]
        shots,_=process_events(rows)
        self.assertIsNone(shots[-1][3])

    def test_sequence_audit(self):
        rows=[["64","2","100","B1","B","20","X","99"],
              ["64","1","90","A1","S","25","X","101"]]
        _,quality=process_events(rows)
        self.assertEqual(quality["non_increasing_sequence"],1)
        self.assertEqual(quality["non_monotonic_timestamp"],1)


if __name__=="__main__":unittest.main()
