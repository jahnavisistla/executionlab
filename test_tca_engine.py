import unittest
from tca_engine import ParentOrder, Fill, analyse, effective_spread_bps, realised_spread_bps


class TCATests(unittest.TestCase):
    def test_full_buy(self):
        p=ParentOrder("p","BUY",100,100,101)
        r=analyse(p,[Fill("p","c1",0,100,100.2,1)],100.1)
        self.assertAlmostEqual(r["fill_rate"],1)
        self.assertAlmostEqual(r["implementation_shortfall"],21)
        self.assertAlmostEqual(r["implementation_shortfall_bps"],21)

    def test_partial_sell_opportunity(self):
        p=ParentOrder("p","SELL",100,100,99)
        r=analyse(p,[Fill("p","c",0,40,99.8,0)],99.9)
        self.assertAlmostEqual(r["opportunity_cost"],60)
        self.assertAlmostEqual(r["executed_arrival_cost"],8)
        self.assertAlmostEqual(r["implementation_shortfall"],68)

    def test_no_fills(self):
        p=ParentOrder("p","BUY",100,100,102)
        r=analyse(p,[],101)
        self.assertEqual(r["fill_rate"],0)
        self.assertIsNone(r["vwap_slippage_bps"])
        self.assertAlmostEqual(r["implementation_shortfall"],200)

    def test_overfill_rejected(self):
        p=ParentOrder("p","BUY",100,100,100)
        with self.assertRaises(ValueError):
            analyse(p,[Fill("p","c",0,101,100)],100)

    def test_parent_mismatch_rejected(self):
        p=ParentOrder("p","BUY",100,100,100)
        with self.assertRaises(ValueError):
            analyse(p,[Fill("other","c",0,1,100)],100)

    def test_spreads(self):
        self.assertAlmostEqual(effective_spread_bps("BUY",100.05,100),10)
        self.assertAlmostEqual(realised_spread_bps("SELL",99.95,100),10)


if __name__ == "__main__":
    unittest.main()
