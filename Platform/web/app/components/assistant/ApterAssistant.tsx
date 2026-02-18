"use client";

import { useState, useRef, useEffect } from "react";
import { Sparkles, X, Send } from "lucide-react";
import { getAssistantResponse, type AssistantResponse } from "../../lib/assistantResponses";
import { COMPLIANCE } from "../../lib/compliance";

type Message = {
  role: "user" | "assistant";
  content: string;
  structured?: AssistantResponse;
};

function AssistantMessage({ msg }: { msg: Message }) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-md bg-panel-2 border border-border px-3 py-2 text-sm">
          {msg.content}
        </div>
      </div>
    );
  }

  if (msg.structured) {
    const s = msg.structured;
    return (
      <div className="flex justify-start">
        <div className="max-w-[95%] rounded-md bg-panel border border-border px-3 py-2 space-y-2">
          <div>
            <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">What the data shows</div>
            <p className="text-sm mt-0.5">{s.dataShows}</p>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">Why it may matter</div>
            <p className="text-sm mt-0.5">{s.whyItMatters}</p>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">What to review next</div>
            <ul className="mt-0.5 text-sm space-y-0.5">
              {s.reviewNext.map((item, i) => (
                <li key={i} className="text-muted-foreground">• {item}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] rounded-md bg-panel border border-border px-3 py-2 text-sm">
        {msg.content}
      </div>
    </div>
  );
}

export function ApterAssistant() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;

    const userMsg: Message = { role: "user", content: text };
    const response = getAssistantResponse(text);
    const assistantMsg: Message = {
      role: "assistant",
      content: "",
      structured: response,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-16 right-6 z-40 h-12 w-12 rounded-full border border-border bg-panel shadow-lg flex items-center justify-center hover:bg-muted transition-colors"
        title="Open Apter Assistant"
      >
        <Sparkles size={20} />
      </button>
    );
  }

  return (
    <div className="fixed bottom-16 right-6 z-40 w-96 max-h-[70vh] rounded-md border border-border bg-card shadow-xl flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-panel">
        <div className="flex items-center gap-2">
          <Sparkles size={14} />
          <span className="text-sm font-semibold">Apter Assistant</span>
        </div>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-muted-foreground hover:text-foreground"
        >
          <X size={16} />
        </button>
      </div>

      {/* Disclaimer */}
      <div className="px-3 py-1.5 border-b border-border bg-panel-2">
        <p className="text-[10px] text-muted-foreground">{COMPLIANCE.ASSISTANT_DISCLAIMER}</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto p-3 space-y-3 min-h-[200px]">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground text-sm py-8">
            <Sparkles size={24} className="mx-auto mb-2 opacity-40" />
            <p>Ask about stocks, market conditions, or your portfolio.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <AssistantMessage key={i} msg={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="border-t border-border px-3 py-2 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          className="flex-1 h-8 rounded-md border border-border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring/40"
        />
        <button
          type="submit"
          className="h-8 w-8 rounded-md border border-border flex items-center justify-center hover:bg-muted"
        >
          <Send size={14} />
        </button>
      </form>
    </div>
  );
}
