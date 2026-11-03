import { Plus } from "lucide-react";

import type { Row } from "../api";
import { dateOnly, isoDate, rupees } from "../format";
import { CreateForm, fieldText } from "./CreateForm";
import { Table, type Column } from "./Table";

const COLUMNS: Column[] = [
  { label: "Type", value: (row) => String(row.kind).toUpperCase() },
  { label: "Name", value: (row) => String(row.name) },
  { label: "Day of month", number: true, value: (row) => String(row.day_of_month) },
  { label: "Started", value: (row) => dateOnly(row.start_date) },
  { label: "Ends", value: (row) => dateOnly(row.end_date) },
  { label: "Active", value: (row) => (row.active ? "Yes" : "No") },
  { label: "Monthly amount", number: true, value: (row) => rupees(Number(row.amount)) },
];

export function Plans({ rows }: { rows: Row[] }) {
  return (
    <>
      <CreateForm
        resource="commitments"
        title="Add EMI or SIP"
        action="Add plan"
        saved="Plan added."
        icon={Plus}
        payload={(fields) => ({
          kind: fieldText(fields, "kind"),
          name: fieldText(fields, "name"),
          amount: Number(fields.get("amount")),
          day_of_month: Number(fields.get("day")),
          start_date: isoDate(new Date()),
          active: true,
        })}
      >
        <div className="lv-form-row">
          <label className="lv-field">
            Type
            <select className="lv-select" name="kind" defaultValue="emi">
              <option value="emi">EMI</option>
              <option value="sip">SIP</option>
            </select>
          </label>
          <label className="lv-field">
            Name
            <input className="lv-input" name="name" maxLength={80} required />
          </label>
          <label className="lv-field">
            Monthly amount
            <input className="lv-input" name="amount" type="number" min="0.01" step="0.01" required />
          </label>
          <label className="lv-field">
            Day of month
            <input className="lv-input" name="day" type="number" min="1" max="31" step="1" defaultValue="1" required />
          </label>
        </div>
      </CreateForm>

      <Table rows={rows} columns={COLUMNS} empty="No EMIs or SIPs yet." />
    </>
  );
}
