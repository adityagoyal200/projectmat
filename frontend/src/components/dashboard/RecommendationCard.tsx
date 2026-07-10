import {
  Award,
  ChevronDown,
  Code2,
  Download,
  GitBranch,
  ListChecks,
  Loader2,
  Mail,
  Phone,
  Zap,
} from 'lucide-react';
import { useState, type ReactNode } from 'react';

import { ScoreCalculation } from '@/components/dashboard/ScoreCalculation';
import { downloadMatchReport } from '@/lib/api/report';
import { cn } from '@/lib/utils';
import type { MatchRecommendation, RepositoryEvaluationSummary } from '@/types/api';

interface RecommendationCardProps {
  rec: MatchRecommendation;
  variant: 'project' | 'candidate';
  /** Registration number for the report download (resolved by the parent). */
  reportRegistration?: string;
  /** Project id for the report download (resolved by the parent). */
  reportProjectId?: number;
}

/** Turns "Python←python(exact)" match notation into "Already has: … · Still needs: …". */
function humanizeSkills(detail?: string): string | null {
  if (!detail || !detail.trim()) return null;
  const strip = (s: string) => s.replace(/←[^,\]]+/g, '').replace(/\s{2,}/g, ' ').trim();
  const matched = /Matched:\s*\[([^\]]*)\]/i.exec(detail)?.[1]?.trim();
  const gaps = /Gaps:\s*\[([^\]]*)\]/i.exec(detail)?.[1]?.trim();
  if (matched === undefined && gaps === undefined) return strip(detail);
  const parts: string[] = [];
  if (matched && matched.toLowerCase() !== 'none') parts.push(`Already has: ${strip(matched)}`);
  else parts.push('None of the required skills matched yet.');
  if (gaps && gaps.toLowerCase() !== 'none') parts.push(`Still needs: ${strip(gaps)}`);
  return parts.join(' · ');
}

function humanizeDetail(detail?: string): string | null {
  if (!detail || !detail.trim()) return null;
  return detail.replace(/Score derived from/i, 'Based on').replace(/\s{2,}/g, ' ').trim();
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

export function RecommendationCard({
  rec,
  variant,
  reportRegistration,
  reportProjectId,
}: RecommendationCardProps) {
  const [expanded, setExpanded] = useState(rec.rank === 1);

  const title =
    variant === 'project'
      ? rec.project_title
      : `${rec.candidate_name} · ${rec.registration_number}`;

  const pct = (rec.final_score * 100).toFixed(1);
  const canDownload = Boolean(reportRegistration && reportProjectId);

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
              Expand for the factor breakdown, evidence, and downloadable report
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
          {canDownload && (
            <div className="flex justify-end">
              <ReportDownloadButton
                registration={reportRegistration!}
                projectId={reportProjectId!}
              />
            </div>
          )}

          <ScoreCalculation
            finalScore={rec.final_score}
            components={rec.score_components}
            breakdown={rec.score_breakdown}
          />

          <section>
            <div className="mb-3 flex items-center gap-2">
              <span className="h-px flex-1 bg-gradient-to-r from-violet-500/40 to-transparent" />
              <h5 className="text-xs font-semibold uppercase tracking-wider text-violet-300/80">
                What the data shows
              </h5>
              <span className="h-px flex-1 bg-gradient-to-l from-cyan-500/40 to-transparent" />
            </div>
            <div className="grid items-start gap-3 lg:grid-cols-3">
              <EvidenceCard
                icon={<ListChecks className="h-4 w-4" />}
                title="Skills that match"
                tint="violet"
                about="How many of the project's must-have skills we already found in this student's profile."
                headline={`${Math.round(rec.score_components.prerequisite_overlap * 100)}% of required skills found`}
                lines={[{ value: humanizeSkills(rec.score_breakdown.prerequisite_detail) }]}
              />
              <EvidenceCard
                icon={<Code2 className="h-4 w-4" />}
                title="Coding & projects"
                tint="cyan"
                about="Hands-on signals pulled from public code, live apps, and competitive-programming activity."
                lines={[
                  { label: 'Code & live apps', value: humanizeDetail(rec.score_breakdown.github_detail) },
                  { label: 'Competitive coding', value: humanizeDetail(rec.score_breakdown.coding_profiles_detail) },
                ]}
                repos={rec.score_breakdown.repository_evaluations}
              />
              <EvidenceCard
                icon={<Award className="h-4 w-4" />}
                title="Standout achievements"
                tint="amber"
                about="Awards, hackathon wins, publications, and citations detected in the student's profile."
                lines={[{ value: humanizeDetail(rec.score_breakdown.achievements_detail) }]}
                achievements={rec.achievements}
              />
            </div>
          </section>

          <section className="rounded-xl border border-primary/15 bg-primary/5 p-4">
            <p className="text-xs font-semibold text-primary/90">Summary</p>
            <p className="mt-2 text-sm leading-relaxed text-foreground/90">{rec.explanation}</p>
          </section>
        </div>
      ) : null}
    </article>
  );
}

