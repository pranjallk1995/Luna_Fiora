/** Dates and amounts as this app shows them. */

export const rupees = (amount: number) =>
  `₹${amount.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/** A date as YYYY-MM-DD in this browser's own time zone. */
export function isoDate(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

export const dayValue = (day: string) => Date.parse(`${day.slice(0, 10)}T00:00:00Z`);

export const dayLabel = (value: number) =>
  new Date(value).toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "UTC" });

/** A stored timestamp as a calendar date in this browser's own time zone; plain dates pass through. */
export function dateOnly(value: unknown): string {
  if (typeof value !== "string") return "";
  return value.length > 10 ? isoDate(new Date(value)) : value;
}

export function currentMonth(today = new Date()): { start: string; end: string } {
  return { start: isoDate(new Date(today.getFullYear(), today.getMonth(), 1)), end: isoDate(today) };
}

export function offsetDays(days: number, today = new Date()): string {
  return isoDate(new Date(today.getFullYear(), today.getMonth(), today.getDate() + days));
}
