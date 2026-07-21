import { FileText, CheckCircle2, RefreshCw, AlertCircle } from 'lucide-react';
import { Document } from '../types';

interface DashboardStatsProps {
  documents: Document[];
}

export default function DashboardStats({ documents }: DashboardStatsProps) {
  const total = documents.length;
  const ready = documents.filter((d) => d.status === 'ready').length;
  const processing = documents.filter((d) => d.status === 'processing').length;
  const failed = documents.filter((d) => d.status === 'failed').length;

  const stats = [
    {
      label: 'Tổng Tài Liệu',
      value: total,
      icon: FileText,
      color: 'border-l-on-surface text-on-surface',
    },
    {
      label: 'Sẵn Sàng',
      value: ready,
      icon: CheckCircle2,
      color: 'border-l-status-healthy text-status-healthy',
    },
    {
      label: 'Đang Xử Lý',
      value: processing,
      icon: RefreshCw,
      color: 'border-l-status-warning text-status-warning',
      isSpinning: processing > 0,
    },
    {
      label: 'Lỗi',
      value: failed,
      icon: AlertCircle,
      color: 'border-l-status-critical text-status-critical',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {stats.map((stat, idx) => {
        const Icon = stat.icon;
        return (
          <div
            key={idx}
            className={`bg-surface-container-lowest rounded-2xl p-5 border border-surface-border border-l-4 ${stat.color} shadow-sm hover:shadow-md transition-all duration-300 flex flex-col justify-between h-32 relative overflow-hidden`}
            id={`stat-card-${idx}`}
          >
            <div className="flex justify-between items-start">
              <span className="text-xs font-display tracking-widest text-on-surface-variant font-bold uppercase">
                {stat.label}
              </span>
              <Icon className={`w-5 h-5 ${stat.isSpinning ? 'animate-spin' : ''}`} />
            </div>
            <div className="text-4xl font-display font-extrabold text-on-surface leading-none">
              {stat.value}
            </div>
          </div>
        );
      })}
    </div>
  );
}
