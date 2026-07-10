import { useState, useEffect, type ComponentType, type ReactNode } from 'react';
import {
  Activity,
  Brain,
  FileDown,
  FileSpreadsheet,
  FileText,
  FolderKanban,
  GraduationCap,
  LayoutGrid,
  Mail,
  Phone,
  Sparkles,
  Upload,
  User,
  Users,
  Zap,
} from 'lucide-react';

import { BatchScoreMatrix } from '@/components/dashboard/BatchScoreMatrix';
import { MatchResultsList } from '@/components/dashboard/MatchResultsList';
import { Button } from '@/components/ui/button';
import { CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import client from '@/lib/api/client';
import { downloadBatchReport } from '@/lib/api/report';
import { streamMatchEvents } from '@/lib/api/stream';
import { cn } from '@/lib/utils';
import type {
  BatchScoreMatrixResponse,
  Candidate,
  HealthDetails,
  ImportBatchListItem,
  ImportBatchResponse,
  LlmPreviewResult,
  MatchRecommendation,
  Mentor,
  Project,
  ProjectRecommendationsResponse,
  StudentRecommendationsResponse,
} from '@/types/api';

type Tab = 'import' | 'match' | 'mentor' | 'batches' | 'llm' | 'dummy_projects';
type MatchMode = 'student' | 'project' | 'resume';

function StatusPill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium backdrop-blur-sm',
        ok
          ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-300'
          : 'border-rose-500/25 bg-rose-500/10 text-rose-300'
      )}
    >
      <span
        className={cn(
          'h-1.5 w-1.5 rounded-full shadow-sm',
          ok ? 'bg-emerald-400 shadow-emerald-400/50' : 'bg-rose-400 shadow-rose-400/50'
        )}
      />
      {label}
    </span>
  );
}

