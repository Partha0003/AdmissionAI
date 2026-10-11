import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  ShieldCheck,
  UserCheck,
  RefreshCw,
  Sparkles,
  History,
} from 'lucide-react';
import { PhysicalVerificationService } from '../services/physicalVerification';
import { applicationService } from '../services/application';
import { ScrutinyService } from '../services/scrutiny';
import {
  PhysicalVerificationSession,
  PhysicalDocumentVerification,
  ApplicationDetail,
  AdmissionReview,
  PhysicalDocDecision,
  PhysicalVerificationDecision,
  PhysicalVerificationAuditLog,
} from '../types';

export const AdminPhysicalVerificationWorkspace: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [session, setSession] = useState<PhysicalVerificationSession | null>(null);
  const [appDetail, setAppDetail] = useState<ApplicationDetail | null>(null);
  const [scrutinyReview, setScrutinyReview] = useState<AdmissionReview | null>(null);
  const [auditLogs, setAuditLogs] = useState<PhysicalVerificationAuditLog[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeDocId, setActiveDocId] = useState<string | null>(null);

  // Verification Item State (for active document)
  const [checks, setChecks] = useState({
    original_presented: false,
    document_legible: true,
    name_matches: true,
    dob_matches: true,
    id_matches: true,
    photo_check_done: true,
  });
  const [verificationNotes, setVerificationNotes] = useState<string>('');
  const [discrepancyReason, setDiscrepancyReason] = useState<string>('ORIGINAL_NOT_PRESENT');
  const [savingItem, setSavingItem] = useState<boolean>(false);

  // Session Completion & Reopen State
  const [overallDecision, setOverallDecision] = useState<PhysicalVerificationDecision>('VERIFIED');
  const [completionNotes, setCompletionNotes] = useState<string>('');
  const [completing, setCompleting] = useState<boolean>(false);
  const [showCompleteModal, setShowCompleteModal] = useState<boolean>(false);
  const [showReopenModal, setShowReopenModal] = useState<boolean>(false);
  const [reopenReason, setReopenReason] = useState<string>('');
  const [reopening, setReopening] = useState<boolean>(false);
  const [showAuditLogs, setShowAuditLogs] = useState<boolean>(false);

  const fetchWorkspaceData = async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const sessData = await PhysicalVerificationService.getSession(sessionId);
      setSession(sessData);

      if (sessData.application_id) {
        const appData = await applicationService.getAdminApplicationDetail(sessData.application_id);
        setAppDetail(appData);

        try {
          const reviewData = await ScrutinyService.getCurrentReview(sessData.application_id);
          setScrutinyReview(reviewData);
        } catch {
          // Scrutiny might not be started
        }
      }

      const logs = await PhysicalVerificationService.getAuditLogs(sessionId);
      setAuditLogs(logs);

      if (sessData.document_verifications && sessData.document_verifications.length > 0) {
        if (!activeDocId) {
          const firstDoc = sessData.document_verifications[0];
          setActiveDocId(firstDoc.document_id);
          populateActiveDocState(firstDoc);
        } else {
          const matched = sessData.document_verifications.find((d) => d.document_id === activeDocId);
          if (matched) populateActiveDocState(matched);
        }
      }
    } catch (err: any) {
      console.error('Failed to load physical verification workspace', err);
    } finally {
      setLoading(false);
    }
  };

  const populateActiveDocState = (docItem: PhysicalDocumentVerification) => {
    setVerificationNotes(docItem.verification_notes || '');
    setDiscrepancyReason(docItem.discrepancy_reason || 'ORIGINAL_NOT_PRESENT');
    if (docItem.checklist_checks) {
      setChecks({
        original_presented: docItem.checklist_checks.original_presented ?? false,
        document_legible: docItem.checklist_checks.document_legible ?? true,
        name_matches: docItem.checklist_checks.name_matches ?? true,
        dob_matches: docItem.checklist_checks.dob_matches ?? true,
        id_matches: docItem.checklist_checks.id_matches ?? true,
        photo_check_done: docItem.checklist_checks.photo_check_done ?? true,
      });
    }
  };

  useEffect(() => {
    fetchWorkspaceData();
  }, [sessionId]);

  const handleSelectDoc = (docItem: PhysicalDocumentVerification) => {
    setActiveDocId(docItem.document_id);
    populateActiveDocState(docItem);
  };

  const handleSaveDocDecision = async (decision: PhysicalDocDecision) => {
    if (!sessionId || !activeDocId) return;
    setSavingItem(true);
    try {
      if (decision === 'CORRECTION_REQUIRED') {
        await PhysicalVerificationService.requestCorrection(sessionId, activeDocId, {
          discrepancy_reason: discrepancyReason,
          verification_notes: verificationNotes,
          checklist_checks: checks,
        });
      } else {
        await PhysicalVerificationService.verifyDocument(sessionId, activeDocId, {
          officer_decision: decision,
          verification_notes: verificationNotes,
          discrepancy_reason: decision === 'NOT_VERIFIED' ? discrepancyReason : undefined,
          checklist_checks: checks,
        });
      }
      await fetchWorkspaceData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to record document decision');
    } finally {
      setSavingItem(false);
    }
  };

  const handleCompleteSession = async () => {
    if (!sessionId) return;
    setCompleting(true);
    try {
      await PhysicalVerificationService.completeSession(sessionId, {
        overall_decision: overallDecision,
        officer_notes: completionNotes || undefined,
      });
      setShowCompleteModal(false);
      await fetchWorkspaceData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to complete session');
    } finally {
      setCompleting(false);
    }
  };

  const handleReopenSession = async () => {
    if (!sessionId || !reopenReason.trim()) return;
    setReopening(true);
    try {
      await PhysicalVerificationService.reopenSession(sessionId, reopenReason);
      setShowReopenModal(false);
      setReopenReason('');
      await fetchWorkspaceData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to reopen session');
    } finally {
      setReopening(false);
    }
  };

  if (loading && !session) {
    return (
      <div className="py-24 text-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-sm text-gray-500">Loading Physical Verification Workspace...</p>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-gray-200">
        <AlertTriangle className="h-10 w-10 text-red-500 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-gray-900">Session Not Found</h2>
        <p className="text-sm text-gray-500 mt-1">
          The requested physical verification session could not be found.
        </p>
        <Link
          to="/admin/physical-verification"
          className="mt-4 inline-flex items-center gap-2 text-sm text-blue-600 hover:underline"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Verification Desk
        </Link>
      </div>
    );
  }

  const activeDocVerification = session.document_verifications.find(
    (d) => d.document_id === activeDocId
  );
  const activeChecklistItem = appDetail?.checklist.find((c) => c.document_id === activeDocId);

  const isCompleted = session.session_status === 'COMPLETED';

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/admin/physical-verification')}
            className="p-2 border border-gray-300 rounded-lg hover:bg-gray-100 text-gray-600 transition"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-gray-900">
                Physical Verification: {appDetail?.student_name || 'Candidate'}
              </h1>
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                  isCompleted
                    ? 'bg-green-100 text-green-800'
                    : 'bg-purple-100 text-purple-800 animate-pulse'
                }`}
              >
                {session.session_status}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">
              App #: <span className="font-mono">{appDetail?.application_number || session.application_id}</span> | Token:{' '}
              <span className="font-mono font-semibold text-blue-600">{session.appointment_id || 'On-Site Walk-In'}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isCompleted ? (
            <button
              onClick={() => setShowReopenModal(true)}
              className="px-4 py-2 border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-900 rounded-lg text-sm font-semibold transition flex items-center gap-2 shadow-sm"
            >
              <RefreshCw className="h-4 w-4" />
              Reopen Session
            </button>
          ) : (
            <button
              onClick={() => setShowCompleteModal(true)}
              className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm font-semibold transition flex items-center gap-2 shadow-md"
            >
              <ShieldCheck className="h-4 w-4" />
              Complete Physical Verification
            </button>
          )}

          <button
            onClick={() => setShowAuditLogs(!showAuditLogs)}
            className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm font-medium text-gray-700 transition flex items-center gap-1.5"
          >
            <History className="h-4 w-4 text-gray-400" />
            Audit Log ({auditLogs.length})
          </button>
        </div>
      </div>

      {/* Candidate Overview Ribbon */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div>
          <span className="text-xs text-gray-400">Allotted Branch</span>
          <p className="font-semibold text-gray-900">{appDetail?.allotted_branch || 'Engineering'}</p>
        </div>
        <div>
          <span className="text-xs text-gray-400">Quota / Category</span>
          <p className="font-semibold text-gray-900">
            {appDetail?.allotment_quota || appDetail?.quota || 'General'} (
            {appDetail?.community || 'OC'})
          </p>
        </div>
        <div>
          <span className="text-xs text-gray-400">Digital Scrutiny Status</span>
          <p className="font-semibold text-blue-600">
            {scrutinyReview?.status || 'NOT_STARTED'} ({scrutinyReview?.decision || 'PENDING'})
          </p>
        </div>
        <div>
          <span className="text-xs text-gray-400">Current Physical Decision</span>
          <p
            className={`font-bold ${
              session.overall_decision === 'VERIFIED'
                ? 'text-green-600'
                : session.overall_decision === 'CORRECTION_REQUIRED'
                ? 'text-red-600'
                : 'text-amber-600'
            }`}
          >
            {session.overall_decision}
          </p>
        </div>
      </div>

      {/* Collapsible Audit Trail */}
      {showAuditLogs && (
        <div className="bg-slate-900 rounded-xl p-5 text-white shadow-lg space-y-3">
          <div className="flex items-center justify-between border-b border-slate-700 pb-2">
            <h3 className="font-bold text-sm flex items-center gap-2">
              <History className="h-4 w-4 text-blue-400" />
              Physical Verification Audit Timeline (Append-Only)
            </h3>
            <button
              onClick={() => setShowAuditLogs(false)}
              className="text-xs text-slate-400 hover:text-white"
            >
              Close
            </button>
          </div>
          <div className="space-y-2 max-h-60 overflow-y-auto font-mono text-xs pr-2">
            {auditLogs.map((log) => (
              <div key={log.id} className="p-2.5 bg-slate-800 rounded-lg border border-slate-700">
                <div className="flex justify-between text-slate-300">
                  <span className="text-blue-400 font-bold">{log.action}</span>
                  <span className="text-slate-500">{new Date(log.created_at).toLocaleString()}</span>
                </div>
                <div className="mt-1 text-slate-400 text-xs">
                  Actor: <span className="text-slate-200">{log.actor_name || log.actor_id}</span> (
                  {log.actor_role})
                </div>
                {log.details && (
                  <pre className="mt-1 text-[11px] text-slate-300 overflow-x-auto">
                    {JSON.stringify(log.details, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Two-Column Verification Desk */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Document Navigation Sidebar */}
        <div className="lg:col-span-3 space-y-2">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider px-1">
            Required Documents ({session.document_verifications.length})
          </h3>
          <div className="space-y-1.5">
            {session.document_verifications.map((dv) => {
              const isActive = dv.document_id === activeDocId;
              return (
                <button
                  key={dv.id}
                  onClick={() => handleSelectDoc(dv)}
                  className={`w-full text-left p-3 rounded-xl border transition flex items-center justify-between ${
                    isActive
                      ? 'bg-blue-50 border-blue-500 shadow-sm'
                      : 'bg-white border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="truncate pr-2">
                    <p className={`text-xs font-bold truncate ${isActive ? 'text-blue-900' : 'text-gray-900'}`}>
                      {dv.document_type_name || dv.document_id}
                    </p>
                    <p className="text-[11px] text-gray-400 mt-0.5">
                      Ver {dv.version_number || 1} • {dv.document_type_code || 'DOC'}
                    </p>
                  </div>
                  <div>
                    {dv.officer_decision === 'VERIFIED' && (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    )}
                    {dv.officer_decision === 'CORRECTION_REQUIRED' && (
                      <AlertTriangle className="h-4 w-4 text-red-600" />
                    )}
                    {dv.officer_decision === 'PENDING' && (
                      <Clock className="h-4 w-4 text-amber-500" />
                    )}
                    {dv.officer_decision === 'NOT_VERIFIED' && (
                      <XCircle className="h-4 w-4 text-gray-400" />
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Column 1: Left - Digital AI Evidence */}
        <div className="lg:col-span-4 bg-white rounded-2xl border border-gray-200 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <div className="flex items-center gap-2 text-xs font-bold text-indigo-700 uppercase tracking-wider">
              <Sparkles className="h-4 w-4 text-indigo-600" />
              Digital AI Evidence
            </div>
            <span className="px-2 py-0.5 text-[11px] font-semibold bg-indigo-50 text-indigo-700 rounded-md border border-indigo-100">
              Advisory Evidence Only
            </span>
          </div>

          {activeChecklistItem ? (
            <div className="space-y-4 text-sm">
              <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                <span className="text-xs text-gray-400">Document Type & Version</span>
                <p className="font-semibold text-gray-900 mt-0.5">{activeChecklistItem.name}</p>
                <p className="text-xs text-gray-500 font-mono mt-1">
                  File: {activeChecklistItem.original_filename || 'Uploaded file'} (Ver {activeChecklistItem.active_version || 1})
                </p>
              </div>

              {/* Processing Pipeline Badges */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 bg-gray-50 rounded-lg border border-gray-100">
                  <span className="text-gray-400">Classification</span>
                  <p className="font-semibold text-gray-800 mt-0.5">
                    {activeChecklistItem.predicted_document_type || 'CLASSIFIED'}
                  </p>
                  <span className="text-[10px] text-gray-500">
                    Confidence: {activeChecklistItem.heuristic_confidence ? `${Math.round(activeChecklistItem.heuristic_confidence * 100)}%` : 'Rule-based'}
                  </span>
                </div>

                <div className="p-2.5 bg-gray-50 rounded-lg border border-gray-100">
                  <span className="text-gray-400">Preprocessing & OCR</span>
                  <p className="font-semibold text-gray-800 mt-0.5">
                    {activeChecklistItem.ocr_status || 'COMPLETED'}
                  </p>
                  <span className="text-[10px] text-gray-500">OpenCV deskewed</span>
                </div>
              </div>

              {/* Scrutiny Previous Findings */}
              <div className="p-3 bg-blue-50/70 rounded-xl border border-blue-100 text-xs text-blue-900 space-y-1">
                <p className="font-bold flex items-center gap-1.5">
                  <ShieldCheck className="h-3.5 w-3.5 text-blue-600" />
                  Phase 4F Digital Scrutiny Finding
                </p>
                <p className="text-blue-800">
                  Status: <span className="font-semibold">{scrutinyReview?.status || 'IN_REVIEW'}</span>
                </p>
                {scrutinyReview?.overall_comments && (
                  <p className="text-blue-700 italic">"{scrutinyReview.overall_comments}"</p>
                )}
              </div>
            </div>
          ) : (
            <div className="py-12 text-center text-gray-400 text-sm">
              Select a document from the left list to inspect digital evidence.
            </div>
          )}
        </div>

        {/* Column 2: Right - Physical Original Inspection Checklist & Decision */}
        <div className="lg:col-span-5 bg-white rounded-2xl border-2 border-blue-500 p-5 shadow-sm space-y-5">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <div className="flex items-center gap-2 text-xs font-bold text-blue-700 uppercase tracking-wider">
              <UserCheck className="h-4 w-4 text-blue-600" />
              Physical Original Inspection
            </div>
            <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-blue-100 text-blue-800">
              Officer Determination
            </span>
          </div>

          {activeDocVerification ? (
            <div className="space-y-4 text-sm">
              {/* Checklist Toggles */}
              <div className="space-y-2.5 bg-slate-50 p-4 rounded-xl border border-slate-200">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Physical Verification Checklist
                </h4>

                <label className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200 cursor-pointer hover:bg-blue-50/50 transition">
                  <span className="font-medium text-slate-800 text-xs">Original Physical Document Presented?</span>
                  <input
                    type="checkbox"
                    checked={checks.original_presented}
                    disabled={isCompleted}
                    onChange={(e) => setChecks({ ...checks, original_presented: e.target.checked })}
                    className="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                </label>

                <label className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200 cursor-pointer hover:bg-blue-50/50 transition">
                  <span className="font-medium text-slate-800 text-xs">Original Document Intact & Fully Legible?</span>
                  <input
                    type="checkbox"
                    checked={checks.document_legible}
                    disabled={isCompleted}
                    onChange={(e) => setChecks({ ...checks, document_legible: e.target.checked })}
                    className="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                </label>

                <label className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200 cursor-pointer hover:bg-blue-50/50 transition">
                  <span className="font-medium text-slate-800 text-xs">Candidate Name Matches Declaration?</span>
                  <input
                    type="checkbox"
                    checked={checks.name_matches}
                    disabled={isCompleted}
                    onChange={(e) => setChecks({ ...checks, name_matches: e.target.checked })}
                    className="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                </label>

                <label className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200 cursor-pointer hover:bg-blue-50/50 transition">
                  <span className="font-medium text-slate-800 text-xs">Date of Birth Matches Certificate?</span>
                  <input
                    type="checkbox"
                    checked={checks.dob_matches}
                    disabled={isCompleted}
                    onChange={(e) => setChecks({ ...checks, dob_matches: e.target.checked })}
                    className="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                </label>

                <label className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200 cursor-pointer hover:bg-blue-50/50 transition">
                  <span className="font-medium text-slate-800 text-xs">Roll / Certificate Number Matches?</span>
                  <input
                    type="checkbox"
                    checked={checks.id_matches}
                    disabled={isCompleted}
                    onChange={(e) => setChecks({ ...checks, id_matches: e.target.checked })}
                    className="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                </label>

                <label className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200 cursor-pointer hover:bg-blue-50/50 transition">
                  <span className="font-medium text-slate-800 text-xs">Photo & In-Person Identity Confirmed?</span>
                  <input
                    type="checkbox"
                    checked={checks.photo_check_done}
                    disabled={isCompleted}
                    onChange={(e) => setChecks({ ...checks, photo_check_done: e.target.checked })}
                    className="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
                  />
                </label>
              </div>

              {/* Discrepancy Reason if Correction */}
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Discrepancy / Correction Reason (If Flagging)
                </label>
                <select
                  value={discrepancyReason}
                  disabled={isCompleted}
                  onChange={(e) => setDiscrepancyReason(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-blue-500"
                >
                  <option value="ORIGINAL_NOT_PRESENT">ORIGINAL_NOT_PRESENT — Original not produced at desk</option>
                  <option value="ORIGINAL_ILLEGIBLE">ORIGINAL_ILLEGIBLE — Physical copy torn / damaged / illegible</option>
                  <option value="INFORMATION_MISMATCH">INFORMATION_MISMATCH — Name/Marks difference on physical copy</option>
                  <option value="WRONG_DOCUMENT">WRONG_DOCUMENT — Document presented does not match category</option>
                  <option value="OUTDATED_DOCUMENT">OUTDATED_DOCUMENT — Expired validity or old certificate</option>
                  <option value="MISSING_REQUIRED_DOCUMENT">MISSING_REQUIRED_DOCUMENT — Mandatory certificate omitted</option>
                  <option value="ADDITIONAL_DOCUMENT_REQUIRED">ADDITIONAL_DOCUMENT_REQUIRED — Supplementary affidavit needed</option>
                  <option value="OTHER">OTHER — Specify explanatory notes below</option>
                </select>
              </div>

              {/* Officer Notes */}
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Officer Inspection Notes / Instructions
                </label>
                <textarea
                  rows={2}
                  placeholder="Record verification notes, seal confirmations, or candidate instructions..."
                  value={verificationNotes}
                  disabled={isCompleted}
                  onChange={(e) => setVerificationNotes(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Action Buttons */}
              {!isCompleted && (
                <div className="grid grid-cols-2 gap-2 pt-2">
                  <button
                    onClick={() => handleSaveDocDecision('VERIFIED')}
                    disabled={savingItem}
                    className="px-4 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 shadow-sm disabled:opacity-50"
                  >
                    <CheckCircle className="h-4 w-4" />
                    Verify Original
                  </button>

                  <button
                    onClick={() => handleSaveDocDecision('CORRECTION_REQUIRED')}
                    disabled={savingItem}
                    className="px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 shadow-sm disabled:opacity-50"
                  >
                    <AlertTriangle className="h-4 w-4" />
                    Request Correction
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="py-12 text-center text-gray-400 text-sm">
              Select a document to conduct physical verification.
            </div>
          )}
        </div>
      </div>

      {/* Completion Modal */}
      {showCompleteModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-green-600" />
                Complete Physical Verification
              </h3>
              <button onClick={() => setShowCompleteModal(false)} className="text-gray-400 hover:text-gray-600">
                ✕
              </button>
            </div>

            <div className="space-y-3 text-sm">
              <p className="text-gray-600 text-xs">
                Record the final physical verification outcome. AI assisted with evidence presentation, but this decision reflects your on-site inspection.
              </p>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Overall Verification Decision
                </label>
                <select
                  value={overallDecision}
                  onChange={(e) => setOverallDecision(e.target.value as PhysicalVerificationDecision)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white font-medium focus:ring-2 focus:ring-blue-500"
                >
                  <option value="VERIFIED">VERIFIED — All required physical originals verified</option>
                  <option value="PARTIALLY_VERIFIED">PARTIALLY_VERIFIED — Some optional documents pending</option>
                  <option value="CORRECTION_REQUIRED">CORRECTION_REQUIRED — Candidate must bring corrected copies</option>
                  <option value="REJECTED">REJECTED — Physical verification failed</option>
                  <option value="PENDING">PENDING — On-site inspection incomplete</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Final Officer Summary Notes
                </label>
                <textarea
                  rows={3}
                  placeholder="Enter overall remarks for physical admission record..."
                  value={completionNotes}
                  onChange={(e) => setCompletionNotes(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
              <button
                onClick={() => setShowCompleteModal(false)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCompleteSession}
                disabled={completing}
                className="px-5 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm font-bold transition shadow"
              >
                {completing ? 'Completing...' : 'Submit Decision'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reopen Modal */}
      {showReopenModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2 text-amber-600">
                <RefreshCw className="h-5 w-5" />
                Reopen Verification Session
              </h3>
              <button onClick={() => setShowReopenModal(false)} className="text-gray-400 hover:text-gray-600">
                ✕
              </button>
            </div>

            <div className="space-y-3 text-sm">
              <p className="text-gray-600 text-xs">
                Authorized role required (Admission Head or Super Admin). Please provide a justification for reopening this completed session.
              </p>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Reopening Justification / Reason *
                </label>
                <textarea
                  rows={3}
                  placeholder="e.g. Dean of Admissions requested re-inspection of Community certificate..."
                  value={reopenReason}
                  onChange={(e) => setReopenReason(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs focus:ring-2 focus:ring-amber-500"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
              <button
                onClick={() => setShowReopenModal(false)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleReopenSession}
                disabled={reopening || !reopenReason.trim()}
                className="px-5 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-sm font-bold transition shadow disabled:opacity-50"
              >
                {reopening ? 'Reopening...' : 'Confirm Reopen'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
