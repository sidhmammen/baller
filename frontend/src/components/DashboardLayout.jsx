import React, { useState } from 'react';
import { Menu, Zap, Users, Search, LogOut } from 'lucide-react';
import { NotificationBell } from './NotificationBell';

const SIDEBAR_TABS = [
  { id: 'roster', label: 'Roster', icon: Users },
  { id: 'waiver', label: 'Free agents', icon: Zap },
]

export default function DashboardLayout({ children, sessionId, notifications, onMarkRead, activeTab, onTabChange, connected }) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-black text-zinc-100 font-sans selection:bg-orange-500 selection:text-white antialiased">

      {/* Sidebar */}
      <aside className="bg-zinc-950/80 backdrop-blur-2xl border-r border-white/5 lg:w-64 w-full lg:h-screen h-16 px-4 lg:px-6 py-4 flex lg:flex-col items-center lg:items-stretch gap-4 lg:gap-6 sticky top-0 z-50">
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2 text-2xl font-serif font-semibold tracking-tight text-orange-500">
             <Zap className="w-6 h-6 text-orange-500 fill-orange-500"/>
             <span className="hidden lg:inline tracking-tight">Baller</span>
          </div>
          <div className="flex items-center gap-2">
             {/* Connection status */}
             <div className={(
               'flex items-center gap-1.5 text-[10px] font-mono px-2 py-0.5 rounded-full border',
               connected
                 ? 'text-green-400 border-green-500/30 bg-green-500/10'
                 : 'text-zinc-500 border-zinc-700 bg-transparent'
             )}>
               <span className={(
                 'w-1.5 h-1.5 rounded-full',
                 connected ? 'bg-green-400 animate-pulse' : 'bg-zinc-500'
               )} />
               {connected ? 'LIVE' : 'offline'}
             </div>
             <button className="lg:hidden p-2 text-zinc-400" onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}>
               <Menu className="w-6 h-6"/>
             </button>
          </div>
        </div>

        <nav className={`lg:flex flex-col gap-2 w-full flex-1 ${isMobileMenuOpen ? 'flex absolute top-16 left-0 bg-zinc-950/98 backdrop-blur-2xl p-6 border-b border-white/5' : 'hidden'}`}>
          <span className="uppercase text-xs font-medium text-zinc-500 mt-4 lg:mt-0 tracking-wide">Menu</span>

          {SIDEBAR_TABS.map(tab => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange?.(tab.id)}
                className={`flex items-center gap-3 py-2.5 px-3 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-orange-500/10 text-orange-500 border border-orange-500/20 shadow-[0_4px_30px_rgba(255,149,0,0.1)]'
                    : 'hover:bg-white/5 text-zinc-300'
                }`}
              >
                 <Icon className="w-4 h-4" /> {tab.label}
                {tab.id === 'waiver' && (
                  <span className="ml-auto text-[10px] font-medium bg-orange-500/20 text-orange-500 rounded-full py-0.5 px-2 pulse-glow">LIVE</span>
                )}
              </button>
            )
          })}

          {/* AI Agent Status */}
          <div className="mt-auto bg-white/5 border border-white/5 rounded-2xl p-4 backdrop-blur-md">
             <div className="flex items-center gap-2 mb-2">
                 <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.8)]"></span>
                 <h3 className="text-sm font-medium text-white">Agent Connected</h3>
             </div>
             <p className="text-xs text-zinc-400 mb-3">Chat active. Real-time lineup alerts.</p>
             <button className="w-full text-xs bg-orange-500/10 hover:bg-orange-500/20 text-orange-500 font-medium rounded-xl px-4 py-2 transition-all">
               Start Chat
             </button>
          </div>
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 p-4 lg:p-6 overflow-y-auto">

        {/* Topbar */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div className="flex-1 max-w-md relative group">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-orange-500 transition-colors" />
            <input
              type="text"
              placeholder="Search players, teams..."
              className="w-full pl-10 pr-20 py-2.5 rounded-xl border border-white/5 bg-white/5 focus:bg-white/10 backdrop-blur-md text-sm focus:outline-none focus:ring-1 focus:ring-orange-500 focus:border-orange-500 text-zinc-100 placeholder-zinc-500 transition-all"
            />
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <span className="hidden md:inline text-xs font-medium text-zinc-500 bg-black/20 border border-white/5 rounded px-2 py-1 font-mono">⌘K</span>
            </div>
          </div>

          <div className="flex items-center gap-3 pl-3 sm:border-l sm:border-white/10">
            <NotificationBell sessionId={sessionId} notifications={notifications || []} onMarkRead={onMarkRead} />
            <button className="relative p-2 rounded-xl text-zinc-400 hover:text-white hover:bg-white/5 transition-colors">
              <LogOut size={20} />
            </button>
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-orange-600 to-zinc-900 border border-white/10 flex items-center justify-center font-serif font-bold text-lg text-white">
              GM
            </div>
          </div>
        </div>

        {/* Dynamic Children Mount (Where you drop WeeklySchedule, etc.) */}
        <div className="animate-in fade-in duration-300">
           {children}
        </div>

      </main>
    </div>
  );
}