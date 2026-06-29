import { useMemo, useState } from 'react';
import { Star, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { BatchScoreMatrixResponse, BatchProjectSummary, PairScore } from '@/types/api';

// ── helpers ────────────────────────────────────────────────────────────────

function band(v: number) {
  if (v >= 0.6) return 'strong';
  if (v >= 0.4) return 'moderate';
  return 'weak';
}

const BAND_STYLES = {
  strong:   { badge: 'bg-emerald-500/20 text-emerald-200 border-emerald-500/25',  bar: 'from-emerald-500 to-emerald-400', dot: 'bg-emerald-400' },
  moderate: { badge: 'bg-amber-500/20   text-amber-200   border-amber-500/25',    bar: 'from-amber-500   to-amber-400',   dot: 'bg-amber-400' },
  weak:     { badge: 'bg-rose-500/15    text-rose-200    border-rose-500/20',      bar: 'from-rose-500    to-rose-400',    dot: 'bg-rose-400' },
};

function pct(v: number) { return `${(v * 100).toFixed(0)}`; }

const SUB_SCORES: { key: keyof PairScore; label: string }[] = [
  { key: 'embedding_similarity',  label: 'Embed' },
  { key: 'prerequisite_overlap',  label: 'Prereq' },
  { key: 'resume_experience',     label: 'Resume' },
  { key: 'preference_signal',     label: 'Pref' },
];

interface ProjectRowProps {
  project: BatchProjectSummary;
  score: PairScore;
  isBest: boolean;
  rank: number;
}

function ProjectRow({ project, score, isBest, rank }: ProjectRowProps) {
  const b = band(score.preliminary_score);
  const s = BAND_STYLES[b];

  return (
    <div className={cn(
      'rounded-xl p-3 transition-all duration-200',
      isBest
        ? 'bg-gradient-to-br from-white/[0.06] to-white/[0.02] border border-white/[0.1]'
        : 'bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04]'
    )}>
      {/* Project name + composite score */}
      <div className="flex items-center gap-2 mb-2">
        {/* rank badge */}
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/[0.07] text-[10px] font-bold text-muted-foreground">
          {rank}
        </span>
        {isBest && <Star className="h-3 w-3 shrink-0 text-amber-400 fill-amber-400" />}
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-semibold text-foreground leading-tight">{project.project_title}</p>
          <p className="text-[10px] text-muted-foreground truncate">{project.mentor_name}</p>
        </div>
        {/* Composite score — always prominent */}
        <span className={cn(
          'inline-flex items-center gap-1 rounded-lg border px-2 py-1 text-sm font-bold tabular-nums shrink-0',
          s.badge
        )}>
          <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', s.dot)} />
          {pct(score.preliminary_score)}
        </span>
      </div>

      {/* Composite progress bar */}
      <div className="mb-2.5 h-1.5 w-full rounded-full bg-white/[0.05] overflow-hidden">
        <div
          className={cn('h-full rounded-full bg-gradient-to-r transition-all duration-700', s.bar)}
          style={{ width: `${score.preliminary_score * 100}%` }}
        />
      </div>

      {/* Sub-score breakdown — always visible, all 4 at once */}
      <div className="grid grid-cols-4 gap-1.5">
        {SUB_SCORES.map(({ key, label }) => {
          const val = score[key] as number;
          const sb = band(val);
          const ss = BAND_STYLES[sb];
          return (
            <div key={key} className="flex flex-col items-center gap-0.5">
              <div className="h-1 w-full rounded-full bg-white/[0.05] overflow-hidden">
                <div
                  className={cn('h-full rounded-full bg-gradient-to-r', ss.bar)}
                  style={{ width: `${val * 100}%` }}
                />
              </div>
              <div className="flex items-center justify-between w-full px-0.5">
                <span className="text-[9px] text-muted-foreground/60">{label}</span>
                <span className={cn('text-[9px] font-bold tabular-nums', ss.badge.split(' ')[1])}>
                  {pct(val)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── StudentCard ────────────────────────────────────────────────────────────

interface StudentCardProps {
  name: string;
  regNumber: string;
  projectScores: Array<{ project: BatchProjectSummary; score: PairScore }>;
  showTopN?: number;
}

function StudentCard({ name, regNumber, projectScores, showTopN = 3 }: StudentCardProps) {
  const [expanded, setExpanded] = useState(false);

  // Always sort by composite score descending
  const sorted = useMemo(
    () => [...projectScores].sort((a, b) => b.score.preliminary_score - a.score.preliminary_score),
    [projectScores]
  );

  const visible = expanded ? sorted : sorted.slice(0, showTopN);
  const hidden = sorted.length - showTopN;
  const best = sorted[0]?.score.preliminary_score ?? 0;
  const avg = sorted.length
    ? sorted.reduce((s, x) => s + x.score.preliminary_score, 0) / sorted.length
    : 0;
  const bst = BAND_STYLES[band(best)];

  return (
    <div className={cn(
      'group relative rounded-2xl border bg-gradient-to-b from-white/[0.04] to-transparent',
      'transition-all duration-200 overflow-hidden flex flex-col',
      'border-white/[0.07] hover:border-white/[0.12]'
    )}>
      {/* Accent top bar — colour driven by best composite score */}
      <div className={cn('h-0.5 w-full bg-gradient-to-r', bst.bar)} />

      {/* Student header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-white/[0.05]">
        {/* Initials avatar */}
        <div className={cn(
          'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-xs font-bold select-none',
          'bg-gradient-to-br from-white/[0.08] to-transparent border border-white/[0.08] text-foreground/70'
        )}>
          {name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold text-foreground leading-tight">{name}</p>
          <p className="text-[11px] text-muted-foreground">{regNumber}</p>
        </div>
        {/* Best + avg chip */}
        <div className="shrink-0 text-right">
          <span className={cn('text-lg font-black tabular-nums', bst.badge.split(' ')[1])}>
            {pct(best)}
          </span>
          <p className="text-[10px] text-muted-foreground">best · avg {pct(avg)}</p>
        </div>
      </div>

      {/* Project rows */}
      <div className="flex-1 p-3 space-y-2">
        {visible.map(({ project, score }, idx) => (
          <ProjectRow
            key={project.project_id}
            project={project}
            score={score}
            isBest={idx === 0}
            rank={idx + 1}
          />
        ))}
      </div>

      {/* Expand toggle */}
      {hidden > 0 && (
        <button
          type="button"
          onClick={() => setExpanded(p => !p)}
          className={cn(
            'flex items-center justify-center gap-1.5 py-2.5 text-[11px] text-muted-foreground',
            'hover:text-foreground transition-colors border-t border-white/[0.05] hover:bg-white/[0.02]'
          )}
        >
          {expanded ? (
            <><ChevronUp className="h-3 w-3" />Show fewer</>
          ) : (
            <><ChevronDown className="h-3 w-3" />+{hidden} more projects</>
          )}
        </button>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

type SortMode = 'best' | 'avg' | 'az';

const SORT_OPTIONS: { key: SortMode; label: string }[] = [
  { key: 'best', label: '★ Best score' },
  { key: 'avg',  label: '⌀ Avg score' },
  { key: 'az',   label: 'A → Z' },
];

interface Props {
  data: BatchScoreMatrixResponse;
}

export function BatchScoreMatrix({ data }: Props) {
  const [sortBy, setSortBy] = useState<SortMode>('best');

  const projectMap = useMemo(
    () => new Map(data.projects.map(p => [p.project_id, p])),
    [data.projects]
  );

  const studentRows = useMemo(() => {
    return data.students.map(student => {
      const pairs = data.scores
        .filter(s => s.candidate_id === student.candidate_id)
        .map(s => ({ project: projectMap.get(s.project_id)!, score: s }))
        .filter(x => !!x.project);

      const best = pairs.length ? Math.max(...pairs.map(x => x.score.preliminary_score)) : 0;
      const avg  = pairs.length ? pairs.reduce((s, x) => s + x.score.preliminary_score, 0) / pairs.length : 0;
      return { student, pairs, best, avg };
    });
  }, [data, projectMap]);

  const sorted = useMemo(() => {
    const arr = [...studentRows];
    if (sortBy === 'best') arr.sort((a, b) => b.best - a.best);
    else if (sortBy === 'avg') arr.sort((a, b) => b.avg - a.avg);
    else arr.sort((a, b) => a.student.candidate_name.localeCompare(b.student.candidate_name));
    return arr;
  }, [studentRows, sortBy]);

  if (data.students.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-muted-foreground">
        No students or projects found in this batch.
      </p>
    );
  }

  return (
    <div className="space-y-5">

      {/* ── Controls ── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Legend */}
        <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
          <span className="font-semibold text-foreground/70 text-[11px] uppercase tracking-wider">Composite score</span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />≥ 60 strong
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-amber-400" />40–59 moderate
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-rose-400" />&lt; 40 weak
          </span>
        </div>

        {/* Sort pills */}
        <div className="flex items-center gap-1 rounded-xl border border-white/[0.07] bg-white/[0.02] p-1">
          {SORT_OPTIONS.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => setSortBy(key)}
              className={cn(
                'rounded-lg px-3 py-1 text-xs font-medium transition-all',
                sortBy === key
                  ? 'bg-white/[0.1] text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Sub-score key ── */}
      <div className="flex flex-wrap items-center gap-4 rounded-xl border border-white/[0.05] bg-white/[0.02] px-4 py-2.5">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/60">Sub-scores shown per card:</span>
        {SUB_SCORES.map(({ key, label }) => (
          <span key={key} className="text-xs text-muted-foreground">
            <span className="font-semibold text-foreground/70">{label}</span>
            {' '}= {key.replace(/_/g, ' ')}
          </span>
        ))}
      </div>

      {/* ── Stats ── */}
      <div className="flex gap-4 text-xs text-muted-foreground">
        <span><span className="font-semibold text-foreground">{data.students.length}</span> students</span>
        <span><span className="font-semibold text-foreground">{data.projects.length}</span> projects</span>
        <span><span className="font-semibold text-foreground">{data.scores.length}</span> pairs computed</span>
      </div>

      {/* ── Student grid ── */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {sorted.map(({ student, pairs }) => (
          <StudentCard
            key={student.candidate_id}
            name={student.candidate_name}
            regNumber={student.registration_number}
            projectScores={pairs}
            showTopN={3}
          />
        ))}
      </div>
    </div>
  );
}
