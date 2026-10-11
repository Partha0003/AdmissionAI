import React from 'react';
import { Outlet } from 'react-router-dom';
import { GraduationCap, ShieldCheck } from 'lucide-react';
import { institutionConfig } from '../config/institution';

export const AuthLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-950 flex flex-col justify-between p-4 sm:p-6 lg:p-8">
      {/* Top Bar */}
      <div className="flex items-center justify-between max-w-7xl mx-auto w-full">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/30">
            <GraduationCap className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white tracking-tight">{institutionConfig.platformName}</h1>
            <p className="text-xs text-slate-400">{institutionConfig.name}</p>
          </div>
        </div>

        <div className="flex items-center space-x-2 text-xs text-amber-400 bg-amber-950/60 border border-amber-800/80 px-3 py-1.5 rounded-lg">
          <ShieldCheck className="w-4 h-4 text-amber-400" />
          <span className="font-mono">{institutionConfig.environmentBadge}</span>
        </div>
      </div>

      {/* Main Outlet */}
      <div className="flex items-center justify-center my-8">
        <Outlet />
      </div>

      {/* Footer */}
      <div className="text-center text-xs text-slate-500 max-w-md mx-auto">
        <p>&copy; 2026 {institutionConfig.name}. All simulated rights reserved.</p>
        <p className="mt-1 text-[11px] text-slate-600">
          This system is an academic research prototype for M.Tech AI & Data Science.
        </p>
      </div>
    </div>
  );
};
