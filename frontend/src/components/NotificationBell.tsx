import React, { useEffect, useState, useRef } from 'react';
import { Bell, Check, CheckCheck, Info, AlertTriangle, AlertCircle, CheckCircle } from 'lucide-react';
import { notificationService } from '../services/notifications';
import { NotificationItem } from '../types';


export const NotificationBell: React.FC = () => {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchNotifications = async () => {
    try {
      const summary = await notificationService.getMyNotifications();
      setNotifications(summary.notifications || []);
      setUnreadCount(summary.unread_count || 0);
    } catch {
      // Ignore background fetch error
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 15000); // Poll every 15s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleMarkRead = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await notificationService.markRead(id);
      setNotifications(prev =>
        prev.map(n => (n.id === id ? { ...n, status: 'READ', read_at: new Date().toISOString() } : n))
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch {
      // ignore
    }
  };

  const handleMarkAllRead = async () => {
    try {
      setLoading(true);
      await notificationService.markAllRead();
      setNotifications(prev =>
        prev.map(n => ({ ...n, status: 'READ', read_at: new Date().toISOString() }))
      );
      setUnreadCount(0);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };



  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'SUCCESS':
        return <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />;
      case 'WARNING':
        return <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />;
      case 'ERROR':
        return <AlertCircle className="w-4 h-4 text-rose-500 flex-shrink-0" />;
      default:
        return <Info className="w-4 h-4 text-blue-500 flex-shrink-0" />;
    }
  };

  const getChannelBadge = (channel: string) => {
    switch (channel) {
      case 'EMAIL_MOCK':
        return <span className="text-[9px] px-1.5 py-0.2 bg-purple-50 text-purple-700 rounded border border-purple-200 font-mono">MOCK EMAIL</span>;
      case 'SMS_MOCK':
        return <span className="text-[9px] px-1.5 py-0.2 bg-cyan-50 text-cyan-700 rounded border border-cyan-200 font-mono">MOCK SMS</span>;
      default:
        return <span className="text-[9px] px-1.5 py-0.2 bg-blue-50 text-blue-700 rounded border border-blue-200 font-mono">IN-APP</span>;
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors focus:outline-none"
        title="Notifications"
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 bg-rose-600 text-white font-mono text-[10px] font-bold rounded-full ring-2 ring-white animate-pulse">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-2xl shadow-2xl border border-slate-200 z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
          <div className="p-3.5 bg-slate-50/80 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="font-bold text-xs text-slate-800 uppercase tracking-wider">
                Notifications
              </span>
              {unreadCount > 0 && (
                <span className="px-2 py-0.5 bg-rose-100 text-rose-700 text-[10px] font-mono font-bold rounded-full">
                  {unreadCount} unread
                </span>
              )}
            </div>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                disabled={loading}
                className="text-[11px] text-blue-600 hover:text-blue-800 font-semibold flex items-center space-x-1"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                <span>Mark all read</span>
              </button>
            )}
          </div>

          <div className="max-h-[380px] overflow-y-auto divide-y divide-slate-100">
            {notifications.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                <Bell className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                <p>No notifications yet</p>
              </div>
            ) : (
              notifications.map(n => {
                const isUnread = n.status !== 'READ' && !n.read_at;
                return (
                  <div
                    key={n.id}
                    className={`p-3.5 transition-colors ${
                      isUnread ? 'bg-blue-50/40 hover:bg-blue-50/70' : 'bg-white hover:bg-slate-50/80'
                    }`}
                  >
                    <div className="flex items-start space-x-3">
                      <div className="mt-0.5">{getSeverityIcon(n.severity)}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-1">
                          <h4 className="text-xs font-bold text-slate-900 truncate">
                            {n.title}
                          </h4>
                          {getChannelBadge(n.channel)}
                        </div>
                        <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                          {n.message}
                        </p>
                        <div className="flex items-center justify-between mt-2 pt-1 border-t border-slate-100/60">
                          <span className="text-[10px] text-slate-400 font-mono">
                            {new Date(n.created_at).toLocaleString([], {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                          {isUnread && (
                            <button
                              onClick={e => handleMarkRead(n.id, e)}
                              className="text-[10px] text-blue-600 hover:text-blue-800 font-medium flex items-center space-x-0.5"
                            >
                              <Check className="w-3 h-3" />
                              <span>Mark read</span>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          <div className="p-2 bg-slate-50 border-t border-slate-100 text-center">
            <span className="text-[10px] font-mono text-slate-400">
              Mock Dispatched &bull; XYZ Engineering College
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
