"use client";
import { useEffect, useState, useRef, useCallback, useMemo, memo } from "react";
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

/* ─── Memoized Markdown renderer ─── */
const MarkdownContent = memo(function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="chat-markdown text-sm">
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>{content}</ReactMarkdown>
    </div>
  );
});

/* ─── Chat Message (memoized to avoid re-rendering all messages on stream) ─── */
const ChatMessage = memo(function ChatMessage({ msg }: { msg: { role: string; content: string } }) {
  return (
    <div className={`animate-slide ${msg.role === "user" ? "flex justify-end" : ""}`}>
      <div className={`max-w-[85%] p-4 rounded-xl ${msg.role === "user"
        ? "bg-[var(--accent)] text-white rounded-br-sm"
        : "pixel-card rounded-bl-sm"
      }`}>
        <MarkdownContent content={msg.content} />
      </div>
    </div>
  );
});

/* ─── Sidebar ─── */
function Sidebar({ cartridge, currentNodeId, onSelectNode, onDAG, onBack }: {
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
          <button onClick={onBack} className="text-xs text-[var(--text-muted)] hover:text-[var(--accent)] transition-colors">← Back</button>
          <button onClick={onDAG} className="text-xs px-2 py-1 rounded border border-[var(--border)] hover:bg-[var(--accent)] hover:text-white transition-colors">🗺️</button>
        </div>
        <h2 className="font-bold text-sm truncate" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
          {cartridge?.title || "Loading..."}
        </h2>
        {cartridge && (
          <div className="mt-2">
            <div className="flex justify-between text-xs text-[var(--text-muted)] mb-1">
              <span>{cartridge.progress.completed}/{cartridge.progress.total}</span>
              <span>{Math.round((cartridge.progress.completed / cartridge.progress.total) * 100)}%</span>
            </div>
            <div className="h-2 bg-[var(--bg-primary)] rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-[var(--accent)] to-[var(--accent-light)] transition-all duration-500"
                style={{ width: `${(cartridge.progress.completed / cartridge.progress.total) * 100}%` }} />
            </div>
          </div>
        )}
      </div>
      <div className="flex-1 overflow-y-auto">
        {cartridge?.nodes.map((node) => (
          <button key={node.id} onClick={() => onSelectNode(node.id)}
            className={`w-full text-left px-4 py-3 text-sm border-b border-[var(--border-light)] flex items-center gap-2 transition-all duration-150
              ${currentNodeId === node.id
                ? "bg-[var(--accent)]/10 border-l-[3px] border-l-[var(--accent)] font-semibold"
                : "hover:bg-[var(--bg-primary)]"}`}>
            <span className="text-xs">{node.status === "completed" ? "🟩" : node.status === "in_progress" ? "🟨" : "⬜"}</span>
            <span className="truncate flex-1">{node.title}</span>
            {node.status === "completed" && <span className="text-xs text-[var(--accent-light)]">✓</span>}
          </button>
        ))}
      </div>
    </>
  );
}

