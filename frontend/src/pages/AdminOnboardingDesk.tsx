import React, { useState, useEffect } from 'react';
import {
  Calendar,
  Bus,
  Filter,
  RefreshCw,
} from 'lucide-react';
import { onboardingService } from '../services/onboarding';
import {
  OnboardingProfile,
  StudentType,
  InaugurationEvent,
  TransportConfig,
  OnboardingAuditLog,
} from '../types';

export const AdminOnboardingDesk: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'profiles' | 'config' | 'audit'>('profiles');
  const [profiles, setProfiles] = useState<OnboardingProfile[]>([]);
  const [auditLogs, setAuditLogs] = useState<OnboardingAuditLog[]>([]);
  const [inauguration, setInauguration] = useState<InaugurationEvent | null>(null);
  const [transport, setTransport] = useState<TransportConfig | null>(null);

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [filterType, setFilterType] = useState<string>('');

  useEffect(() => {
    loadAdminData();
  }, [activeTab, filterType]);

  const loadAdminData = async () => {
    try {
      setLoading(true);
      if (activeTab === 'profiles') {
        const profs = await onboardingService.listProfiles({
          student_type: filterType || undefined,
        });
        setProfiles(profs);
      } else if (activeTab === 'config') {
        const [inaug, trans] = await Promise.all([
          onboardingService.getInauguration(),
          onboardingService.getTransport(),
        ]);
        setInauguration(inaug);
        setTransport(trans);
      } else if (activeTab === 'audit') {
        const logs = await onboardingService.listAuditLogs({ limit: 100 });
        setAuditLogs(logs);
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to load onboarding desk data.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmType = async (studentId: string, type: StudentType) => {
    try {
      setActionLoading(true);
      await onboardingService.confirmStudentType(studentId, type);
      await loadAdminData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to confirm student type.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-16">
      {/* Institutional Header */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white p-8 rounded-3xl shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-3 py-1 bg-amber-500/20 border border-amber-400/40 text-amber-300 text-xs font-semibold rounded-full uppercase tracking-wider">
                Prototype / Demo Only
              </span>
              <span className="px-3 py-1 bg-indigo-500/30 border border-indigo-400/40 text-indigo-200 text-xs font-semibold rounded-full">
                Admin & Verifier Control Desk
              </span>
            </div>
            <h1 className="text-3xl font-black tracking-tight">XYZ Engineering College (Code: XYZ)</h1>
            <p className="text-indigo-200 text-sm mt-1">
              Academic Year 2026–27 • First-Year Onboarding, Commute Confirmation & Audit Desk
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => loadAdminData()}
              className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 text-white text-xs font-bold rounded-xl transition backdrop-blur-sm"
            >
              <RefreshCw className="w-4 h-4" /> Refresh Desk
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-3 mt-8 border-t border-white/10 pt-4">
          <button
            onClick={() => setActiveTab('profiles')}
            className={`px-4 py-2 rounded-xl font-bold text-xs transition ${
              activeTab === 'profiles' ? 'bg-white text-slate-900 shadow-md' : 'text-indigo-200 hover:bg-white/10'
            }`}
          >
            Student Profiles & Confirmations
          </button>
          <button
            onClick={() => setActiveTab('config')}
            className={`px-4 py-2 rounded-xl font-bold text-xs transition ${
              activeTab === 'config' ? 'bg-white text-slate-900 shadow-md' : 'text-indigo-200 hover:bg-white/10'
            }`}
          >
            Inauguration & Transport Settings
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`px-4 py-2 rounded-xl font-bold text-xs transition ${
              activeTab === 'audit' ? 'bg-white text-slate-900 shadow-md' : 'text-indigo-200 hover:bg-white/10'
            }`}
          >
            Append-Only Audit Logs
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center min-h-[300px] space-y-4">
          <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-slate-600 font-medium text-sm">Loading desk data...</p>
        </div>
      ) : activeTab === 'profiles' ? (
        /* Profiles Tab */
        <div className="space-y-6">
          <div className="bg-white p-4 rounded-2xl border border-slate-200 flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-3">
              <Filter className="w-4 h-4 text-slate-400" />
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">Filter By Type:</span>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="text-xs font-semibold px-3 py-1.5 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Types</option>
                <option value="DAY_SCHOLAR">Day-Scholar</option>
                <option value="HOSTELLER">Hosteller</option>
                <option value="UNSPECIFIED">Unspecified</option>
              </select>
            </div>
            <div className="text-xs font-bold text-slate-500">
              {profiles.length} Student Profile(s) Loaded
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider">
                <tr>
                  <th className="p-4">Student ID</th>
                  <th className="p-4">Student Type</th>
                  <th className="p-4">Workflow Status</th>
                  <th className="p-4">Onboarding State</th>
                  <th className="p-4">Completion</th>
                  <th className="p-4 text-right">Confirm / Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {profiles.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50/60">
                    <td className="p-4 font-mono font-bold text-slate-800">{p.student_id}</td>
                    <td className="p-4">
                      <span className="font-bold text-slate-800">{p.student_type}</span>
                    </td>
                    <td className="p-4">
                      <span
                        className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${
                          p.student_type_status === 'ADMIN_CONFIRMED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : p.student_type_status === 'STUDENT_REQUESTED'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {p.student_type_status}
                      </span>
                    </td>
                    <td className="p-4 font-semibold text-slate-600">{p.onboarding_status}</td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-2 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-indigo-600 rounded-full"
                            style={{ width: `${p.overall_completion_percentage}%` }}
                          ></div>
                        </div>
                        <span className="font-bold text-slate-700">{p.overall_completion_percentage}%</span>
                      </div>
                    </td>
                    <td className="p-4 text-right space-x-2">
                      <button
                        type="button"
                        disabled={actionLoading}
                        onClick={() => handleConfirmType(p.student_id, 'DAY_SCHOLAR')}
                        className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-md text-[11px] transition"
                      >
                        Confirm Day-Scholar
                      </button>
                      <button
                        type="button"
                        disabled={actionLoading}
                        onClick={() => handleConfirmType(p.student_id, 'HOSTELLER')}
                        className="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold rounded-md text-[11px] transition"
                      >
                        Confirm Hosteller
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : activeTab === 'config' ? (
        /* Config Tab */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {inauguration && (
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <h3 className="font-bold text-lg text-slate-800 flex items-center gap-2">
                <Calendar className="w-5 h-5 text-indigo-600" /> Inauguration Ceremony Configuration
              </h3>
              <div className="text-xs space-y-2 text-slate-600">
                <p><span className="font-bold text-slate-700">Event Date:</span> {inauguration.event_date}</p>
                <p><span className="font-bold text-slate-700">Reporting:</span> {inauguration.reporting_time}</p>
                <p><span className="font-bold text-slate-700">Ceremony:</span> {inauguration.ceremony_time}</p>
                <p><span className="font-bold text-slate-700">Venue:</span> {inauguration.venue}</p>
                <p><span className="font-bold text-slate-700">Dynamic Status:</span> {inauguration.event_status}</p>
              </div>
            </div>
          )}

          {transport && (
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <h3 className="font-bold text-lg text-slate-800 flex items-center gap-2">
                <Bus className="w-5 h-5 text-indigo-600" /> Transport Configuration (XYZ Routes)
              </h3>
              <div className="text-xs space-y-2 text-slate-600">
                <p><span className="font-bold text-slate-700">College Code:</span> {transport.college_code}</p>
                <p><span className="font-bold text-slate-700">Status:</span> {transport.is_configured ? 'Configured' : 'Prototype Default Notice'}</p>
                <p className="text-slate-500 italic">{transport.message || transport.general_instructions}</p>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Audit Tab */
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider">
              <tr>
                <th className="p-4">Timestamp</th>
                <th className="p-4">Actor</th>
                <th className="p-4">Action</th>
                <th className="p-4">Student ID</th>
                <th className="p-4">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {auditLogs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50/60">
                  <td className="p-4 text-slate-500 font-mono">{new Date(log.created_at).toLocaleString()}</td>
                  <td className="p-4">
                    <span className="font-bold text-slate-800">{log.actor_role}</span>
                    <span className="block text-[10px] text-slate-400">{log.actor_id}</span>
                  </td>
                  <td className="p-4">
                    <span className="font-bold text-indigo-700 bg-indigo-50 px-2.5 py-1 rounded">
                      {log.action}
                    </span>
                  </td>
                  <td className="p-4 font-mono text-slate-700">{log.student_id || '-'}</td>
                  <td className="p-4 font-mono text-[11px] text-slate-600">
                    {JSON.stringify(log.details_json)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
