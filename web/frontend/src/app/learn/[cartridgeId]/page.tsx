"use client";
import { useEffect, useState, useRef, useCallback, useMemo, memo, useDeferredValue, startTransition } from "react";
import { useParams, useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { api, chatStream, ApiError } from "@/lib/api";
import { useAuthStore, useLearningStore } from "@/lib/store";
import { showToast } from "@/components/Toast";

interface NodeInfo { id: string; title: string; difficulty: number; prerequisites: string[]; pass_criteria: string; status: string; score: number | null }
interface CartridgeData { id: string; title: string; nodes: NodeInfo[]; progress: { completed: number; total: number }; dag: Record<string, unknown> }

/* ─── Lightweight streaming text (no markdown parsing during stream) ─── */
const StreamingText = memo(function StreamingText({ text }: { text: string }) {
  return (
    <div className="chat-markdown text-sm whitespace-pre-wrap break-words leading-relaxed">
      {text}
      <span className="inline-block w-1.5 h-[1.1em] bg-[var(--accent)] animate-pulse ml-0.5 rounded-sm align-text-bottom" />
    </div>
  );
});

/* ─── Finalized Markdown (full parse, only for completed messages) ─── */
const MarkdownContent = memo(function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="chat-markdown text-sm">
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>{content}</ReactMarkdown>
    </div>
  );
});

