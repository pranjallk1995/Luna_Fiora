/** The backend routes the gateway forwards, and the React Query hooks over them. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { post, request } from "./http";

export type Row = Record<string, unknown>;

export type Dashboard = {
  analytics: {
    income: number;
    expense: number;
    net: number;
    categories: { category: string; total: number }[];
    trend: { day: string; income: number; expense: number }[];
  };
  transactions: Row[];
  commitments: Row[];
  goals: Row[];
  reminders: Row[];
};

export type DateRange = { start: string; end: string };
export type Resource = "transactions" | "commitments" | "goals" | "reminders";

export function useDashboard({ start, end }: DateRange) {
  return useQuery({
    queryKey: ["dashboard", start, end],
    queryFn: () =>
      request<Dashboard>(`/api/dashboard?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`),
    placeholderData: (previous) => previous,
  });
}

export function useCreate(resource: Resource) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: Row) => post(`/api/${resource}`, payload),
    onSuccess: () => client.invalidateQueries({ queryKey: ["dashboard"] }),
  });
}

export type GmailStatus = { configured: boolean; connected: boolean; email?: string | null; sign_in_expired?: boolean };

export function useGmailStatus() {
  return useQuery({
    queryKey: ["gmail-status"],
    queryFn: () => request<GmailStatus>("/api/gmail/status"),
    // Connecting happens in another tab, so check again on returning here.
    staleTime: 0,
  });
}

export function useGmailLink() {
  return useQuery({
    queryKey: ["gmail-link"],
    queryFn: () => request<{ url: string }>("/api/gmail/authorization-url"),
    retry: false,
    // Each link carries a signed state that expires, so fetch a fresh one every visit.
    staleTime: 0,
    gcTime: 0,
  });
}

export type DriveStatus = { configured: boolean; connected: boolean; email?: string | null; sign_in_expired?: boolean };
export type DriveFile = { file_id: string; name: string; path?: string | null; outcome: string; added: number; matched: number; rejected: number; error?: string | null };
export type DriveJob = {
  job_id: string;
  folder_name: string;
  status: string;
  total: number;
  processed: number;
  added: number;
  matched: number;
  error?: string | null;
  current_item?: string | null;
  outcomes: Record<string, number>;
  files?: DriveFile[];
};

const ACTIVE_STATUSES = ["queued", "listing", "running"];
const DRIVE_REFRESH_MS = 3000;
export const isActive = (job: DriveJob) => ACTIVE_STATUSES.includes(job.status);

export const useDriveStatus = () =>
  useQuery({ queryKey: ["drive-status"], queryFn: () => request<DriveStatus>("/api/drive/status"), staleTime: 0 });

export const useDriveLink = () =>
  useQuery({
    queryKey: ["drive-link"],
    queryFn: () => request<{ url: string }>("/api/drive/authorization-url"),
    retry: false,
    staleTime: 0,
    gcTime: 0,
  });

export const useDriveFolders = () =>
  useQuery({
    queryKey: ["drive-folders"],
    queryFn: async () => (await request<{ folders: { folder_id: string; name: string }[] }>("/api/drive/folders")).folders,
    staleTime: 5 * 60_000,
  });

export const useDriveJobs = (enabled: boolean) =>
  useQuery({
    queryKey: ["drive-jobs"],
    queryFn: async () => (await request<{ jobs: DriveJob[] }>("/api/imports?limit=5")).jobs,
    enabled,
    staleTime: 0,
    refetchInterval: (query) => (query.state.data?.some(isActive) ? DRIVE_REFRESH_MS : false),
  });

export const useDriveJob = (jobId: string, active: boolean) =>
  useQuery({
    queryKey: ["drive-job", jobId, active],
    queryFn: () => request<DriveJob>(`/api/imports/${jobId}`),
    refetchInterval: active ? DRIVE_REFRESH_MS : false,
    staleTime: active ? 0 : Infinity,
  });

export const drive = {
  disconnect: () => post("/api/drive/disconnect"),
  importFolder: (folder: string, recursive: boolean, password: string) =>
    post<DriveJob>("/api/imports/drive-folder", { folder, recursive, password }),
};

export function useGmailSync() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () =>
      post<{ configured: boolean; connected: boolean; imported: number; review: number }>("/api/gmail/sync"),
    onSuccess: () => client.invalidateQueries({ queryKey: ["dashboard"] }),
    // A failed sync may mean the sign-in has expired.
    onError: () => client.invalidateQueries({ queryKey: ["gmail-status"] }),
  });
}

export function useGmailDisconnect() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => post("/api/gmail/disconnect"),
    onSuccess: () => client.invalidateQueries({ queryKey: ["gmail-status"] }),
  });
}
