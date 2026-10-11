import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { 
  CreditCard, 
  Search, 
  Filter, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Eye, 
  RefreshCw,
  Building2
} from 'lucide-react';
import { paymentService } from '../services/payment';
import { PaymentTransaction, PaymentCorrectionReason, PaymentAuditLog } from '../types';
import { institutionConfig } from '../config/institution';

export const AdminPaymentDesk: React.FC = () => {
  const { paymentId } = useParams<{ paymentId?: string }>();

  const [payments, setPayments] = useState<PaymentTransaction[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedPayment, setSelectedPayment] = useState<PaymentTransaction | null>(null);
  const [auditLogs, setAuditLogs] = useState<PaymentAuditLog[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Decision Modal State
  const [showDecisionModal, setShowDecisionModal] = useState<boolean>(false);
  const [decisionType, setDecisionType] = useState<'VERIFY' | 'REJECT' | 'CORRECTION'>('VERIFY');
  const [reason, setReason] = useState<PaymentCorrectionReason>('INVALID_DD_DETAILS');
  const [notes, setNotes] = useState<string>('');
  const [processingDecision, setProcessingDecision] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchPayments = async () => {
    try {
      setLoading(true);
      const res = await paymentService.listAdminPayments({
        status: statusFilter === 'ALL' ? undefined : statusFilter,
        search: searchQuery || undefined,
      });
      setPayments(res);

      if (paymentId) {
        const found = res.find((p: PaymentTransaction) => p.id === paymentId);
        if (found) {
          handleSelectPayment(found);
        }
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPayments();
  }, [statusFilter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchPayments();
  };

  const handleSelectPayment = async (p: PaymentTransaction) => {
    setSelectedPayment(p);
    try {
      const logs = await paymentService.getPaymentAudit(p.id);
      setAuditLogs(logs);
    } catch {
      setAuditLogs([]);
    }
  };

  const openDecision = (type: 'VERIFY' | 'REJECT' | 'CORRECTION') => {
    setDecisionType(type);
    setErrorMsg(null);
    setNotes('');
    setShowDecisionModal(true);
  };

  const handleExecuteDecision = async () => {
    if (!selectedPayment) return;
    if ((decisionType === 'REJECT' || decisionType === 'CORRECTION') && reason === 'OTHER' && !notes.trim()) {
      setErrorMsg('Notes are mandatory when selecting "OTHER" reason.');
      return;
    }

    try {
      setProcessingDecision(true);
      setErrorMsg(null);

      const mappedDecision = decisionType === 'VERIFY' ? 'VERIFIED' : decisionType === 'REJECT' ? 'REJECTED' : 'CORRECTION_REQUIRED';
      const updated = await paymentService.reviewAdminPayment(selectedPayment.id, {
        decision: mappedDecision,
        reason: decisionType !== 'VERIFY' ? reason : undefined,
        notes: notes || undefined,
      });
      setSelectedPayment(updated);

      setShowDecisionModal(false);
      await fetchPayments();
      // Refresh audit
      const logs = await paymentService.getPaymentAudit(selectedPayment.id);
      setAuditLogs(logs);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to record decision');
    } finally {
      setProcessingDecision(false);
    }
  };

  const getStatusBadge = (st: string) => {
    switch (st) {
      case 'VERIFIED':
        return <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 font-mono text-[10px] font-bold rounded">VERIFIED</span>;
      case 'REJECTED':
        return <span className="px-2 py-0.5 bg-rose-100 text-rose-800 font-mono text-[10px] font-bold rounded">REJECTED</span>;
      case 'CORRECTION_REQUIRED':
        return <span className="px-2 py-0.5 bg-amber-100 text-amber-800 font-mono text-[10px] font-bold rounded">CORRECTION REQ</span>;
      case 'SUBMITTED':
      case 'UNDER_REVIEW':
        return <span className="px-2 py-0.5 bg-blue-100 text-blue-800 font-mono text-[10px] font-bold rounded">UNDER REVIEW</span>;
      default:
        return <span className="px-2 py-0.5 bg-slate-100 text-slate-700 font-mono text-[10px] font-bold rounded">{st}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-blue-900 rounded-2xl p-6 text-white shadow-lg relative overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-[10px] font-mono bg-blue-500/20 text-blue-200 border border-blue-400/30 px-2 py-0.5 rounded font-bold uppercase tracking-wider">
                Phase 6 &bull; Finance Reconciliation Desk
              </span>
              <span className="text-[10px] font-mono bg-amber-500/20 text-amber-300 border border-amber-400/30 px-2 py-0.5 rounded font-bold">
                PROTOTYPE / NO REAL BANK VERIFICATION
              </span>
            </div>
            <h1 className="text-2xl font-bold mt-2">
              Fee &amp; Demand Draft Settlement Queue
            </h1>
            <p className="text-xs text-blue-200 mt-0.5">
              {institutionConfig.name} &bull; Academic Year {institutionConfig.academicYear}
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => fetchPayments()}
              className="p-2 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh Queue</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid: Queue on Left, Inspector on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Queue Table (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-4">
            {/* Search & Filter Bar */}
            <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
              <form onSubmit={handleSearch} className="relative flex-1 w-full">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search App No / Ref / DD No..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </form>

              <div className="flex items-center space-x-2 w-full sm:w-auto">
                <Filter className="w-4 h-4 text-slate-400" />
                <select
                  value={statusFilter}
                  onChange={e => setStatusFilter(e.target.value)}
                  className="px-2.5 py-1.5 border border-slate-300 rounded-xl text-xs bg-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="SUBMITTED">SUBMITTED</option>
                  <option value="UNDER_REVIEW">UNDER_REVIEW</option>
                  <option value="VERIFIED">VERIFIED</option>
                  <option value="CORRECTION_REQUIRED">CORRECTION_REQUIRED</option>
                  <option value="REJECTED">REJECTED</option>
                  <option value="PENDING">PENDING</option>
                </select>
              </div>
            </div>

            {/* Queue Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-400 uppercase font-semibold text-[10px] tracking-wider">
                    <th className="py-2.5 px-3">Candidate / App No</th>
                    <th className="py-2.5 px-3">Method &amp; Ref</th>
                    <th className="py-2.5 px-3">Amount</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {loading ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-400">
                        <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-1 text-indigo-600" />
                        <span>Loading queue...</span>
                      </td>
                    </tr>
                  ) : payments.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-400 italic">
                        No payment transactions found matching criteria.
                      </td>
                    </tr>
                  ) : (
                    payments.map(p => {
                      const isSelected = selectedPayment?.id === p.id;
                      return (
                        <tr
                          key={p.id}
                          onClick={() => handleSelectPayment(p)}
                          className={`cursor-pointer transition-colors ${
                            isSelected ? 'bg-indigo-50/80 font-medium' : 'hover:bg-slate-50'
                          }`}
                        >
                          <td className="py-2.5 px-3">
                            <p className="font-bold text-slate-900">{p.candidate_name || 'Candidate'}</p>
                            <span className="text-[10px] font-mono text-slate-500">
                              App #{p.application_number || p.application_id.slice(0, 8)}
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <p className="font-mono font-bold text-indigo-700">{p.payment_reference}</p>
                            <span className="text-[10px] text-slate-500 font-mono">
                              {p.payment_method === 'DEMAND_DRAFT' && p.dd_submission
                                ? `DD: ${p.dd_submission.dd_number}`
                                : p.payment_method}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 font-mono font-bold text-slate-800">
                            ₹{Number(p.amount).toLocaleString('en-IN')}
                          </td>
                          <td className="py-2.5 px-3">{getStatusBadge(p.status)}</td>
                          <td className="py-2.5 px-3 text-right">
                            <button
                              onClick={e => {
                                e.stopPropagation();
                                handleSelectPayment(p);
                              }}
                              className="p-1 text-slate-500 hover:text-indigo-600 rounded"
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

        {/* Right: Payment Details Inspector (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {selectedPayment ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-5">
              {/* Header */}
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold tracking-wider">
                    Payment Dossier
                  </span>
                  <h2 className="text-base font-bold text-slate-900 font-mono">
                    {selectedPayment.payment_reference}
                  </h2>
                </div>
                <div>{getStatusBadge(selectedPayment.status)}</div>
              </div>

              {/* Transaction Details */}
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/80 text-xs space-y-2">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <span className="text-slate-400">Candidate Name:</span>
                    <p className="font-bold text-slate-900">{selectedPayment.candidate_name || '-'}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Application No:</span>
                    <p className="font-mono font-bold text-slate-900">{selectedPayment.application_number || '-'}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Authoritative Amount:</span>
                    <p className="font-mono font-bold text-emerald-700 text-sm">
                      ₹{Number(selectedPayment.amount).toLocaleString('en-IN')} {selectedPayment.currency}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400">Payment Method:</span>
                    <p className="font-mono font-bold text-slate-800">{selectedPayment.payment_method}</p>
                  </div>
                </div>
              </div>

              {/* Demand Draft Details if applicable */}
              {selectedPayment.dd_submission && (
                <div className="p-4 bg-indigo-50/50 rounded-xl border border-indigo-200 text-xs space-y-2.5">
                  <div className="flex items-center space-x-1.5 text-indigo-900 font-bold">
                    <Building2 className="w-4 h-4 text-indigo-600" />
                    <span>Demand Draft Submission Evidence</span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
                    <div>
                      <span className="text-slate-400">DD Number:</span>
                      <p className="font-mono font-bold text-slate-900">{selectedPayment.dd_submission.dd_number}</p>
                    </div>
                    <div>
                      <span className="text-slate-400">DD Date:</span>
                      <p className="font-mono font-bold text-slate-900">{selectedPayment.dd_submission.dd_date}</p>
                    </div>
                    <div>
                      <span className="text-slate-400">Bank Name:</span>
                      <p className="font-bold text-slate-900">{selectedPayment.dd_submission.bank_name}</p>
                    </div>
                    <div>
                      <span className="text-slate-400">Branch Name:</span>
                      <p className="font-bold text-slate-900">{selectedPayment.dd_submission.branch_name || 'Main'}</p>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-indigo-100 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                    <span>Pinned Doc Version: {selectedPayment.dd_submission.supporting_document_version_id || 'v1-pinned'}</span>
                    <span>Submitted: {new Date(selectedPayment.dd_submission.submitted_at).toLocaleDateString()}</span>
                  </div>
                </div>
              )}

              {/* Rejection / Correction Notes if any */}
              {(selectedPayment.rejection_reason || selectedPayment.notes) && (
                <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-xs space-y-1">
                  {selectedPayment.rejection_reason && (
                    <div className="font-bold text-amber-900">
                      Reason: {selectedPayment.rejection_reason}
                    </div>
                  )}
                  {selectedPayment.notes && (
                    <p className="text-amber-800 italic">"{selectedPayment.notes}"</p>
                  )}
                </div>
              )}

              {/* Action Buttons for Finance Officer */}
              {selectedPayment.status !== 'VERIFIED' && (
                <div className="space-y-2 pt-2 border-t border-slate-100">
                  <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                    Finance Officer Decisions
                  </span>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => openDecision('VERIFY')}
                      className="py-2 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition flex items-center justify-center space-x-1 shadow-sm"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Verify</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => openDecision('CORRECTION')}
                      className="py-2 px-3 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-xs font-bold transition flex items-center justify-center space-x-1 shadow-sm"
                    >
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>Correction</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => openDecision('REJECT')}
                      className="py-2 px-3 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition flex items-center justify-center space-x-1 shadow-sm"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Reject</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Audit History Drawer */}
              <div className="pt-2 border-t border-slate-100 space-y-2">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Payment Audit Trail ({auditLogs.length})
                </span>
                <div className="max-h-40 overflow-y-auto space-y-1.5 divide-y divide-slate-100 pr-1">
                  {auditLogs.map(log => (
                    <div key={log.id} className="pt-1.5 text-[11px] space-y-0.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-800">{log.action}</span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <p className="text-slate-500 font-mono text-[10px]">
                        By: {log.actor_role} ({log.actor_name || 'System'})
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm text-center text-slate-400 text-xs">
              <CreditCard className="w-8 h-8 mx-auto mb-2 text-slate-300" />
              <p>Select a payment from the queue to view evidence and record finance decisions.</p>
            </div>
          )}
        </div>
      </div>

      {/* Decision Confirmation Modal */}
      {showDecisionModal && selectedPayment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                {decisionType === 'VERIFY' ? 'Verify Payment Transaction' : decisionType === 'REJECT' ? 'Reject Payment Transaction' : 'Request Payment Correction'}
              </h3>
              <button
                type="button"
                onClick={() => setShowDecisionModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                &times;
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <p className="text-slate-600">
                Recording decision for <strong>{selectedPayment.candidate_name}</strong> ({selectedPayment.payment_reference})
              </p>

              {(decisionType === 'REJECT' || decisionType === 'CORRECTION') && (
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Reason Code</label>
                  <select
                    value={reason}
                    onChange={e => setReason(e.target.value as PaymentCorrectionReason)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  >
                    <option value="INVALID_DD_DETAILS">INVALID_DD_DETAILS</option>
                    <option value="AMOUNT_MISMATCH">AMOUNT_MISMATCH</option>
                    <option value="MISSING_SUPPORTING_DOCUMENT">MISSING_SUPPORTING_DOCUMENT</option>
                    <option value="ILLEGIBLE_DOCUMENT">ILLEGIBLE_DOCUMENT</option>
                    <option value="OUTDATED_DOCUMENT">OUTDATED_DOCUMENT</option>
                    <option value="INCORRECT_REFERENCE">INCORRECT_REFERENCE</option>
                    <option value="DUPLICATE_PAYMENT_REFERENCE">DUPLICATE_PAYMENT_REFERENCE</option>
                    <option value="OTHER">OTHER (Requires Notes)</option>
                  </select>
                </div>
              )}

              <div>
                <label className="block text-slate-700 font-semibold mb-1">
                  Finance Notes {reason === 'OTHER' ? '(Mandatory)' : '(Optional)'}
                </label>
                <textarea
                  rows={3}
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  placeholder="Enter details for the candidate..."
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              {errorMsg && (
                <div className="p-2.5 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-xs">
                  {errorMsg}
                </div>
              )}
            </div>

            <div className="pt-2 flex items-center justify-end space-x-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setShowDecisionModal(false)}
                className="px-4 py-2 border border-slate-200 text-slate-700 rounded-lg text-xs font-medium hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExecuteDecision}
                disabled={processingDecision}
                className={`px-4 py-2 text-white rounded-lg text-xs font-bold shadow disabled:opacity-50 ${
                  decisionType === 'VERIFY'
                    ? 'bg-emerald-600 hover:bg-emerald-700'
                    : decisionType === 'REJECT'
                    ? 'bg-rose-600 hover:bg-rose-700'
                    : 'bg-amber-600 hover:bg-amber-700'
                }`}
              >
                {processingDecision ? 'Processing...' : 'Confirm Decision'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
