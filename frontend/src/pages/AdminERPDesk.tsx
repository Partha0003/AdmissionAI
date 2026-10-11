import React, { useEffect, useState } from 'react';
import { 
  Search, 
  Filter, 
  RefreshCw, 
  Send, 
  RotateCw, 
  FileCode, 
  Eye,
  ShieldAlert,
  Server,
  AlertCircle
} from 'lucide-react';
import { erpService } from '../services/erp';
import { ERPAdmissionRecord, ERPIntegrationEvent } from '../types';

export const AdminERPDesk: React.FC = () => {
  const [records, setRecords] = useState<ERPAdmissionRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedRecord, setSelectedRecord] = useState<ERPAdmissionRecord | null>(null);
  const [events, setEvents] = useState<ERPIntegrationEvent[]>([]);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [simulateFailure, setSimulateFailure] = useState<boolean>(false);
  const [showPayloadModal, setShowPayloadModal] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchRecords = async () => {
    try {
      setLoading(true);
      const res = await erpService.listRecords({
        status: statusFilter === 'ALL' ? undefined : statusFilter,
        search: searchQuery || undefined,
      });
      setRecords(res);
      if (selectedRecord) {
        const found = res.find((r: ERPAdmissionRecord) => r.id === selectedRecord.id);
        if (found) {
          handleSelectRecord(found);
        }
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, [statusFilter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchRecords();
  };

  const handleSelectRecord = async (rec: ERPAdmissionRecord) => {
    setSelectedRecord(rec);
    try {
      const evs = await erpService.getRecordEvents(rec.id);
      setEvents(evs);
    } catch {
      setEvents([]);
    }
  };

  const handleStageRecord = async (appId: string) => {
    try {
      setActionLoading(true);
      setErrorMsg(null);
      const res = await erpService.stageRecord(appId);
      await fetchRecords();
      handleSelectRecord(res);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to stage ERP record');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSyncRecord = async (recId: string) => {
    try {
      setActionLoading(true);
      setErrorMsg(null);
      const res = await erpService.syncRecord(recId, {
        simulate_failure: simulateFailure,
        failure_reason: simulateFailure ? 'Mock ERP adapter timed out' : undefined,
      });
      await fetchRecords();
      handleSelectRecord(res);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to sync ERP record');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRetryRecord = async (recId: string) => {
    try {
      setActionLoading(true);
      setErrorMsg(null);
      const res = await erpService.retrySync(recId, {
        simulate_failure: simulateFailure,
      });
      await fetchRecords();
      handleSelectRecord(res);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to retry sync');
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusBadge = (st: string) => {
    switch (st) {
      case 'SYNCED':
        return <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 font-mono text-[10px] font-bold rounded">SYNCED</span>;
      case 'SYNC_FAILED':
        return <span className="px-2 py-0.5 bg-rose-100 text-rose-800 font-mono text-[10px] font-bold rounded">SYNC FAILED</span>;
      case 'STAGED':
        return <span className="px-2 py-0.5 bg-indigo-100 text-indigo-800 font-mono text-[10px] font-bold rounded">STAGED</span>;
      case 'READY_FOR_STAGING':
        return <span className="px-2 py-0.5 bg-cyan-100 text-cyan-800 font-mono text-[10px] font-bold rounded">READY FOR STAGING</span>;
      case 'NOT_READY':
        return <span className="px-2 py-0.5 bg-amber-100 text-amber-800 font-mono text-[10px] font-bold rounded">NOT READY</span>;
      case 'SYNCING':
        return <span className="px-2 py-0.5 bg-blue-100 text-blue-800 font-mono text-[10px] font-bold rounded animate-pulse">SYNCING</span>;
      default:
        return <span className="px-2 py-0.5 bg-slate-100 text-slate-700 font-mono text-[10px] font-bold rounded">{st}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-purple-950 rounded-2xl p-6 text-white shadow-lg relative overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-[10px] font-mono bg-purple-500/20 text-purple-200 border border-purple-400/30 px-2 py-0.5 rounded font-bold uppercase tracking-wider">
                Phase 7 &bull; Institutional ERP Staging Console
              </span>
              <span className="text-[10px] font-mono bg-amber-500/20 text-amber-300 border border-amber-400/30 px-2 py-0.5 rounded font-bold">
                MOCK ERP &bull; PROTOTYPE / NO REAL ERP CONNECTION
              </span>
            </div>
            <h1 className="text-2xl font-bold mt-2">
              ERP Admission Staging &amp; Integration Queue
            </h1>
            <p className="text-xs text-purple-200 mt-0.5">
              Deterministic payload snapshotting, institutional readiness policy, and mock sync dispatcher.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => fetchRecords()}
              className="p-2 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh Records</span>
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

      {/* Main Grid: Staging Queue (7 cols) + Inspector (5 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Records Queue */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-4">
            {/* Search & Filters */}
            <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
              <form onSubmit={handleSearch} className="relative flex-1 w-full">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search App No / Candidate / Staging Ref..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-purple-500 focus:outline-none"
                />
              </form>

              <div className="flex items-center space-x-2 w-full sm:w-auto">
                <Filter className="w-4 h-4 text-slate-400" />
                <select
                  value={statusFilter}
                  onChange={e => setStatusFilter(e.target.value)}
                  className="px-2.5 py-1.5 border border-slate-300 rounded-xl text-xs bg-white focus:ring-2 focus:ring-purple-500 focus:outline-none"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="NOT_READY">NOT_READY</option>
                  <option value="READY_FOR_STAGING">READY_FOR_STAGING</option>
                  <option value="STAGED">STAGED</option>
                  <option value="SYNCED">SYNCED</option>
                  <option value="SYNC_FAILED">SYNC_FAILED</option>
                </select>
              </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-400 uppercase font-semibold text-[10px] tracking-wider">
                    <th className="py-2.5 px-3">Candidate / App No</th>
                    <th className="py-2.5 px-3">Staging Ref &amp; Ver</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {loading ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-slate-400">
                        <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-1 text-purple-600" />
                        <span>Loading ERP records...</span>
                      </td>
                    </tr>
                  ) : records.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-slate-400 italic">
                        No ERP records found.
                      </td>
                    </tr>
                  ) : (
                    records.map(rec => {
                      const isSelected = selectedRecord?.id === rec.id;
                      return (
                        <tr
                          key={rec.id}
                          onClick={() => handleSelectRecord(rec)}
                          className={`cursor-pointer transition-colors ${
                            isSelected ? 'bg-purple-50/80 font-medium' : 'hover:bg-slate-50'
                          }`}
                        >
                          <td className="py-2.5 px-3">
                            <p className="font-bold text-slate-900">{rec.candidate_name || 'Candidate'}</p>
                            <span className="text-[10px] font-mono text-slate-500">
                              App #{rec.application_number || rec.application_id.slice(0, 8)}
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <p className="font-mono font-bold text-purple-700">{rec.staging_reference}</p>
                            <span className="text-[10px] text-slate-400 font-mono">
                              v{rec.payload_version} &bull; Hash: {rec.payload_hash.slice(0, 8)}...
                            </span>
                          </td>
                          <td className="py-2.5 px-3">{getStatusBadge(rec.status)}</td>
                          <td className="py-2.5 px-3 text-right">
                            <button
                              onClick={e => {
                                e.stopPropagation();
                                handleSelectRecord(rec);
                              }}
                              className="p-1 text-slate-500 hover:text-purple-600 rounded"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right: Record Dossier & Actions (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {selectedRecord ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-5">
              {/* Header */}
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold tracking-wider">
                    ERP Staging Record
                  </span>
                  <h2 className="text-base font-bold text-slate-900 font-mono">
                    {selectedRecord.staging_reference}
                  </h2>
                </div>
                <div>{getStatusBadge(selectedRecord.status)}</div>
              </div>

              {/* Record Snapshot Details */}
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2">
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-slate-400">Candidate:</span>
                    <p className="font-bold text-slate-900">{selectedRecord.candidate_name || '-'}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Allotted Branch:</span>
                    <p className="font-bold text-slate-900">{selectedRecord.allotted_branch || '-'}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Payload Version:</span>
                    <p className="font-mono font-bold text-purple-700">v{selectedRecord.payload_version}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Retry Count:</span>
                    <p className="font-mono font-bold text-slate-800">{selectedRecord.retry_count}</p>
                  </div>
                  <div className="col-span-2">
                    <span className="text-slate-400">SHA-256 Payload Hash:</span>
                    <p className="font-mono text-[10px] text-slate-700 truncate">{selectedRecord.payload_hash}</p>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() => setShowPayloadModal(true)}
                    className="text-xs text-purple-700 hover:text-purple-900 font-bold flex items-center space-x-1"
                  >
                    <FileCode className="w-3.5 h-3.5" />
                    <span>Inspect Sanitized JSON Payload</span>
                  </button>
                </div>
              </div>

              {/* Validation Errors if NOT_READY or has errors */}
              {selectedRecord.validation_errors && selectedRecord.validation_errors.length > 0 && (
                <div className="p-3.5 bg-amber-50 rounded-xl border border-amber-200 text-xs space-y-1.5">
                  <div className="flex items-center space-x-1.5 text-amber-900 font-bold">
                    <ShieldAlert className="w-4 h-4 text-amber-700" />
                    <span>Readiness Policy Blockers:</span>
                  </div>
                  <ul className="list-disc list-inside text-amber-800 space-y-0.5 text-[11px]">
                    {selectedRecord.validation_errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Last Error if failed */}
              {selectedRecord.last_error && (
                <div className="p-3 bg-rose-50 rounded-xl border border-rose-200 text-xs space-y-1">
                  <span className="font-bold text-rose-900">Sync Failure Error:</span>
                  <p className="text-rose-800 font-mono text-[11px]">{selectedRecord.last_error}</p>
                </div>
              )}

              {/* Action Controls */}
              <div className="space-y-3 pt-2 border-t border-slate-100">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  ERP Staging Operations
                </span>

                <div className="flex items-center space-x-2 text-xs">
                  <input
                    type="checkbox"
                    id="simFail"
                    checked={simulateFailure}
                    onChange={e => setSimulateFailure(e.target.checked)}
                    className="rounded border-slate-300 text-purple-600 focus:ring-purple-500"
                  />
                  <label htmlFor="simFail" className="text-slate-600 cursor-pointer">
                    Simulate ERP Adapter Timeout / Failure
                  </label>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => handleStageRecord(selectedRecord.application_id)}
                    disabled={actionLoading}
                    className="flex-1 py-2 px-3 bg-slate-800 hover:bg-slate-900 text-white rounded-xl text-xs font-bold transition flex items-center justify-center space-x-1.5 shadow-sm disabled:opacity-50"
                  >
                    <RotateCw className="w-3.5 h-3.5" />
                    <span>Re-Stage Snapshot</span>
                  </button>

                  {selectedRecord.status === 'SYNC_FAILED' ? (
                    <button
                      type="button"
                      onClick={() => handleRetryRecord(selectedRecord.id)}
                      disabled={actionLoading}
                      className="flex-1 py-2 px-3 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold transition flex items-center justify-center space-x-1.5 shadow-sm disabled:opacity-50"
                    >
                      <RotateCw className="w-3.5 h-3.5" />
                      <span>Retry Sync</span>
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleSyncRecord(selectedRecord.id)}
                      disabled={actionLoading || selectedRecord.status === 'SYNCED'}
                      className="flex-1 py-2 px-3 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-bold transition flex items-center justify-center space-x-1.5 shadow-sm disabled:opacity-50"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>{selectedRecord.status === 'SYNCED' ? 'Already Synced' : 'Sync to ERP (Mock)'}</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Integration Event Log */}
              <div className="pt-2 border-t border-slate-100 space-y-2">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Integration Event Log ({events.length})
                </span>
                <div className="max-h-40 overflow-y-auto space-y-1.5 divide-y divide-slate-100 pr-1">
                  {events.map(ev => (
                    <div key={ev.id} className="pt-1.5 text-[11px] space-y-0.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-purple-900">{ev.event_type}</span>
                        <span className={`text-[10px] font-mono font-bold px-1.5 py-0.2 rounded ${
                          ev.status === 'SUCCESS' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                        }`}>
                          {ev.status}
                        </span>
                      </div>
                      <p className="text-slate-500 font-mono text-[10px]">
                        Adapter: {ev.adapter_name} &bull; Ref: {ev.request_reference || '-'}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm text-center text-slate-400 text-xs">
              <Server className="w-8 h-8 mx-auto mb-2 text-slate-300" />
              <p>Select an ERP staging record from the queue to view payload and trigger mock sync.</p>
            </div>
          )}
        </div>
      </div>

      {/* Sanitized JSON Payload Modal */}
      {showPayloadModal && selectedRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <FileCode className="w-5 h-5 text-purple-600" />
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                  Sanitized ERP JSON Payload Snapshot (v{selectedRecord.payload_version})
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowPayloadModal(false)}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold"
              >
                &times;
              </button>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs font-mono text-slate-600">
              <p>Staging Reference: <strong>{selectedRecord.staging_reference}</strong></p>
              <p className="truncate">Hash (SHA-256): <strong>{selectedRecord.payload_hash}</strong></p>
            </div>

            <div className="flex-1 overflow-y-auto bg-slate-900 rounded-xl p-4 text-emerald-400 font-mono text-xs shadow-inner">
              <pre>{JSON.stringify(selectedRecord.payload, null, 2)}</pre>
            </div>

            <div className="pt-2 flex items-center justify-between border-t border-slate-100 text-xs">
              <span className="text-slate-400 italic">
                Strictly sanitized: Contains no passwords, JWTs, or raw OCR.
              </span>
              <button
                type="button"
                onClick={() => setShowPayloadModal(false)}
                className="px-4 py-2 bg-slate-800 text-white rounded-lg text-xs font-bold hover:bg-slate-900"
              >
                Close Payload
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