/* ─── Question Card ─── */
function QuestionCard({ question, onSubmit, nextNodeTitle, onNextNode }: {
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

  return (
    <div className="space-y-2">
      {question.type === "single_choice" && question.options?.map((opt, i) => (
        <button key={i} onClick={() => !submitted && setSelected(i)}
          disabled={submitted}
          className={`w-full text-left p-3 border-2 rounded-lg text-sm transition-all duration-150
            ${submitted && i === question.answer ? "border-[var(--success)] bg-[var(--success)]/10" : ""}
            ${submitted && i === selected && i !== question.answer ? "border-[var(--error)] bg-[var(--error)]/10" : ""}
            ${!submitted && selected === i ? "border-[var(--accent)] bg-[var(--accent)]/10 scale-[1.01]" : "border-[var(--border-light)] hover:border-[var(--accent)]"}
            ${submitted ? "cursor-default" : "cursor-pointer"}`}>
          <span className="font-mono text-xs mr-2">{String.fromCharCode(65 + i)}.</span>{opt}
        </button>
      ))}
      {question.type === "multi_choice" && question.options?.map((opt, i) => (
        <button key={i} onClick={() => {
          if (submitted) return;
          const s = [...(selected as number[])];
          const idx = s.indexOf(i);
          if (idx >= 0) s.splice(idx, 1); else s.push(i);
          setSelected(s);
        }}
          disabled={submitted}
          className={`w-full text-left p-3 border-2 rounded-lg text-sm transition-all duration-150
            ${(selected as number[]).includes(i) ? "border-[var(--accent)] bg-[var(--accent)]/10" : "border-[var(--border-light)] hover:border-[var(--accent)]"}
            ${submitted ? "cursor-default" : "cursor-pointer"}`}>
          <span className="font-mono text-xs mr-2">{String.fromCharCode(65 + i)}.</span>{opt}
          {(selected as number[]).includes(i) && <span className="float-right">✓</span>}
        </button>
      ))}
      {question.type === "fill_blank" && (
        <input value={fillAnswer} onChange={(e) => setFillAnswer(e.target.value)} placeholder="Type your answer..."
          disabled={submitted}
          className="w-full p-3 border-2 border-[var(--border)] rounded-lg text-sm focus:border-[var(--accent-light)] focus:outline-none transition-colors" />
      )}
      {question.type === "judgment" && (
        <div className="flex gap-3">
          <button onClick={() => !submitted && setJudgmentAnswer(true)} disabled={submitted}
            className={`flex-1 p-3 border-2 rounded-lg text-sm transition-all ${judgmentAnswer === true ? "border-[var(--accent)] bg-[var(--accent)]/10 font-bold" : "border-[var(--border-light)]"}`}>
            ✅ True
          </button>
          <button onClick={() => !submitted && setJudgmentAnswer(false)} disabled={submitted}
            className={`flex-1 p-3 border-2 rounded-lg text-sm transition-all ${judgmentAnswer === false ? "border-[var(--error)] bg-[var(--error)]/10 font-bold" : "border-[var(--border-light)]"}`}>
            ❌ False
          </button>
        </div>
      )}
      {!submitted && (
        <button onClick={checkAnswer} disabled={!canSubmit}
          className="pixel-btn pixel-btn-primary w-full mt-2 text-sm disabled:opacity-40 disabled:cursor-not-allowed transition-opacity">
          Submit Answer
        </button>
      )}
      {result.checked && result.correct && (
        <div className="mt-2 p-4 bg-[var(--success)]/10 border-2 border-[var(--success)] rounded-lg animate-pop">
          <p className="text-sm font-bold text-center">✅ 正确！</p>
          {question.explanation && <p className="text-xs text-[var(--text-secondary)] text-center mt-1">{question.explanation}</p>}
          {nextNodeTitle && onNextNode && (
            <button onClick={onNextNode}
              className="pixel-btn pixel-btn-primary w-full mt-3 text-sm flex items-center justify-center gap-2">
              ▶ 下一个知识点：{nextNodeTitle}
            </button>
          )}
        </div>
      )}
      {result.checked && !result.correct && (
        <div className="mt-2 p-4 bg-[var(--error)]/10 border-2 border-[var(--error)] rounded-lg animate-pop">
          <p className="text-sm font-bold text-center">❌ 不对！正确答案是 <span className="font-mono">{JSON.stringify(question.answer)}</span></p>
          {question.explanation && <p className="text-xs text-[var(--text-secondary)] text-center mt-1">{question.explanation}</p>}
        </div>
      )}
    </div>
  );
}

/* ─── Reasoning Card ─── */
const ReasoningCard = memo(function ReasoningCard({ reasoning }: { reasoning: NonNullable<ReturnType<typeof useLearningStore.getState>["currentReasoning"]> }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="pixel-card p-4 max-w-lg">
      <button onClick={() => setExpanded(!expanded)} className="flex items-center gap-2 w-full text-left">
        <span>🧠</span>
        <span className="font-bold text-sm" style={{ fontFamily: "'JetBrains Mono', monospace" }}>{reasoning.title}</span>
        <span className="ml-auto text-xs text-[var(--text-muted)]">{expanded ? "▼" : "▶"}</span>
      </button>
      {expanded && (
        <div className="mt-3 space-y-2 animate-slide">
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
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(true);
  const streamingRef = useRef<HTMLDivElement>(null);

  // Smart scroll
  useEffect(() => {
    if (!chatContainerRef.current || !autoScrollRef.current) return;
    const el = chatContainerRef.current;
    requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; });
  }, [messages, streamingText]);

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
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentNodeId, cartridge]);

  const selectNode = useCallback((nodeId: string) => {
    setCurrentNode(nodeId);
    setQuestion(null);
    setSidebarOpen(false);
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

  // Memoize next node info
  const nextNodeInfo = useMemo(() => {
    const nodes = cartridge?.nodes || [];
    const idx = nodes.findIndex(n => n.id === currentNodeId);
    return { title: nodes[idx + 1]?.title, select: nodes[idx + 1] ? () => selectNode(nodes[idx + 1].id) : undefined };
  }, [cartridge, currentNodeId, selectNode]);

  // Clean streaming text for display
  const displayStreaming = useMemo(() =>
    streamingText.replace(/<<QUESTION>>[\s\S]*?<<\/QUESTION>>/g, "").replace(/<<REASONING>>[\s\S]*?<<\/REASONING>>/g, ""),
    [streamingText]
  );

  return (
    <div className="h-screen flex relative bg-white">
      {/* Login Modal */}
      {showLogin && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm">
          <div className="pixel-card p-8 max-w-sm w-full mx-4 animate-pop">
            <h2 className="text-xl font-bold mb-4">🔐 Login to Learn</h2>
            <p className="text-sm text-[var(--text-secondary)] mb-4">Please login or register to start learning.</p>
            <div className="flex gap-3">
              <button onClick={() => router.push("/login")} className="pixel-btn pixel-btn-primary flex-1">Login</button>
              <button onClick={() => router.push("/register")} className="pixel-btn flex-1">Register</button>
            </div>
            <button onClick={() => setShowLogin(false)} className="mt-3 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)]">Cancel</button>
          </div>
        </div>
      )}

      {/* Mobile sidebar overlay */}
      {sidebarOpen && <div className="fixed inset-0 bg-black/40 z-30 md:hidden backdrop-blur-sm" onClick={() => setSidebarOpen(false)} />}

      {/* Sidebar */}
      <div className={`w-72 border-r-2 border-[var(--border)] bg-white flex flex-col z-40 transition-transform duration-200 ease-out
        fixed md:relative inset-y-0 left-0 h-full
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}>
        <Sidebar
          cartridge={cartridge} currentNodeId={currentNodeId}
          onSelectNode={selectNode}
          onDAG={() => router.push(`/learn/${cartridgeId}/dag`)}
          onBack={() => router.push("/")}
        />
      </div>

      {/* Main Chat */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <div className="h-14 px-4 border-b-2 border-[var(--border)] bg-white flex items-center gap-3 shrink-0">
          <button onClick={() => setSidebarOpen(true)} className="md:hidden p-2 rounded-lg hover:bg-[var(--bg-primary)] transition-colors" aria-label="Menu">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
          </button>
          <h2 className="font-bold text-sm md:text-base truncate flex-1" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            {currentNode ? `${currentNode.id}: ${currentNode.title}` : "Select a node to start"}
          </h2>
          {currentNode && (
            <span className={`text-xs px-2 py-1 rounded-full border ${
              currentNode.difficulty <= 1 ? "border-green-300 text-green-700 bg-green-50" :
              currentNode.difficulty <= 2 ? "border-yellow-300 text-yellow-700 bg-yellow-50" :
              "border-red-300 text-red-700 bg-red-50"
            }`}>
              {currentNode.difficulty <= 1 ? "Easy" : currentNode.difficulty <= 2 ? "Medium" : "Hard"}
            </span>
          )}
        </div>

        {/* Chat area */}
        <div ref={chatContainerRef} className="flex-1 overflow-y-auto px-4 md:px-6 py-4 space-y-3" onScroll={() => {
          if (!chatContainerRef.current) return;
          const el = chatContainerRef.current;
          autoScrollRef.current = (el.scrollHeight - el.scrollTop - el.clientHeight) < 120;
        }}>
          {/* Welcome */}
          {!currentNodeId && cartridge && (
            <div className="text-center text-[var(--text-muted)] mt-16 animate-slide">
              <div className="text-5xl mb-4">🎮</div>
              <p className="mb-2 text-lg font-semibold">Welcome to <strong>{cartridge.title}</strong></p>
              <p className="text-sm mb-6">Select a node from the sidebar to start learning</p>
              {(() => {
                const first = cartridge.nodes.find(n => n.status !== 'completed');
                return first ? (
                  <button onClick={() => selectNode(first.id)} className="pixel-btn pixel-btn-primary text-sm">
                    ▶ Start from「{first.title}」
                  </button>
                ) : null;
              })()}
            </div>
          )}

          {/* Messages */}
          {nodeMessages.map((msg, i) => (
            <ChatMessage key={`${currentNodeId}-${i}`} msg={msg} />
          ))}

          {/* Streaming */}
          {displayStreaming && (
            <div className="animate-slide">
              <div className="max-w-[85%] p-4 pixel-card rounded-xl rounded-bl-sm min-h-[48px]">
                <MarkdownContent content={displayStreaming} />
                <span className="inline-block w-1.5 h-4 bg-[var(--accent)] animate-pulse ml-1 rounded-sm" />
              </div>
            </div>
          )}

          {/* Question */}
          {currentQuestion && !displayStreaming && (
            <div className="animate-pop">
              <div className="pixel-card p-5 max-w-lg rounded-xl">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-lg">{currentQuestion.type === "single_choice" ? "🔍" : currentQuestion.type === "multi_choice" ? "🎯" : currentQuestion.type === "fill_blank" ? "📝" : "✅"}</span>
                  <h3 className="font-bold text-sm" style={{ fontFamily: "'JetBrains Mono', monospace" }}>{currentQuestion.question}</h3>
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
          {currentReasoning && !displayStreaming && <ReasoningCard reasoning={currentReasoning} />}

          <div className="h-2" />
        </div>

        {/* Input */}
        <div className="px-3 md:px-6 py-3 border-t-2 border-[var(--border)] bg-white shrink-0">
          <div className="flex gap-2 max-w-4xl mx-auto">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }}}
              placeholder={currentNodeId ? "Type your answer..." : "Select a node first"}
              disabled={!currentNodeId || isStreaming}
              className="flex-1 px-4 py-2.5 border-2 border-[var(--border)] rounded-xl bg-[var(--bg-primary)] focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/20 disabled:opacity-40 text-sm transition-all"
            />
            <button onClick={sendMessage} disabled={!currentNodeId || isStreaming || !input.trim()}
              className="pixel-btn pixel-btn-primary px-5 disabled:opacity-40 disabled:cursor-not-allowed text-sm rounded-xl transition-opacity">
              {isStreaming ? <span className="flex items-center gap-1"><span className="animate-spin">⏳</span></span> : "Send"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
