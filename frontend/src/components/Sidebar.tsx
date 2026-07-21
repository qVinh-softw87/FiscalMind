import { LayoutDashboard, FolderOpen, Bot, Radar, ArrowLeftRight, Settings, HelpCircle, Plus, Sparkles, LogOut } from 'lucide-react';
import { Tab } from '../types';

interface SidebarProps {
  activeTab: Tab;
  setActiveTab: (tab: Tab) => void;
  onNewAnalysis?: () => void;
  onLogout?: () => void;
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
}

export default function Sidebar({ activeTab, setActiveTab, onNewAnalysis, onLogout, isOpen, setIsOpen }: SidebarProps) {
  const menuItems = [
    { id: 'dashboard' as Tab, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'document-hub' as Tab, label: 'Document Hub', icon: FolderOpen },
    { id: 'ai-chat' as Tab, label: 'AI Chat Assistant', icon: Bot, isAi: true },
    { id: 'radar' as Tab, label: 'Analysis & Radar', icon: Radar },
    { id: 'comparison' as Tab, label: 'Cross-Comparison', icon: ArrowLeftRight },
  ];

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 md:hidden transition-opacity duration-300"
          onClick={() => setIsOpen(false)}
        />
      )}

      <aside
        className={`fixed left-0 top-0 h-screen w-[260px] border-r border-surface-border dark:border-on-primary-container bg-surface-container-lowest dark:bg-primary-container flex flex-col py-6 z-50 transition-transform duration-300 md:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand */}
        <div className="px-6 mb-6 flex flex-col gap-1">
          <div className="flex items-center gap-2.5 text-xl font-display font-extrabold text-on-surface dark:text-inverse-on-surface">
            <div className="bg-primary-container dark:bg-inverse-primary p-1.5 rounded-lg flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-ai-accent" />
            </div>
            <span>FiscalMind AI</span>
          </div>
          <span className="font-mono text-[10px] tracking-wider text-on-surface-variant font-medium uppercase ml-1">
            Technical Corporate v1.0
          </span>
        </div>

        {/* Primary CTA */}
        <div className="px-6 mb-6">
          <button
            onClick={onNewAnalysis}
            className="w-full flex items-center justify-center gap-2 bg-on-surface hover:bg-on-surface-variant text-white font-semibold text-sm py-2.5 px-4 rounded-xl shadow-sm hover:shadow transition-all duration-200 group active:scale-95"
            id="btn-new-analysis"
          >
            <Plus className="w-4 h-4 group-hover:rotate-90 transition-transform duration-200" />
            <span>New Analysis</span>
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 flex flex-col gap-1 px-3 overflow-y-auto custom-scrollbar">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  setIsOpen(false);
                }}
                className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-surface-container-high dark:bg-on-primary-fixed-variant text-on-surface dark:text-inverse-on-surface font-semibold shadow-sm'
                    : 'text-on-surface-variant dark:text-on-primary-container hover:bg-surface-container-low hover:text-on-surface dark:hover:bg-on-primary-fixed-variant/40'
                }`}
                id={`nav-${item.id}`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-[18px] h-[18px] ${isActive && item.isAi ? 'text-ai-accent' : ''}`} />
                  <span className="font-display font-medium">{item.label}</span>
                </div>
                {isActive && (
                  <span className="w-1.5 h-1.5 rounded-full bg-ai-accent animate-pulse" />
                )}
              </button>
            );
          })}
        </nav>

        {/* Footer Links */}
        <div className="px-3 pt-4 border-t border-surface-border flex flex-col gap-1">
          <button
            onClick={() => setActiveTab('dashboard')}
            className="flex items-center gap-3 px-3.5 py-2 rounded-lg text-xs font-mono tracking-wide text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface transition-colors duration-200 text-left"
            id="nav-settings"
          >
            <Settings className="w-4 h-4" />
            <span>SETTINGS</span>
          </button>
          {onLogout && (
            <button
              onClick={onLogout}
              className="flex items-center gap-3 px-3.5 py-2 rounded-lg text-xs font-mono tracking-wide text-status-critical/80 hover:bg-status-critical/10 hover:text-status-critical transition-colors duration-200 text-left font-bold"
              id="nav-logout"
            >
              <LogOut className="w-4 h-4" />
              <span>LOGOUT</span>
            </button>
          )}
        </div>
      </aside>
    </>
  );
}
