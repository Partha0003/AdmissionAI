import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  Send,
  Plus,
  BookOpen,
  ShieldCheck,
  AlertCircle,
  HelpCircle,
  Clock,
  Sparkles,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  X,
  FileText,
  Layers,
  Cpu,
} from 'lucide-react';
import { chatService } from '../services/chat';
import { ChatSession, ChatMessage, KnowledgeChunk } from '../types';

export const StudentChatAssistant: React.FC = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Source inspection modal
  const [selectedChunk, setSelectedChunk] = useState<KnowledgeChunk | null>(null);

  // Expanded citations map: messageId -> boolean
  const [expandedCitations, setExpandedCitations] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const suggestedPrompts = [
    'What should I do next in my admission journey?',
    'What documents are pending or need correction?',
    'What original certificates do I need for physical verification?',
    'How do I submit my Demand Draft for fee settlement?',
    'How do I know when my admission is confirmed in ERP?',
  ];

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadSessions = async () => {
    try {
      const data = await chatService.listSessions();
      setSessions(data);
      if (data.length > 0) {
        selectSession(data[0].id);
      } else {
        createNewSession('Initial Admission Inquiry');
      }
    } catch (err: any) {
      console.error('Failed to load sessions', err);
    }
  };

  const selectSession = async (sessionId: string) => {
    setError(null);
    try {
      const sessionData = await chatService.getSession(sessionId);
      setActiveSession(sessionData);
      setMessages(sessionData.messages || []);
    } catch (err: any) {
      setError('Unable to load chat session.');
    }
  };

  const createNewSession = async (title?: string) => {
    setError(null);
    try {
      const newSession = await chatService.createSession(title || 'New Admission Inquiry');
      setSessions((prev) => [newSession, ...prev]);
      setActiveSession(newSession);
      setMessages([]);
    } catch (err: any) {
      setError('Failed to create new chat session.');
    }
  };

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputQuery).trim();
    if (!query || !activeSession || isLoading) return;

    setInputQuery('');
    setError(null);

    // Optimistically append user message
    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      session_id: activeSession.id,
      user_id: activeSession.user_id,
      sender_role: 'USER',
      message: query,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setIsLoading(true);

    try {
      const assistantResponse = await chatService.sendMessage(
        activeSession.id,
        query,
        'mock',
        4
      );
      setMessages((prev) => {
        // Replace temp or append
        const filtered = prev.filter((m) => m.id !== tempUserMsg.id);
        return [...filtered, tempUserMsg, assistantResponse];
      });
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to get response from AI assistant.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleInspectChunk = async (chunkId: string) => {
    try {
      const chunk = await chatService.getSourceChunk(chunkId);
      setSelectedChunk(chunk);
    } catch (err) {
      console.error('Failed to fetch source chunk', err);
    }
  };

  const toggleCitations = (msgId: string) => {
    setExpandedCitations((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const getResponseTypeBadge = (type?: string | null) => {
    switch (type) {
      case 'GROUNDED_ANSWER':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            Verified Knowledge
          </span>
        );
      case 'INSUFFICIENT_EVIDENCE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <HelpCircle className="w-3.5 h-3.5 text-amber-600" />
            Insufficient Knowledge
          </span>
        );
      case 'SECURITY_REFUSAL':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
            <AlertCircle className="w-3.5 h-3.5 text-purple-600" />
            Security Refusal
          </span>
        );
      case 'SYSTEM_ERROR':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-50 text-red-700 border border-red-200">
            <AlertCircle className="w-3.5 h-3.5 text-red-600" />
            System Error
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 text-white rounded-2xl p-6 shadow-lg border border-indigo-800/40">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 text-xs font-bold tracking-wider uppercase bg-blue-500/30 text-blue-200 rounded-md border border-blue-400/30">
                Phase 9 • RAG Assistant
              </span>
              <span className="px-2.5 py-0.5 text-xs font-semibold bg-amber-500/20 text-amber-300 rounded-md border border-amber-400/30">
                PROTOTYPE / DEMO ONLY
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight">
              AI Admission & Onboarding Assistant
            </h1>
            <p className="text-sm text-slate-300 mt-1">
              XYZ Engineering College (Code: XYZ) • Academic Year 2026–27
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <div className="text-xs text-slate-300">Grounding Engine</div>
              <div className="text-sm font-semibold text-emerald-400 flex items-center justify-end gap-1">
                <Cpu className="w-4 h-4" /> MockLLMAdapter (Zero Hallucination)
              </div>
            </div>
          </div>
        </div>

        {/* Prototype Transparency Notice */}
        <div className="mt-4 pt-3 border-t border-indigo-800/50 flex items-center gap-2 text-xs text-indigo-200">
          <Sparkles className="w-4 h-4 text-amber-400 shrink-0" />
          <span>
            Answers are strictly synthesized from approved institutional guidelines and your authorized admission status. No real external LLM API billing keys required.
          </span>
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 min-h-[620px]">
        {/* Left Sidebar: Sessions */}
        <div className="lg:col-span-1 bg-white rounded-xl shadow-sm border border-slate-200 p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <MessageSquare className="w-4 h-4 text-blue-600" />
                Consultations
              </h2>
              <button
                onClick={() => createNewSession()}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-semibold rounded-lg transition"
                title="New Chat Session"
              >
                <Plus className="w-3.5 h-3.5" />
                New
              </button>
            </div>

            <div className="space-y-2 overflow-y-auto max-h-[460px] pr-1">
              {sessions.length === 0 ? (
                <div className="text-xs text-slate-400 text-center py-6">
                  No previous sessions.
                </div>
              ) : (
                sessions.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => selectSession(s.id)}
                    className={`w-full text-left p-3 rounded-lg text-xs transition border ${
                      activeSession?.id === s.id
                        ? 'bg-blue-50/80 border-blue-300 text-blue-900 font-semibold shadow-xs'
                        : 'bg-slate-50/50 hover:bg-slate-100/70 border-slate-200 text-slate-700'
                    }`}
                  >
                    <div className="truncate mb-1">{s.title || 'Admission Inquiry'}</div>
                    <div className="text-[10px] text-slate-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(s.created_at).toLocaleDateString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 text-[11px] text-slate-500 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Anti-IDOR protected: only you can view your inquiries.</span>
          </div>
        </div>

        {/* Right Area: Chat Messages & Input */}
        <div className="lg:col-span-3 bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col h-[650px]">
          {/* Active Chat Header */}
          <div className="px-6 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50 rounded-t-xl">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></div>
              <h3 className="font-semibold text-slate-800 text-sm">
                {activeSession?.title || 'Admission Support Session'}
              </h3>
            </div>
            <span className="text-xs text-slate-500 font-mono">
              Session ID: {activeSession?.id.slice(0, 8)}...
            </span>
          </div>

          {/* Messages Feed */}
          <div className="flex-1 overflow-y-auto p-6 space-y-5">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-100 to-indigo-100 text-blue-600 flex items-center justify-center shadow-inner">
                  <Sparkles className="w-7 h-7" />
                </div>
                <div>
                  <h4 className="text-base font-bold text-slate-800">
                    How can I assist your admission today?
                  </h4>
                  <p className="text-xs text-slate-500 max-w-md mt-1">
                    Ask any question about your application status, required documents, physical verification, DD payment, or college policies.
                  </p>
                </div>

                {/* Suggested Prompt Chips */}
                <div className="flex flex-wrap justify-center gap-2 max-w-xl mt-2">
                  {suggestedPrompts.map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(prompt)}
                      className="px-3 py-1.5 bg-slate-100 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 text-slate-700 text-xs rounded-full border border-slate-200 transition text-left"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg) => {
                const isUser = msg.sender_role === 'USER';
                const hasCitations = (msg.retrieved_sources_json || []).length > 0;
                const isExpanded = expandedCitations[msg.id] ?? true;

                return (
                  <div
                    key={msg.id}
                    className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-5 py-4 ${
                        isUser
                          ? 'bg-blue-600 text-white rounded-br-xs shadow-sm'
                          : 'bg-slate-50 border border-slate-200 text-slate-800 rounded-bl-xs shadow-xs'
                      }`}
                    >
                      {/* Assistant Header Badge */}
                      {!isUser && (
                        <div className="flex flex-wrap items-center justify-between gap-2 mb-2 pb-2 border-b border-slate-200/70">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-slate-700">
                              Admission AI
                            </span>
                            {getResponseTypeBadge(msg.response_type)}
                          </div>
                          {msg.latency_ms && (
                            <span className="text-[10px] text-slate-400 font-mono">
                              {msg.latency_ms} ms
                            </span>
                          )}
                        </div>
                      )}

                      {/* Personal Context Banner if consulted */}
                      {!isUser && msg.personal_context_used_json?.used && (
                        <div className="mb-3 px-3 py-1.5 bg-blue-100/60 border border-blue-200/80 rounded-lg text-xs text-blue-800 flex items-center gap-2">
                          <BookOpen className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                          <span>
                            Tailored to your current application status:{' '}
                            <strong className="font-semibold text-blue-900">
                              {msg.personal_context_used_json.app_status || 'Active'}
                            </strong>
                          </span>
                        </div>
                      )}

                      {/* Message Content */}
                      <div className="text-sm whitespace-pre-wrap leading-relaxed">
                        {msg.message}
                      </div>

                      {/* Grounded Citations Accordion */}
                      {!isUser && hasCitations && (
                        <div className="mt-4 pt-3 border-t border-slate-200/80 text-xs">
                          <button
                            onClick={() => toggleCitations(msg.id)}
                            className="flex items-center justify-between w-full text-slate-600 hover:text-slate-900 font-semibold mb-2"
                          >
                            <span className="flex items-center gap-1.5 text-xs text-slate-700">
                              <FileText className="w-3.5 h-3.5 text-blue-600" />
                              Grounded Citations ({msg.retrieved_sources_json?.length})
                            </span>
                            {isExpanded ? (
                              <ChevronUp className="w-3.5 h-3.5" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5" />
                            )}
                          </button>

                          {isExpanded && (
                            <div className="space-y-1.5">
                              {msg.retrieved_sources_json?.map((cite, cIdx) => (
                                <div
                                  key={cIdx}
                                  className="flex items-center justify-between bg-white px-3 py-2 rounded-lg border border-slate-200 hover:border-blue-300 transition text-xs"
                                >
                                  <div className="truncate pr-2">
                                    <span className="font-medium text-slate-800">
                                      {cite.document_title}
                                    </span>
                                    {cite.section_title && (
                                      <span className="text-slate-500 ml-1">
                                        • {cite.section_title}
                                      </span>
                                    )}
                                    <span className="text-[10px] text-slate-400 block">
                                      Version {cite.version_number} • Relevance:{' '}
                                      {(cite.score * 100).toFixed(0)}%
                                    </span>
                                  </div>
                                  <button
                                    onClick={() => handleInspectChunk(cite.chunk_id)}
                                    className="shrink-0 p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded"
                                    title="View Source Chunk Provenance"
                                  >
                                    <ExternalLink className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Timestamp */}
                      <div
                        className={`text-[10px] mt-2 text-right ${
                          isUser ? 'text-blue-200' : 'text-slate-400'
                        }`}
                      >
                        {new Date(msg.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </div>
                    </div>
                  </div>
                );
              })
            )}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-slate-50 border border-slate-200 rounded-2xl rounded-bl-xs px-5 py-4 flex items-center gap-3 text-sm text-slate-600">
                  <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                  <span>Synthesizing grounded answer from institutional knowledge base...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Error Message */}
          {error && (
            <div className="px-6 py-2 bg-red-50 border-t border-red-200 text-xs text-red-700 flex items-center justify-between">
              <span>{error}</span>
              <button onClick={() => setError(null)}>
                <X className="w-4 h-4 text-red-500" />
              </button>
            </div>
          )}

          {/* Quick Prompts Bar if messages exist */}
          {messages.length > 0 && (
            <div className="px-6 py-2 bg-slate-50 border-t border-slate-100 flex items-center gap-2 overflow-x-auto">
              <span className="text-[11px] font-semibold text-slate-500 shrink-0 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-amber-500" /> Suggested:
              </span>
              {suggestedPrompts.slice(0, 3).map((prompt, pIdx) => (
                <button
                  key={pIdx}
                  onClick={() => handleSendMessage(prompt)}
                  disabled={isLoading}
                  className="shrink-0 px-2.5 py-1 bg-white hover:bg-blue-50 text-[11px] text-slate-700 border border-slate-200 hover:border-blue-300 rounded-full transition truncate max-w-[220px]"
                >
                  {prompt}
                </button>
              ))}
            </div>
          )}

          {/* Input Area */}
          <div className="p-4 border-t border-slate-200 bg-white rounded-b-xl">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                placeholder="Ask about required documents, dates, physical verification, DD fees, ERP..."
                disabled={isLoading}
                className="flex-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-blue-500 focus:bg-white transition"
              />
              <button
                type="submit"
                disabled={isLoading || !inputQuery.trim()}
                className="px-5 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold rounded-xl flex items-center gap-1.5 text-sm transition shadow-sm"
              >
                <Send className="w-4 h-4" />
                <span className="hidden sm:inline">Send</span>
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Source Chunk Provenance Modal */}
      {selectedChunk && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-2xl w-full p-6 space-y-4 max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-slate-800 text-base">
                  Knowledge Provenance Inspector
                </h3>
              </div>
              <button
                onClick={() => setSelectedChunk(null)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div>
                <span className="text-slate-500">Chunk ID:</span>{' '}
                <span className="font-mono font-medium text-slate-800">
                  {selectedChunk.id}
                </span>
              </div>
              <div>
                <span className="text-slate-500">Section:</span>{' '}
                <span className="font-medium text-slate-800">
                  {selectedChunk.section_title || 'N/A'}
                </span>
              </div>
              <div>
                <span className="text-slate-500">Token Count:</span>{' '}
                <span className="font-medium text-slate-800">
                  {selectedChunk.token_count}
                </span>
              </div>
              <div>
                <span className="text-slate-500">Version ID:</span>{' '}
                <span className="font-mono font-medium text-slate-800 truncate block">
                  {selectedChunk.version_id}
                </span>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2">
              <div className="text-xs font-semibold text-slate-600">Exact Chunk Text:</div>
              <div className="p-4 bg-slate-900 text-slate-100 font-mono text-xs rounded-xl whitespace-pre-wrap leading-relaxed shadow-inner">
                {selectedChunk.content}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => setSelectedChunk(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-lg transition"
              >
                Close Provenance
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
