import type { ReactNode } from "react";

import type { Row } from "../api";

export type Column = {
  label: string;
  value: (row: Row) => ReactNode;
  number?: boolean;
};

export function Table({ rows, columns, empty }: { rows: Row[]; columns: Column[]; empty: string }) {
  if (!rows.length) return <p className="lv-alert">{empty}</p>;
  return (
    <div className="lv-panel lv-table-scroll">
      <table className="lv-table">
        <thead>
          <tr>
            {columns.map(({ label, number }) => (
              <th className={number ? "lv-number" : undefined} key={label}>
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={String(row.id ?? index)}>
              {columns.map(({ label, value, number }) => (
                <td className={number ? "lv-number" : undefined} key={label}>
                  {value(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
