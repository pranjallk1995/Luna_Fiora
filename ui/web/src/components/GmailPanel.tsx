import { CloudOff, Mail, RefreshCw } from "lucide-react";

import { useGmailDisconnect, useGmailLink, useGmailStatus, useGmailSync } from "../api";
import { messageOf } from "../lib";
import { useToast } from "./Toasts";

function Connect({ label = "Connect Gmail" }: { label?: string }) {
  const link = useGmailLink();
  if (link.error) return <p className="lv-alert lv-alert-error lf-gmail-note">{messageOf(link.error, "Could not start the Google sign-in.")}</p>;
  return (
    <>
      <a className={link.data ? "lv-button lv-button-wide" : "lv-button lv-button-wide lf-disabled"} href={link.data?.url} target="_blank" rel="noopener">
        <Mail size={17} />
        {label}
      </a>
      <p className="lv-caption lf-gmail-note">Read-only access. After signing in, close that tab and come back here.</p>
    </>
  );
}

function Connected({ email, expired }: { email?: string | null; expired?: boolean }) {
  const sync = useGmailSync();
  const disconnect = useGmailDisconnect();
  const toast = useToast();

  const syncNow = () =>
    sync.mutate(undefined, {
      onSuccess: ({ imported, review }) => toast(`Gmail synced: ${imported} imported, ${review} to review.`),
      onError: (failure) => toast(messageOf(failure, "Gmail could not be synced.")),
    });
  const disconnectNow = () =>
    disconnect.mutate(undefined, {
      onError: (failure) => toast(messageOf(failure, "Could not disconnect Gmail.")),
    });

  return (
    <>
      <div className="lf-gmail-account">
        <p className="lv-caption">Connected as {email}</p>
        <button className="lv-icon-button" type="button" aria-label="Disconnect Gmail" disabled={disconnect.isPending} onClick={disconnectNow}>
          <CloudOff size={16} />
        </button>
      </div>
      {expired ? (
        <>
          <p className="lv-alert lv-alert-error lf-gmail-note">
            Your Gmail sign-in has expired. Reconnect to keep importing. Your transactions are safe.
          </p>
          <Connect label="Reconnect Gmail" />
        </>
      ) : (
        <button className="lv-button lv-button-wide" type="button" disabled={sync.isPending} onClick={syncNow}>
          <RefreshCw size={17} />
          {sync.isPending ? "Syncing…" : "Sync now"}
        </button>
      )}
    </>
  );
}

export function GmailPanel() {
  const status = useGmailStatus();

  return (
    <section className="lv-panel">
      <h2>Gmail transaction import</h2>
      <div className="lf-gmail">
        {status.error && <p className="lv-alert lv-alert-error lf-gmail-note">{messageOf(status.error, "Could not reach Fiora.")}</p>}
        {status.data && !status.data.configured && (
          <p className="lv-alert lf-gmail-note">Gmail is not set up yet: set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in Fiora's .env and restart it.</p>
        )}
        {status.data?.configured && !status.data.connected && <Connect />}
        {status.data?.configured && status.data.connected && <Connected email={status.data.email} expired={status.data.sign_in_expired} />}
      </div>
    </section>
  );
}
