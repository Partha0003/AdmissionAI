import React, { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from '../components/Header';
import { Sidebar } from '../components/Sidebar';
import { authService } from '../services/auth';
import { User, UserRole } from '../types';

export const AdminLayout: React.FC = () => {
  const [user, setUser] = useState<User | null>(authService.getStoredUser());

  useEffect(() => {
    authService.getCurrentUser().then(setUser).catch(() => {});
  }, []);

  const adminRole: UserRole = (user?.role as UserRole) || 'ADMIN_VERIFIER';

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Header user={user} />
      <div className="flex flex-1 max-w-7xl w-full mx-auto">
        <Sidebar role={adminRole} />
        <main className="flex-1 p-6 lg:p-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
