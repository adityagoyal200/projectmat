import { RefreshCw, Sparkles, Trophy } from 'lucide-react';

import { RecommendationCard } from '@/components/dashboard/RecommendationCard';
import type { MatchRecommendation } from '@/types/api';

interface MatchResultsListProps {
  results: MatchRecommendation[];
  variant: 'project' | 'candidate';
  emptyMessage: string;
  contextTitle?: string;
  contextSubtitle?: string;
  /** Student's registration number when the list is scoped to one student. */
  registrationNumber?: string;
  /** Project id when the list is scoped to one project. */
  projectId?: number;
  /** Whether these results were served from the saved cache. */
  cached?: boolean;
  /** Recompute (bypass cache); when provided, a Recompute button is shown. */
  onRecompute?: () => void;
  /** True while a recompute is in flight. */
  recomputing?: boolean;
}

export function MatchResultsList({
  results,
  variant,
  emptyMessage,
  contextTitle,
  contextSubtitle,
  registrationNumber,
  projectId,
  cached,
  onRecompute,
  recomputing,
}: MatchResultsListProps) {
  if (results.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 bg-gradient-to-b from-white/[0.03] to-transparent px-8 py-16 text-center">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500/20 to-cyan-500/20 ring-1 ring-white/10">
          <Sparkles className="h-7 w-7 text-violet-400" />
        </div>
        <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-fade-in">
      {(contextTitle || contextSubtitle) && (
        <div className="glass-card overflow-hidden">
          <div className="h-0.5 bg-gradient-to-r from-violet-500 to-cyan-400" />
          <div className="px-5 py-4">
            {contextTitle && <h3 className="text-base font-semibold text-foreground">{contextTitle}</h3>}
            {contextSubtitle && (
              <p className="mt-1 text-sm text-muted-foreground">{contextSubtitle}</p>
            )}
          </div>
        </div>
      )}

      <div className="glass-card flex flex-wrap items-center gap-3 px-4 py-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-amber-400/20 to-orange-500/20">
          <Trophy className="h-4 w-4 text-amber-400" />
        </div>
        <div>
          <span className="font-semibold text-foreground">
            {results.length} recommendation{results.length !== 1 ? 's' : ''}
          </span>
          <span className="ml-2 text-sm text-muted-foreground">ranked by hybrid match score</span>
        </div>
        <div className="ml-auto flex items-center gap-3">
          {cached && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              Saved result
            </span>
          )}
          {onRecompute && (
            <button
              type="button"
              onClick={onRecompute}
              disabled={recomputing}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-amber-300 disabled:opacity-40"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${recomputing ? 'animate-spin' : ''}`} />
              {recomputing ? 'Recomputing…' : 'Recompute'}
            </button>
          )}
        </div>
      </div>
      <div className="space-y-3">
        {results.map((rec) => (
          <RecommendationCard
            key={variant === 'project' ? rec.project_id : rec.candidate_id}
            rec={rec}
            variant={variant}
            reportRegistration={registrationNumber ?? rec.registration_number}
            reportProjectId={projectId ?? rec.project_id}
          />
        ))}
      </div>
    </div>
  );
}
