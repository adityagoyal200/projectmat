import { ChevronDown, Mail, Phone, Sprout, Target, User, Zap } from 'lucide-react';
import { useState, type ReactNode } from 'react';

import { ScoreBar } from '@/components/dashboard/ScoreBar';
import { ScoreCalculation } from '@/components/dashboard/ScoreCalculation';import { cn } from '@/lib/utils';
import type { MatchRecommendation } from '@/types/api';

interface RecommendationCardProps {
  rec: MatchRecommendation;
  variant: 'project' | 'candidate';
}

function scoreRingClass(score: number): string {
  if (score >= 0.75) return 'from-emerald-400 to-teal-400 text-emerald-300';
  if (score >= 0.5) return 'from-amber-400 to-orange-400 text-amber-300';
  return 'from-rose-400 to-pink-400 text-rose-300';
}

function rankBadgeClass(rank: number | undefined): string {
  if (rank === 1) return 'bg-gradient-to-br from-amber-400 to-orange-500 text-white shadow-lg shadow-amber-500/30';
  if (rank === 2) return 'bg-gradient-to-br from-slate-300 to-slate-400 text-slate-900';
  if (rank === 3) return 'bg-gradient-to-br from-amber-700 to-amber-800 text-amber-100';
  return 'bg-gradient-to-br from-violet-500/20 to-cyan-500/20 text-violet-300 ring-1 ring-white/10';
}

