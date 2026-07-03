"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/components/providers/auth-provider";
import { apiFetch } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/media";

type CommunityMessage = {
  id: string;
  sender: string;
  sender_role: "corper";
  sender_name?: string;
  sender_profile_photo?: string | null;
  content: string;
  created_at: string;
  pending?: boolean;
};

type CommunityTopic = {
  topic_id: string;
  name: string;
  description: string;
  message_count: number;
  unread_count?: number;
};

type CommunityThread = {
  topic: CommunityTopic;
  messages: CommunityMessage[];
};

const MAX_MESSAGE_WORDS = 100;

const FALLBACK_TOPICS: CommunityTopic[] = [
  { topic_id: "ppa-search", name: "PPA Placement Search", description: "Discuss and share your experiences PPA placements", message_count: 0, unread_count: 0 },
  { topic_id: "general-discussion", name: "General Discussion", description: "Free for all chat about anything related to NYSC", message_count: 0, unread_count: 0 },
  { topic_id: "camp-life", name: "Orientation Camp Life", description: "Share your camp experiences, tips, and preparations", message_count: 0, unread_count: 0 },
  { topic_id: "accommodation-allowance", name: "Accommodation & Allowance", description: "Discuss monthly allowances, payments, and financial matters", message_count: 0, unread_count: 0 },
];

function getInitials(value: string) {
  const parts = value
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);

  if (!parts.length) {
    return "C";
  }

  return parts.map((part) => part.charAt(0).toUpperCase()).join("");
}

function normalizeId(id: string | undefined | null): string {
  if (!id) return "";
  return String(id).trim().toLowerCase();
}

function upsertMessage(messages: CommunityMessage[], nextMessage: CommunityMessage, replaceId?: string) {
  const withoutDuplicate = messages.filter((message) => message.id !== nextMessage.id);
  if (replaceId !== undefined) {
    const targetIndex = withoutDuplicate.findIndex((message) => message.id === replaceId);
    if (targetIndex >= 0) {
      const updated = [...withoutDuplicate];
      updated[targetIndex] = nextMessage;
      return updated;
    }
  }
  return [...withoutDuplicate, nextMessage];
}

function chunkMessageContent(content: string, wordsPerLine = 10) {
  const words = content.trim().split(/\s+/).filter(Boolean);
  const lines: string[] = [];

  for (let index = 0; index < words.length; index += wordsPerLine) {
    lines.push(words.slice(index, index + wordsPerLine).join(" "));
  }

  return lines.length > 0 ? lines : [content];
}

function countWords(content: string) {
  const trimmed = content.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}

function CorperAvatar({ name, image }: { name: string; image?: string | null }) {
  const imageUrl = resolveMediaUrl(image);
  const displayName = name.trim() || "Corper";

  return (
    <div className="h-7 w-7 shrink-0 overflow-hidden rounded-full border border-white/10 bg-white/10">
      {imageUrl ? (
        <img src={imageUrl} alt={displayName} className="h-full w-full object-cover" />
      ) : (
        <div className="flex h-full w-full items-center justify-center bg-[#0F5A3A]/70 text-[10px] font-semibold uppercase tracking-[0.12em] text-white">
          {getInitials(displayName)}
        </div>
      )}
    </div>
  );
}

