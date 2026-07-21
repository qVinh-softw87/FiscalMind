import { useState, useEffect } from 'react';
import { Radar, RadarChart as RechartsRadar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import { Sliders, Activity, AlertTriangle, CheckCircle, Sparkles, RefreshCw, FileText } from 'lucide-react';
import { BenchmarkSettings, Document } from '../types';
import { api } from '../services/api';

interface RadarChartProps {
  settings: BenchmarkSettings;
  onSettingsChange: (newSettings: BenchmarkSettings) => void;
  documents: Document[];
}

export default function RadarChart({ settings, onSettingsChange, documents }: RadarChartProps) {
  const readyDocs = documents.filter(d => d.status === 'ready');
  const [selectedDocId, setSelectedDocId] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [ratioReport, setRatioReport] = useState<any>(null);

  // Local inputs to track custom thresholds
  const [localRoe, setLocalRoe] = useState<number>(settings.roeTarget);
  const [localDe, setLocalDe] = useState<number>(settings.deLimit);
  const [localCr, setLocalCr] = useState<number>(settings.currentRatioMin);
  const [updatingThresholds, setUpdatingThresholds] = useState<boolean>(false);

  // Set default selected document on mount/doc load
  useEffect(() => {
    if (readyDocs.length > 0 && !selectedDocId) {
      setSelectedDocId(readyDocs[0].id);
    }
  }, [readyDocs, selectedDocId]);

  // Load report when selectedDocId changes
  useEffect(() => {
    if (selectedDocId) {
      loadBenchmarkReport(selectedDocId);
    }
  }, [selectedDocId]);

  const loadBenchmarkReport = async (id: string) => {
    setLoading(true);
    try {
      const data = await api.getDocumentBenchmark(id);
      if (data) {
        setRatioReport(data);
        
        // Sync local settings with boundaries if returned
        const roeTh = data.ratios?.profitability?.roe?.thresholds;
        const deTh = data.ratios?.solvency?.debt_to_equity?.thresholds;
        const crTh = data.ratios?.liquidity?.current_ratio?.thresholds;

        if (roeTh) setLocalRoe(roeTh.healthy);
        if (deTh) setLocalDe(deTh.warning);
        if (crTh) setLocalCr(crTh.healthy);
      }
    } catch (err) {
      console.error('Không thể lấy báo cáo so sánh benchmark:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle benchmark update
  const handleUpdateBenchmarks = async () => {
    if (!selectedDocId || !ratioReport) return;
    setUpdatingThresholds(true);

    try {
      const sector = ratioReport.sector || 'general';

      // Save custom ROE
      await api.saveCustomBenchmark({
        sector,
        metric: 'roe',
        healthy_boundary: localRoe,
        warning_boundary: localRoe * 0.7, // Set warning slightly lower
      });

      // Save custom Debt-to-Equity
      await api.saveCustomBenchmark({
        sector,
        metric: 'debt_to_equity',
        healthy_boundary: localDe * 0.7,
        warning_boundary: localDe,
      });

      // Save custom Current Ratio
      await api.saveCustomBenchmark({
        sector,
        metric: 'current_ratio',
        healthy_boundary: localCr,
        warning_boundary: localCr * 0.7,
      });

      // Update parent config settings
      onSettingsChange({
        roeTarget: localRoe,
        deLimit: localDe,
        currentRatioMin: localCr,
      });

      alert('Đã cập nhật các ngưỡng tham chiếu tùy chỉnh lên hệ thống thành công! Chỉ số đang được tính toán lại.');
      // Refresh report data
      await loadBenchmarkReport(selectedDocId);
    } catch (err: any) {
      alert(`Cập nhật ngưỡng thất bại: ${err.message}`);
    } finally {
      setUpdatingThresholds(false);
    }
  };

  // Helper values for display (default fallback if no data loaded)
  const roeVal = ratioReport?.ratios?.profitability?.roe?.value ? (ratioReport.ratios.profitability.roe.value * 100).toFixed(1) : '0';
  const roaVal = ratioReport?.ratios?.profitability?.roa?.value ? (ratioReport.ratios.profitability.roa.value * 100).toFixed(1) : '0';
  const gmVal = ratioReport?.ratios?.profitability?.gross_margin?.value ? (ratioReport.ratios.profitability.gross_margin.value * 100).toFixed(1) : '0';
  const nmVal = ratioReport?.ratios?.profitability?.net_margin?.value ? (ratioReport.ratios.profitability.net_margin.value * 100).toFixed(1) : '0';

  const deVal = ratioReport?.ratios?.solvency?.debt_to_equity?.value ? ratioReport.ratios.solvency.debt_to_equity.value.toFixed(2) : '0';
  const drVal = ratioReport?.ratios?.solvency?.debt_ratio?.value ? (ratioReport.ratios.solvency.debt_ratio.value * 100).toFixed(1) : '0';

  const crVal = ratioReport?.ratios?.liquidity?.current_ratio?.value ? ratioReport.ratios.liquidity.current_ratio.value.toFixed(2) : '0';
  const qrVal = ratioReport?.ratios?.liquidity?.quick_ratio?.value ? ratioReport.ratios.liquidity.quick_ratio.value.toFixed(2) : '0';

  const opmVal = ratioReport?.ratios?.operations?.operating_margin?.value ? (ratioReport.ratios.operations.operating_margin.value * 100).toFixed(1) : '0';

  // Construct chartData dynamically from actual API values
  const companyMetrics = {
    roe: ratioReport?.ratios?.profitability?.roe?.value ? ratioReport.ratios.profitability.roe.value * 100 : 0,
    de: ratioReport?.ratios?.solvency?.debt_to_equity?.value ? ratioReport.ratios.solvency.debt_to_equity.value : 0,
    cr: ratioReport?.ratios?.liquidity?.current_ratio?.value ? ratioReport.ratios.liquidity.current_ratio.value : 0,
    grossMargin: ratioReport?.ratios?.profitability?.gross_margin?.value ? ratioReport.ratios.profitability.gross_margin.value * 100 : 0,
    operatingMargin: ratioReport?.ratios?.operations?.operating_margin?.value ? ratioReport.ratios.operations.operating_margin.value * 100 : 0,
  };

  const industryAverage = {
    roe: ratioReport?.ratios?.profitability?.roe?.thresholds?.industry_average 
      ? ratioReport.ratios.profitability.roe.thresholds.industry_average * 100 : 15.0,
    de: ratioReport?.ratios?.solvency?.debt_to_equity?.thresholds?.industry_average 
      ? ratioReport.ratios.solvency.debt_to_equity.thresholds.industry_average : 1.5,
    cr: ratioReport?.ratios?.liquidity?.current_ratio?.thresholds?.industry_average 
      ? ratioReport.ratios.liquidity.current_ratio.thresholds.industry_average : 1.2,
    grossMargin: ratioReport?.ratios?.profitability?.gross_margin?.thresholds?.industry_average 
      ? ratioReport.ratios.profitability.gross_margin.thresholds.industry_average * 100 : 30.0,
    operatingMargin: ratioReport?.ratios?.operations?.operating_margin?.thresholds?.industry_average 
      ? ratioReport.ratios.operations.operating_margin.thresholds.industry_average * 100 : 12.0,
  };

  const chartData = [
    { subject: 'ROE (%)', Company: companyMetrics.roe, Industry: industryAverage.roe },
    { subject: 'Nợ/VCSH (x10)', Company: companyMetrics.de * 10, Industry: industryAverage.de * 10 },
    { subject: 'Thanh toán (x10)', Company: companyMetrics.cr * 10, Industry: industryAverage.cr * 10 },
    { subject: 'Biên LN Gộp (%)', Company: companyMetrics.grossMargin, Industry: industryAverage.grossMargin },
    { subject: 'Biên LN HĐ (%)', Company: companyMetrics.operatingMargin, Industry: industryAverage.operatingMargin },
  ];

  // Evaluations text helper
  const getEvaluationStatusBadge = (resItem: any) => {
    const status = resItem?.status || 'UNKNOWN';
    switch (status) {
      case 'HEALTHY':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold text-status-healthy bg-status-healthy/10 px-2 py-0.5 rounded-full border border-status-healthy/20">
            <CheckCircle className="w-3 h-3" />
            <span>AN TOÀN</span>
          </span>
        );
      case 'WARNING':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold text-status-warning bg-status-warning/10 px-2 py-0.5 rounded-full border border-status-warning/20">
            <AlertTriangle className="w-3 h-3" />
            <span>CẢNH BÁO</span>
          </span>
        );
      case 'CRITICAL':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold text-status-critical bg-status-critical/10 px-2 py-0.5 rounded-full border border-status-critical/20">
            <AlertTriangle className="w-3 h-3 animate-bounce" />
            <span>RỦI RO CAO</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold text-on-surface-variant/60 bg-surface-container-high px-2 py-0.5 rounded-full">
            <span>CHƯA CÓ</span>
          </span>
        );
    }
  };

  const roeReportItem = ratioReport?.ratios?.profitability?.roe;
  const deReportItem = ratioReport?.ratios?.solvency?.debt_to_equity;
  const crReportItem = ratioReport?.ratios?.liquidity?.current_ratio;

  return (
    <div className="space-y-6">
      {/* Page Header & Selector */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shrink-0">
        <div>
          <h1 className="text-xl md:text-2xl font-display font-extrabold text-on-surface mb-2">Phân tích Chỉ số & Radar</h1>
          <p className="text-xs md:text-sm text-on-surface-variant font-medium">Đánh giá hiệu suất tài chính tổng thể so với trung bình ngành.</p>
        </div>

        {/* Ready documents select dropdown */}
        <div className="flex items-center gap-2 bg-surface-container-low p-2 rounded-xl border border-surface-border">
          <FileText className="w-4 h-4 text-on-surface-variant" />
          <select
            value={selectedDocId}
            onChange={(e) => setSelectedDocId(e.target.value)}
            className="bg-transparent text-xs font-bold text-on-surface outline-none border-0 pr-6 cursor-pointer"
          >
            {readyDocs.length === 0 ? (
              <option value="">Chưa có file sẵn sàng</option>
            ) : (
              readyDocs.map(doc => (
                <option key={doc.id} value={doc.id}>{doc.name}</option>
              ))
            )}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="h-[400px] flex items-center justify-center bg-surface-container-lowest border border-surface-border rounded-2xl shadow-sm">
          <div className="flex flex-col items-center gap-3">
            <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin" />
            <span className="text-xs font-semibold text-on-surface-variant">Đang tính toán chỉ số tài chính...</span>
          </div>
        </div>
      ) : !ratioReport ? (
        <div className="h-[250px] flex items-center justify-center bg-surface-container-lowest border border-surface-border rounded-2xl p-8 text-center text-on-surface-variant font-medium text-sm">
          Không tìm thấy tài liệu sẵn sàng nào để phân tích. Vui lòng upload tài liệu tại mục Document Hub trước!
        </div>
      ) : (
        <>
          {/* Bento Grid Layout */}
          <div className="grid grid-cols-12 gap-6">
            {/* Radar Chart Section (Spans 8 cols) */}
            <div className="col-span-12 lg:col-span-8 bg-surface-container-lowest border border-surface-border rounded-2xl p-5 shadow-sm flex flex-col">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-sm font-display font-extrabold text-on-surface">Radar Hiệu suất Tổng thể</h2>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-ai-accent" />
                    <span className="text-[10px] font-mono font-bold text-on-surface-variant uppercase">Doanh nghiệp</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full border border-outline border-dashed" />
                    <span className="text-[10px] font-mono font-bold text-on-surface-variant uppercase">Ngành</span>
                  </div>
                </div>
              </div>

              {/* Actual Radar Rendering with Recharts */}
              <div className="w-full h-[360px] flex items-center justify-center bg-surface-bright/50 rounded-xl border border-surface-border p-4">
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsRadar data={chartData}>
                    <PolarGrid stroke="#E2E8F0" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: '#45464d', fontSize: 11, fontWeight: '600' }} />
                    <PolarRadiusAxis angle={30} domain={[0, 50]} tick={{ fill: '#76777d', fontSize: 9 }} />
                    <Radar name="Doanh nghiệp" dataKey="Company" stroke="#8B5CF6" fill="#8B5CF6" fillOpacity={0.2} strokeWidth={2} />
                    <Radar name="Ngành" dataKey="Industry" stroke="#45464d" fill="none" strokeDasharray="4 4" strokeWidth={1.5} />
                  </RechartsRadar>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Benchmark Settings (Spans 4 cols) */}
            <div className="col-span-12 lg:col-span-4 bg-surface-container-lowest border border-surface-border rounded-2xl p-5 shadow-sm flex flex-col">
              <h2 className="text-sm font-display font-extrabold text-on-surface mb-3">Cài đặt Ngưỡng tham chiếu</h2>
              <p className="text-[11px] text-on-surface-variant font-medium leading-relaxed mb-5">
                Tùy chỉnh các giá trị chuẩn để FiscalMind tự động tính toán cảnh báo AI thời gian thực cho ngành **{ratioReport.sector || 'tiêu dùng'}**.
              </p>
              <div className="space-y-4 flex-1">
                <div>
                  <label className="block text-[11px] font-mono font-bold text-on-surface uppercase tracking-wider mb-1.5">
                    Mục tiêu ROE (%)
                  </label>
                  <input
                    type="number"
                    value={localRoe}
                    step="0.01"
                    onChange={(e) => setLocalRoe(parseFloat(e.target.value) || 0)}
                    className="w-full bg-surface-bright border border-surface-border rounded-xl px-3.5 py-2 text-xs font-semibold focus:ring-2 focus:ring-ai-accent/30 focus:outline-none transition-all"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono font-bold text-on-surface uppercase tracking-wider mb-1.5">
                    Giới hạn D/E (Lần)
                  </label>
                  <input
                    type="number"
                    value={localDe}
                    step="0.01"
                    onChange={(e) => setLocalDe(parseFloat(e.target.value) || 0)}
                    className="w-full bg-surface-bright border border-surface-border rounded-xl px-3.5 py-2 text-xs font-semibold focus:ring-2 focus:ring-ai-accent/30 focus:outline-none transition-all"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono font-bold text-on-surface uppercase tracking-wider mb-1.5">
                    Current Ratio Tối thiểu
                  </label>
                  <input
                    type="number"
                    value={localCr}
                    step="0.01"
                    onChange={(e) => setLocalCr(parseFloat(e.target.value) || 0)}
                    className="w-full bg-surface-bright border border-surface-border rounded-xl px-3.5 py-2 text-xs font-semibold focus:ring-2 focus:ring-ai-accent/30 focus:outline-none transition-all"
                  />
                </div>
              </div>
              <button
                onClick={handleUpdateBenchmarks}
                disabled={updatingThresholds}
                className="w-full bg-on-surface hover:bg-on-surface-variant disabled:opacity-50 text-white font-semibold text-xs py-2.5 mt-6 rounded-xl transition-all active:scale-95 shadow-sm flex items-center justify-center gap-2"
              >
                {updatingThresholds && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>Cập nhật Ngưỡng</span>
              </button>
            </div>
          </div>

          {/* Metric Cards Group with dynamic states */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Profitability Card */}
            <div className="bg-surface-container-lowest border border-surface-border border-l-4 border-l-status-healthy rounded-2xl p-5 shadow-sm hover:shadow-md transition-all duration-300 relative overflow-hidden group">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xs font-display tracking-wider text-on-surface-variant font-bold uppercase">
                    Khả năng Sinh lời (ROE)
                  </h3>
                  <div className="text-3xl font-display font-extrabold text-on-surface mt-1">
                    {roeVal}%
                  </div>
                </div>
                {getEvaluationStatusBadge(roeReportItem)}
              </div>
              <p className="text-[11px] text-on-surface-variant leading-relaxed">
                {roeReportItem?.explanation || 'Hiệu suất sinh lời trên mỗi đồng vốn góp của cổ đông (ROE).'}
              </p>
              <div className="h-px bg-surface-border my-3.5" />
              <div className="flex justify-between items-center text-[10px] text-on-surface-variant font-medium">
                <span>Mục tiêu hiện tại: {localRoe}%</span>
                <span>Trung bình ngành: {industryAverage.roe.toFixed(1)}%</span>
              </div>
            </div>

            {/* Solvency Card */}
            <div className="bg-surface-container-lowest border border-surface-border border-l-4 border-l-violet-600 rounded-2xl p-5 shadow-sm hover:shadow-md transition-all duration-300 relative overflow-hidden group">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xs font-display tracking-wider text-on-surface-variant font-bold uppercase">
                    Hệ số Nợ / VCSH (D/E)
                  </h3>
                  <div className="text-3xl font-display font-extrabold text-on-surface mt-1">
                    {deVal}x
                  </div>
                </div>
                {getEvaluationStatusBadge(deReportItem)}
              </div>
              <p className="text-[11px] text-on-surface-variant leading-relaxed">
                {deReportItem?.explanation || 'Tương quan nợ phải trả trên vốn chủ sở hữu (An toàn khi tỷ lệ < 1.0).'}
              </p>
              <div className="h-px bg-surface-border my-3.5" />
              <div className="flex justify-between items-center text-[10px] text-on-surface-variant font-medium">
                <span>Giới hạn an toàn: {localDe}x</span>
                <span>Trung bình ngành: {industryAverage.de.toFixed(2)}x</span>
              </div>
            </div>

            {/* Liquidity Card */}
            <div className="bg-surface-container-lowest border border-surface-border border-l-4 border-l-status-warning rounded-2xl p-5 shadow-sm hover:shadow-md transition-all duration-300 relative overflow-hidden group">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xs font-display tracking-wider text-on-surface-variant font-bold uppercase">
                    Thanh toán Hiện hành (CR)
                  </h3>
                  <div className="text-3xl font-display font-extrabold text-on-surface mt-1">
                    {crVal}x
                  </div>
                </div>
                {getEvaluationStatusBadge(crReportItem)}
              </div>
              <p className="text-[11px] text-on-surface-variant leading-relaxed">
                {crReportItem?.explanation || 'Khả năng chi trả nợ ngắn hạn bằng tài sản ngắn hạn.'}
              </p>
              <div className="h-px bg-surface-border my-3.5" />
              <div className="flex justify-between items-center text-[10px] text-on-surface-variant font-medium">
                <span>Ngưỡng tối thiểu: {localCr}x</span>
                <span>Trung bình ngành: {industryAverage.cr.toFixed(2)}x</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
