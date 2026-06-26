import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Activity, Brain, FileSpreadsheet, ListChecks, Play, Upload } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import client from '@/lib/api/client';

const queryClient = new QueryClient();

function HealthPanel() {
  const [status, setStatus] = useState('Not checked');
  const [details, setDetails] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  const checkHealth = async () => {
    setLoading(true);
    setStatus('Checking');
    setDetails(null);

    try {
      const response = await client.get('/health');
      setStatus('Connected');
      setDetails(response.data);
    } catch (error: unknown) {
      setStatus('Unavailable');
      setDetails({
        error: error instanceof Error ? error.message : 'Connection failed',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          API Status
        </CardTitle>
        <CardDescription>Backend readiness for import and matching work.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={checkHealth} disabled={loading}>
            {loading ? 'Checking...' : 'Check API'}
          </Button>
          <span className="text-sm font-semibold text-muted-foreground">{status}</span>
        </div>

        {details ? (
          <pre className="max-h-52 overflow-auto rounded-md border bg-muted p-3 text-xs">
            {JSON.stringify(details, null, 2)}
          </pre>
        ) : null}
      </CardContent>
    </Card>
  );
}

function IntakePanel() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="h-5 w-5 text-primary" />
          Intake
        </CardTitle>
        <CardDescription>Workbook and resume inputs for the next implementation phase.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 sm:grid-cols-2">
        <label className="space-y-2 text-sm font-medium">
          Student, mentor, and project workbook
          <Input type="file" accept=".xlsx,.xls,.csv" disabled />
        </label>
        <label className="space-y-2 text-sm font-medium">
          Resume files
          <Input type="file" accept=".pdf" multiple disabled />
        </label>
      </CardContent>
    </Card>
  );
}

function WorkflowPanel() {
  const steps = [
    { label: 'Import workbook', icon: FileSpreadsheet },
    { label: 'Validate rows', icon: ListChecks },
    { label: 'Run matching', icon: Play },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-primary" />
          Matching Run
        </CardTitle>
        <CardDescription>Phase work starts with backend import, validation, and match-run APIs.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-3">
        {steps.map((step) => {
          const Icon = step.icon;
          return (
            <div key={step.label} className="rounded-md border bg-muted/40 p-4">
              <Icon className="mb-3 h-5 w-5 text-primary" />
              <div className="text-sm font-semibold">{step.label}</div>
              <div className="mt-2 text-xs text-muted-foreground">Pending phase implementation</div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

function AppShell() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-6 py-5">
          <Brain className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-xl font-semibold">ProjectMatchAI</h1>
            <p className="text-sm text-muted-foreground">Bulk intake and mentor-project matching</p>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl gap-6 px-6 py-8">
        <HealthPanel />
        <IntakePanel />
        <WorkflowPanel />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppShell />
    </QueryClientProvider>
  );
}
