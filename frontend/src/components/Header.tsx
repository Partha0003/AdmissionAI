import React from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, User as UserIcon, GraduationCap } from 'lucide-react';
import { institutionConfig } from '../config/institution';
import { authService } from '../services/auth';
import { User } from '../types';
import { NotificationBell } from './NotificationBell';

interface HeaderProps {
  user: User | null;
}

export const Header: React.FC<HeaderProps> = ({ user }) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo & Institution branding */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <GraduationCap className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg text-slate-900 tracking-tight">
                  {institutionConfig.platformName}
                </span>
                <span className="text-[10px] font-mono font-semibold bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded border border-amber-300">
                  PROTOTYPE
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">
                {institutionConfig.name} &bull; Admissions {institutionConfig.academicYear}
              </p>
            </div>
          </div>

          {/* User profile & actions */}
          <div className="flex items-center space-x-4">
            {user && (
              <div className="flex items-center space-x-3 border-l border-slate-200 pl-4">
                <NotificationBell />
                <div className="text-right">
                  <p className="text-xs font-semibold text-slate-800">{user.email}</p>
                  <span className="inline-block text-[10px] font-mono px-2 py-0.5 bg-blue-50 text-blue-700 rounded border border-blue-200 font-bold">
                    {user.role}
                  </span>
                </div>
                <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center text-slate-600">
                  <UserIcon className="w-4 h-4" />
                </div>
                <button
                  onClick={handleLogout}
                  title="Logout"
                  className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

