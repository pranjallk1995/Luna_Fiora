import unittest
from datetime import datetime, timezone
from pydantic import ValidationError
from app.core.models import TransactionInput, GoalInput
from app.integrations.gmail import deterministic_extract

class FinanceModelsTest(unittest.TestCase):
    def test_transaction_rejects_non_positive_amount(self):
        with self.assertRaises(ValidationError):
            TransactionInput(occurred_at=datetime.now(timezone.utc),kind="expense",amount=0,merchant="Shop")
    def test_goal_rejects_empty_name(self):
        with self.assertRaises(ValidationError):
            GoalInput(name="",target_amount=100,target_date="2030-01-01")

class GmailParserTest(unittest.TestCase):
    def test_debit_message(self):
        result=deterministic_extract({"id":"m1","subject":"UPI payment","sender":"bank@example.com",
          "received_at":datetime(2026,1,2,tzinfo=timezone.utc),"body":"Rs. 1,250.50 debited from your account"})
        self.assertEqual(result["kind"],"expense")
        self.assertEqual(result["amount"],"1250.50")
        self.assertEqual(result["external_id"],"m1")
    def test_ignores_non_transaction(self):
        self.assertIsNone(deterministic_extract({"id":"m2","subject":"Offer","sender":"shop",
          "received_at":datetime.now(timezone.utc),"body":"Save Rs 500 on your next visit"}))

if __name__=="__main__": unittest.main()