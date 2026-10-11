import React, { useEffect, useState } from 'react';
import { 
  Clock, 
  FileText, 
  CheckCircle2, 
  AlertTriangle, 
  CreditCard, 
  Server, 
  Bell, 
  RefreshCw,
  AlertCircle,
  FolderCheck
} from 'lucide-react';
import { analyticsService } from '../services/analytics';
import { AnalyticsOverview } from '../types';
import { institutionConfig } from '../config/institution';

export const AdminAnalyticsDashboard: React.FC = () => {
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [dateFilter, setDateFilter] = useState<'today' | 'last_7_days' | 'last_30_days' | 'all_time'>('all_time');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchAnalytics = async (filter: 'today' | 'last_7_days' | 'last_30_days' | 'all_time') => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const res = await analyticsService.getOverview(filter);
      setData(res);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to load operational analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics(dateFilter);
  }, [dateFilter]);

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-blue-950 rounded-2xl p-6 text-white shadow-lg relative overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-[10px] font-mono bg-blue-500/20 text-blue-200 border border-blue-400/30 px-2 py-0.5 rounded font-bold uppercase tracking-wider">
                Phase 8 &bull; Operational Analytics Console
              </span>
              <span className="text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 px-2 py-0.5 rounded font-bold">
                READ-ONLY &bull; ZERO MUTATION &bull; DATABASE-DERIVED
              </span>
            </div>
            <h1 className="text-2xl font-bold mt-2">
              Institutional Admission Operations Analytics
            </h1>
            <p className="text-xs text-blue-200 mt-0.5">
              {institutionConfig.name} &bull; Academic Year {institutionConfig.academicYear}
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <div className="flex items-center bg-white/10 p-1 rounded-xl border border-white/20">
              {(['today', 'last_7_days', 'last_30_days', 'all_time'] as const).map(f => (
                <button
                  key={f}
                  onClick={() => setDateFilter(f)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition ${
                    dateFilter === f ? 'bg-white text-slate-900 font-bold shadow-sm' : 'text-white/80 hover:text-white'
                  }`}
                >
                  {f === 'today' ? 'Today' : f === 'last_7_days' ? 'Last 7 Days' : f === 'last_30_days' ? 'Last 30 Days' : 'All Time'}
                </button>
              ))}
            </div>

            <button
              onClick={() => fetchAnalytics(dateFilter)}
              className="p-2 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3.5 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {loading ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-600" />
          <p className="text-xs font-mono">Computing database-derived analytics metrics...</p>
        </div>
      ) : data ? (
        <div className="space-y-6">
          {/* Bottlenecks / Alert Banner if any */}
          {data.bottlenecks && data.bottlenecks.length > 0 && (
            <div className="p-4 bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-amber-300 rounded-2xl shadow-sm space-y-2">
              <div className="flex items-center space-x-2 text-amber-900 font-bold text-xs uppercase tracking-wide">
                <AlertTriangle className="w-4 h-4 text-amber-700" />
                <span>Operational Bottleneck Alerts</span>
              </div>
              <ul className="list-disc list-inside text-xs text-amber-950 space-y-1">
                {data.bottlenecks.map((b, i) => (
                  <li key={i}>{b}</li>
                ))}
              </ul>
            </div>
          )}

          {/* 6 Key Operational Domain Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {/* 1. Applications */}
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <div className="flex items-center space-x-2">
                  <FileText className="w-4 h-4 text-blue-600" />
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Digital Applications
                  </h3>
                </div>
                <span className="text-xs font-bold font-mono text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                  {data.applications.total} Total
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 bg-slate-50 rounded-xl">
                  <span className="text-slate-400 text-[10px] uppercase font-bold">Submitted</span>
                  <p className="font-bold text-slate-900 text-sm mt-0.5">{data.applications.submitted}</p>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-xl">
                  <span className="text-slate-400 text-[10px] uppercase font-bold">Incomplete</span>
                  <p className="font-bold text-slate-900 text-sm mt-0.5">{data.applications.incomplete}</p>
                </div>
                <div className="p-2.5 bg-amber-50 rounded-xl col-span-2">
                  <span className="text-amber-800 text-[10px] uppercase font-bold">Correction Required</span>
                  <p className="font-bold text-amber-900 text-sm mt-0.5">{data.applications.correction_required}</p>
                </div>
              </div>
            </div>

            {/* 2. Documents & Scrutiny */}
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <div className="flex items-center space-x-2">
                  <FolderCheck className="w-4 h-4 text-indigo-600" />
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Certificates &amp; Scrutiny
                  </h3>
                </div>
                <span className="text-xs font-bold font-mono text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
                  {data.documents.total_uploaded} Uploaded
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 bg-emerald-50 rounded-xl">
                  <span className="text-emerald-700 text-[10px] uppercase font-bold">Verified</span>
                  <p className="font-bold text-emerald-900 text-sm mt-0.5">{data.documents.verified}</p>
                </div>
                <div className="p-2.5 bg-indigo-50 rounded-xl">
                  <span className="text-indigo-700 text-[10px] uppercase font-bold">Pending Scrutiny</span>
                  <p className="font-bold text-indigo-900 text-sm mt-0.5">{data.documents.pending_scrutiny}</p>
                </div>
                <div className="p-2.5 bg-amber-50 rounded-xl col-span-2">
                  <span className="text-amber-800 text-[10px] uppercase font-bold">Document Corrections</span>
                  <p className="font-bold text-amber-900 text-sm mt-0.5">{data.documents.correction_required}</p>
                </div>
              </div>
            </div>

            {/* 3. Physical Verification */}
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Physical Verification
                  </h3>
                </div>
                <span className="text-xs font-bold font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                  {data.physical_verification.appointments_scheduled} Appts
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 bg-slate-50 rounded-xl">
                  <span className="text-slate-400 text-[10px] uppercase font-bold">Checked In</span>
                  <p className="font-bold text-slate-900 text-sm mt-0.5">{data.physical_verification.checked_in}</p>
                </div>
                <div className="p-2.5 bg-emerald-50 rounded-xl">
                  <span className="text-emerald-700 text-[10px] uppercase font-bold">Completed</span>
                  <p className="font-bold text-emerald-900 text-sm mt-0.5">{data.physical_verification.completed}</p>
                </div>
                <div className="p-2.5 bg-amber-50 rounded-xl col-span-2">
                  <span className="text-amber-800 text-[10px] uppercase font-bold">Physical Corrections</span>
                  <p className="font-bold text-amber-900 text-sm mt-0.5">{data.physical_verification.correction_required}</p>
                </div>
              </div>
            </div>

            {/* 4. Payment & DD Settlement */}
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <div className="flex items-center space-x-2">
                  <CreditCard className="w-4 h-4 text-emerald-600" />
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Fee &amp; DD Payments
                  </h3>
                </div>
                <span className="text-xs font-bold font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                  {data.payments.total_transactions} Transactions
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 bg-emerald-50 rounded-xl">
                  <span className="text-emerald-700 text-[10px] uppercase font-bold">Verified</span>
                  <p className="font-bold text-emerald-900 text-sm mt-0.5">{data.payments.verified}</p>
                </div>
                <div className="p-2.5 bg-blue-50 rounded-xl">
                  <span className="text-blue-700 text-[10px] uppercase font-bold">Under Review</span>
                  <p className="font-bold text-blue-900 text-sm mt-0.5">{data.payments.submitted}</p>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-xl col-span-2 flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Total Verified Amount:</span>
                  <span className="font-mono font-bold text-emerald-700">
                    ₹{Number(data.payments.total_verified_amount).toLocaleString('en-IN')}
                  </span>
                </div>
              </div>
            </div>

            {/* 5. ERP Integration */}
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <div className="flex items-center space-x-2">
                  <Server className="w-4 h-4 text-purple-600" />
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    ERP Staging
                  </h3>
                </div>
                <span className="text-xs font-bold font-mono text-purple-700 bg-purple-50 px-2 py-0.5 rounded">
                  {data.erp.total_records} Records
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 bg-emerald-50 rounded-xl">
                  <span className="text-emerald-700 text-[10px] uppercase font-bold">Synced</span>
                  <p className="font-bold text-emerald-900 text-sm mt-0.5">{data.erp.synced}</p>
                </div>
                <div className="p-2.5 bg-purple-50 rounded-xl">
                  <span className="text-purple-700 text-[10px] uppercase font-bold">Staged</span>
                  <p className="font-bold text-purple-900 text-sm mt-0.5">{data.erp.staged}</p>
                </div>
                <div className="p-2.5 bg-rose-50 rounded-xl col-span-2">
                  <span className="text-rose-700 text-[10px] uppercase font-bold">Sync Failed</span>
                  <p className="font-bold text-rose-900 text-sm mt-0.5">{data.erp.sync_failed}</p>
                </div>
              </div>
            </div>

            {/* 6. Notifications */}
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <div className="flex items-center space-x-2">
                  <Bell className="w-4 h-4 text-cyan-600" />
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Notifications
                  </h3>
                </div>
                <span className="text-xs font-bold font-mono text-cyan-700 bg-cyan-50 px-2 py-0.5 rounded">
                  {data.notifications.total_dispatched} Dispatched
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 bg-slate-50 rounded-xl">
                  <span className="text-slate-400 text-[10px] uppercase font-bold">Unread</span>
                  <p className="font-bold text-slate-900 text-sm mt-0.5">{data.notifications.unread}</p>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-xl">
                  <span className="text-slate-400 text-[10px] uppercase font-bold">Mock Channels</span>
                  <p className="font-bold text-slate-900 text-xs mt-0.5 font-mono">IN_APP, EMAIL, SMS</p>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-xl col-span-2">
                  <span className="text-slate-400 text-[10px] uppercase font-bold">Failed Deliveries</span>
                  <p className="font-bold text-slate-700 text-sm mt-0.5">{data.notifications.failed}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Average Processing Times (With Explicit Start & End Markers) */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <Clock className="w-4 h-4 text-indigo-600" />
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                  Stage Processing Durations
                </h3>
              </div>
              <span className="text-[10px] font-mono text-slate-400">
                Calculated strictly between defined domain timestamps
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/80 space-y-1">
                <span className="text-slate-500 font-semibold block">Application Scrutiny</span>
                <p className="text-lg font-bold text-slate-900 font-mono">
                  {data.processing_times_hours.avg_application_review_hours !== null && data.processing_times_hours.avg_application_review_hours !== undefined
                    ? `${data.processing_times_hours.avg_application_review_hours.toFixed(1)} hrs`
                    : 'No data available'}
                </p>
                <p className="text-[10px] text-slate-400 font-mono">submitted_at &rarr; review_completed_at</p>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/80 space-y-1">
                <span className="text-slate-500 font-semibold block">Physical Verification</span>
                <p className="text-lg font-bold text-slate-900 font-mono">
                  {data.processing_times_hours.avg_physical_verification_hours !== null && data.processing_times_hours.avg_physical_verification_hours !== undefined
                    ? `${data.processing_times_hours.avg_physical_verification_hours.toFixed(1)} hrs`
                    : 'No data available'}
                </p>
                <p className="text-[10px] text-slate-400 font-mono">session_started_at &rarr; completed_at</p>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/80 space-y-1">
                <span className="text-slate-500 font-semibold block">Payment Settlement</span>
                <p className="text-lg font-bold text-slate-900 font-mono">
                  {data.processing_times_hours.avg_payment_verification_hours !== null && data.processing_times_hours.avg_payment_verification_hours !== undefined
                    ? `${data.processing_times_hours.avg_payment_verification_hours.toFixed(1)} hrs`
                    : 'No data available'}
                </p>
                <p className="text-[10px] text-slate-400 font-mono">payment_submitted_at &rarr; verified_at</p>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/80 space-y-1">
                <span className="text-slate-500 font-semibold block">ERP Synchronization</span>
                <p className="text-lg font-bold text-purple-700 font-mono">
                  {data.processing_times_hours.avg_erp_sync_seconds !== null && data.processing_times_hours.avg_erp_sync_seconds !== undefined
                    ? `${data.processing_times_hours.avg_erp_sync_seconds.toFixed(2)} sec`
                    : 'No data available'}
                </p>
                <p className="text-[10px] text-slate-400 font-mono">sync_started_at &rarr; synced_at</p>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