function TabButton({
  active,
  onClick,
  icon: Icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: ComponentType<{ className?: string }>;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'inline-flex flex-1 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all duration-200 sm:flex-none',
        active
          ? 'tab-pill-active text-white'
          : 'text-muted-foreground hover:bg-white/[0.04] hover:text-foreground'
      )}
    >
      <Icon className="h-4 w-4" />
      {children}
    </button>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/[0.06] bg-white/[0.03] p-3">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-1 font-semibold text-foreground">{value}</p>
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('match');
  const [matchMode, setMatchMode] = useState<MatchMode>('student');

  const [health, setHealth] = useState<HealthDetails | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);

  const [listsLoading, setListsLoading] = useState(false);
  const [listsError, setListsError] = useState<string | null>(null);
  const [listsLastLoadedAt, setListsLastLoadedAt] = useState<number | null>(null);

  const [workbookFile, setWorkbookFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [batchInfo, setBatchInfo] = useState<ImportBatchResponse | null>(null);
  const [selectedBatchDetails, setSelectedBatchDetails] = useState<ImportBatchResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [driveUrl, setDriveUrl] = useState('');
  const [importingDrive, setImportingDrive] = useState(false);
  const [driveError, setDriveError] = useState<string | null>(null);
  const [driveSuccessInfo, setDriveSuccessInfo] = useState<{
    id: number;
    status: string;
    candidateCount: number;
  } | null>(null);

  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [mentors, setMentors] = useState<Mentor[]>([]);

  // ── Match tab ─────────────────────────────────────────────────────────────
  const [selectedCandidateReg, setSelectedCandidateReg] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [candidateRecommendations, setCandidateRecommendations] = useState<MatchRecommendation[]>([]);
  const [studentMatchContext, setStudentMatchContext] = useState<{ candidateName: string; registrationNumber: string; cached: boolean } | null>(null);
  const [projectRecommendations, setProjectRecommendations] = useState<MatchRecommendation[]>([]);
  const [projectMatchContext, setProjectMatchContext] = useState<{ projectTitle: string; projectId: number; cached: boolean } | null>(null);
  const [matchingLoading, setMatchingLoading] = useState(false);
  const [matchError, setMatchError] = useState<string | null>(null);

  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [preferredTopics, setPreferredTopics] = useState('');
  const [githubUrl, setGithubUrl] = useState('');
  const [leetcodeUrl, setLeetcodeUrl] = useState('');
  const [codeforcesUrl, setCodeforcesUrl] = useState('');
  const [kaggleUrl, setKaggleUrl] = useState('');
  const [scholarUrl, setScholarUrl] = useState('');
  const [liveAppUrl, setLiveAppUrl] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [resumeRecs, setResumeRecs] = useState<MatchRecommendation[]>([]);
  const [resumeMatchContext, setResumeMatchContext] = useState<{ candidateName: string; registrationNumber: string } | null>(null);
  const [resumeLoading, setResumeLoading] = useState(false);

  // ── Mentor tab ────────────────────────────────────────────────────────────
  const [selectedMentorId, setSelectedMentorId] = useState('');
  const [mentorMatchResults, setMentorMatchResults] = useState<MatchRecommendation[]>([]);
  const [mentorMatchContext, setMentorMatchContext] = useState<{ projectTitle: string; projectId: number; cached: boolean } | null>(null);
  const [mentorMatchLoading, setMentorMatchLoading] = useState(false);
  const [mentorMatchError, setMentorMatchError] = useState<string | null>(null);

  // ── Batches tab ───────────────────────────────────────────────────────────
  const [importBatches, setImportBatches] = useState<ImportBatchListItem[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState('');
  const [batchMatrix, setBatchMatrix] = useState<BatchScoreMatrixResponse | null>(null);
  const [batchScoreLoading, setBatchScoreLoading] = useState(false);
  const [batchScoreError, setBatchScoreError] = useState<string | null>(null);
  const [batchReportLoading, setBatchReportLoading] = useState(false);
  const [batchReportError, setBatchReportError] = useState<string | null>(null);

  // ── LLM tab ───────────────────────────────────────────────────────────────
  const [previewPrompt, setPreviewPrompt] = useState(
    'Say hello and confirm you can help match students to research projects.'
  );
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewResult, setPreviewResult] = useState<LlmPreviewResult | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  // ── Dummy Projects tab ───────────────────────────────────────────────────
  const [dummyProjects, setDummyProjects] = useState<Project[]>([]);
  const [dummyProjectsLoading, setDummyProjectsLoading] = useState(false);
  const [newDummyTitle, setNewDummyTitle] = useState('');
  const [newDummyAbstract, setNewDummyAbstract] = useState('');
  const [newDummyMentorName, setNewDummyMentorName] = useState('');
  const [newDummyMentorEmail, setNewDummyMentorEmail] = useState('');
  const [newDummyPrereqs, setNewDummyPrereqs] = useState('');
  const [dummyProjectSaving, setDummyProjectSaving] = useState(false);
  const [dummyProjectError, setDummyProjectError] = useState<string | null>(null);
  const [editingDummyId, setEditingDummyId] = useState<number | null>(null);

  const [studentSourceFilter, setStudentSourceFilter] = useState<'all' | 'excel' | 'drive'>('all');

  const refreshDummyProjects = async () => {
    setDummyProjectsLoading(true);
    try {
      const res = await client.get<Project[]>('/projects?dummy_only=true');
      setDummyProjects(res.data);
    } catch (e) {
      console.error('Failed to load dummy projects', e);
    } finally {
      setDummyProjectsLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'dummy_projects') {
      void refreshDummyProjects();
    }
  }, [activeTab]);

  // ── Data fetching ─────────────────────────────────────────────────────────
  const refreshLists = async () => {
    setListsLoading(true);
    setListsError(null);
    try {
      const [candRes, projRes, mentorRes, batchRes] = await Promise.all([
        client.get<Candidate[]>('/candidates?all=true'),
        client.get<Project[]>('/projects'),
        client.get<Mentor[]>('/mentors'),
        client.get<ImportBatchListItem[]>('/import-batches'),
      ]);
      setCandidates(candRes.data);
      setProjects(projRes.data);
      setMentors(mentorRes.data);
      setImportBatches(batchRes.data);
      setListsLastLoadedAt(Date.now());
    } catch (e) {
      setListsError(e instanceof Error ? e.message : 'Failed to fetch lists');
    } finally {
      setListsLoading(false);
    }
  };

  const checkHealth = async () => {
    setHealthLoading(true);
    try {
      const res = await client.get<HealthDetails>('/health');
      setHealth(res.data);
      return res.data;
    } catch (e: unknown) {
      const err = { error: e instanceof Error ? e.message : 'Connection failed' } satisfies HealthDetails;
      setHealth(err);
      return null;
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

    const bootstrap = async () => {
      for (let attempt = 0; attempt < 5; attempt += 1) {
        const healthResult = await checkHealth();
        if (cancelled) return;
        const apiReady = healthResult?.status === 'ok';
        const dbReady = healthResult?.database === 'connected';
        if (apiReady && dbReady) break;
        await sleep(600 + attempt * 600);
        if (cancelled) return;
      }
      await refreshLists();
    };

    bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const hasParsing = importBatches.some((b) => b.status === 'parsing');
    if (!hasParsing) return;

    const interval = setInterval(() => {
      void refreshLists();
    }, 3000);

    return () => clearInterval(interval);
  }, [importBatches]);

  useEffect(() => {
    if (activeTab !== 'batches') return;
    const stale = listsLastLoadedAt == null || Date.now() - listsLastLoadedAt > 15_000;
    if (!stale) return;
    void refreshLists();
  }, [activeTab, listsLastLoadedAt]);

  // ── Actions ───────────────────────────────────────────────────────────────
  const handleWorkbookUpload = async () => {
    if (!workbookFile) return;
    setUploading(true);
    setUploadError(null);
    setBatchInfo(null);
    try {
      const batchRes = await client.post('/import-batches');
      const formData = new FormData();
      formData.append('file', workbookFile);
      formData.append('file_type', 'workbook');
      const uploadRes = await client.post(`/import-batches/${batchRes.data.id}/files`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setBatchInfo(uploadRes.data);
      setSelectedBatchDetails(uploadRes.data);
      setSelectedBatchId(String(uploadRes.data.id));
      await refreshLists();
      setActiveTab('import');
    } catch (e: unknown) {
      setUploadError(e instanceof Error ? e.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDriveImport = async () => {
    if (!driveUrl) return;
    setImportingDrive(true);
    setDriveError(null);
    setDriveSuccessInfo(null);
    try {
      const res = await client.post('/import-batches/drive-resumes', { resumes_url: driveUrl });
      const batchId = res.data.id;
      setDriveSuccessInfo({ id: batchId, status: 'parsing', candidateCount: 0 });
      setDriveUrl('');

      // Resumes download + per-resume name extraction run in the background.
      // Poll the batch until it leaves "parsing" so the count updates live
      // instead of showing a stale 0.
      const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
      for (let i = 0; i < 60; i += 1) {
        await sleep(3000);
        try {
          const detail = await client.get<ImportBatchResponse>(`/import-batches/${batchId}`);
          setDriveSuccessInfo({
            id: batchId,
            status: detail.data.status,
            candidateCount: detail.data.candidates.length,
          });
          if (detail.data.status !== 'parsing') break;
        } catch {
          // transient; keep polling
        }
      }
      await refreshLists();
    } catch (e: unknown) {
      setDriveError(e instanceof Error ? e.message : 'Import failed');
    } finally {
      setImportingDrive(false);
    }
  };

  const resetDummyForm = () => {
    setEditingDummyId(null);
    setNewDummyTitle('');
    setNewDummyAbstract('');
    setNewDummyMentorName('');
    setNewDummyMentorEmail('');
    setNewDummyPrereqs('');
  };

  const startEditDummyProject = (p: Project) => {
    setEditingDummyId(p.id);
    setNewDummyTitle(p.title);
    setNewDummyAbstract(p.abstract || '');
    setNewDummyMentorName(p.mentor?.name || '');
    setNewDummyMentorEmail(p.mentor?.email || '');
    setNewDummyPrereqs((p.prerequisites || []).map((pr) => pr.skill.name).join(', '));
    setDummyProjectError(null);
  };

  const handleCreateDummyProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDummyTitle || !newDummyMentorName || !newDummyMentorEmail) return;
    setDummyProjectSaving(true);
    setDummyProjectError(null);
    try {
      const payload = {
        title: newDummyTitle,
        abstract: newDummyAbstract || null,
        mentor_name: newDummyMentorName,
        mentor_email: newDummyMentorEmail,
        prerequisites: newDummyPrereqs.split(',').map((s) => s.trim()).filter(Boolean),
      };
      if (editingDummyId != null) {
        await client.put(`/projects/dummy/${editingDummyId}`, payload);
      } else {
        await client.post('/projects/dummy', payload);
      }
      resetDummyForm();
      await refreshDummyProjects();
      await refreshLists();
    } catch (err: unknown) {
      setDummyProjectError(err instanceof Error ? err.message : 'Failed to save dummy project');
    } finally {
      setDummyProjectSaving(false);
    }
  };

  const handleDeleteDummyProject = async (id: number) => {
    setDummyProjectError(null);
    try {
      await client.delete(`/projects/dummy/${id}`);
      if (editingDummyId === id) resetDummyForm();
      await refreshDummyProjects();
      await refreshLists();
    } catch (err: unknown) {
      setDummyProjectError(err instanceof Error ? err.message : 'Failed to delete dummy project');
    }
  };

  const loadCandidateRecs = async (force = false) => {
    if (!selectedCandidateReg) return;
    setMatchingLoading(true);
    setMatchError(null);
    setCandidateRecommendations([]);
    try {
      // Stream results: render the deterministic ranked list immediately, then
      // fill in each project's LLM score as it finishes computing.
      await streamMatchEvents(
        `/matching/student-recommendations/${selectedCandidateReg}/stream${force ? '?force=true' : ''}`,
        (evt) => {
          if (evt.type === 'meta') {
            setStudentMatchContext({ candidateName: evt.candidate_name, registrationNumber: evt.registration_number, cached: evt.cached });
          } else if (evt.type === 'prelim') {
            setCandidateRecommendations(evt.recommendations);
          } else if (evt.type === 'update') {
            setCandidateRecommendations((prev) => {
              const merged = prev.map((r) => (r.project_id === evt.recommendation.project_id ? evt.recommendation : r));
              merged.sort((a, b) => b.final_score - a.final_score);
              return merged.map((r, i) => ({ ...r, rank: i + 1 }));
            });
          } else if (evt.type === 'done') {
            setCandidateRecommendations(evt.response.recommendations);
            setStudentMatchContext({ candidateName: evt.response.candidate_name, registrationNumber: evt.response.registration_number, cached: evt.response.cached ?? false });
          } else if (evt.type === 'error') {
            setMatchError(evt.message);
          }
        }
      );
    } catch (e: unknown) {
      setMatchError(e instanceof Error ? e.message : 'Matching failed');
    } finally {
      setMatchingLoading(false);
    }
  };

  const loadProjectRecs = async (force = false) => {
    if (!selectedProjectId) return;
    setMatchingLoading(true);
    setMatchError(null);
    if (!force) setProjectRecommendations([]);
    try {
      const res = await client.get<ProjectRecommendationsResponse>(
        `/matching/project-recommendations/${selectedProjectId}${force ? '?force=true' : ''}`
      );
      setProjectRecommendations(res.data.recommendations);
      setProjectMatchContext({ projectTitle: res.data.project_title, projectId: res.data.project_id, cached: res.data.cached ?? false });
    } catch (e: unknown) {
      setMatchError(e instanceof Error ? e.message : 'Matching failed');
    } finally {
      setMatchingLoading(false);
    }
  };

  const handleResumeRecommendation = async () => {
    if (!resumeFile) return;
    setResumeLoading(true);
    setMatchError(null);
    setResumeRecs([]);
    setResumeMatchContext(null);
    try {
      const formData = new FormData();
      formData.append('file', resumeFile);
      if (preferredTopics) formData.append('preferred_topics', preferredTopics);
      if (githubUrl) formData.append('github_url', githubUrl);
      if (leetcodeUrl) formData.append('leetcode_url', leetcodeUrl);
      if (codeforcesUrl) formData.append('codeforces_url', codeforcesUrl);
      if (kaggleUrl) formData.append('kaggle_url', kaggleUrl);
      if (scholarUrl) formData.append('scholar_url', scholarUrl);
      if (liveAppUrl) formData.append('live_app_url', liveAppUrl);
      const res = await client.post<StudentRecommendationsResponse>(
        '/matching/student-recommendations',
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      setResumeRecs(res.data.recommendations);
      setResumeMatchContext({ candidateName: res.data.candidate_name, registrationNumber: res.data.registration_number });
    } catch (e: unknown) {
      setMatchError(e instanceof Error ? e.message : 'Matching failed');
    } finally {
      setResumeLoading(false);
    }
  };

  const runPreview = async () => {
    setPreviewLoading(true);
    setPreviewError(null);
    setPreviewResult(null);
    try {
      const res = await client.post<LlmPreviewResult>('/matching/llm-preview', { prompt: previewPrompt });
      setPreviewResult(res.data);
    } catch (e: unknown) {
      setPreviewError(e instanceof Error ? e.message : 'LLM preview failed');
    } finally {
      setPreviewLoading(false);
    }
  };

  const loadMentorStudentRecs = async (force = false) => {
    const mentor = mentors.find((m) => String(m.id) === selectedMentorId);
    if (!mentor?.project?.id) return;
    setMentorMatchLoading(true);
    setMentorMatchError(null);
    if (!force) setMentorMatchResults([]);
    try {
      const res = await client.get<ProjectRecommendationsResponse>(
        `/matching/project-recommendations/${mentor.project.id}${force ? '?force=true' : ''}`
      );
      setMentorMatchResults(res.data.recommendations);
      setMentorMatchContext({ projectTitle: res.data.project_title, projectId: res.data.project_id, cached: res.data.cached ?? false });
    } catch (e: unknown) {
      setMentorMatchError(e instanceof Error ? e.message : 'Matching failed');
    } finally {
      setMentorMatchLoading(false);
    }
  };

  const loadBatchScores = async (batchId: string, force = false) => {
    if (!batchId) return;
    setBatchScoreLoading(true);
    setBatchScoreError(null);
    if (!force) setBatchMatrix(null);
    try {
      const [batchRes, scoreRes] = await Promise.all([
        client.get<ImportBatchResponse>(`/import-batches/${batchId}`),
        client.get<BatchScoreMatrixResponse>(
          `/matching/batch-scores/${batchId}${force ? '?force=true' : ''}`
        ),
      ]);
      setSelectedBatchDetails(batchRes.data);
      setBatchMatrix(scoreRes.data);
    } catch (e: unknown) {
      setBatchScoreError(e instanceof Error ? e.message : 'Failed to load batch scores');
    } finally {
      setBatchScoreLoading(false);
    }
  };

  const selectBatch = (id: string) => {
    setSelectedBatchId(id);
    setSelectedBatchDetails(null);
    setBatchMatrix(null);
    setBatchScoreError(null);
    setBatchReportError(null);
    loadBatchScores(id);
  };

  const handleBatchReport = async () => {
    if (!selectedBatchId) return;
    setBatchReportLoading(true);
    setBatchReportError(null);
    try {
      await downloadBatchReport(selectedBatchId);
    } catch (e: unknown) {
      setBatchReportError(e instanceof Error ? e.message : 'Failed to generate report');
    } finally {
      setBatchReportLoading(false);
    }
  };

  const apiOk = health?.status === 'ok';
  const dbOk = health?.database === 'connected';
  const llmOk = health?.llm?.configured && health?.llm?.enabled;

  return (
    <div className="app-shell">
      <div className="app-mesh" aria-hidden />
      <div className="app-grid" aria-hidden />

      {/* ── Header ── */}
      <header className="glass-header sticky top-0 z-20">
        <div className="relative mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-cyan-500 shadow-lg shadow-violet-500/25">
              <Brain className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">
                <span className="text-gradient">ProjectMatchAI</span>
              </h1>
              <p className="text-xs text-muted-foreground">Intelligent student–project matching</p>
            </div>
          </div>

          <div className="hidden items-center gap-2 sm:flex">
            {healthLoading ? (
              <span className="text-xs text-muted-foreground animate-pulse">Connecting…</span>
            ) : (
              <>
                <StatusPill ok={!!apiOk} label="API" />
                <StatusPill ok={!!dbOk} label="Database" />
                <StatusPill ok={!!llmOk} label="LLM" />
                <span className="stat-chip ml-1">
                  <Users className="h-3.5 w-3.5 text-cyan-400" />
                  {candidates.length} students
                </span>
                <span className="stat-chip">
                  <FolderKanban className="h-3.5 w-3.5 text-violet-400" />
                  {projects.length} projects
                </span>
                <span className="stat-chip">
                  <GraduationCap className="h-3.5 w-3.5 text-fuchsia-400" />
                  {mentors.length} mentors
                </span>
                <span className="stat-chip">
                  <LayoutGrid className="h-3.5 w-3.5 text-amber-400" />
                  {importBatches.length} batches
                </span>
              </>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2 sm:hidden">
            {!healthLoading && (
              <>
                <StatusPill ok={!!apiOk} label="API" />
                <StatusPill ok={!!llmOk} label="LLM" />
              </>
            )}
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-10">
        {/* ── Tab bar ── */}
        <nav className="glass-card mb-8 flex flex-wrap gap-1 p-1.5">
          <TabButton active={activeTab === 'match'} onClick={() => setActiveTab('match')} icon={Zap}>
            Matching
          </TabButton>
          <TabButton active={activeTab === 'mentor'} onClick={() => setActiveTab('mentor')} icon={GraduationCap}>
            Mentors
          </TabButton>
          <TabButton active={activeTab === 'batches'} onClick={() => setActiveTab('batches')} icon={LayoutGrid}>
            Batches
          </TabButton>
          <TabButton active={activeTab === 'import'} onClick={() => setActiveTab('import')} icon={Upload}>
            Import
          </TabButton>
          <TabButton active={activeTab === 'dummy_projects'} onClick={() => setActiveTab('dummy_projects')} icon={FolderKanban}>
            Dummy Projects
          </TabButton>
          <TabButton active={activeTab === 'llm'} onClick={() => setActiveTab('llm')} icon={Sparkles}>
            LLM test
          </TabButton>
        </nav>

        {listsError && (
          <div className="mb-6 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200 backdrop-blur-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span>{listsError}</span>
              <Button
                variant="outline"
                size="sm"
                onClick={refreshLists}
                disabled={listsLoading}
                className="border-white/10 bg-white/[0.03]"
              >
                {listsLoading ? 'Refreshing…' : 'Retry'}
              </Button>
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════
            MATCH TAB
        ═══════════════════════════════════════════════════════════ */}
        {activeTab === 'match' && (
          <div className="space-y-6 animate-fade-in">
            <div className="glass-card overflow-hidden">
              <div className="h-1 bg-gradient-to-r from-violet-500 via-fuchsia-500 to-cyan-400" />
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center gap-2 text-lg font-bold">
                  <Zap className="h-5 w-5 text-violet-400" />
                  Run matching
                </CardTitle>
                <CardDescription className="text-muted-foreground/90">
                  Growth-weighted hybrid scoring · embeddings · tiered skills · top-K LLM deep-eval
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="flex flex-wrap gap-2">
                  {(
                    [
                      ['student', 'By student', User],
                      ['project', 'By project', FolderKanban],
                      ['resume', 'By resume', FileText],
                    ] as const
                  ).map(([mode, label, Icon]) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => setMatchMode(mode)}
                      className={cn(
                        'inline-flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-medium transition-all duration-200',
                        matchMode === mode
                          ? 'border-violet-500/40 bg-gradient-to-r from-violet-500/15 to-cyan-500/10 text-violet-200 shadow-sm shadow-violet-500/10'
                          : 'border-white/[0.06] bg-white/[0.02] text-muted-foreground hover:border-white/10 hover:text-foreground'
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      {label}
                    </button>
                  ))}
                </div>

                {matchMode === 'student' && (
                  <div className="flex flex-col gap-3 sm:flex-row">
                    <select
                      className="select-glass sm:w-48"
                      value={studentSourceFilter}
                      onChange={(e) => {
                        setStudentSourceFilter(e.target.value as 'all' | 'excel' | 'drive');
                        setSelectedCandidateReg('');
                      }}
                    >
                      <option value="all">All Sources</option>
                      <option value="excel">Excel Uploads</option>
                      <option value="drive">Drive Link Uploads</option>
                    </select>
                    <select
                      className="select-glass flex-1"
                      value={selectedCandidateReg}
                      onChange={(e) => setSelectedCandidateReg(e.target.value)}
                    >
                      <option value="">Select a student…</option>
                      {candidates
                        .filter((c) => studentSourceFilter === 'all' || c.source === studentSourceFilter)
                        .map((c) => (
                          <option key={c.id} value={c.registration_number}>
                            {c.name} ({c.registration_number})
                          </option>
                        ))}
                    </select>
                    <Button onClick={() => loadCandidateRecs()} disabled={!selectedCandidateReg || matchingLoading} className="btn-glow sm:w-44">
                      {matchingLoading ? 'Running…' : 'Match projects'}
                    </Button>
                  </div>
                )}

                {matchMode === 'project' && (
                  <div className="flex flex-col gap-3 sm:flex-row">
                    <select
                      className="select-glass flex-1"
                      value={selectedProjectId}
                      onChange={(e) => setSelectedProjectId(e.target.value)}
                    >
                      <option value="">Select a project…</option>
                      {projects.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.title}{p.mentor ? ` — ${p.mentor.name}` : ''}
                        </option>
                      ))}
                    </select>
                    <Button onClick={() => loadProjectRecs()} disabled={!selectedProjectId || matchingLoading} className="btn-glow sm:w-44">
                      {matchingLoading ? 'Running…' : 'Match students'}
                    </Button>
                  </div>
                )}

                {matchMode === 'resume' && (
                  <div className="space-y-4 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                    <div className="space-y-3">
                      <Input type="file" accept=".pdf" onChange={(e) => setResumeFile(e.target.files?.[0] || null)} />
                      <Input
                        placeholder="Preferred topics (comma-separated, optional)"
                        value={preferredTopics}
                        onChange={(e) => setPreferredTopics(e.target.value)}
                      />
                    </div>

                    <div>
                      <button
                        type="button"
                        onClick={() => setShowAdvanced(!showAdvanced)}
                        className="text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {showAdvanced ? 'Hide optional platform links ↑' : 'Show optional platform links ↓'}
                      </button>

                      {showAdvanced && (
                        <div className="mt-3 grid gap-3 sm:grid-cols-2">
                          <Input placeholder="GitHub URL or Username" value={githubUrl} onChange={(e) => setGithubUrl(e.target.value)} />
                          <Input placeholder="LeetCode URL or Username" value={leetcodeUrl} onChange={(e) => setLeetcodeUrl(e.target.value)} />
                          <Input placeholder="Codeforces URL or Username" value={codeforcesUrl} onChange={(e) => setCodeforcesUrl(e.target.value)} />
                          <Input placeholder="Kaggle URL or Username" value={kaggleUrl} onChange={(e) => setKaggleUrl(e.target.value)} />
                          <Input placeholder="Google Scholar URL" value={scholarUrl} onChange={(e) => setScholarUrl(e.target.value)} />
                          <Input placeholder="Live App URLs (comma-separated)" value={liveAppUrl} onChange={(e) => setLiveAppUrl(e.target.value)} />
                          <p className="sm:col-span-2 text-[10px] text-muted-foreground">
                            If provided, these links will be fetched live to score the Developer Profile accurately. If left blank, the system will try to extract them from the PDF.
                          </p>
                        </div>
                      )}
                    </div>

                    <Button onClick={handleResumeRecommendation} disabled={resumeLoading || !resumeFile} className="btn-glow w-full">
                      {resumeLoading ? 'Processing & Fetching metrics…' : 'Match resume to projects'}
                    </Button>
                  </div>
                )}

                {matchError && (
                  <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200 backdrop-blur-sm">
                    {matchError}
                  </div>
                )}
              </CardContent>
            </div>

            {matchMode === 'student' && (
              <MatchResultsList
                results={candidateRecommendations}
                variant="project"
                registrationNumber={studentMatchContext?.registrationNumber}
                emptyMessage="Select a student and run matching to see ranked project recommendations."
                contextTitle={studentMatchContext ? `Recommendations for ${studentMatchContext.candidateName}` : undefined}
                contextSubtitle={studentMatchContext ? `Registration ${studentMatchContext.registrationNumber} · expand any card for weights, contributions, and LLM rationale` : undefined}
                cached={studentMatchContext?.cached}
                onRecompute={() => loadCandidateRecs(true)}
                recomputing={matchingLoading}
              />
            )}
            {matchMode === 'project' && (
              <MatchResultsList
                results={projectRecommendations}
                variant="candidate"
                projectId={projectMatchContext?.projectId}
                emptyMessage="Select a project and run matching to see ranked student recommendations."
                contextTitle={projectMatchContext ? `Students for "${projectMatchContext.projectTitle}"` : undefined}
                contextSubtitle={projectMatchContext ? `Project #${projectMatchContext.projectId} · full calculation details inside each card` : undefined}
                cached={projectMatchContext?.cached}
                onRecompute={() => loadProjectRecs(true)}
                recomputing={matchingLoading}
              />
            )}
            {matchMode === 'resume' && (
              <MatchResultsList
                results={resumeRecs}
                variant="project"
                registrationNumber={resumeMatchContext?.registrationNumber}
                emptyMessage="Upload a PDF resume to see ranked project recommendations."
                contextTitle={resumeMatchContext ? `Resume match · ${resumeMatchContext.candidateName}` : undefined}
                contextSubtitle={resumeMatchContext ? `Registration ${resumeMatchContext.registrationNumber}` : undefined}
              />
            )}
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════
            MENTOR TAB
        ═══════════════════════════════════════════════════════════ */}
        {activeTab === 'mentor' && (
          <div className="space-y-6 animate-fade-in">
            <div className="glass-card overflow-hidden">
              <div className="h-1 bg-gradient-to-r from-fuchsia-500 via-violet-500 to-cyan-400" />
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center gap-2 text-lg font-bold">
                  <GraduationCap className="h-5 w-5 text-fuchsia-400" />
                  Mentor view
                </CardTitle>
                <CardDescription className="text-muted-foreground/90">
                  Select a mentor to see their project and find the students who best align with it.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="flex flex-col gap-3 sm:flex-row">
                  <select
                    className="select-glass flex-1"
                    value={selectedMentorId}
                    onChange={(e) => {
                      setSelectedMentorId(e.target.value);
                      setMentorMatchResults([]);
                      setMentorMatchContext(null);
                      setMentorMatchError(null);
                    }}
                  >
                    <option value="">Select a mentor…</option>
                    {mentors.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name}{m.project ? ` — ${m.project.title}` : ' (no project assigned)'}
                      </option>
                    ))}
                  </select>
                  <Button
                    onClick={() => loadMentorStudentRecs()}
                    disabled={!selectedMentorId || mentorMatchLoading || !mentors.find((m) => String(m.id) === selectedMentorId)?.project}
                    className="btn-glow sm:w-44"
                  >
                    {mentorMatchLoading ? 'Running…' : 'Find students'}
                  </Button>
                </div>

                {selectedMentorId && (() => {
                  const mentor = mentors.find((m) => String(m.id) === selectedMentorId);
                  if (!mentor) return null;
                  return (
                    <div className="rounded-xl border border-fuchsia-500/20 bg-gradient-to-br from-fuchsia-500/5 to-violet-500/5 p-4 space-y-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-fuchsia-300/70">Mentor profile</p>
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className="rounded-lg border border-white/[0.06] bg-white/[0.03] p-3">
                          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Name</p>
                          <p className="mt-1 font-semibold text-foreground">{mentor.name}</p>
                        </div>
                        <div className="rounded-lg border border-white/[0.06] bg-white/[0.03] p-3">
                          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Email</p>
                          <p className="mt-1 flex items-center gap-1.5 font-semibold text-cyan-300">
                            <Mail className="h-3.5 w-3.5" />{mentor.email}
                          </p>
                        </div>
                        {mentor.phone && (
                          <div className="rounded-lg border border-white/[0.06] bg-white/[0.03] p-3">
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Phone</p>
                            <p className="mt-1 flex items-center gap-1.5 font-semibold text-violet-300">
                              <Phone className="h-3.5 w-3.5" />{mentor.phone}
                            </p>
                          </div>
                        )}
                        {mentor.project ? (
                          <div className="rounded-lg border border-violet-500/20 bg-violet-500/5 p-3">
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-violet-300/70">Assigned project</p>
                            <p className="mt-1 font-semibold text-foreground">{mentor.project.title}</p>
                            <p className="mt-0.5 text-[10px] text-muted-foreground">Project ID #{mentor.project.id}</p>
                          </div>
                        ) : (
                          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-300/70">Project</p>
                            <p className="mt-1 text-sm text-amber-300">No project assigned — matching unavailable</p>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })()}

                {mentorMatchError && (
                  <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200 backdrop-blur-sm">
                    {mentorMatchError}
                  </div>
                )}
              </CardContent>
            </div>

            <MatchResultsList
              results={mentorMatchResults}
              variant="candidate"
              projectId={mentorMatchContext?.projectId}
              emptyMessage='Select a mentor and click "Find students" to see ranked student recommendations.'
              contextTitle={mentorMatchContext ? `Students for "${mentorMatchContext.projectTitle}"` : undefined}
              contextSubtitle={mentorMatchContext ? `Project #${mentorMatchContext.projectId} · expand each card for full score breakdown` : undefined}
              cached={mentorMatchContext?.cached}
              onRecompute={() => loadMentorStudentRecs(true)}
              recomputing={mentorMatchLoading}
            />
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════
            BATCHES TAB  — click a batch, scores auto-load instantly
        ═══════════════════════════════════════════════════════════ */}
        {activeTab === 'batches' && (
          <div className="space-y-7 animate-fade-in">

            {/* Section header */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                  <LayoutGrid className="h-4 w-4 text-amber-400" />
                  Import batches
                </h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Click a batch — scores load instantly from cache, or compute once and save automatically.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={refreshLists}
                  disabled={listsLoading}
                  className="text-xs text-muted-foreground hover:text-amber-300 transition-colors flex items-center gap-1.5 disabled:opacity-40"
                >
                  ↺ Refresh lists
                </button>
                {batchMatrix && (
                  <button
                    type="button"
                    onClick={() => loadBatchScores(selectedBatchId, true)}
                    disabled={batchScoreLoading}
                    className="text-xs text-muted-foreground hover:text-amber-300 transition-colors flex items-center gap-1.5 disabled:opacity-40"
                  >
                    ↺ Recompute
                  </button>
                )}
                <Button
                  onClick={handleBatchReport}
                  disabled={!selectedBatchId || batchReportLoading || batchScoreLoading}
                  size="sm"
                  className="btn-glow gap-2"
                  title={
                    selectedBatchId
                      ? 'Download a PDF of every student’s top 2 projects vs. the mentor-selected students'
                      : 'Select a batch first'
                  }
                >
                  <FileDown className="h-4 w-4" />
                  {batchReportLoading ? 'Generating…' : 'Generate PDF report'}
                </Button>
              </div>
            </div>

            {batchReportError && (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200 backdrop-blur-sm">
                {batchReportError}
              </div>
            )}

            {/* Batch cards */}
            {importBatches.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/[0.08] bg-white/[0.01] px-6 py-14 text-center">
                <LayoutGrid className="h-8 w-8 text-muted-foreground/25 mx-auto mb-3" />
                <p className="text-sm font-medium text-muted-foreground">No import batches yet</p>
                <p className="text-xs text-muted-foreground/50 mt-1">
                  Upload a workbook on the Import tab to create one.
                </p>
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {importBatches.map((b) => {
                  const isSelected = String(b.id) === selectedBatchId;
                  return (
                    <button
                      key={b.id}
                      type="button"
                      onClick={() => selectBatch(String(b.id))}
                      disabled={batchScoreLoading && !isSelected}
                      className={cn(
                        'relative rounded-2xl border p-5 text-left transition-all duration-200 overflow-hidden group',
                        isSelected
                          ? 'border-amber-500/50 shadow-lg shadow-amber-500/10'
                          : 'border-white/[0.07] hover:border-white/[0.14] hover:bg-white/[0.02]'
                      )}
                    >
                      {isSelected && (
                        <span className="absolute inset-0 bg-gradient-to-br from-amber-500/10 via-orange-500/5 to-transparent pointer-events-none" />
                      )}
                      <span className={cn(
                        'absolute top-0 left-0 right-0 h-0.5 transition-all',
                        isSelected
                          ? 'bg-gradient-to-r from-amber-400 via-orange-400 to-amber-300'
                          : 'bg-gradient-to-r from-white/20 to-white/5 opacity-0 group-hover:opacity-40'
                      )} />

                      <div className="relative flex items-start justify-between gap-2 mb-3">
                        <div>
                          <span className="text-base font-bold text-foreground">Batch #{b.id}</span>
                          <p className="text-[11px] text-muted-foreground mt-0.5">
                            {new Date(b.created_at).toLocaleString()}
                          </p>
                        </div>
                        <span className={cn(
                          'rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase shrink-0',
                          b.status === 'validated' ? 'bg-emerald-500/15 text-emerald-300' : 'bg-amber-500/15 text-amber-300'
                        )}>
                          {b.status}
                        </span>
                      </div>

                      <div className="relative flex flex-wrap gap-4 text-xs">
                        <span className="flex items-center gap-1.5 text-cyan-300/80">
                          <Users className="h-3 w-3" />{b.candidate_count} students
                        </span>
                        <span className="flex items-center gap-1.5 text-emerald-300/80">
                          <User className="h-3 w-3" />{b.mentor_count} mentors
                        </span>
                        <span className="flex items-center gap-1.5 text-violet-300/80">
                          <FolderKanban className="h-3 w-3" />{b.project_count} projects
                        </span>
                      </div>

                      {isSelected && batchScoreLoading && (
                        <div className="relative mt-3 h-1 rounded-full bg-white/[0.06] overflow-hidden">
                          <div className="absolute inset-0 h-full w-full bg-gradient-to-r from-transparent via-amber-400/60 to-transparent animate-[shimmer_1.2s_ease-in-out_infinite]" />
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            )}

            {/* Error */}
            {batchScoreError && (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200 backdrop-blur-sm">
                {batchScoreError}
              </div>
            )}

            {/* Loading skeleton */}
            {batchScoreLoading && !batchMatrix && (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-ping" />
                  <span className="animate-pulse">Computing scores for all student × project pairs…</span>
                </div>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div
                      key={i}
                      className="h-52 rounded-2xl border border-white/[0.05] bg-white/[0.02] animate-pulse"
                      style={{ animationDelay: `${i * 80}ms` }}
                    />
                  ))}
                </div>
              </div>
            )}

            {selectedBatchDetails && !batchScoreLoading && (
              <div className="glass-card overflow-hidden">
                <div className="h-1 bg-gradient-to-r from-cyan-500 to-emerald-500" />
                <CardHeader>
                  <CardTitle className="text-base">Imported batch data</CardTitle>
                  <CardDescription>
                    Review the exact students, mentors, and projects stored for Batch #{selectedBatchDetails.id}.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="grid gap-3 sm:grid-cols-3">
                    <Meta label="Students" value={String(selectedBatchDetails.candidates.length)} />
                    <Meta label="Mentors" value={String(selectedBatchDetails.mentors.length)} />
                    <Meta label="Projects" value={String(selectedBatchDetails.projects.length)} />
                  </div>

                  <div className="grid gap-5 lg:grid-cols-3">
                    <div className="space-y-2">
                      <h3 className="text-sm font-semibold text-foreground">Students</h3>
                      <div className="max-h-72 space-y-2 overflow-y-auto rounded-xl border border-white/[0.06] bg-black/20 p-3">
                        {selectedBatchDetails.candidates.length === 0 ? (
                          <p className="text-xs text-muted-foreground">No students stored for this batch.</p>
                        ) : (
                          selectedBatchDetails.candidates.map((candidate) => (
                            <div key={candidate.id} className="rounded-lg border border-white/[0.06] bg-white/[0.03] p-3 text-xs">
                              <p className="font-semibold text-foreground">{candidate.name}</p>
                              <p className="text-muted-foreground">{candidate.registration_number}</p>
                              {candidate.email && <p className="text-muted-foreground">{candidate.email}</p>}
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <h3 className="text-sm font-semibold text-foreground">Mentors</h3>
                      <div className="max-h-72 space-y-2 overflow-y-auto rounded-xl border border-white/[0.06] bg-black/20 p-3">
                        {selectedBatchDetails.mentors.length === 0 ? (
                          <p className="text-xs text-muted-foreground">No mentors stored for this batch.</p>
                        ) : (
                          selectedBatchDetails.mentors.map((mentor) => (
                            <div key={mentor.id} className="rounded-lg border border-white/[0.06] bg-white/[0.03] p-3 text-xs">
                              <p className="font-semibold text-foreground">{mentor.name}</p>
                              <p className="text-muted-foreground">{mentor.email}</p>
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <h3 className="text-sm font-semibold text-foreground">Projects</h3>
                      <div className="max-h-72 space-y-2 overflow-y-auto rounded-xl border border-white/[0.06] bg-black/20 p-3">
                        {selectedBatchDetails.projects.length === 0 ? (
                          <p className="text-xs text-muted-foreground">No projects stored for this batch.</p>
                        ) : (
                          selectedBatchDetails.projects.map((project) => (
                            <div key={project.id} className="rounded-lg border border-white/[0.06] bg-white/[0.03] p-3 text-xs">
                              <p className="font-semibold text-foreground">{project.title}</p>
                              {project.mentor && <p className="text-muted-foreground">{project.mentor.name}</p>}
                              {project.abstract && <p className="mt-1 line-clamp-3 text-muted-foreground">{project.abstract}</p>}
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </div>
            )}

            {/* Score tiles — shown immediately, no wrapper card */}
            {batchMatrix && !batchScoreLoading && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-sm font-semibold text-foreground">Batch #{batchMatrix.batch_id}</span>
                  {batchMatrix.cached ? (
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-300">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                      Cached
                      {batchMatrix.computed_at && (
                        <span className="text-emerald-300/60">· {new Date(batchMatrix.computed_at).toLocaleString()}</span>
                      )}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/25 bg-amber-500/10 px-2.5 py-1 text-[11px] font-medium text-amber-300">
                      <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                      Computed &amp; saved
                    </span>
                  )}
                </div>
                <BatchScoreMatrix data={batchMatrix} />
              </div>
            )}

          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════
            IMPORT TAB
        ═══════════════════════════════════════════════════════════ */}
        {activeTab === 'import' && (
          <div className="space-y-6 animate-fade-in">
            <div className="glass-card overflow-hidden">
              <div className="h-1 bg-gradient-to-r from-cyan-500 to-violet-500" />
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg font-bold">
                  <FileSpreadsheet className="h-5 w-5 text-cyan-400" />
                  Workbook upload
                </CardTitle>
                <CardDescription>Import students and projects from your mentorship workbook (.xlsx).</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                  <Input
                    type="file"
                    accept=".xlsx"
                    className="flex-1 border-white/[0.08] bg-white/[0.03] file:text-violet-300"
                    onChange={(e) => setWorkbookFile(e.target.files?.[0] || null)}
                  />
                  <Button onClick={handleWorkbookUpload} disabled={uploading || !workbookFile} className="btn-glow gap-2">
                    <Upload className="h-4 w-4" />
                    {uploading ? 'Processing…' : 'Upload'}
                  </Button>
                </div>

                {uploadError && (
                  <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                    {uploadError}
                  </div>
                )}
              </CardContent>
            </div>

            <div className="glass-card overflow-hidden">
              <div className="h-1 bg-gradient-to-r from-violet-500 to-fuchsia-500" />
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg font-bold">
                  <FileText className="h-5 w-5 text-violet-400" />
                  Import resumes from Drive link
                </CardTitle>
                <CardDescription>Create a workbook-less batch by importing candidate resumes directly from a Google Drive folder URL.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                  <Input
                    placeholder="Enter Google Drive folder URL containing PDFs..."
                    className="flex-1 border-white/[0.08] bg-white/[0.03]"
                    value={driveUrl}
                    onChange={(e) => setDriveUrl(e.target.value)}
                  />
                  <Button onClick={handleDriveImport} disabled={importingDrive || !driveUrl} className="btn-glow gap-2">
                    <Upload className="h-4 w-4" />
                    {importingDrive ? 'Importing…' : 'Import'}
                  </Button>
                </div>

                {driveError && (
                  <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                    {driveError}
                  </div>
                )}

                {driveSuccessInfo && (
                  driveSuccessInfo.status === 'parsing' ? (
                    <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
                      <span className="inline-flex items-center gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-ping" />
                        Importing resumes for Batch #{driveSuccessInfo.id}… {driveSuccessInfo.candidateCount} candidate{driveSuccessInfo.candidateCount === 1 ? '' : 's'} created so far. Downloading + parsing each resume takes a moment.
                      </span>
                    </div>
                  ) : driveSuccessInfo.status === 'failed' ? (
                    <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                      Batch #{driveSuccessInfo.id} failed — no resumes could be downloaded or parsed. Check that the Drive folder is shared and contains PDF resumes.
                    </div>
                  ) : (
                    <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
                      Batch #{driveSuccessInfo.id} imported {driveSuccessInfo.candidateCount} candidate{driveSuccessInfo.candidateCount === 1 ? '' : 's'}. They're now selectable under Matching → By student (Drive Link Uploads) and match against your dummy projects.
                    </div>
                  )
                )}
              </CardContent>
            </div>

            {batchInfo && (
              <div className="glass-card overflow-hidden">
                <div className="h-1 bg-gradient-to-r from-cyan-500 to-emerald-500" />
                <CardHeader>
                  <CardTitle className="text-base">Imported records</CardTitle>
                  <CardDescription>
                    These are the students, mentors, and projects persisted from the uploaded workbook.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="grid gap-3 sm:grid-cols-3">
                    <Meta label="Students" value={String(batchInfo.candidates.length)} />
                    <Meta label="Mentors" value={String(batchInfo.mentors.length)} />
                    <Meta label="Projects" value={String(batchInfo.projects.length)} />
                  </div>
                  <div className="grid gap-5 lg:grid-cols-3">
                    <div className="space-y-2">
                      <h3 className="text-sm font-semibold text-foreground">Students</h3>
                      <div className="max-h-72 space-y-2 overflow-y-auto rounded-xl border border-white/[0.06] bg-black/20 p-3">
                        {batchInfo.candidates.length === 0 ? (
                          <p className="text-xs text-muted-foreground">No students were persisted from this upload.</p>
                        ) : (
                          batchInfo.candidates.map((candidate) => (
                            <div key={candidate.id} className="rounded-lg border border-white/[0.06] bg-white/[0.03] p-3 text-xs">
                              <p className="font-semibold text-foreground">{candidate.name}</p>
                              <p className="text-muted-foreground">{candidate.registration_number}</p>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                    <div className="space-y-2">
                      <h3 className="text-sm font-semibold text-foreground">Mentors</h3>
                      <div className="max-h-72 space-y-2 overflow-y-auto rounded-xl border border-white/[0.06] bg-black/20 p-3">
                        {batchInfo.mentors.length === 0 ? (
                          <p className="text-xs text-muted-foreground">No mentors were persisted from this upload.</p>
                        ) : (
                          batchInfo.mentors.map((mentor) => (
                            <div key={mentor.id} className="rounded-lg border border-white/[0.06] bg-white/[0.03] p-3 text-xs">
                              <p className="font-semibold text-foreground">{mentor.name}</p>
                              <p className="text-muted-foreground">{mentor.email}</p>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                    <div className="space-y-2">
                      <h3 className="text-sm font-semibold text-foreground">Projects</h3>
                      <div className="max-h-72 space-y-2 overflow-y-auto rounded-xl border border-white/[0.06] bg-black/20 p-3">
                        {batchInfo.projects.length === 0 ? (
                          <p className="text-xs text-muted-foreground">No projects were persisted from this upload.</p>
                        ) : (
                          batchInfo.projects.map((project) => (
                            <div key={project.id} className="rounded-lg border border-white/[0.06] bg-white/[0.03] p-3 text-xs">
                              <p className="font-semibold text-foreground">{project.title}</p>
                              {project.mentor && <p className="text-muted-foreground">{project.mentor.name}</p>}
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </div>
            )}

            {batchInfo && (
              <div className="glass-card overflow-hidden">
                <div className="h-1 bg-gradient-to-r from-emerald-500 to-cyan-500" />
                <CardHeader>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="text-base">Import result</CardTitle>
                    <div className="flex gap-2">
                      <StatusPill ok={batchInfo.can_proceed} label={batchInfo.status} />
                      <span className="text-xs text-muted-foreground">Batch #{batchInfo.id}</span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    {Object.entries(batchInfo.sheet_summaries).map(([sheet, s]) => (
                      <div
                        key={sheet}
                        className="rounded-xl border border-white/[0.06] bg-gradient-to-br from-white/[0.04] to-transparent p-4 transition-colors hover:border-violet-500/20"
                      >
                        <p className="truncate text-sm font-medium">{sheet}</p>
                        <div className="mt-2 flex gap-3 text-xs text-muted-foreground">
                          <span>{s.total_rows} rows</span>
                          {s.errors > 0 && <span className="text-rose-400">{s.errors} err</span>}
                          {s.warnings > 0 && <span className="text-amber-400">{s.warnings} warn</span>}
                        </div>
                      </div>
                    ))}
                  </div>

                  {batchInfo.issues.length > 0 && (
                    <div className="max-h-72 space-y-2 overflow-y-auto rounded-xl border border-white/[0.06] bg-black/20 p-3">
                      {batchInfo.issues.map((issue, idx) => (
                        <div
                          key={idx}
                          className={cn(
                            'rounded-md px-3 py-2 text-xs',
                            issue.severity === 'error' ? 'bg-rose-500/10 text-rose-300' : 'bg-amber-500/10 text-amber-200'
                          )}
                        >
                          <span className="font-semibold uppercase">{issue.severity}</span>
                          {issue.sheet_name && (
                            <span className="text-muted-foreground">
                              {' '} · {issue.sheet_name}{issue.row_number ? ` row ${issue.row_number}` : ''}
                            </span>
                          )}
                          <p className="mt-0.5">{issue.message}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </div>
            )}
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════
            DUMMY PROJECTS TAB
        ═══════════════════════════════════════════════════════════ */}
        {activeTab === 'dummy_projects' && (
          <div className="space-y-6 animate-fade-in">
            <div className="grid gap-6 md:grid-cols-2">
              {/* Add Form */}
              <div className="glass-card overflow-hidden">
                <div className="h-1 bg-gradient-to-r from-violet-500 to-fuchsia-500" />
                <CardHeader>
                  <CardTitle className="text-lg font-bold">
                    {editingDummyId != null ? `Edit Dummy Project #${editingDummyId}` : 'Add Dummy Project'}
                  </CardTitle>
                  <CardDescription>Create a project not linked to any workbook batch (matched only against Drive candidates).</CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleCreateDummyProject} className="space-y-4">
                    <div>
                      <label className="text-xs font-semibold text-muted-foreground">Project Title *</label>
                      <Input required placeholder="Title" value={newDummyTitle} onChange={(e) => setNewDummyTitle(e.target.value)} />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-muted-foreground">Description / Abstract</label>
                      <textarea
                        className="input-glass w-full rounded-xl border border-white/[0.08] bg-white/[0.03] p-3 text-sm text-foreground focus:border-violet-500 focus:outline-none"
                        rows={3}
                        placeholder="Abstract description..."
                        value={newDummyAbstract}
                        onChange={(e) => setNewDummyAbstract(e.target.value)}
                      />
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div>
                        <label className="text-xs font-semibold text-muted-foreground">Mentor Name *</label>
                        <Input required placeholder="Mentor Name" value={newDummyMentorName} onChange={(e) => setNewDummyMentorName(e.target.value)} />
                      </div>
                      <div>
                        <label className="text-xs font-semibold text-muted-foreground">Mentor Email *</label>
                        <Input required type="email" placeholder="email@example.com" value={newDummyMentorEmail} onChange={(e) => setNewDummyMentorEmail(e.target.value)} />
                      </div>
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-muted-foreground">Prerequisites (comma-separated)</label>
                      <Input placeholder="Python, PyTorch, React" value={newDummyPrereqs} onChange={(e) => setNewDummyPrereqs(e.target.value)} />
                    </div>
                    {dummyProjectError && (
                      <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-xs text-rose-200">
                        {dummyProjectError}
                      </div>
                    )}
                    <div className="flex gap-2">
                      <Button type="submit" disabled={dummyProjectSaving} className="btn-glow w-full">
                        {dummyProjectSaving ? 'Saving…' : editingDummyId != null ? 'Update Project' : 'Add Project'}
                      </Button>
                      {editingDummyId != null && (
                        <Button type="button" variant="outline" onClick={resetDummyForm} disabled={dummyProjectSaving} className="border-white/10 bg-white/[0.03]">
                          Cancel
                        </Button>
                      )}
                    </div>
                  </form>
                </CardContent>
              </div>

              {/* List of Dummy Projects */}
              <div className="glass-card overflow-hidden">
                <div className="h-1 bg-gradient-to-r from-cyan-500 to-violet-500" />
                <CardHeader>
                  <CardTitle className="text-lg font-bold">Dummy Projects ({dummyProjects.length})</CardTitle>
                  <CardDescription>All batch-less custom projects configured in the system.</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="max-h-[500px] space-y-3 overflow-y-auto pr-1">
                    {dummyProjectsLoading ? (
                      <p className="text-sm text-muted-foreground animate-pulse">Loading dummy projects...</p>
                    ) : dummyProjects.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No dummy projects created yet.</p>
                    ) : (
                      dummyProjects.map((p) => (
                        <div key={p.id} className={cn(
                          'rounded-xl border bg-white/[0.03] p-4 text-xs space-y-2',
                          editingDummyId === p.id ? 'border-violet-500/50' : 'border-white/[0.06]'
                        )}>
                          <div className="flex items-start justify-between gap-3">
                            <h4 className="font-semibold text-foreground text-sm">{p.title}</h4>
                            <div className="flex shrink-0 items-center gap-1.5">
                              <button
                                type="button"
                                onClick={() => startEditDummyProject(p)}
                                className="rounded-md border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[10px] font-medium text-cyan-300 hover:bg-white/[0.08] transition-colors"
                              >
                                Edit
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDeleteDummyProject(p.id)}
                                className="rounded-md border border-rose-500/20 bg-rose-500/10 px-2 py-0.5 text-[10px] font-medium text-rose-300 hover:bg-rose-500/20 transition-colors"
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                          {p.abstract && <p className="text-muted-foreground line-clamp-3">{p.abstract}</p>}
                          {p.mentor && (
                            <div className="flex flex-wrap gap-x-3 text-[11px] text-muted-foreground/80">
                              <span className="font-medium text-foreground">{p.mentor.name}</span>
                              <span>·</span>
                              <span>{p.mentor.email}</span>
                            </div>
                          )}
                          {p.prerequisites && p.prerequisites.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 pt-1">
                              {p.prerequisites.map((pr) => (
                                <span key={pr.skill.id} className="rounded bg-white/[0.05] border border-white/[0.08] px-1.5 py-0.5 text-[10px] text-foreground/85">
                                  {pr.skill.name}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </CardContent>
              </div>
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════
            LLM TAB
        ═══════════════════════════════════════════════════════════ */}
        {activeTab === 'llm' && (
          <div className="space-y-6 animate-fade-in">
            <div className="glass-card overflow-hidden">
              <div className="h-1 bg-gradient-to-r from-fuchsia-500 to-violet-500" />
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg font-bold">
                  <Sparkles className="h-5 w-5 text-fuchsia-400" />
                  LLM connection test
                </CardTitle>
                <CardDescription>
                  Send a test prompt before running full matching. Requires LLM_ENABLED=true in .env.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input value={previewPrompt} onChange={(e) => setPreviewPrompt(e.target.value)} placeholder="Test prompt" />
                <Button onClick={runPreview} disabled={previewLoading || !previewPrompt.trim()} className="btn-glow">
                  {previewLoading ? 'Calling LLM…' : 'Test response'}
                </Button>

                {previewError && (
                  <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                    {previewError}
                  </div>
                )}

                {previewResult && (
                  <div className="space-y-4 rounded-xl border border-white/[0.08] bg-gradient-to-b from-violet-500/5 to-transparent p-5">
                    <div className="grid gap-3 text-sm sm:grid-cols-2">
                      <Meta label="Provider" value={previewResult.provider} />
                      <Meta label="Model" value={previewResult.model || '—'} />
                      <Meta label="Matching enabled" value={previewResult.llm_enabled ? 'Yes' : 'No'} />
                      <Meta label="Configured" value={previewResult.configured ? 'Yes' : 'No'} />
                      {previewResult.http_status != null && (
                        <Meta label="HTTP status" value={String(previewResult.http_status)} />
                      )}
                    </div>
                    {previewResult.skipped && (
                      <p className="text-sm text-amber-300">Skipped: {previewResult.skip_reason}</p>
                    )}
                    {previewResult.error && (
                      <p className="text-sm text-rose-300">{previewResult.error}</p>
                    )}
                    <div>
                      <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">Response</p>
                      <pre className="max-h-64 overflow-auto rounded-xl border border-white/[0.06] bg-black/30 p-4 text-xs leading-relaxed whitespace-pre-wrap text-foreground/90">
                        {previewResult.raw_response || '(empty)'}
                      </pre>
                    </div>
                  </div>
                )}
              </CardContent>
            </div>

            <div className="glass-card">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg font-bold">
                  <Activity className="h-5 w-5 text-cyan-400" />
                  System status
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Button variant="outline" size="sm" onClick={checkHealth} disabled={healthLoading} className="mb-4 border-white/10 bg-white/[0.03]">
                  {healthLoading ? 'Refreshing…' : 'Refresh'}
                </Button>
                {health && (
                  <pre className="overflow-auto rounded-xl border border-white/[0.06] bg-black/30 p-4 text-xs text-muted-foreground">
                    {JSON.stringify(health, null, 2)}
                  </pre>
                )}
              </CardContent>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
