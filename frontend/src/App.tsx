import React, { useState, useRef, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import DashboardStats from './components/DashboardStats';
import FileTable from './components/FileTable';
import ChatWindow from './components/ChatWindow';
import RadarChart from './components/RadarChart';
import ComparisonMatrix from './components/ComparisonMatrix';
import AuthScreen from './components/AuthScreen';
import { Tab, Document, BenchmarkSettings } from './types';
import { api, getAccessToken } from './services/api';
import { UploadCloud, Sparkles, ArrowRight } from 'lucide-react';

export default function App() {
  const [hasToken, setHasToken] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);
  const [searchVal, setSearchVal] = useState<string>('');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loadingDocs, setLoadingDocs] = useState<boolean>(false);

  // Selected document context for AI Chat
  const [selectedDocId, setSelectedDocId] = useState<string>('');

  // Benchmark thresholds for Radar analysis
  const [benchmarkSettings, setBenchmarkSettings] = useState<BenchmarkSettings>({
    roeTarget: 15.0,
    deLimit: 2.0,
    currentRatioMin: 1.5,
  });

  // Drag-and-drop state
  const [isDragActive, setIsDragActive] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Check auth token on mount
  useEffect(() => {
    const token = getAccessToken();
    if (token) {
      setHasToken(true);
    }
  }, []);

  // Fetch documents when authenticated or when activeTab changes
  useEffect(() => {
    if (hasToken) {
      fetchDocuments();
    }
  }, [hasToken, activeTab]);

  const fetchDocuments = async () => {
    setLoadingDocs(true);
    try {
      const data = await api.listDocuments();
      if (data && data.items) {
        const mappedDocs: Document[] = data.items.map((doc: any) => {
          const ext = doc.original_filename.split('.').pop()?.toLowerCase();
          const docType = ext === 'xlsx' || ext === 'xls' || ext === 'csv' ? 'excel' : 'pdf';
          const sizeMB = (doc.file_size / (1024 * 1024)).toFixed(1);

          return {
            id: doc.id,
            name: doc.original_filename,
            uploadDate: new Date(doc.created_at).toLocaleDateString('vi-VN'),
            size: `${sizeMB} MB`,
            status: doc.status,
            type: docType,
          };
        });
        setDocuments(mappedDocs);

        // Auto-select first ready document if none selected
        if (!selectedDocId || !mappedDocs.find(d => d.id === selectedDocId)) {
          const firstReady = mappedDocs.find(d => d.status === 'ready');
          if (firstReady) {
            setSelectedDocId(firstReady.id);
          } else if (mappedDocs.length > 0) {
            setSelectedDocId(mappedDocs[0].id);
          }
        }
      }
    } catch (err) {
      console.error('Không thể lấy danh sách tài liệu:', err);
    } finally {
      setLoadingDocs(false);
    }
  };

  // Filter documents by search value
  const filteredDocs = documents.filter((doc) =>
    doc.name.toLowerCase().includes(searchVal.toLowerCase())
  );

  // File handlers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true);
    } else if (e.type === "dragleave") {
      setIsDragActive(false);
    }
  };

  const processUploadedFiles = async (files: FileList) => {
    setIsDragActive(false);
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const ext = file.name.split('.').pop()?.toLowerCase();
      const docType = ext === 'xlsx' || ext === 'xls' || ext === 'csv' ? 'excel' : 'pdf';

      // Insert placeholder doc in state as processing
      const placeholderId = `uploading-${Date.now()}-${i}`;
      const placeholderDoc: Document = {
        id: placeholderId,
        name: file.name,
        uploadDate: new Date().toLocaleDateString('vi-VN'),
        size: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
        status: 'processing',
        type: docType,
      };

      setDocuments((prev) => [placeholderDoc, ...prev]);

      try {
        const uploaded = await api.uploadDocument(file);
        
        // Update placeholder with actual uploaded document info
        setDocuments((prev) =>
          prev.map((d) => (d.id === placeholderId ? {
            ...d,
            id: uploaded.id,
            status: uploaded.status,
            uploadDate: new Date(uploaded.created_at).toLocaleDateString('vi-VN'),
          } : d))
        );

        // Start polling if still processing
        if (uploaded.status === 'pending' || uploaded.status === 'processing') {
          pollDocumentStatus(uploaded.id);
        }
      } catch (err: any) {
        console.error('Lỗi khi tải file lên:', err);
        setDocuments((prev) =>
          prev.map((d) => (d.id === placeholderId ? { ...d, status: 'failed' } : d))
        );
        alert(`Tải file "${file.name}" thất bại: ${err.message}`);
      }
    }
  };

  // Poll status of document from backend
  const pollDocumentStatus = (docId: string) => {
    const interval = setInterval(async () => {
      try {
        const data = await api.getDocumentStatus(docId);
        if (data.status === 'ready' || data.status === 'failed') {
          clearInterval(interval);
          setDocuments((prev) =>
            prev.map((d) => (d.id === docId ? { ...d, status: data.status } : d))
          );
          if (data.status === 'ready') {
            setSelectedDocId(docId);
          }
        }
      } catch (err) {
        clearInterval(interval);
        console.error(`Lỗi polling status tài liệu ${docId}:`, err);
      }
    }, 3000);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processUploadedFiles(e.dataTransfer.files);
    }
  };

  const handleManualUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processUploadedFiles(e.target.files);
    }
  };

  const handleTriggerFileInput = () => {
    fileInputRef.current?.click();
  };

  const handleDeleteDoc = async (id: string) => {
    if (!confirm('Bạn có chắc chắn muốn xóa tài liệu này?')) return;
    try {
      await api.deleteDocument(id);
      setDocuments((prev) => prev.filter((doc) => doc.id !== id));
      if (selectedDocId === id) {
        setSelectedDocId('');
      }
    } catch (err: any) {
      alert(`Xóa tài liệu thất bại: ${err.message}`);
    }
  };

  const handleRetryDoc = (id: string) => {
    // For failed placeholders, we ask user to upload again
    alert('Vui lòng kéo thả hoặc chọn file để tải lại tài liệu này.');
  };

  const handleAnalyzeChat = (id: string) => {
    setSelectedDocId(id);
    setActiveTab('ai-chat');
  };

  const handleNewAnalysis = () => {
    setActiveTab('document-hub');
    setTimeout(() => {
      handleTriggerFileInput();
    }, 100);
  };

  const handleLogout = async () => {
    await api.logout();
    setHasToken(false);
    setDocuments([]);
  };

  // If not authenticated, render AuthScreen
  if (!hasToken) {
    return <AuthScreen onAuthSuccess={() => setHasToken(true)} />;
  }

  return (
    <div className="min-h-screen bg-surface-bg flex">
      {/* Persistent Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onNewAnalysis={handleNewAnalysis}
        onLogout={handleLogout}
        isOpen={sidebarOpen}
        setIsOpen={setSidebarOpen}
      />

      {/* Main Content Pane */}
      <div className="flex-1 md:pl-[260px] flex flex-col h-screen overflow-hidden">
        <Navbar
          searchVal={searchVal}
          onSearchChange={setSearchVal}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          setSidebarOpen={setSidebarOpen}
        />

        {/* Workspace body */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 md:p-8 space-y-8 pb-16">
          {activeTab === 'dashboard' && (
            <div className="space-y-8 animate-fade-in">
              {/* Header Title */}
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shrink-0">
                <div>
                  <h1 className="text-xl md:text-2xl font-display font-extrabold text-on-surface mb-2">Tổng quan Phân tích</h1>
                  <p className="text-xs md:text-sm text-on-surface-variant font-medium">Bảng điều khiển thông minh phân tích chỉ số tài chính.</p>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => setActiveTab('ai-chat')}
                    className="bg-primary-container text-white px-4 py-2 rounded-xl text-xs font-semibold hover:bg-opacity-90 transition-all flex items-center gap-1.5"
                  >
                    <Sparkles className="w-4 h-4 text-ai-accent" />
                    <span>Chat với CFO AI</span>
                  </button>
                </div>
              </div>

              {/* Statistical Bento Cards */}
              <DashboardStats documents={documents} />

              {/* Recent Files + Dropzone Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* File list section (Spans 8 cols) */}
                <div className="lg:col-span-8 bg-surface-container-lowest border border-surface-border rounded-2xl p-5 shadow-sm flex flex-col min-h-[350px]">
                  <div className="flex justify-between items-center mb-5 shrink-0">
                    <h2 className="text-sm font-display font-extrabold text-on-surface">Tài liệu phân tích gần đây</h2>
                    <button
                      onClick={() => setActiveTab('document-hub')}
                      className="text-xs font-bold text-ai-accent hover:underline flex items-center gap-1 shrink-0"
                    >
                      <span>Tất cả tài liệu</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                  {loadingDocs ? (
                    <div className="flex-1 flex items-center justify-center">
                      <span className="w-8 h-8 border-4 border-indigo-600/20 border-t-indigo-600 rounded-full animate-spin" />
                    </div>
                  ) : (
                    <FileTable
                      documents={filteredDocs.slice(0, 4)}
                      onDelete={handleDeleteDoc}
                      onRetry={handleRetryDoc}
                      onAnalyzeChat={handleAnalyzeChat}
                    />
                  )}
                </div>

                {/* Dropzone (Spans 4 cols) */}
                <div className="lg:col-span-4 flex flex-col gap-6">
                  <div
                    onDragEnter={handleDrag}
                    onDragOver={handleDrag}
                    onDragLeave={handleDrag}
                    onDrop={handleDrop}
                    onClick={handleTriggerFileInput}
                    className={`border-2 border-dashed border-surface-border rounded-2xl p-6 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-surface-container-low/30 hover:border-ai-accent transition-all duration-300 min-h-[220px] ${
                      isDragActive ? 'drag-active' : ''
                    }`}
                    id="dropzone-dashboard"
                  >
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleManualUpload}
                      className="hidden"
                      multiple
                      accept=".pdf,.xlsx,.xls,.csv"
                    />
                    <div className="bg-surface-container p-3 rounded-full mb-4">
                      <UploadCloud className="w-6 h-6 text-on-surface-variant" />
                    </div>
                    <span className="text-xs font-bold text-on-surface mb-1">
                      Kéo thả Báo cáo tài chính
                    </span>
                    <span className="text-[10px] text-on-surface-variant font-medium max-w-[200px] leading-relaxed">
                      Hỗ trợ định dạng PDF, Excel hoặc CSV (Tối đa 15MB)
                    </span>
                  </div>

                  {/* Benchmark targets highlight widget */}
                  <div className="bg-surface-container-lowest border border-surface-border rounded-2xl p-5 shadow-sm flex flex-col justify-between">
                    <div>
                      <h3 className="text-xs font-display tracking-widest text-on-surface-variant font-bold uppercase mb-3">
                        Mục tiêu hiện hành
                      </h3>
                      <div className="space-y-2.5">
                        <div className="flex justify-between items-center text-xs font-medium">
                          <span className="text-on-surface-variant">Target ROE:</span>
                          <span className="font-mono font-bold text-on-surface bg-surface-bright px-2 py-0.5 rounded border border-surface-border">{benchmarkSettings.roeTarget}%</span>
                        </div>
                        <div className="flex justify-between items-center text-xs font-medium">
                          <span className="text-on-surface-variant">Giới hạn D/E:</span>
                          <span className="font-mono font-bold text-on-surface bg-surface-bright px-2 py-0.5 rounded border border-surface-border">{benchmarkSettings.deLimit}x</span>
                        </div>
                        <div className="flex justify-between items-center text-xs font-medium">
                          <span className="text-on-surface-variant">Current Ratio:</span>
                          <span className="font-mono font-bold text-on-surface bg-surface-bright px-2 py-0.5 rounded border border-surface-border">&ge; {benchmarkSettings.currentRatioMin}</span>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => setActiveTab('radar')}
                      className="w-full bg-surface-bright hover:bg-surface-container-low border border-surface-border text-on-surface font-semibold text-xs py-2 mt-4 rounded-xl transition-all"
                    >
                      Thay đổi cài đặt
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'document-hub' && (
            <div className="space-y-8 animate-fade-in">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 shrink-0">
                <div>
                  <h1 className="text-xl md:text-2xl font-display font-extrabold text-on-surface mb-2">Kho Tài liệu Phân tích</h1>
                  <p className="text-xs md:text-sm text-on-surface-variant font-medium">Tải lên, tổ chức và quản lý các báo cáo tài chính của doanh nghiệp.</p>
                </div>
                <button
                  onClick={handleTriggerFileInput}
                  className="bg-on-surface hover:bg-on-surface-variant text-white px-4 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-sm active:scale-95 transition-all"
                  id="btn-upload-hub"
                >
                  <UploadCloud className="w-4 h-4" />
                  <span>Tải tài liệu mới</span>
                </button>
              </div>

              {/* Bulk upload target box */}
              <div
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={handleTriggerFileInput}
                className={`border-2 border-dashed border-surface-border bg-surface-container-lowest rounded-2xl p-8 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-surface-container-low/30 hover:border-ai-accent transition-all duration-300 ${
                  isDragActive ? 'drag-active' : ''
                }`}
              >
                <div className="bg-surface-container p-3.5 rounded-full mb-3.5">
                  <UploadCloud className="w-8 h-8 text-on-surface-variant" />
                </div>
                <h3 className="text-xs font-bold text-on-surface mb-1">
                  Kéo thả file vào đây hoặc click để duyệt từ máy tính
                </h3>
                <p className="text-[10px] text-on-surface-variant font-medium leading-relaxed">
                  Chấp nhận PDF, XLSX, XLS hoặc CSV. Giới hạn tối đa 15MB mỗi file.
                </p>
              </div>

              {/* Comprehensive Document Table */}
              <div className="bg-surface-container-lowest border border-surface-border rounded-2xl p-5 shadow-sm flex flex-col">
                <div className="flex justify-between items-center mb-5 shrink-0">
                  <h2 className="text-sm font-display font-extrabold text-on-surface">Tất cả tài liệu ({filteredDocs.length})</h2>
                  <div className="flex items-center gap-3">
                    <input
                      type="text"
                      placeholder="Tìm kiếm file..."
                      value={searchVal}
                      onChange={(e) => setSearchVal(e.target.value)}
                      className="bg-surface-bright border border-surface-border rounded-xl px-3 py-1.5 text-xs outline-none focus:ring-1 focus:ring-ai-accent w-48"
                    />
                  </div>
                </div>
                {loadingDocs ? (
                  <div className="py-12 flex items-center justify-center">
                    <span className="w-8 h-8 border-4 border-indigo-600/20 border-t-indigo-600 rounded-full animate-spin" />
                  </div>
                ) : (
                  <FileTable
                    documents={filteredDocs}
                    onDelete={handleDeleteDoc}
                    onRetry={handleRetryDoc}
                    onAnalyzeChat={handleAnalyzeChat}
                  />
                )}
              </div>
            </div>
          )}

          {activeTab === 'ai-chat' && (
            <div className="h-[calc(100vh-100px)] -m-6 md:-m-8 flex overflow-hidden animate-fade-in">
              <ChatWindow
                documents={documents}
                selectedDocId={selectedDocId}
                setSelectedDocId={setSelectedDocId}
              />
            </div>
          )}

          {activeTab === 'radar' && (
            <div className="animate-fade-in">
              <RadarChart
                settings={benchmarkSettings}
                onSettingsChange={setBenchmarkSettings}
                documents={documents}
              />
            </div>
          )}

          {activeTab === 'comparison' && (
            <div className="animate-fade-in">
              <ComparisonMatrix documents={documents} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