/* ─── Chat Message ─── */
const ChatMessage = memo(function ChatMessage({ msg, index }: { msg: { role: string; content: string }; index: number }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`} style={{ animationDelay: `${index * 30}ms` }}>
      <div className={`max-w-[85%] p-4 rounded-2xl transition-all duration-200
        ${isUser
          ? "bg-[var(--accent)] text-white rounded-br-md shadow-sm"
          : "pixel-card rounded-bl-md"
        }`}>
        {!isUser && (
          <div className="flex items-center gap-1.5 mb-2">
            <div className="w-5 h-5 rounded-full bg-[var(--accent)]/10 flex items-center justify-center text-xs">✨</div>
            <span className="text-[10px] text-[var(--text-muted)] font-medium uppercase tracking-wider">AI Tutor</span>
          </div>
        )}
        <MarkdownContent content={msg.content} />
      </div>
    </div>
  );
});

/* ─── Typing indicator (three bouncing dots) ─── */
function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="pixel-card rounded-2xl rounded-bl-md px-5 py-4">
        <div className="flex items-center gap-1.5">
          <div className="w-5 h-5 rounded-full bg-[var(--accent)]/10 flex items-center justify-center text-xs">✨</div>
          <div className="flex gap-1 ml-1">
            <span className="w-2 h-2 rounded-full bg-[var(--accent)]/60 animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="w-2 h-2 rounded-full bg-[var(--accent)]/60 animate-bounce" style={{ animationDelay: "150ms" }} />
            <span className="w-2 h-2 rounded-full bg-[var(--accent)]/60 animate-bounce" style={{ animationDelay: "300ms" }} />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Skeleton loader for node switch ─── */
function NodeSkeleton() {
  return (
    <div className="space-y-4 animate-pulse px-2">
      <div className="flex justify-start">
        <div className="max-w-[75%] space-y-2">
          <div className="flex items-center gap-1.5">
            <div className="w-5 h-5 rounded-full bg-[var(--border-light)]" />
            <div className="h-2 w-12 rounded bg-[var(--border-light)]" />
          </div>
          <div className="h-4 w-full rounded bg-[var(--border-light)]" />
          <div className="h-4 w-3/4 rounded bg-[var(--border-light)]" />
          <div className="h-4 w-1/2 rounded bg-[var(--border-light)]" />
        </div>
      </div>
    </div>
  );
}

/* ─── Sidebar ─── */
const Sidebar = memo(function Sidebar({ cartridge, currentNodeId, onSelectNode, onDAG, onBack }: {
  cartridge: CartridgeData | null;
  currentNodeId: string | null;
  onSelectNode: (id: string) => void;
  onDAG: () => void;
  onBack: () => void;
}) {
  return (
    <>
      <div className="p-4 border-b-2 border-[var(--border)]">
        <div className="flex items-center justify-between mb-2">
          <button onClick={onBack} className="text-xs text-[var(--text-muted)] hover:text-[var(--accent)] transition-colors flex items-center gap-1">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M8 2L4 6l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
            Back
          </button>
          <button onClick={onDAG} className="text-xs px-2 py-1 rounded-md border border-[var(--border-light)] hover:bg-[var(--accent)] hover:text-white hover:border-[var(--accent)] transition-all duration-200 active:scale-95">
            🗺️ Map
          </button>
        </div>
        <h2 className="font-bold text-sm truncate" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
          {cartridge?.title || "Loading..."}
        </h2>
        {cartridge && (
          <div className="mt-3">
            <div className="flex justify-between text-xs text-[var(--text-muted)] mb-1.5">
              <span>Progress</span>
              <span className="font-mono">{cartridge.progress.completed}/{cartridge.progress.total}</span>
            </div>
            <div className="h-2 bg-[var(--bg-primary)] rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-[var(--accent)] to-[var(--accent-light)] rounded-full transition-all duration-700 ease-out"
                style={{ width: `${(cartridge.progress.completed / cartridge.progress.total) * 100}%` }} />
            </div>
          </div>
        )}
      </div>
      <div className="flex-1 overflow-y-auto overscroll-contain">
        {cartridge?.nodes.map((node, i) => (
          <button key={node.id} onClick={() => onSelectNode(node.id)}
            className={`w-full text-left px-4 py-3 text-sm border-b border-[var(--border-light)]/50 flex items-center gap-2.5 transition-all duration-200
              ${currentNodeId === node.id
                ? "bg-[var(--accent)]/8 border-l-[3px] border-l-[var(--accent)] font-semibold"
                : "hover:bg-[var(--bg-primary)] active:bg-[var(--border-light)]/30"
              }`}
            style={{ animationDelay: `${i * 30}ms` }}>
            <span className="text-xs shrink-0">{node.status === "completed" ? "✅" : node.status === "in_progress" ? "🔸" : "⬜"}</span>
            <span className="truncate flex-1">{node.title}</span>
            {node.status === "completed" && <span className="text-[10px] text-[var(--accent-light)]">DONE</span>}
          </button>
        ))}
      </div>
    </>
  );
});

/* ─── Question Card ─── */
const QuestionCard = memo(function QuestionCard({ question, onSubmit, nextNodeTitle, onNextNode }: {
  question: NonNullable<ReturnType<typeof useLearningStore.getState>["currentQuestion"]>;
  onSubmit: (answer: string | number | number[], correct: boolean) => Promise<void>;
  nextNodeTitle?: string;
  onNextNode?: () => void;
}) {
  const [selected, setSelected] = useState<number | number[]>(question.type === "multi_choice" ? [] : -1);
  const [fillAnswer, setFillAnswer] = useState("");
  const [judgmentAnswer, setJudgmentAnswer] = useState<boolean | null>(null);
  const [result, setResult] = useState<{ correct: boolean; checked: boolean }>({ correct: false, checked: false });
  const submitted = result.checked;

  const checkAnswer = useCallback(() => {
    let correct = false;
    let answerStr = "";
    if (question.type === "single_choice") {
      correct = (selected as number) === question.answer;
      answerStr = String(selected);
    } else if (question.type === "multi_choice") {
      const userSelected = [...(selected as number[])].sort();
      const correctAnswers = [...(question.answer as number[])].sort();
      correct = JSON.stringify(userSelected) === JSON.stringify(correctAnswers);
      answerStr = JSON.stringify(userSelected);
    } else if (question.type === "fill_blank") {
      correct = fillAnswer.toLowerCase().includes(String(question.answer).toLowerCase());
      answerStr = fillAnswer;
    } else if (question.type === "judgment") {
      correct = judgmentAnswer === question.answer;
      answerStr = String(judgmentAnswer);
    }
    setResult({ correct, checked: true });
    onSubmit(answerStr, correct);
  }, [selected, fillAnswer, judgmentAnswer, question, onSubmit]);

  const canSubmit = useMemo(() => {
    if (submitted) return false;
    if (question.type === 'multi_choice') return (selected as number[]).length > 0;
    if (question.type === 'single_choice') return (selected as number) !== -1;
    if (question.type === 'fill_blank') return fillAnswer !== '';
    if (question.type === 'judgment') return judgmentAnswer !== null;
    return false;
  }, [question.type, selected, fillAnswer, judgmentAnswer, submitted]);

  const icon = question.type === "single_choice" ? "🔍" : question.type === "multi_choice" ? "🎯" : question.type === "fill_blank" ? "📝" : "✅";

  return (
    <div className="space-y-2">
      {question.type === "single_choice" && question.options?.map((opt, i) => (
        <button key={i} onClick={() => !submitted && setSelected(i)} disabled={submitted}
          className={`w-full text-left p-3 border-2 rounded-xl text-sm transition-all duration-200 active:scale-[0.98]
            ${submitted && i === question.answer ? "border-[var(--success)] bg-[var(--success)]/10" : ""}
            ${submitted && i === selected && i !== question.answer ? "border-[var(--error)] bg-[var(--error)]/10" : ""}
            ${!submitted && selected === i ? "border-[var(--accent)] bg-[var(--accent)]/8 shadow-sm" : "border-[var(--border-light)] hover:border-[var(--accent)] hover:shadow-sm"}
            ${submitted ? "cursor-default" : "cursor-pointer"}`}>
          <span className="font-mono text-xs text-[var(--text-muted)] mr-2">{String.fromCharCode(65 + i)}.</span>
          <span>{opt}</span>
        </button>
      ))}
      {question.type === "multi_choice" && question.options?.map((opt, i) => {
        const isSelected = (selected as number[]).includes(i);
        return (
          <button key={i} onClick={() => {
            if (submitted) return;
            const s = [...(selected as number[])];
            const idx = s.indexOf(i);
            if (idx >= 0) s.splice(idx, 1); else s.push(i);
            setSelected(s);
          }} disabled={submitted}
            className={`w-full text-left p-3 border-2 rounded-xl text-sm transition-all duration-200 active:scale-[0.98]
              ${isSelected ? "border-[var(--accent)] bg-[var(--accent)]/8 shadow-sm" : "border-[var(--border-light)] hover:border-[var(--accent)]"}
              ${submitted ? "cursor-default" : "cursor-pointer"}`}>
            <span className="font-mono text-xs text-[var(--text-muted)] mr-2">{String.fromCharCode(65 + i)}.</span>
            <span className="flex-1">{opt}</span>
            {isSelected && <span className="float-right text-[var(--accent)]">✓</span>}
          </button>
        );
      })}
      {question.type === "fill_blank" && (
        <input value={fillAnswer} onChange={(e) => setFillAnswer(e.target.value)} placeholder="Type your answer..."
          disabled={submitted}
          className="w-full p-3 border-2 border-[var(--border)] rounded-xl text-sm focus:border-[var(--accent-light)] focus:ring-2 focus:ring-[var(--accent)]/20 focus:outline-none transition-all" />
      )}
      {question.type === "judgment" && (
        <div className="flex gap-3">
          <button onClick={() => !submitted && setJudgmentAnswer(true)} disabled={submitted}
            className={`flex-1 p-3 border-2 rounded-xl text-sm transition-all duration-200 active:scale-[0.98]
              ${judgmentAnswer === true ? "border-[var(--accent)] bg-[var(--accent)]/8 font-bold shadow-sm" : "border-[var(--border-light)] hover:border-[var(--accent)]"}`}>
            ✅ True
          </button>
          <button onClick={() => !submitted && setJudgmentAnswer(false)} disabled={submitted}
            className={`flex-1 p-3 border-2 rounded-xl text-sm transition-all duration-200 active:scale-[0.98]
              ${judgmentAnswer === false ? "border-[var(--error)] bg-[var(--error)]/8 font-bold shadow-sm" : "border-[var(--border-light)] hover:border-[var(--error)]"}`}>
            ❌ False
          </button>
        </div>
      )}
      {!submitted && (
        <button onClick={checkAnswer} disabled={!canSubmit}
          className="pixel-btn pixel-btn-primary w-full mt-2 text-sm disabled:opacity-30 disabled:cursor-not-allowed active:scale-[0.97] transition-all duration-150">
          Submit Answer
        </button>
      )}
      {result.checked && result.correct && (
        <div className="mt-2 p-4 bg-gradient-to-br from-[var(--success)]/15 to-[var(--success)]/5 border-2 border-[var(--success)] rounded-xl" style={{ animation: "popIn 0.3s cubic-bezier(0.16, 1, 0.3, 1)" }}>
          <p className="text-sm font-bold text-center">🎉 正确！</p>
          {question.explanation && <p className="text-xs text-[var(--text-secondary)] text-center mt-1">{question.explanation}</p>}
          {nextNodeTitle && onNextNode && (
            <button onClick={onNextNode}
              className="pixel-btn pixel-btn-primary w-full mt-3 text-sm flex items-center justify-center gap-2 active:scale-[0.97]">
              ▶ {nextNodeTitle}
            </button>
          )}
        </div>
      )}
      {result.checked && !result.correct && (
        <div className="mt-2 p-4 bg-gradient-to-br from-[var(--error)]/15 to-[var(--error)]/5 border-2 border-[var(--error)] rounded-xl" style={{ animation: "popIn 0.3s cubic-bezier(0.16, 1, 0.3, 1)" }}>
          <p className="text-sm font-bold text-center">❌ 不对！正确答案是 <span className="font-mono">{JSON.stringify(question.answer)}</span></p>
          {question.explanation && <p className="text-xs text-[var(--text-secondary)] text-center mt-1">{question.explanation}</p>}
        </div>
      )}
    </div>
  );
});

/* ─── Reasoning Card ─── */
const ReasoningCard = memo(function ReasoningCard({ reasoning }: { reasoning: NonNullable<ReturnType<typeof useLearningStore.getState>["currentReasoning"]> }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="pixel-card p-4 max-w-lg rounded-xl overflow-hidden transition-all duration-300" style={{ maxHeight: expanded ? '500px' : '48px' }}>
      <button onClick={() => setExpanded(!expanded)} className="flex items-center gap-2 w-full text-left">
        <span>🧠</span>
        <span className="font-bold text-sm truncate" style={{ fontFamily: "'JetBrains Mono', monospace" }}>{reasoning.title}</span>
        <span className="ml-auto text-xs text-[var(--text-muted)] transition-transform duration-300" style={{ transform: expanded ? 'rotate(180deg)' : '' }}>▼</span>
      </button>
      {expanded && (
        <div className="mt-3 space-y-2">
          {reasoning.steps.map((step, i) => (
            <div key={i} className="pl-4 border-l-2 border-[var(--accent-light)]">
              <div className="font-semibold text-sm">{step.title}</div>
              <div className="text-sm text-[var(--text-secondary)]">{step.content}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
});

/* ─── Main Page ─── */
export default function LearnPage() {
  const params = useParams();
  const router = useRouter();
  const cartridgeId = params.cartridgeId as string;
  const { token } = useAuthStore();
  const {
    currentNodeId, messages, streamingText, isStreaming, currentQuestion, currentReasoning,
    setCurrentNode, addUserMessage, appendStreamText, finalizeStream, setIsStreaming, setQuestion,
  } = useLearningStore();

  const [cartridge, setCartridge] = useState<CartridgeData | null>(null);
  const [input, setInput] = useState("");
  const [showLogin, setShowLogin] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loadingNode, setLoadingNode] = useState(false);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(true);

  // Use deferred value for streaming text to avoid jank
  const deferredStreaming = useDeferredValue(streamingText);

  // Smart scroll with rAF
  useEffect(() => {
    if (!chatContainerRef.current || !autoScrollRef.current) return;
    requestAnimationFrame(() => {
      if (!chatContainerRef.current) return;
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    });
  }, [messages, deferredStreaming]);

  // Load cartridge
  useEffect(() => {
    if (token) {
      api.getCartridge(cartridgeId).then(setCartridge).catch((err) => {
        if (err instanceof ApiError && err.status === 401) setShowLogin(true);
        else showToast('error', `Failed to load: ${err.message}`);
      });
    } else { setShowLogin(true); }
  }, [cartridgeId, token]);

  const currentNode = cartridge?.nodes.find((n) => n.id === currentNodeId);
  const nodeMessages = currentNodeId ? messages[currentNodeId] || [] : [];

  // Auto-select first uncompleted node
  useEffect(() => {
    if (cartridge && !currentNodeId) {
      const first = cartridge.nodes.find(n => n.status !== 'completed') || cartridge.nodes[0];
      if (first) selectNode(first.id);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cartridge]);

  // Auto-greet on new node
  useEffect(() => {
    if (!currentNodeId || !token || !cartridge) return;
    const existing = messages[currentNodeId];
    if (existing && existing.length > 0) return;
    const node = cartridge.nodes.find(n => n.id === currentNodeId);
    if (!node) return;

    setLoadingNode(true);
    const greetMsg = `开始学习：${node.title}`;
    addUserMessage(currentNodeId, greetMsg);
    setIsStreaming(true);
    (async () => {
      try {
        for await (const text of chatStream(cartridgeId, currentNodeId, greetMsg, [])) {
          appendStreamText(text);
        }
        finalizeStream(currentNodeId);
      } catch { appendStreamText(`❌ Connection error.`); finalizeStream(currentNodeId); }
      setIsStreaming(false);
      setLoadingNode(false);
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentNodeId, cartridge]);

  const selectNode = useCallback((nodeId: string) => {
    startTransition(() => {
      setCurrentNode(nodeId);
      setQuestion(null);
      setSidebarOpen(false);
    });
  }, [setCurrentNode, setQuestion]);

  const sendMessage = useCallback(async () => {
    if (!input.trim() || !currentNodeId || isStreaming) return;
    if (!token) { setShowLogin(true); return; }
    const msg = input.trim();
    setInput("");
    addUserMessage(currentNodeId, msg);
    setIsStreaming(true);
    try {
      const history = nodeMessages.map((m) => ({ role: m.role, content: m.content }));
      for await (const text of chatStream(cartridgeId, currentNodeId, msg, history)) {
        appendStreamText(text);
      }
      finalizeStream(currentNodeId);
    } catch (err: any) {
      const errMsg = err instanceof ApiError ? err.message : 'Connection error.';
      showToast('error', errMsg);
      appendStreamText(`\n\n❌ ${errMsg}`);
      finalizeStream(currentNodeId);
    }
    setIsStreaming(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input, currentNodeId, isStreaming, token, cartridgeId, nodeMessages]);

  const submitAnswer = useCallback(async (answer: string | number | number[], correct: boolean) => {
    if (!currentNodeId || !currentQuestion) return;
    const explanation = currentQuestion.explanation || "";
    await api.submitAnswer({
      cartridge_id: cartridgeId, node_id: currentNodeId,
      question_type: currentQuestion.type, user_answer: String(answer),
      correct_answer: String(currentQuestion.answer), correct,
    }).catch(() => {});

    setQuestion(null);
    const nodes = cartridge?.nodes || [];
    const idx = nodes.findIndex(n => n.id === currentNodeId);
    const nextNode = nodes[idx + 1];
    const feedbackMsg = correct
      ? `✅ 正确！${explanation}\n\n${nextNode ? `下一个知识点是「${nextNode.title}」，请开始教我。` : '我已经完成了，请总结。'}`
      : `❌ 不对，正确答案是 ${JSON.stringify(currentQuestion.answer)}。${explanation}\n\n请换个方式讲解。`;

    addUserMessage(currentNodeId, feedbackMsg);
    setIsStreaming(true);
    try {
      const history = (messages[currentNodeId] || []).map((m) => ({ role: m.role, content: m.content }));
      for await (const text of chatStream(cartridgeId, currentNodeId, feedbackMsg, history)) {
        appendStreamText(text);
      }
      finalizeStream(currentNodeId);
    } catch { appendStreamText(`\n\n❌ Error`); finalizeStream(currentNodeId); }
    setIsStreaming(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentNodeId, currentQuestion, cartridgeId, cartridge]);

  const nextNodeInfo = useMemo(() => {
    const nodes = cartridge?.nodes || [];
    const idx = nodes.findIndex(n => n.id === currentNodeId);
    return { title: nodes[idx + 1]?.title, select: nodes[idx + 1] ? () => selectNode(nodes[idx + 1].id) : undefined };
  }, [cartridge, currentNodeId, selectNode]);

  const displayStreaming = useMemo(() =>
    deferredStreaming.replace(/<<QUESTION>>[\s\S]*?<<\/QUESTION>>/g, "").replace(/<<REASONING>>[\s\S]*?<<\/REASONING>>/g, ""),
    [deferredStreaming]
  );

  return (
    <div className="h-screen flex relative bg-[var(--bg-primary)]">
      {/* Login Modal */}
      {showLogin && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 backdrop-blur-md" onClick={(e) => e.target === e.currentTarget && setShowLogin(false)}>
          <div className="pixel-card p-8 max-w-sm w-full mx-4" style={{ animation: "popIn 0.35s cubic-bezier(0.16, 1, 0.3, 1)" }}>
            <h2 className="text-xl font-bold mb-2">🔐 Welcome Back</h2>
            <p className="text-sm text-[var(--text-secondary)] mb-5">Login or register to start learning.</p>
            <div className="flex gap-3">
              <button onClick={() => router.push("/login")} className="pixel-btn pixel-btn-primary flex-1 active:scale-95 transition-transform">Login</button>
              <button onClick={() => router.push("/register")} className="pixel-btn flex-1 active:scale-95 transition-transform">Register</button>
            </div>
            <button onClick={() => setShowLogin(false)} className="mt-3 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors w-full text-center">Cancel</button>
          </div>
        </div>
      )}

      {/* Mobile overlay */}
      {sidebarOpen && <div className="fixed inset-0 bg-black/30 z-30 md:hidden backdrop-blur-sm transition-opacity" onClick={() => setSidebarOpen(false)} />}

      {/* Sidebar */}
      <div className={`w-72 border-r-2 border-[var(--border)] bg-white flex flex-col z-40 shrink-0
        fixed md:relative inset-y-0 left-0 h-full
        transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}>
        <Sidebar
          cartridge={cartridge} currentNodeId={currentNodeId}
          onSelectNode={selectNode}
          onDAG={() => router.push(`/learn/${cartridgeId}/dag`)}
          onBack={() => router.push("/")}
        />
      </div>

      {/* Main Chat */}
      <div className="flex-1 flex flex-col min-w-0 bg-white">
        {/* Top bar */}
        <div className="h-13 px-4 border-b border-[var(--border)]/60 bg-white/80 backdrop-blur-lg flex items-center gap-3 shrink-0 sticky top-0 z-10">
          <button onClick={() => setSidebarOpen(true)} className="md:hidden p-2 -ml-1 rounded-xl hover:bg-[var(--bg-primary)] active:scale-95 transition-all" aria-label="Menu">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
          </button>
          <div className="flex-1 min-w-0">
            <h2 className="font-bold text-sm truncate" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              {currentNode ? currentNode.title : "Select a node to start"}
            </h2>
            {currentNode && (
              <p className="text-[10px] text-[var(--text-muted)] truncate">{currentNode.id} · Difficulty {currentNode.difficulty}/3</p>
            )}
          </div>
          {currentNode && (
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold tracking-wide shrink-0 ${
              currentNode.difficulty <= 1 ? "bg-green-100 text-green-700" :
              currentNode.difficulty <= 2 ? "bg-amber-100 text-amber-700" :
              "bg-red-100 text-red-700"
            }`}>
              {currentNode.difficulty <= 1 ? "BEGINNER" : currentNode.difficulty <= 2 ? "INTERMEDIATE" : "ADVANCED"}
            </span>
          )}
        </div>

        {/* Chat area */}
        <div ref={chatContainerRef} className="flex-1 overflow-y-auto px-4 md:px-6 py-4 space-y-3 overscroll-contain scroll-smooth" onScroll={() => {
          if (!chatContainerRef.current) return;
          const el = chatContainerRef.current;
          autoScrollRef.current = (el.scrollHeight - el.scrollTop - el.clientHeight) < 120;
        }}>
          {/* Welcome */}
          {!currentNodeId && cartridge && (
            <div className="text-center text-[var(--text-muted)] mt-16">
              <div className="text-6xl mb-6" style={{ animation: "float 3s ease-in-out infinite" }}>🎮</div>
              <h3 className="text-lg font-bold mb-2">{cartridge.title}</h3>
              <p className="text-sm mb-8 max-w-xs mx-auto">Choose a topic from the sidebar to start your learning journey</p>
              {(() => {
                const first = cartridge.nodes.find(n => n.status !== 'completed');
                return first ? (
                  <button onClick={() => selectNode(first.id)} className="pixel-btn pixel-btn-primary text-sm active:scale-95 transition-transform">
                    ▶ Start with「{first.title}」
                  </button>
                ) : null;
              })()}
            </div>
          )}

          {/* Loading skeleton */}
          {loadingNode && nodeMessages.length === 0 && !displayStreaming && <NodeSkeleton />}

          {/* Messages */}
          {nodeMessages.map((msg, i) => (
            <ChatMessage key={`${currentNodeId}-${i}`} msg={msg} index={i} />
          ))}

          {/* Streaming — lightweight text rendering, no markdown parsing */}
          {displayStreaming && (
            <div className="flex justify-start">
              <div className="max-w-[85%] p-4 pixel-card rounded-2xl rounded-bl-md min-h-[48px]">
                <div className="flex items-center gap-1.5 mb-2">
                  <div className="w-5 h-5 rounded-full bg-[var(--accent)]/10 flex items-center justify-center text-xs">✨</div>
                  <span className="text-[10px] text-[var(--text-muted)] font-medium uppercase tracking-wider">AI Tutor</span>
                </div>
                <StreamingText text={displayStreaming} />
              </div>
            </div>
          )}

          {/* Typing indicator before stream starts */}
          {isStreaming && !displayStreaming && <TypingIndicator />}

          {/* Question */}
          {currentQuestion && !displayStreaming && !isStreaming && (
            <div className="flex justify-start" style={{ animation: "popIn 0.35s cubic-bezier(0.16, 1, 0.3, 1)" }}>
              <div className="pixel-card p-5 max-w-lg rounded-2xl">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-lg">{currentQuestion.type === "single_choice" ? "🔍" : currentQuestion.type === "multi_choice" ? "🎯" : currentQuestion.type === "fill_blank" ? "📝" : "✅"}</span>
                  <h3 className="font-bold text-sm flex-1" style={{ fontFamily: "'JetBrains Mono', monospace" }}>{currentQuestion.question}</h3>
                </div>
                <QuestionCard
                  question={currentQuestion}
                  onSubmit={submitAnswer}
                  nextNodeTitle={nextNodeInfo.title}
                  onNextNode={nextNodeInfo.select}
                />
              </div>
            </div>
          )}

          {/* Reasoning */}
          {currentReasoning && !displayStreaming && !isStreaming && <ReasoningCard reasoning={currentReasoning} />}

          <div className="h-2" />
        </div>

        {/* Input */}
        <div className="px-3 md:px-6 py-3 border-t border-[var(--border)]/40 bg-white shrink-0">
          <div className="flex gap-2 max-w-4xl mx-auto">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }}}
              placeholder={currentNodeId ? "Ask anything..." : "Select a node first"}
              disabled={!currentNodeId || isStreaming}
              className="flex-1 px-4 py-2.5 border-2 border-[var(--border-light)] rounded-2xl bg-[var(--bg-primary)] focus:outline-none focus:border-[var(--accent)] focus:ring-4 focus:ring-[var(--accent)]/10 disabled:opacity-30 text-sm transition-all duration-200 placeholder:text-[var(--text-muted)]"
            />
            <button onClick={sendMessage} disabled={!currentNodeId || isStreaming || !input.trim()}
              className="pixel-btn pixel-btn-primary px-5 rounded-2xl disabled:opacity-30 disabled:cursor-not-allowed text-sm active:scale-95 transition-all duration-150 shrink-0">
              {isStreaming ? <span className="flex items-center gap-1.5"><svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg></span> : "Send"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
