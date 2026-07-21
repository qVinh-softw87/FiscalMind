import { useState, useRef, useEffect } from 'react';
import { Bot, User, Send, PlusCircle, Trash2, Edit2, Sliders, ChevronDown, CheckCircle2, FileText, Sparkles, MessageSquare, Plus, History } from 'lucide-react';
import { Message, ChatHistoryItem, Document, Citation } from '../types';
import { api } from '../services/api';

interface ChatWindowProps {
  documents: Document[];
  selectedDocId?: string;
  setSelectedDocId?: (id: string) => void;
}

export default function ChatWindow({ documents, selectedDocId, setSelectedDocId }: ChatWindowProps) {
  // Chat History list (synced from API)
  const [chatList, setChatList] = useState<ChatHistoryItem[]>([]);
  const [activeChatId, setActiveChatId] = useState<string>('');
  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [editTitleVal, setEditTitleVal] = useState<string>('');

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMsg, setInputMsg] = useState<string>('');
  const [modelSettingsOpen, setModelSettingsOpen] = useState<boolean>(false);
  const [showScopeDropdown, setShowScopeDropdown] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  // Load message history when activeChatId changes
  useEffect(() => {
    if (activeChatId && !activeChatId.startsWith('temp-')) {
      loadHistory(activeChatId);
    } else {
      // Empty room or new chat session
      setMessages([
        {
          id: 'welcome',
          sender: 'ai',
          text: 'Xin chào. Tôi là Cố vấn CFO AI. Hãy chọn văn bản và gửi câu hỏi để tôi bắt đầu phân tích báo cáo tài chính cho bạn!',
          timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
        }
      ]);
    }
  }, [activeChatId]);

  const loadConversations = async (selectLatest = true) => {
    try {
      const data = await api.listConversations();
      if (data) {
        const mappedList: ChatHistoryItem[] = data.map((c: any) => ({
          id: c.id,
          title: c.title || 'Cuộc hội thoại mới',
          timestamp: new Date(c.updated_at).toLocaleDateString('vi-VN'),
        }));
        setChatList(mappedList);
        
        if (selectLatest && mappedList.length > 0 && !activeChatId) {
          setActiveChatId(mappedList[0].id);
        }
      }
    } catch (err) {
      console.error('Lỗi khi tải danh sách phòng chat:', err);
    }
  };

  const loadHistory = async (id: string) => {
    try {
      const data = await api.getConversationHistory(id);
      if (data && data.messages) {
        const mappedMsgs: Message[] = data.messages.map((m: any) => {
          const timestampStr = new Date(m.created_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
          const mappedCitations: Citation[] = m.citations ? m.citations.map((c: any, index: number) => ({
            id: index + 1,
            source: `BCTC - Trang ${c.chunk_index !== null ? c.chunk_index + 1 : '?'}`,
            text: `Tệp tin: ${c.filename}. Loại tài liệu: ${c.document_type || 'BCTC'}`
          })) : [];

          return {
            id: m.id,
            sender: m.role === 'user' ? 'user' : 'ai',
            text: m.content,
            timestamp: timestampStr,
            citations: mappedCitations.length > 0 ? mappedCitations : undefined,
            verified: m.role === 'assistant',
          };
        });
        setMessages(mappedMsgs);
      }
    } catch (err) {
      console.error('Lỗi khi tải lịch sử tin nhắn:', err);
    }
  };

  // Handle active document scope selection
  const activeDoc = documents.find((doc) => doc.id === selectedDocId);

  const handleSendMessage = async () => {
    if (!inputMsg.trim() || isGenerating) return;

    const currentQuery = inputMsg;
    setInputMsg('');
    setIsGenerating(true);

    // Create user message locally
    const userMsgId = `user-msg-${Date.now()}`;
    const userMsg: Message = {
      id: userMsgId,
      sender: 'user',
      text: currentQuery,
      timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);

    // Create placeholder for AI streaming response
    const aiMsgId = `ai-msg-stream-${Date.now()}`;
    const aiPlaceholder: Message = {
      id: aiMsgId,
      sender: 'ai',
      text: '',
      timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
      verified: false,
    };

    setMessages((prev) => [...prev, aiPlaceholder]);

    // Prepare active document scope array
    const docIds = selectedDocId ? [selectedDocId] : undefined;

    // Send SSE request
    let fullText = '';
    let resolvedConvId = activeChatId.startsWith('temp-') ? undefined : activeChatId;

    await api.chatStream(
      {
        message: currentQuery,
        conversation_id: resolvedConvId,
        document_ids: docIds,
      },
      (chunk) => {
        // SSE chunk received
        if (chunk.conversation_id) {
          resolvedConvId = chunk.conversation_id;
        }
        if (chunk.text) {
          fullText += chunk.text;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === aiMsgId ? { ...msg, text: fullText } : msg
            )
          );
        }
      },
      (doneData) => {
        // Stream done
        setIsGenerating(false);
        const finalCitations: Citation[] = doneData.citations
          ? doneData.citations.map((c: any, index: number) => ({
              id: index + 1,
              source: `BCTC - Trang ${c.chunk_index !== null ? c.chunk_index + 1 : '?'}`,
              text: `Tệp tin: ${c.filename}. Loại tài liệu: ${c.document_type || 'BCTC'}`
            }))
          : [];

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === aiMsgId
              ? {
                  ...msg,
                  citations: finalCitations.length > 0 ? finalCitations : undefined,
                  verified: true,
                }
              : msg
          )
        );

        if (resolvedConvId) {
          setActiveChatId(resolvedConvId);
          loadConversations(false);
        }
      },
      (err) => {
        // Stream failed
        console.error('SSE Chat stream failed:', err);
        setIsGenerating(false);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === aiMsgId
              ? {
                  ...msg,
                  text: 'Đã xảy ra lỗi khi tạo phản hồi từ AI. Vui lòng kiểm tra lại cấu hình hoặc kết nối mạng.',
                }
              : msg
          )
        );
      }
    );
  };

  // Chat History operations
  const handleEditChat = (id: string, title: string) => {
    setEditingChatId(id);
    setEditTitleVal(title);
  };

  const handleSaveEditChat = (id: string) => {
    setChatList((prev) =>
      prev.map((chat) => (chat.id === id ? { ...chat, title: editTitleVal } : chat))
    );
    setEditingChatId(null);
  };

  const handleDeleteChat = async (id: string) => {
    if (!confirm('Bạn có chắc chắn muốn xóa cuộc hội thoại này?')) return;
    try {
      await api.deleteConversation(id);
      setChatList((prev) => prev.filter((chat) => chat.id !== id));
      if (activeChatId === id) {
        setActiveChatId('');
        setMessages([
          {
            id: 'm-empty',
            sender: 'ai',
            text: 'Tôi là Cố vấn CFO AI. Hãy gửi câu hỏi để tôi bắt đầu phân tích báo cáo tài chính cho bạn!',
            timestamp: 'Vừa xong',
          }
        ]);
      }
    } catch (err: any) {
      alert(`Xóa cuộc hội thoại thất bại: ${err.message}`);
    }
  };

  const handleCreateNewChat = () => {
    const tempId = `temp-${Date.now()}`;
    const newChat: ChatHistoryItem = {
      id: tempId,
      title: 'Cuộc hội thoại mới',
      timestamp: 'Hôm nay',
    };
    setChatList([newChat, ...chatList]);
    setActiveChatId(tempId);
    setMessages([
      {
        id: `welcome-${tempId}`,
        sender: 'ai',
        text: 'Bạn đã bắt đầu phiên hội thoại mới. Vui lòng gửi câu hỏi để tôi phân tích báo cáo tài chính.',
        timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
      }
    ]);
  };

  return (
    <div className="flex-1 flex overflow-hidden h-full">
      {/* Mini Chat History Panel */}
      <div className="w-[280px] bg-surface-container-lowest border-r border-surface-border hidden lg:flex flex-col h-full shrink-0 z-10 animate-slide-right">
        {/* Header */}
        <div className="p-4 border-b border-surface-border flex justify-between items-center shrink-0">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-on-surface-variant animate-pulse" />
            <h2 className="text-xs font-display tracking-widest font-bold text-on-surface-variant uppercase">Lịch sử phân tích</h2>
          </div>
          <button
            onClick={handleCreateNewChat}
            className="p-1 rounded-lg hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface transition-colors"
            title="Tạo cuộc hội thoại mới"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        {/* History List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1.5 custom-scrollbar">
          {chatList.map((chat) => {
            const isActive = activeChatId === chat.id;
            const isEditing = editingChatId === chat.id;

            return (
              <div
                key={chat.id}
                onClick={() => !isEditing && setActiveChatId(chat.id)}
                className={`w-full group/chat flex items-center justify-between px-3 py-2.5 rounded-xl text-left cursor-pointer transition-all border ${
                  isActive
                    ? 'bg-surface-container-low border-surface-border text-on-surface font-semibold shadow-sm'
                    : 'bg-transparent border-transparent text-on-surface-variant hover:bg-surface-container-low/40 hover:text-on-surface'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0 flex-1">
                  <MessageSquare className="w-4 h-4 text-on-surface-variant shrink-0" />
                  {isEditing ? (
                    <input
                      type="text"
                      value={editTitleVal}
                      onChange={(e) => setEditTitleVal(e.target.value)}
                      onBlur={() => handleSaveEditChat(chat.id)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSaveEditChat(chat.id)}
                      autoFocus
                      className="bg-surface-bright border border-surface-border rounded px-1.5 py-0.5 text-xs text-on-surface outline-none w-full"
                    />
                  ) : (
                    <div className="flex flex-col min-w-0">
                      <span className="text-xs font-semibold truncate leading-tight">{chat.title}</span>
                      <span className="text-[10px] text-on-surface-variant/70 font-medium font-mono mt-0.5">{chat.timestamp}</span>
                    </div>
                  )}
                </div>

                {!isEditing && (
                  <div className="flex items-center gap-0.5 opacity-0 group-hover/chat:opacity-100 transition-opacity ml-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEditChat(chat.id, chat.title);
                      }}
                      className="p-1 rounded hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface"
                    >
                      <Edit2 className="w-3 h-3" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteChat(chat.id);
                      }}
                      className="p-1 rounded hover:bg-surface-container-high text-on-surface-variant hover:text-status-critical"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                )}
              </div>
            );
          })}

          {chatList.length === 0 && (
            <div className="p-8 text-center text-on-surface-variant text-[11px] font-medium leading-relaxed">
              Chưa có phiên chat nào. Hãy tạo phiên mới!
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Workspace */}
      <div className="flex-1 flex flex-col h-full bg-surface-bg relative overflow-hidden">
        {/* Chat Header */}
        <div className="h-16 border-b border-surface-border bg-surface-container-lowest px-6 flex justify-between items-center shrink-0 z-10">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center shadow-md shadow-indigo-600/10">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-sm font-display font-extrabold text-on-surface leading-tight">Cố vấn CFO AI</h2>
              <span className="text-[10px] text-on-surface-variant font-medium flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-status-healthy animate-pulse" />
                <span>Hoạt động (Llama 3.3 70B)</span>
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Context file scope selector */}
            <div className="relative">
              <button
                onClick={() => setShowScopeDropdown(!showScopeDropdown)}
                className="bg-surface-bright border border-surface-border text-on-surface px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-2 hover:bg-surface-container-low transition-colors"
              >
                <FileText className="w-3.5 h-3.5 text-on-surface-variant" />
                <span className="max-w-[120px] truncate">
                  {activeDoc ? activeDoc.name : 'Tất cả ngữ cảnh'}
                </span>
                <ChevronDown className="w-3 h-3 text-on-surface-variant" />
              </button>

              {showScopeDropdown && (
                <>
                  <div className="fixed inset-0 z-20" onClick={() => setShowScopeDropdown(false)} />
                  <div className="absolute right-0 top-full mt-2 w-64 bg-surface-container-lowest border border-surface-border rounded-2xl shadow-xl p-2 z-30 animate-fade-in flex flex-col gap-0.5">
                    <button
                      onClick={() => {
                        if (setSelectedDocId) setSelectedDocId('');
                        setShowScopeDropdown(false);
                      }}
                      className={`w-full text-left px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-colors ${
                        !selectedDocId
                          ? 'bg-surface-container-high text-on-surface'
                          : 'bg-transparent text-on-surface-variant hover:bg-surface-container-low'
                      }`}
                    >
                      <Sparkles className="w-3.5 h-3.5 text-ai-accent" />
                      <span>Tất cả ngữ cảnh tài liệu</span>
                    </button>
                    <div className="h-px bg-surface-border my-1" />
                    <div className="max-h-48 overflow-y-auto custom-scrollbar flex flex-col gap-0.5">
                      {documents.filter(d => d.status === 'ready').map((doc) => (
                        <button
                          key={doc.id}
                          onClick={() => {
                            if (setSelectedDocId) setSelectedDocId(doc.id);
                            setShowScopeDropdown(false);
                          }}
                          className={`w-full text-left px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-colors truncate ${
                            selectedDocId === doc.id
                              ? 'bg-surface-container-high text-on-surface'
                              : 'bg-transparent text-on-surface-variant hover:bg-surface-container-low'
                          }`}
                        >
                          <FileText className="w-3.5 h-3.5 text-on-surface-variant shrink-0" />
                          <span className="truncate">{doc.name}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Model Configuration override UI */}
            <div className="relative">
              <button
                onClick={() => setModelSettingsOpen(!modelSettingsOpen)}
                className="p-2 rounded-xl hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface transition-colors"
                title="Cấu hình Model AI"
              >
                <Sliders className="w-4 h-4" />
              </button>

              {modelSettingsOpen && (
                <>
                  <div className="fixed inset-0 z-20" onClick={() => setModelSettingsOpen(false)} />
                  <div className="absolute right-0 top-full mt-2 w-72 bg-surface-container-lowest border border-surface-border rounded-2xl shadow-xl p-5 z-30 animate-fade-in space-y-4">
                    <h4 className="text-xs font-display tracking-wider font-bold text-on-surface uppercase">Cấu hình mô hình</h4>
                    <div className="space-y-3">
                      <div>
                        <label className="text-[10px] font-bold text-on-surface-variant block mb-1">MÔ HÌNH SUY LUẬN</label>
                        <select className="w-full bg-surface-bright border border-surface-border rounded-xl px-2.5 py-1.5 text-xs font-semibold text-on-surface outline-none">
                          <option>Llama 3.3 70B (Groq)</option>
                          <option>Mixtral 8x7B (Groq)</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-on-surface-variant block mb-1">ĐỘ SÁNG TẠO (TEMPERATURE): 0.2</label>
                        <input type="range" min="0" max="1" step="0.1" defaultValue="0.2" className="w-full h-1 bg-surface-border rounded-lg appearance-none cursor-pointer accent-indigo-600" />
                        <span className="text-[9px] text-on-surface-variant font-medium mt-1 block">Giá trị thấp thích hợp cho phân tích số liệu tài chính cần độ chính xác cao.</span>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Message Log */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6 custom-scrollbar bg-[#0E101D]/20">
          {messages.map((msg) => {
            const isAI = msg.sender === 'ai';
            return (
              <div
                key={msg.id}
                className={`flex gap-4 max-w-[85%] animate-fade-in ${
                  isAI ? 'self-start' : 'self-end flex-row-reverse ml-auto'
                }`}
              >
                {/* Avatar */}
                <div
                  className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 shadow-sm border ${
                    isAI
                      ? 'bg-gradient-to-tr from-violet-600 to-indigo-600 text-white border-transparent'
                      : 'bg-surface-container-high text-on-surface-variant border-surface-border'
                  }`}
                >
                  {isAI ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                </div>

                {/* Text Bubble container */}
                <div className="space-y-1.5">
                  <div
                    className={`rounded-2xl p-4 shadow-sm border leading-relaxed text-sm ${
                      isAI
                        ? 'bg-surface-container-lowest border-surface-border text-on-surface font-medium'
                        : 'bg-indigo-600 text-white border-transparent font-semibold'
                    }`}
                  >
                    {/* Rich text line-by-line render for bold, bullet points, citations */}
                    <div className="space-y-2 whitespace-pre-wrap break-words">
                      {msg.text.split('\n').map((line, lIdx) => {
                        const isHeader = line.trim().startsWith('##');
                        if (isHeader) {
                          return (
                            <h3 key={lIdx} className="text-sm font-bold text-on-surface dark:text-white pt-2 pb-1 border-b border-surface-border/40">
                              {line.replace('##', '').trim()}
                            </h3>
                          );
                        }

                        let processedLine = line;
                        const isBullet = processedLine.trim().startsWith('*');
                        if (isBullet) {
                          processedLine = processedLine.trim().substring(1).trim();
                        }

                        // Replace bold markdown with JSX style
                        const parts = processedLine.split('**');
                        const parsedParts = parts.map((part, pIdx) => {
                          if (pIdx % 2 === 1) {
                            return <strong key={pIdx} className="font-extrabold text-on-surface dark:text-white">{part}</strong>;
                          }

                          // Re-process citations e.g. [1]
                          const citationRegex = /\[(\d+)\]/g;
                          const finalElements = [];
                          let lastIdx = 0;
                          let match;

                          while ((match = citationRegex.exec(part)) !== null) {
                            const citationNum = parseInt(match[1], 10);
                            const textBefore = part.substring(lastIdx, match.index);
                            finalElements.push(textBefore);

                            // Find corresponding citation
                            const citationObj = msg.citations?.find((c) => c.id === citationNum);

                            finalElements.push(
                              <span key={match.index} className="inline-block relative group/cit mx-0.5">
                                <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-surface-container-high dark:bg-slate-800 hover:bg-on-surface hover:text-white text-[9px] font-mono font-bold text-primary ring-1 ring-surface-border cursor-pointer transition-all">
                                  {citationNum}
                                </span>
                                {citationObj && (
                                  <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 w-64 p-3 bg-inverse-surface text-white border border-surface-border rounded-xl shadow-xl opacity-0 pointer-events-none group-hover/cit:opacity-100 transition-all duration-200 z-50 text-left leading-normal">
                                    <span className="text-[9px] font-mono font-bold text-inverse-primary uppercase block mb-1">
                                      {citationObj.source}
                                    </span>
                                    <p className="text-[10px] text-white/90">
                                      "{citationObj.text}"
                                    </p>
                                    <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-inverse-surface" />
                                  </div>
                                )}
                              </span>
                            );
                            lastIdx = citationRegex.lastIndex;
                          }
                          finalElements.push(part.substring(lastIdx));
                          return <span key={pIdx}>{finalElements}</span>;
                        });

                        return (
                          <div key={lIdx} className={isBullet ? "flex items-start gap-1.5 pl-2" : ""}>
                            {isBullet && <span className="text-ai-accent shrink-0 mt-1.5 font-bold">•</span>}
                            <span>{parsedParts}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Verification Status Flag / Citation list summary */}
                  <div className={`flex items-center gap-2 px-1 text-[10px] font-medium ${
                    isAI ? 'text-on-surface-variant' : 'text-on-surface-variant ml-auto text-right'
                  }`}>
                    <span>{msg.timestamp}</span>
                    {isAI && msg.verified && (
                      <span className="flex items-center gap-1 text-status-healthy">
                        <CheckCircle2 className="w-3.5 h-3.5 text-status-healthy" />
                        <span>Đối chiếu đối tượng hoàn tất</span>
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Pane */}
        <div className="p-4 border-t border-surface-border bg-surface-container-lowest shrink-0 z-10">
          <div className="max-w-4xl mx-auto flex gap-3 relative items-end">
            <div className="flex-1 bg-surface-bright border border-surface-border rounded-2xl p-2.5 flex items-end gap-2 focus-within:ring-1 focus-within:ring-ai-accent focus-within:border-ai-accent transition-all">
              <button
                className="p-2 rounded-xl hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface shrink-0"
                title="Tải tệp bổ sung (Chưa hỗ trợ)"
              >
                <PlusCircle className="w-5 h-5" />
              </button>
              
              <textarea
                rows={1}
                value={inputMsg}
                onChange={(e) => setInputMsg(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder={`Hỏi CFO AI về ${activeDoc ? activeDoc.name : 'báo cáo tài chính'}...`}
                className="flex-1 bg-transparent border-0 outline-none text-sm text-on-surface py-2 resize-none max-h-32 custom-scrollbar placeholder-on-surface-variant/60"
              />
            </div>

            <button
              onClick={handleSendMessage}
              disabled={!inputMsg.trim() || isGenerating}
              className="bg-on-surface hover:bg-on-surface-variant disabled:opacity-40 text-white p-3.5 rounded-2xl shrink-0 transition-colors shadow-md shadow-on-surface/5 active:scale-95 duration-150 flex items-center justify-center"
            >
              {isGenerating ? (
                <span className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
          <p className="text-[10px] text-on-surface-variant/60 text-center mt-2.5 font-medium leading-normal">
            AI có thể mắc lỗi. Vui lòng đối chiếu các trích dẫn nguồn số liệu trước khi ra quyết định đầu tư.
          </p>
        </div>
      </div>
    </div>
  );
}