export function RecommendationCard({ rec, variant }: RecommendationCardProps) {
  const [expanded, setExpanded] = useState(rec.rank === 1);

  const title =
    variant === 'project'
      ? rec.project_title
      : `${rec.candidate_name} · ${rec.registration_number}`;


  const pct = (rec.final_score * 100).toFixed(1);

  return (
    <article
      className={cn(
        'glass-card-hover overflow-hidden animate-fade-in',
        rec.rank === 1 && 'ring-1 ring-amber-500/20'
      )}
    >
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-start gap-4 p-5 text-left"
      >
        <div
          className={cn(
            'flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-sm font-bold',
            rankBadgeClass(rec.rank)
          )}
        >
          {rec.rank}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <h4 className="text-base font-semibold leading-snug text-foreground">{title}</h4>
              {variant === 'project' && (rec.mentor_name || rec.mentor_email) ? (
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <p className="text-xs text-cyan-400/80">Mentor · {rec.mentor_name ?? 'Unknown'}</p>
                  {rec.mentor_email && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-cyan-500/20 bg-cyan-500/10 px-2 py-0.5 text-[10px] text-cyan-300/80">
                      <Mail className="h-2.5 w-2.5" />
                      {rec.mentor_email}
                    </span>
                  )}
                  {rec.mentor_phone && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-violet-500/20 bg-violet-500/10 px-2 py-0.5 text-[10px] text-violet-300/80">
                      <Phone className="h-2.5 w-2.5" />
                      {rec.mentor_phone}
                    </span>
                  )}
                </div>
              ) : null}
              {!rec.score_components.llm_evaluated && (
                <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/20 bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-300">
                  <Zap className="h-3 w-3" />
                  Preliminary rank
                </span>
              )}
            </div>

            <div
              className={cn(
                'flex flex-col items-center rounded-2xl bg-gradient-to-br p-[2px]',
                scoreRingClass(rec.final_score)
              )}
            >
              <div className="flex min-w-[4.5rem] flex-col items-center rounded-[14px] bg-card/90 px-3 py-2">
                <span className="text-2xl font-bold tabular-nums leading-none">{pct}</span>
                <span className="mt-0.5 text-[9px] font-semibold uppercase tracking-widest opacity-70">
                  match
                </span>
              </div>
            </div>
          </div>

          <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-muted-foreground">
            {rec.explanation}
          </p>
          {!expanded && (
            <p className="mt-2 text-[11px] text-violet-400/70">
              Expand for full score calculation, weights, and LLM rationale
            </p>
          )}
        </div>

        <ChevronDown
          className={cn(
            'mt-2 h-5 w-5 shrink-0 text-muted-foreground/60 transition-transform duration-200',
            expanded && 'rotate-180 text-primary'
          )}
        />
      </button>

      {expanded ? (
        <div className="space-y-5 border-t border-white/[0.06] bg-gradient-to-b from-white/[0.02] to-transparent px-5 py-5">
          <ScoreCalculation
            finalScore={rec.final_score}
            components={rec.score_components}
            breakdown={rec.score_breakdown}
          />

          <section>            <h5 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-violet-300/80">
              <span className="h-px flex-1 bg-gradient-to-r from-violet-500/40 to-transparent" />
              Score breakdown
              <span className="h-px flex-1 bg-gradient-to-l from-cyan-500/40 to-transparent" />
            </h5>
            <div className="grid gap-2 sm:grid-cols-2">
              <ScoreBar label="Growth potential" value={rec.score_components.growth_potential} accent="emerald" />
              <ScoreBar label="Embedding similarity" value={rec.score_components.embedding_similarity} accent="cyan" />
              <ScoreBar label="Readiness" value={rec.score_components.readiness} accent="violet" />
              <ScoreBar label="Interest" value={rec.score_components.interest} accent="amber" />
              <ScoreBar label="Prerequisite overlap" value={rec.score_components.prerequisite_overlap} accent="default" />
              <ScoreBar label="Resume experience" value={rec.score_components.resume_experience} accent="cyan" />
              <ScoreBar label="Stage 1 preliminary" value={rec.score_components.preliminary_score} hint="Before LLM deep-eval" />
              <ScoreBar label="Preference signal" value={rec.score_components.preference_signal} hint="Info only" muted accent="rose" />
            </div>
          </section>

          <section className="grid gap-3 lg:grid-cols-3">            <DetailBlock icon={<User className="h-4 w-4" />} title="Technical readiness" body={rec.technical_readiness} tint="violet" />
            <DetailBlock icon={<Sprout className="h-4 w-4" />} title="Growth potential" body={rec.growth_potential} tint="emerald" />
            <DetailBlock icon={<Target className="h-4 w-4" />} title="Interest alignment" body={rec.interest_alignment} tint="cyan" />
          </section>

          <section className="rounded-xl border border-primary/15 bg-primary/5 p-4">
            <p className="text-xs font-semibold text-primary/90">Summary</p>
            <p className="mt-2 text-sm leading-relaxed text-foreground/90">{rec.explanation}</p>
          </section>

          <section className="space-y-3 rounded-xl border border-white/[0.05] bg-white/[0.02] p-4 text-xs leading-relaxed text-muted-foreground">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Detailed signals
            </p>
            <DetailRow label="Embedding" value={rec.score_breakdown.embedding_detail} />
            <DetailRow label="Prerequisites" value={rec.score_breakdown.prerequisite_detail} />
            <DetailRow label="Resume" value={rec.score_breakdown.resume_experience_detail} />
            <DetailRow label="Preference (excluded)" value={rec.score_breakdown.preference_detail} />
            <DetailRow label="LLM rationale" value={rec.score_breakdown.llm_scoring_rationale} />
          </section>        </div>
      ) : null}
    </article>
  );
}

function DetailBlock({
  icon,
  title,
  body,
  tint,
}: {
  icon: ReactNode;
  title: string;
  body: string;
  tint: 'violet' | 'emerald' | 'cyan';
}) {
  const tints = {
    violet: 'border-violet-500/20 bg-violet-500/5 text-violet-300',
    emerald: 'border-emerald-500/20 bg-emerald-500/5 text-emerald-300',
    cyan: 'border-cyan-500/20 bg-cyan-500/5 text-cyan-300',
  };

  return (
    <div className={cn('rounded-xl border p-4', tints[tint])}>
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold">
        {icon}
        {title}
      </div>
      <p className="text-xs leading-relaxed text-muted-foreground">{body}</p>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <p>
      <span className="font-semibold text-foreground/80">{label}: </span>
      {value}
    </p>
  );
}
