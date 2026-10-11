import React, { useState, useEffect } from 'react';
import { Search, RefreshCw, FileText } from 'lucide-react';
import { tneaService } from '../services/tnea';
import { StatusBadge } from '../components/StatusBadge';
import { institutionConfig } from '../config/institution';
import { TNEAAllotment, AdmissionLifecycleState } from '../types';

export const AdminAllotments: React.FC = () => {
  const [allotments, setAllotments] = useState<TNEAAllotment[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedBranch, setSelectedBranch] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');

  const branches = [
    'Computer Science and Engineering',
    'Electronics and Communication Engineering',
    'Information Technology',
    'Artificial Intelligence and Data Science',
    'Electrical and Electronics Engineering',
    'Mechanical Engineering',
  ];

  const statuses = [
    'ALLOTTED',
    'ACTIVATION_PENDING',
    'ACTIVATED',
    'APPLICATION_IN_PROGRESS',
    'APPLICATION_SUBMITTED',
    'DOCUMENT_REVIEW',
    'DOCUMENTS_VERIFIED',
    'ADMISSION_CONFIRMED',
  ];

  useEffect(() => {
    loadAllotments();
  }, [selectedBranch, selectedStatus]);

  const loadAllotments = async () => {
    setLoading(true);
    try {
      const data = await tneaService.getAllotments({
        branch: selectedBranch || undefined,
        status: selectedStatus || undefined,
        search: search || undefined,
      });
      setAllotments(data);
    } catch (e) {
      console.error('Failed to load allotments', e);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadAllotments();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">TNEA Allotments Registry</h1>
          <p className="text-xs text-slate-500 mt-1">
            Master list of synthetic and ingested counselling candidates for {institutionConfig.name} ({institutionConfig.academicYear})
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={loadAllotments}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-white border border-slate-200 text-slate-700 text-xs font-semibold hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-blue-600' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3">
        <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by candidate name, TNEA app no, or allotment order..."
              className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-blue-600 bg-white"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            <select
              value={selectedBranch}
              onChange={(e) => setSelectedBranch(e.target.value)}
              className="text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 bg-white text-slate-700"
            >
              <option value="">All Branches</option>
              {branches.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>

            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 bg-white text-slate-700"
            >
              <option value="">All Lifecycle States</option>
              {statuses.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>

            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
            >
              Filter
            </button>
          </div>
        </form>
      </div>

      {/* Allotments Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-500">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-blue-600 mb-2" />
            <p className="text-xs">Loading candidate allotment records...</p>
          </div>
        ) : allotments.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <FileText className="w-8 h-8 mx-auto text-slate-300 mb-2" />
            <p className="text-sm font-semibold text-slate-600">No Allotment Records Found</p>
            <p className="text-xs mt-1">Try clearing your filters or import new allotments via the TNEA Mock Import tool.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold">
                <tr>
                  <th className="px-4 py-3 text-left">TNEA App No</th>
                  <th className="px-4 py-3 text-left">Candidate Name</th>
                  <th className="px-4 py-3 text-left">Allotment No</th>
                  <th className="px-4 py-3 text-left">Allotted Branch</th>
                  <th className="px-4 py-3 text-left">Category / Quota</th>
                  <th className="px-4 py-3 text-left">Cutoff Mark</th>
                  <th className="px-4 py-3 text-left">Joining Deadline</th>
                  <th className="px-4 py-3 text-left">Admission Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {allotments.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-4 py-3 font-mono font-bold text-blue-700">{a.tnea_application_number}</td>
                    <td className="px-4 py-3 font-semibold text-slate-800">{a.student_name || 'Pending Onboarding'}</td>
                    <td className="px-4 py-3 font-mono text-slate-500 text-[11px]">{a.allotment_number}</td>
                    <td className="px-4 py-3 text-slate-700">{a.branch_name}</td>
                    <td className="px-4 py-3 text-slate-600">
                      <span className="font-semibold">{a.community || 'N/A'}</span> &bull; {a.quota || 'General'}
                    </td>
                    <td className="px-4 py-3 font-mono font-semibold text-slate-700">
                      {a.cutoff_mark !== null && a.cutoff_mark !== undefined ? a.cutoff_mark.toFixed(2) : '-'}
                    </td>
                    <td className="px-4 py-3 text-slate-500 font-mono text-[11px]">{a.joining_deadline}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={(a.admission_status || 'ALLOTTED') as AdmissionLifecycleState} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="p-4 bg-slate-50 border-t border-slate-200 text-xs text-slate-500 flex justify-between items-center">
          <span>Showing {allotments.length} candidate allotments</span>
          <span className="font-mono text-[11px]">Academic Year: {institutionConfig.academicYear}</span>
        </div>
      </div>
    </div>
  );
};
