import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Activity, Shield, Sparkles, Brain, CheckCircle } from 'lucide-react';
import client from '@/lib/api/client';

const queryClient = new QueryClient();

function HealthChecker() {
  const [status, setStatus] = useState<string>('Unknown');
  const [loading, setLoading] = useState<boolean>(false);
  const [details, setDetails] = useState<unknown>(null);

  const checkHealth = async () => {
    setLoading(true);
    setStatus('Checking...');
    setDetails(null);
    try {
      const response = await client.get('/health');
      setStatus('Success');
      setDetails(response.data);
    } catch (error: unknown) {
      setStatus('Failed');
      const msg = error instanceof Error ? error.message : 'Unknown connection error';
      setDetails({ error: msg });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="border-primary/20 bg-card/60 backdrop-blur-xl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-white">
          <Activity className="h-5 w-5 text-primary" />
          Backend Connection Test
        </CardTitle>
        <CardDescription>Verify Vite Proxy & FastAPI Health Connection</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-4">
          <Button onClick={checkHealth} disabled={loading}>
            {loading ? 'Testing...' : 'Test Health Endpoint'}
          </Button>
          <div className="flex flex-col">
            <span className="text-xs text-muted-foreground font-semibold">Status</span>
            <span className={`text-sm font-bold ${
              status === 'Success' ? 'text-green-400' : status === 'Failed' ? 'text-red-400' : 'text-yellow-400'
            }`}>{status}</span>
          </div>
        </div>
        {details ? (
          <pre className="bg-black/40 p-4 rounded-md text-xs font-mono border border-border overflow-x-auto text-green-300">
            {JSON.stringify(details, null, 2)}
          </pre>
        ) : null}
      </CardContent>
    </Card>
  );
}

function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col justify-between">
      <header className="border-b border-border bg-background/50 backdrop-blur-md sticky top-0 z-50 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2 font-bold text-lg text-primary">
          <Brain className="h-6 w-6" />
          <span>ProjectMatchAI</span>
        </div>
        <div className="flex items-center gap-4">
          <Button variant="ghost">Sign In</Button>
          <Button>Get Started</Button>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto px-6 py-12 space-y-12">
        <section className="text-center space-y-6 max-w-3xl mx-auto py-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/20 bg-primary/5 text-xs text-primary font-medium animate-pulse mx-auto">
            <Sparkles className="h-3 w-3" />
            Empowering Growth-First Mentorship
          </div>
          <h1 className="text-5xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-primary bg-clip-text text-transparent sm:text-6xl">
            Match on Potential, <br />
            Not Just Credentials.
          </h1>
          <p className="text-lg text-muted-foreground leading-relaxed">
            ProjectMatchAI is an intelligent platform connecting students to real-world projects based on growth potential. Discover project-driven learning opportunities matched to your velocity.
          </p>
        </section>

        <section className="grid md:grid-cols-2 gap-8 items-start">
          <HealthChecker />

          <Card className="border-border/60 bg-card/40">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <Shield className="h-5 w-5 text-primary" />
                Constitutional Foundation Active
              </CardTitle>
              <CardDescription>Core Engineering Quality Gates</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <CheckCircle className="h-4 w-4 text-primary" />
                <span>FastAPI Async Service Scaffolded</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <CheckCircle className="h-4 w-4 text-primary" />
                <span>Vite + React 18 SPA configured</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <CheckCircle className="h-4 w-4 text-primary" />
                <span>Docker Postgres & Ollama environments ready</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <CheckCircle className="h-4 w-4 text-primary" />
                <span>Ruff, Prettier & ESLint check gates verified</span>
              </div>
            </CardContent>
            <CardFooter className="gap-2">
              <Input placeholder="Enter email to join newsletter" className="max-w-xs" />
              <Button variant="secondary">Subscribe</Button>
            </CardFooter>
          </Card>
        </section>
      </main>

      <footer className="border-t border-border px-6 py-6 text-center text-xs text-muted-foreground">
        &copy; {new Date().getFullYear()} ProjectMatchAI. Created with Staff AI Architecture.
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <LandingPage />
    </QueryClientProvider>
  );
}
