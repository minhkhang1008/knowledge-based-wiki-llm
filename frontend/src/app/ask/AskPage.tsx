"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, User, Bot, AlertCircle, FileText } from "lucide-react";

// --- Types ---
type Source = {
  text: string;
  article_id: string;
  source_file: string;
  page_number: number | null;
  distance: number;
};

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  noContext?: boolean;
};

const MIN_QUESTION_LENGTH = 5;

// --- Helper Functions ---
// Parses [S1], [S2] into stylized citation badges
const renderTextWithCitations = (text: string) => {
  const parts = text.split(/(\[S\d+\])/g);
  return parts.map((part, index) => {
    if (part.match(/\[S\d+\]/)) {
      return (
        <span
          key={index}
          className="inline-flex items-center justify-center px-1.5 py-0.5 mx-0.5 text-xs font-semibold text-blue-300 bg-blue-500/20 border border-blue-500/30 rounded cursor-help"
          title="See source below"
        >
          {part}
        </span>
      );
    }
    return <React.Fragment key={index}>{part}</React.Fragment>;
  });
};

export default function AskPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const trimmedLength = inputValue.trim().length;
  const isTooShort = trimmedLength > 0 && trimmedLength < MIN_QUESTION_LENGTH;

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [inputValue]);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setError(null);
    const trimmedInput = inputValue.trim();

    // Minimum five-character question requirement
    if (trimmedInput.length < MIN_QUESTION_LENGTH) {
      setError(`Please enter a question with at least ${MIN_QUESTION_LENGTH} characters.`);
      return;
    }

    const newUserMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: trimmedInput,
    };

    // Prepare API history format
    const chatHistory = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    setMessages((prev) => [...prev, newUserMessage]);
    setInputValue("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/qa/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: trimmedInput,
          chat_history: chatHistory,
        }),
      });

      if (!response.ok) {
        // Distinguish server-side errors (e.g. 4xx/5xx) from network failures
        throw new Error(`server_status_${response.status}`);
      }

      const json = await response.json();

      // Handle potential API envelope `{"success": true, "data": {...}}`
      // or direct response fallback
      const payload = json.data ? json.data : json;
      const { answer, sources, no_answer_reason } = payload;

      const newAssistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: answer,
        sources: sources || [],
        noContext: no_answer_reason === "insufficient_context",
      };

      setMessages((prev) => [...prev, newAssistantMessage]);
    } catch (err) {
      // Restore user input on failure so it can be retried
      setInputValue(trimmedInput);
      setMessages((prev) => prev.filter((m) => m.id !== newUserMessage.id));

      const message = err instanceof Error ? err.message : "";
      if (message.startsWith("server_status_")) {
        const status = message.replace("server_status_", "");
        setError(`Server error (${status}). Your question has been kept so you can retry.`);
      } else {
        setError("Failed to connect to the server. Your question has been kept so you can retry.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Ignore Enter while an IME composition is in progress (e.g. some
    // Vietnamese/CJK input methods), so it doesn't submit mid-composition.
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      if (!isLoading) handleSubmit();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-black text-white">
      {/* Header */}
      <header className="flex items-center justify-between p-4 bg-black border-b border-white/10">
        <h1 className="text-xl font-semibold text-white">Knowledge Base QA</h1>
      </header>

      {/* Chat Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
            <Bot size={48} className="text-white/70" />
            <p className="text-lg font-medium text-white">How can I help you today?</p>
            <p className="text-sm max-w-md text-white/60">
              Ask questions about your uploaded documents. I will provide answers with exact citations and source references.
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-4 max-w-4xl mx-auto ${
                message.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {/* Assistant Avatar */}
              {message.role === "assistant" && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-white">
                  <Bot size={18} />
                </div>
              )}

              {/* Message Content */}
              <div
                className={`flex flex-col space-y-2 max-w-[85%] sm:max-w-[75%] ${
                  message.role === "user" ? "items-end" : "items-start"
                }`}
              >
                <div
                  className={`px-4 py-3 rounded-2xl border ${
                    message.role === "user"
                      ? "bg-white text-black border-white rounded-br-none"
                      : "bg-white/5 text-white border-white/10 rounded-bl-none"
                  }`}
                >
                  {/* Context Missing Warning */}
                  {message.noContext && (
                    <div className="flex items-center gap-2 mb-2 text-amber-300 font-medium text-sm bg-amber-500/10 border border-amber-500/20 p-2 rounded">
                      <AlertCircle size={16} />
                      Insufficient Context
                    </div>
                  )}

                  <div className="whitespace-pre-wrap leading-relaxed">
                    {message.role === "assistant"
                      ? renderTextWithCitations(message.content)
                      : message.content}
                  </div>
                </div>

                {/* Sources List */}
                {message.sources && message.sources.length > 0 && (
                  <div className="w-full mt-2 space-y-2">
                    <p className="text-xs font-semibold text-white/50 uppercase tracking-wider ml-1">
                      Sources
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {message.sources.map((source, idx) => (
                        <div
                          key={idx}
                          className="flex flex-col p-3 bg-white/5 border border-white/10 rounded-lg text-sm"
                        >
                          <div className="flex items-start gap-2 mb-1.5 font-medium text-white/80">
                            <span className="flex-shrink-0 bg-blue-500/20 text-blue-300 border border-blue-500/30 px-1.5 py-0.5 rounded text-xs">
                              S{idx + 1}
                            </span>
                            <span className="flex items-center gap-1 truncate text-xs text-white/70">
                              <FileText size={14} className="flex-shrink-0" />
                              {source.source_file}
                              {source.page_number && ` (p. ${source.page_number})`}
                            </span>
                          </div>
                          <p className="text-white/50 line-clamp-3 text-xs italic border-l-2 border-white/20 pl-2">
                            &quot;{source.text}&quot;
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* User Avatar */}
              {message.role === "user" && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-white">
                  <User size={18} />
                </div>
              )}
            </div>
          ))
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex gap-4 max-w-4xl mx-auto">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-white">
              <Bot size={18} />
            </div>
            <div className="bg-white/5 border border-white/10 px-4 py-3 rounded-2xl rounded-bl-none flex items-center gap-2">
              <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
              <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
              <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce"></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Error Banner */}
      {error && (
        <div className="max-w-4xl mx-auto w-full px-4 sm:px-6">
          <div className="flex items-center gap-2 mb-2 px-3 py-2 bg-red-500/10 border border-red-500/30 text-red-300 text-sm rounded-lg">
            <AlertCircle size={16} className="flex-shrink-0" />
            {error}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="p-4 bg-black border-t border-white/10">
        <form
          onSubmit={handleSubmit}
          className="max-w-4xl mx-auto flex items-end gap-2"
        >
          <div className="flex-1 flex flex-col gap-1">
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              rows={1}
              placeholder="Ask a question about your documents..."
              className={`w-full resize-none rounded-xl border bg-white/5 text-white placeholder-white/40 px-4 py-3 text-sm focus:outline-none focus:ring-2 disabled:opacity-60 disabled:cursor-not-allowed max-h-[200px] ${
                isTooShort
                  ? "border-amber-500/50 focus:ring-amber-500/50"
                  : "border-white/15 focus:ring-white/30"
              }`}
            />
            {/* Minimum length hint */}
            <div className="flex items-center justify-between px-1">
              <span className={`text-xs ${isTooShort ? "text-amber-300" : "text-white/40"}`}>
                Minimum {MIN_QUESTION_LENGTH} characters
              </span>
              {trimmedLength > 0 && (
                <span className={`text-xs ${isTooShort ? "text-amber-300" : "text-white/40"}`}>
                  {trimmedLength}/{MIN_QUESTION_LENGTH}
                </span>
              )}
            </div>
          </div>
          <button
            type="submit"
            disabled={isLoading || trimmedLength === 0}
            className="flex-shrink-0 w-11 h-11 rounded-xl bg-white text-black flex items-center justify-center hover:bg-white/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            aria-label="Send question"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}