"use client";

import {
  Fragment,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { askQuestion } from "@/lib/api/qa";
import { errorMessage } from "@/lib/api/errors";
import type { SourceChunk } from "@/types/api";
import {
  AlertIcon,
  BotIcon,
  DocumentsIcon,
  SendIcon,
  UserIcon,
} from "@/components/ui/Icons";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceChunk[];
  noContext?: boolean;
}

const MIN_QUESTION_LENGTH = 5;
const MAX_LOCAL_MESSAGES = 50;
const HISTORY_MESSAGES = 12;

function CitedAnswer({ text, messageId }: { text: string; messageId: string }) {
  const parts = text.split(/(\[S\d+])/g);
  return parts.map((part, index) => {
    const match = part.match(/^\[S(\d+)]$/);
    if (!match) return <Fragment key={`${part}-${index}`}>{part}</Fragment>;
    const sourceIndex = Number(match[1]) - 1;
    return (
      <button
        key={`${part}-${index}`}
        type="button"
        className="mx-0.5 inline-flex rounded-md border border-line bg-hover px-1.5 py-0.5 font-mono text-xs font-semibold text-ink hover:bg-elevated"
        aria-label={`Jump to source ${sourceIndex + 1}`}
        onClick={() =>
          document
            .getElementById(`source-${messageId}-${sourceIndex}`)
            ?.scrollIntoView({ behavior: "smooth", block: "center" })
        }
      >
        {part}
      </button>
    );
  });
}

