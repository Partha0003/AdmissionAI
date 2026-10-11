import React, { useState, useEffect } from 'react';
import { 
  UploadCloud, 
  CheckCircle2, 
  XCircle, 
  Copy, 
  Check, 
  RefreshCw, 
  Sparkles, 
  Layers,
  ShieldAlert
} from 'lucide-react';
import { tneaService } from '../services/tnea';
import { institutionConfig } from '../config/institution';
import { TNEAImportResponse, TNEAImportBatch } from '../types';

const PRESET_ALLOTMENTS_VALID = [
  {
    "tnea_application_number": "XYZ2026101",
    "allotment_number": "XYZALT2026101",
    "student_name": "Suresh Raina K",
    "date_of_birth": "2008-04-12",
    "email": "suresh.xyz2026101@demo.admissionai.local",
    "mobile": "9840112345",
    "college_code": "XYZ",
    "college_name": "XYZ Engineering College",
    "branch_code": "CSE",
    "branch_name": "Computer Science and Engineering",
    "community": "BC",
    "quota": "GOVERNMENT",
    "cutoff_mark": 194.50,
    "allotment_date": "2026-08-10",
    "joining_deadline": "2026-08-25",
    "allotment_status": "ALLOTTED"
  },
  {
    "tnea_application_number": "XYZ2026102",
    "allotment_number": "XYZALT2026102",
    "student_name": "Kavitha Sundaram",
    "date_of_birth": "2008-09-22",
    "email": "kavitha.xyz2026102@demo.admissionai.local",
    "mobile": "9840223456",
    "college_code": "XYZ",
    "college_name": "XYZ Engineering College",
    "branch_code": "ECE",
    "branch_name": "Electronics and Communication Engineering",
    "community": "MBC",
    "quota": "GOVERNMENT",
    "cutoff_mark": 189.75,
    "allotment_date": "2026-08-10",
    "joining_deadline": "2026-08-25",
    "allotment_status": "ALLOTTED"
  },
  {
    "tnea_application_number": "XYZ2026103",
    "allotment_number": "XYZALT2026103",
    "student_name": "Arjun Venkatesh",
    "date_of_birth": "2008-01-15",
    "email": "arjun.xyz2026103@demo.admissionai.local",
    "mobile": "9840334567",
    "college_code": "XYZ",
    "college_name": "XYZ Engineering College",
    "branch_code": "IT",
    "branch_name": "Information Technology",
    "community": "OC",
    "quota": "GOVERNMENT",
    "cutoff_mark": 191.00,
    "allotment_date": "2026-08-10",
    "joining_deadline": "2026-08-25",
    "allotment_status": "ALLOTTED"
  },
  {
    "tnea_application_number": "XYZ2026104",
    "allotment_number": "XYZALT2026104",
    "student_name": "Sneha Priya M",
    "date_of_birth": "2008-11-05",
    "email": "sneha.xyz2026104@demo.admissionai.local",
    "mobile": "9840445678",
    "college_code": "XYZ",
    "college_name": "XYZ Engineering College",
    "branch_code": "ADS",
    "branch_name": "Artificial Intelligence and Data Science",
    "community": "BC",
    "quota": "MANAGEMENT",
    "cutoff_mark": 186.25,
    "allotment_date": "2026-08-10",
    "joining_deadline": "2026-08-25",
    "allotment_status": "ALLOTTED"
  },
  {
    "tnea_application_number": "XYZ2026105",
    "allotment_number": "XYZALT2026105",
    "student_name": "Vijay Shankar R",
    "date_of_birth": "2008-06-30",
    "email": "vijay.xyz2026105@demo.admissionai.local",
    "mobile": "9840556789",
    "college_code": "XYZ",
    "college_name": "XYZ Engineering College",
    "branch_code": "EEE",
    "branch_name": "Electrical and Electronics Engineering",
    "community": "SC",
    "quota": "GOVERNMENT",
    "cutoff_mark": 178.50,
    "allotment_date": "2026-08-10",
    "joining_deadline": "2026-08-25",
    "allotment_status": "ALLOTTED"
  }
];

