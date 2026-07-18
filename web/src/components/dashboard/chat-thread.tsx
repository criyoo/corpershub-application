"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/components/providers/auth-provider";
import { apiFetch } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/media";
import { getBillingPathForRole, isPaidAccessRequiredMessage } from "@/lib/subscriptions";

type Message = {
  id: string;
  sender: string;
  sender_role: string;
  content: string;
  created_at: string;
  pending?: boolean;
};

type MessageResponse = {
  results: Message[];
};

const MAX_MESSAGE_WORDS = 100;

type ParticipantLabels = {
  company: string;
  corper: string;
};

type ParticipantNames = {
  company: string;
  corper: string;
};

type ParticipantImages = {
  company: string | null;
  corper: string | null;
};

type ConversationDetail = {
  participant_labels: ParticipantLabels;
  participant_names: ParticipantNames;
  participant_images: ParticipantImages;
};

type WebSocketPayload =
  | {
      type: "message";
      id: string;
      sender_id: string;
      sender_role: string;
      content: string;
      created_at: string;
    }
  | {
      type: "typing";
      conversation_id: string;
      sender_id: string;
    };

function upsertMessage(messages: Message[], nextMessage: Message, options?: { replaceId?: string }) {
  const withoutDuplicate = messages.filter((message) => message.id !== nextMessage.id);
  const targetIndex =
    options?.replaceId !== undefined ? withoutDuplicate.findIndex((message) => message.id === options.replaceId) : -1;

  if (targetIndex >= 0) {
    const updated = [...withoutDuplicate];
    updated[targetIndex] = nextMessage;
    return updated;
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

function getInitials(value: string) {
  const parts = value
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);

  if (!parts.length) {
    return "NA";
  }

  return parts.map((part) => part.charAt(0).toUpperCase()).join("");
}

export function ChatThread({
  conversationId,
  onConversationStateChange,
}: {
  conversationId: string;
  onConversationStateChange?: () => void | Promise<void>;
}) {
  const { session } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [content, setContent] = useState("");
  const [participantLabels, setParticipantLabels] = useState<ParticipantLabels>({
    company: "Company",
    corper: "Corper"
  });
  const [participantNames, setParticipantNames] = useState<ParticipantNames>({
    company: "Company",
    corper: "Corper"
  });
  const [participantImages, setParticipantImages] = useState<ParticipantImages>({
    company: null,
    corper: null
  });
  const [loadError, setLoadError] = useState<string | null>(null);
  const messagesContainerRef = useRef<HTMLDivElement | null>(null);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);
  const wordCount = countWords(content);
  const isSendDisabled = wordCount === 0 || wordCount > MAX_MESSAGE_WORDS;

  async function syncConversationReadState() {
    try {
      await apiFetch<{ unread_count: number }>(`/chat/conversations/${conversationId}/mark-read/`, {
        method: "POST",
      });
      await onConversationStateChange?.();
    } catch {
      // Ignore best-effort read sync failures so the chat thread stays usable.
    }
  }

  useEffect(() => {
    setLoadError(null);
    void apiFetch<MessageResponse>(`/chat/conversations/${conversationId}/messages/`)
      .then(async (response) => {
        setMessages(response.results);
        await onConversationStateChange?.();
      })
      .catch((error) => {
        setLoadError(error instanceof Error ? error.message : "Unable to load messages.");
      });
  }, [conversationId, onConversationStateChange]);

  useEffect(() => {
    let cancelled = false;

    void apiFetch<ConversationDetail>(`/chat/conversations/${conversationId}/`)
      .then((response) => {
        if (cancelled) {
          return;
        }
        setParticipantLabels({
          company: response.participant_labels.company || "Company",
          corper: response.participant_labels.corper || "Corper"
        });
        setParticipantNames({
          company: response.participant_names.company || "Company",
          corper: response.participant_names.corper || "Corper"
        });
        setParticipantImages({
          company: response.participant_images.company,
          corper: response.participant_images.corper
        });
      })
      .catch(() => undefined);

    return () => {
      cancelled = true;
    };
  }, [conversationId]);

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

  useEffect(() => {
    if (!session) {
      return;
    }
    const base = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
    const socket = new WebSocket(`${base}/ws/chat/${conversationId}/?token=${session.accessToken}`);
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as WebSocketPayload;
      if (payload.type === "message") {
        const nextMessage = {
          id: payload.id,
          sender: payload.sender_id,
          sender_role: payload.sender_role,
          content: payload.content,
          created_at: payload.created_at
        };
        setMessages((current) => {
          const optimisticMatch =
            payload.sender_id === session.user.id
              ? current.find(
                  (message) => message.pending && message.sender === payload.sender_id && message.content === payload.content
                )
              : undefined;
          return upsertMessage(current, nextMessage, { replaceId: optimisticMatch?.id });
        });
        if (payload.sender_id !== session.user.id) {
          void syncConversationReadState();
        } else {
          void onConversationStateChange?.();
        }
      }
    };
    return () => socket.close();
  }, [conversationId, onConversationStateChange, session]);

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
    const optimisticMessage = {
      id: optimisticId,
      sender: session.user.id,
      sender_role: session.user.role,
      content: nextContent,
      created_at: new Date().toISOString(),
      pending: true
    };

    setMessages((current) => [...current, optimisticMessage]);
    setContent("");

    try {
      const response = await apiFetch<Message>(`/chat/conversations/${conversationId}/messages/`, {
        method: "POST",
        body: JSON.stringify({ content: nextContent })
      });
      setMessages((current) => upsertMessage(current, response, { replaceId: optimisticId }));
      await onConversationStateChange?.();
    } catch (error) {
      setMessages((current) => current.filter((message) => message.id !== optimisticId));
      setContent(nextContent);
      toast.error(error instanceof Error ? error.message : "Unable to send message.");
    }
  }

  if (loadError) {
    return (
      <Card className="border-coral/30 bg-coral/10">
        <h2 className="font-display text-2xl text-white">Unable to load conversation</h2>
        <p className="mt-3 text-sm text-mist">{loadError}</p>
        {session?.user.role === "corper" && isPaidAccessRequiredMessage(loadError) ? (
          <Link
            href={getBillingPathForRole("corper")}
            className="mt-5 inline-flex items-center justify-center rounded-full border border-lime/30 bg-lime/10 px-5 py-2.5 text-sm font-semibold text-[#E6D28C] transition duration-200 hover:border-lime/60 hover:bg-lime/15 hover:text-[#E6D28C]"
          >
            Upgrade now
          </Link>
        ) : null}
      </Card>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-[50rem] flex-col gap-3">
      <Card className="overflow-hidden bg-white/[0.05] border-white/5 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-0 shadow-[0_20px_50px_rgba(4,21,15,0.16)] backdrop-blur-sm motion-safe:animate-[chat-panel-in_220ms_ease-out]">
        <div
          ref={messagesContainerRef}
          aria-live="polite"
          aria-label="Conversation messages"
          className="max-h-[56vh] overflow-y-auto px-4 py-4 sm:px-5"
        >
          <div className="flex flex-col gap-3">
            {messages.map((message) => {
              const isOwnMessage = session?.user.id === message.sender;
              const isCompanyMessage = message.sender_role === "company";
              const senderLabel = isCompanyMessage ? participantLabels.company : participantLabels.corper;
              const senderName = isCompanyMessage ? participantNames.company : participantNames.corper;
              const senderImageUrl = resolveMediaUrl(isCompanyMessage ? participantImages.company : participantImages.corper);

              return (
                <div
                  key={message.id}
                  className={`flex ${isOwnMessage ? "justify-end" : "justify-start"} ${
                    message.pending ? "opacity-60" : ""
                  } motion-reduce:animate-none motion-safe:animate-[chat-bubble-in_180ms_ease-out]`}
                >
                  <div className={`relative max-w-[15.5rem] ${isOwnMessage ? "items-end" : "items-start"} flex flex-col`}>
                    <div className={`mb-1 flex items-center gap-2 px-1 ${isOwnMessage ? "flex-row-reverse" : ""}`}>
                      <div className="h-7 w-7 shrink-0 overflow-hidden rounded-full border border-white/10 bg-white/10">
                        {senderImageUrl ? (
                          <img src={senderImageUrl} alt={senderName} className="h-full w-full object-cover" />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center bg-[#0F5A3A]/70 text-[10px] font-semibold uppercase tracking-[0.12em] text-white">
                            {getInitials(senderLabel)}
                          </div>
                        )}
                      </div>
                      <span className="max-w-[11.5rem] truncate text-[11px] font-medium tracking-[0.14em] text-white/58 uppercase">
                        {senderName}
                      </span>
                    </div>
                    <div
                      className={`relative z-10 w-fit rounded-[22px] border px-3.5 py-2.5 shadow-[0_12px_26px_rgba(4,21,15,0.1)] ${
                        isCompanyMessage
                          ? "border-[#0F5A3A]/18 bg-white text-[#0B3223]"
                          : "border-[#0F5A3A]/80 bg-[#0F5A3A] text-white"
                      }`}
                    >
                      <p className="break-words text-[13px] leading-5">
                        {chunkMessageContent(message.content).map((line, index) => (
                          <span key={`${message.id}-line-${index}`} className="block">
                            {line}
                          </span>
                        ))}
                      </p>
                      <p className={`mt-2 text-[11px] ${isCompanyMessage ? "text-[#2E5D48]/75" : "text-white/72"}`}>
                        {new Date(message.created_at).toLocaleString()}
                      </p>
                      <span
                        aria-hidden="true"
                        className={`absolute -bottom-1.5 h-3 w-3 rotate-45 border ${
                          isOwnMessage ? "right-5 border-l-0 border-t-0" : "left-5 border-r-0 border-t-0"
                        } ${isCompanyMessage ? "border-[#0F5A3A]/18 bg-white" : "border-[#0F5A3A]/80 bg-[#0F5A3A]"}`}
                      />
                    </div>
                  </div>
                </div>
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
            placeholder="Type your message"
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
  );
}
