import { Search, Bell, Menu } from 'lucide-react';
import { Tab } from '../types';

interface NavbarProps {
  onSearchChange?: (val: string) => void;
  searchVal?: string;
  activeTab: Tab;
  setActiveTab: (tab: Tab) => void;
  setSidebarOpen: (open: boolean) => void;
}

export default function Navbar({ onSearchChange, searchVal, activeTab, setActiveTab, setSidebarOpen }: NavbarProps) {
  return (
    <header className="flex items-center justify-between h-16 px-4 md:px-8 bg-surface-bg sticky top-0 z-40 border-b border-surface-border">
      {/* Mobile Toggle & Brand */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => setSidebarOpen(true)}
          className="md:hidden text-on-surface p-2 rounded-xl hover:bg-surface-container-low transition-colors"
          id="btn-sidebar-toggle"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Search Input (Filters global file state) */}
        <div className="hidden md:flex items-center bg-surface-container-lowest border border-surface-border rounded-xl px-3 py-1.5 focus-within:ring-2 focus-within:ring-ai-accent/30 transition-all shadow-sm">
          <Search className="w-4 h-4 text-on-surface-variant mr-2" />
          <input
            type="text"
            value={searchVal || ''}
            onChange={(e) => onSearchChange?.(e.target.value)}
            className="bg-transparent border-none outline-none text-xs font-sans text-on-surface placeholder:text-outline w-64 p-0 focus:ring-0"
            placeholder="Search files or reports..."
            id="input-navbar-search"
          />
        </div>
      </div>

      {/* Center Tabs (Documents / Reports / Settings) */}
      <div className="hidden md:flex items-center gap-8">
        <button
          onClick={() => setActiveTab('document-hub')}
          className={`font-display text-xs tracking-wider font-semibold uppercase pb-1.5 border-b-2 transition-all ${
            activeTab === 'document-hub'
              ? 'border-on-surface text-on-surface font-bold'
              : 'border-transparent text-on-surface-variant hover:text-on-surface'
          }`}
          id="tab-documents"
        >
          Documents
        </button>
        <button
          onClick={() => setActiveTab('comparison')}
          className={`font-display text-xs tracking-wider font-semibold uppercase pb-1.5 border-b-2 transition-all ${
            activeTab === 'comparison'
              ? 'border-on-surface text-on-surface font-bold'
              : 'border-transparent text-on-surface-variant hover:text-on-surface'
          }`}
          id="tab-reports"
        >
          Reports
        </button>
        <button
          onClick={() => setActiveTab('radar')}
          className={`font-display text-xs tracking-wider font-semibold uppercase pb-1.5 border-b-2 transition-all ${
            activeTab === 'radar'
              ? 'border-on-surface text-on-surface font-bold'
              : 'border-transparent text-on-surface-variant hover:text-on-surface'
          }`}
          id="tab-settings"
        >
          Radar Settings
        </button>
      </div>

      {/* Trailing Actions & User Profile */}
      <div className="flex items-center gap-4">
        <button
          className="text-on-surface-variant hover:text-on-surface transition-colors p-2 rounded-full hover:bg-surface-container-low relative"
          id="btn-notifications"
          onClick={() => alert('FiscalMind: No new notifications. AI CFO Advisor is active.')}
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-status-warning rounded-full border-2 border-surface-bg" />
        </button>

        <div className="h-6 w-px bg-surface-border hidden md:block" />

        <div
          className="w-8 h-8 rounded-full border border-surface-border overflow-hidden cursor-pointer hover:ring-2 hover:ring-ai-accent transition-all duration-200"
          id="profile-avatar"
          title="User Account"
          onClick={() => alert('Logged in as Corporate Analyst (quangvinhwr87@gmail.com)')}
        >
          <img
            alt="User Avatar"
            className="w-full h-full object-cover"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuAWF1iVV8gm_tfzvngZG8nydQqp9ghEutJ9vrirWybvu-POxm4wRV29pvx5BjrQg9x4nhBYY6cpO4_un50XMpGOQ2FPjDdPfbS35HLwiCo6PYvvm1SuoJ4_spCIQAbAMpZBAwj0FmVy5abl2YwXhhvaGaokzPDd9W4Z1_Vl-V0pnEnIReberpaCO0ZNZ8cbdPXJcSL7F32_7ENvMqvjNlBTnlQ6m67M8De2KWc3MH1f3eEdJeGoYwdCTRvKiZkfHSXW0lJDiVJuqw86"
          />
        </div>
      </div>
    </header>
  );
}
