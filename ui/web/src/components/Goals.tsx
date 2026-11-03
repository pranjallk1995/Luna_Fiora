import { useState } from "react";

import type { Row } from "../api";
import { dateOnly, offsetDays, rupees } from "../format";
import { remember, remembered } from "../lib";
import { CreateForm, fieldText } from "./CreateForm";
import { Table, type Column } from "./Table";

const GOAL_COLUMNS: Column[] = [
  { label: "Goal", value: (row) => String(row.name) },
  { label: "Target date", value: (row) => dateOnly(row.target_date) },
  { label: "Priority", value: (row) => String(row.priority) },
  { label: "Saved", number: true, value: (row) => rupees(Number(row.current_amount)) },
  { label: "Target", number: true, value: (row) => rupees(Number(row.target_amount)) },
];

const REMINDER_COLUMNS: Column[] = [
  { label: "Reminder", value: (row) => String(row.title) },
  { label: "Due", value: (row) => dateOnly(row.due_at) },
  { label: "Repeat", value: (row) => String(row.recurrence) },
  { label: "For", value: (row) => String(row.entity_type) },
  { label: "Done", value: (row) => (row.completed ? "Yes" : "No") },
];

const TABS = ["goals", "reminders"] as const;

export function Goals({ goals, reminders }: { goals: Row[]; reminders: Row[] }) {
  const [tab, setTab] = useState(() => remembered("lf-goals-tab", TABS, "goals"));

  return (
    <>
      <div className="lv-tabs" role="tablist">
        {TABS.map((id) => (
          <button
            className={tab === id ? "lv-tab lv-tab-active" : "lv-tab"}
            type="button"
            role="tab"
            aria-selected={tab === id}
            key={id}
            onClick={() => {
              setTab(id);
              remember("lf-goals-tab", id);
            }}
          >
            {id === "goals" ? "Goals" : "Reminders"}
          </button>
        ))}
      </div>

      {tab === "goals" ? (
        <>
          <CreateForm
            resource="goals"
            title="Create financial goal"
            action="Create goal"
            saved="Goal created."
            payload={(fields) => ({
              name: fieldText(fields, "name"),
              target_amount: Number(fields.get("target")),
              current_amount: Number(fields.get("saved") || 0),
              target_date: fieldText(fields, "due"),
              priority: "medium",
            })}
          >
            <label className="lv-field">
              Goal name
              <input className="lv-input" name="name" maxLength={80} required />
            </label>
            <div className="lv-form-row">
              <label className="lv-field">
                Target
                <input className="lv-input" name="target" type="number" min="0.01" step="0.01" required />
              </label>
              <label className="lv-field">
                Already saved
                <input className="lv-input" name="saved" type="number" min="0" step="0.01" defaultValue="0" />
              </label>
              <label className="lv-field">
                Target date
                <input className="lv-input" name="due" type="date" defaultValue={offsetDays(365)} required />
              </label>
            </div>
          </CreateForm>
          <Table rows={goals} columns={GOAL_COLUMNS} empty="No financial goals yet." />
        </>
      ) : (
        <>
          <CreateForm
            resource="reminders"
            action="Add reminder"
            saved="Reminder added."
            payload={(fields) => ({
              title: fieldText(fields, "title"),
              due_at: `${fieldText(fields, "due")}T00:00:00`,
              recurrence: fieldText(fields, "repeat"),
              entity_type: "general",
            })}
          >
            <label className="lv-field">
              Reminder
              <input className="lv-input" name="title" maxLength={120} required />
            </label>
            <div className="lv-form-row">
              <label className="lv-field">
                Due date
                <input className="lv-input" name="due" type="date" defaultValue={offsetDays(1)} required />
              </label>
              <label className="lv-field">
                Repeat
                <select className="lv-select" name="repeat" defaultValue="none">
                  <option value="none">none</option>
                  <option value="monthly">monthly</option>
                  <option value="yearly">yearly</option>
                </select>
              </label>
            </div>
          </CreateForm>
          <Table rows={reminders} columns={REMINDER_COLUMNS} empty="No reminders yet." />
        </>
      )}
    </>
  );
}
