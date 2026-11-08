import { useQueryClient } from "@tanstack/react-query";
import { Flag, Landmark, LineChart as LineChartIcon, LogOut, Receipt, type LucideIcon } from "lucide-react";
import { useState } from "react";

import { useDashboard, type Dashboard, type DateRange } from "./api";
import { Goals } from "./components/Goals";
import { Overview } from "./components/Overview";
import { Plans } from "./components/Plans";
import { Transactions } from "./components/Transactions";
import { Brand, ForbiddenPage, SignInPage, UnreachablePage } from "./components/Gate";
import { currentMonth } from "./format";
import { useSession } from "./http";
import { messageOf, remember, remembered } from "./lib";

const SECTIONS = ["overview", "transactions", "plans", "goals"] as const;
type Section = (typeof SECTIONS)[number];

const NAV: { id: Section; label: string; icon: LucideIcon }[] = [
  { id: "overview", label: "Overview", icon: LineChartIcon },
  { id: "transactions", label: "Transactions", icon: Receipt },
  { id: "plans", label: "EMIs & SIPs", icon: Landmark },
  { id: "goals", label: "Goals & reminders", icon: Flag },
];

type Settings = { version: string };

function SectionBody({ section, dashboard }: { section: Section; dashboard: Dashboard }) {
  if (section === "transactions") return <Transactions rows={dashboard.transactions} />;
  if (section === "plans") return <Plans rows={dashboard.commitments} />;
  if (section === "goals") return <Goals goals={dashboard.goals} reminders={dashboard.reminders} />;
  return <Overview analytics={dashboard.analytics} />;
}

function Workspace({ logoutUrl, settings }: { logoutUrl: string; settings: Settings }) {
  const [section, setSection] = useState<Section>(() => remembered("lf-section", SECTIONS, "overview"));
  const [range, setRange] = useState<DateRange>(currentMonth);
  const dashboard = useDashboard(range);
  const client = useQueryClient();

  const choose = (id: Section) => {
    setSection(id);
    remember("lf-section", id);
  };

  return (
    <main className="lv-page">
      <div className="lv-header-row">
        <Brand />
        <div className="lv-header-actions">
          <input
            className="lv-input lf-date"
            type="date"
            aria-label="From date"
            value={range.start}
            max={range.end}
            required
            onChange={(event) => event.target.value && setRange({ ...range, start: event.target.value })}
          />
          <input
            className="lv-input lf-date"
            type="date"
            aria-label="To date"
            value={range.end}
            min={range.start}
            required
            onChange={(event) => event.target.value && setRange({ ...range, end: event.target.value })}
          />
          <a className="lv-button lv-sign-out" href={logoutUrl}>
            <LogOut size={16} />
            Sign out
          </a>
        </div>
      </div>

      <nav className="lv-nav" aria-label="Section">
        {NAV.map(({ id, label, icon: Icon }) => (
          <button
            className={section === id ? "lv-nav-item lv-nav-active" : "lv-nav-item"}
            type="button"
            key={id}
            aria-label={label}
            aria-current={section === id ? "page" : undefined}
            onClick={() => choose(id)}
          >
            <Icon size={17} />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      {dashboard.error && !dashboard.data && (
        <div className="lv-alert lv-alert-error">
          {messageOf(dashboard.error, "Luna Fiora's backend is unavailable.")}{" "}
          <button className="lv-link" type="button" onClick={() => client.invalidateQueries({ queryKey: ["dashboard"] })}>
            Try again
          </button>
        </div>
      )}
      {dashboard.data && <SectionBody section={section} dashboard={dashboard.data} />}
      <footer className="lv-footer">Luna Fiora{settings.version && ` · v${settings.version}`}</footer>
    </main>
  );
}

export function App() {
  const { data: session, error, refetch } = useSession<Settings>();

  if (error) return <UnreachablePage onRetry={() => refetch()} />;
  if (!session) return null;
  if (session.status === "signed_out") return <SignInPage url={session.login_url} />;
  if (session.status === "forbidden") return <ForbiddenPage email={session.email} logoutUrl={session.logout_url} />;
  return <Workspace logoutUrl={session.logout_url} settings={session.settings} />;
}
