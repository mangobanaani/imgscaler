export async function createJob(file, factor, denoise, useTFHub = false) {
  const form = new FormData();
  form.append('file', file);
  form.append('factor', factor);
  form.append('denoise', denoise);
  form.append('use_tfhub', useTFHub);
  const resp = await fetch('/api/v1/upscale/job', { method: 'POST', body: form });
  if (!resp.ok) throw new Error('Job create failed');
  return resp.json();
}

export async function getJobStatus(jobId) {
  const resp = await fetch(`/api/v1/upscale/job/${jobId}`);
  if (!resp.ok) throw new Error('Status failed');
  return resp.json();
}

export function getJobResultUrl(jobId) {
  return `/api/v1/upscale/job/${jobId}/result`;
}