function ReportDownloadButton({
  registration,
  projectId,
}: {
  registration: string;
  projectId: number;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handle = async () => {
    setLoading(true);
    setError(null);
    try {
      await downloadMatchReport(registration, projectId);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Report generation failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={handle}
        disabled={loading}
        className="inline-flex items-center gap-2 rounded-lg border border-violet-500/30 bg-violet-500/10 px-3 py-1.5 text-xs font-semibold text-violet-200 transition-colors hover:bg-violet-500/20 disabled:opacity-60"
      >
        {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
        {loading ? 'Generating report…' : 'Download fit report (PDF)'}
      </button>
      {error && <span className="max-w-[240px] text-right text-[10px] text-rose-400">{error}</span>}
    </div>
  );
}

const EVIDENCE_TINTS = {
  violet: 'border-violet-500/20 bg-violet-500/5 text-violet-300',
  cyan: 'border-cyan-500/20 bg-cyan-500/5 text-cyan-300',
  amber: 'border-amber-500/20 bg-amber-500/5 text-amber-300',
} as const;

/** A data-derived evidence card (Skills / Coding / Achievements). */
function EvidenceCard({
  icon,
  title,
  tint,
  about,
  headline,
  lines,
  repos,
  achievements,
}: {
  icon: ReactNode;
  title: string;
  tint: keyof typeof EVIDENCE_TINTS;
  about: string;
  headline?: string;
  lines: { label?: string; value: string | null }[];
  repos?: RepositoryEvaluationSummary[];
  achievements?: string[];
}) {
  const visibleLines = lines.filter((l) => l.value && l.value.trim());

  return (
    <div className={cn('flex h-full flex-col rounded-xl border overflow-hidden', EVIDENCE_TINTS[tint])}>
      <div className="flex items-center gap-2 px-4 pt-4 text-xs font-semibold">
        {icon}
        {title}
      </div>
      <div className="flex flex-1 flex-col gap-2 px-4 pb-4 pt-2">
        <p className="text-[11px] leading-snug text-muted-foreground/70">{about}</p>
        {headline && <p className="text-sm font-semibold text-foreground/90">{headline}</p>}
        {visibleLines.length > 0 ? (
          <div className="space-y-1.5">
            {visibleLines.map((line, i) => (
              <p key={i} className="text-xs leading-relaxed text-muted-foreground">
                {line.label && <span className="font-semibold text-foreground/70">{line.label}: </span>}
                {line.value}
              </p>
            ))}
          </div>
        ) : (
          !headline && achievements === undefined && (
            <p className="text-xs italic text-muted-foreground/60">Nothing detected for this student.</p>
          )
        )}
        {achievements !== undefined && (
          achievements.length > 0 ? (
            <ul className="space-y-1">
              {achievements.map((a, i) => (
                <li key={i} className="flex gap-1.5 text-xs leading-relaxed text-foreground/90">
                  <span className="mt-0.5 shrink-0 text-amber-400/80">•</span>
                  <span>{a}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs italic text-muted-foreground/60">No achievements detected for this student.</p>
          )
        )}
        {repos !== undefined && <RepoReviewList repos={repos} />}
      </div>
    </div>
  );
}

/** Per-repository review list shown inside the Coding & projects card. */
function RepoReviewList({ repos }: { repos: RepositoryEvaluationSummary[] }) {
  const successfulStatuses = new Set(['completed', 'success', 'evaluated']);
  return (
    <div className="mt-1 border-t border-white/[0.06] pt-2">
      <p className="mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
        <GitBranch className="h-3 w-3" />
        Repository review
      </p>
      {repos.length === 0 ? (
        <p className="text-[11px] italic leading-snug text-muted-foreground/60">
          No repositories were cloned or reviewed for this student yet.
        </p>
      ) : (
        <ul className="space-y-1.5">
          {repos.map((repo, i) => {
            const reviewed = successfulStatuses.has(repo.status.toLowerCase());
            const name =
              repo.repository_name ||
              repo.repository_url.replace(/^https?:\/\/github\.com\//i, '') ||
              'repository';
            return (
              <li key={i} className="text-[11px] leading-snug">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate font-medium text-foreground/80" title={repo.repository_url}>
                    {name}
                  </span>
                  <span
                    className={cn(
                      'shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide',
                      reviewed ? 'bg-emerald-500/10 text-emerald-300' : 'bg-amber-500/10 text-amber-300'
                    )}
                  >
                    {repo.status}
                  </span>
                </div>
                {reviewed && (
                  <div className="mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-muted-foreground/80">
                    <span>Quality {Math.round(repo.score * 100)}%</span>
                    {repo.logic_score != null && <span>Code review {Math.round(repo.logic_score * 100)}%</span>}
                    {repo.findings_count > 0 && (
                      <span>
                        {repo.findings_count} finding{repo.findings_count === 1 ? '' : 's'}
                      </span>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
