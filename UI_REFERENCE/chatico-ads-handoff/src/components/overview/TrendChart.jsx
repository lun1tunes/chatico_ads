import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

function LegendDot({ color, label }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="h-2 w-2 rounded-[2px]" style={{ backgroundColor: color }} />
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

/** График динамики в стиле shadcn/ui card (CardHeader + CardAction-легенда). */
export default function TrendChart({ data, loading }) {
  if (loading) {
    return (
      <div className="flex h-80 items-center justify-center rounded-xl border border-outline bg-white p-6 shadow-sm">
        <p className="text-sm text-muted-foreground">Загрузка графика…</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-outline bg-white shadow-sm">
      <div className="flex flex-col gap-3 border-b border-outline px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-on-surface">
            Расходы и обращения по дням
          </h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Динамика за выбранный период
          </p>
        </div>
        <div className="flex items-center gap-4">
          <LegendDot color="#5E44EB" label="Расход (₸)" />
          <LegendDot color="#8BC53F" label="Контакты" />
        </div>
      </div>

      <div className="h-72 w-full p-4">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorSpent" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#5E44EB" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#5E44EB" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorLeads" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8BC53F" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#8BC53F" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#F4F4F5" vertical={false} />
            <XAxis dataKey="date" stroke="#A1A1AA" fontSize={11} tickLine={false} axisLine={false} />
            <YAxis stroke="#A1A1AA" fontSize={11} tickLine={false} axisLine={false} />
            <Tooltip
              cursor={{ stroke: '#E4E4E7', strokeWidth: 1 }}
              contentStyle={{
                backgroundColor: '#FFFFFF',
                borderRadius: '8px',
                border: '1px solid #E4E4E7',
                boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                fontFamily: 'Montserrat, sans-serif',
                fontSize: '12px',
              }}
            />
            <Area type="monotone" dataKey="spent" name="Расход (₸)" stroke="#5E44EB" strokeWidth={2} fillOpacity={1} fill="url(#colorSpent)" />
            <Area type="monotone" dataKey="leads" name="Контакты" stroke="#8BC53F" strokeWidth={2} fillOpacity={1} fill="url(#colorLeads)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
