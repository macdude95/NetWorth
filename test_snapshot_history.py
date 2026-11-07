"""Regression checks for the recovered September/October 2026 snapshots."""
import json
from pathlib import Path
import unittest


class SnapshotHistoryTests(unittest.TestCase):
    def test_recovered_months_preserve_reported_balances(self):
        snapshots = json.loads((Path(__file__).parent / 'data/snapshots.json').read_text())['snapshots']
        dates = [s['date'] for s in snapshots]
        self.assertEqual(dates, sorted(set(dates)))
        by_date = {s['date']: s for s in snapshots}
        keys = ['michael_robinhood_retirement', 'michael_robinhood_taxable',
                'michael_fidelity_401k', 'chris_robinhood_retirement',
                'chris_fidelity_401k', 'chris_invesco_ira']
        # September: original commit 834aaa0. October: updates through a273041.
        expected = {
            '2026-09-01': ([176629, 468822, 298135.99, 94165.21, 68852.49, 11631.95], 646811, 564076),
            '2026-10-01': ([179653, 465730, 305375, 99547, 67721, 11853.67], 633795, 562752),
            '2026-11-01': ([168482, 455325, 306205.45, 87983.88, 66708.94, 11944.75], 609838.62, 561425.38),
        }
        for date, (balances, equity, mortgage) in expected.items():
            with self.subTest(date=date):
                self.assertIn(date, by_date)
                snapshot = by_date[date]
                self.assertEqual(snapshot['accounts'], dict(zip(keys, balances)))
                self.assertEqual(snapshot['home_equity'], equity)
                self.assertEqual(snapshot['mortgage_balance'], mortgage)
                self.assertEqual(snapshot['income'], 400000)
                self.assertEqual(snapshot['expenses'], 108000)


if __name__ == '__main__':
    unittest.main()
