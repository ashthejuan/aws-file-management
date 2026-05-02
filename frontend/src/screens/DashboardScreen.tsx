import { useCallback, useEffect, useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";

import { ApiError, api, uploadToPresignedUrl } from "../api/client";
import type { FileItem, UploadTicket } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { formatBytes, formatTimestamp } from "../utils/format";

interface UploadProgress {
  fileName: string;
  loaded: number;
  total: number;
}

export default function DashboardScreen() {
  const { token, signOut } = useAuth();
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const refresh = useCallback(async () => {
    if (!token) return;
    try {
      const items = await api.listFiles(token);
      setFiles(items);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        signOut();
        return;
      }
      setError(err instanceof Error ? err.message : "Failed to load files.");
    } finally {
      setLoading(false);
    }
  }, [token, signOut]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleUpload = useCallback(
    async (file: File) => {
      if (!token || progress) return;
      setError(null);
      setProgress({ fileName: file.name, loaded: 0, total: file.size });
      let ticket: UploadTicket | null = null;
      try {
        ticket = await api.requestUpload(token, {
          fileName: file.name,
          size: file.size,
          contentType: file.type || "application/octet-stream",
        });
        await uploadToPresignedUrl(ticket, file, (loaded, total) => {
          setProgress({ fileName: file.name, loaded, total });
        });
        await refresh();
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          signOut();
          return;
        }
        if (ticket) {
          try {
            await api.deleteFile(token, ticket.fileId);
          } catch (cleanupErr) {
            console.warn("Failed to clean up incomplete upload", cleanupErr);
          }
        }
        setError(err instanceof Error ? err.message : "Upload failed.");
      } finally {
        setProgress(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      }
    },
    [token, progress, refresh, signOut],
  );

  const handleFileInput = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      void handleUpload(file);
    }
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragActive(false);
    const file = event.dataTransfer.files?.[0];
    if (file) {
      void handleUpload(file);
    }
  };

  const handleDelete = async (file: FileItem) => {
    if (!token) return;
    if (!window.confirm(`Delete "${file.fileName}"? This cannot be undone.`)) return;
    setDeletingId(file.fileId);
    setError(null);
    try {
      await api.deleteFile(token, file.fileId);
      setFiles((prev) => prev.filter((item) => item.fileId !== file.fileId));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        signOut();
        return;
      }
      setError(err instanceof Error ? err.message : "Failed to delete file.");
    } finally {
      setDeletingId(null);
    }
  };

  const progressPct = progress && progress.total > 0
    ? Math.min(100, Math.round((progress.loaded / progress.total) * 100))
    : 0;

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Files</h1>
        <div className="app-header-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => void refresh()}
            disabled={loading}
          >
            Refresh
          </button>
          <button type="button" className="btn btn-ghost" onClick={signOut}>
            Sign out
          </button>
        </div>
      </header>

      <main className="app-main">
        <section
          className={`dropzone ${dragActive ? "dropzone-active" : ""}`}
          onDragOver={(event) => {
            event.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
        >
          <div className="dropzone-inner">
            <p className="dropzone-title">Drag &amp; drop a file here</p>
            <p className="dropzone-or">or</p>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => fileInputRef.current?.click()}
              disabled={!!progress}
            >
              {progress ? "Uploading…" : "Choose a file"}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              className="visually-hidden"
              onChange={handleFileInput}
            />
          </div>
          {progress && (
            <div className="upload-progress" aria-live="polite">
              <div className="upload-progress-meta">
                <span className="upload-progress-name" title={progress.fileName}>
                  {progress.fileName}
                </span>
                <span>{progressPct}%</span>
              </div>
              <div className="progress-bar">
                <div className="progress-bar-fill" style={{ width: `${progressPct}%` }} />
              </div>
            </div>
          )}
        </section>

        {error && (
          <div className="banner banner-error" role="alert">
            {error}
          </div>
        )}

        <section className="files">
          <div className="files-header">
            <h2>Your files</h2>
            <span className="files-count">{files.length}</span>
          </div>
          {loading ? (
            <p className="state-text">Loading…</p>
          ) : files.length === 0 ? (
            <p className="state-text">No files yet. Upload one above to get started.</p>
          ) : (
            <ul className="file-list">
              {files.map((file) => (
                <li key={file.fileId} className="file-row">
                  <div className="file-meta">
                    <span className="file-name" title={file.fileName}>
                      {file.fileName}
                    </span>
                    <span className="file-sub">
                      {formatBytes(file.size)} · {formatTimestamp(file.uploadedAt)}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="btn btn-ghost btn-danger"
                    onClick={() => void handleDelete(file)}
                    disabled={deletingId === file.fileId}
                  >
                    {deletingId === file.fileId ? "Deleting…" : "Delete"}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}
