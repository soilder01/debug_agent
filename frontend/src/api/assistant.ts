import { buildHttpErrorMessage } from "./http";
import type {
  AssistantChatResponse
} from "./types";

export async function askProjectAssistant(question: string): Promise<AssistantChatResponse> {
  const response = await fetch("/api/assistant/chat", {
    body: JSON.stringify({ question }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(await buildHttpErrorMessage("询问项目助手失败", response));
  }
  return (await response.json()) as AssistantChatResponse;
}
