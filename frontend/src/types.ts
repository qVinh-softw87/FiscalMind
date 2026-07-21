export type Tab = 'dashboard' | 'document-hub' | 'ai-chat' | 'radar' | 'comparison';

export type DocStatus = 'ready' | 'processing' | 'pending' | 'failed';

export interface Document {
  id: string;
  name: string;
  uploadDate: string;
  size: string;
  status: DocStatus;
  type: 'pdf' | 'excel' | 'word' | 'csv';
}

export interface Citation {
  id: number;
  source: string;
  text: string;
}

export interface Message {
  id: string;
  sender: 'ai' | 'user';
  text: string;
  timestamp: string;
  citations?: Citation[];
  verified?: boolean;
}

export interface ChatHistoryItem {
  id: string;
  title: string;
  timestamp: string;
}

export interface BenchmarkSettings {
  roeTarget: number;
  deLimit: number;
  currentRatioMin: number;
}

export interface IndicatorMatrixRow {
  metric: string;
  vnm: { value: string; trend?: 'up' | 'down' | 'trophy' | 'warning' | 'normal'; badge?: string };
  msn: { value: string; trend?: 'up' | 'down' | 'trophy' | 'warning' | 'normal'; badge?: string };
  fpt: { value: string; trend?: 'up' | 'down' | 'trophy' | 'warning' | 'normal'; badge?: string };
}
