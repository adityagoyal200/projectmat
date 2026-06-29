import { Sparkles, Trophy } from 'lucide-react';

import { RecommendationCard } from '@/components/dashboard/RecommendationCard';
import type { MatchRecommendation } from '@/types/api';

interface MatchResultsListProps {
  results: MatchRecommendation[];
  variant: 'project' | 'candidate';
  emptyMessage: string;
  contextTitle?: string;
  contextSubtitle?: string;
}

export function MatchResultsList({
  results,
  variant,
  emptyMessage,
  contextTitle,
  contextSubtitle,
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

      <div className="glass-card flex items-center gap-3 px-4 py-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-amber-400/20 to-orange-500/20">
          <Trophy className="h-4 w-4 text-amber-400" />
        </div>
        <div>
          <span className="font-semibold text-foreground">
            {results.length} recommendation{results.length !== 1 ? 's' : ''}
          </span>
          <span className="ml-2 text-sm text-muted-foreground">ranked by hybrid match score</span>
        </div>
      </div>
      <div className="space-y-3">
        {results.map((rec) => (
          <RecommendationCard
            key={variant === 'project' ? rec.project_id : rec.candidate_id}
            rec={rec}
            variant={variant}
          />
        ))}
      </div>
    </div>
  );
}
