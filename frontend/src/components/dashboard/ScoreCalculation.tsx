import { AlertTriangle, Calculator, ChevronDown, Cpu, GitBranch, Info } from 'lucide-react';
import { Fragment, useState } from 'react';

import { Tooltip } from '@/components/ui/Tooltip';
import { cn } from '@/lib/utils';
import type { RepositoryEvaluationSummary, ScoreBreakdown, ScoreComponents } from '@/types/api';

const FACTOR_LABELS: Record<string, string> = {
  llm_fit: 'AI Fit Analysis',
  embedding_similarity: 'Topic Alignment',
  prerequisite_overlap: 'Required Skills Match',
  resume_experience: 'Relevant Experience',
  github: 'GitHub Profile',
  coding_profiles: 'Coding Profiles',
  achievements: 'Notable Achievements',
};

const FACTOR_EXPLANATIONS: Record<string, string> = {
  llm_fit: 'AI-evaluated match between the project abstract and candidate resume. Assesses readiness, growth potential, and interest.',
  embedding_similarity: "Semantic similarity comparing the project description against the candidate's overall profile.",
  prerequisite_overlap: "Share of the project's required skills that were found in the candidate's profile.",
  resume_experience: 'Depth of relevant experience, project mentions, and domain keywords in the resume.',
  github: 'Score derived from GitHub public repositories, stars, PRs, live apps, and recent activity.',
  coding_profiles: 'Competitive-programming activity and ratings (LeetCode, Codeforces, Kaggle).',
  achievements: 'Bonus for notable awards, hackathons, publications, and scholarships detected.',
};

const FACTOR_ORDER = [
  'llm_fit',
  'embedding_similarity',
  'prerequisite_overlap',
  'resume_experience',
  'github',
  'coding_profiles',
  'achievements',
] as const;

