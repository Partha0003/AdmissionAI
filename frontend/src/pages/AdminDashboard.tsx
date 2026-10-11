import React, { useEffect, useState } from 'react';
import { 
  Users, 
  UserCheck, 
  FileCheck2, 
  Clock, 
  Search, 
  Filter, 
  RefreshCw 
} from 'lucide-react';
import { admissionService } from '../services/admission';
import { AdminDashboardMetrics, AdminStudentItem } from '../types';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';

export const AdminDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<AdminDashboardMetrics | null>(null);
  const [students, setStudents] = useState<AdminStudentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      const [met, stud] = await Promise.all([
        admissionService.getAdminDashboardMetrics(),
        admissionService.getAdminStudents({
          status: statusFilter || undefined,
          search: search || undefined,
        }),
      ]);
      setMetrics(met);
      setStudents(stud);
    } catch (err) {
      console.error('Failed to load admin data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadData();
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold bg-purple-100 text-purple-800 px-2.5 py-0.5 rounded border border-purple-300">
              ADMINISTRATION CONSOLE
            </span>
            <span className="text-xs text-slate-400 font-mono">XYZ-2026-27</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight mt-1.5">
            Admission Scrutiny & Overview
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time candidate telemetry across all admission lifecycle stages
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center space-x-2 px-3.5 py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold border border-slate-200 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-blue-600' : ''}`} />
          <span>Refresh Metrics</span>
        </button>
      </div>

      {/* Metric Cards Grid */}
      {metrics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Total Allotted"
            value={metrics.total_allotted}
            subtitle="Imported via Mock TNEA"
            color="blue"
            icon={<Users className="w-5 h-5" />}
          />
          <MetricCard
            title="Activated Portals"
            value={metrics.activated}
            subtitle="Candidate credentials verified"
            color="indigo"
            icon={<UserCheck className="w-5 h-5" />}
          />
          <MetricCard
            title="In Progress"
            value={metrics.applications_in_progress}
            subtitle="Filling digital application"
            color="amber"
            icon={<Clock className="w-5 h-5" />}
          />
          <MetricCard
            title="Submitted"
            value={metrics.applications_submitted}
            subtitle="Ready for document scrutiny"
            color="emerald"
            icon={<FileCheck2 className="w-5 h-5" />}
          />
        </div>
      )}

      {/* Candidate Table Section */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div>
            <h3 className="text-base font-bold text-slate-900">Registered Candidates</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Live records queried directly from the PostgreSQL relational database
            </p>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3">
            <form onSubmit={handleSearchSubmit} className="relative">
              <input
                type="text"
                placeholder="Search candidate..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-600 focus:border-blue-600 w-48"
              />
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            </form>

            <div className="flex items-center space-x-2">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:ring-2 focus:ring-blue-600"
              >
                <option value="">All Lifecycle States</option>
                <option value="ACTIVATION_PENDING">ACTIVATION_PENDING</option>
                <option value="ACTIVATED">ACTIVATED</option>
                <option value="APPLICATION_IN_PROGRESS">APPLICATION_IN_PROGRESS</option>
                <option value="APPLICATION_SUBMITTED">APPLICATION_SUBMITTED</option>
                <option value="DOCUMENT_REVIEW">DOCUMENT_REVIEW</option>
                <option value="DOCUMENTS_VERIFIED">DOCUMENTS_VERIFIED</option>
              </select>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto border border-slate-100 rounded-xl">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">TNEA App No.</th>
                <th className="py-3 px-4">Candidate Name</th>
                <th className="py-3 px-4">Allotted Branch</th>
                <th className="py-3 px-4">Community</th>
                <th className="py-3 px-4">Admission Status</th>
                <th className="py-3 px-4">Form Progress</th>
                <th className="py-3 px-4">Last Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {students.length > 0 ? (
                students.map((st) => (
                  <tr key={st.student_id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3 px-4 font-mono font-semibold text-blue-600">
                      {st.tnea_application_number}
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-800">{st.full_name}</td>
                    <td className="py-3 px-4 text-slate-600">{st.allotted_branch || '-'}</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] font-mono font-bold">
                        {st.community || 'N/A'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={st.status} size="sm" />
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-2">
                        <div className="w-16 bg-slate-200 rounded-full h-1.5 overflow-hidden">
                          <div
                            className="bg-blue-600 h-1.5 rounded-full"
                            style={{ width: `${st.completion_percentage}%` }}
                          ></div>
                        </div>
                        <span className="font-mono text-[10px] text-slate-500 font-medium">
                          {st.completion_percentage}%
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                      {new Date(st.updated_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400 italic">
                    No matching candidate records found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
