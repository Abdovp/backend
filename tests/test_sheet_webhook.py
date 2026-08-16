import unittest
from datetime import datetime

from app.services.sheet_webhook import build_sheet_row


class SheetWebhookTests(unittest.TestCase):
    def test_build_sheet_row_uses_requested_sheet_headers(self):
        order = type("Order", (), {
            "id": 42,
            "created_at": datetime(2026, 8, 17),
            "customer_name": "Ali",
            "phone": "+212612345678",
            "total": 199.0,
            "items": [],
        })()

        row = build_sheet_row(order, public_order_id="boya000042")

        self.assertEqual(row["date"], "17/8/26")
        self.assertEqual(row["order id"], "boya000042")
        self.assertEqual(row["nom"], "Ali")
        self.assertEqual(row["telephone"], "0612345678")
        self.assertEqual(row["Qté"], "")
        self.assertEqual(row["prix total"], "199 dh")
        self.assertNotIn("orderid", row)
        self.assertNotIn("téléphone", row)


if __name__ == "__main__":
    unittest.main()
