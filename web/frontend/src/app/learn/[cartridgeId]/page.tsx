"use client";
import { useEffect, useState, useRef, useCallback } from "react";
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

export default function LearnPage() {
  const params = useParams();
  const router = useRouter();
  const cartridgeId = params.cartridgeId as string;
  const { token } = useAuthStore();
  const { currentNodeId, messages, streamingText, isStreaming, currentQuestion, currentReasoning, wrongCount,
    setCurrentNode, addUserMessage, appendStreamText, finalizeStream, setIsStreaming, setQuestion, addWrongCount, resetWrongCount } = useLearningStore();

  const [cartridge, setCartridge] = useState<CartridgeData | null>(null);
  const [input, setInput] = useState("");
  const [showLogin, setShowLogin] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(true);

  // Smart scroll: only auto-scroll if user is near bottom
  useEffect(() => {
    if (!chatContainerRef.current || !autoScrollRef.current) return;
    const el = chatContainerRef.current;
    el.scrollTop = el.scrollHeight;
  }, [messages, streamingText]);

  useEffect(() => {
    if (token) { api.getCartridge(cartridgeId).then(setCartridge).catch((err) => {
      if (err instanceof ApiError && err.status === 401) { setShowLogin(true); }
      else { showToast('error', `Failed to load cartridge: ${err.message}`); }
    }); }
    else { setShowLogin(true); }
  }, [cartridgeId, token]);

  const currentNode = cartridge?.nodes.find((n) => n.id === currentNodeId);
  const nodeMessages = currentNodeId ? messages[currentNodeId] || [] : [];

  // Auto-select first uncompleted node when cartridge loads
  useEffect(() => {
    if (cartridge && !currentNodeId) {
      const firstIncomplete = cartridge.nodes.find(n => n.status !== 'completed') || cartridge.nodes[0];
      if (firstIncomplete) {
        selectNode(firstIncomplete.id);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cartridge]);

  // Auto-greet when selecting a new node (no messages yet)
  useEffect(() => {
    if (!currentNodeId || !token || !cartridge) return;
    const existing = messages[currentNodeId];
    if (existing && existing.length > 0) return; // already has conversation
    
    const node = cartridge.nodes.find(n => n.id === currentNodeId);
    if (!node) return;

    // Send auto-greet
    const greetMsg = `开始学习：${node.title}`;
    addUserMessage(currentNodeId, greetMsg);
    setIsStreaming(true);
    (async () => {
      try {
        for await (const text of chatStream(cartridgeId, currentNodeId, greetMsg, [])) {
          appendStreamText(text);
        }
        finalizeStream(currentNodeId);
      } catch (err) {
        appendStreamText(`❌ Connection error. Please try again.`);
        finalizeStream(currentNodeId);
      }
      setIsStreaming(false);
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentNodeId, cartridge]);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const selectNode = useCallback((nodeId: string) => {
    setCurrentNode(nodeId);
    setQuestion(null);
    setSidebarOpen(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sendMessage = async () => {
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
      const msg = err instanceof ApiError ? err.message : 'Connection error. Please try again.';
      showToast('error', msg);
      appendStreamText(`\n\n❌ ${msg}`);
      finalizeStream(currentNodeId);
    }
    setIsStreaming(false);
  };

  const submitAnswer = async (answer: string | number | number[], correct: boolean) => {
    if (!currentNodeId || !currentQuestion) return;
    const explanation = currentQuestion.explanation || "";
    const wasCorrect = correct;

    await api.submitAnswer({ cartridge_id: cartridgeId, node_id: currentNodeId, question_type: currentQuestion.type, user_answer: String(answer), correct_answer: String(currentQuestion.answer), correct }).catch(() => {});

    // Clear current question
    resetWrongCount();
    setQuestion(null);

    // Show feedback and continue conversation
    let feedbackMsg: string;
    if (wasCorrect) {
      // Check if there's a next node to suggest
      const nodes = cartridge?.nodes || [];
      const currentIdx = nodes.findIndex(n => n.id === currentNodeId);
      const nextNode = nodes[currentIdx + 1];
      feedbackMsg = `✅ 正确！${explanation}\n\n${nextNode ? `下一个知识点是「${nextNode.title}」，请开始教我。` : '我已经完成了这个节点的学习，请总结一下。'}`;
    } else {
      feedbackMsg = `❌ 不对，正确答案是 ${JSON.stringify(currentQuestion.answer)}。${explanation}\n\n请再详细讲解一下这个概念，换个方式让我理解。`;
    }

    addUserMessage(currentNodeId, feedbackMsg);
    setIsStreaming(true);
    try {
      const history = (messages[currentNodeId] || []).map((m) => ({ role: m.role, content: m.content }));
      for await (const text of chatStream(cartridgeId, currentNodeId, feedbackMsg, history)) {
        appendStreamText(text);
      }
      finalizeStream(currentNodeId);
    } catch (err) {
      appendStreamText(`\n\n❌ Error: ${err}`);
      finalizeStream(currentNodeId);
    }
    setIsStreaming(false);
  };

  return (
    <div className="h-screen flex relative">
      {/* Login Modal */}
      {showLogin && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="pixel-card p-8 max-w-sm w-full">
            <h2 className="text-xl font-bold mb-4">🔐 Login to Learn</h2>
            <p className="text-sm text-[var(--text-secondary)] mb-4">Please login or register to start learning.</p>
            <div className="flex gap-3">
              <button onClick={() => router.push("/login")} className="pixel-btn pixel-btn-primary flex-1">Login</button>
              <button onClick={() => router.push("/register")} className="pixel-btn flex-1">Register</button>
            </div>
            <button onClick={() => setShowLogin(false)} className="mt-3 text-sm text-[var(--text-muted)]">Cancel</button>
          </div>
        </div>
      )}

      {/* Sidebar Overlay (mobile) */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/40 z-30 md:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <div className={`w-72 border-r-2 border-[var(--border)] bg-white flex flex-col z-40 transition-transform duration-200
        fixed md:relative inset-y-0 left-0 h-full
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}>
        <div className="p-4 border-b-2 border-[var(--border)]">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-sm" style={{ fontFamily: "'JetBrains Mono', monospace" }}>{cartridge?.title || "Loading..."}</h2>
            <button onClick={() => router.push(`/learn/${cartridgeId}/dag`)} className="pixel-btn text-xs px-2 py-1" title="View DAG">🗺️ DAG</button>
          </div>
          {cartridge && (
            <div className="mt-2">
              <div className="flex justify-between text-xs text-[var(--text-muted)] mb-1">
                <span>{cartridge.progress.completed}/{cartridge.progress.total}</span>
                <span>{Math.round((cartridge.progress.completed / cartridge.progress.total) * 100)}%</span>
              </div>
              <div className="h-2 bg-[var(--bg-primary)] rounded-full overflow-hidden">
                <div className="h-full bg-[var(--accent-light)] transition-all" style={{ width: `${(cartridge.progress.completed / cartridge.progress.total) * 100}%` }} />
              </div>
            </div>
          )}
        </div>
        <div className="flex-1 overflow-y-auto">
          {cartridge?.nodes.map((node) => (
            <button key={node.id} onClick={() => selectNode(node.id)}
              className={`w-full text-left px-4 py-3 text-sm border-b border-[var(--border-light)] flex items-center gap-2 transition-colors
                ${currentNodeId === node.id ? "bg-[var(--accent-light)]/10 border-l-4 border-l-[var(--accent)]" : "hover:bg-[var(--bg-primary)]"}`}>
              <span>{node.status === "completed" ? "🟩" : node.status === "in_progress" ? "🟨" : "⬜"}</span>
              <span className="truncate">{node.title}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Top bar */}
        <div className="px-4 py-3 border-b-2 border-[var(--border)] bg-white flex items-center gap-3">
          {/* Mobile hamburger */}
          <button onClick={() => setSidebarOpen(true)} className="md:hidden pixel-btn text-sm px-2 py-1" aria-label="Open sidebar">☰</button>
          <h2 className="font-bold text-sm md:text-base truncate" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            {currentNode ? `${currentNode.id}: ${currentNode.title}` : "Select a node to start"}
          </h2>
          {/* Mobile DAG button */}
          <button onClick={() => router.push(`/learn/${cartridgeId}/dag`)} className="md:hidden pixel-btn text-xs px-2 py-1 ml-auto">🗺️</button>
        </div>

        {/* Chat messages */}
        <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-6 space-y-4" onScroll={() => {
          if (!chatContainerRef.current) return;
          const el = chatContainerRef.current;
          autoScrollRef.current = (el.scrollHeight - el.scrollTop - el.clientHeight) < 100;
        }}>
          {!currentNodeId && cartridge && (
            <div className="text-center text-[var(--text-muted)] mt-20 animate-slide">
              <div className="text-4xl mb-4">🎮</div>
              <p className="mb-2">Welcome to <strong>{cartridge.title}</strong>!</p>
              <p className="text-sm mb-4">Select a node from the sidebar to start learning</p>
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

          {nodeMessages.map((msg, i) => (
            <div key={i} className={`animate-slide ${msg.role === "user" ? "flex justify-end" : ""}`}>
              <div className={`max-w-[80%] p-4 rounded-lg ${msg.role === "user" ? "bg-[var(--accent)] text-white" : "pixel-card"}`}>
                <div className="chat-markdown text-sm">
                  <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>{msg.content}</ReactMarkdown>
                </div>
              </div>
            </div>
          ))}

          {/* Streaming text */}
          {streamingText && (
            <div className="animate-slide">
              <div className="max-w-[80%] p-4 pixel-card min-h-[60px]">
                <div className="chat-markdown text-sm">
                  <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                    {streamingText.replace(/<<QUESTION>>[\s\S]*?<<\/QUESTION>>/g, "").replace(/<<REASONING>>[\s\S]*?<<\/REASONING>>/g, "")}
                  </ReactMarkdown>
                </div>
                <span className="inline-block w-2 h-4 bg-[var(--accent)] animate-pulse ml-1" />
              </div>
            </div>
          )}

          {/* Question Card */}
          {currentQuestion && !streamingText && (
            <div className="animate-pop">
              <div className="pixel-card p-6 max-w-lg">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-lg">{currentQuestion.type === "single_choice" ? "🔍" : currentQuestion.type === "multi_choice" ? "🎯" : currentQuestion.type === "fill_blank" ? "📝" : "✅"}</span>
                  <h3 className="font-bold text-sm" style={{ fontFamily: "'JetBrains Mono', monospace" }}>{currentQuestion.question}</h3>
                </div>
                {/* Options will be rendered by QuestionCard component */}
                <QuestionCard 
                  question={currentQuestion} 
                  onSubmit={submitAnswer} 
                  wrongCount={wrongCount}
                  nextNodeTitle={(() => {
                    const nodes = cartridge?.nodes || [];
                    const idx = nodes.findIndex(n => n.id === currentNodeId);
                    return nodes[idx + 1]?.title;
                  })()}
                  onNextNode={(() => {
                    const nodes = cartridge?.nodes || [];
                    const idx = nodes.findIndex(n => n.id === currentNodeId);
                    const next = nodes[idx + 1];
                    return next ? () => selectNode(next.id) : undefined;
                  })()}
                />
              </div>
            </div>
          )}

          {/* Reasoning Card */}
          {currentReasoning && !streamingText && <ReasoningCard reasoning={currentReasoning} />}

          <div className="h-4" />
        </div>

        {/* Input */}
        <div className="px-3 md:px-6 py-3 md:py-4 border-t-2 border-[var(--border)] bg-white">
          <div className="flex gap-2 md:gap-3">
            <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
              placeholder={currentNodeId ? "Type your answer..." : "Select a node first"}
              disabled={!currentNodeId || isStreaming}
              className="flex-1 px-3 md:px-4 py-2 md:py-3 border-2 border-[var(--border)] rounded-lg bg-white focus:outline-none focus:border-[var(--accent-light)] disabled:opacity-50 text-sm" />
            <button onClick={sendMessage} disabled={!currentNodeId || isStreaming || !input.trim()}
              className="pixel-btn pixel-btn-primary px-4 md:px-6 disabled:opacity-50 text-sm">
              {isStreaming ? "..." : "Send"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* Question Card Component */
function QuestionCard({ question, onSubmit, wrongCount, nextNodeTitle, onNextNode }: { 
  question: NonNullable<ReturnType<typeof useLearningStore.getState>["currentQuestion"]>; 
  onSubmit: (answer: string | number | number[], correct: boolean) => Promise<void>; 
  wrongCount: number;
  nextNodeTitle?: string;
  onNextNode?: () => void;
}) {
  const [selected, setSelected] = useState<number | number[]>(question.type === "multi_choice" ? [] : -1);
  const [fillAnswer, setFillAnswer] = useState("");
  const [judgmentAnswer, setJudgmentAnswer] = useState<boolean | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [result, setResult] = useState<{correct: boolean; checked: boolean}>({correct: false, checked: false});

  const checkAnswer = () => {
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
    setSubmitted(true);
    setResult({ correct, checked: true });
    onSubmit(answerStr, correct);
  };

  return (
    <div>
      {question.type === "single_choice" && question.options?.map((opt, i) => (
        <button key={i} onClick={() => !submitted && setSelected(i)}
          className={`w-full text-left p-3 mb-2 border-2 rounded text-sm transition-colors ${selected === i ? "border-[var(--accent)] bg-[var(--accent-light)]/10" : "border-[var(--border-light)] hover:border-[var(--accent)]"}`}>
          {String.fromCharCode(65 + i)}. {opt}
        </button>
      ))}
      {question.type === "multi_choice" && question.options?.map((opt, i) => (
        <button key={i} onClick={() => { if (submitted) return; const s = [...(selected as number[])]; const idx = s.indexOf(i); if (idx >= 0) { s.splice(idx, 1); } else { s.push(i); } setSelected(s); }}
          className={`w-full text-left p-3 mb-2 border-2 rounded text-sm transition-colors ${(selected as number[]).includes(i) ? "border-[var(--accent)] bg-[var(--accent-light)]/10" : "border-[var(--border-light)] hover:border-[var(--accent)]"}`}
        >
          {String.fromCharCode(65 + i)}. {opt}
        </button>
      ))}
      {question.type === "fill_blank" && (
        <input value={fillAnswer} onChange={(e) => setFillAnswer(e.target.value)} placeholder="Type your answer..."
          className="w-full p-3 border-2 border-[var(--border)] rounded text-sm focus:border-[var(--accent-light)] focus:outline-none" />
      )}
      {question.type === "judgment" && (
        <div className="flex gap-4">
          <button onClick={() => !submitted && setJudgmentAnswer(true)} className={`flex-1 p-3 border-2 rounded text-sm ${judgmentAnswer === true ? "border-[var(--accent)] bg-[var(--accent-light)]/10" : "border-[var(--border-light)]"}`}>✅ True</button>
          <button onClick={() => !submitted && setJudgmentAnswer(false)} className={`flex-1 p-3 border-2 rounded text-sm ${judgmentAnswer === false ? "border-[var(--error)] bg-red-50" : "border-[var(--border-light)]"}`}>❌ False</button>
        </div>
      )}
      {!submitted && (
        <button onClick={checkAnswer} disabled={
          (question.type === 'multi_choice' && (selected as number[]).length === 0) ||
          (question.type === 'single_choice' && (selected as number) === -1) ||
          (question.type === 'fill_blank' && fillAnswer === '') ||
          (question.type === 'judgment' && judgmentAnswer === null)
        } className="pixel-btn pixel-btn-primary w-full mt-3 text-sm disabled:opacity-50">Submit</button>
      )}
      {result.checked && result.correct && (
        <div className="mt-3 p-3 bg-[#d8f5e2] border-2 border-[var(--success)] rounded text-sm text-center animate-pop">
          ✅ 正确！{question.explanation || 'Great job!'}
          {nextNodeTitle && onNextNode && (
            <button onClick={onNextNode} className="pixel-btn pixel-btn-primary w-full mt-3 text-sm">
              ▶ 下一个知识点：{nextNodeTitle}
            </button>
          )}
        </div>
      )}
      {result.checked && !result.correct && (
        <div className="mt-3 p-3 bg-red-50 border-2 border-[var(--error)] rounded text-sm text-center animate-pop">
          ❌ 不对！正确答案是 {JSON.stringify(question.answer)}
          {question.explanation && <p className="mt-1 text-[var(--text-secondary)]">{question.explanation}</p>}
        </div>
      )}
      {submitted && wrongCount >= 3 && (
        <div className="mt-3 p-3 bg-yellow-50 border-2 border-[var(--warning)] rounded text-sm">
          💡 You seem stuck. Try reviewing the basics first!
        </div>
      )}
    </div>
  );
}

/* Reasoning Card Component */
function ReasoningCard({ reasoning }: { reasoning: NonNullable<ReturnType<typeof useLearningStore.getState>["currentReasoning"]> }) {
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
}