function CommunityMessageBubble({
  message,
  isOwnMessage,
}: {
  message: CommunityMessage;
  isOwnMessage: boolean;
}) {
  const senderFullName = message.sender_name || (isOwnMessage ? "You" : "Corper");
  const senderFirstName = senderFullName.split(/\s+/)[0] || senderFullName;
  return (
    <div
      className={`flex ${isOwnMessage ? "justify-end" : "justify-start"} ${message.pending ? "opacity-60" : ""
        } motion-reduce:animate-none motion-safe:animate-[chat-bubble-in_180ms_ease-out]`}
    >
      <div className={`relative max-w-[15.5rem] ${isOwnMessage ? "items-end" : "items-start"} flex flex-col`}>
        <div
          className={`relative z-10 w-fit rounded-[22px] border px-3.5 py-2.5 shadow-[0_12px_26px_rgba(4,21,15,0.1)] ${isOwnMessage
            ? "border-[#0F5A3A]/80 bg-[#0F5A3A] text-white"
            : "border-[#0F5A3A]/18 bg-white text-[#0B3223]"
            }`}
        >
          <p className="break-words text-[13px] leading-5">
            {chunkMessageContent(message.content).map((line, index) => (
              <span key={`${message.id}-line-${index}`} className="block">
                {line}
              </span>
            ))}
          </p>
        </div>
        <div className={`mt-1.5 flex items-center gap-2 px-1 ${isOwnMessage ? "flex-row-reverse" : ""}`}>
          <CorperAvatar name={senderFirstName} image={message.sender_profile_photo} />
          <span className="max-w-[11.5rem] truncate text-[11px] font-medium tracking-[0.14em] text-white/58">
            {senderFirstName.charAt(0).toUpperCase() + senderFirstName.slice(1).toLowerCase()}
          </span>
        </div>
      </div>
    </div>
  );
}


export default function CommunityChatPage() {
  return (
    <Suspense fallback={null}>
      <CommunityChatPageContent />
    </Suspense>
  );
}

function CommunityChatPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { session } = useAuth();
  const selectedTopic = searchParams.get("topic");
  const [topics, setTopics] = useState<CommunityTopic[]>(FALLBACK_TOPICS);
  const [messages, setMessages] = useState<CommunityMessage[]>([]);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const messagesContainerRef = useRef<HTMLDivElement | null>(null);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);

  const wordCount = countWords(content);
  const isSendDisabled = wordCount === 0 || wordCount > MAX_MESSAGE_WORDS;
  const currentTopic = topics.find((t) => t.topic_id === selectedTopic);

  useEffect(() => {
    apiFetch<CommunityTopic[]>("/community/threads/")
      .then((apiTopics) => {
        const apiTopicsMap = new Map(apiTopics.map((t) => [t.topic_id, t]));
        const mergedTopics = FALLBACK_TOPICS.map((topic) =>
          apiTopicsMap.get(topic.topic_id) ?? topic
        );
        setTopics(mergedTopics);
      })
      .catch(() => setTopics(FALLBACK_TOPICS));
  }, []);

  useEffect(() => {
    if (!selectedTopic) {
      setMessages([]);
      setLoadError(null);
      return;
    }

    setLoadError(null);
    setLoading(true);
    apiFetch<CommunityThread>(`/community/threads/${selectedTopic}/`)
      .then((response) => {
        setMessages(response.messages);
        setTopics((current) =>
          current.map((t) => (t.topic_id === response.topic.topic_id ? response.topic : t))
        );
      })
      .catch(() => {
        setMessages([]);
      })
      .finally(() => setLoading(false));
  }, [selectedTopic]);

