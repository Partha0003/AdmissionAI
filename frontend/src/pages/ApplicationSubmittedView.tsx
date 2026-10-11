import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  Download,
  Eye,
  User,
  GraduationCap,
  MapPin,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { applicationService } from '../services/application';
import { documentService } from '../services/document';
import { ApplicationDetail } from '../types';

export const ApplicationSubmittedView: React.FC = () => {
  const [appData, setAppData] = useState<ApplicationDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const fetchApp = async () => {
      try {
        setLoading(true);
        const data = await applicationService.getMyApplication();
        setAppData(data);
      } catch (err: any) {
        setErrorMsg(err.response?.data?.detail || 'Failed to load submitted application.');
      } finally {
        setLoading(false);
      }
    };
    fetchApp();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (errorMsg || !appData) {
    return (
      <div className="p-8 text-center text-rose-600 space-y-2">
        <AlertCircle className="w-8 h-8 mx-auto" />
        <p>{errorMsg || 'No application found.'}</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-16">
      {/* Submission Success Hero */}
      <div className="bg-gradient-to-r from-emerald-600 to-teal-700 rounded-3xl text-white p-8 shadow-md">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center space-x-2 bg-emerald-500/30 px-3 py-1 rounded-full text-xs font-semibold tracking-wide uppercase">
              <CheckCircle2 className="w-4 h-4 text-emerald-200" />
              <span>Application Submitted Successfully</span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight">
              Application Dossier: {appData.application_number}
            </h1>
            <p className="text-emerald-100 text-sm max-w-2xl">
              Submitted on {appData.submitted_at ? new Date(appData.submitted_at).toLocaleString() : 'N/A'}.
              Your application is locked and currently queued in the <strong>{appData.status}</strong> workflow.
            </p>
          </div>

          <button
            onClick={() => window.print()}
            className="px-5 py-2.5 bg-white text-emerald-800 hover:bg-emerald-50 font-bold text-xs rounded-xl shadow-sm flex items-center space-x-2 transition flex-shrink-0"
          >
            <Download className="w-4 h-4" />
            <span>Print Application Summary</span>
          </button>
        </div>
      </div>

      {/* Snapshot Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Candidate & Allotment */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 space-y-4">
          <div className="flex items-center space-x-2 text-indigo-700 font-bold text-xs uppercase tracking-wider">
            <User className="w-4 h-4" />
            <span>Candidate Info</span>
          </div>
          <div className="space-y-2 text-sm">
            <div>
              <p className="text-xs text-slate-400">Full Name</p>
              <p className="font-bold text-slate-900">{appData.student_name}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400">TNEA App No / Quota</p>
              <p className="font-medium text-slate-800">{appData.tnea_application_number} ({appData.quota || 'General'})</p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Allotted Branch</p>
              <p className="font-bold text-indigo-950">{appData.allotted_branch_name || appData.allotted_branch}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Community / Caste</p>
              <p className="font-medium text-slate-800">{appData.caste || appData.community} ({appData.religion || 'Hindu'})</p>
            </div>
          </div>
        </div>

        {/* Academic Summary */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 space-y-4">
          <div className="flex items-center space-x-2 text-indigo-700 font-bold text-xs uppercase tracking-wider">
            <GraduationCap className="w-4 h-4" />
            <span>Academic Performance</span>
          </div>
          <div className="space-y-2 text-sm">
            <div>
              <p className="text-xs text-slate-400">Engineering Cutoff Score</p>
              <p className="text-2xl font-black text-indigo-600 font-mono">{appData.twelfth_cutoff_marks || 'N/A'}</p>
            </div>
            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100 text-center">
              <div className="p-2 bg-slate-50 rounded-lg">
                <p className="text-[10px] text-slate-500 font-bold">Maths</p>
                <p className="text-xs font-bold text-slate-800">{appData.twelfth_maths_marks || '-'}</p>
              </div>
              <div className="p-2 bg-slate-50 rounded-lg">
                <p className="text-[10px] text-slate-500 font-bold">Physics</p>
                <p className="text-xs font-bold text-slate-800">{appData.twelfth_physics_marks || '-'}</p>
              </div>
              <div className="p-2 bg-slate-50 rounded-lg">
                <p className="text-[10px] text-slate-500 font-bold">Chemistry</p>
                <p className="text-xs font-bold text-slate-800">{appData.twelfth_chemistry_marks || '-'}</p>
              </div>
            </div>
            <div>
              <p className="text-xs text-slate-400">12th Total / Reg No</p>
              <p className="text-xs font-medium text-slate-800">{appData.twelfth_total_marks}/{appData.twelfth_max_marks} ({appData.twelfth_registration_number})</p>
            </div>
          </div>
        </div>

        {/* Contact & Family */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 space-y-4">
          <div className="flex items-center space-x-2 text-indigo-700 font-bold text-xs uppercase tracking-wider">
            <MapPin className="w-4 h-4" />
            <span>Contact & Domicile</span>
          </div>
          <div className="space-y-2 text-sm">
            <div>
              <p className="text-xs text-slate-400">Address</p>
              <p className="font-medium text-slate-800">{appData.address_line1}</p>
              <p className="text-xs text-slate-600">{appData.city}, {appData.district} - {appData.pincode}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Parent / Guardian</p>
              <p className="font-medium text-slate-800">{appData.father_name || appData.mother_name || appData.guardian_name}</p>
              <p className="text-xs text-slate-600">Mobile: {appData.father_mobile || appData.student_mobile}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Annual Family Income</p>
              <p className="font-bold text-slate-900">₹{appData.annual_family_income?.toLocaleString() || 'N/A'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Uploaded Documents Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 space-y-4">
        <h2 className="text-base font-bold text-slate-900">Submitted Verification Certificates</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider font-semibold border-y border-slate-200">
              <tr>
                <th className="py-3 px-4">Certificate Name</th>
                <th className="py-3 px-4">Requirement</th>
                <th className="py-3 px-4">Filename</th>
                <th className="py-3 px-4">Version</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {appData.checklist.map((doc) => (
                <tr key={doc.code} className="hover:bg-slate-50/60">
                  <td className="py-3 px-4 font-semibold text-slate-900">{doc.name}</td>
                  <td className="py-3 px-4">
                    {doc.is_mandatory ? (
                      <span className="px-2 py-0.5 bg-rose-50 text-rose-700 text-xs font-bold rounded-full border border-rose-100">
                        Mandatory
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs font-medium rounded-full">
                        Optional
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 font-mono text-xs text-slate-600">
                    {doc.original_filename || 'Not Uploaded'}
                  </td>
                  <td className="py-3 px-4 font-mono text-xs font-bold text-indigo-700">
                    {doc.active_version ? `v${doc.active_version}` : '-'}
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-2.5 py-1 bg-emerald-50 text-emerald-700 font-bold text-xs rounded-full border border-emerald-200">
                      {doc.document_status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    {doc.document_id && (
                      <a
                        href={documentService.getDocumentDownloadUrl(doc.document_id)}
                        target="_blank"
                        rel="noreferrer"
                        className="px-3 py-1 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded-lg text-xs font-bold inline-flex items-center space-x-1"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>View</span>
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
