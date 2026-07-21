import { FileText, Database, Eye, Trash2, RefreshCw, MessageSquare, AlertCircle, FileSpreadsheet } from 'lucide-react';
import { Document, DocStatus } from '../types';

interface FileTableProps {
  documents: Document[];
  onDelete?: (id: string) => void;
  onRetry?: (id: string) => void;
  onAnalyzeChat?: (id: string) => void;
}

export default function FileTable({ documents, onDelete, onRetry, onAnalyzeChat }: FileTableProps) {
  const getStatusBadge = (status: DocStatus, reason?: string) => {
    switch (status) {
      case 'ready':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-status-healthy/10 text-status-healthy border border-status-healthy/20">
            <span className="w-1.5 h-1.5 rounded-full bg-status-healthy" />
            Sẵn Sàng
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-status-warning/10 text-status-warning border border-status-warning/20">
            <RefreshCw className="w-3 h-3 animate-spin" />
            Đang Xử Lý
          </span>
        );
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-outline-variant/30 text-on-surface-variant border border-outline-variant/20">
            <span className="w-1.5 h-1.5 rounded-full bg-outline" />
            Chờ xử lý
          </span>
        );
      case 'failed':
        return (
          <div className="relative inline-block group cursor-help">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-status-critical/10 text-status-critical font-semibold text-xs border border-status-critical/20">
              <AlertCircle className="w-3 h-3" />
              Lỗi
            </span>
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-52 p-2 bg-inverse-surface text-white text-[11px] font-medium rounded-lg shadow-lg opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-20 text-center leading-relaxed">
              {reason || 'Không thể trích xuất văn bản. File bị hỏng hoặc mã hóa.'}
              <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-inverse-surface" />
            </div>
          </div>
        );
    }
  };

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'pdf':
        return <FileText className="w-4 h-4 text-status-critical" />;
      case 'excel':
      case 'csv':
        return <FileSpreadsheet className="w-4 h-4 text-status-healthy" />;
      default:
        return <Database className="w-4 h-4 text-on-surface-variant" />;
    }
  };

  return (
    <div className="overflow-x-auto flex-1">
      <table className="w-full text-left border-collapse min-w-[700px]" id="table-document-hub">
        <thead className="bg-surface-bg/60 border-b border-surface-border">
          <tr>
            <th className="p-4 font-display text-xs tracking-wider font-bold text-on-surface-variant uppercase w-5/12">
              Tên file
            </th>
            <th className="p-4 font-display text-xs tracking-wider font-bold text-on-surface-variant uppercase w-2/12">
              Ngày tải
            </th>
            <th className="p-4 font-display text-xs tracking-wider font-bold text-on-surface-variant uppercase w-1/12">
              Kích thước
            </th>
            <th className="p-4 font-display text-xs tracking-wider font-bold text-on-surface-variant uppercase w-2/12">
              Trạng thái
            </th>
            <th className="p-4 font-display text-xs tracking-wider font-bold text-on-surface-variant uppercase w-2/12 text-right">
              Thao tác
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-border">
          {documents.map((doc) => (
            <tr key={doc.id} className="hover:bg-surface-container-low/40 transition-all duration-150 group">
              <td className="p-4 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-surface-container-low flex items-center justify-center shrink-0 border border-surface-border">
                  {getFileIcon(doc.type)}
                </div>
                <span className="font-semibold text-sm text-on-surface truncate max-w-[280px]" title={doc.name}>
                  {doc.name}
                </span>
              </td>
              <td className="p-4 text-xs text-on-surface-variant font-medium">
                {doc.uploadDate}
              </td>
              <td className="p-4 text-xs text-on-surface-variant font-mono font-medium">
                {doc.size}
              </td>
              <td className="p-4">
                {getStatusBadge(doc.status)}
              </td>
              <td className="p-4 text-right">
                <div className="flex items-center justify-end gap-1 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity duration-200">
                  {doc.status === 'ready' && (
                    <>
                      <button
                        onClick={() => onAnalyzeChat?.(doc.id)}
                        className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant hover:text-ai-accent transition-colors"
                        title="Chat với CFO AI"
                      >
                        <MessageSquare className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => alert(`Reviewing details for ${doc.name}`)}
                        className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface transition-colors"
                        title="Xem tài liệu"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </>
                  )}
                  {doc.status === 'failed' && (
                    <button
                      onClick={() => onRetry?.(doc.id)}
                      className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant hover:text-status-healthy transition-colors flex items-center gap-1 text-[11px] font-bold"
                      title="Thử lại"
                    >
                      <RefreshCw className="w-4 h-4" />
                      <span>Thử lại</span>
                    </button>
                  )}
                  <button
                    onClick={() => onDelete?.(doc.id)}
                    className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant hover:text-status-critical transition-colors"
                    title="Xóa tài liệu"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
          {documents.length === 0 && (
            <tr>
              <td colSpan={5} className="p-8 text-center text-on-surface-variant text-sm font-medium">
                Không tìm thấy tài liệu nào. Hãy kéo thả để tải thêm!
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
