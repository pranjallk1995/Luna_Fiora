import type { LucideIcon } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";

import { useCreate, type Resource, type Row } from "../api";
import { messageOf } from "../lib";
import { useToast } from "./Toasts";

type Props = {
  resource: Resource;
  title?: string;
  action: string;
  saved: string;
  icon?: LucideIcon;
  /** Turn the submitted fields into the backend's payload. */
  payload: (fields: FormData) => Row;
  children: ReactNode;
};

export const fieldText = (fields: FormData, name: string) => String(fields.get(name) ?? "").trim();

/** A form that adds one record, keeps its values if the server refuses, and clears on success. */
export function CreateForm({ resource, title, action, saved, icon: Icon, payload, children }: Props) {
  const create = useCreate(resource);
  const toast = useToast();
  const [error, setError] = useState("");

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    setError("");
    create.mutate(payload(new FormData(form)), {
      onSuccess: () => {
        form.reset();
        toast(saved);
      },
      onError: (failure) => setError(messageOf(failure, "That could not be saved.")),
    });
  };

  return (
    <form className="lv-panel lv-form" onSubmit={submit}>
      {title && <h2>{title}</h2>}
      {children}
      {error && <p className="lv-alert lv-alert-error">{error}</p>}
      <button className="lv-button lv-button-primary" type="submit" disabled={create.isPending}>
        {Icon && <Icon size={17} />}
        {action}
      </button>
    </form>
  );
}