export const AdminTNEAImport: React.FC = () => {
  const [jsonText, setJsonText] = useState(JSON.stringify(PRESET_ALLOTMENTS_VALID, null, 2));
  const [batchName, setBatchName] = useState('TNEA_ROUND_1_ALLOTMENT_DEMO');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<TNEAImportResponse | null>(null);
  const [copiedToken, setCopiedToken] = useState<string | null>(null);
  const [batches, setBatches] = useState<TNEAImportBatch[]>([]);

  useEffect(() => {
    loadBatches();
  }, []);

  const loadBatches = async () => {
    try {
      const data = await tneaService.getImportBatches();
      setBatches(data);
    } catch (e) {
      console.error('Failed to load import batches', e);
    }
  };

  const handleImport = async () => {
    setError(null);
    setImportResult(null);

    let parsedRecords: any[];
    try {
      parsedRecords = JSON.parse(jsonText);
      if (!Array.isArray(parsedRecords)) {
        throw new Error('Input must be a JSON array of allotment objects.');
      }
    } catch (e: any) {
      setError(`Invalid JSON format: ${e.message}`);
      return;
    }

    setLoading(true);
    try {
      const result = await tneaService.importAllotments({
        source: 'MOCK_TNEA_ADAPTER',
        filename_or_reference: batchName || 'synthetic_allotments.json',
        records: parsedRecords,
      });
      setImportResult(result);
      loadBatches();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Import failed. Please verify the records.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedToken(text);
    setTimeout(() => setCopiedToken(null), 2500);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setBatchName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const content = event.target?.result as string;
        setJsonText(content);
      } catch (err) {
        setError('Failed to read file content.');
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-blue-900 to-indigo-900 text-white rounded-2xl p-6 shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center space-x-2 bg-blue-800/80 px-2.5 py-1 rounded-md text-xs font-semibold uppercase tracking-wider text-blue-200 mb-2 border border-blue-700">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>Phase 2 Simulation Engine</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight">TNEA Mock Allotment Ingestion</h1>
            <p className="text-sm text-blue-200 mt-1">
              Ingest simulated Tamil Nadu Engineering Admissions (TNEA) counselling allotments for {institutionConfig.name} ({institutionConfig.code}) &bull; {institutionConfig.academicYear}
            </p>
          </div>

          <div className="bg-white/10 backdrop-blur-md rounded-xl p-3 border border-white/20 text-xs space-y-1">
            <div className="text-blue-200">Target Institution: <span className="text-white font-semibold">{institutionConfig.name}</span></div>
            <div className="text-blue-200">Institution Code: <span className="font-mono text-amber-300 font-bold">{institutionConfig.code}</span></div>
            <div className="text-blue-200">Mode: <span className="text-emerald-300 font-semibold">MockTNEAAdapter</span></div>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start space-x-3 text-rose-800 text-sm">
          <XCircle className="w-5 h-5 mt-0.5 text-rose-600 flex-shrink-0" />
          <div>
            <p className="font-semibold">Import Error</p>
            <p className="text-xs text-rose-700 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Ingestion Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Input Editor */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">Synthetic Allotment Records</h2>
              <p className="text-xs text-slate-500">Provide JSON allotment records matching the TNEA schema</p>
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => setJsonText(JSON.stringify(PRESET_ALLOTMENTS_VALID, null, 2))}
                className="px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 text-xs font-semibold border border-blue-200 transition-colors"
              >
                Reset 5 Demo Allotments
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Batch Reference Name
              </label>
              <input
                type="text"
                value={batchName}
                onChange={(e) => setBatchName(e.target.value)}
                placeholder="e.g. TNEA_ROUND_1"
                className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-blue-600 bg-white"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Upload Custom JSON/CSV File
              </label>
              <input
                type="file"
                accept=".json,.csv"
                onChange={handleFileUpload}
                className="w-full text-xs file:mr-2 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 cursor-pointer"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              JSON Records Payload
            </label>
            <textarea
              rows={12}
              value={jsonText}
              onChange={(e) => setJsonText(e.target.value)}
              className="w-full font-mono text-xs p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-blue-600 bg-slate-900 text-emerald-400"
            />
          </div>

          <div className="pt-2 flex justify-end">
            <button
              type="button"
              disabled={loading}
              onClick={handleImport}
              className="flex items-center space-x-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold shadow-md shadow-blue-500/20 disabled:opacity-50 transition-all"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Processing Ingestion &amp; Generating Tokens...</span>
                </>
              ) : (
                <>
                  <UploadCloud className="w-4 h-4" />
                  <span>Import Allotments</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right: Validation & Adapter Rules */}
        <div className="space-y-5">
          <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 text-xs space-y-3">
            <h3 className="font-bold text-slate-800 text-sm flex items-center space-x-2">
              <Layers className="w-4 h-4 text-blue-600" />
              <span>Deterministic Ingestion Rules</span>
            </h3>
            <ul className="space-y-2 text-slate-600">
              <li className="flex items-start space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                <span><strong>College Code Assertion:</strong> Only allotments where <code className="bg-white px-1 py-0.5 rounded border border-slate-200">college_code == "XYZ"</code> are created.</span>
              </li>
              <li className="flex items-start space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                <span><strong>Idempotency:</strong> Re-importing existing application numbers updates/skips duplicates safely without duplicate records.</span>
              </li>
              <li className="flex items-start space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                <span><strong>Initial State:</strong> Newly created candidates are assigned <code className="bg-white px-1 py-0.5 rounded border border-slate-200 text-blue-600 font-bold">ACTIVATION_PENDING</code>.</span>
              </li>
              <li className="flex items-start space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                <span><strong>Token Security:</strong> Cryptographically generated single-use tokens are hashed (SHA-256) before storing.</span>
              </li>
            </ul>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 text-xs text-amber-900 space-y-2">
            <div className="flex items-center space-x-2 font-bold text-amber-950">
              <ShieldAlert className="w-4 h-4 text-amber-600" />
              <span>Real-World Boundary Notice</span>
            </div>
            <p className="leading-relaxed text-[11px] text-amber-800">
              This ingestion workflow simulates the college-side receipt of TNEA allotments. It does not connect to live TNEA servers or scrape public portals.
            </p>
          </div>
        </div>
      </div>

      {/* Import Result Dashboard */}
      {importResult && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-100 pb-4">
            <div>
              <div className="inline-flex items-center space-x-2 bg-emerald-50 text-emerald-700 px-2.5 py-0.5 rounded-full text-xs font-semibold mb-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Batch {importResult.status}</span>
              </div>
              <h2 className="text-lg font-bold text-slate-900">Import Batch Summary</h2>
              <p className="text-xs text-slate-500 font-mono">Batch ID: {importResult.batch_id}</p>
            </div>

            <div className="flex items-center space-x-2">
              <span className="text-xs text-slate-500">Dispatched Mock Notifications:</span>
              <span className="text-xs font-bold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-md border border-blue-200">
                {importResult.dispatched_notifications_count} Delivered
              </span>
            </div>
          </div>

          {/* Metric Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-center">
              <p className="text-xs font-medium text-slate-500">Total Processed</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{importResult.total_records}</p>
            </div>
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-center">
              <p className="text-xs font-medium text-emerald-700">Successful / Created</p>
              <p className="text-2xl font-bold text-emerald-800 mt-1">{importResult.successful_records}</p>
            </div>
            <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 text-center">
              <p className="text-xs font-medium text-blue-700">Duplicates Handled</p>
              <p className="text-2xl font-bold text-blue-800 mt-1">{importResult.duplicate_records}</p>
            </div>
            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-center">
              <p className="text-xs font-medium text-amber-700">Skipped (Other Inst)</p>
              <p className="text-2xl font-bold text-amber-800 mt-1">{importResult.skipped_records}</p>
            </div>
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-center">
              <p className="text-xs font-medium text-rose-700">Failed / Invalid</p>
              <p className="text-2xl font-bold text-rose-800 mt-1">{importResult.failed_records}</p>
            </div>
          </div>

          {/* Record Breakdown Table with Activation Tokens */}
          <div>
            <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center justify-between">
              <span>Processed Candidate Allotments &amp; Activation Tokens</span>
              <span className="text-[11px] font-normal text-slate-500">
                (Tokens visible in Admin/Demo console for testing onboarding)
              </span>
            </h3>

            <div className="overflow-x-auto border border-slate-200 rounded-xl">
              <table className="min-w-full divide-y divide-slate-200 text-xs">
                <thead className="bg-slate-50 text-slate-600 font-semibold">
                  <tr>
                    <th className="px-4 py-3 text-left">TNEA App No</th>
                    <th className="px-4 py-3 text-left">Student Name</th>
                    <th className="px-4 py-3 text-left">Allotted Branch</th>
                    <th className="px-4 py-3 text-left">Allotment No</th>
                    <th className="px-4 py-3 text-left">Result Status</th>
                    <th className="px-4 py-3 text-left">Activation Token (Demo Copy)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {importResult.results.map((r, idx) => {
                    const isSuccess = r.status === 'CREATED';
                    const isDuplicate = r.status === 'SKIPPED_DUPLICATE' || r.status === 'EXISTING_UPDATED';
                    return (
                      <tr key={idx} className="hover:bg-slate-50/80">
                        <td className="px-4 py-3 font-mono font-semibold text-slate-900">{r.tnea_application_number}</td>
                        <td className="px-4 py-3 font-medium text-slate-800">{r.student_name}</td>
                        <td className="px-4 py-3 text-slate-600">{r.branch_name}</td>
                        <td className="px-4 py-3 font-mono text-slate-500">{r.allotment_number}</td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold ${
                              isSuccess
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : isDuplicate
                                ? 'bg-blue-50 text-blue-700 border border-blue-200'
                                : 'bg-rose-50 text-rose-700 border border-rose-200'
                            }`}
                          >
                            {r.status}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {r.raw_activation_token ? (
                            <div className="flex items-center space-x-2">
                              <code className="bg-slate-100 text-slate-800 px-2 py-1 rounded text-[11px] font-mono border border-slate-200 max-w-[220px] truncate">
                                {r.raw_activation_token}
                              </code>
                              <button
                                type="button"
                                onClick={() => handleCopy(r.raw_activation_token!)}
                                className="p-1 rounded bg-white hover:bg-slate-100 border border-slate-200 text-slate-600 transition-colors"
                                title="Copy Token"
                              >
                                {copiedToken === r.raw_activation_token ? (
                                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                                ) : (
                                  <Copy className="w-3.5 h-3.5" />
                                )}
                              </button>
                            </div>
                          ) : (
                            <span className="text-slate-400 italic text-[11px]">N/A</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Batch Audit Log */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
        <h2 className="text-base font-bold text-slate-900">Historical Ingestion Batches</h2>
        {batches.length === 0 ? (
          <p className="text-xs text-slate-400 italic">No batches imported yet.</p>
        ) : (
          <div className="overflow-x-auto border border-slate-200 rounded-xl">
            <table className="min-w-full divide-y divide-slate-200 text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold">
                <tr>
                  <th className="px-4 py-3 text-left">Batch ID / Reference</th>
                  <th className="px-4 py-3 text-left">Source</th>
                  <th className="px-4 py-3 text-left">Records</th>
                  <th className="px-4 py-3 text-left">Created / Success</th>
                  <th className="px-4 py-3 text-left">Imported By</th>
                  <th className="px-4 py-3 text-left">Timestamp</th>
                  <th className="px-4 py-3 text-left">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {batches.map((b) => (
                  <tr key={b.id} className="hover:bg-slate-50/80">
                    <td className="px-4 py-3 font-mono font-medium text-slate-900">
                      {b.filename_or_reference || b.id.substring(0, 8)}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{b.source}</td>
                    <td className="px-4 py-3 font-semibold">{b.record_count}</td>
                    <td className="px-4 py-3 text-emerald-700 font-semibold">{b.successful_count}</td>
                    <td className="px-4 py-3 text-slate-500">{b.imported_by}</td>
                    <td className="px-4 py-3 text-slate-500">{new Date(b.imported_at).toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-[10px] font-semibold uppercase">
                        {b.status}
                      </span>
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
