import { Mail, RefreshCw } from "lucide-react";

import { useGmailLink, useGmailSync, type Dashboard } from "../api";
import { dayLabel, dayValue, rupees } from "../format";
import { messageOf } from "../lib";
import { LineChart } from "./LineChart";
import { useToast } from "./Toasts";

const INCOME_COLOR = "#3987e5";
const EXPENSE_COLOR = "#d95926";

function GmailImport() {
  const link = useGmailLink();
  const sync = useGmailSync();
  const toast = useToast();

  const syncNow = () =>
    sync.mutate(undefined, {
      onSuccess: ({ configured, imported, review }) =>
        toast(
          configured
            ? `Gmail synced: ${imported} imported, ${review} to review.`
            : "Add Gmail OAuth settings to connect an inbox.",
        ),
      onError: (failure) => toast(messageOf(failure, "Gmail could not be synced.")),
    });

  return (
    <section className="lv-panel">
      <h2>Gmail transaction import</h2>
      <div className="lf-gmail">
        {link.data ? (
          <a className="lv-button" href={link.data.url} target="_blank" rel="noopener">
            <Mail size={17} />
            Connect Gmail
          </a>
        ) : (
          <p className="lv-alert lf-gmail-note">
            {link.isPending ? "Checking Gmail settings…" : "Add Gmail OAuth settings to connect an inbox."}
          </p>
        )}
        <button className="lv-button" type="button" disabled={sync.isPending} onClick={syncNow}>
          <RefreshCw size={17} />
          {sync.isPending ? "Syncing…" : "Sync now"}
        </button>
      </div>
    </section>
  );
}

export function Overview({ analytics }: { analytics: Dashboard["analytics"] }) {
  const { income, expense, net, trend, categories } = analytics;
  const largest = Math.max(...categories.map(({ total }) => total), 0);

  return (
    <>
      <div className="lv-metrics">
        <div className="lv-metric">
          <span>Income</span>
          <strong>{rupees(income)}</strong>
        </div>
        <div className="lv-metric">
          <span>Expenditure</span>
          <strong>{rupees(expense)}</strong>
        </div>
        <div className="lv-metric">
          <span>Net savings</span>
          <strong>{rupees(net)}</strong>
        </div>
      </div>

      <div className="lf-charts">
        <section className="lv-panel">
          <h2>Cash flow</h2>
          {trend.length ? (
            <LineChart
              label="Income and expenditure by day"
              fromZero
              formatX={dayLabel}
              formatY={compactRupees}
              formatValue={rupees}
              series={[
                { name: "Income", color: INCOME_COLOR, points: trend.map((day) => ({ x: dayValue(day.day), y: day.income })) },
                { name: "Expenditure", color: EXPENSE_COLOR, points: trend.map((day) => ({ x: dayValue(day.day), y: day.expense })) },
              ]}
            />
          ) : (
            <p className="lv-alert">No transactions in this date range.</p>
          )}
        </section>

        <section className="lv-panel">
          <h2>Expense categories</h2>
          {categories.length ? (
            <div className="lv-bars">
              {categories.map(({ category, total }) => (
                <div key={category}>
                  <div className="lv-bar-label">
                    <span title={category}>{category}</span>
                    <span>{rupees(total)}</span>
                  </div>
                  <div className="lv-bar-track">
                    <span className="lv-bar-fill" style={{ width: `${(total / largest) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="lv-alert">No expenses in this date range.</p>
          )}
        </section>
      </div>

      <GmailImport />
    </>
  );
}

const compactRupees = (amount: number) => `₹${amount.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
