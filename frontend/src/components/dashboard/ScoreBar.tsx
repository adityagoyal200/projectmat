import { cn } from '@/lib/utils';

interface ScoreBarProps {
  label: string;
  value: number;
  hint?: string;
  muted?: boolean;
  accent?: 'violet' | 'cyan' | 'emerald' | 'amber' | 'rose' | 'default';
}

const ACCENT_GRADIENTS: Record<string, string> = {
  violet: 'from-violet-500 to-fuchsia-500',
  cyan: 'from-cyan-400 to-blue-500',
  emerald: 'from-emerald-400 to-teal-500',
  amber: 'from-amber-400 to-orange-500',
  rose: 'from-rose-400 to-pink-500',
  default: 'from-violet-500 to-cyan-400',
};

export function ScoreBar({ label, value, hint, muted, accent = 'default' }: ScoreBarProps) {
  const pct = Math.round(value * 100);
  const gradient = ACCENT_GRADIENTS[accent] ?? ACCENT_GRADIENTS.default;

  return (
    <div
      className={cn(
        'rounded-xl border border-white/[0.05] bg-white/[0.02] p-3',
        muted && 'opacity-65'
      )}
    >
      <div className="mb-2 flex items-center justify-between text-xs">
        <span className="font-medium text-muted-foreground">{label}</span>
        <span className="font-semibold tabular-nums text-foreground">{pct}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-secondary/80">
        <div
          className={cn(
            'h-full rounded-full bg-gradient-to-r transition-all duration-500 ease-out',
            muted ? 'from-muted-foreground/30 to-muted-foreground/20' : gradient
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      {hint ? <p className="mt-1.5 text-[10px] leading-snug text-muted-foreground/80">{hint}</p> : null}
    </div>
  );
}
