"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/providers/auth-provider";

const STORAGE_KEY = "corpershub.corper-verification-draft";

export type CorperVerificationDraft = {
  biodata: {
    first_name: string;
    middle_name: string;
    surname: string;
    date_of_birth: string;
    gender: string;
    mobile_number: string;
    state_of_origin: string;
    country_of_birth: string;
    university_matriculation_number: string;
  };
  nin: {
    submitted_value: string;
  };
  callup: {
    submitted_value: string;
    document: File | null;
    document_name: string;
  };
  state_code: {
    submitted_value: string;
    document: File | null;
    document_name: string;
  };
};

type SerializableCorperVerificationDraft = {
  owner_email: string | null;
  draft: Omit<CorperVerificationDraft, "callup" | "state_code"> & {
    callup: Omit<CorperVerificationDraft["callup"], "document">;
    state_code: Omit<CorperVerificationDraft["state_code"], "document">;
  };
};

type CorperVerificationDraftContextValue = {
  draft: CorperVerificationDraft;
  hydrated: boolean;
  replaceDraft: (value: CorperVerificationDraft) => void;
  clearDraft: () => void;
};

const EMPTY_DRAFT: CorperVerificationDraft = {
  biodata: {
    first_name: "",
    middle_name: "",
    surname: "",
    date_of_birth: "",
    gender: "",
    mobile_number: "",
    state_of_origin: "",
    country_of_birth: "",
    university_matriculation_number: "",
  },
  nin: {
    submitted_value: "",
  },
  callup: {
    submitted_value: "",
    document: null,
    document_name: "",
  },
  state_code: {
    submitted_value: "",
    document: null,
    document_name: "",
  },
};

const CorperVerificationDraftContext = createContext<CorperVerificationDraftContextValue | undefined>(undefined);

function serializeDraft(
  draft: CorperVerificationDraft,
  ownerEmail: string | null
): SerializableCorperVerificationDraft {
  return {
    owner_email: ownerEmail,
    draft: {
      biodata: draft.biodata,
      nin: draft.nin,
      callup: {
        submitted_value: draft.callup.submitted_value,
        document_name: draft.callup.document?.name ?? draft.callup.document_name,
      },
      state_code: {
        submitted_value: draft.state_code.submitted_value,
        document_name: draft.state_code.document?.name ?? draft.state_code.document_name,
      },
    },
  };
}

function deserializeDraft(
  serializedDraft: SerializableCorperVerificationDraft | null,
  ownerEmail: string | null
): CorperVerificationDraft {
  if (!serializedDraft || serializedDraft.owner_email !== ownerEmail) {
    return EMPTY_DRAFT;
  }

  return {
    biodata: serializedDraft.draft.biodata,
    nin: serializedDraft.draft.nin,
    callup: {
      submitted_value: serializedDraft.draft.callup.submitted_value,
      document: null,
      document_name: serializedDraft.draft.callup.document_name,
    },
    state_code: {
      submitted_value: serializedDraft.draft.state_code.submitted_value,
      document: null,
      document_name: serializedDraft.draft.state_code.document_name,
    },
  };
}

export function CorperVerificationDraftProvider({ children }: { children: React.ReactNode }) {
  const { hydrated: authHydrated, session } = useAuth();
  const ownerEmail = session?.user.role === "corper" ? session.user.email : null;
  const [draft, setDraft] = useState<CorperVerificationDraft>(EMPTY_DRAFT);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    if (!authHydrated || typeof window === "undefined") {
      return;
    }

    const serializedDraft = window.sessionStorage.getItem(STORAGE_KEY);
    if (!serializedDraft) {
      setDraft(EMPTY_DRAFT);
      setHydrated(true);
      return;
    }

    try {
      setDraft(deserializeDraft(JSON.parse(serializedDraft) as SerializableCorperVerificationDraft, ownerEmail));
    } catch {
      setDraft(EMPTY_DRAFT);
    }
    setHydrated(true);
  }, [authHydrated, ownerEmail]);

  useEffect(() => {
    if (!hydrated || typeof window === "undefined") {
      return;
    }

    if (!ownerEmail) {
      window.sessionStorage.removeItem(STORAGE_KEY);
      return;
    }

    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(serializeDraft(draft, ownerEmail)));
  }, [draft, hydrated, ownerEmail]);

  const value = useMemo<CorperVerificationDraftContextValue>(
    () => ({
      draft,
      hydrated,
      replaceDraft: setDraft,
      clearDraft: () => setDraft(EMPTY_DRAFT),
    }),
    [draft, hydrated]
  );

  return (
    <CorperVerificationDraftContext.Provider value={value}>
      {children}
    </CorperVerificationDraftContext.Provider>
  );
}

export function useCorperVerificationDraft() {
  const context = useContext(CorperVerificationDraftContext);
  if (!context) {
    throw new Error("useCorperVerificationDraft must be used within CorperVerificationDraftProvider.");
  }
  return context;
}

export function createEmptyCorperVerificationDraft(): CorperVerificationDraft {
  return {
    biodata: {
      first_name: "",
      middle_name: "",
      surname: "",
      date_of_birth: "",
      gender: "",
      mobile_number: "",
      state_of_origin: "",
      country_of_birth: "",
      university_matriculation_number: "",
    },
    nin: {
      submitted_value: "",
    },
    callup: {
      submitted_value: "",
      document: null,
      document_name: "",
    },
    state_code: {
      submitted_value: "",
      document: null,
      document_name: "",
    },
  };
}
