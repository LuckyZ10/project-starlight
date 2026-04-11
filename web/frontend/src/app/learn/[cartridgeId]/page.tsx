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

/* ─── SVG Icons ─── */
function ChevronLeftIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6"/></svg>; }
function MenuIcon() { return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>; }
function MapIcon() { return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg>; }
function SendIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>; }
function SpinnerIcon() { return <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>; }
function CheckIcon() { return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>; }
function PlayIcon() { return <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>; }
function XIcon() { return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>; }
function CheckCircleIcon() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>; }
function BrainIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a7 7 0 017 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 01-2 2h-4a2 2 0 01-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 017-7z"/><line x1="9" y1="22" x2="15" y2="22"/></svg>; }
function SparklesIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8L12 2z"/></svg>; }

/* ─── Lightweight streaming text (no markdown parsing during stream) ─── */
const StreamingText = memo(function StreamingText({ text }: { text: string }) {
  return (
    <div className="chat-markdown text-sm whitespace-pre-wrap break-words leading-relaxed">
      {text}
      <span className="inline-block w-[3px] h-[1.1em] bg-[var(--accent)] rounded-full ml-0.5 align-text-bottom animate-pulse" />
    </div>
  );
});

/* ─── Finalized Markdown (full parse, only for completed messages) ─── */
const MarkdownContent = memo(function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="chat-markdown text-sm leading-relaxed">
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[[rehypeKatex, { output: 'html', throwOnError: false }]]}>{content}</ReactMarkdown>
    </div>
  );
});

/* ─── Chat Message ─── */
const ChatMessage = memo(function ChatMessage({ msg, index }: { msg: { role: string; content: string }; index: number }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} animate-slide`} style={{ animationDelay: `${Math.min(index * 20, 200)}ms` }}>
      <div className={`flex gap-2.5 max-w-[85%] ${isUser ? "flex-row-reverse" : ""}`}>
        {/* Avatar */}
        <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-1
          ${isUser ? "bg-[var(--accent)]/10 text-[var(--accent)]" : "bg-gradient-to-br from-[var(--accent)] to-[var(--accent-light)] text-white"}`}>
          {isUser ? <span className="text-xs font-semibold">{msg.content?.[0]?.toUpperCase() || "U"}</span> : <SparklesIcon />}
        </div>
        {/* Bubble */}
        <div className={`px-4 py-3 rounded-2xl text-sm
          ${isUser
            ? "bg-[var(--accent)] text-white rounded-br-md"
            : "bg-[var(--bg-card)] border border-[var(--border)] rounded-bl-md"
          }`}>
          <MarkdownContent content={msg.content} />
        </div>
      </div>
    </div>
  );
});

