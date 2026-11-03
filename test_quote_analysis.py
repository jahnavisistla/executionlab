import tempfile
import unittest
from pathlib import Path
from quote_analysis import load_quotes, join_trades, utc_seconds


class QuoteTests(unittest.TestCase):
    def test_join_excludes_future_and_stale_quotes(self):
        with tempfile.TemporaryDirectory() as root:
            q=Path(root)/"q.csv";t=Path(root)/"t.csv"
            q.write_text("timestamp,isin,venue,bid,ask\n2026-11-02T13:00:00Z,X,VEN,99.9,100.1\n2026-11-02T13:00:10Z,X,VEN,100,100.2\n")
            t.write_text("timestamp,isin,venue,price,side\n2026-11-02T12:59:59Z,X,VEN,100,BUY\n2026-11-02T13:00:00.5Z,X,VEN,100.1,BUY\n2026-11-02T13:00:05Z,X,VEN,100.1,BUY\n")
            joined=join_trades(t,load_quotes(q),tolerance_seconds=1)
            self.assertEqual(len(joined),1)
            self.assertAlmostEqual(joined[0]["quoted_spread_bps"],20)
            self.assertAlmostEqual(joined[0]["effective_spread_bps"],20)

    def test_latest_equal_timestamp_update_wins(self):
        with tempfile.TemporaryDirectory() as root:
            quotes = Path(root) / "quotes.csv"
            trades = Path(root) / "trades.csv"
            quotes.write_text(
                "timestamp,isin,venue,bid,ask\n"
                "2026-11-02T13:00:00Z,X,VEN,101,103\n"
                "2026-11-02T13:00:00Z,X,VEN,99,101\n"
                "2026-11-02T13:00:00Z,X,VEN,100,100\n"
                "2026-11-02T13:00:00Z,X,VEN,nan,100\n"
            )
            trades.write_text(
                "timestamp,isin,venue,price,side\n"
                "2026-11-02T13:00:00Z,X,VEN,101,BUY\n"
                "2026-11-02T13:00:00Z,X,VEN,inf,BUY\n"
                "2026-11-02T13:00:00Z,X,VEN,101,\n"
            )
            joined = join_trades(trades, load_quotes(quotes))
            self.assertEqual(len(joined), 2)
            self.assertAlmostEqual(joined[0]["effective_spread_bps"], 200)
            self.assertIsNone(joined[1]["effective_spread_bps"])

    def test_timezone_is_required(self):
        with self.assertRaises(ValueError):utc_seconds("2026-11-02T13:00:00")


if __name__=="__main__":unittest.main()
