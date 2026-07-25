"use client";
/* eslint-disable react-hooks/purity */

import { useState } from "react";
import { useAssistantStore } from "@/lib/stores/useAssistantStore";
import { assistantApi }     from "@/lib/api/assistant.api";
import { ConfidenceMeter }   from "@/components/intelligence/ConfidenceMeter";
import { SourceChipList }    from "@/components/intelligence/SourceChip";
import { EvidenceList }      from "@/components/intelligence/EvidenceList";
import { RecommendationList }from "@/components/intelligence/RecommendationCard";
import { Bot, Send, Shield, Sparkles, Plus, Pin, AlertCircle, RefreshCw } from "lucide-react";
import { format } from "date-fns";
import { cn } from "@/lib/utils/cn";
import { toast } from "sonner";

function getIsoTimestamp(): string {
  return new Date().toISOString();
}

export default function AssistantPage() {
  const {
    sessionId, context, messages, isLoading, activePanel,
    clearContext, addMessage, setLoading, newSession, setActivePanel,
  } = useAssistantStore();

  const [question, setQuestion] = useState("");

  const handleSend = async (qText?: string) => {
    const queryText = qText || question;
    if (!queryText.trim() || isLoading) return;

    const ts = getIsoTimestamp();
    const userMsgId = `user-${Date.now()}`;
    addMessage({
      id:        userMsgId,
      role:      "user",
      content:   queryText,
      timestamp: ts,
    });

    if (!qText) setQuestion("");
    setLoading(true);

    try {
      const response = await assistantApi.chat({
        question:    queryText,
        session_id:  sessionId,
        criminal_id: context.criminal_id,
        crime_id:    context.crime_id,
        district:    context.district,
        gang_name:   context.gang_name,
      });

      addMessage({
        id:        `ai-${response.session_id}`,
        role:      "assistant",
        content:   response.answer,
        timestamp: getIsoTimestamp(),
        response,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "AI Copilot query failed";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const lastAiResponse = [...messages].reverse().find((m) => m.response)?.response;

  return (
    <div className="h-[calc(100vh-56px)] flex overflow-hidden bg-[#0d1117]">
      {/* Left Column: Context & Quick Actions Panel (280px) */}
      <aside className="w-70 border-r border-[#30363d] bg-[#0d1117] flex flex-col p-4 gap-4 flex-shrink-0 overflow-y-auto">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot size={18} className="text-[#bc8cff]" />
            <h2 className="text-[14px] font-bold text-[#e6edf3]">PAC AI Copilot</h2>
          </div>
          <button
            onClick={newSession}
            className="p-1 rounded bg-[#21262d] text-[#8b949e] hover:text-[#e6edf3] text-[11px] font-mono flex items-center gap-1 border border-[#30363d]"
            title="Start new conversation session"
          >
            <Plus size={12} /> New
          </button>
        </div>

        {/* Pinned Entity Context Card */}
        <div className="pac-card flex flex-col gap-2 border-[#bc8cff]/40 bg-[rgba(188,140,255,0.04)]">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#bc8cff] flex items-center gap-1">
              <Pin size={11} /> Pinned Context
            </span>
            {(context.criminal_id || context.crime_id || context.district) && (
              <button onClick={clearContext} className="text-[10px] text-[#8b949e] hover:text-[#f85149]">
                Clear
              </button>
            )}
          </div>

          <div className="flex flex-col gap-1 text-[12px]">
            {context.crime_id && (
              <div className="flex justify-between font-mono">
                <span className="text-[#8b949e]">Crime ID:</span>
                <span className="text-[#58a6ff] truncate">{context.crime_id}</span>
              </div>
            )}
            {context.criminal_id && (
              <div className="flex justify-between font-mono">
                <span className="text-[#8b949e]">Criminal ID:</span>
                <span className="text-[#3fb950] truncate">{context.criminal_id}</span>
              </div>
            )}
            {context.district && (
              <div className="flex justify-between font-mono">
                <span className="text-[#8b949e]">District:</span>
                <span className="text-[#d29922]">{context.district}</span>
              </div>
            )}

            {!context.criminal_id && !context.crime_id && !context.district && (
              <p className="text-[11px] text-[#8b949e] italic py-1">
                No active entity pinned. Copilot will query global intelligence.
              </p>
            )}
          </div>
        </div>

        {/* Suggested Quick Action Prompts */}
        <div className="flex flex-col gap-2">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-[#8b949e]">
            Suggested Investigations
          </p>
          {[
            "Why is this offender classified as High Risk?",
            "Identify crime hotspots in Bengaluru Urban district.",
            "Find similar modus operandi cases across districts.",
            "Generate patrol recommendations for tonight.",
          ].map((promptText, i) => (
            <button
              key={i}
              onClick={() => handleSend(promptText)}
              disabled={isLoading}
              className="text-left p-2.5 rounded bg-[#161b22] border border-[#30363d] text-[12px] text-[#c9d1d9] hover:text-[#e6edf3] hover:border-[#bc8cff]/50 transition-colors leading-snug"
            >
              {promptText}
            </button>
          ))}
        </div>
      </aside>

      {/* Middle Column: Chat Window (Flexible) */}
      <main className="flex-1 flex flex-col min-w-0 bg-[#0d1117]">
        {/* Mandatory Disclaimer Header */}
        <div className="px-4 py-2 bg-[#161b22] border-b border-[#30363d] flex items-center justify-between text-[11px] text-[#d29922]">
          <span className="flex items-center gap-1.5 font-semibold">
            <AlertCircle size={13} />
            AI Decision Support — Output contains evidence-backed recommendations. Verify before operational use.
          </span>
          <span className="font-mono text-[#8b949e]">Session: {sessionId.slice(0, 16)}</span>
        </div>

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
          {!messages.length ? (
            <div className="my-auto text-center flex flex-col items-center gap-3 py-12">
              <div className="w-12 h-12 rounded-full bg-[rgba(188,140,255,0.15)] border border-[rgba(188,140,255,0.4)] flex items-center justify-center text-[#bc8cff]">
                <Sparkles size={24} />
              </div>
              <h3 className="text-[16px] font-bold text-[#e6edf3]">PAC AI Investigation Copilot</h3>
              <p className="text-[13px] text-[#8b949e] max-w-md">
                Ask any natural language question to search across Crime DNA, Neo4j Network Graphs, PostGIS Spatial Hotspots, and Behavioral Intelligence.
              </p>
            </div>
          ) : (
            messages.map((m) => {
              const isUser = m.role === "user";
              return (
                <div key={m.id} className={cn("flex flex-col gap-2", isUser ? "items-end" : "items-start")}>
                  <div
                    className={cn(
                      "p-4 rounded-lg max-w-2xl text-[13px] leading-relaxed",
                      isUser
                        ? "bg-[#1f6feb] text-white rounded-br-none"
                        : "bg-[#161b22] border border-[#30363d] text-[#e6edf3] rounded-bl-none shadow-card",
                    )}
                  >
                    <p className="whitespace-pre-wrap">{m.content}</p>

                    {m.response && (
                      <div className="mt-3 pt-3 border-t border-[#30363d] flex flex-col gap-3">
                        <ConfidenceMeter score={m.response.confidence} />
                        <SourceChipList sources={m.response.sources} />
                      </div>
                    )}
                  </div>
                  <span className="text-[10px] text-[#484f58] font-mono px-1">
                    {format(new Date(m.timestamp), "HH:mm")}
                  </span>
                </div>
              );
            })
          )}

          {isLoading && (
            <div className="flex items-center gap-2 text-[12px] text-[#bc8cff] p-3 rounded bg-[#161b22] border border-[#30363d] w-fit">
              <RefreshCw size={14} className="animate-spin" />
              <span>Querying PAC Intelligence Pipeline…</span>
            </div>
          )}
        </div>

        {/* Input Box */}
        <div className="p-4 border-t border-[#30363d] bg-[#0d1117]">
          <form
            onSubmit={(e) => { e.preventDefault(); handleSend(); }}
            className="flex items-center gap-2 bg-[#161b22] border border-[#30363d] rounded-md p-2 focus-within:border-[#bc8cff]"
          >
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask an investigation question..."
              className="flex-1 bg-transparent text-[13px] text-[#e6edf3] placeholder-[#484f58] focus:outline-none px-2"
            />
            <button
              type="submit"
              disabled={isLoading || !question.trim()}
              className="p-2 rounded bg-[#bc8cff] text-[#0d1117] hover:bg-[#c8a0ff] disabled:opacity-30 transition-colors"
            >
              <Send size={15} />
            </button>
          </form>
        </div>
      </main>

      {/* Right Column: Evidence & Recommendations Panel (320px) */}
      <aside className="w-80 border-l border-[#30363d] bg-[#0d1117] flex flex-col p-4 gap-4 flex-shrink-0 overflow-y-auto">
        <div className="flex border-b border-[#30363d]">
          {[
            { key: "evidence",        label: "Evidence" },
            { key: "recommendations", label: "Actions" },
            { key: "followup",        label: "Follow-ups" },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActivePanel(tab.key as "evidence" | "recommendations" | "followup")}
              className={cn(
                "flex-1 py-1.5 text-[12px] font-semibold border-b-2 transition-colors",
                activePanel === tab.key
                  ? "border-[#bc8cff] text-[#bc8cff]"
                  : "border-transparent text-[#8b949e]",
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {lastAiResponse ? (
          <div className="flex flex-col gap-4 text-[13px]">
            {activePanel === "evidence" && (
              <EvidenceList items={lastAiResponse.evidence} title="Traceable Evidence Facts" variant="evidence" />
            )}

            {activePanel === "recommendations" && (
              <RecommendationList items={lastAiResponse.recommendations} title="Operational Recommendations" />
            )}

            {activePanel === "followup" && (
              <div className="flex flex-col gap-2">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#8b949e]">
                  Suggested Follow-up Questions
                </p>
                {lastAiResponse.follow_up_questions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(q)}
                    className="text-left p-2 rounded bg-[#161b22] border border-[#30363d] text-[12px] text-[#58a6ff] hover:underline"
                  >
                    → {q}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <p className="text-[12px] text-[#8b949e] py-8 text-center italic">
            Send a query to view grounded evidence facts and recommendations.
          </p>
        )}
      </aside>
    </div>
  );
}
