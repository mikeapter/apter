"use client";

import { ThumbsUp, ThumbsDown, Database } from "lucide-react";
import { useState } from "react";
import { sendFeedback, type AIResponse } from "../../lib/api/ai";

type Props = {
  role: "user" | "assistant";
  content: string;
  structured?: AIResponse | null;
  messageId?: string;
  isStreaming?: boolean;
};

export function AIMessage({ role, content, structured, messageId, isStreaming }: Props) {
  const [feedbackSent, setFeedbackSent] = useState<"helpful" | "not_helpful" | null>(null);

  if (role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-md bg-panel-2 border border-border px-3 py-2 text-sm">
          {content}
        </div>
      </div>
    );
  }

  // Streaming text (not yet parsed as structured)
  if (isStreaming && !structured) {
    return (
      <div className="flex justify-start">
        <div className="max-w-[95%] rounded-md bg-panel border border-border px-3 py-2">
          <p className="text-sm whitespace-pre-wrap">{content}<span className="animate-pulse">|</span></p>
        </div>
      </div>
    );
  }

  // Structured AI response
  if (structured) {
    return (
      <div className="flex justify-start">
        <div className="max-w-[95%] rounded-md bg-panel border border-border px-3 py-2 space-y-2">
          {/* Data sources — shown first so users see what the AI pulled */}
          {structured.data_used?.length > 0 && (
            <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground bg-panel-2 rounded px-2 py-1">
              <Database size={10} className="shrink-0" />
              <span>Looking at: {structured.data_used.join(", ")}</span>
            </div>
          )}

          {/* Summary */}
          <div>
            <p className="text-sm">{structured.summary}</p>
          </div>

          {/* Detail */}
          {structured.explanation && (
            <div>
              <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">Detail</div>
              <p className="text-sm mt-0.5">{structured.explanation}</p>
            </div>
          )}

          {/* Risk flags */}
          {structured.risk_flags?.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">Risk Factors</div>
              <ul className="mt-0.5 text-sm space-y-0.5">
                {structured.risk_flags.map((flag, i) => (
                  <li key={i} className="text-orange-400/80">• {flag}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Checklist */}
          {structured.checklist?.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">Things to Monitor</div>
              <ul className="mt-0.5 text-sm space-y-0.5">
                {structured.checklist.map((item, i) => (
                  <li key={i} className="text-muted-foreground">• {item}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Scenarios */}
          {structured.scenarios && structured.scenarios.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">Scenarios</div>
              <ul className="mt-0.5 text-sm space-y-0.5">
                {structured.scenarios.map((s, i) => (
                  <li key={i} className="text-muted-foreground">• {s}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Disclaimer — compact, non-intrusive */}
          <div className="pt-1 border-t border-border/50">
            <p className="text-[10px] text-muted-foreground/60">Not investment advice.</p>
          </div>

          {/* Feedback buttons */}
          {messageId && (
            <div className="flex items-center gap-2 pt-1">
              <button
                type="button"
                disabled={feedbackSent !== null}
                onClick={() => {
                  setFeedbackSent("helpful");
                  sendFeedback({ message_id: messageId, rating: "helpful" }).catch(() => {});
                }}
                className={`p-1 rounded hover:bg-muted transition-colors ${
                  feedbackSent === "helpful" ? "text-green-400" : "text-muted-foreground"
                }`}
                title="Helpful"
              >
                <ThumbsUp size={12} />
              </button>
              <button
                type="button"
                disabled={feedbackSent !== null}
                onClick={() => {
                  setFeedbackSent("not_helpful");
                  sendFeedback({ message_id: messageId, rating: "not_helpful" }).catch(() => {});
                }}
                className={`p-1 rounded hover:bg-muted transition-colors ${
                  feedbackSent === "not_helpful" ? "text-red-400" : "text-muted-foreground"
                }`}
                title="Not helpful"
              >
                <ThumbsDown size={12} />
              </button>
              {feedbackSent && (
                <span className="text-[10px] text-muted-foreground">Thanks for the feedback</span>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Fallback plain text
  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] rounded-md bg-panel border border-border px-3 py-2 text-sm">
        {content}
      </div>
    </div>
  );
}
