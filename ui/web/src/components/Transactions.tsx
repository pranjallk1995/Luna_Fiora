import { Plus } from "lucide-react";

import type { Row } from "../api";
import { dateOnly, isoDate, rupees } from "../format";
import { CreateForm, fieldText } from "./CreateForm";
import { Table, type Column } from "./Table";

const COLUMNS: Column[] = [
  { label: "Date", value: (row) => dateOnly(row.occurred_at) },
  { label: "Type", value: (row) => String(row.kind) },
  { label: "Merchant or source", value: (row) => String(row.merchant) },
  { label: "Category", value: (row) => String(row.category) },
  { label: "Account", value: (row) => String(row.account ?? "") },
  { label: "Source", value: (row) => String(row.source ?? "") },
  { label: "Amount", number: true, value: (row) => rupees(Number(row.amount)) },
];

export function Transactions({ rows }: { rows: Row[] }) {
  return (
    <>
      <CreateForm
        resource="transactions"
        title="Add transaction"
        action="Add transaction"
        saved="Transaction added."
        icon={Plus}
        payload={(fields) => ({
          occurred_at: `${fieldText(fields, "when")}T00:00:00`,
          kind: fieldText(fields, "kind"),
          amount: Number(fields.get("amount")),
          merchant: fieldText(fields, "merchant"),
          category: fieldText(fields, "category") || "Uncategorized",
          account: fieldText(fields, "account") || null,
        })}
      >
        <div className="lv-form-row">
          <label className="lv-field">
            Type
            <select className="lv-select" name="kind" defaultValue="expense">
              <option value="expense">expense</option>
              <option value="income">income</option>
            </select>
          </label>
          <label className="lv-field">
            Amount
            <input className="lv-input" name="amount" type="number" min="0.01" step="0.01" required />
          </label>
          <label className="lv-field">
            Date
            <input className="lv-input" name="when" type="date" defaultValue={isoDate(new Date())} required />
          </label>
        </div>
        <label className="lv-field">
          Merchant or source
          <input className="lv-input" name="merchant" maxLength={120} required />
        </label>
        <label className="lv-field">
          Category
          <input className="lv-input" name="category" maxLength={60} defaultValue="Uncategorized" />
        </label>
        <label className="lv-field">
          Account
          <input className="lv-input" name="account" maxLength={80} />
        </label>
      </CreateForm>

      <h2 className="lv-section-title">Transactions</h2>
      <Table rows={rows} columns={COLUMNS} empty="No transactions in this date range." />
    </>
  );
}
