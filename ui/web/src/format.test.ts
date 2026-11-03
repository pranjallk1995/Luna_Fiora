import { describe, expect, it } from "vitest";

import { niceTicks } from "./components/LineChart";
import { currentMonth, dateOnly, dayLabel, dayValue, isoDate, offsetDays, rupees } from "./format";

describe("amounts and dates", () => {
  it("groups rupees the Indian way", () => {
    expect(rupees(1234567.5)).toBe("₹12,34,567.50");
  });

  it("gives a range from the first of the month to today", () => {
    expect(currentMonth(new Date(2026, 1, 14))).toEqual({ start: "2026-02-01", end: "2026-02-14" });
  });

  it("crosses a year when offsetting", () => {
    expect(offsetDays(1, new Date(2026, 11, 31))).toBe("2027-01-01");
  });

  it("keeps calendar days in their own zone", () => {
    expect(isoDate(new Date(2026, 0, 5))).toBe("2026-01-05");
    expect(dayLabel(dayValue("2026-03-09"))).toBe("9 Mar");
    expect(dateOnly("2026-03-09")).toBe("2026-03-09");
    expect(dateOnly(null)).toBe("");
  });
});

describe("niceTicks", () => {
  it("covers the range with round steps", () => {
    expect(niceTicks(0, 950)).toEqual([0, 250, 500, 750, 1000]);
  });

  it("handles a flat series", () => {
    expect(niceTicks(5, 5)).toEqual([5]);
  });
});
