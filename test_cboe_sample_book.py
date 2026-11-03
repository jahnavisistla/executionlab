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
        self.assertEqual(len(shots),2)
        self.assertAlmostEqual(shots[0][1],99)
        self.assertAlmostEqual(shots[1][1],100)
        self.assertEqual(quality["deletes"],1)

    def test_weighted_spread(self):
        shots=[(0,99,101,200),(100,99.5,100.5,100),(300,99.5,100.5,100)]
        r=summarise(shots)
        self.assertAlmostEqual(r["mean_time_weighted_spread_bps"],133.333333,places=4)


if __name__=="__main__":unittest.main()
