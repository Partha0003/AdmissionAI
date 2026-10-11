import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  FileText, 
  CreditCard, 
  Users, 
  FileCheck, 
  UploadCloud,
  FolderCheck,
  Server,
  BarChart3,
  Bot,
  BookOpen,
  Sparkles,
  UserCheck,
} from 'lucide-react';
import { UserRole } from '../types';

interface SidebarProps {
  role: UserRole;
}

export const Sidebar: React.FC<SidebarProps> = ({ role }) => {
  const isStudent = role === 'STUDENT' || role === 'PARENT';

  const studentLinks = [
    { to: '/student/dashboard', label: 'Admission Dashboard', icon: LayoutDashboard, active: true },
    { to: '/application/form', label: 'Online Application Form', icon: FileText, active: true },
    { to: '/application/status', label: 'Application Dossier', icon: FolderCheck, active: true },
    { to: '/student/chat', label: 'AI Admission Assistant', icon: Bot, active: true },
    { to: '/student/onboarding', label: 'First-Year Onboarding', icon: Sparkles, active: true },
    { to: '/parent/dashboard', label: 'Parent & Guardian Portal', icon: Users, active: true },
  ];

  const adminLinks = [
    { to: '/admin/dashboard', label: 'Admin Overview', icon: LayoutDashboard, active: true },
    { to: '/admin/tnea-import', label: 'TNEA Mock Import', icon: UploadCloud, active: true },
    { to: '/admin/allotments', label: 'Allotments Registry', icon: Users, active: true },
    { to: '/admin/applications', label: 'Application Scrutiny Desk', icon: FileCheck, active: true },
    { to: '/admin/physical-verification', label: 'Physical Verification Desk', icon: FolderCheck, active: true },
    { to: '/admin/payments', label: 'Finance Settlement Desk', icon: CreditCard, active: true },
    { to: '/admin/erp', label: 'ERP Staging Console', icon: Server, active: true },
    { to: '/admin/knowledge', label: 'Knowledge & Policy Desk', icon: BookOpen, active: true },
    { to: '/admin/onboarding', label: 'Student Onboarding Desk', icon: UserCheck, active: true },
    { to: '/admin/analytics', label: 'Operations Analytics', icon: BarChart3, active: true },
  ];

  const links = isStudent ? studentLinks : adminLinks;

  return (
    <aside className="w-64 bg-white border-r border-slate-200 min-h-[calc(100vh-4rem)] p-4 flex flex-col justify-between">
      <div className="space-y-1">
        <div className="px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
          {isStudent ? 'Student & Parent Portal' : 'Administrative Console'}
        </div>

        {links.map((link, idx) => {
          const Icon = link.icon;
          return link.active ? (
            <NavLink
              key={idx}
              to={link.to}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700 font-semibold'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`
              }
            >
              <Icon className="w-4 h-4 text-indigo-600" />
              <span>{link.label}</span>
            </NavLink>
          ) : (
            <div
              key={idx}
              className="flex items-center justify-between px-3 py-2.5 rounded-lg text-sm text-slate-400 cursor-not-allowed opacity-60 hover:bg-slate-50/50"
            >
              <div className="flex items-center space-x-3">
                <Icon className="w-4 h-4 text-slate-300" />
                <span>{link.label}</span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-500">
        <p className="font-semibold text-slate-700">Prototype Disclaimer</p>
        <p className="mt-1 text-[11px] leading-relaxed">
          Phase 10 Active: Context-aware student/parent onboarding, first-year induction guidelines, Day-Scholar vs Hosteller personalization, and secure single-use parent tokens.
        </p>
      </div>
    </aside>
  );
};
