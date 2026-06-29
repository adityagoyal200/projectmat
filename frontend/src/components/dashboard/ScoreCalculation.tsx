import { Calculator, Cpu } from 'lucide-react';

import { cn } from '@/lib/utils';
import type { ScoreBreakdown, ScoreComponents } from '@/types/api';

const FACTOR_LABELS: Record<string, string> = {
  embedding_similarity: 'Embedding similarity',
  readiness: 'Readiness',
  growth_potential: 'Growth potential',
  interest: 'Interest alignment',
  prerequisite_overlap: 'Prerequisite overlap',
  resume_experience: 'Resume experience',
};

const FACTOR_ORDER = [
  'growth_potential',
  'readiness',
  'embedding_similarity',
  'prerequisite_overlap',
  'interest',
  'resume_experience',
] as const;

function pct(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

function pts(value: number): string {
  return (value * 100).toFixed(2);
}

interface ScoreCalculationProps {
  finalScore: number;
  components: ScoreComponents;
  breakdown: ScoreBreakdown;
}

export function ScoreCalculation({ finalScore, components, breakdown }: ScoreCalculationProps) {
  const componentScores: Record<string, number> = {
    embedding_similarity: components.embedding_similarity,
    readiness: components.readiness,
    growth_potential: components.growth_potential,
    interest: components.interest,
    prerequisite_overlap: components.prerequisite_overlap,
    resume_experience: components.resume_experience,
  };

  const rows = FACTOR_ORDER.map((key) => ({
    key,
    label: FACTOR_LABELS[key] ?? key,
    weight: breakdown.weights[key] ?? 0,
    score: componentScores[key] ?? 0,
    contribution: breakdown.weighted_contributions[key] ?? 0,
  }));

  const contributionSum = rows.reduce((sum, row) => sum + row.contribution, 0);

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h5 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-violet-300/80">
          <Calculator className="h-4 w-4" />
          How this score was calculated
        </h5>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            v{breakdown.scoring_version}
          </span>
          <span
            className={cn(
              'rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide',
              components.llm_evaluated
                ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-300'
                : 'border-amber-500/25 bg-amber-500/10 text-amber-300'
            )}
          >
            {components.llm_evaluated ? 'Full LLM eval' : 'Preliminary only'}
          </span>
          {(breakdown.llm_provider || breakdown.llm_model) && (
            <span className="inline-flex items-center gap-1 rounded-full border border-cyan-500/20 bg-cyan-500/10 px-2.5 py-1 text-[10px] font-medium text-cyan-300">
              <Cpu className="h-3 w-3" />
              {[breakdown.llm_provider, breakdown.llm_model].filter(Boolean).join(' · ')}
            </span>
          )}
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-white/[0.06] bg-black/25">
        <table className="w-full min-w-[520px] text-left text-xs">
          <thead>
            <tr className="border-b border-white/[0.06] text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              <th className="px-4 py-3">Factor</th>
              <th className="px-4 py-3 text-right">Weight</th>
              <th className="px-4 py-3 text-right">Component</th>
              <th className="px-4 py-3 text-right">Contribution</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} className="border-b border-white/[0.04] last:border-0">
                <td className="px-4 py-2.5 font-medium text-foreground/90">{row.label}</td>
                <td className="px-4 py-2.5 text-right tabular-nums text-muted-foreground">
                  {pct(row.weight)}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-foreground/80">
                  {pct(row.score)}
                </td>
                <td className="px-4 py-2.5 text-right font-semibold tabular-nums text-violet-300">
                  {pts(row.contribution)} pts
                </td>
              </tr>
            ))}
            <tr className="bg-violet-500/5">
              <td className="px-4 py-3 font-semibold text-foreground" colSpan={3}>
                Final score (sum of contributions)
              </td>
              <td className="px-4 py-3 text-right text-sm font-bold tabular-nums text-violet-200">
                {pts(finalScore)} / 100
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-[11px] leading-relaxed text-muted-foreground">
        Each contribution = weight × component score. Preference signal (
        {pct(components.preference_signal)}) is shown for context only and is{' '}
        <span className="font-medium text-foreground/80">not</span> included in the final score.
        {Math.abs(contributionSum - finalScore) > 0.001 && (
          <span className="ml-1 text-amber-300">
            (Rounded sum: {pts(contributionSum)} pts)
          </span>
        )}
      </p>

      <div className="rounded-xl border border-white/[0.06] bg-black/20 p-4">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Formula (machine-readable)
        </p>
        <p className="mt-2 font-mono text-[11px] leading-relaxed text-foreground/85">
          {breakdown.formula}
        </p>
      </div>
    </section>
  );
}
