import client from '@/lib/api/client';

const XLSX_MEDIA_TYPE =
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

/**
 * Downloads the blank import workbook — the sheets, headers, and example rows
 * the upload expects.
 */
export async function downloadWorkbookTemplate(): Promise<void> {
  const res = await client.get('/import-batches/template', { responseType: 'blob' });

  const blob = new Blob([res.data as BlobPart], { type: XLSX_MEDIA_TYPE });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'import-template.xlsx';
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
