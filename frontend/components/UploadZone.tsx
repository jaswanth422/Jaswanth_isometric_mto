"use client";

import { useCallback, useRef, useState } from "react";

const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/jpg", "application/pdf"];
const MAX_SIZE_MB = 20;

interface UploadZoneProps {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

export default function UploadZone({ onFileSelected, disabled }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndSelect = useCallback(
    (file: File | undefined) => {
      if (!file) return;

      if (!ACCEPTED_TYPES.includes(file.type)) {
        setValidationError(`Unsupported file type: ${file.type || "unknown"}. Use PNG, JPG, or PDF.`);
        return;
      }

      const sizeMb = file.size / (1024 * 1024);
      if (sizeMb > MAX_SIZE_MB) {
        setValidationError(`File is ${sizeMb.toFixed(1)} MB, which exceeds the ${MAX_SIZE_MB} MB limit.`);
        return;
      }

      setValidationError(null);
      onFileSelected(file);
    },
    [onFileSelected]
  );

  return (
    <div>
      <div
        onClick={() => !disabled && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          if (!disabled) validateAndSelect(e.dataTransfer.files?.[0]);
        }}
        className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 text-center transition-colors cursor-pointer
          ${isDragging ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-slate-50"}
          ${disabled ? "opacity-50 cursor-not-allowed" : "hover:border-blue-400"}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_TYPES.join(",")}
          className="hidden"
          disabled={disabled}
          onChange={(e) => validateAndSelect(e.target.files?.[0])}
        />
        <p className="text-slate-700 font-medium">
          Drag and drop an isometric drawing here, or click to browse
        </p>
        <p className="text-sm text-slate-500 mt-1">PNG, JPG, or PDF — max {MAX_SIZE_MB} MB</p>
      </div>
      {validationError && (
        <p className="mt-2 text-sm text-red-600" role="alert">
          {validationError}
        </p>
      )}
    </div>
  );
}
