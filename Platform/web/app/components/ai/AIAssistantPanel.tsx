"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Sparkles, X, Send, Database, RefreshCw, AlertCircle, Shield } from "lucide-react";
import { chatStream, chatJSON, type AIResponse } from "../../lib/api/ai";
import {
  askApterIntelligence,
  type ApterIntelligenceResponse,
  type ApterIntelligenceAnswer,
} from "../../lib/apterIntelligence";
import { AIMessage } from "./AIMessage";
import { AIPromptCards } from "./AIPromptCards";

// Feature flag: set NEXT_PUBLIC_APTER_INTELLIGENCE_V2=true to use the new endpoint
const USE_V2 = process.env.NEXT_PUBLIC_APTER_INTELLIGENCE_V2 === "true";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  structured?: AIResponse | null;
  v2Response?: ApterIntelligenceAnswer | null;
  dataQuality?: "live" | "partial" | "unavailable";
  isStreaming?: boolean;
  isError?: boolean;
};

let _msgCounter = 0;
function nextId() {
  return `msg_${Date.now()}_${++_msgCounter}`;
}

/** Map V2 answer shape to the existing AIResponse shape for AIMessage rendering */
function v2ToLegacy(answer: ApterIntelligenceAnswer): AIResponse {
  return {
    summary: answer.summary,
    data_used: [...answer.data_used, ...answer.data_sources],
    explanation: answer.explanation,
    watchlist_items: answer.what_to_watch,
    risk_flags: answer.risks,
    checklist: answer.key_drivers,
    disclaimer: answer.disclaimer,
    citations: answer.data_sources,
    scenarios: null,
    comparisons: null,
  };
}

export function AIAssistantPanel() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [tickers, setTickers] = useState<string[]>([]);
  const [tickerInput, setTickerInput] = useState("");
  const [lastError, setLastError] = useState<{
    question: string;
    tickers: string[];
  } | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── V2 handler (Apter Intelligence endpoint) ──
  const handleSubmitV2 = useCallback(
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
      setLastError(null);

      try {
        const resp: ApterIntelligenceResponse = await askApterIntelligence(
          msg,
          tickers,
        );

        const structured = v2ToLegacy(resp.answer);

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: resp.answer.summary,
                  structured,
                  v2Response: resp.answer,
                  dataQuality: resp.meta.data_quality,
                  isStreaming: false,
                  id: resp.meta.request_id || assistantMsgId,
                }
              : m,
          ),
        );
      } catch (err) {
        const errMsg =
          err instanceof Error ? err.message : String(err);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: `Error: ${errMsg.slice(0, 300)}`,
                  isStreaming: false,
                  isError: true,
                }
              : m,
          ),
        );
        setLastError({ question: msg, tickers: [...tickers] });
      } finally {
        setSending(false);
      }
    },
    [input, sending, tickers],
  );

  // ── V1 handler (legacy SSE streaming endpoint) ──
  const handleSubmitV1 = useCallback(
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
                // Not valid JSON — leave as plain text
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
              console.error("[AI Chat] SSE error:", error?.message || error);
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
                  console.error("[AI Chat] JSON fallback error:", errMsg);
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMsgId
                        ? {
                            ...m,
                            content: `AI service error: ${errMsg.slice(0, 200)}`,
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

  const handleSubmit = USE_V2 ? handleSubmitV2 : handleSubmitV1;

  function handleRetry() {
    if (lastError) {
      handleSubmitV2(lastError.question);
    }
  }

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
          <span className="text-sm font-semibold">
            {USE_V2 ? "Apter Intelligence" : "Apter AI"}
          </span>
          {USE_V2 && (
            <span className="text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded px-1 py-0.5 font-mono">
              LIVE
            </span>
          )}
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
              <p>
                {USE_V2
                  ? "Ask about any stock or market condition \u2014 I\u2019ll pull live data and provide institutional-grade analysis."
                  : "Ask about any stock, market conditions, or financial metric \u2014 I\u2019ll pull the data and break it down."}
              </p>
            </div>
            <AIPromptCards onSelect={(prompt) => handleSubmit(prompt)} />
          </div>
        )}
        {messages.map((msg) => (
          <div key={msg.id}>
            {/* Data quality badge for V2 responses */}
            {USE_V2 && msg.role === "assistant" && msg.dataQuality && !msg.isStreaming && !msg.isError && (
              <div className="flex items-center gap-1.5 mb-1">
                <span
                  className={`text-[9px] font-mono rounded px-1.5 py-0.5 border ${
                    msg.dataQuality === "live"
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      : msg.dataQuality === "partial"
                        ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                        : "bg-red-500/10 text-red-400 border-red-500/20"
                  }`}
                >
                  {msg.dataQuality === "live"
                    ? "LIVE DATA"
                    : msg.dataQuality === "partial"
                      ? "PARTIAL DATA"
                      : "DATA UNAVAILABLE"}
                </span>
              </div>
            )}

            {/* Error with retry */}
            {msg.isError && USE_V2 ? (
              <div className="flex justify-start">
                <div className="max-w-[95%] rounded-md bg-red-500/5 border border-red-500/20 px-3 py-2 space-y-2">
                  <div className="flex items-center gap-1.5 text-red-400 text-xs">
                    <AlertCircle size={12} />
                    <span>{msg.content}</span>
                  </div>
                  <button
                    type="button"
                    onClick={handleRetry}
                    disabled={sending}
                    className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground disabled:opacity-30"
                  >
                    <RefreshCw size={10} />
                    Retry
                  </button>
                </div>
              </div>
            ) : (
              <AIMessage
                role={msg.role}
                content={msg.content}
                structured={msg.structured}
                messageId={msg.role === "assistant" ? msg.id : undefined}
                isStreaming={msg.isStreaming}
              />
            )}
          </div>
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

      {/* Footer disclaimer */}
      {USE_V2 && (
        <div className="px-3 py-1.5 border-t border-border/50 flex items-center gap-1.5">
          <Shield size={8} className="text-muted-foreground/50 shrink-0" />
          <p className="text-[9px] text-muted-foreground/50">
            Not investment advice. For informational purposes only.
          </p>
        </div>
      )}
    </div>
  );
}
