import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Auth store
interface AuthState {
  token: string | null;
  user: { id: number; email: string } | null;
  setAuth: (token: string, user: { id: number; email: string }) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => {
        localStorage.setItem('starlight-token', token);
        set({ token, user });
      },
      logout: () => {
        localStorage.removeItem('starlight-token');
        set({ token: null, user: null });
      },
    }),
    { name: 'starlight-auth' },
  ),
);

// Learning store
interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface Question {
  type: 'single_choice' | 'multi_choice' | 'fill_blank' | 'judgment';
  question: string;
  options?: string[];
  answer: number | boolean | string | number[];
  explanation: string;
}

interface Reasoning {
  title: string;
  steps: { title: string; content: string }[];
}

interface LearningState {
  cartridgeId: string | null;
  currentNodeId: string | null;
  messages: Record<string, ChatMessage[]>;
  streamingText: string;
  currentQuestion: Question | null;
  currentReasoning: Reasoning | null;
  isStreaming: boolean;
  wrongCount: number;

  setCartridge: (id: string) => void;
  setCurrentNode: (nodeId: string) => void;
  addUserMessage: (nodeId: string, content: string) => void;
  appendStreamText: (text: string) => void;
  finalizeStream: (nodeId: string) => void;
  clearStream: () => void;
  setIsStreaming: (v: boolean) => void;
  setQuestion: (q: Question | null) => void;
  setReasoning: (r: Reasoning | null) => void;
  addWrongCount: () => void;
  resetWrongCount: () => void;
}

export const useLearningStore = create<LearningState>()((set) => ({
  cartridgeId: null,
  currentNodeId: null,
  messages: {},
  streamingText: '',
  currentQuestion: null,
  currentReasoning: null,
  isStreaming: false,
  wrongCount: 0,

  setCartridge: (id) => set({ cartridgeId: id }),
  setCurrentNode: (nodeId) => set({ currentNodeId: nodeId }),
  addUserMessage: (nodeId, content) =>
    set((s) => ({
      messages: { ...s.messages, [nodeId]: [...(s.messages[nodeId] || []), { role: 'user' as const, content }] },
    })),
  appendStreamText: (text) => set((s) => ({ streamingText: s.streamingText + text })),
  finalizeStream: (nodeId) =>
    set((s) => {
      const streamText = s.streamingText;
      // Parse question tags
      let question: Question | null = null;
      let reasoning: Reasoning | null = null;
      let cleanText = streamText;

      const qMatch = streamText.match(/<<QUESTION>>([\s\S]*?)<<\/QUESTION>>/);
      if (qMatch) {
        try { question = JSON.parse(qMatch[1]); } catch {}
        cleanText = cleanText.replace(/<<QUESTION>>[\s\S]*?<<\/QUESTION>>/, '');
      }

      const rMatch = streamText.match(/<<REASONING>>([\s\S]*?)<<\/REASONING>>/);
      if (rMatch) {
        try { reasoning = JSON.parse(rMatch[1]); } catch {}
        cleanText = cleanText.replace(/<<REASONING>>[\s\S]*?<<\/REASONING>>/, '');
      }

      return {
        streamingText: '',
        currentQuestion: question,
        currentReasoning: reasoning,
        messages: {
          ...s.messages,
          [nodeId]: [...(s.messages[nodeId] || []), { role: 'assistant' as const, content: cleanText.trim() }],
        },
      };
    }),
  clearStream: () => set({ streamingText: '' }),
  setIsStreaming: (v) => set({ isStreaming: v }),
  setQuestion: (q) => set({ currentQuestion: q }),
  setReasoning: (r) => set({ currentReasoning: r }),
  addWrongCount: () => set((s) => ({ wrongCount: s.wrongCount + 1 })),
  resetWrongCount: () => set({ wrongCount: 0 }),
}));