useEffect(() => {
    if (!session?.accessToken || !selectedTopic) {
      return;
    }
    const base = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
    const socket = new WebSocket(`${base}/ws/community/${selectedTopic}/?token=${session.accessToken}`);
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as {
        type: "message";
        id: string;
        sender_id: string;
        sender_role: string;
        sender_name?: string;
        sender_profile_photo?: string | null;
        content: string;
        created_at: string;
      };
      if (payload.type === "message") {
        const nextMessage: CommunityMessage = {
          id: payload.id,
          sender: payload.sender_id,
          sender_role: "corper",
          sender_name: payload.sender_name,
          sender_profile_photo: payload.sender_profile_photo,
          content: payload.content,
          created_at: payload.created_at
        };
        const isOwnMessage = payload.sender_id === session.user.id;
        setMessages((current) => {
          const optimisticMatch =
            payload.sender_id === session.user.id
              ? current.find(
                (message) => message.pending && message.sender === payload.sender_id && message.content === payload.content
                )
              : undefined;
          return upsertMessage(current, nextMessage, optimisticMatch?.id);
        });
        if (!isOwnMessage) {
          setTopics((current) =>
            current.map((t) =>
              t.topic_id === selectedTopic
                ? { ...t, message_count: (t.message_count ?? 0) + 1, unread_count: (t.unread_count ?? 0) + 1 }
                : t
            )
          );
        }
      }
    };
    return () => socket.close();
  }, [selectedTopic, session?.accessToken, session?.user.id]);

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) {
      return;
    }
    container.scrollTop = container.scrollHeight;
  }, [messages]);

  useEffect(() => {
    const composer = composerRef.current;
    if (!composer) {
      return;
    }

    composer.style.height = "0px";
    composer.style.height = `${Math.min(composer.scrollHeight, 160)}px`;
    composer.style.overflowY = composer.scrollHeight > 160 ? "auto" : "hidden";
  }, [content]);

  async function sendMessage() {
    if (!session) {
      return;
    }
    const nextContent = content.trim();
    if (!nextContent) {
      return;
    }
    if (countWords(nextContent) > MAX_MESSAGE_WORDS) {
      toast.error("Messages cannot be more than 100 words.");
      return;
    }

    const optimisticId = `temp:${crypto.randomUUID()}`;
    const optimisticMessage: CommunityMessage = {
      id: optimisticId,
      sender: session.user.id,
      sender_role: "corper",
      content: nextContent,
      created_at: new Date().toISOString(),
      pending: true,
    };

    setMessages((current) => [...current, optimisticMessage]);
    setTopics((current) =>
      current.map((t) =>
        t.topic_id === selectedTopic
          ? { ...t, message_count: (t.message_count ?? 0) + 1 }
          : t
      )
    );
    setContent("");

    try {
      await apiFetch<CommunityMessage>(`/community/threads/${selectedTopic}/messages/`, {
        method: "POST",
        body: JSON.stringify({ content: nextContent }),
      });
    } catch (error) {
      setMessages((current) => current.filter((m) => m.id !== optimisticId));
      setTopics((current) =>
        current.map((t) =>
          t.topic_id === selectedTopic
            ? { ...t, message_count: Math.max((t.message_count ?? 1) - 1, 0) }
            : t
        )
      );
      setContent(nextContent);
      toast.error(error instanceof Error ? error.message : "Unable to send message.");
    }
  }

  if (selectedTopic && !currentTopic) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <Card className="text-center">
          <h2 className="font-display text-2xl text-white">Topic not found</h2>
          <p className="mt-3 text-sm text-mist">The requested community topic does not exist.</p>
          <Link
            href="/corper/community"
            className="mt-5 inline-flex items-center justify-center rounded-full border border-white/15 bg-white/[0.08] px-5 py-2.5 text-sm font-semibold text-white transition duration-200 hover:border-lime/70 hover:bg-white/[0.14]"
          >
            Back to topics
          </Link>
        </Card>
      </main>
    );
  }

  if (selectedTopic && !loading && !loadError && !session) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <div className="rounded-full border border-white/10 bg-white/[0.08] px-5 py-3 text-sm text-mist backdrop-blur-xl">
          Loading community thread...
        </div>
      </main>
    );
  }

  if (!selectedTopic) {
    return (
      <main className="min-h-screen px-4 py-6 md:px-8">
        <div className="mx-auto max-w-[1480px]">
          <Link
            href="/corper/dashboard"
            className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.07] px-4 py-2 text-sm text-mist transition hover:border-lime/60 hover:bg-white/[0.12] hover:text-white"
          >
            Back to dashboard
          </Link>

          <section className="mt-8 rounded-[34px] border border-white/10 bg-white/[0.07] p-6 shadow-glow backdrop-blur-xl">
            <h1 className="font-display text-3xl text-white">Community Chat</h1>
            <p className="mt-2 text-base text-mist">
              Connect with fellow corpers, share experiences, and discuss topics related to NYSC.
            </p>

            <p className="mt-6 text-xs uppercase tracking-[0.26em] text-lime">Available Topics</p>

            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {topics.map((topic) => (
                <article
                  key={topic.topic_id}
                  className="group flex cursor-pointer flex-col rounded-[28px] border border-white/10 bg-white/[0.05] p-5 transition duration-300 hover:-translate-y-1 hover:border-lime/35"
                  onClick={() => router.push(`/corper/community?topic=${topic.topic_id}`)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      router.push(`/corper/community?topic=${topic.topic_id}`);
                    }
                  }}
                  role="link"
                  tabIndex={0}
                >
                  <h2 className="font-display text-lg text-lime">{topic.name}</h2>
                  <p className="mt-2 text-xs text-[#C3B091]">{topic.description}</p>
                  <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-[15px] text-white/58">
                    <span className="inline-block h-2 w-2 rounded-full bg-lime" />
                    <span>Total: {topic.message_count ?? 0}</span>
                    <span>Unread: {topic.unread_count ?? 0}</span>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>
      </main>
    );
  }

  const senderName = session?.user.email?.split("@")[0] || "You";

  return (
    <main className="min-h-screen px-4 py-6 md:px-8">
      <div className="mx-auto max-w-[1480px]">
        <Link
          href="/corper/community"
          className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.07] px-4 py-2 text-sm text-mist transition hover:border-lime/60 hover:bg-white/[0.12] hover:text-white"
        >
          Back to topics
        </Link>

        <section className="mt-6 rounded-[34px] border border-white/10 bg-white/[0.07] p-6 shadow-glow backdrop-blur-xl">
          <h1 className="font-display text-2xl text-white">{currentTopic?.name}</h1>
          <p className="mt-1 text-sm text-mist">{currentTopic?.description}</p>
        </section>

        <div className="mx-auto mt-6 flex w-full max-w-[50rem] flex-col gap-3">
          <Card className="overflow-hidden bg-white/[0.05] border-white/5 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-0 shadow-[0_20px_50px_rgba(4,21,15,0.16)] backdrop-blur-sm motion-safe:animate-[chat-panel-in_220ms_ease-out]">
            <div
              ref={messagesContainerRef}
              aria-live="polite"
              aria-label="Community messages"
              className="max-h-[56vh] overflow-y-auto px-4 py-4 sm:px-5"
            >
              <div className="flex flex-col gap-3">
                {messages.map((message) => {
                  const isOwnMessage = normalizeId(session?.user.id) === normalizeId(message.sender);
                  return (
                    <CommunityMessageBubble
                      key={message.id}
                      message={message}
                      isOwnMessage={isOwnMessage}
                    />
                  );
                })}
              </div>
            </div>
          </Card>

          <div className="rounded-[26px] border border-white/10 bg-white/[0.01] p-2 shadow-[0_16px_40px_rgba(4,21,15,0.14)] backdrop-blur-xl transition duration-200 focus-within:border-lime/35 focus-within:ring-2 focus-within:ring-lime/20 motion-reduce:animate-none motion-safe:animate-[chat-panel-in_260ms_ease-out]">
            <div className="flex items-end gap-2">
              <Textarea
                ref={composerRef}
                value={content}
                onChange={(event) => setContent(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void sendMessage();
                  }
                }}
                aria-label="Type a message"
                aria-describedby="chat-word-limit"
                className="min-h-[52px] max-h-40 resize-none whitespace-pre-wrap break-words border-0 bg-transparent px-3 py-3 leading-5 shadow-none [overflow-wrap:anywhere] focus:border-transparent focus:ring-0"
                placeholder="Share your experience..."
                rows={1}
                wrap="soft"
              />
              <Button
                className="h-11 shrink-0 px-4 text-sm shadow-[0_12px_28px_rgba(17,138,72,0.24)]"
                disabled={isSendDisabled}
                onClick={() => void sendMessage()}
              >
                Send
              </Button>
            </div>
            <div className="mt-2 flex items-center justify-end px-1 text-[11px]">
              <span id="chat-word-limit" className={wordCount > MAX_MESSAGE_WORDS ? "text-coral" : "text-white/58"}>
                {wordCount}/{MAX_MESSAGE_WORDS} words
              </span>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
