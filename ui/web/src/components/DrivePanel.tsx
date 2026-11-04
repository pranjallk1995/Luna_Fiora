import { useQueryClient } from "@tanstack/react-query";
import { CloudDownload, CloudOff, HardDriveDownload } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { drive, isActive, useDriveFolders, useDriveJob, useDriveJobs, useDriveLink, useDriveStatus, type DriveJob } from "../api";
import { messageOf } from "../lib";
import { useToast } from "./Toasts";

const outcomeLabel = (outcome: string) => outcome.replace(/_/g, " ");

function Connect({ label = "Connect Google Drive" }: { label?: string }) {
  const link = useDriveLink();
  if (link.error) return <p className="lv-alert lv-alert-error lf-gmail-note">{messageOf(link.error, "Could not start the Google sign-in.")}</p>;
  return (
    <>
      <a className={link.data ? "lv-button lv-button-wide" : "lv-button lv-button-wide lf-disabled"} href={link.data?.url} target="_blank" rel="noopener">
        <HardDriveDownload size={17} />
        {label}
      </a>
      <p className="lv-caption lf-gmail-note">Read-only access. After signing in, close that tab and come back here.</p>
    </>
  );
}

function ImportFolder({ refreshJobs }: { refreshJobs: () => void }) {
  const toast = useToast();
  const folders = useDriveFolders();
  const [picked, setPicked] = useState("");
  const [typed, setTyped] = useState("");
  const [password, setPassword] = useState("");
  const [recursive, setRecursive] = useState(true);
  const folder = typed.trim() || picked;

  const start = async () => {
    try {
      const job = await drive.importFolder(folder, recursive, password);
      toast(`Importing ${job.folder_name}`);
      setPassword("");
      refreshJobs();
    } catch (failure) {
      toast(messageOf(failure, "Could not start the import."));
    }
  };

  return (
    <div className="lv-form">
      {folders.error && <p className="lv-alert lv-alert-error lf-gmail-note">{messageOf(folders.error, "Could not list your Drive folders.")}</p>}
      <select className="lv-select" aria-label="Folder in My Drive" value={picked} onChange={(event) => setPicked(event.target.value)}>
        <option value="">Choose a folder in My Drive</option>
        {(folders.data ?? []).map(({ folder_id, name }) => (
          <option value={folder_id} key={folder_id}>
            {name}
          </option>
        ))}
      </select>
      <input className="lv-input" aria-label="Or a folder link, ID, or name" placeholder="…or paste a folder link, ID, or exact name" value={typed} onChange={(event) => setTyped(event.target.value)} />
      <div className="lf-drive-row">
        <label className="lf-drive-check">
          <input type="checkbox" checked={recursive} onChange={(event) => setRecursive(event.target.checked)} />
          Subfolders
        </label>
        <input className="lv-input" type="password" autoComplete="off" aria-label="Password for locked PDFs" placeholder="Password for locked PDFs, if any" value={password} onChange={(event) => setPassword(event.target.value)} />
        <button className="lv-button" type="button" aria-label="Import the folder" disabled={!folder} onClick={start}>
          <CloudDownload size={17} />
        </button>
      </div>
      <p className="lv-caption lf-gmail-note">Rows are read by the local model, so check the first few against the statement.</p>
    </div>
  );
}

function Files({ job }: { job: DriveJob }) {
  const report = useDriveJob(job.job_id, isActive(job));
  const files = report.data?.files ?? [];
  if (!files.length) return null;
  return (
    <div className="lv-table-scroll">
      <table className="lv-table">
        <thead>
          <tr>
            <th>File</th>
            <th>Outcome</th>
            <th>Added</th>
            <th>Matched</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file) => (
            <tr key={file.file_id}>
              <td>
                {file.path ?? ""}
                {file.name}
              </td>
              <td>{outcomeLabel(file.outcome)}</td>
              <td>{file.added}</td>
              <td>{file.matched}</td>
              <td>{file.error ?? (file.rejected ? `${file.rejected} row(s) could not be read` : "")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Job({ job }: { job: DriveJob }) {
  const [open, setOpen] = useState(false);
  return (
    <details className="lf-drive-job" open={open} onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary>
        {job.folder_name} — {job.status} ({job.processed}/{job.total}) · {job.added} added, {job.matched} matched
      </summary>
      {job.current_item && <p className="lv-caption">Reading {job.current_item}</p>}
      {job.error && <p className="lv-alert lv-alert-error">{job.error}</p>}
      {open && <Files job={job} />}
    </details>
  );
}

function Connected({ email, expired }: { email?: string | null; expired?: boolean }) {
  const client = useQueryClient();
  const toast = useToast();
  const jobs = useDriveJobs(true);
  const refreshJobs = () => client.invalidateQueries({ queryKey: ["drive-jobs"] });
  const active = jobs.data?.filter(isActive).length ?? 0;
  const previous = useRef(active);

  // Each file adds its rows when it finishes, so the figures refresh as a job moves on.
  const added = jobs.data?.reduce((total, job) => total + job.added, 0) ?? 0;
  useEffect(() => {
    if (previous.current || active) client.invalidateQueries({ queryKey: ["dashboard"] });
    previous.current = active;
  }, [active, added, client]);

  const disconnect = async () => {
    try {
      await drive.disconnect();
      client.removeQueries({ queryKey: ["drive-folders"] });
      client.invalidateQueries({ queryKey: ["drive-status"] });
    } catch (failure) {
      toast(messageOf(failure, "Could not disconnect Google Drive."));
    }
  };

  return (
    <>
      <div className="lf-gmail-account">
        <p className="lv-caption">Connected as {email}</p>
        <button className="lv-icon-button" type="button" aria-label="Disconnect Google Drive" onClick={disconnect}>
          <CloudOff size={16} />
        </button>
      </div>
      {expired ? (
        <>
          <p className="lv-alert lv-alert-error lf-gmail-note">Your Google Drive sign-in has expired. Reconnect to keep importing. Your transactions are safe.</p>
          <Connect label="Reconnect Google Drive" />
        </>
      ) : (
        <ImportFolder refreshJobs={refreshJobs} />
      )}
      {jobs.error && <p className="lv-caption lf-gmail-note">Import progress is unavailable right now.</p>}
      {jobs.data?.map((job) => <Job job={job} key={job.job_id} />)}
    </>
  );
}

export function DrivePanel() {
  const status = useDriveStatus();

  return (
    <section className="lv-panel">
      <h2>Google Drive statement import</h2>
      <div className="lf-gmail">
        {status.error && <p className="lv-alert lv-alert-error lf-gmail-note">{messageOf(status.error, "Could not reach Fiora.")}</p>}
        {status.data && !status.data.configured && (
          <p className="lv-alert lf-gmail-note">Google Drive is not set up yet: set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in Fiora's .env and restart it.</p>
        )}
        {status.data?.configured && !status.data.connected && <Connect />}
        {status.data?.configured && status.data.connected && <Connected email={status.data.email} expired={status.data.sign_in_expired} />}
      </div>
    </section>
  );
}
