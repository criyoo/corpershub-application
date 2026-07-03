import { clearSession, getSession, setSession, type SessionState, type SessionUser } from "@/lib/session";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function getApiErrorMessage(body: unknown): string {
  if (!body || typeof body !== "object") {
    return "Request failed.";
  }

  if ("detail" in body) {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }

  for (const value of Object.values(body as Record<string, unknown>)) {
    if (Array.isArray(value) && typeof value[0] === "string") {
      return value[0];
    }
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }

  return JSON.stringify(body);
}

type RequestOptions = RequestInit & {
  auth?: boolean;
  formData?: boolean;
};

type TokenState = {
  accessToken: string;
  refreshToken?: string;
};

async function refreshAccessToken(session: SessionState | null): Promise<TokenState> {
  const payload = session?.refreshToken ? { refresh: session.refreshToken } : {};
  const response = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    clearSession();
    throw new Error("Session expired.");
  }
  const data = (await response.json()) as { access: string; refresh?: string };
  return {
    accessToken: data.access,
    refreshToken: data.refresh ?? session?.refreshToken
  };
}

export async function restoreSessionFromRefreshCookie(): Promise<SessionState | null> {
  let session: SessionState | null = null;

  try {
    const refreshed = await refreshAccessToken(null);
    const requestHeaders = new Headers({
      Authorization: `Bearer ${refreshed.accessToken}`
    });
    const response = await fetch(`${API_BASE_URL}/auth/me/`, {
      credentials: "include",
      headers: requestHeaders
    });

    if (!response.ok) {
      clearSession();
      return null;
    }

    const user = (await response.json()) as SessionUser;
    session = {
      accessToken: refreshed.accessToken,
      refreshToken: refreshed.refreshToken,
      user
    };
    setSession(session);
    return session;
  } catch {
    clearSession();
    return null;
  }
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { auth = true, formData = false, headers, ...init } = options;
  let session = getSession();
  const requestHeaders = new Headers(headers);
  if (!formData) {
    requestHeaders.set("Content-Type", "application/json");
  }
  if (auth && session?.accessToken) {
    requestHeaders.set("Authorization", `Bearer ${session.accessToken}`);
  }

  let response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: requestHeaders
  });

  if (response.status === 401 && auth && session) {
    const refreshed = await refreshAccessToken(session);
    session = { ...session, ...refreshed };
    setSession(session);
    requestHeaders.set("Authorization", `Bearer ${session.accessToken}`);
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: "include",
      headers: requestHeaders
    });
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({
      detail: response.statusText ? `Request failed (${response.status} ${response.statusText}).` : "Request failed.",
    }));
    throw new ApiError(getApiErrorMessage(body), response.status, body);
  }

  return (await response.json()) as T;
}

export async function loginWithCredentials(payload: { email: string; password: string; rememberMe?: boolean }): Promise<SessionState> {
  const response = await apiFetch<{
    access: string;
    user: SessionUser;
  }>("/auth/login/", {
    auth: false,
    method: "POST",
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
      remember_me: payload.rememberMe,
    }),
  });

  const session: SessionState = {
    accessToken: response.access,
    rememberMe: payload.rememberMe ?? false,
    user: response.user,
  };
  setSession(session);
  return session;
}

export async function resolveSessionUser(): Promise<SessionUser | null> {
  let session = getSession();
  if (!session?.accessToken) {
    return null;
  }

  const requestHeaders = new Headers({
    Authorization: `Bearer ${session.accessToken}`
  });

  let response = await fetch(`${API_BASE_URL}/auth/me/`, {
    credentials: "include",
    headers: requestHeaders
  });

  if (response.status === 401) {
    try {
      const refreshed = await refreshAccessToken(session);
      session = { ...session, ...refreshed };
      setSession(session);
    } catch {
      return null;
    }

    requestHeaders.set("Authorization", `Bearer ${session.accessToken}`);
    response = await fetch(`${API_BASE_URL}/auth/me/`, {
      credentials: "include",
      headers: requestHeaders
    });
  }

  if (response.status === 401 || response.status === 403) {
    clearSession();
    return null;
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Request failed." }));
    throw new ApiError(getApiErrorMessage(body), response.status, body);
  }

  const user = (await response.json()) as SessionUser;
  const nextSession = {
    ...session,
    user
  };
  setSession(nextSession);
  return user;
}

export type PaginatedResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
