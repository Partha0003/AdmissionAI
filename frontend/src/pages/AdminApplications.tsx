import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Filter,
  Eye,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { applicationService } from '../services/application';
import { AdminApplicationListItem } from '../types';

export const AdminApplications: React.FC = () => {
  const navigate = useNavigate();
  const [applications, setApplications] = useState<AdminApplicationListItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const fetchApplications = async () => {
    try {
      setLoading(true);
      const data = await applicationService.listAdminApplications({
        status: statusFilter !== 'ALL' ? statusFilter : undefined,
        search: searchTerm || undefined,
      });
      setApplications(data);
    } catch (err) {
      console.error('Failed to load applications', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, [statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchApplications();
  };

  return (
    <div className="space-y-6 pb-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-200/80">
        <div>
          <span className="px-3 py-1 bg-indigo-50 text-indigo-700 font-semibold text-xs rounded-full border border-indigo-100 uppercase tracking-wider">
            Admission Scrutiny Desk
          </span>
          <h1 className="text-2xl font-bold text-slate-900 mt-2">
            Student Admission Applications
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Review digital applications, verified documents, cutoff validations, and candidate declarations.
          </p>
        </div>

        <button
          onClick={fetchApplications}
          className="px-4 py-2 bg-slate-100 text-slate-700 hover:bg-slate-200 font-bold text-xs rounded-xl flex items-center space-x-2 transition self-start md:self-center"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Records</span>
        </button>
      </div>

      {/* Filters & Search */}
      <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 flex flex-col md:flex-row items-center justify-between gap-4">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-96">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search by Name, TNEA No, App No..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
          />
        </form>

        <div className="flex items-center space-x-2 w-full md:w-auto overflow-x-auto">
          <Filter className="w-4 h-4 text-slate-400" />
          {['ALL', 'APPLICATION_SUBMITTED', 'APPLICATION_IN_PROGRESS', 'ACTIVATED', 'DOCUMENT_REVIEW'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition ${
                statusFilter === st
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {st.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Applications Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 overflow-hidden">
        {loading ? (
          <div className="p-12 flex justify-center">
            <RefreshCw className="w-8 h-8 animate-spin text-indigo-600" />
          </div>
        ) : applications.length === 0 ? (
          <div className="p-12 text-center text-slate-500 space-y-2">
            <AlertCircle className="w-8 h-8 mx-auto text-slate-400" />
            <p className="font-semibold">No applications found matching the criteria.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-3.5 px-4">Application No</th>
                  <th className="py-3.5 px-4">Candidate Details</th>
                  <th className="py-3.5 px-4">Branch Allotted</th>
                  <th className="py-3.5 px-4">Quota / Category</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4">Progress</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {applications.map((app) => (
                  <tr key={app.application_id} className="hover:bg-slate-50/80 transition">
                    <td className="py-4 px-4 font-mono font-bold text-indigo-700">
                      {app.application_number || 'PENDING'}
                    </td>
                    <td className="py-4 px-4">
                      <p className="font-bold text-slate-900">{app.student_name}</p>
                      <p className="text-xs font-mono text-slate-500">{app.tnea_application_number}</p>
                    </td>
                    <td className="py-4 px-4 font-medium text-slate-800">
                      {app.allotted_branch}
                    </td>
                    <td className="py-4 px-4 text-xs font-semibold text-slate-600">
                      {app.quota || 'General'} ({app.community || 'OC'})
                    </td>
                    <td className="py-4 px-4">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                        app.status === 'APPLICATION_SUBMITTED'
                          ? 'bg-emerald-100 text-emerald-800'
                          : app.status === 'APPLICATION_IN_PROGRESS'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-indigo-100 text-indigo-800'
                      }`}>
                        {app.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      <div className="flex items-center space-x-2">
                        <div className="w-16 bg-slate-100 rounded-full h-2 overflow-hidden">
                          <div
                            className="bg-indigo-600 h-2 rounded-full"
                            style={{ width: `${app.completion_percentage}%` }}
                          />
                        </div>
                        <span className="text-xs font-bold text-slate-700">{app.completion_percentage}%</span>
                      </div>
                    </td>
                    <td className="py-4 px-4 text-right">
                      <button
                        onClick={() => navigate(`/admin/applications/${app.application_id}`)}
                        className="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold text-xs rounded-lg inline-flex items-center space-x-1 transition"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Scrutinize</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