export default function AskPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const requestRef = useRef<AbortController | null>(null);
  const messageSequence = useRef(0);

  const trimmedLength = inputValue.trim().length;
  const isTooShort = trimmedLength > 0 && trimmedLength < MIN_QUESTION_LENGTH;

  useEffect(() => () => requestRef.current?.abort(), []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  }, [inputValue]);

  function nextMessageId(role: Message["role"]) {
    messageSequence.current += 1;
    return `${role}-${messageSequence.current}`;
  }

  async function handleSubmit(event?: FormEvent) {
    event?.preventDefault();
    const question = inputValue.trim();
    setError("");
    if (question.length < MIN_QUESTION_LENGTH) {
      setError(`Enter at least ${MIN_QUESTION_LENGTH} characters.`);
      return;
    }

    const userMessage: Message = {
      id: nextMessageId("user"),
      role: "user",
      content: question,
    };
    const history = messages.slice(-HISTORY_MESSAGES).map((message) => ({
      role: message.role,
      content: message.content,
    }));
    const controller = new AbortController();
    requestRef.current?.abort();
    requestRef.current = controller;

    setMessages((current) => [...current, userMessage].slice(-MAX_LOCAL_MESSAGES));
    setInputValue("");
    setIsLoading(true);
    try {
      const result = await askQuestion(question, history, controller.signal);
      const assistantMessage: Message = {
        id: nextMessageId("assistant"),
        role: "assistant",
        content: result.answer,
        sources: result.sources,
        noContext: result.no_answer_reason === "insufficient_context",
      };
      setMessages((current) => [...current, assistantMessage].slice(-MAX_LOCAL_MESSAGES));
    } catch (cause) {
      if (controller.signal.aborted) return;
      setInputValue(question);
      setMessages((current) => current.filter((message) => message.id !== userMessage.id));
      setError(`${errorMessage(cause)} Your question was restored so you can retry.`);
    } finally {
      if (requestRef.current === controller) setIsLoading(false);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      if (!isLoading) void handleSubmit();
    }
  }

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-3.5rem)] w-full max-w-5xl flex-col px-4 py-6 sm:px-6 lg:py-8">
      <header className="border-b border-line pb-5">
        <h1 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">Ask</h1>
        <p className="mt-1.5 max-w-2xl text-sm leading-6 text-muted">
          Ask a grounded question. Answers without valid source citations are rejected automatically.
        </p>
      </header>

      <section className="flex min-h-0 flex-1 flex-col" aria-label="Knowledge base conversation">
        <div className="flex-1 space-y-6 overflow-y-auto py-6" aria-live="polite" aria-busy={isLoading}>
          {messages.length === 0 ? (
            <div className="flex min-h-80 flex-col items-center justify-center rounded-xl border border-dashed border-line px-6 text-center">
              <BotIcon className="h-10 w-10 text-faint" aria-hidden="true" />
              <h2 className="mt-4 text-base font-semibold text-ink">Ask your documents</h2>
              <p className="mt-1 max-w-md text-sm leading-6 text-muted">
                Questions work best when they name the topic, policy, product, or procedure you need.
              </p>
            </div>
          ) : (
            messages.map((message) => (
              <article key={message.id} className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                {message.role === "assistant" ? (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-line bg-surface text-muted">
                    <BotIcon className="h-4 w-4" aria-hidden="true" />
                  </div>
                ) : null}
                <div className={`min-w-0 max-w-[88%] sm:max-w-[78%] ${message.role === "user" ? "text-right" : "text-left"}`}>
                  <div className={`inline-block rounded-xl border px-4 py-3 text-left text-sm leading-6 ${message.role === "user" ? "border-ink bg-ink text-canvas" : "border-line bg-surface text-ink"}`}>
                    {message.noContext ? (
                      <div className="mb-2 flex items-center gap-2 text-sm font-medium text-warning">
                        <AlertIcon className="h-4 w-4" aria-hidden="true" />
                        No relevant context found
                      </div>
                    ) : null}
                    <div className="whitespace-pre-wrap">
                      {message.role === "assistant" ? <CitedAnswer text={message.content} messageId={message.id} /> : message.content}
                    </div>
                  </div>

                  {message.sources && message.sources.length > 0 ? (
                    <ol className="mt-3 grid gap-2 text-left sm:grid-cols-2">
                      {message.sources.map((source, index) => (
                        <li id={`source-${message.id}-${index}`} key={`${source.article_id ?? "unknown"}-${index}`} className="rounded-lg border border-line bg-elevated p-3 text-xs">
                          <div className="flex items-center gap-2 font-medium text-ink">
                            <span className="font-mono">S{index + 1}</span>
                            <DocumentsIcon className="h-3.5 w-3.5 text-muted" aria-hidden="true" />
                            <span className="truncate">{source.source_file ?? "Unknown source"}</span>
                            {source.page_number !== null ? <span className="ml-auto shrink-0 text-muted">p. {source.page_number}</span> : null}
                          </div>
                          <p className="mt-2 line-clamp-4 border-l-2 border-line pl-2 leading-5 text-muted">{source.text}</p>
                        </li>
                      ))}
                    </ol>
                  ) : null}
                </div>
                {message.role === "user" ? (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-line bg-surface text-muted">
                    <UserIcon className="h-4 w-4" aria-hidden="true" />
                  </div>
                ) : null}
              </article>
            ))
          )}

          {isLoading ? (
            <div className="flex gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-line bg-surface text-muted">
                <BotIcon className="h-4 w-4" aria-hidden="true" />
              </div>
              <div className="w-48 space-y-2 rounded-xl border border-line bg-surface p-4" aria-label="Generating answer">
                <div className="h-2.5 animate-pulse rounded bg-hover" />
                <div className="h-2.5 w-2/3 animate-pulse rounded bg-hover" />
              </div>
            </div>
          ) : null}
          <div ref={messagesEndRef} />
        </div>

        <div className="sticky bottom-0 border-t border-line bg-canvas py-4">
          {error ? (
            <p id="ask-error" role="alert" className="mb-3 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
              {error}
            </p>
          ) : null}
          <form onSubmit={handleSubmit} className="flex items-end gap-2">
            <div className="min-w-0 flex-1">
              <label htmlFor="question" className="mb-1.5 block text-sm font-medium text-ink">Question</label>
              <textarea
                id="question"
                ref={textareaRef}
                value={inputValue}
                onChange={(event) => {
                  setInputValue(event.target.value);
                  setError("");
                }}
                onKeyDown={handleKeyDown}
                disabled={isLoading}
                rows={1}
                placeholder="Ask about an indexed document"
                aria-describedby={error ? "ask-error question-help" : "question-help"}
                className={`max-h-[200px] w-full resize-none rounded-xl border bg-surface px-4 py-3 text-sm text-ink placeholder:text-faint disabled:cursor-not-allowed disabled:opacity-60 ${isTooShort ? "border-warning" : "border-line"}`}
              />
              <div id="question-help" className="mt-1 flex justify-between px-1 text-xs text-muted">
                <span>Enter to send, Shift+Enter for a new line</span>
                <span>{trimmedLength}/{MIN_QUESTION_LENGTH} min</span>
              </div>
            </div>
            <button
              type="submit"
              disabled={isLoading || trimmedLength < MIN_QUESTION_LENGTH}
              className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-ink text-canvas transition-opacity hover:opacity-90 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
              aria-label="Send question"
            >
              <SendIcon className="h-4 w-4" aria-hidden="true" />
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
