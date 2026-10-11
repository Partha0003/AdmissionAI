import React, { useState, useEffect } from 'react';
import { 
  CreditCard, 
  AlertCircle, 
  Building2, 
  FileText, 
  RefreshCw,
  Sparkles,
  ShieldCheck,
  AlertTriangle
} from 'lucide-react';
import { paymentService } from '../services/payment';
import { documentService } from '../services/document';
import { StudentPaymentSummary } from '../types';

interface Props {
  onPaymentUpdated: () => void;
}

export const StudentPaymentCard: React.FC<Props> = ({ onPaymentUpdated }) => {
  const [summary, setSummary] = useState<StudentPaymentSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [showDDModal, setShowDDModal] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'ONLINE' | 'DD'>('ONLINE');

  // DD form state
  const [ddNumber, setDdNumber] = useState<string>('');
  const [ddDate, setDdDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [bankName, setBankName] = useState<string>('State Bank of India');
  const [branchName, setBranchName] = useState<string>('Main Branch, Chennai');
  const [ddFile, setDdFile] = useState<File | null>(null);
  const [uploadingFile, setUploadingFile] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchSummary = async () => {
    try {
      setLoading(true);
      const res = await paymentService.getStudentPaymentSummary();
      setSummary(res);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  const handleInitiateOnline = async (simulateFailure: boolean = false) => {
    try {
      setActionLoading(true);
      setErrorMsg(null);
      // If no active payment, initiate first
      let currentPayment = summary?.active_payment;
      if (!currentPayment) {
        currentPayment = await paymentService.initiatePayment({
          payment_method: 'DEMO_ONLINE_PAYMENT',
        });
      }
      await paymentService.simulateOnlinePayment(currentPayment.id, {
        simulate_failure: simulateFailure,
        notes: simulateFailure ? 'Simulated gateway network drop' : 'Simulated successful demo payment',
      });
      await fetchSummary();
      onPaymentUpdated();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to simulate online payment');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSubmitDD = async () => {
    if (!ddNumber || !bankName || !ddDate) {
      setErrorMsg('Please fill all mandatory DD details.');
      return;
    }
    try {
      setActionLoading(true);
      setErrorMsg(null);

      let docId: string | undefined = undefined;
      let docVerId: string | undefined = undefined;

      // If a file is selected, upload it first to obtain pinned version ID
      if (ddFile) {
        setUploadingFile(true);
        const uploadRes = await documentService.uploadDocument(
          'DEMAND_DRAFT',
          ddFile
        );
        docId = uploadRes.document_id;
        docVerId = uploadRes.version_id;
        setUploadingFile(false);
      }

      // If no active payment exists, initiate one first
      let currentPayment = summary?.active_payment;
      if (!currentPayment) {
        currentPayment = await paymentService.initiatePayment({
          payment_method: 'DEMAND_DRAFT',
        });
      }

      const authoritativeAmount = summary?.fee_requirement?.amount || 55000;

      await paymentService.submitDemandDraft(currentPayment.id, {
        dd_number: ddNumber,
        dd_date: ddDate,
        bank_name: bankName,
        branch_name: branchName,
        amount: authoritativeAmount,
        supporting_document_id: docId,
        supporting_document_version_id: docVerId,
      });

      setShowDDModal(false);
      setDdFile(null);
      await fetchSummary();
      onPaymentUpdated();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to submit Demand Draft');
    } finally {
      setActionLoading(false);
      setUploadingFile(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex items-center justify-center space-x-2 py-10">
        <RefreshCw className="w-5 h-5 animate-spin text-indigo-600" />
        <span className="text-xs text-slate-500 font-mono">Loading Payment Status...</span>
      </div>
    );
  }

  const fee = summary?.fee_requirement;
  const payment = summary?.active_payment;
  const status = payment?.status || 'PENDING';
  const isVerified = status === 'VERIFIED';
  const isCorrection = status === 'CORRECTION_REQUIRED';
  const isUnderReview = status === 'UNDER_REVIEW' || status === 'SUBMITTED';

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold">
            <CreditCard className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Admission Fee Settlement
            </h3>
            <span className="text-[10px] text-slate-400 font-mono">PHASE 6 &bull; PROTOTYPE RECONCILIATION</span>
          </div>
        </div>

        <div>
          <span className={`px-2.5 py-1 rounded-full font-mono text-[11px] font-bold ${
            isVerified
              ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
              : isCorrection
              ? 'bg-amber-100 text-amber-800 border border-amber-300 animate-bounce'
              : isUnderReview
              ? 'bg-blue-100 text-blue-800 border border-blue-300'
              : 'bg-slate-100 text-slate-700 border border-slate-300'
          }`}>
            {status}
          </span>
        </div>
      </div>

      {/* Authoritative Server-Side Fee Card */}
      <div className="bg-gradient-to-br from-slate-50 to-indigo-50/40 rounded-xl p-4 border border-slate-200/80 flex flex-wrap items-center justify-between gap-4">
        <div>
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Authoritative Server-Enforced Fee
          </span>
          <div className="flex items-baseline space-x-1.5 mt-0.5">
            <span className="text-2xl font-black text-slate-900 font-mono tracking-tight">
              ₹{fee?.amount ? Number(fee.amount).toLocaleString('en-IN') : '55,000'}
            </span>
            <span className="text-xs font-bold text-slate-500">{fee?.currency || 'INR'}</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Category: <strong className="text-slate-700">{fee?.category || 'GENERAL'}</strong> &bull; Quota: <strong className="text-slate-700">{fee?.quota || 'GOVERNMENT'}</strong>
          </p>
        </div>

        <div className="text-right">
          <span className="inline-block text-[10px] font-mono font-bold bg-amber-100 text-amber-900 px-2 py-0.5 rounded border border-amber-200">
            PROTOTYPE DEMO FEE
          </span>
          <p className="text-[10px] text-slate-400 mt-1">
            Server enforces authoritative amount
          </p>
        </div>
      </div>

      {/* Correction Required Banner */}
      {isCorrection && (
        <div className="p-4 bg-amber-50 border-2 border-amber-300 rounded-xl space-y-2">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-700" />
            <span className="text-xs font-bold text-amber-900 uppercase tracking-wide">
              Finance Correction Required: {summary?.correction_reason}
            </span>
          </div>
          <p className="text-xs text-amber-800">
            {summary?.correction_instructions || payment?.notes || 'Please resubmit updated DD details or clearer supporting evidence.'}
          </p>
          <button
            onClick={() => {
              if (payment?.dd_submission) {
                setDdNumber(payment.dd_submission.dd_number);
                setBankName(payment.dd_submission.bank_name);
                setBranchName(payment.dd_submission.branch_name || '');
              }
              setShowDDModal(true);
            }}
            className="mt-2 px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold transition shadow-sm"
          >
            Resubmit Corrected DD Details
          </button>
        </div>
      )}

      {/* Payment Active Details if exists */}
      {payment && (
        <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <span className="text-slate-400 font-medium">Payment Reference: </span>
              <strong className="font-mono text-slate-900">{payment.payment_reference}</strong>
            </div>
            <div>
              <span className="text-slate-400 font-medium">Method: </span>
              <span className="px-1.5 py-0.5 bg-indigo-50 text-indigo-700 rounded font-mono font-bold text-[10px]">
                {payment.payment_method}
              </span>
            </div>
          </div>

          {payment.dd_submission && (
            <div className="pt-2 border-t border-slate-200/60 grid grid-cols-2 gap-2 text-[11px]">
              <div>
                <span className="text-slate-400">DD Number:</span>
                <p className="font-mono font-bold text-slate-800">{payment.dd_submission.dd_number}</p>
              </div>
              <div>
                <span className="text-slate-400">Bank &amp; Branch:</span>
                <p className="font-bold text-slate-800">{payment.dd_submission.bank_name} ({payment.dd_submission.branch_name || 'Main'})</p>
              </div>
              <div>
                <span className="text-slate-400">DD Date:</span>
                <p className="font-mono text-slate-800">{payment.dd_submission.dd_date}</p>
              </div>
              <div>
                <span className="text-slate-400">Supporting Doc Version:</span>
                <p className="font-mono text-slate-800">
                  {payment.dd_submission.supporting_document_version_id ? 'Pinned Ver Record' : 'None Attached'}
                </p>
              </div>
            </div>
          )}

          {payment.verified_at && (
            <div className="pt-2 border-t border-slate-200/60 flex items-center space-x-2 text-emerald-700 font-medium text-[11px]">
              <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>Verified by Finance Desk on {new Date(payment.verified_at).toLocaleDateString()}</span>
            </div>
          )}
        </div>
      )}

      {/* Action Options (If not verified and not under review) */}
      {!isVerified && !isUnderReview && (
        <div className="space-y-3 pt-2">
          <div className="flex border-b border-slate-200">
            <button
              onClick={() => setActiveTab('ONLINE')}
              className={`pb-2 px-3 text-xs font-bold transition-colors border-b-2 ${
                activeTab === 'ONLINE'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Demo Online Payment
            </button>
            <button
              onClick={() => setActiveTab('DD')}
              className={`pb-2 px-3 text-xs font-bold transition-colors border-b-2 ${
                activeTab === 'DD'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Demand Draft (Physical DD)
            </button>
          </div>

          {activeTab === 'ONLINE' ? (
            <div className="p-4 bg-indigo-50/60 rounded-xl border border-indigo-200 space-y-3">
              <div className="flex items-start space-x-2.5">
                <Sparkles className="w-4 h-4 text-indigo-600 mt-0.5 flex-shrink-0" />
                <div className="text-xs text-indigo-950">
                  <strong className="block font-bold">Mock Online Settlement Gateway</strong>
                  <span>Simulate an online net banking or card transaction for demo verification.</span>
                </div>
              </div>

              <div className="flex flex-wrap gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => handleInitiateOnline(false)}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold shadow-sm transition flex items-center space-x-1.5 disabled:opacity-50"
                >
                  <CreditCard className="w-3.5 h-3.5" />
                  <span>{actionLoading ? 'Simulating...' : 'Simulate Success Payment (₹55,000)'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleInitiateOnline(true)}
                  disabled={actionLoading}
                  className="px-3 py-2 bg-white hover:bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-xs font-medium transition disabled:opacity-50"
                >
                  Simulate Gateway Failure
                </button>
              </div>
            </div>
          ) : (
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
              <div className="flex items-start space-x-2.5">
                <Building2 className="w-4 h-4 text-slate-600 mt-0.5 flex-shrink-0" />
                <div className="text-xs text-slate-800">
                  <strong className="block font-bold">Demand Draft Physical Submission</strong>
                  <span>Submit the DD details taken in favor of <em>XYZ Engineering College</em> and upload the scanned DD copy.</span>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setShowDDModal(true)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-bold shadow-sm transition flex items-center space-x-1.5"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Enter Demand Draft Details</span>
              </button>
            </div>
          )}
        </div>
      )}

      {errorMsg && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* DD Modal */}
      {showDDModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900 flex items-center">
                <Building2 className="w-4 h-4 mr-2 text-indigo-600" />
                Submit Demand Draft
              </h3>
              <button
                type="button"
                onClick={() => setShowDDModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                &times;
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">DD Number (6 Digits)</label>
                <input
                  type="text"
                  placeholder="e.g. 849201"
                  value={ddNumber}
                  onChange={e => setDdNumber(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-mono focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Bank Name</label>
                  <input
                    type="text"
                    value={bankName}
                    onChange={e => setBankName(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Branch Name</label>
                  <input
                    type="text"
                    value={branchName}
                    onChange={e => setBranchName(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">DD Issue Date</label>
                <input
                  type="date"
                  value={ddDate}
                  onChange={e => setDdDate(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-mono focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Upload Scanned DD Copy (PDF / Image)</label>
                <input
                  type="file"
                  accept="image/*,application/pdf"
                  onChange={e => setDdFile(e.target.files?.[0] || null)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:outline-none file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-indigo-50 file:text-indigo-700"
                />
              </div>

              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-[11px] text-amber-900 leading-relaxed">
                <strong>Notice:</strong> The submitted DD will be reviewed by the College Finance Officer. Verification is done per prototype workflow (No real bank connection).
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end space-x-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setShowDDModal(false)}
                className="px-4 py-2 border border-slate-200 text-slate-700 rounded-lg text-xs font-medium hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmitDD}
                disabled={actionLoading || uploadingFile}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold shadow"
              >
                {actionLoading || uploadingFile ? 'Submitting...' : 'Submit DD for Verification'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
