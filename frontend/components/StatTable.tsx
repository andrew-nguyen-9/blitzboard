import { formatStat, type StatFormat } from "@/lib/viz";

// StatCell + StatTable — the instrument's tabular primitives.
//
// No-clip guarantee (the named v1 homepage bug): numerals render in mono with
// `tabular-nums`, so every glyph is exactly 1ch. Reserving `min-width` equal to
// the formatted string's length (in ch) means digits always fit — at 360px or
// 1920px, and at any A11y text scale, because ch tracks font-size. Sizing is
// `clamp()`-driven, never fixed px.

export function StatCell({
  value,
  label,
  decimals = 0,
  sign,
  suffix,
  size = "md",
  align = "start",
  className,
}: {
  value: number | null | undefined;
  label?: string;
  size?: "sm" | "md" | "lg";
  align?: "start" | "end" | "center";
  className?: string;
} & StatFormat) {
  const text = formatStat(value, { decimals, sign, suffix });
  const sizeClass =
    size === "lg"
      ? "text-[clamp(2.5rem,6vw,4.5rem)] leading-none"
      : size === "sm"
        ? "text-[var(--step-0)] leading-tight"
        : "text-[clamp(1.25rem,2.5vw,2rem)] leading-tight";

  return (
    <div className={`flex flex-col gap-1 ${className ?? ""}`} style={{ textAlign: align }}>
      <span
        className={`font-mono font-semibold tabular-nums text-ink ${sizeClass}`}
        // Reserve enough character cells that the longest expected glyph run
        // never clips. +0.5ch breathing room for the decimal point / sign.
        style={{ minWidth: `${text.length + 0.5}ch`, display: "inline-block" }}
      >
        {text}
      </span>
      {label && <span className="text-label uppercase text-ink-2">{label}</span>}
    </div>
  );
}

export interface StatColumn extends StatFormat {
  /** key into each row object */
  key: string;
  label: string;
  /** numeric columns are mono/tabular and right-aligned; text columns are not */
  numeric?: boolean;
  align?: "start" | "end";
}

/**
 * A semantic <table> of stats. `<th scope>` on headers and row keys; numeric
 * cells reserve ch-width so they never clip. Under 640px it stacks into labelled
 * stat rows (`.stat-table` in globals.css) instead of horizontal scrolling.
 */
export function StatTable<Row extends Record<string, unknown>>({
  caption,
  columns,
  rows,
  rowKey,
  className,
}: {
  caption: string;
  columns: StatColumn[];
  rows: Row[];
  /** column key whose value labels the row (becomes <th scope="row">) */
  rowKey: string;
  className?: string;
}) {
  return (
    <table className={`stat-table w-full border-collapse text-left ${className ?? ""}`}>
      <caption className="sr-only">{caption}</caption>
      <thead>
        <tr>
          {columns.map((c) => (
            <th
              key={c.key}
              scope="col"
              className={`px-3 py-2 text-label uppercase text-ink-2 ${
                c.numeric || c.align === "end" ? "text-right" : "text-left"
              }`}
            >
              {c.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={String(row[rowKey] ?? i)} className="border-t border-line">
            {columns.map((c) => {
              const raw = row[c.key];
              const isRowHeader = c.key === rowKey;
              const numericAlign = c.numeric || c.align === "end";
              const content = c.numeric
                ? formatStat(typeof raw === "number" ? raw : null, c)
                : String(raw ?? "—");
              const cellClass = `px-3 py-2 ${numericAlign ? "text-right" : "text-left"} ${
                c.numeric ? "font-mono tabular-nums" : ""
              }`;

              return isRowHeader ? (
                <th key={c.key} scope="row" data-label={c.label} className={`${cellClass} font-semibold text-ink`}>
                  {content}
                </th>
              ) : (
                <td key={c.key} data-label={c.label} className={`${cellClass} text-ink-1`}>
                  {c.numeric ? (
                    <span style={{ minWidth: `${content.length + 0.5}ch`, display: "inline-block" }}>{content}</span>
                  ) : (
                    content
                  )}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
