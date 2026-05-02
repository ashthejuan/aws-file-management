const RAW_BASE = import.meta.env.VITE_API_URL ?? "";
const API_BASE = RAW_BASE.replace(/\/+$/, "");

export interface AuthResponse {
  token: string;
  expiresIn: number;
}

export interface FileItem {
  fileId: string;
  fileName: string;
  size: number;
  contentType: string;
  status: string;
  uploadedAt: number;
}

export interface UploadTicket {
  fileId: string;
  uploadUrl: string;
  expiresIn: number;
  requiredHeaders: Record<string, string>;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  token?: string | null;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  if (!API_BASE) {
    throw new ApiError(0, "VITE_API_URL is not configured. Set it in frontend/.env.");
  }

  const headers: Record<string, string> = {};
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (options.token) {
    headers["Authorization"] = `Bearer ${options.token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch (err) {
    throw new ApiError(0, err instanceof Error ? err.message : "Network error");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    const message =
      (payload && typeof payload === "object" && "message" in payload
        ? String((payload as { message: unknown }).message)
        : null) ??
      (typeof payload === "string" && payload ? payload : null) ??
      `Request failed with status ${response.status}`;
    throw new ApiError(response.status, message);
  }

  return payload as T;
}

export const api = {
  signup(email: string, password: string) {
    return request<AuthResponse>("/signup", {
      method: "POST",
      body: { email, password },
    });
  },
  login(email: string, password: string) {
    return request<AuthResponse>("/login", {
      method: "POST",
      body: { email, password },
    });
  },
  listFiles(token: string) {
    return request<FileItem[]>("/files", { token });
  },
  requestUpload(
    token: string,
    payload: { fileName: string; size: number; contentType: string },
  ) {
    return request<UploadTicket>("/files", {
      method: "POST",
      body: payload,
      token,
    });
  },
  deleteFile(token: string, fileId: string) {
    return request<void>(`/files/${encodeURIComponent(fileId)}`, {
      method: "DELETE",
      token,
    });
  },
};

export async function uploadToPresignedUrl(
  ticket: UploadTicket,
  file: File,
  onProgress?: (loaded: number, total: number) => void,
): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", ticket.uploadUrl);

    const contentType = ticket.requiredHeaders["Content-Type"];
    if (contentType) {
      xhr.setRequestHeader("Content-Type", contentType);
    }

    if (onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          onProgress(event.loaded, event.total);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(new ApiError(xhr.status, `Upload failed with status ${xhr.status}`));
      }
    };
    xhr.onerror = () => reject(new ApiError(0, "Network error during upload"));
    xhr.onabort = () => reject(new ApiError(0, "Upload aborted"));

    xhr.send(file);
  });
}
