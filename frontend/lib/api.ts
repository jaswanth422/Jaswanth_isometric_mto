import { MTOResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiRequestError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export interface UploadJobResponse {
  job_id: string;
  status: string;
  detail?: string | null;
  mto?: MTOResponse;
}

export async function extractMTO(file: File): Promise<UploadJobResponse> {
  const formData = new FormData();
  formData.append("file", file);

  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/upload`, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new ApiRequestError(
      `Couldn't reach the backend at ${API_URL}. Make sure the backend server is running and try again.`,
      0,
    );
  }

  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || body.error || detail;
    } catch {
      // response wasn't JSON, keep default message
    }
    throw new ApiRequestError(detail, res.status);
  }

  return res.json();
}

export function csvExportUrl(resultId: string): string {
  return `${API_URL}/api/mto/${encodeURIComponent(resultId)}/csv`;
}

export function excelExportUrl(resultId: string): string {
  return `${API_URL}/api/mto/${encodeURIComponent(resultId)}/xlsx`;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/api/health`);
    return res.ok;
  } catch {
    return false;
  }
}
