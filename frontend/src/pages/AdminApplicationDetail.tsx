import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  User,
  GraduationCap,
  MapPin,
  Eye,
  RefreshCw,
  Sparkles,
  AlertCircle,
  Sliders,
  X,
  FileCheck,
  FileText,
  ScanText,
  Copy,
  Check,
  TableProperties,
  AlertTriangle,
  GitCompare,
  CheckCircle2,
  HelpCircle,
  SearchCode,
  UserCheck,
  RotateCcw,
  FileWarning,
  Send,
  CheckCheck,
  Clock,
  Info
} from 'lucide-react';
import { applicationService } from '../services/application';
import { documentService } from '../services/document';
import { ScrutinyService } from '../services/scrutiny';
import {
  ApplicationDetail,
  ChecklistItem,
  OCRResult,
  DocumentExtractionResult,
  ExtractedField,
  CrossDocumentReconciliation,
  ReconciliationFinding,
  AdmissionReview,
  FieldReviewDecision,
  CorrectionReason
} from '../types';

export const AdminApplicationDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [appData, setAppData] = useState<ApplicationDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [processingDocId, setProcessingDocId] = useState<string | null>(null);
  const [selectedDocForComparison, setSelectedDocForComparison] = useState<ChecklistItem | null>(null);
  const [selectedDocForOCR, setSelectedDocForOCR] = useState<ChecklistItem | null>(null);
  const [ocrData, setOcrData] = useState<OCRResult | null>(null);
  const [loadingOCR, setLoadingOCR] = useState<boolean>(false);
  const [copiedText, setCopiedText] = useState<boolean>(false);
  const [hoveredBlockIdx, setHoveredBlockIdx] = useState<number | null>(null);
  const [imgNaturalDims, setImgNaturalDims] = useState<{ width: number; height: number }>({ width: 800, height: 600 });

  // Phase 4D Field Extraction state
  const [selectedDocForExtraction, setSelectedDocForExtraction] = useState<ChecklistItem | null>(null);
  const [extractionData, setExtractionData] = useState<DocumentExtractionResult | null>(null);
  const [loadingExtraction, setLoadingExtraction] = useState<boolean>(false);
  const [selectedFieldForHighlight, setSelectedFieldForHighlight] = useState<ExtractedField | null>(null);
  const [extractionImgDims, setExtractionImgDims] = useState<{ width: number; height: number }>({ width: 800, height: 600 });

  // Phase 4E Reconciliation state
  const [reconciliationData, setReconciliationData] = useState<CrossDocumentReconciliation | null>(null);
  const [loadingReconciliation, setLoadingReconciliation] = useState<boolean>(false);
  const [runningReconciliation, setRunningReconciliation] = useState<boolean>(false);
  const [selectedFindingForProvenance, setSelectedFindingForProvenance] = useState<ReconciliationFinding | null>(null);

  // Phase 4F HITL Scrutiny state
  const [reviewData, setReviewData] = useState<AdmissionReview | null>(null);
  const [startingReview, setStartingReview] = useState<boolean>(false);
  
  const [showCorrectionModal, setShowCorrectionModal] = useState<boolean>(false);
  const [correctionReason, setCorrectionReason] = useState<CorrectionReason>('FIELD_MISMATCH');
  const [correctionInstructions, setCorrectionInstructions] = useState<string>('');
  const [flaggedDocIds, setFlaggedDocIds] = useState<string[]>([]);
  const [submittingCorrection, setSubmittingCorrection] = useState<boolean>(false);

  const [showCompleteModal, setShowCompleteModal] = useState<boolean>(false);
  const [completeDecision, setCompleteDecision] = useState<'VERIFIED' | 'REJECTED' | 'CORRECTION_REQUIRED'>('VERIFIED');
  const [completeComments, setCompleteComments] = useState<string>('');
  const [submittingComplete, setSubmittingComplete] = useState<boolean>(false);

  const [showReopenModal, setShowReopenModal] = useState<boolean>(false);
  const [reopenReason, setReopenReason] = useState<string>('');
  const [submittingReopen, setSubmittingReopen] = useState<boolean>(false);

  const currentUser = JSON.parse(localStorage.getItem('admissionai_user') || '{}');
  const isLeadAdmin = currentUser?.role === 'ADMISSION_HEAD' || currentUser?.role === 'SUPER_ADMIN';

  const fetchDetail = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const data = await applicationService.getAdminApplicationDetail(id);
      setAppData(data);
      fetchReconciliation(id);
      fetchReview(id);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to load application detail.');
    } finally {
      setLoading(false);
    }
  };

  const fetchReconciliation = async (appId: string) => {
    try {
      setLoadingReconciliation(true);
      const recon = await applicationService.getAdminReconciliation(appId);
      setReconciliationData(recon);
    } catch (err) {
      // No reconciliation snapshot yet
      setReconciliationData(null);
    } finally {
      setLoadingReconciliation(false);
    }
  };

  const fetchReview = async (appId: string) => {
    try {
      const rev = await ScrutinyService.getCurrentReview(appId);
      setReviewData(rev);
    } catch (err) {
      setReviewData(null);
    }
  };

  const handleStartReview = async () => {
    if (!id) return;
    try {
      setStartingReview(true);
      const rev = await ScrutinyService.startReview(id, 'Scrutiny session started from scrutiny desk');
      setReviewData(rev);
      await fetchDetail();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to start review session.');
    } finally {
      setStartingReview(false);
    }
  };

  const handleFieldDecision = async (
    fieldKey: string,
    decision: FieldReviewDecision,
    declaredVal?: string | null,
    extractedVal?: string | null,
    reconStatus?: string | null,
    notes?: string | null
  ) => {
    if (!id) return;
    try {
      await ScrutinyService.reviewField(id, {
        field_key: fieldKey,
        decision: decision,
        declared_value: declaredVal,
        extracted_value: extractedVal,
        reconciliation_status: reconStatus,
        notes: notes,
      });
      await fetchReview(id);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to record field verification decision.');
    }
  };

  const handleDocumentDecision = async (
    docId: string,
    status: string,
    reason?: string,
    comments?: string
  ) => {
    if (!id) return;
    try {
      await ScrutinyService.reviewDocument(id, {
        document_id: docId,
        status: status,
        correction_reason: reason,
        reviewer_comments: comments,
      });
      await fetchReview(id);
      await fetchDetail();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to record document review decision.');
    }
  };

  const handleSubmitCorrection = async () => {
    if (!id) return;
    if (!correctionReason) {
      setErrorMsg('Please select a structured correction reason.');
      return;
    }
    if (correctionReason === 'OTHER' && !correctionInstructions.trim()) {
      setErrorMsg("Reviewer instructions are mandatory when selecting 'OTHER'.");
      return;
    }
    try {
      setSubmittingCorrection(true);
      const rev = await ScrutinyService.requestCorrection(id, {
        correction_reason: correctionReason,
        correction_instructions: correctionInstructions,
        flagged_document_ids: flaggedDocIds,
      });
      setReviewData(rev);
      setShowCorrectionModal(false);
      setCorrectionInstructions('');
      setFlaggedDocIds([]);
      await fetchDetail();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to submit correction request.');
    } finally {
      setSubmittingCorrection(false);
    }
  };

  const handleSubmitComplete = async () => {
    if (!id) return;
    try {
      setSubmittingComplete(true);
      const rev = await ScrutinyService.completeReview(id, {
        decision: completeDecision,
        overall_comments: completeComments,
      });
      setReviewData(rev);
      setShowCompleteModal(false);
      setCompleteComments('');
      await fetchDetail();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to complete review.');
    } finally {
      setSubmittingComplete(false);
    }
  };

  const handleSubmitReopen = async () => {
    if (!id) return;
    if (!reopenReason.trim()) {
      setErrorMsg('Please provide a justification reason for reopening scrutiny.');
      return;
    }
    try {
      setSubmittingReopen(true);
      const rev = await ScrutinyService.reopenReview(id, reopenReason);
      setReviewData(rev);
      setShowReopenModal(false);
      setReopenReason('');
      await fetchDetail();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to reopen scrutiny review.');
    } finally {
      setSubmittingReopen(false);
    }
  };

  const handleTriggerReconciliation = async () => {
    if (!id) return;
    try {
      setRunningReconciliation(true);
      const recon = await applicationService.runAdminReconciliation(id);
      setReconciliationData(recon);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to run cross-document consistency reconciliation.');
    } finally {
      setRunningReconciliation(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [id]);

  const handleAdminTriggerPreprocessing = async (documentId: string) => {
    try {
      setProcessingDocId(documentId);
      await documentService.preprocessDocument(documentId);
      await fetchDetail();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to trigger OpenCV preprocessing');
    } finally {
      setProcessingDocId(null);
    }
  };

  const handleAdminTriggerOCR = async (documentId: string) => {
    try {
      setProcessingDocId(documentId);
      await documentService.runDocumentOCR(documentId);
      await fetchDetail();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to trigger OCR extraction');
    } finally {
      setProcessingDocId(null);
    }
  };

  const handleAdminTriggerExtraction = async (documentId: string) => {
    try {
      setProcessingDocId(documentId);
      await documentService.runFieldExtraction(documentId);
      await fetchDetail();
      if (selectedDocForExtraction && selectedDocForExtraction.document_id === documentId) {
        const data = await documentService.getAdminDocumentExtractedFields(documentId);
        setExtractionData(data);
      }
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to trigger field extraction');
    } finally {
      setProcessingDocId(null);
    }
  };

  const handleOpenExtractionModal = async (doc: ChecklistItem) => {
    if (!doc.document_id) return;
    try {
      setSelectedDocForExtraction(doc);
      setLoadingExtraction(true);
      setExtractionData(null);
      setSelectedFieldForHighlight(null);
      const data = await documentService.getAdminDocumentExtractedFields(doc.document_id);
      setExtractionData(data);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to load structured field extraction data.');
    } finally {
      setLoadingExtraction(false);
    }
  };

  const handleOpenOCRModal = async (doc: ChecklistItem) => {
    if (!doc.document_id) return;
    try {
      setSelectedDocForOCR(doc);
      setLoadingOCR(true);
      setOcrData(null);
      const data = await documentService.getAdminDocumentOCR(doc.document_id);
      setOcrData(data);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to load OCR extraction data.');
    } finally {
      setLoadingOCR(false);
    }
  };

  const handleCopyOCRText = () => {
    if (ocrData?.full_text) {
      navigator.clipboard.writeText(ocrData.full_text);
      setCopiedText(true);
      setTimeout(() => setCopiedText(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (errorMsg || !appData) {
    return (
      <div className="p-8 text-center text-rose-600">
        <p>{errorMsg || 'Application record not found.'}</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-16">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-200/80">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => navigate('/admin/applications')}
            className="p-2 bg-slate-100 hover:bg-slate-200 rounded-xl text-slate-600 transition"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-0.5 bg-indigo-50 text-indigo-700 text-xs font-bold rounded-full font-mono">
                {appData.application_number || 'DRAFT'}
              </span>
              <span className="px-2.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs font-bold rounded-full">
                {appData.status}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mt-1">
              {appData.student_name}
            </h1>
            <p className="text-xs text-slate-500">
              TNEA No: <span className="font-mono text-slate-800">{appData.tnea_application_number}</span> | Branch: <strong className="text-indigo-900">{appData.allotted_branch_name || appData.allotted_branch}</strong>
            </p>
          </div>
        </div>

        <div className="text-right">
          <p className="text-xs font-medium text-slate-500">Form Completion</p>
          <p className="text-xl font-black text-indigo-600">{appData.completion_percentage}%</p>
        </div>
      </div>

      {/* Phase 4F Human-In-The-Loop Scrutiny Command Desk */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white rounded-2xl p-6 shadow-md border border-indigo-900/60 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <span className="p-3 bg-indigo-600/30 border border-indigo-400/40 rounded-xl text-indigo-300">
              <UserCheck className="w-6 h-6" />
            </span>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-lg font-bold text-white">
                  Human Admission Scrutiny Desk
                </h2>
                <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 text-[11px] font-bold rounded-full">
                  Phase 4F Active
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-0.5">
                Authorized admission staff verification workspace. AI assists with evidence; human verifiers retain final decision authority.
              </p>
            </div>
          </div>

          {/* Current Review State Badge & Reviewer */}
          <div className="flex items-center space-x-3 bg-slate-800/80 p-3 rounded-xl border border-slate-700">
            <div className="text-right">
              <span className="text-[10px] text-slate-400 uppercase font-bold block">Scrutiny Status</span>
              <span className={`inline-block px-2.5 py-0.5 rounded text-xs font-black uppercase ${
                reviewData?.status === 'VERIFIED'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : reviewData?.status === 'CORRECTION_REQUIRED'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                  : reviewData?.status === 'RESUBMISSION_PENDING'
                  ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                  : reviewData?.status === 'REJECTED'
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                  : reviewData?.status === 'IN_REVIEW'
                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40'
                  : 'bg-slate-700 text-slate-300'
              }`}>
                {reviewData?.status || 'NOT_STARTED'}
              </span>
            </div>
            {reviewData?.reviewer_name && (
              <div className="border-l border-slate-700 pl-3 text-left">
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Assigned Verifier</span>
                <span className="text-xs font-mono text-slate-200">{reviewData.reviewer_name}</span>
              </div>
            )}
          </div>
        </div>

        {/* Scrutiny Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5 pt-2 border-t border-slate-800">
          {(!reviewData || reviewData.status === 'NOT_STARTED') && (
            <button
              type="button"
              onClick={handleStartReview}
              disabled={startingReview}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition inline-flex items-center space-x-1.5 shadow-sm"
            >
              <UserCheck className="w-4 h-4" />
              <span>{startingReview ? 'Starting...' : 'Start Scrutiny Review'}</span>
            </button>
          )}

          {reviewData && reviewData.status !== 'NOT_STARTED' && (
            <>
              <button
                type="button"
                onClick={() => setShowCorrectionModal(true)}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-xl text-xs font-bold transition inline-flex items-center space-x-1.5 shadow-sm"
              >
                <FileWarning className="w-4 h-4" />
                <span>Request Candidate Correction</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setCompleteDecision('VERIFIED');
                  setShowCompleteModal(true);
                }}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold transition inline-flex items-center space-x-1.5 shadow-sm"
              >
                <CheckCheck className="w-4 h-4" />
                <span>Complete Verification Decision</span>
              </button>

              {isLeadAdmin && (reviewData.status === 'VERIFIED' || reviewData.status === 'REJECTED') && (
                <button
                  type="button"
                  onClick={() => setShowReopenModal(true)}
                  className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-200 rounded-xl text-xs font-bold transition inline-flex items-center space-x-1.5 ml-auto"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Reopen Scrutiny</span>
                </button>
              )}
            </>
          )}
        </div>

        {/* Correction Instructions Banner if active */}
        {reviewData?.status === 'CORRECTION_REQUIRED' && (
          <div className="p-3.5 bg-amber-950/60 border border-amber-800/80 rounded-xl text-xs text-amber-200 space-y-1">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
              <strong>Active Correction Notice to Candidate:</strong>
              <span className="px-2 py-0.5 bg-amber-800 text-amber-100 rounded text-[10px] font-mono">
                {reviewData.correction_reason}
              </span>
            </div>
            <p className="pl-6 text-amber-100/90 font-medium">
              "{reviewData.correction_instructions}"
            </p>
          </div>
        )}
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Personal & Category */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 space-y-3">
          <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
            <User className="w-4 h-4 text-indigo-600" />
            <span>Identity & Category</span>
          </h3>
          <div className="text-xs space-y-2 text-slate-700">
            <p><span className="text-slate-400">Gender:</span> <strong>{appData.gender || 'N/A'}</strong></p>
            <p><span className="text-slate-400">Blood Group:</span> <strong>{appData.blood_group || 'N/A'}</strong></p>
            <p><span className="text-slate-400">Community:</span> <strong>{appData.caste || appData.community}</strong></p>
            <p><span className="text-slate-400">Religion / Tongue:</span> <strong>{appData.religion || 'N/A'} / {appData.mother_tongue || 'Tamil'}</strong></p>
            <p><span className="text-slate-400">Aadhaar No:</span> <strong className="font-mono">{appData.aadhaar_number || 'N/A'}</strong></p>
          </div>
        </div>

        {/* Academic Marks */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 space-y-3">
          <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
            <GraduationCap className="w-4 h-4 text-indigo-600" />
            <span>Academic Performance</span>
          </h3>
          <div className="text-xs space-y-2 text-slate-700">
            <div className="p-2.5 bg-indigo-50/70 rounded-lg text-indigo-950">
              <span className="text-[10px] uppercase font-bold text-indigo-600">Cutoff Score:</span>
              <p className="text-xl font-black font-mono">{appData.twelfth_cutoff_marks || 'N/A'}</p>
            </div>
            <p><span className="text-slate-400">12th Marks:</span> <strong>M:{appData.twelfth_maths_marks || '-'} | P:{appData.twelfth_physics_marks || '-'} | C:{appData.twelfth_chemistry_marks || '-'}</strong></p>
            <p><span className="text-slate-400">12th Total:</span> <strong>{appData.twelfth_total_marks}/{appData.twelfth_max_marks} ({appData.twelfth_percentage}%)</strong></p>
            <p><span className="text-slate-400">10th Total:</span> <strong>{appData.tenth_total_marks}/{appData.tenth_max_marks} ({appData.tenth_percentage}%)</strong></p>
          </div>
        </div>

        {/* Family & Concessions */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 space-y-3">
          <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
            <MapPin className="w-4 h-4 text-indigo-600" />
            <span>Family & Concessions</span>
          </h3>
          <div className="text-xs space-y-2 text-slate-700">
            <p><span className="text-slate-400">Father:</span> <strong>{appData.father_name || 'N/A'}</strong> ({appData.father_mobile || 'N/A'})</p>
            <p><span className="text-slate-400">Mother:</span> <strong>{appData.mother_name || 'N/A'}</strong></p>
            <p><span className="text-slate-400">Family Income:</span> <strong>₹{appData.annual_family_income?.toLocaleString() || 'N/A'}</strong></p>
            <div className="pt-2 flex flex-wrap gap-1">
              {appData.is_first_graduate && (
                <span className="px-2 py-0.5 bg-amber-100 text-amber-800 text-[10px] font-bold rounded">
                  FIRST GRADUATE
                </span>
              )}
              {appData.is_7_5_govt_quota && (
                <span className="px-2 py-0.5 bg-purple-100 text-purple-800 text-[10px] font-bold rounded">
                  7.5% GOVT QUOTA
                </span>
              )}
              {appData.is_pmss_scholarship && (
                <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-[10px] font-bold rounded">
                  PMSS
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Documents Scrutiny Table with AI Classification, Preprocessing, OCR & Structured Extraction */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <span>Document Verification & AI Intelligence Scrutiny</span>
              <span className="px-2.5 py-0.5 bg-purple-100 text-purple-800 text-[11px] font-bold rounded-full">
                Phase 4A, 4B, 4C & 4D Prototype
              </span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Review declared documents alongside heuristic classification, OpenCV image enhancements, OCR text, and structured deterministic field extraction. AI outputs are assistive only and require human verification.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider font-semibold border-y border-slate-200">
              <tr>
                <th className="py-3 px-4">Certificate Name</th>
                <th className="py-3 px-4">Requirement</th>
                <th className="py-3 px-4">Filename & Ver</th>
                <th className="py-3 px-4">AI Classification</th>
                <th className="py-3 px-4">OpenCV Preprocess</th>
                <th className="py-3 px-4">OCR Extraction</th>
                <th className="py-3 px-4">Structured Fields</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {appData.checklist.map((doc) => (
                <tr key={doc.code} className="hover:bg-slate-50/60">
                  <td className="py-3.5 px-4">
                    <p className="font-bold text-slate-900">{doc.name}</p>
                    {doc.mandatory_reason && (
                      <p className="text-[11px] text-indigo-600">{doc.mandatory_reason}</p>
                    )}
                  </td>
                  <td className="py-3.5 px-4">
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
                  <td className="py-3.5 px-4 font-mono text-xs text-slate-700">
                    {doc.original_filename ? (
                      <div>
                        <span>{doc.original_filename}</span>
                        <div className="text-[11px] text-slate-400">
                          v{doc.active_version || 1} • {((doc.file_size_bytes || 0) / 1024).toFixed(1)} KB
                        </div>
                      </div>
                    ) : (
                      <span className="text-rose-500 font-semibold">Not Uploaded</span>
                    )}
                  </td>
                  <td className="py-3.5 px-4">
                    {doc.document_id && doc.processing_status === 'COMPLETED' ? (
                      <div className="space-y-1">
                        <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 bg-purple-50 border border-purple-200 text-purple-900 rounded-md text-xs font-semibold">
                          <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                          <span>{doc.predicted_document_type_name || doc.predicted_document_type}</span>
                          <span className="bg-purple-200 text-purple-800 text-[10px] px-1.5 py-0.2 rounded font-bold">
                            {((doc.heuristic_confidence || 0.5) * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    ) : doc.document_id && (doc.processing_status === 'PROCESSING' || doc.processing_status === 'QUEUED') ? (
                      <span className="inline-flex items-center space-x-1 px-2.5 py-1 bg-blue-50 text-blue-700 rounded text-xs font-medium">
                        <RefreshCw className="w-3 h-3 animate-spin text-blue-600" />
                        <span>AI Processing...</span>
                      </span>
                    ) : doc.document_id && doc.processing_status === 'FAILED' ? (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-amber-50 text-amber-800 border border-amber-200 text-xs font-medium rounded">
                        <AlertCircle className="w-3 h-3 text-amber-600" />
                        <span>Classification Error</span>
                      </span>
                    ) : doc.document_id ? (
                      <span className="text-xs text-slate-400 italic">Not Processed</span>
                    ) : (
                      <span className="text-xs text-slate-300">-</span>
                    )}
                  </td>
                  <td className="py-3.5 px-4">
                    {doc.document_id && doc.has_preprocessed_image ? (
                      <div className="space-y-1">
                        <span className="inline-flex items-center space-x-1 px-2.5 py-1 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-md text-xs font-semibold">
                          <FileCheck className="w-3.5 h-3.5 text-emerald-600" />
                          <span>Deskewed</span>
                        </span>
                      </div>
                    ) : doc.document_id && doc.preprocessing_status === 'PROCESSING' ? (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-blue-50 text-blue-700 text-xs font-medium rounded">
                        <RefreshCw className="w-3 h-3 animate-spin text-blue-600" />
                        <span>Processing...</span>
                      </span>
                    ) : doc.document_id ? (
                      <button
                        type="button"
                        onClick={() => handleAdminTriggerPreprocessing(doc.document_id!)}
                        disabled={processingDocId === doc.document_id}
                        className="text-xs text-indigo-600 hover:text-indigo-800 font-medium inline-flex items-center space-x-1"
                      >
                        <Sliders className="w-3 h-3" />
                        <span>{processingDocId === doc.document_id ? 'Enhancing...' : 'Preprocess'}</span>
                      </button>
                    ) : (
                      <span className="text-xs text-slate-300">-</span>
                    )}
                  </td>
                  <td className="py-3.5 px-4">
                    {doc.document_id && doc.has_ocr_result ? (
                      <div className="space-y-1">
                        <span className="inline-flex items-center space-x-1 px-2.5 py-1 bg-indigo-50 border border-indigo-200 text-indigo-900 rounded-md text-xs font-semibold">
                          <ScanText className="w-3.5 h-3.5 text-indigo-600" />
                          <span>Extracted</span>
                        </span>
                      </div>
                    ) : doc.document_id && doc.ocr_status === 'PROCESSING' ? (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-blue-50 text-blue-700 text-xs font-medium rounded">
                        <RefreshCw className="w-3 h-3 animate-spin text-blue-600" />
                        <span>Scanning...</span>
                      </span>
                    ) : doc.document_id && doc.ocr_status === 'FAILED' ? (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-amber-50 text-amber-800 border border-amber-200 text-xs font-medium rounded">
                        <AlertCircle className="w-3 h-3 text-amber-600" />
                        <span>Failed</span>
                      </span>
                    ) : doc.document_id && doc.has_preprocessed_image ? (
                      <button
                        type="button"
                        onClick={() => handleAdminTriggerOCR(doc.document_id!)}
                        disabled={processingDocId === doc.document_id}
                        className="text-xs text-indigo-600 hover:text-indigo-800 font-medium inline-flex items-center space-x-1"
                      >
                        <ScanText className="w-3 h-3" />
                        <span>{processingDocId === doc.document_id ? 'Scanning...' : 'Run OCR'}</span>
                      </button>
                    ) : doc.document_id ? (
                      <span className="text-xs text-slate-400 italic">Needs Preprocess</span>
                    ) : (
                      <span className="text-xs text-slate-300">-</span>
                    )}
                  </td>
                  {/* Structured Fields Column */}
                  <td className="py-3.5 px-4">
                    {doc.document_id && doc.has_extracted_fields ? (
                      <div className="space-y-1">
                        <span className="inline-flex items-center space-x-1 px-2.5 py-1 bg-purple-50 border border-purple-200 text-purple-900 rounded-md text-xs font-semibold">
                          <TableProperties className="w-3.5 h-3.5 text-purple-600" />
                          <span>Structured</span>
                        </span>
                      </div>
                    ) : doc.document_id && doc.extraction_status === 'PROCESSING' ? (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-purple-50 text-purple-700 text-xs font-medium rounded">
                        <RefreshCw className="w-3 h-3 animate-spin text-purple-600" />
                        <span>Extracting...</span>
                      </span>
                    ) : doc.document_id && doc.extraction_status === 'FAILED' ? (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-amber-50 text-amber-800 border border-amber-200 text-xs font-medium rounded">
                        <AlertCircle className="w-3 h-3 text-amber-600" />
                        <span>Failed</span>
                      </span>
                    ) : doc.document_id && doc.has_ocr_result ? (
                      <button
                        type="button"
                        onClick={() => handleAdminTriggerExtraction(doc.document_id!)}
                        disabled={processingDocId === doc.document_id}
                        className="text-xs text-purple-600 hover:text-purple-800 font-medium inline-flex items-center space-x-1"
                      >
                        <TableProperties className="w-3 h-3" />
                        <span>{processingDocId === doc.document_id ? 'Extracting...' : 'Extract Fields'}</span>
                      </button>
                    ) : doc.document_id ? (
                      <span className="text-xs text-slate-400 italic">Needs OCR</span>
                    ) : (
                      <span className="text-xs text-slate-300">-</span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <div className="flex items-center justify-end space-x-2">
                      {doc.document_id && (
                        <>
                          {doc.has_extracted_fields && (
                            <button
                              type="button"
                              onClick={() => handleOpenExtractionModal(doc)}
                              className="px-2.5 py-1.5 bg-purple-50 hover:bg-purple-100 text-purple-700 rounded-lg text-xs font-bold inline-flex items-center space-x-1 transition"
                              title="Inspect Structured Extracted Fields & Provenance"
                            >
                              <TableProperties className="w-3.5 h-3.5" />
                              <span>Fields</span>
                            </button>
                          )}
                          {doc.has_ocr_result && (
                            <button
                              type="button"
                              onClick={() => handleOpenOCRModal(doc)}
                              className="px-2.5 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg text-xs font-bold inline-flex items-center space-x-1 transition"
                              title="Inspect OCR Text & Bounding Boxes"
                            >
                              <ScanText className="w-3.5 h-3.5" />
                              <span>OCR</span>
                            </button>
                          )}
                          {doc.has_preprocessed_image && (
                            <button
                              type="button"
                              onClick={() => setSelectedDocForComparison(doc)}
                              className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold inline-flex items-center space-x-1 transition"
                              title="Compare Original vs Preprocessed Image"
                            >
                              <Sliders className="w-3.5 h-3.5" />
                              <span>Compare</span>
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => handleDocumentDecision(doc.document_id!, 'CONFIRMED', undefined, 'Confirmed by verifier')}
                            className="px-2.5 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-lg text-xs font-bold inline-flex items-center space-x-1"
                            title="Confirm Document Verification"
                          >
                            <Check className="w-3.5 h-3.5" />
                            <span>Confirm</span>
                          </button>
                          <a
                            href={documentService.getDocumentDownloadUrl(doc.document_id)}
                            target="_blank"
                            rel="noreferrer"
                            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold inline-flex items-center space-x-1"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>Inspect</span>
                          </a>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Phase 4E Cross-Document Consistency & Verification Matrix */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="p-2 bg-indigo-50 text-indigo-700 rounded-xl">
                <GitCompare className="w-5 h-5" />
              </span>
              <div>
                <div className="flex items-center space-x-2">
                  <h2 className="text-base font-bold text-slate-900">
                    Cross-Document Consistency & Verification Matrix
                  </h2>
                  <span className="px-2.5 py-0.5 bg-indigo-100 text-indigo-800 text-[11px] font-bold rounded-full">
                    Phase 4E Engine
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Deterministic cross-document reconciliation between candidate self-declarations, extracted document fields, and the imported TNEA allotment baseline.
                </p>
              </div>
            </div>
          </div>
          <div>
            <button
              type="button"
              onClick={handleTriggerReconciliation}
              disabled={runningReconciliation}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-sm transition inline-flex items-center space-x-1.5 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${runningReconciliation ? 'animate-spin' : ''}`} />
              <span>{runningReconciliation ? 'Reconciling...' : 'Run Consistency Reconciliation'}</span>
            </button>
          </div>
        </div>

        {/* Non-Authenticity and Read-Only Disclaimers */}
        <div className="p-4 bg-amber-50/90 border border-amber-300 rounded-xl text-xs text-amber-950 flex items-start space-x-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <strong className="text-amber-900 font-bold block text-sm">
              Non-Authenticity & Non-Mutation Notice
            </strong>
            <p className="text-amber-900 leading-relaxed font-medium">
              "Phase 4E performs deterministic cross-document consistency reconciliation only. It does not verify document authenticity, legal validity, or query live government databases. Human verifiers retain sole verification authority."
            </p>
            <p className="text-[11px] text-amber-800 italic">
              Strictly read-only: running reconciliation does not alter candidate application workflow state or document verification status. TNEA data represents stored/imported allotment baseline only.
            </p>
          </div>
        </div>

        {loadingReconciliation ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-400">
            <RefreshCw className="w-7 h-7 animate-spin text-indigo-600 mb-2" />
            <p className="text-xs font-medium">Loading reconciliation snapshot...</p>
          </div>
        ) : reconciliationData ? (
          <div className="space-y-5">
            {/* Status Summary & Metric Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Overall Status</span>
                <span
                  className={`inline-block mt-0.5 px-2.5 py-1 rounded-md text-xs font-black ${
                    reconciliationData.overall_status === 'MATCH'
                      ? 'bg-emerald-100 text-emerald-800'
                      : reconciliationData.overall_status === 'DISCREPANCY_DETECTED'
                      ? 'bg-rose-100 text-rose-800'
                      : reconciliationData.overall_status === 'PENDING_SCRUTINY'
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-slate-200 text-slate-800'
                  }`}
                >
                  {reconciliationData.overall_status}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Passed Checks</span>
                <span className="font-bold text-emerald-700 text-sm">
                  {reconciliationData.passed_rules_count} / {reconciliationData.total_rules_evaluated}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Discrepancies</span>
                <span className="font-bold text-rose-700 text-sm">
                  {reconciliationData.discrepancy_count}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Pending Scrutiny</span>
                <span className="font-bold text-amber-700 text-sm">
                  {reconciliationData.pending_scrutiny_count}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Incomplete Checks</span>
                <span className="font-semibold text-slate-700 text-sm">
                  {reconciliationData.incomplete_count}
                </span>
              </div>
            </div>

            {/* Reconciliation Findings Table */}
            <div className="overflow-x-auto border border-slate-200 rounded-xl">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider font-semibold border-b border-slate-200 text-[11px]">
                  <tr>
                    <th className="py-3 px-3.5">Parameter & Check</th>
                    <th className="py-3 px-3.5">TNEA Allotment Baseline</th>
                    <th className="py-3 px-3.5">Application Form Draft</th>
                    <th className="py-3 px-3.5">Extracted Document Field</th>
                    <th className="py-3 px-3.5">Status</th>
                    <th className="py-3 px-3.5 text-center">Human Scrutiny Action</th>
                    <th className="py-3 px-3.5 text-right">Provenance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {reconciliationData.findings.map((f, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/70">
                      <td className="py-3 px-3.5">
                        <p className="font-bold text-slate-900">{f.rule_name}</p>
                        <p className="text-[10px] text-slate-400 font-mono">{f.field_key}</p>
                      </td>
                      <td className="py-3 px-3.5 font-mono text-slate-700">
                        {f.allotment_baseline_value !== null && f.allotment_baseline_value !== undefined ? (
                          <span className="bg-indigo-50 text-indigo-900 px-2 py-0.5 rounded font-semibold">
                            {String(f.allotment_baseline_value)}
                          </span>
                        ) : (
                          <span className="text-slate-300">-</span>
                        )}
                      </td>
                      <td className="py-3 px-3.5 font-mono text-slate-700">
                        {f.declared_value !== null && f.declared_value !== undefined ? (
                          <span className="bg-slate-100 text-slate-900 px-2 py-0.5 rounded font-semibold">
                            {String(f.declared_value)}
                          </span>
                        ) : (
                          <span className="text-slate-400 italic">Not Declared</span>
                        )}
                      </td>
                      <td className="py-3 px-3.5 font-mono text-slate-700">
                        {f.extracted_value !== null && f.extracted_value !== undefined ? (
                          <span className="bg-purple-50 text-purple-900 px-2 py-0.5 rounded font-semibold">
                            {String(f.extracted_value)}
                          </span>
                        ) : (
                          <span className="text-slate-400 italic">Missing / Not Detected</span>
                        )}
                      </td>
                      <td className="py-3 px-3.5">
                        {f.status === 'MATCH' && (
                          <span className="inline-flex items-center space-x-1 px-2.5 py-1 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-md font-bold text-[11px]">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            <span>MATCH</span>
                          </span>
                        )}
                        {f.status === 'DISCREPANCY' && (
                          <div>
                            <span className="inline-flex items-center space-x-1 px-2.5 py-1 bg-rose-50 text-rose-800 border border-rose-200 rounded-md font-bold text-[11px]">
                              <AlertCircle className="w-3 h-3 text-rose-600" />
                              <span>DISCREPANCY</span>
                            </span>
                            {f.discrepancy_reason && (
                              <p className="text-[10px] text-rose-600 mt-1 font-sans">{f.discrepancy_reason}</p>
                            )}
                          </div>
                        )}
                        {f.status === 'PENDING_SCRUTINY' && (
                          <div>
                            <span className="inline-flex items-center space-x-1 px-2.5 py-1 bg-amber-50 text-amber-800 border border-amber-200 rounded-md font-bold text-[11px]">
                              <HelpCircle className="w-3 h-3 text-amber-600" />
                              <span>SCRUTINY NEEDED</span>
                            </span>
                            {f.discrepancy_reason && (
                              <p className="text-[10px] text-amber-700 mt-1 font-sans">{f.discrepancy_reason}</p>
                            )}
                          </div>
                        )}
                        {f.status === 'INCOMPLETE_DOCUMENTS' && (
                          <span className="inline-flex items-center space-x-1 px-2.5 py-1 bg-slate-100 text-slate-700 border border-slate-200 rounded-md font-medium text-[11px]">
                            <AlertCircle className="w-3 h-3 text-slate-500" />
                            <span>INCOMPLETE</span>
                          </span>
                        )}
                      </td>

                      {/* Phase 4F Human Scrutiny Field Action Column */}
                      {(() => {
                        const existingReview = reviewData?.field_reviews?.find(fr => fr.field_key === f.field_key);
                        return (
                          <td className="py-3 px-3.5 text-center">
                            <div className="flex flex-col items-center space-y-1.5">
                              {existingReview ? (
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  existingReview.decision === 'CONFIRMED'
                                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                                    : existingReview.decision === 'ACCEPTED_WITH_REVIEW'
                                    ? 'bg-blue-100 text-blue-800 border border-blue-300'
                                    : existingReview.decision === 'REQUIRES_CORRECTION'
                                    ? 'bg-amber-100 text-amber-800 border border-amber-300'
                                    : 'bg-slate-100 text-slate-700'
                                }`}>
                                  {existingReview.decision}
                                </span>
                              ) : (
                                <span className="text-[10px] text-slate-400 italic">Unreviewed</span>
                              )}

                              {/* Quick Decision Action Buttons */}
                              <div className="flex items-center space-x-1">
                                <button
                                  type="button"
                                  onClick={() => handleFieldDecision(f.field_key, 'CONFIRMED', f.declared_value ? String(f.declared_value) : null, f.extracted_value ? String(f.extracted_value) : null, f.status, 'Confirmed by verifier')}
                                  className="p-1 hover:bg-emerald-100 text-emerald-700 rounded transition"
                                  title="Confirm Field Decision"
                                >
                                  <Check className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleFieldDecision(f.field_key, 'ACCEPTED_WITH_REVIEW', f.declared_value ? String(f.declared_value) : null, f.extracted_value ? String(f.extracted_value) : null, f.status, 'Accepted with review notes')}
                                  className="p-1 hover:bg-blue-100 text-blue-700 rounded transition"
                                  title="Accept with Review"
                                >
                                  <CheckCircle2 className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleFieldDecision(f.field_key, 'REQUIRES_CORRECTION', f.declared_value ? String(f.declared_value) : null, f.extracted_value ? String(f.extracted_value) : null, f.status, 'Flagged for candidate correction')}
                                  className="p-1 hover:bg-amber-100 text-amber-700 rounded transition"
                                  title="Flag for Correction"
                                >
                                  <FileWarning className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleFieldDecision(f.field_key, 'NOT_APPLICABLE', f.declared_value ? String(f.declared_value) : null, f.extracted_value ? String(f.extracted_value) : null, f.status, 'Not applicable')}
                                  className="p-1 hover:bg-slate-200 text-slate-600 rounded transition"
                                  title="Not Applicable"
                                >
                                  <span className="text-[10px] font-bold">N/A</span>
                                </button>
                              </div>
                            </div>
                          </td>
                        );
                      })()}

                      <td className="py-3 px-3.5 text-right">
                        {f.provenance && (
                          <button
                            type="button"
                            onClick={() => setSelectedFindingForProvenance(f)}
                            className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-bold text-[11px] inline-flex items-center space-x-1 transition"
                            title="Inspect complete reconciliation provenance"
                          >
                            <SearchCode className="w-3.5 h-3.5 text-slate-500" />
                            <span>Audit</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="text-center py-10 bg-slate-50 rounded-xl border border-dashed border-slate-200">
            <GitCompare className="w-8 h-8 text-slate-400 mx-auto mb-2" />
            <p className="text-xs font-semibold text-slate-700">No reconciliation snapshot recorded yet.</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Click "Run Consistency Reconciliation" above to execute cross-document comparison.</p>
          </div>
        )}
      </div>

      {/* Phase 4F Scrutiny Audit Trail Timeline */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <span className="p-2 bg-slate-100 text-slate-700 rounded-xl">
              <Clock className="w-5 h-5 text-indigo-600" />
            </span>
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Human Scrutiny Audit Log & Trail
              </h2>
              <p className="text-xs text-slate-500">
                Immutable ledger of all reviewer actions, transitions, instructions, and verification decisions.
              </p>
            </div>
          </div>
          <span className="text-xs font-mono text-slate-500 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200">
            {reviewData?.audit_logs?.length || 0} Actions Recorded
          </span>
        </div>

        {reviewData?.audit_logs && reviewData.audit_logs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider font-semibold border-b border-slate-200 text-[11px]">
                <tr>
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3">Reviewer / Actor</th>
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">Transition</th>
                  <th className="py-2.5 px-3">Details / Reasons</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {reviewData.audit_logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/70">
                    <td className="py-2.5 px-3 text-slate-500 text-[11px]">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="font-semibold text-slate-800">{log.user_name || log.user_id || 'System'}</span>
                      <span className="text-[10px] text-slate-400 block font-sans">{log.user_role}</span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 bg-indigo-50 text-indigo-800 font-bold rounded text-[11px]">
                        {log.action}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-[11px]">
                      {log.previous_status ? (
                        <span>
                          <span className="text-slate-400">{log.previous_status}</span> &rarr;{' '}
                          <span className="font-bold text-slate-900">{log.new_status}</span>
                        </span>
                      ) : (
                        <span className="font-bold text-slate-900">{log.new_status || '-'}</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-slate-700 font-sans text-xs">
                      {log.details?.reason && <span className="font-semibold">{log.details.reason}. </span>}
                      {log.details?.instructions && <span className="italic">"{log.details.instructions}" </span>}
                      {log.details?.comments && <span>{log.details.comments} </span>}
                      {log.details?.notes && <span>{log.details.notes}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-xs text-slate-400 italic py-4 text-center">
            No scrutiny audit records found for this application yet.
          </p>
        )}
      </div>

      {/* Provenance Audit Modal (Phase 4E) */}
      {selectedFindingForProvenance && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full flex flex-col overflow-hidden border border-slate-200">
            <div className="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between bg-indigo-50/50">
              <div className="flex items-center space-x-2">
                <span className="p-1.5 bg-indigo-100 text-indigo-700 rounded-lg">
                  <SearchCode className="w-4 h-4" />
                </span>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Reconciliation Diagnostic Provenance
                  </h3>
                  <p className="text-[11px] text-slate-500 font-mono">
                    Rule ID: {selectedFindingForProvenance.rule_id}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedFindingForProvenance(null)}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs">
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-2">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Field Key</span>
                    <span className="font-mono font-bold text-slate-800">{selectedFindingForProvenance.field_key}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Comparison Method</span>
                    <span className="font-mono font-bold text-indigo-700">{selectedFindingForProvenance.provenance?.comparison_method || 'EXACT_MATCH'}</span>
                  </div>
                  {selectedFindingForProvenance.provenance?.tolerance_applied && (
                    <div className="col-span-2">
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">Tolerance Applied</span>
                      <span className="font-mono font-bold text-emerald-700">{selectedFindingForProvenance.provenance.tolerance_applied}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Document Reference */}
              {selectedFindingForProvenance.provenance?.document_id && (
                <div className="border border-slate-200 p-3.5 rounded-xl space-y-1.5 bg-white font-mono text-[11px]">
                  <p className="text-slate-400 uppercase text-[10px] font-bold">Document Source Integrity</p>
                  <p><span className="text-slate-500">Document ID:</span> <strong className="text-slate-800">{selectedFindingForProvenance.provenance.document_id}</strong></p>
                  <p><span className="text-slate-500">Document Version:</span> <strong className="text-slate-800">v{selectedFindingForProvenance.provenance.document_version}</strong></p>
                  <p><span className="text-slate-500">Extraction Result ID:</span> <strong className="text-slate-800">{selectedFindingForProvenance.provenance.extraction_result_id}</strong></p>
                  <p><span className="text-slate-500">OCR Block Indices:</span> <strong className="text-indigo-700">{JSON.stringify(selectedFindingForProvenance.provenance.ocr_block_indices)}</strong></p>
                  {selectedFindingForProvenance.provenance.bounding_box && (
                    <p><span className="text-slate-500">Bounding Box (x,y,w,h):</span> <strong className="text-purple-700">[{selectedFindingForProvenance.provenance.bounding_box.x}, {selectedFindingForProvenance.provenance.bounding_box.y}, {selectedFindingForProvenance.provenance.bounding_box.width}, {selectedFindingForProvenance.provenance.bounding_box.height}]</strong></p>
                  )}
                </div>
              )}

              {/* Review Reason / Discrepancy details */}
              {selectedFindingForProvenance.review_reason && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-[11px] text-amber-900">
                  <strong className="block mb-0.5">Scrutiny Context:</strong>
                  {selectedFindingForProvenance.review_reason}
                </div>
              )}
            </div>

            <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-end">
              <button
                type="button"
                onClick={() => setSelectedFindingForProvenance(null)}
                className="px-4 py-2 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800 transition"
              >
                Close Audit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Comparison Modal: Original vs Preprocessed Image */}
      {selectedDocForComparison && selectedDocForComparison.document_id && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-5xl w-full max-h-[90vh] flex flex-col overflow-hidden border border-slate-200">
            <div className="p-4 sm:p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="px-2.5 py-0.5 bg-purple-100 text-purple-800 text-xs font-bold rounded-full">
                    Phase 4B OpenCV Visual Scrutiny
                  </span>
                  <span className="text-xs text-slate-500 font-mono">
                    {selectedDocForComparison.code}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-slate-900 mt-1">
                  {selectedDocForComparison.name} — Preprocessing Comparison
                </h3>
              </div>
              <button
                onClick={() => setSelectedDocForComparison(null)}
                className="p-2 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 sm:p-6 overflow-y-auto space-y-6">
              <div className="p-3 bg-purple-50/80 border border-purple-200 rounded-xl text-xs text-purple-950 flex items-start space-x-2">
                <Sparkles className="w-4 h-4 text-purple-600 shrink-0 mt-0.5" />
                <div>
                  <strong>OCR Preprocessing Transformation:</strong> The original document is normalized, converted to grayscale, denoised via Gaussian filtering, enhanced with CLAHE contrast equalization, deskewed, and binarized for optimal downstream OCR text extraction.
                  <p className="mt-1 text-[11px] text-purple-700 italic">
                    Preprocessed image — assistive transformation for downstream OCR; not human verification.
                  </p>
                </div>
              </div>

              {/* Side-by-side Images */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Original Document */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      1. Original Uploaded Document
                    </h4>
                    <span className="text-[11px] font-mono text-slate-500">
                      v{selectedDocForComparison.active_version || 1} • {selectedDocForComparison.original_filename}
                    </span>
                  </div>
                  <div className="border border-slate-200 rounded-xl bg-slate-50 min-h-[350px] max-h-[450px] flex items-center justify-center p-2 overflow-hidden">
                    <img
                      src={documentService.getDocumentDownloadUrl(selectedDocForComparison.document_id)}
                      alt="Original Document"
                      className="max-h-[420px] max-w-full object-contain rounded shadow-xs"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                    <div className="text-center p-4 text-slate-400 text-xs">
                      <p className="font-semibold text-slate-600">{selectedDocForComparison.original_filename}</p>
                      <p className="mt-1 text-[11px]">Click Inspect to view full PDF/Image in new tab</p>
                    </div>
                  </div>
                </div>

                {/* Preprocessed Image */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-purple-900 flex items-center space-x-1">
                      <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                      <span>2. OpenCV Preprocessed Output (OCR-Ready)</span>
                    </h4>
                    <span className="text-[11px] font-mono text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded">
                      Deskewed & Binarized
                    </span>
                  </div>
                  <div className="border-2 border-purple-200 rounded-xl bg-slate-900/5 min-h-[350px] max-h-[450px] flex items-center justify-center p-2 overflow-hidden">
                    <img
                      src={documentService.getPreprocessedImageUrl(selectedDocForComparison.document_id)}
                      alt="Preprocessed Output"
                      className="max-h-[420px] max-w-full object-contain rounded shadow-xs"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-between">
              <span className="text-xs text-slate-500">
                Engine: <strong>OpenCVDocumentPreprocessor v1.0.0-opencv</strong>
              </span>
              <button
                type="button"
                onClick={() => setSelectedDocForComparison(null)}
                className="px-4 py-2 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800 transition"
              >
                Close Visual Scrutiny
              </button>
            </div>
          </div>
        </div>
      )}

      {/* OCR Inspection & Bounding Box Visualizer Modal */}
      {selectedDocForOCR && selectedDocForOCR.document_id && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-6xl w-full max-h-[92vh] flex flex-col overflow-hidden border border-slate-200">
            <div className="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between bg-indigo-50/50">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="px-2.5 py-0.5 bg-indigo-100 text-indigo-800 text-xs font-bold rounded-full flex items-center space-x-1">
                    <ScanText className="w-3.5 h-3.5" />
                    <span>Phase 4C OCR Layout & Scrutiny Visualizer</span>
                  </span>
                  <span className="text-xs text-slate-500 font-mono">
                    {selectedDocForOCR.code}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-slate-900 mt-1">
                  {selectedDocForOCR.name} — Recognized Text & Bounding Boxes
                </h3>
              </div>
              <button
                onClick={() => setSelectedDocForOCR(null)}
                className="p-2 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 sm:p-6 overflow-y-auto space-y-6">
              {/* Mandatory Disclaimer */}
              <div className="p-3.5 bg-amber-50/80 border border-amber-200 rounded-xl text-xs text-amber-950 flex items-start space-x-2">
                <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <strong>AI/OCR Extracted Text Notice:</strong> Machine-readable text and bounding box layouts are extracted automatically from the preprocessed document image. 
                  <span className="font-semibold block mt-0.5 text-amber-900">
                    AI/OCR extracted text requires human verification. Raw text is not verification and does not approve admission.
                  </span>
                </div>
              </div>

              {loadingOCR ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400">
                  <RefreshCw className="w-8 h-8 animate-spin text-indigo-600 mb-2" />
                  <p className="text-sm font-medium">Loading OCR extraction data...</p>
                </div>
              ) : ocrData ? (
                <div className="space-y-6">
                  {/* Metadata Chips Bar */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs">
                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">OCR Engine</span>
                      <span className="font-mono font-bold text-slate-800">
                        {ocrData.engine_name} <span className="text-slate-400">v{ocrData.engine_version}</span>
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">Language & Time</span>
                      <span className="font-semibold text-slate-800">
                        {ocrData.language.toUpperCase()} • {ocrData.processing_time_ms || 0} ms
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">OCR Confidence (Avg)</span>
                      <span className="font-bold text-indigo-700">
                        {ocrData.ocr_confidence !== null && ocrData.ocr_confidence !== undefined
                          ? `${(ocrData.ocr_confidence * 100).toFixed(1)}%`
                          : 'N/A'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">Image SHA-256</span>
                      <span className="font-mono text-[11px] text-slate-600 truncate block" title={ocrData.image_sha256}>
                        {ocrData.image_sha256.substring(0, 12)}...
                      </span>
                    </div>
                  </div>

                  {/* Visualizer & Text Split */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Bounding Box Visualizer Canvas */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center space-x-1.5">
                          <ScanText className="w-3.5 h-3.5 text-indigo-600" />
                          <span>Preprocessed Image with Bounding Boxes</span>
                        </h4>
                        <span className="text-[11px] font-mono text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded font-bold">
                          {ocrData.blocks.length} Blocks Detected
                        </span>
                      </div>
                      <div className="relative border-2 border-indigo-200 rounded-xl bg-slate-900/5 min-h-[380px] max-h-[480px] flex items-center justify-center p-2 overflow-hidden group">
                        <div className="relative inline-block max-h-[450px] max-w-full">
                          <img
                            src={documentService.getPreprocessedImageUrl(selectedDocForOCR.document_id)}
                            alt="Preprocessed OCR Target"
                            className="max-h-[450px] max-w-full object-contain rounded select-none"
                            onLoad={(e) => {
                              setImgNaturalDims({
                                width: e.currentTarget.naturalWidth || 800,
                                height: e.currentTarget.naturalHeight || 600,
                              });
                            }}
                          />
                          {/* SVG Coordinate Overlay */}
                          <svg
                            viewBox={`0 0 ${imgNaturalDims.width} ${imgNaturalDims.height}`}
                            className="absolute inset-0 w-full h-full pointer-events-auto"
                            style={{ overflow: 'visible' }}
                          >
                            {ocrData.blocks.map((b, idx) => {
                              const isHovered = hoveredBlockIdx === idx;
                              return (
                                <g key={idx} onMouseEnter={() => setHoveredBlockIdx(idx)} onMouseLeave={() => setHoveredBlockIdx(null)}>
                                  <rect
                                    x={b.bounding_box.x}
                                    y={b.bounding_box.y}
                                    width={b.bounding_box.width}
                                    height={b.bounding_box.height}
                                    fill={isHovered ? 'rgba(79, 70, 229, 0.35)' : 'rgba(99, 102, 241, 0.15)'}
                                    stroke={isHovered ? '#4338ca' : '#6366f1'}
                                    strokeWidth={isHovered ? 3 : 1.5}
                                    className="cursor-pointer transition"
                                  >
                                    <title>{`${b.text} (${((b.confidence || 0) * 100).toFixed(0)}%)`}</title>
                                  </rect>
                                </g>
                              );
                            })}
                          </svg>
                        </div>
                      </div>
                      <p className="text-[11px] text-slate-400 italic">
                        Coordinates mapped strictly to preprocessed image dimensions (top-left 0,0 origin). Hover over boxes to see extracted words.
                      </p>
                    </div>

                    {/* Extracted Text Monospace Panel */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center space-x-1.5">
                          <FileText className="w-3.5 h-3.5 text-slate-500" />
                          <span>Raw Extracted Text</span>
                        </h4>
                        <button
                          type="button"
                          onClick={handleCopyOCRText}
                          className="px-2.5 py-1 bg-white hover:bg-slate-100 border border-slate-200 rounded text-xs font-semibold text-slate-700 flex items-center space-x-1"
                        >
                          {copiedText ? (
                            <>
                              <Check className="w-3 h-3 text-emerald-600" />
                              <span className="text-emerald-700">Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3 text-slate-500" />
                              <span>Copy Text</span>
                            </>
                          )}
                        </button>
                      </div>
                      <div className="border border-slate-200 rounded-xl bg-slate-900 text-emerald-400 font-mono text-xs p-4 min-h-[380px] max-h-[480px] overflow-y-auto whitespace-pre-wrap leading-relaxed shadow-inner">
                        {ocrData.full_text || (
                          <span className="text-slate-500 italic">
                            [OCR completed successfully but no readable text was detected in the preprocessed image.]
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-400 italic">
                        Raw OCR output stream for verification scrutiny. Field extraction belongs to subsequent Phase 4D.
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-slate-500 text-sm">
                  <AlertCircle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
                  <p>No OCR result found for this document. Please trigger OCR extraction first.</p>
                </div>
              )}
            </div>

            <div className="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-between">
              <span className="text-xs text-slate-500">
                Phase 4C • <strong>Machine-Readable Text & Coordinate Abstraction</strong>
              </span>
              <button
                type="button"
                onClick={() => setSelectedDocForOCR(null)}
                className="px-4 py-2 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800 transition"
              >
                Close OCR Scrutiny
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Structured Field Extraction Scrutiny Modal (Phase 4D) */}
      {selectedDocForExtraction && selectedDocForExtraction.document_id && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-6xl w-full max-h-[92vh] flex flex-col overflow-hidden border border-slate-200">
            {/* Modal Header */}
            <div className="p-4 sm:p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="px-2.5 py-0.5 bg-purple-100 text-purple-800 text-xs font-bold rounded-full flex items-center space-x-1">
                    <TableProperties className="w-3.5 h-3.5" />
                    <span>Phase 4D Structured Extraction Scrutiny</span>
                  </span>
                  <span className="text-xs text-slate-500 font-mono">
                    {selectedDocForExtraction.code}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-slate-900 mt-1">
                  {selectedDocForExtraction.name} — Extracted Fields & Provenance
                </h3>
              </div>
              <button
                onClick={() => {
                  setSelectedDocForExtraction(null);
                  setSelectedFieldForHighlight(null);
                }}
                className="p-2 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-4 sm:p-6 overflow-y-auto space-y-6">
              {/* Mandatory Scrutiny Disclaimer Banner */}
              <div className="p-4 bg-amber-50/90 border border-amber-300 rounded-xl text-xs text-amber-950 flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <strong className="text-amber-900 font-bold block text-sm">
                    Machine-Assisted Suggestions Disclaimer
                  </strong>
                  <p className="text-amber-900 leading-relaxed font-medium">
                    "Extracted fields are machine-assisted suggestions. Human verifiers must cross-verify against the official original document."
                  </p>
                  <p className="text-[11px] text-amber-800 italic">
                    Deterministic field extraction runs on OCR tokens. Confidence values are heuristic scores (0.6 × OCR word confidence + 0.4 × pattern certainty), NOT probabilities or authenticity verification.
                  </p>
                </div>
              </div>

              {loadingExtraction ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400">
                  <RefreshCw className="w-8 h-8 animate-spin text-purple-600 mb-2" />
                  <p className="text-sm font-medium">Loading structured field extraction data...</p>
                </div>
              ) : extractionData ? (
                <div className="space-y-6">
                  {/* Metadata Chips Bar */}
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs">
                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">Extractor Module</span>
                      <span className="font-mono font-bold text-slate-800">
                        {extractionData.extractor_name}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">Document Type</span>
                      <span className="font-bold text-slate-800">
                        {extractionData.document_type}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">Overall Heuristic Score</span>
                      <span className="font-bold text-purple-700">
                        {extractionData.overall_confidence !== null && extractionData.overall_confidence !== undefined
                          ? `${(extractionData.overall_confidence * 100).toFixed(1)}%`
                          : 'N/A'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">Fields Detected</span>
                      <span className="font-semibold text-slate-800">
                        {Object.keys(extractionData.fields || {}).length} Fields
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">Processing Time</span>
                      <span className="font-semibold text-slate-800">
                        {extractionData.processing_time_ms || 0} ms
                      </span>
                    </div>
                  </div>

                  {/* Calculated Cutoff Marks Card (12th Marksheet Special Derived Value) */}
                  {extractionData.calculated_fields?.calculated_cutoff_marks && (
                    <div className="p-4 bg-gradient-to-r from-indigo-50 via-purple-50 to-pink-50 border-2 border-indigo-200 rounded-2xl shadow-xs">
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center space-x-2">
                            <span className="px-2.5 py-0.5 bg-indigo-600 text-white text-[11px] font-bold rounded-full uppercase tracking-wider">
                              Deterministic Derived Value
                            </span>
                            <span className="text-xs font-semibold text-indigo-900">
                              Calculated Cutoff Marks
                            </span>
                          </div>
                          <p className="text-2xl font-black font-mono text-indigo-950">
                            {extractionData.calculated_fields.calculated_cutoff_marks.normalized_value} / 200
                          </p>
                          <p className="text-xs text-slate-600 font-mono">
                            Formula: round(Maths + Physics / 2.0 + Chemistry / 2.0, 2)
                          </p>
                        </div>
                        <div className="md:max-w-md p-3 bg-white/80 rounded-xl border border-indigo-100 text-[11px] text-slate-600">
                          <p className="font-semibold text-indigo-900 flex items-center space-x-1 mb-0.5">
                            <Info className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                            <span>Mandatory Derived Disclaimer:</span>
                          </p>
                          <p className="italic">
                            "This is a deterministic derived value calculated from extracted subject marks. It is NOT a verification result."
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Two-Column Scrutiny Layout */}
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    {/* Left Column: Image Canvas with Field Bounding Box Overlay */}
                    <div className="lg:col-span-5 space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center space-x-1.5">
                          <ScanText className="w-3.5 h-3.5 text-purple-600" />
                          <span>Preprocessed Coordinate Overlay</span>
                        </h4>
                        {selectedFieldForHighlight && (
                          <span className="text-[10px] bg-purple-100 text-purple-800 font-bold px-2 py-0.5 rounded">
                            {selectedFieldForHighlight.field_name}
                          </span>
                        )}
                      </div>
                      <div className="relative border-2 border-purple-200 rounded-xl bg-slate-900/5 min-h-[380px] max-h-[500px] flex items-center justify-center p-2 overflow-hidden group">
                        <div className="relative inline-block max-h-[470px] max-w-full">
                          <img
                            src={documentService.getPreprocessedImageUrl(selectedDocForExtraction.document_id)}
                            alt="Preprocessed Extraction Target"
                            className="max-h-[470px] max-w-full object-contain rounded select-none"
                            onLoad={(e) => {
                              setExtractionImgDims({
                                width: e.currentTarget.naturalWidth || 800,
                                height: e.currentTarget.naturalHeight || 600,
                              });
                            }}
                          />
                          {/* SVG Overlay for Extracted Fields */}
                          <svg
                            viewBox={`0 0 ${extractionImgDims.width} ${extractionImgDims.height}`}
                            className="absolute inset-0 w-full h-full pointer-events-auto"
                            style={{ overflow: 'visible' }}
                          >
                            {Object.values(extractionData.fields || {}).map((field, idx) => {
                              const bbox = field.provenance?.bounding_box;
                              if (!bbox) return null;
                              const isSelected = selectedFieldForHighlight?.field_name === field.field_name;
                              return (
                                <g
                                  key={idx}
                                  onClick={() => setSelectedFieldForHighlight(field)}
                                  className="cursor-pointer"
                                >
                                  <rect
                                    x={bbox.x}
                                    y={bbox.y}
                                    width={bbox.width}
                                    height={bbox.height}
                                    fill={isSelected ? 'rgba(147, 51, 234, 0.45)' : 'rgba(168, 85, 247, 0.2)'}
                                    stroke={isSelected ? '#7e22ce' : '#a855f7'}
                                    strokeWidth={isSelected ? 3.5 : 1.5}
                                    className="transition"
                                  >
                                    <title>{`${field.field_name}: ${field.normalized_value || field.raw_value || 'None'}`}</title>
                                  </rect>
                                </g>
                              );
                            })}
                          </svg>
                        </div>
                      </div>
                      <p className="text-[11px] text-slate-400 italic">
                        Click on any field row on the right to highlight its bounding box on the preprocessed image.
                      </p>
                    </div>

                    {/* Right Column: Structured Extracted Fields Table */}
                    <div className="lg:col-span-7 space-y-3">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center space-x-1.5">
                          <TableProperties className="w-3.5 h-3.5 text-purple-600" />
                          <span>Extracted Fields Scrutiny</span>
                        </h4>
                        <span className="text-[11px] text-slate-500">
                          {Object.values(extractionData.fields || {}).filter((f) => f.requires_review).length} marked for review
                        </span>
                      </div>

                      <div className="border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100 max-h-[500px] overflow-y-auto bg-white shadow-xs">
                        {Object.values(extractionData.fields || {}).map((field) => {
                          const isSelected = selectedFieldForHighlight?.field_name === field.field_name;
                          return (
                            <div
                              key={field.field_name}
                              onClick={() => setSelectedFieldForHighlight(field)}
                              className={`p-3.5 transition cursor-pointer ${
                                isSelected
                                  ? 'bg-purple-50/90 border-l-4 border-l-purple-600'
                                  : 'hover:bg-slate-50/80'
                              }`}
                            >
                              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                <div className="space-y-0.5">
                                  <div className="flex items-center space-x-2">
                                    <span className="text-xs font-bold text-slate-900">
                                      {field.field_name.replace(/_/g, ' ').toUpperCase()}
                                    </span>
                                    {field.is_derived && (
                                      <span className="px-1.5 py-0.2 bg-blue-50 text-blue-700 text-[10px] font-bold rounded">
                                        DERIVED
                                      </span>
                                    )}
                                    {field.requires_review && (
                                      <span className="px-2 py-0.5 bg-amber-100 text-amber-800 text-[10px] font-bold rounded-full flex items-center space-x-1">
                                        <AlertTriangle className="w-2.5 h-2.5" />
                                        <span>Review Needed</span>
                                      </span>
                                    )}
                                  </div>

                                  {/* Normalized Value */}
                                  <div className="flex items-baseline space-x-2">
                                    <span className="text-xs text-slate-400">Normalized:</span>
                                    {field.normalized_value !== null && field.normalized_value !== undefined ? (
                                      <span className="text-sm font-bold text-slate-900 font-mono">
                                        {String(field.normalized_value)}
                                      </span>
                                    ) : (
                                      <span className="text-xs font-semibold text-rose-600 italic">
                                        [null — Value not detected or ambiguous]
                                      </span>
                                    )}
                                  </div>

                                  {/* Raw OCR Value */}
                                  <div className="flex items-baseline space-x-2 text-[11px]">
                                    <span className="text-slate-400">Raw OCR:</span>
                                    <span className="font-mono text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">
                                      {field.raw_value || 'None'}
                                    </span>
                                  </div>
                                </div>

                                {/* Heuristic Confidence Score */}
                                <div className="text-right sm:self-center shrink-0">
                                  <span className="text-[10px] uppercase font-bold text-slate-400 block">
                                    Heuristic Score
                                  </span>
                                  <span className="text-xs font-bold text-purple-700">
                                    {(field.confidence * 100).toFixed(0)}%
                                  </span>
                                </div>
                              </div>

                              {/* Review Reason Alert if flag set */}
                              {field.requires_review && field.review_reason && (
                                <div className="mt-2 p-2 bg-amber-50/70 border border-amber-200 rounded-lg text-[11px] text-amber-900">
                                  <strong>Scrutiny Notice:</strong> {field.review_reason}
                                </div>
                              )}

                              {/* Provenance Drawer / Collapsible Info */}
                              {field.provenance && (
                                <div className="mt-2 pt-2 border-t border-slate-100 text-[10px] text-slate-500 font-mono space-y-0.5">
                                  {field.provenance.context && (
                                    <p className="truncate" title={field.provenance.context}>
                                      <span className="text-slate-400">Context:</span> "{field.provenance.context}"
                                    </p>
                                  )}
                                  {field.provenance.bounding_box && (
                                    <p>
                                      <span className="text-slate-400">Box (x,y,w,h):</span> [{field.provenance.bounding_box.x}, {field.provenance.bounding_box.y}, {field.provenance.bounding_box.width}, {field.provenance.bounding_box.height}]
                                    </p>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-slate-500 text-sm">
                  <AlertCircle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
                  <p>No structured field extraction data found. Please trigger field extraction.</p>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-500">
                  Phase 4D • <strong>Structured Deterministic Field Extraction</strong>
                </span>
                {selectedDocForExtraction && selectedDocForExtraction.document_id && (
                  <button
                    type="button"
                    onClick={() => handleAdminTriggerExtraction(selectedDocForExtraction.document_id!)}
                    disabled={processingDocId === selectedDocForExtraction.document_id}
                    className="px-3 py-1 bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200 rounded-lg text-xs font-semibold transition inline-flex items-center space-x-1"
                  >
                    <RefreshCw className={`w-3 h-3 ${processingDocId === selectedDocForExtraction.document_id ? 'animate-spin' : ''}`} />
                    <span>{processingDocId === selectedDocForExtraction.document_id ? 'Extracting...' : 'Re-run Extraction'}</span>
                  </button>
                )}
              </div>
              <button
                type="button"
                onClick={() => {
                  setSelectedDocForExtraction(null);
                  setSelectedFieldForHighlight(null);
                }}
                className="px-4 py-2 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800 transition"
              >
                Close Scrutiny
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 1. Request Candidate Correction Modal */}
      {showCorrectionModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-xl w-full flex flex-col overflow-hidden border border-slate-200">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-amber-50/50">
              <div className="flex items-center space-x-2">
                <span className="p-2 bg-amber-100 text-amber-800 rounded-xl">
                  <FileWarning className="w-5 h-5" />
                </span>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Request Candidate Correction
                  </h3>
                  <p className="text-xs text-slate-500">
                    Issue actionable guidance for candidate to re-upload or rectify information.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowCorrectionModal(false)}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 text-xs">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Correction Reason (Mandatory)
                </label>
                <select
                  value={correctionReason}
                  onChange={(e) => setCorrectionReason(e.target.value as CorrectionReason)}
                  className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-slate-800 font-medium focus:ring-2 focus:ring-indigo-500 text-xs"
                >
                  <option value="MISSING_DOCUMENT">Missing Document</option>
                  <option value="ILLEGIBLE_DOCUMENT">Illegible / Corrupted Document</option>
                  <option value="FIELD_MISMATCH">Field Value Mismatch</option>
                  <option value="INCORRECT_INFORMATION">Incorrect Information Declared</option>
                  <option value="WRONG_DOCUMENT_TYPE">Wrong Document Type Uploaded</option>
                  <option value="EXPIRED_OR_OUTDATED_DOCUMENT">Expired or Outdated Document</option>
                  <option value="ADDITIONAL_INFORMATION_REQUIRED">Additional Information Required</option>
                  <option value="OTHER">Other Reason (Specific Instructions Mandatory)</option>
                </select>
              </div>

              {/* Flagged Document Selection */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Select Document(s) Requiring Replacement Upload
                </label>
                <div className="space-y-1.5 max-h-36 overflow-y-auto p-2.5 bg-slate-50 border border-slate-200 rounded-xl">
                  {appData.checklist.map((doc) => (
                    <label key={doc.document_type_id} className="flex items-center space-x-2 text-xs text-slate-700 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={doc.document_id ? flaggedDocIds.includes(doc.document_id) : false}
                        onChange={(e) => {
                          if (!doc.document_id) return;
                          if (e.target.checked) {
                            setFlaggedDocIds([...flaggedDocIds, doc.document_id]);
                          } else {
                            setFlaggedDocIds(flaggedDocIds.filter(id => id !== doc.document_id));
                          }
                        }}
                        disabled={!doc.document_id}
                        className="rounded text-indigo-600 focus:ring-indigo-500"
                      />
                      <span>{doc.name}</span>
                      {doc.active_version && (
                        <span className="text-[10px] text-slate-400 font-mono">(v{doc.active_version})</span>
                      )}
                    </label>
                  ))}
                </div>
              </div>

              {/* Actionable Instructions */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Reviewer Instructions to Candidate {correctionReason === 'OTHER' && <span className="text-rose-600 font-bold">*Required</span>}
                </label>
                <textarea
                  rows={3}
                  value={correctionInstructions}
                  onChange={(e) => setCorrectionInstructions(e.target.value)}
                  placeholder="Clearly describe the discrepancy and exact steps the student should follow to correct it..."
                  className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-slate-800 text-xs focus:ring-2 focus:ring-indigo-500 font-sans"
                />
              </div>
            </div>

            <div className="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-end space-x-2">
              <button
                type="button"
                onClick={() => setShowCorrectionModal(false)}
                className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold rounded-xl text-xs transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmitCorrection}
                disabled={submittingCorrection}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded-xl text-xs transition inline-flex items-center space-x-1.5"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{submittingCorrection ? 'Submitting...' : 'Send Correction Request'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 2. Complete Scrutiny Verification Modal */}
      {showCompleteModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full flex flex-col overflow-hidden border border-slate-200">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-emerald-50/50">
              <div className="flex items-center space-x-2">
                <span className="p-2 bg-emerald-100 text-emerald-800 rounded-xl">
                  <CheckCheck className="w-5 h-5" />
                </span>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Complete Scrutiny Decision
                  </h3>
                  <p className="text-xs text-slate-500">
                    Record final human admission verification determination.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowCompleteModal(false)}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 text-xs">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Determination Decision
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setCompleteDecision('VERIFIED')}
                    className={`p-3 rounded-xl border text-center font-bold text-xs transition ${
                      completeDecision === 'VERIFIED'
                        ? 'bg-emerald-50 border-emerald-500 text-emerald-800 shadow-sm'
                        : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    VERIFIED
                  </button>
                  <button
                    type="button"
                    onClick={() => setCompleteDecision('CORRECTION_REQUIRED')}
                    className={`p-3 rounded-xl border text-center font-bold text-xs transition ${
                      completeDecision === 'CORRECTION_REQUIRED'
                        ? 'bg-amber-50 border-amber-500 text-amber-800 shadow-sm'
                        : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    CORRECTION
                  </button>
                  <button
                    type="button"
                    onClick={() => setCompleteDecision('REJECTED')}
                    className={`p-3 rounded-xl border text-center font-bold text-xs transition ${
                      completeDecision === 'REJECTED'
                        ? 'bg-rose-50 border-rose-500 text-rose-800 shadow-sm'
                        : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    REJECTED
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Reviewer Notes / Verification Comments
                </label>
                <textarea
                  rows={3}
                  value={completeComments}
                  onChange={(e) => setCompleteComments(e.target.value)}
                  placeholder="Record summary observations, document verifications, or justification remarks..."
                  className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-slate-800 text-xs focus:ring-2 focus:ring-indigo-500 font-sans"
                />
              </div>
            </div>

            <div className="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-end space-x-2">
              <button
                type="button"
                onClick={() => setShowCompleteModal(false)}
                className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold rounded-xl text-xs transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmitComplete}
                disabled={submittingComplete}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-xs transition inline-flex items-center space-x-1.5"
              >
                <Check className="w-3.5 h-3.5" />
                <span>{submittingComplete ? 'Saving...' : 'Finalize Scrutiny Decision'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. Reopen Review Modal */}
      {showReopenModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full flex flex-col overflow-hidden border border-slate-200">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-indigo-50/50">
              <div className="flex items-center space-x-2">
                <span className="p-2 bg-indigo-100 text-indigo-800 rounded-xl">
                  <RotateCcw className="w-5 h-5" />
                </span>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Reopen Scrutiny Review
                  </h3>
                  <p className="text-xs text-slate-500">
                    Authorized for Admission Head and Super Admin only.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowReopenModal(false)}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 space-y-3 text-xs">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                Reopening Justification (Mandatory)
              </label>
              <textarea
                rows={3}
                value={reopenReason}
                onChange={(e) => setReopenReason(e.target.value)}
                placeholder="State the administrative reason or newly available document evidence requiring scrutiny reopening..."
                className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-slate-800 text-xs focus:ring-2 focus:ring-indigo-500 font-sans"
              />
            </div>

            <div className="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-end space-x-2">
              <button
                type="button"
                onClick={() => setShowReopenModal(false)}
                className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold rounded-xl text-xs transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmitReopen}
                disabled={submittingReopen}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl text-xs transition inline-flex items-center space-x-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>{submittingReopen ? 'Reopening...' : 'Confirm Reopen'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};


