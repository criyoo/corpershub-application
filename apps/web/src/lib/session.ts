export type UserRole = "company" | "corper" | "admin";

export type SessionUser = {
  id: string;
  email: string;
  role: UserRole;
  email_verified: boolean;
  is_active: boolean;
  created_at: string;
  profile_id?: string | null;
  profile_completed?: boolean;
  profile_path?: string;
  company_verification_status?: string | null;
  needs_subscription_selection?: boolean;
};

export type SessionState = {
  accessToken: string;
  refreshToken?: string;
  rememberMe?: boolean;
  user: SessionUser;
};

const STORAGE_KEY = "corpershub.session";
export const LOGIN_PATH = "/login/";
export const ADMIN_LOGIN_PATH = "/admin/login";

export function getSession(): SessionState | null {
  if (typeof window === "undefined") {
    return null;
  }
  const value = window.sessionStorage.getItem(STORAGE_KEY);
  return value ? (JSON.parse(value) as SessionState) : null;
}

export function setSession(session: SessionState) {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearSession() {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.removeItem(STORAGE_KEY);
}

export function dashboardPathForRole(role: UserRole) {
  if (role === "company") {
    return "/company/corpers";
  }
  if (role === "corper") {
    return "/corper/dashboard";
  }
  return "/admin/overview";
}

export function loginPathForRole(role: UserRole) {
  return role === "admin" ? ADMIN_LOGIN_PATH : LOGIN_PATH;
}

export function profilePathForRole(role: UserRole) {
  if (role === "company") {
    return "/company/verification";
  }
  if (role === "corper") {
    return "/corper/profile";
  }
  return "/admin/overview";
}

export function normalizeAppPath(path?: string | null) {
  const value = String(path ?? "").trim();
  if (!value) {
    return "";
  }

  const [pathname, search = ""] = value.split("?", 2);
  if (!pathname || pathname === "/") {
    return search ? `/?${search}` : "/";
  }

  const normalizedPathname = pathname.endsWith("/") ? pathname.replace(/\/+$/, "") || "/" : pathname;
  return search ? `${normalizedPathname}?${search}` : normalizedPathname;
}

export function normalizeProfilePath(role: UserRole, profilePath?: string) {
  const normalizedProfilePath = normalizeAppPath(profilePath);

  if (role === "company" && normalizedProfilePath === "/business/profile") {
    return "/company/verification";
  }

  if (role === "company") {
    if (!normalizedProfilePath) {
      return "/company/verification";
    }

    if (
      normalizedProfilePath === "/company/verification" ||
      normalizedProfilePath === "/company/profile" ||
      normalizedProfilePath === "/company/profile/terms"
    ) {
      return normalizedProfilePath;
    }

    return "/company/verification";
  }

  if (role === "corper") {
    if (!normalizedProfilePath) {
      return "/corper/profile";
    }

    if (
      normalizedProfilePath === "/corper/profile" ||
      normalizedProfilePath === "/corper/profile/terms" ||
      normalizedProfilePath === "/corper/verification"
    ) {
      return normalizedProfilePath;
    }

    return "/corper/profile";
  }

  const canonicalPath = profilePathForRole(role);
  if (!normalizedProfilePath) {
    return canonicalPath;
  }

  return normalizedProfilePath === canonicalPath ? normalizedProfilePath : canonicalPath;
}

export function isDiscoveryRouteForRole(role: UserRole, path?: string | null) {
  const normalizedPath = normalizeAppPath(path);

  if (role === "company") {
    return normalizedPath === "/company/corpers";
  }

  if (role === "corper") {
    return normalizedPath === "/corper/companies";
  }

  return false;
}

export function isBillingRouteForRole(role: UserRole, path?: string | null) {
  const normalizedPath = normalizeAppPath(path);

  if (role === "corper") {
    return normalizedPath === "/corper/billing";
  }

  return false;
}

export function defaultAppPathForUser(user: SessionUser) {
  if (user.role === "corper") {
    const normalizedProfilePath = user.profile_path
      ? normalizeProfilePath(user.role, user.profile_path)
      : null;

    if (!user.profile_path || normalizedProfilePath === "/corper/verification") {
      return "/corper/verification";
    }

    if (user.profile_completed === false && normalizedProfilePath) {
      return normalizedProfilePath;
    }

    if (user.needs_subscription_selection) {
      return "/corper/billing";
    }

    return "/corper/companies";
  }
  if (user.role === "company") {
    const normalizedProfilePath = user.profile_path
      ? normalizeProfilePath(user.role, user.profile_path)
      : null;

    if (user.company_verification_status !== "verified") {
      return "/company/verification";
    }

    if (user.profile_completed === false) {
      if (!normalizedProfilePath || normalizedProfilePath === "/company/verification") {
        return "/company/profile";
      }
      return normalizedProfilePath;
    }
    return dashboardPathForRole(user.role);
  }
  if (user.profile_completed === false) {
    return normalizeProfilePath(user.role, user.profile_path);
  }
  return dashboardPathForRole(user.role);
}
