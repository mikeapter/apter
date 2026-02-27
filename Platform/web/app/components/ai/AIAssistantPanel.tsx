"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Sparkles, X, Send, Database } from "lucide-react";
import { chatStream, chatJSON, type AIResponse } from "../../lib/api/ai";
import { AIMessage } from "./AIMessage";
import { AIPromptCards } from "./AIPromptCards";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  structured?: AIResponse | null;
  isStreaming?: boolean;
};

let _msgCounter = 0;
function nextId() {
  return `msg_${Date.now()}_${++_msgCounter}`;
}

export function AIAssistantPanel() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [tickers, setTickers] = useState<string[]>([]);
  const [tickerInput, setTickerInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = useCallback(
    async (text?: string) => {
      const msg = (text ?? input).trim();
      if (!msg || sending) return;

      const userMsg: Message = { id: nextId(), role: "user", content: msg };
      const assistantMsgId = nextId();
      const assistantMsg: Message = {
        id: assistantMsgId,
        role: "assistant",
        content: "",
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setInput("");
      setSending(true);

      try {
        let serverMessageId = assistantMsgId;

        await chatStream(
          { message: msg, context: { tickers: tickers.length ? tickers : undefined } },
          {
            onStart(messageId) {
              serverMessageId = messageId;
            },
            onToken(token) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? { ...m, content: m.content + token }
                    : m,
                ),
              );
            },
            onReplace(json) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        content: json.summary,
                        structured: json,
                        isStreaming: false,
                        id: serverMessageId,
                      }
                    : m,
                ),
              );
            },
            onDone(messageId, fullText) {
              let structured: AIResponse | null = null;
              try {
                structured = JSON.parse(fullText) as AIResponse;
              } catch {
                // Not valid JSON -- leave as plain text
              }

              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        content: structured ? structured.summary : fullText,
                        structured,
                        isStreaming: false,
                        id: messageId,
                      }
                    : m,
                ),
              );
            },
            onError(error) {
              console.error("[Apter Intelligence] SSE error:", error?.message || error);
              chatJSON({ message: msg, context: { tickers: tickers.length ? tickers : undefined } })
                .then((json) => {
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMsgId
                        ? {
                            ...m,
                            content: json.summary,
                            structured: json,
                            isStreaming: false,
                            id: json.message_id || assistantMsgId,
                          }
                        : m,
                    ),
                  );
                })
                .catch((fallbackErr) => {
                  const errMsg = fallbackErr?.message || String(fallbackErr);
                  console.error("[Apter Intelligence] JSON fallback error:", errMsg);
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMsgId
                        ? {
                            ...m,
                            content: `Service error: ${errMsg.slice(0, 200)}`,
                            isStreaming: false,
                          }
                        : m,
                    ),
                  );
                });
            },
          },
        );
      } catch {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: "An error occurred. Please try again.",
                  isStreaming: false,
                }
              : m,
          ),
        );
      } finally {
        setSending(false);
      }
    },
    [input, sending, tickers],
  );

  function addTicker() {
    const t = tickerInput.trim().toUpperCase();
    if (t && !tickers.includes(t)) {
      setTickers((prev) => [...prev, t]);
    }
    setTickerInput("");
  }

  function removeTicker(t: string) {
    setTickers((prev) => prev.filter((x) => x !== t));
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-16 right-6 z-40 h-12 w-12 rounded-full border border-border bg-panel shadow-lg flex items-center justify-center hover:bg-muted transition-colors"
        title="Open Apter Intelligence"
      >
        <Sparkles size={20} />
      </button>
    );
  }

  return (
    <div className="fixed bottom-16 right-6 z-40 w-[420px] max-h-[75vh] rounded-md border border-border bg-card shadow-xl flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-panel">
        <div className="flex items-center gap-2">
          <Sparkles size={14} />
          <div>
            <span className="text-sm font-semibold">Apter Intelligence</span>
            <span className="block text-[9px] text-muted-foreground leading-tight">Institutional-grade analysis</span>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-muted-foreground hover:text-foreground"
        >
          <X size={16} />
        </button>
      </div>

      {/* Context selector (tickers) */}
      <div className="px-3 py-1.5 border-b border-border flex items-center gap-1.5 flex-wrap">
        <Database size={10} className="text-muted-foreground shrink-0" />
        {tickers.map((t) => (
          <span
            key={t}
            className="text-[10px] bg-panel border border-border rounded px-1.5 py-0.5 font-mono flex items-center gap-1"
          >
            {t}
            <button
              type="button"
              onClick={() => removeTicker(t)}
              className="text-muted-foreground hover:text-foreground"
            >
              <X size={8} />
            </button>
          </span>
        ))}
        <input
          type="text"
          value={tickerInput}
          onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addTicker();
            }
          }}
          placeholder={tickers.length ? "Add ticker..." : "Add tickers for context..."}
          className="flex-1 min-w-[80px] h-5 bg-transparent text-[10px] outline-none placeholder:text-muted-foreground/60"
        />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto p-3 space-y-3 min-h-[200px] max-h-[400px]">
        {messages.length === 0 && (
          <div className="space-y-3">
            <div className="text-center text-muted-foreground text-sm py-4">
              <Sparkles size={24} className="mx-auto mb-2 opacity-40" />
              <p>Institutional-grade financial analysis. Ask about any stock, market conditions, or financial metric.</p>
            </div>
            <AIPromptCards onSelect={(prompt) => handleSubmit(prompt)} />
          </div>
        )}
        {messages.map((msg) => (
          <AIMessage
            key={msg.id}
            role={msg.role}
            content={msg.content}
            structured={msg.structured}
            messageId={msg.role === "assistant" ? msg.id : undefined}
            isStreaming={msg.isStreaming}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSubmit();
        }}
        className="border-t border-border px-3 py-2 flex gap-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          disabled={sending}
          className="flex-1 h-8 rounded-md border border-border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring/40 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="h-8 w-8 rounded-md border border-border flex items-center justify-center hover:bg-muted disabled:opacity-30"
        >
          <Send size={14} />
        </button>
      </form>
    </div>
  );
}
