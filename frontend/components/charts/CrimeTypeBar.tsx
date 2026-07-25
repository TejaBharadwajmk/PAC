"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

interface CrimeTypeBarProps {
  data: Array<{ type: string; count: number }>;
}

const COLOURS = [
  "#58a6ff", "#bc8cff", "#e98d30", "#f85149", "#3fb950", "#d29922",
];

export function CrimeTypeBar({ data }: CrimeTypeBarProps) {
  return (
    <div className="w-full h-48">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <XAxis
            dataKey="type"
            tick={{ fill: "#8b949e", fontSize: 11 }}
            axisLine={{ stroke: "#30363d" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#8b949e", fontSize: 11 }}
            axisLine={{ stroke: "#30363d" }}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: "#21262d",
              border: "1px solid #30363d",
              borderRadius: "6px",
              color: "#e6edf3",
              fontSize: "12px",
            }}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLOURS[index % COLOURS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
