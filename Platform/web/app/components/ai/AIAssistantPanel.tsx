"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Sparkles, X, Send, Database, RefreshCw, AlertCircle, Shield } from "lucide-react";
import { Drawer } from "vaul";
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
  const [snap, setSnap] = useState<number | string | null>(0.75);
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

  return (
    <Drawer.Root
      open={open}
      onOpenChange={setOpen}
      snapPoints={[0.5, 0.75, 0.95]}
      activeSnapPoint={snap}
      setActiveSnapPoint={setSnap}
      modal
    >
      {/* ── Floating Action Button (trigger) ── */}
      <Drawer.Trigger asChild>
        <button
          type="button"
          className="fixed bottom-[calc(80px_+_env(safe-area-inset-bottom,0px))] right-4 lg:bottom-6 lg:right-6 z-40 h-12 w-12 rounded-full border border-border bg-panel/90 backdrop-blur-md shadow-lg flex items-center justify-center hover:bg-muted transition-colors"
          title="Open Apter Intelligence"
        >
          <Sparkles size={20} />
        </button>
      </Drawer.Trigger>

      <Drawer.Portal>
        <Drawer.Overlay className="fixed inset-0 z-[60] bg-black/50" />
        <Drawer.Content className="fixed bottom-0 left-0 right-0 z-[60] rounded-t-3xl bg-card border-t border-border outline-none">
          <div className="flex flex-col h-full overflow-hidden">
            {/* ── Drag handle ── */}
            <div className="flex-shrink-0 pt-3 pb-1">
              <div className="mx-auto w-12 h-1.5 rounded-full bg-muted-foreground/20" />
            </div>

            {/* ── Header ── */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-border flex-shrink-0">
              <div className="flex items-center gap-2">
                <Sparkles size={16} />
                <div>
                  <Drawer.Title className="text-sm font-semibold">
                    Apter Intelligence
                  </Drawer.Title>
                  <Drawer.Description className="sr-only">
                    AI-powered financial analysis assistant
                  </Drawer.Description>
                  <span className="block text-[9px] text-muted-foreground leading-tight">
                    Institutional-grade analysis
                  </span>
                </div>
                {USE_V2 && (
                  <span className="text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded px-1 py-0.5 font-mono">
                    LIVE
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="h-9 w-9 rounded-xl flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            {/* ── Context selector (tickers) ── */}
            <div className="px-4 py-2 border-b border-border flex items-center gap-1.5 flex-wrap flex-shrink-0">
              <Database size={10} className="text-muted-foreground shrink-0" />
              {tickers.map((t) => (
                <span
                  key={t}
                  className="text-[10px] bg-panel border border-border rounded-lg px-1.5 py-0.5 font-mono flex items-center gap-1"
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
                className="flex-1 min-w-[80px] h-6 bg-transparent text-[10px] outline-none placeholder:text-muted-foreground/60"
              />
            </div>

            {/* ── Messages ── */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
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
                      <div className="max-w-[95%] rounded-2xl bg-red-500/5 border border-red-500/20 px-3 py-2 space-y-2">
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

            {/* ── Input ── */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSubmit();
              }}
              className="border-t border-border px-4 py-3 flex gap-2 flex-shrink-0"
              style={{ paddingBottom: "max(12px, env(safe-area-inset-bottom, 12px))" }}
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question..."
                disabled={sending}
                className="flex-1 h-11 rounded-xl border border-border bg-background px-4 text-sm outline-none focus:ring-2 focus:ring-ring/40 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={sending || !input.trim()}
                className="h-11 w-11 rounded-xl border border-border flex items-center justify-center hover:bg-muted disabled:opacity-30 transition-colors"
              >
                <Send size={16} />
              </button>
            </form>

            {/* ── Footer disclaimer ── */}
            {USE_V2 && (
              <div className="px-4 py-1.5 border-t border-border/50 flex items-center gap-1.5 flex-shrink-0">
                <Shield size={8} className="text-muted-foreground/50 shrink-0" />
                <p className="text-[9px] text-muted-foreground/50">
                  Not investment advice. For informational purposes only.
                </p>
              </div>
            )}
          </div>
        </Drawer.Content>
      </Drawer.Portal>
    </Drawer.Root>
  );
}