function pct(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

function pts(value: number): string {
  return (value * 100).toFixed(2);
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

interface ScoreCalculationProps {
  finalScore: number;
  components: ScoreComponents;
  breakdown: ScoreBreakdown;
}

export function ScoreCalculation({ finalScore, components, breakdown }: ScoreCalculationProps) {
  const [open, setOpen] = useState<Set<string>>(new Set());
  const toggle = (key: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const componentScores: Record<string, number> = {
    llm_fit: components.llm_fit_score,
    embedding_similarity: components.embedding_similarity,
    prerequisite_overlap: components.prerequisite_overlap,
    resume_experience: components.resume_experience,
    github: components.github_score,
    coding_profiles: components.coding_profiles_score,
    achievements: components.achievements_score,
  };

  const getDynamicDetail = (key: string) => {
    switch (key) {
      case 'github': return breakdown.github_detail;
      case 'coding_profiles': return breakdown.coding_profiles_detail;
      case 'achievements': return breakdown.achievements_detail;
      case 'llm_fit': return breakdown.llm_scoring_rationale;
      case 'embedding_similarity': return breakdown.embedding_detail;
      case 'prerequisite_overlap': return breakdown.prerequisite_detail;
      case 'resume_experience': return breakdown.resume_experience_detail;
      default: return undefined;
    }
  };

  const rows = FACTOR_ORDER.map((key) => ({
    key,
    label: FACTOR_LABELS[key] ?? key,
    explanation: FACTOR_EXPLANATIONS[key] ?? '',
    detail:
      key === 'prerequisite_overlap'
        ? humanizeSkills(getDynamicDetail(key))
        : humanizeDetail(getDynamicDetail(key)),
    weight: breakdown.weights[key] ?? 0,
    score: componentScores[key] ?? 0,
    contribution: breakdown.weighted_contributions[key] ?? 0,
  }));

  const contributionSum = rows.reduce((sum, row) => sum + row.contribution, 0);

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tooltip
          wrapperClassName="flex items-center gap-2 cursor-help"
          panelClassName="w-[400px] text-xs"
          content={
            <>
              <p className="mb-2">The final score is the sum of all factor contributions. Each contribution is the factor's score multiplied by its assigned weight.</p>
              {breakdown.formula && (
                <div className="mt-2 rounded bg-white/5 p-2 font-mono text-[10px] text-violet-200">
                  <span className="mb-1 block font-semibold text-muted-foreground uppercase tracking-wider text-[9px]">Formula</span>
                  {breakdown.formula}
                </div>
              )}
            </>
          }
        >
          <h5 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-violet-300/80">
            <Calculator className="h-4 w-4" />
            How this score was calculated
          </h5>
          <Info className="h-4 w-4 text-violet-300/60 transition-colors group-hover:text-violet-300/90" />
        </Tooltip>
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

      <p className="text-[11px] text-muted-foreground/70">
        Tap any factor row to expand its detailed evidence.
      </p>

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
            {rows.map((row) => {
              const isOpen = open.has(row.key);
              return (
                <Fragment key={row.key}>
                  <tr
                    onClick={() => toggle(row.key)}
                    className="cursor-pointer border-b border-white/[0.04] transition-colors hover:bg-white/[0.03]"
                  >
                    <td className="px-4 py-2.5 font-medium text-foreground/90">
                      <div className="flex items-center gap-1.5">
                        <ChevronDown
                          className={cn(
                            'h-3.5 w-3.5 shrink-0 text-muted-foreground/50 transition-transform duration-200',
                            isOpen && 'rotate-180 text-primary'
                          )}
                        />
                        <span>{row.label}</span>
                        <Tooltip
                          wrapperClassName="inline-flex cursor-help"
                          panelClassName="w-64 text-[11px]"
                          content={
                            <>
                              <p className="mb-1 font-semibold text-violet-200">{row.label}</p>
                              <p>{row.explanation}</p>
                              {row.score === 0 && (
                                <p className="mt-1.5 text-amber-300">
                                  This factor scored 0 — expand the row to see why.
                                </p>
                              )}
                            </>
                          }
                        >
                          <span
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex"
                          >
                            {row.score === 0 ? (
                              <AlertTriangle className="h-3.5 w-3.5 text-amber-500/80" />
                            ) : (
                              <Info className="h-3 w-3 text-muted-foreground/40 transition-colors hover:text-violet-300/90" />
                            )}
                          </span>
                        </Tooltip>
                      </div>
                    </td>
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
                  {isOpen && (
                    <tr className="border-b border-white/[0.04] bg-black/30">
                      <td colSpan={4} className="px-4 pb-3 pt-0">
                        <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                          <div className="mb-1 text-[9px] font-semibold uppercase tracking-wider text-violet-300/70">
                            What this measures
                          </div>
                          <p className="mb-2.5 text-[11px] leading-relaxed text-muted-foreground/80">
                            {row.explanation}
                          </p>
                          <div
                            className={cn(
                              'mb-1 text-[9px] font-semibold uppercase tracking-wider',
                              row.score === 0 ? 'text-amber-500/70' : 'text-cyan-300/70'
                            )}
                          >
                            {row.score === 0 ? 'Why is this 0?' : 'Detailed evidence'}
                          </div>
                          <p className="text-[11px] leading-relaxed text-foreground/80">
                            {row.detail || 'Data missing or insufficient for this metric.'}
                          </p>
                          {row.key === 'github' && breakdown.repository_evaluations !== undefined && (
                            <RepoReviewList repos={breakdown.repository_evaluations} />
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
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
    </section>
  );
}

/** Per-repository review list shown inside the GitHub factor dropdown. */
function RepoReviewList({ repos }: { repos: RepositoryEvaluationSummary[] }) {
  const successfulStatuses = new Set(['completed', 'success', 'evaluated']);
  return (
    <div className="mt-2.5 border-t border-white/[0.06] pt-2">
      <p className="mb-1.5 flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-wider text-muted-foreground/70">
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
            // Older evaluations stored the temp clone folder name ("checkout")
            // instead of the real repository name — prefer the URL in that case.
            const storedName =
              repo.repository_name && repo.repository_name !== 'checkout'
                ? repo.repository_name
                : '';
            const name =
              storedName ||
              repo.repository_url.replace(/^https?:\/\/github\.com\//i, '').replace(/\.git$/i, '') ||
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
