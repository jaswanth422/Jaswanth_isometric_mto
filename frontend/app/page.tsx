"use client";

import { useEffect, useState } from "react";
import UploadZone from "@/components/UploadZone";
import SummaryCards from "@/components/SummaryCards";
import MTOTable from "@/components/MTOTable";
import ReviewQueue from "@/components/ReviewQueue";
import { extractMTO, csvExportUrl, excelExportUrl, ApiRequestError, UploadJobResponse } from "@/lib/api";
import { MTOResponse } from "@/lib/types";

type Status = "idle" | "processing" | "success" | "error";

function mockBannerMessage(result: MTOResponse): string {
  switch (result.mock_reason) {
    case "missing_api_key":
      return "No Gemini API key is configured on the backend, so this is a sample mock output rather than a real extraction.";
    case "configured_mock_provider":
      return "The backend is explicitly configured to use the mock provider, so this is a sample output rather than a real extraction.";
    case "gemini_cooldown":
      return `Gemini is temporarily unavailable${result.mock_details ? ` (${result.mock_details})` : ""}, so the backend is using the mock fallback for now.`;
    case "gemini_error":
      return `Gemini was unavailable for this upload${result.mock_details ? ` (${result.mock_details})` : ""}, so the backend returned the mock fallback instead of a real extraction.`;
    default:
      return "The backend used the mock fallback instead of Gemini, so this is a sample output rather than a real extraction.";
  }
}

export default function Home() {
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<MTOResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>("");
  const [resultId, setResultId] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  async function processFile(file: File) {
    setStatus("processing");
    setErrorMessage(null);
    setResult(null);
    setSelectedFile(file);
    setFileName(file.name);

    // Revoke any previous preview URL to avoid memory leaks.
    if (previewUrl) {
      try {
        URL.revokeObjectURL(previewUrl);
      } catch {
        /* ignore */
      }
      setPreviewUrl(null);
    }

    if (file.type !== "application/pdf") {
      const obj = URL.createObjectURL(file);
      setPreviewUrl(obj);
    } else {
      setPreviewUrl(null);
    }

    try {
      const response = await extractMTO(file);
      if (!response.mto) {
        throw new ApiRequestError(response.detail || "No extraction result available.", 500);
      }
      setResult(response.mto);
      setResultId(response.job_id ?? null);
      setStatus("success");
    } catch (err) {
      const message = err instanceof ApiRequestError ? err.message : "Something went wrong while processing the drawing.";
      setErrorMessage(message);
      setStatus("error");
    }
  }

  async function handleFileSelected(file: File) {
    await processFile(file);
  }

  async function retryLastFile() {
    if (!selectedFile) return;
    await processFile(selectedFile);
  }

  function reset() {
    setStatus("idle");
    setResult(null);
    setErrorMessage(null);
    if (previewUrl) {
      try {
        URL.revokeObjectURL(previewUrl);
      } catch {
        /* ignore */
      }
    }
    setPreviewUrl(null);
    setFileName("");
    setResultId(null);
    setSelectedFile(null);
  }

  // Revoke object URL on unmount
  useEffect(() => {
    return () => {
      if (previewUrl) {
        try {
          URL.revokeObjectURL(previewUrl);
        } catch {
          /* ignore */
        }
      }
    };
  }, [previewUrl]);

  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-6xl px-4 py-10">
        <header className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900">Isometric Drawing → MTO Generator</h1>
          <p className="text-slate-600 mt-1">
            Upload a piping isometric drawing to automatically generate a Material Take-Off.
          </p>
        </header>

        {status === "idle" && (
          <UploadZone onFileSelected={handleFileSelected} disabled={false} />
        )}

        {status === "processing" && (
          <div className="rounded-xl border border-slate-200 bg-white p-12 text-center">
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" />
            <p className="mt-4 text-slate-700 font-medium">Processing {fileName}…</p>
            <p className="text-sm text-slate-500 mt-1">
              Running extraction, OCR cross-check, and validation. Most uploads finish in well under 20 seconds.
            </p>
          </div>
        )}

        {status === "error" && (
          <div className="rounded-xl border border-red-300 bg-red-50 p-8 text-center">
            <p className="font-semibold text-red-800">Couldn't process this drawing</p>
            {fileName && <p className="mt-2 text-sm text-red-700">File: {fileName}</p>}
            <p className="text-sm text-red-700 mt-2">{errorMessage}</p>
            <div className="mt-4 flex justify-center gap-3">
              <button
                onClick={retryLastFile}
                disabled={!selectedFile}
                className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Retry same file
              </button>
              <button
                onClick={reset}
                className="rounded-md border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-100"
              >
                Try another file
              </button>
            </div>
          </div>
        )}

        {status === "success" && result && (
          <div className="space-y-6">
            {result.mock && (
              <div className="rounded-md border border-blue-300 bg-blue-50 px-4 py-2 text-sm text-blue-800">
                <strong>Mock mode:</strong> {mockBannerMessage(result)}
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <h2 className="font-semibold text-slate-800 mb-2">Uploaded Drawing</h2>
                {previewUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={previewUrl} alt="Uploaded isometric drawing" className="w-full rounded-md border border-slate-100" />
                ) : (
                  <p className="text-sm text-slate-500">{fileName} (PDF preview not shown)</p>
                )}
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <h2 className="font-semibold text-slate-800 mb-2">Drawing Metadata</h2>
                <dl className="text-sm space-y-1">
                  {Object.entries(result.drawing_meta).map(([key, value]) => (
                    <div key={key} className="flex justify-between border-b border-slate-50 py-1">
                      <dt className="text-slate-500">{key.replace(/_/g, " ")}</dt>
                      <dd className="text-slate-800 font-medium">{value ?? "—"}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            </div>

            <SummaryCards summary={result.summary} />

            <ReviewQueue items={result.items} needsReview={result.needs_review} />

            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">Material Take-Off</h2>
              <div className="flex gap-2">
                <a
                  href={resultId ? csvExportUrl(resultId) : "#"}
                  className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-900"
                >
                  Export CSV
                </a>
                <a
                  href={resultId ? excelExportUrl(resultId) : "#"}
                  className="rounded-md border border-emerald-300 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-800 hover:bg-emerald-100"
                >
                  Export Excel
                </a>
                <button
                  onClick={reset}
                  className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
                >
                  Upload another
                </button>
              </div>
            </div>

            <MTOTable items={result.items} />
          </div>
        )}
      </div>
    </main>
  );
}
