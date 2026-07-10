import client from '@/lib/api/client';

/**
 * Fetches the candidate-project fit report PDF and triggers a browser download.
 * Throws with a readable message on failure (the API error interceptor returns
 * an Error, but blob error bodies aren't parsed, so we fall back to a default).
 */
export async function downloadMatchReport(
  registrationNumber: string,
  projectId: number
): Promise<void> {
  const res = await client.get('/matching/report', {
    params: { registration_number: registrationNumber, project_id: projectId },
    responseType: 'blob',
  });

  triggerDownload(res.data as BlobPart, `fit-report-${registrationNumber}-${projectId}.pdf`);
}

/**
 * Fetches the whole-batch selection report PDF (each student's top-2 projects
 * vs. the mentor-selected students from the workbook) and triggers a download.
 */
export async function downloadBatchReport(batchId: number | string): Promise<void> {
  const res = await client.get(`/matching/batch-report/${batchId}`, {
    responseType: 'blob',
  });

  triggerDownload(res.data as BlobPart, `batch-${batchId}-selection-report.pdf`);
}

function triggerDownload(data: BlobPart, filename: string): void {
  const blob = new Blob([data], { type: 'application/pdf' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
