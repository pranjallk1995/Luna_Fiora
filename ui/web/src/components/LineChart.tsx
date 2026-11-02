import { useLayoutEffect, useRef, useState } from "react";

export type Point = { x: number; y: number };
export type Series = { name: string; color: string; points: Point[] };

type Props = {
  series: Series[];
  label: string;
  formatX: (x: number) => string;
  formatY: (y: number) => string;
  /** The tooltip's value, when it should say more than the axis. */
  formatValue?: (y: number) => string;
  /** Start the axis at zero; amounts want this, a body weight does not. */
  fromZero?: boolean;
  height?: number;
};

const MARGIN = { top: 12, right: 16, bottom: 28, left: 64 };

/** Round axis values covering ``low`` to ``high``. */
export function niceTicks(low: number, high: number, wanted = 5): number[] {
  if (low === high) return [low];
  const rough = (high - low) / Math.max(1, wanted - 1);
  const power = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 2.5, 5, 10].map((factor) => factor * power).find((candidate) => candidate >= rough)!;
  const ticks: number[] = [];
  const first = Math.floor(low / step);
  const last = Math.ceil(high / step);
  for (let index = first; index <= last; index += 1) ticks.push(Number((index * step).toFixed(10)));
  return ticks;
}

/** One y-axis of lines with a crosshair and a tooltip at the nearest x. */
export function LineChart({ series, label, formatX, formatY, formatValue = formatY, fromZero = false, height = 280 }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(640);
  const [hovered, setHovered] = useState<number | null>(null);

  useLayoutEffect(() => {
    const element = box.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const xs = [...new Set(series.flatMap(({ points }) => points.map((point) => point.x)))].sort((a, b) => a - b);
  const ys = series.flatMap(({ points }) => points.map((point) => point.y));
  if (!xs.length) return null;

  const ticks = niceTicks(fromZero ? Math.min(0, ...ys) : Math.min(...ys), Math.max(...ys));
  const [yLow, yHigh] = [ticks[0], Math.max(ticks[ticks.length - 1], ticks[0] + 1)];
  const [xLow, xHigh] = [xs[0], xs[xs.length - 1]];
  const plotWidth = Math.max(1, width - MARGIN.left - MARGIN.right);
  const plotHeight = height - MARGIN.top - MARGIN.bottom;
  const xAt = (x: number) => MARGIN.left + (xHigh === xLow ? plotWidth / 2 : ((x - xLow) / (xHigh - xLow)) * plotWidth);
  const yAt = (y: number) => MARGIN.top + plotHeight - ((y - yLow) / (yHigh - yLow)) * plotHeight;
  const labelled = xs.length <= 4 ? xs : [xs[0], xs[Math.floor(xs.length / 2)], xs[xs.length - 1]];

  const hover = (clientX: number) => {
    const left = box.current?.getBoundingClientRect().left ?? 0;
    const at = clientX - left;
    setHovered(xs.reduce((best, x) => (Math.abs(xAt(x) - at) < Math.abs(xAt(best) - at) ? x : best), xs[0]));
  };

  return (
    <figure className="lv-chart" ref={box}>
      <svg
        role="img"
        aria-label={label}
        width={width}
        height={height}
        onPointerMove={(event) => hover(event.clientX)}
        onPointerDown={(event) => hover(event.clientX)}
        onPointerLeave={() => setHovered(null)}
      >
        {ticks.map((tick) => (
          <g key={tick}>
            <line className="lv-chart-grid" x1={MARGIN.left} x2={width - MARGIN.right} y1={yAt(tick)} y2={yAt(tick)} />
            <text className="lv-chart-axis" x={MARGIN.left - 8} y={yAt(tick) + 4} textAnchor="end">
              {formatY(tick)}
            </text>
          </g>
        ))}
        {labelled.map((x, index) => (
          <text
            className="lv-chart-axis"
            key={x}
            x={xAt(x)}
            y={height - 8}
            textAnchor={index === 0 ? "start" : index === labelled.length - 1 ? "end" : "middle"}
          >
            {formatX(x)}
          </text>
        ))}
        {hovered !== null && (
          <line className="lv-chart-cross" x1={xAt(hovered)} x2={xAt(hovered)} y1={MARGIN.top} y2={MARGIN.top + plotHeight} />
        )}
        {series.map(({ name, color, points }) => (
          <g key={name}>
            <polyline
              fill="none"
              stroke={color}
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
              points={points.map((point) => `${xAt(point.x)},${yAt(point.y)}`).join(" ")}
            />
            {points
              .filter((point) => points.length === 1 || point.x === hovered)
              .map((point) => (
                <circle className="lv-chart-dot" key={point.x} cx={xAt(point.x)} cy={yAt(point.y)} r={4} fill={color} />
              ))}
          </g>
        ))}
      </svg>
      {hovered !== null && (
        <div
          className="lv-chart-tip"
          style={{
            left: Math.min(xAt(hovered) + 12, Math.max(0, width - 190)),
            top: MARGIN.top,
          }}
        >
          <strong>{formatX(hovered)}</strong>
          {series.map(({ name, color, points }) => {
            const point = points.find((candidate) => candidate.x === hovered);
            return (
              point && (
                <span key={name}>
                  <i style={{ background: color }} />
                  {name}: {formatValue(point.y)}
                </span>
              )
            );
          })}
        </div>
      )}
      {series.length > 1 && (
        <figcaption className="lv-chart-legend">
          {series.map(({ name, color }) => (
            <span key={name}>
              <i style={{ background: color }} />
              {name}
            </span>
          ))}
        </figcaption>
      )}
    </figure>
  );
}
