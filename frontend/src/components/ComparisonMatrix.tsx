import { useState } from 'react';
import { Table, Trophy, AlertTriangle, Sparkles, RefreshCw, Info, Check } from 'lucide-react';
import { Document } from '../types';
import { api } from '../services/api';

interface ComparisonMatrixProps {
  documents: Document[];
}

export default function ComparisonMatrix({ documents }: ComparisonMatrixProps) {
  const readyDocs = documents.filter(d => d.status === 'ready');
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [comparisonResult, setComparisonResult] = useState<any>(null);

  const toggleSelectDoc = (id: string) => {
    if (selectedDocIds.includes(id)) {
      setSelectedDocIds(prev => prev.filter(item => item !== id));
    } else {
      if (selectedDocIds.length >= 5) {
        alert('Chỉ hỗ trợ so sánh tối đa 5 tài liệu cùng lúc.');
        return;
      }
      setSelectedDocIds(prev => [...prev, id]);
    }
  };

  const handleStartComparison = async () => {
    if (selectedDocIds.length < 2) {
      alert('Vui lòng chọn tối thiểu 2 tài liệu để tiến hành so sánh đối chiếu.');
      return;
    }
    setLoading(true);
    setComparisonResult(null);

    try {
      const data = await api.compareDocuments(selectedDocIds);
      setComparisonResult(data);
    } catch (err: any) {
      alert(`Lỗi khi thực hiện so sánh chéo: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Helper to format metric keys to human-readable names
  const getMetricLabel = (key: string) => {
    const labels: Record<string, string> = {
      net_revenue: 'Doanh thu thuần',
      revenue: 'Doanh thu thuần',
      gross_margin: 'Biên lợi nhuận gộp (%)',
      net_margin: 'Biên lợi nhuận ròng (%)',
      operating_margin: 'Biên lợi nhuận HĐ (%)',
      roe: 'ROE (%)',
      roa: 'ROA (%)',
      debt_ratio: 'Tỷ lệ Nợ / Tổng tài sản (Debt Ratio)',
      debt_to_equity: 'Hệ số Nợ / VCSH (D/E)',
      current_ratio: 'Thanh toán hiện hành (Current Ratio)',
      quick_ratio: 'Thanh toán nhanh (Quick Ratio)',
      ebitda: 'Chỉ số EBITDA',
    };
    return labels[key] || key;
  };

  // Helper to display percentage or multiplier dynamically
  const formatMetricValue = (key: string, val: any) => {
    if (val === null || val === undefined) return '-';
    const num = parseFloat(val);
    if (isNaN(num)) return val;

    if (key.includes('margin') || key === 'roe' || key === 'roa' || key === 'debt_ratio') {
      // Check if it's already in percentage scale (e.g. 0.195 or 19.5)
      // Usually backend returns value as float (e.g. 0.195), so we multiply by 100
      if (Math.abs(num) < 1.0) {
        return `${(num * 100).toFixed(1)}%`;
      }
      return `${num.toFixed(1)}%`;
    }
    if (key.includes('ratio') || key === 'debt_to_equity') {
      return `${num.toFixed(2)}x`;
    }
    // Large numbers (e.g. revenue, EBITDA)
    if (num > 1000000) {
      return `${(num / 1000000000).toFixed(1)} tỷ VNĐ`;
    }
    return num.toString();
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div>
        <h1 className="text-xl md:text-2xl font-display font-extrabold text-on-surface mb-2">So sánh chéo doanh nghiệp</h1>
        <p className="text-xs md:text-sm text-on-surface-variant font-medium">Đối chiếu các trụ cột tài chính then chốt giữa các báo cáo tài chính đã chọn.</p>
      </div>

      {/* Document Selection Grid */}
      <div className="bg-surface-container-lowest border border-surface-border rounded-2xl p-5 shadow-sm space-y-4">
        <h2 className="text-xs font-display font-bold tracking-widest text-on-surface-variant uppercase">
          Chọn báo cáo để đối chiếu (Từ 2 đến 5 báo cáo)
        </h2>

        {readyDocs.length === 0 ? (
          <p className="text-xs font-semibold text-on-surface-variant py-3 text-center">
            Chưa có báo cáo tài chính nào sẵn sàng. Vui lòng upload tài liệu trước.
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {readyDocs.map(doc => {
              const isSelected = selectedDocIds.includes(doc.id);
              return (
                <button
                  key={doc.id}
                  onClick={() => toggleSelectDoc(doc.id)}
                  className={`flex items-center justify-between p-3 rounded-xl border text-left transition-all ${
                    isSelected
                      ? 'bg-primary-container/10 border-indigo-600/40 text-on-surface'
                      : 'bg-surface-bright border-surface-border text-on-surface-variant hover:bg-surface-container-low'
                  }`}
                >
                  <span className="text-xs font-bold truncate max-w-[200px]" title={doc.name}>
                    {doc.name}
                  </span>
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center border transition-all ${
                    isSelected ? 'bg-indigo-600 border-indigo-600 text-white' : 'border-surface-border bg-white'
                  }`}>
                    {isSelected && <Check className="w-3.5 h-3.5" />}
                  </div>
                </button>
              );
            })}
          </div>
        )}

        <div className="flex justify-end pt-2">
          <button
            onClick={handleStartComparison}
            disabled={selectedDocIds.length < 2 || loading}
            className="bg-on-surface hover:bg-on-surface-variant disabled:opacity-40 text-white font-semibold text-xs py-2.5 px-5 rounded-xl transition-all shadow-sm active:scale-95 flex items-center gap-2"
          >
            {loading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
            <span>Bắt đầu So sánh chéo</span>
          </button>
        </div>
      </div>

      {loading && (
        <div className="h-[300px] flex items-center justify-center bg-surface-container-lowest border border-surface-border rounded-2xl shadow-sm">
          <div className="flex flex-col items-center gap-3">
            <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin" />
            <span className="text-xs font-semibold text-on-surface-variant">AI đang tổng hợp và đánh giá ma trận đối chiếu...</span>
          </div>
        </div>
      )}

      {comparisonResult && (
        <>
          {/* Comparison Matrix Table */}
          <div className="bg-surface-container-lowest border border-surface-border rounded-2xl p-5 shadow-sm overflow-hidden flex flex-col">
            <div className="flex justify-between items-center mb-5 shrink-0">
              <h2 className="text-sm font-display font-extrabold text-on-surface flex items-center gap-2">
                <Table className="w-4 h-4 text-on-surface-variant" />
                Bảng chỉ số chéo (Indicator Matrix)
              </h2>
            </div>

            {/* Table representation */}
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[700px]">
                <thead className="bg-surface-bg/60 border-b border-surface-border">
                  <tr>
                    <th className="p-4 font-display text-xs tracking-wider font-bold text-on-surface-variant uppercase w-4/12">
                      Chỉ số tài chính
                    </th>
                    {comparisonResult.compared_entities.map((entity: any) => (
                      <th
                        key={entity.document_id}
                        className="p-4 font-display text-xs tracking-wider font-bold text-on-surface-variant uppercase"
                      >
                        {entity.company_name} ({entity.year || 'BCTC'})
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border font-medium text-xs">
                  {Object.keys(comparisonResult.comparison_matrix).map((metricKey) => {
                    const rowValues = comparisonResult.comparison_matrix[metricKey];
                    return (
                      <tr key={metricKey} className="hover:bg-surface-container-low/30 transition-all duration-150">
                        <td className="p-4 font-semibold text-on-surface flex items-center gap-2">
                          {getMetricLabel(metricKey)}
                          <Info className="w-3.5 h-3.5 text-outline-variant hover:text-on-surface cursor-help shrink-0" title={getMetricLabel(metricKey)} />
                        </td>
                        {comparisonResult.compared_entities.map((entity: any) => {
                          // Find key used in the matrix for this company
                          const colKey = `${entity.company_name} ${entity.year || ''}`.trim();
                          // Fallback to match if names differ slightly
                          const matchedKey = Object.keys(rowValues).find(k => k.includes(entity.company_name)) || colKey;
                          const rawVal = rowValues[matchedKey];

                          return (
                            <td key={entity.document_id} className="p-4 font-mono font-bold text-on-surface">
                              {formatMetricValue(metricKey, rawVal)}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* CFO AI Insights report */}
          <div className="bg-surface-container-lowest border border-surface-border rounded-2xl p-6 shadow-sm space-y-6">
            <div className="flex items-center gap-2 pb-4 border-b border-surface-border">
              <div className="bg-primary-container text-white p-2 rounded-xl">
                <Sparkles className="w-5 h-5 text-ai-accent" />
              </div>
              <div>
                <h2 className="text-sm font-display font-extrabold text-on-surface leading-tight">Nhận định của CFO AI</h2>
                <span className="text-[10px] text-on-surface-variant font-medium">Báo cáo so sánh chéo tổng hợp tự động</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
              <div className="bg-surface-bright/50 border border-surface-border rounded-xl p-5 space-y-2">
                <div className="flex items-center gap-2 text-xs font-extrabold text-on-surface mb-2">
                  <span className="w-2 h-2 rounded-full bg-indigo-600" />
                  <span>PHÂN TÍCH KHẢ NĂNG SINH LỜI</span>
                </div>
                <p className="text-xs text-on-surface-variant leading-relaxed">
                  {comparisonResult.ai_evaluation.profitability_comparison}
                </p>
              </div>

              <div className="bg-surface-bright/50 border border-surface-border rounded-xl p-5 space-y-2">
                <div className="flex items-center gap-2 text-xs font-extrabold text-on-surface mb-2">
                  <span className="w-2 h-2 rounded-full bg-violet-600" />
                  <span>ĐÒN BẨY & ĐỘC LẬP TÀI CHÍNH</span>
                </div>
                <p className="text-xs text-on-surface-variant leading-relaxed">
                  {comparisonResult.ai_evaluation.leverage_comparison}
                </p>
              </div>

              <div className="bg-surface-bright/50 border border-surface-border rounded-xl p-5 space-y-2">
                <div className="flex items-center gap-2 text-xs font-extrabold text-on-surface mb-2">
                  <span className="w-2 h-2 rounded-full bg-yellow-500" />
                  <span>NĂNG LỰC THANH KHOẢN NGẮN HẠN</span>
                </div>
                <p className="text-xs text-on-surface-variant leading-relaxed">
                  {comparisonResult.ai_evaluation.liquidity_comparison}
                </p>
              </div>

              <div className="bg-[#101223]/30 border border-indigo-500/10 rounded-xl p-5 space-y-2 col-span-1 md:col-span-2">
                <div className="flex items-center gap-2 text-xs font-extrabold text-indigo-400 mb-2">
                  <Trophy className="w-4 h-4 text-ai-accent" />
                  <span>KẾT LUẬN & KIẾN NGHỊ CUỐI CÙNG CỦA CFO</span>
                </div>
                <p className="text-xs text-on-surface-variant leading-relaxed font-semibold">
                  {comparisonResult.ai_evaluation.cfo_verdict}
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
