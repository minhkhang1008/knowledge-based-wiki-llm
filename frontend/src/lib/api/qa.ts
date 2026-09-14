import type { AskData, ChatMessage } from "@/types/api";
import { requestEnvelope } from "./client";

export function askQuestion(
  question: string,
  chatHistory: ChatMessage[],
  signal?: AbortSignal,
): Promise<AskData> {
  return requestEnvelope<AskData>("/api/qa/ask", {
    method: "POST",
    json: { question, chat_history: chatHistory },
    signal,
    timeoutMs: 120_000,
  });
}