/* ─── Typing indicator ─── */
function TypingIndicator() {
  return (
    <div className="flex justify-start animate-fade">
      <div className="flex gap-2.5">
        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[var(--accent)] to-[var(--accent-light)] flex items-center justify-center text-white shrink-0 mt-1">
          <SparklesIcon />
        </div>
        <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl rounded-bl-md px-4 py-3">
          <div className="flex gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--text-muted)] animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--text-muted)] animate-bounce" style={{ animationDelay: "120ms" }} />
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--text-muted)] animate-bounce" style={{ animationDelay: "240ms" }} />
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
      <div className="flex gap-2.5">
        <div className="w-7 h-7 rounded-full bg-[var(--border)] shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-3.5 bg-[var(--border)] rounded w-full" />
          <div className="h-3.5 bg-[var(--border)] rounded w-4/5" />
          <div className="h-3.5 bg-[var(--border)] rounded w-3/5" />
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
      <div className="p-4 border-b border-[var(--border)]">
        <div className="flex items-center justify-between mb-3">
          <button onClick={onBack} className="btn btn-ghost text-xs gap-1 px-2 py-1.5">
            <ChevronLeftIcon /> Back
          </button>
          <button onClick={onDAG} className="btn text-xs gap-1 px-2.5 py-1.5">
            <MapIcon /> Map
          </button>
        </div>
        <h2 className="font-semibold text-sm truncate" style={{ fontFamily: "var(--font-geist-mono)" }}>
          {cartridge?.title || "Loading..."}
        </h2>
        {cartridge && (
          <div className="mt-3">
            <div className="flex justify-between text-xs text-[var(--text-muted)] mb-1.5">
              <span>Progress</span>
              <span className="font-medium">{cartridge.progress.completed}/{cartridge.progress.total}</span>
            </div>
            <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-[var(--accent)] to-[var(--accent-light)] rounded-full transition-all duration-700 ease-out"
                style={{ width: `${(cartridge.progress.completed / cartridge.progress.total) * 100}%` }} />
            </div>
          </div>
        )}
      </div>
      <div className="flex-1 overflow-y-auto overscroll-contain">
        {cartridge?.nodes.map((node) => (
          <button key={node.id} onClick={() => onSelectNode(node.id)}
            className={`w-full text-left px-4 py-3 text-sm border-b border-[var(--border-light)] flex items-center gap-3 transition-all duration-150
              ${currentNodeId === node.id
                ? "bg-[var(--accent)]/5 border-l-[3px] border-l-[var(--accent)] font-medium"
                : "hover:bg-[var(--border-light)]/50"
              }`}>
            <span className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 text-[10px]
              ${node.status === "completed" ? "bg-[var(--success)]/15 text-[var(--success)]" : node.status === "in_progress" ? "bg-[var(--warning)]/15 text-[var(--warning)]" : "bg-[var(--border)] text-[var(--text-muted)]"}`}>
              {node.status === "completed" ? <CheckIcon /> : node.status === "in_progress" ? "●" : ""}
            </span>
            <span className="truncate flex-1">{node.title}</span>
            {node.status === "completed" && (
              <span className="badge bg-[var(--success)]/10 text-[var(--success)]">Done</span>
            )}
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

  const typeIcon = question.type === "single_choice" ? "🔍" : question.type === "multi_choice" ? "🎯" : question.type === "fill_blank" ? "📝" : "✅";

  return (
    <div className="space-y-2">
      {question.type === "single_choice" && question.options?.map((opt, i) => (
        <button key={i} onClick={() => !submitted && setSelected(i)} disabled={submitted}
          className={`w-full text-left px-4 py-3 rounded-xl text-sm transition-all duration-150 flex items-center gap-3
            ${submitted && i === question.answer ? "bg-[var(--success)]/8 border-2 border-[var(--success)]" : ""}
            ${submitted && i === selected && i !== question.answer ? "bg-[var(--error)]/8 border-2 border-[var(--error)]" : ""}
            ${!submitted && selected === i ? "bg-[var(--accent)]/5 border-2 border-[var(--accent)]" : "border-2 border-[var(--border)] hover:border-[var(--accent)]/40"}
            ${submitted ? "cursor-default opacity-80" : "cursor-pointer active:scale-[0.98]"}`}>
          <span className={`w-6 h-6 rounded-full border-2 flex items-center justify-center text-xs font-medium shrink-0
            ${submitted && i === question.answer ? "border-[var(--success)] bg-[var(--success)] text-white" : ""}
            ${submitted && i === selected && i !== question.answer ? "border-[var(--error)] bg-[var(--error)] text-white" : ""}
            ${!submitted && selected === i ? "border-[var(--accent)] bg-[var(--accent)] text-white" : "border-[var(--border)]"}`}>
            {submitted && i === question.answer ? <CheckIcon /> : submitted && i === selected ? <XIcon /> : String.fromCharCode(65 + i)}
          </span>
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
            className={`w-full text-left px-4 py-3 rounded-xl text-sm transition-all duration-150 flex items-center gap-3
              ${isSelected ? "bg-[var(--accent)]/5 border-2 border-[var(--accent)]" : "border-2 border-[var(--border)] hover:border-[var(--accent)]/40"}
              ${submitted ? "cursor-default opacity-80" : "cursor-pointer active:scale-[0.98]"}`}>
            <span className={`w-6 h-6 rounded border-2 flex items-center justify-center text-xs shrink-0
              ${isSelected ? "border-[var(--accent)] bg-[var(--accent)] text-white" : "border-[var(--border)]"}`}>
              {isSelected ? <CheckIcon /> : ""}
            </span>
            <span>{opt}</span>
          </button>
        );
      })}
      {question.type === "fill_blank" && (
        <input value={fillAnswer} onChange={(e) => setFillAnswer(e.target.value)} placeholder="Type your answer..."
          disabled={submitted}
          className="input" />
      )}
      {question.type === "judgment" && (
        <div className="flex gap-3">
          <button onClick={() => !submitted && setJudgmentAnswer(true)} disabled={submitted}
            className={`flex-1 py-3 rounded-xl text-sm font-medium transition-all duration-150 flex items-center justify-center gap-2
              ${judgmentAnswer === true ? "bg-[var(--accent)] text-white border-2 border-[var(--accent)]" : "border-2 border-[var(--border)] hover:border-[var(--accent)]/40"}
              ${submitted ? "cursor-default" : "cursor-pointer active:scale-[0.98]"}`}>
            <CheckCircleIcon /> True
          </button>
          <button onClick={() => !submitted && setJudgmentAnswer(false)} disabled={submitted}
            className={`flex-1 py-3 rounded-xl text-sm font-medium transition-all duration-150 flex items-center justify-center gap-2
              ${judgmentAnswer === false ? "bg-[var(--error)] text-white border-2 border-[var(--error)]" : "border-2 border-[var(--border)] hover:border-[var(--error)]/40"}
              ${submitted ? "cursor-default" : "cursor-pointer active:scale-[0.98]"}`}>
            <XIcon /> False
          </button>
        </div>
      )}
      {!submitted && (
        <button onClick={checkAnswer} disabled={!canSubmit}
          className="btn btn-primary w-full mt-2 disabled:opacity-30 disabled:cursor-not-allowed">
          Submit Answer
        </button>
      )}

      {result.checked && result.correct && nextNodeTitle && onNextNode && (
        <div className="mt-3 p-4 bg-[var(--success)]/5 border border-[var(--success)]/30 rounded-xl animate-pop">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircleIcon />
            <span className="text-sm font-semibold text-[var(--success)]">Correct!</span>
          </div>
          {question.explanation && <p className="text-xs text-[var(--text-secondary)] mt-1">{question.explanation}</p>}
          <button onClick={onNextNode}
            className="btn btn-primary w-full mt-3 text-xs gap-1.5">
            <PlayIcon /> 开始下一个：{nextNodeTitle}
          </button>
        </div>
      )}
      {result.checked && !result.correct && (
        <div className="mt-3 p-4 bg-[var(--error)]/5 border border-[var(--error)]/30 rounded-xl animate-pop">
          <div className="flex items-center gap-2 mb-1">
            <XIcon />
            <span className="text-sm font-semibold text-[var(--error)]">Not quite</span>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">The correct answer is <span className="font-mono font-medium">{JSON.stringify(question.answer)}</span></p>
          {question.explanation && <p className="text-xs text-[var(--text-secondary)] mt-1">{question.explanation}</p>}
        </div>
      )}
    </div>
  );
});

/* ─── Reasoning Card ─── */
const ReasoningCard = memo(function ReasoningCard({ reasoning }: { reasoning: NonNullable<ReturnType<typeof useLearningStore.getState>["currentReasoning"]> }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="card overflow-hidden transition-all duration-300 animate-pop" style={{ maxHeight: expanded ? '500px' : '44px' }}>
      <button onClick={() => setExpanded(!expanded)} className="flex items-center gap-2.5 w-full text-left p-3.5">
        <BrainIcon />
        <span className="font-medium text-sm truncate flex-1">{reasoning.title}</span>
        <svg className={`w-4 h-4 text-[var(--text-muted)] transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg>
      </button>
      {expanded && (
        <div className="px-3.5 pb-3.5 space-y-2 border-t border-[var(--border)] pt-3">
          {reasoning.steps.map((step, i) => (
            <div key={i} className="pl-4 border-l-2 border-[var(--accent)]/40">
              <div className="font-medium text-sm">{step.title}</div>
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

  const deferredStreaming = useDeferredValue(streamingText);

  useEffect(() => {
    if (!chatContainerRef.current || !autoScrollRef.current) return;
    requestAnimationFrame(() => {
      if (!chatContainerRef.current) return;
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    });
  }, [messages, deferredStreaming]);

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

  useEffect(() => {
    if (cartridge && !currentNodeId) {
      const first = cartridge.nodes.find(n => n.status !== 'completed') || cartridge.nodes[0];
      if (first) selectNode(first.id);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cartridge]);

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
      } catch { appendStreamText(`Connection error.`); finalizeStream(currentNodeId); }
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
      appendStreamText(`\n\n${errMsg}`);
      finalizeStream(currentNodeId);
    }
    setIsStreaming(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input, currentNodeId, isStreaming, token, cartridgeId, nodeMessages]);

  const submitAnswer = useCallback(async (answer: string | number | number[], correct: boolean) => {
    if (!currentNodeId || !currentQuestion) return;
    const explanation = currentQuestion.explanation || "";
    
    // Convert answer to string properly (arrays need JSON.stringify)
    const answerStr = Array.isArray(answer) ? JSON.stringify(answer) : String(answer);
    const correctAnswerStr = Array.isArray(currentQuestion.answer) 
      ? JSON.stringify(currentQuestion.answer) 
      : String(currentQuestion.answer);
    
    await api.submitAnswer({
      cartridge_id: cartridgeId, node_id: currentNodeId,
      question_type: currentQuestion.type, user_answer: answerStr,
      correct_answer: correctAnswerStr, correct,
    }).catch(() => {});

    setQuestion(null);
    const nodes = cartridge?.nodes || [];
    const idx = nodes.findIndex(n => n.id === currentNodeId);
    const nextNode = nodes[idx + 1];

    if (correct) {
      // 答对：只记录本地反馈，不触发 AI 回复，等用户手动选择下一步
      const feedbackText = nextNode
        ? `✅ 正确！${explanation}`
        : `✅ 正确！${explanation}\n✨ 节点已完成！`;
      addUserMessage(currentNodeId, feedbackText);
      finalizeStream(currentNodeId);
    } else {
      // 答错：让 AI 换个方式讲解
      const feedbackMsg = `❌ 不对，正确答案是 ${JSON.stringify(currentQuestion.answer)}。${explanation}\n\n请换个方式讲解。`;
      addUserMessage(currentNodeId, feedbackMsg);
      setIsStreaming(true);
      try {
        const history = (messages[currentNodeId] || []).map((m) => ({ role: m.role, content: m.content }));
        for await (const text of chatStream(cartridgeId, currentNodeId, feedbackMsg, history)) {
          appendStreamText(text);
        }
        finalizeStream(currentNodeId);
      } catch { appendStreamText(`\n\nError`); finalizeStream(currentNodeId); }
      setIsStreaming(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentNodeId, currentQuestion, cartridgeId, cartridge]);

  const nextNodeInfo = useMemo(() => {
    const nodes = cartridge?.nodes || [];
    const idx = nodes.findIndex(n => n.id === currentNodeId);
    const nextNode = nodes[idx + 1];
    return {
      title: nextNode?.title,
      select: nextNode ? () => selectNode(nextNode.id) : undefined,
      start: nextNode ? () => {
        selectNode(nextNode.id);
        // Wait for node selection, then start the lesson
        setTimeout(() => {
          const node = cartridge?.nodes.find(n => n.id === nextNode.id);
          if (!node) return;
          
          // Send "开始学习：XXX" message to start AI teaching
          addUserMessage(nextNode.id, `开始学习：${node.title}`);
          setIsStreaming(true);
          (async () => {
            try {
              const history = (messages[nextNode.id] || []).map((m) => ({ role: m.role, content: m.content }));
              for await (const text of chatStream(cartridgeId, nextNode.id, `开始学习：${node.title}`, history)) {
                appendStreamText(text);
              }
              finalizeStream(nextNode.id);
            } catch {
              appendStreamText(`\n\nError`);
              finalizeStream(nextNode.id);
            }
            setIsStreaming(false);
          })();
        }, 100);
      } : undefined
    };
  }, [cartridge, currentNodeId, selectNode, cartridgeId]);

  const displayStreaming = useMemo(() =>
    deferredStreaming.replace(/<<QUESTION>>[\s\S]*?<<\/QUESTION>>/g, "").replace(/<<REASONING>>[\s\S]*?<<\/REASONING>>/g, ""),
    [deferredStreaming]
  );

  return (
    <div className="h-screen flex relative bg-[var(--bg-primary)]">
      {/* Login Modal */}
      {showLogin && (
        <div className="fixed inset-0 bg-black/30 glass flex items-center justify-center z-50" onClick={(e) => e.target === e.currentTarget && setShowLogin(false)}>
          <div className="card p-8 max-w-sm w-full mx-4 animate-pop">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[var(--accent)] to-[var(--accent-light)] flex items-center justify-center text-white mx-auto mb-4">
              <SparklesIcon />
            </div>
            <h2 className="text-lg font-bold text-center mb-1">Welcome to Starlight</h2>
            <p className="text-sm text-[var(--text-secondary)] text-center mb-6">Sign in to continue learning.</p>
            <div className="flex gap-3">
              <button onClick={() => router.push("/login")} className="btn btn-primary flex-1">Log in</button>
              <button onClick={() => router.push("/register")} className="btn flex-1">Register</button>
            </div>
            <button onClick={() => setShowLogin(false)} className="mt-3 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors w-full text-center">Cancel</button>
          </div>
        </div>
      )}

      {/* Mobile overlay */}
      {sidebarOpen && <div className="fixed inset-0 bg-black/20 z-30 md:hidden backdrop-blur-sm transition-opacity" onClick={() => setSidebarOpen(false)} />}

      {/* Sidebar */}
      <div className={`w-72 border-r border-[var(--border)] bg-[var(--bg-card)] flex flex-col z-40 shrink-0
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
      <div className="flex-1 flex flex-col min-w-0 bg-[var(--bg-primary)]">
        {/* Top bar */}
        <div className="h-14 px-4 border-b border-[var(--border)] glass flex items-center gap-3 shrink-0 sticky top-0 z-10">
          <button onClick={() => setSidebarOpen(true)} className="icon-btn md:hidden" aria-label="Menu">
            <MenuIcon />
          </button>
          <div className="flex-1 min-w-0">
            <h2 className="font-semibold text-sm truncate" style={{ fontFamily: "var(--font-geist-mono)" }}>
              {currentNode ? currentNode.title : "Select a topic to start"}
            </h2>
            {currentNode && (
              <p className="text-[11px] text-[var(--text-muted)] truncate mt-0.5">{currentNode.id}</p>
            )}
          </div>
          {currentNode && (
            <span className={`badge shrink-0 ${
              currentNode.difficulty <= 1 ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400" :
              currentNode.difficulty <= 2 ? "bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400" :
              "bg-rose-50 text-rose-600 dark:bg-rose-900/30 dark:text-rose-400"
            }`}>
              {currentNode.difficulty <= 1 ? "Beginner" : currentNode.difficulty <= 2 ? "Intermediate" : "Advanced"}
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
            <div className="text-center text-[var(--text-muted)] mt-16 animate-fade">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[var(--accent)] to-[var(--accent-light)] flex items-center justify-center text-white mx-auto mb-6" style={{ animation: "float 3s ease-in-out infinite" }}>
                <SparklesIcon />
              </div>
              <h3 className="text-lg font-bold text-[var(--text-primary)] mb-2">{cartridge.title}</h3>
              <p className="text-sm mb-8 max-w-xs mx-auto">Choose a topic from the sidebar to begin</p>
              {(() => {
                const first = cartridge.nodes.find(n => n.status !== 'completed');
                return first ? (
                  <button onClick={() => selectNode(first.id)} className="btn btn-primary gap-1.5">
                    <PlayIcon /> Start with &ldquo;{first.title}&rdquo;
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

          {/* Streaming */}
          {displayStreaming && (
            <div className="flex justify-start animate-fade">
              <div className="flex gap-2.5 max-w-[85%]">
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[var(--accent)] to-[var(--accent-light)] flex items-center justify-center text-white shrink-0 mt-1">
                  <SparklesIcon />
                </div>
                <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl rounded-bl-md px-4 py-3 min-h-[48px]">
                  <StreamingText text={displayStreaming} />
                </div>
              </div>
            </div>
          )}

          {/* Typing indicator before stream starts */}
          {isStreaming && !displayStreaming && <TypingIndicator />}

          {/* Question */}
          {currentQuestion && !displayStreaming && !isStreaming && (
            <div className="flex justify-start animate-pop">
              <div className="card p-5 max-w-lg">
                <div className="flex items-center gap-2.5 mb-4">
                  <span className="text-lg">{currentQuestion.type === "single_choice" ? "🔍" : currentQuestion.type === "multi_choice" ? "🎯" : currentQuestion.type === "fill_blank" ? "📝" : "✅"}</span>
                  <h3 className="font-semibold text-sm flex-1">{currentQuestion.question}</h3>
                </div>
                <QuestionCard
                  question={currentQuestion}
                  onSubmit={submitAnswer}
                  nextNodeTitle={nextNodeInfo.title}
                  onNextNode={nextNodeInfo.start}
                />
              </div>
            </div>
          )}

          {/* Reasoning */}
          {currentReasoning && !displayStreaming && !isStreaming && <ReasoningCard reasoning={currentReasoning} />}

          <div className="h-2" />
        </div>

        {/* Input */}
        <div className="px-3 md:px-6 py-3 border-t border-[var(--border)] glass shrink-0">
          <div className="flex gap-2 max-w-4xl mx-auto">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }}}
              placeholder={currentNodeId ? "Ask anything..." : "Select a topic first"}
              disabled={!currentNodeId || isStreaming}
              className="input flex-1 disabled:opacity-30"
            />
            <button onClick={sendMessage} disabled={!currentNodeId || isStreaming || !input.trim()}
              className="btn btn-primary px-4 rounded-xl disabled:opacity-30 disabled:cursor-not-allowed shrink-0">
              {isStreaming ? <SpinnerIcon /> : <SendIcon />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
