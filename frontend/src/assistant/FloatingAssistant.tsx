import { type MouseEvent, type PointerEvent, useRef, useState } from "react";

import type { AssistantChatResponse } from "../api/client";
import { askProjectAssistant } from "../api/client";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  citations?: AssistantChatResponse["citations"];
  modelProvider?: string;
};

export function FloatingAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [position, setPosition] = useState({ right: 0, bottom: 88 });
  const dragState = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    startRight: number;
    startBottom: number;
  } | null>(null);
  const movedDuringDrag = useRef(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: "我是项目助手，可以问我使用流程、数据导入、调查工作台、Agent 状态机、飞书回写和监控含义。"
    }
  ]);

  function startDragAt(pointerId: number, clientX: number, clientY: number) {
    dragState.current = {
      pointerId,
      startX: clientX,
      startY: clientY,
      startRight: position.right,
      startBottom: position.bottom
    };
    movedDuringDrag.current = false;
  }

  function startDrag(event: PointerEvent<HTMLButtonElement>) {
    startDragAt(event.pointerId, event.clientX, event.clientY);
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }

  function dragTo(pointerId: number, clientX: number, clientY: number) {
    if (!dragState.current || dragState.current.pointerId !== pointerId) {
      return;
    }
    const deltaX = clientX - dragState.current.startX;
    const deltaY = clientY - dragState.current.startY;
    if (Math.abs(deltaX) + Math.abs(deltaY) > 4) {
      movedDuringDrag.current = true;
    }
    const maxRight = Math.max(0, window.innerWidth - 96);
    const maxBottom = Math.max(0, window.innerHeight - 128);
    setPosition({
      right: clamp(dragState.current.startRight - deltaX, 0, maxRight),
      bottom: clamp(dragState.current.startBottom - deltaY, 0, maxBottom)
    });
  }

  function dragBot(event: PointerEvent<HTMLButtonElement>) {
    dragTo(event.pointerId, event.clientX, event.clientY);
  }

  function stopDrag(event: PointerEvent<HTMLButtonElement>) {
    if (dragState.current?.pointerId === event.pointerId) {
      dragState.current = null;
      event.currentTarget.releasePointerCapture?.(event.pointerId);
    }
  }

  function startMouseDrag(event: MouseEvent<HTMLButtonElement>) {
    startDragAt(-1, event.clientX, event.clientY);
  }

  function dragMouse(event: MouseEvent<HTMLButtonElement>) {
    dragTo(-1, event.clientX, event.clientY);
  }

  function stopMouseDrag() {
    if (dragState.current?.pointerId === -1) {
      dragState.current = null;
    }
  }

  async function submitQuestion() {
    const trimmed = question.trim();
    if (!trimmed || isLoading) {
      return;
    }
    setQuestion("");
    setMessages((current) => [...current, { role: "user", content: trimmed }]);
    setIsLoading(true);
    try {
      const response = await askProjectAssistant(trimmed);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.answer,
          citations: response.citations,
          modelProvider: response.model_provider
        }
      ]);
    } catch (caught) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: caught instanceof Error ? caught.message : "助手暂时无法回答，请稍后再试。"
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <aside
      className="floating-assistant"
      data-assistant-open={String(isOpen)}
      aria-label="项目助手"
      style={{ right: `${position.right}px`, bottom: `${position.bottom}px` }}
    >
      <button
        type="button"
        className="floating-assistant__bot"
        aria-label={isOpen ? "收起项目助手" : "唤醒项目助手"}
        onPointerDown={startDrag}
        onPointerMove={dragBot}
        onPointerUp={stopDrag}
        onPointerCancel={stopDrag}
        onMouseDown={startMouseDrag}
        onMouseMove={dragMouse}
        onMouseUp={stopMouseDrag}
        onMouseLeave={stopMouseDrag}
        onClick={() => {
          if (movedDuringDrag.current) {
            movedDuringDrag.current = false;
            return;
          }
          setIsOpen((current) => !current);
        }}
      >
        <span className="floating-assistant__antenna" />
        <span className="floating-assistant__head">
          <span className="floating-assistant__eye" />
          <span className="floating-assistant__eye" />
          <span className="floating-assistant__mouth" />
        </span>
        <span className="floating-assistant__body">AI</span>
        <span className="floating-assistant__wake">问我流程</span>
      </button>

      {isOpen ? (
        <section className="floating-assistant__panel" aria-label="项目助手对话">
          <header>
            <div>
              <p>RAG 项目助手</p>
              <h2>问我 Debug Agent 怎么用</h2>
            </div>
            <button type="button" aria-label="关闭项目助手" onClick={() => setIsOpen(false)}>
              收起
            </button>
          </header>
          <div className="floating-assistant__messages" aria-label="项目助手消息">
            {messages.map((message, index) => (
              <article className="floating-assistant__message" data-message-role={message.role} key={`${message.role}-${index}`}>
                <p>{message.content}</p>
                {message.modelProvider ? <small>回答来源：{message.modelProvider}</small> : null}
                {message.citations && message.citations.length > 0 ? (
                  <ul aria-label="知识来源">
                    {message.citations.map((citation) => (
                      <li key={`${citation.source}-${citation.title}`}>
                        {citation.title}｜{citation.source}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </article>
            ))}
            {isLoading ? <p className="floating-assistant__thinking">正在检索知识库并组织回答...</p> : null}
          </div>
          <form
            className="floating-assistant__composer"
            onSubmit={(event) => {
              event.preventDefault();
              void submitQuestion();
            }}
          >
            <label htmlFor="assistant-question">向项目助手提问</label>
            <textarea
              id="assistant-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="比如：我只有飞书链接该怎么开始？"
            />
            <button type="submit" disabled={isLoading || !question.trim()}>
              发送
            </button>
          </form>
        </section>
      ) : null}
    </aside>
  );
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}
