import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  User,
  MapPin,
  Users,
  GraduationCap,
  Upload,
  CheckCircle2,
  AlertCircle,
  Save,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
  ShieldCheck,
  FileCheck,
  History,
  Eye,
  AlertTriangle,
  Sparkles,
  GitCompare
} from 'lucide-react';
import { applicationService } from '../services/application';
import { documentService } from '../services/document';
import { ApplicationDetail, ApplicationDraft, ApplicationCompletion, ChecklistItem, DocumentVersion, CrossDocumentReconciliation } from '../types';

export const StudentApplicationWizard: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  
  // Data state
  const [appData, setAppData] = useState<ApplicationDetail | null>(null);
  const [formData, setFormData] = useState<ApplicationDraft>({});
  const [completion, setCompletion] = useState<ApplicationCompletion | null>(null);
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [processingDocId, setProcessingDocId] = useState<string | null>(null);

  // Version modal state
  const [selectedDocForVersions, setSelectedDocForVersions] = useState<ChecklistItem | null>(null);
  const [docVersions, setDocVersions] = useState<DocumentVersion[]>([]);
  const [loadingVersions, setLoadingVersions] = useState<boolean>(false);

  // Phase 4E Student Reconciliation state
  const [studentRecon, setStudentRecon] = useState<CrossDocumentReconciliation | null>(null);
  const [runningStudentRecon, setRunningStudentRecon] = useState<boolean>(false);

  const handleRunStudentReconciliation = async () => {
    try {
      setRunningStudentRecon(true);
      setErrorMsg(null);
      // Save draft first
      await applicationService.updateDraft(formData);
      const recon = await applicationService.runMyReconciliation();
      setStudentRecon(recon);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to run consistency pre-check');
    } finally {
      setRunningStudentRecon(false);
    }
  };

  // Uploading state per document type
  const [uploadingCode, setUploadingCode] = useState<string | null>(null);

  const loadApplication = useCallback(async () => {
    try {
      setLoading(true);
      const data = await applicationService.getMyApplication();
      
      // If already submitted, redirect to submitted view
      if (['APPLICATION_SUBMITTED', 'DOCUMENT_REVIEW', 'DOCUMENTS_VERIFIED', 'ADMISSION_CONFIRMED', 'ACTIVE_STUDENT'].includes(data.status)) {
        navigate('/application/status');
        return;
      }

      setAppData(data);
      setChecklist(data.checklist || []);
      setFormData({
        gender: data.gender || 'Male',
        blood_group: data.blood_group || 'O+ve',
        nationality: data.nationality || 'Indian',
        religion: data.religion || 'Hindu',
        caste: data.caste || data.community || '',
        mother_tongue: data.mother_tongue || 'Tamil',
        aadhaar_number: data.aadhaar_number || '',
        
        address_line1: data.address_line1 || '',
        address_line2: data.address_line2 || '',
        city: data.city || '',
        district: data.district || '',
        state: data.state || 'Tamil Nadu',
        pincode: data.pincode || '',
        emergency_contact_name: data.emergency_contact_name || '',
        emergency_contact_phone: data.emergency_contact_phone || '',
        emergency_contact_relation: data.emergency_contact_relation || 'Father',
        
        father_name: data.father_name || '',
        father_occupation: data.father_occupation || '',
        father_mobile: data.father_mobile || '',
        father_email: data.father_email || '',
        mother_name: data.mother_name || '',
        mother_occupation: data.mother_occupation || '',
        mother_mobile: data.mother_mobile || '',
        mother_email: data.mother_email || '',
        guardian_name: data.guardian_name || '',
        guardian_occupation: data.guardian_occupation || '',
        guardian_mobile: data.guardian_mobile || '',
        guardian_relation: data.guardian_relation || '',
        annual_family_income: data.annual_family_income || undefined,
        
        tenth_school_name: data.tenth_school_name || '',
        tenth_board: data.tenth_board || 'State Board',
        tenth_year_of_passing: data.tenth_year_of_passing || 2024,
        tenth_registration_number: data.tenth_registration_number || '',
        tenth_total_marks: data.tenth_total_marks || undefined,
        tenth_max_marks: data.tenth_max_marks || 500,
        tenth_percentage: data.tenth_percentage || undefined,
        
        twelfth_school_name: data.twelfth_school_name || '',
        twelfth_board: data.twelfth_board || 'State Board',
        twelfth_year_of_passing: data.twelfth_year_of_passing || 2026,
        twelfth_registration_number: data.twelfth_registration_number || '',
        twelfth_total_marks: data.twelfth_total_marks || undefined,
        twelfth_max_marks: data.twelfth_max_marks || 600,
        twelfth_percentage: data.twelfth_percentage || undefined,
        twelfth_maths_marks: data.twelfth_maths_marks || undefined,
        twelfth_physics_marks: data.twelfth_physics_marks || undefined,
        twelfth_chemistry_marks: data.twelfth_chemistry_marks || undefined,
        twelfth_cutoff_marks: data.twelfth_cutoff_marks || undefined,
        
        is_first_graduate: data.is_first_graduate,
        is_pmss_scholarship: data.is_pmss_scholarship,
        is_7_5_govt_quota: data.is_7_5_govt_quota,
        is_hostel_required: data.is_hostel_required,
        is_transport_required: data.is_transport_required,
        declaration_accepted: data.declaration_accepted,
      });

      const comp = await applicationService.getCompletion();
      setCompletion(comp);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to load application');
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    loadApplication();
  }, [loadApplication]);

  const handleInputChange = (field: keyof ApplicationDraft, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const calculateCutoff = () => {
    const m = Number(formData.twelfth_maths_marks || 0);
    const p = Number(formData.twelfth_physics_marks || 0);
    const c = Number(formData.twelfth_chemistry_marks || 0);
    if (m > 0 && p > 0 && c > 0) {
      // TNEA Cutoff standard: Maths + (Physics/2) + (Chemistry/2) = 200 Max
      const cutoff = Number((m + (p / 2) + (c / 2)).toFixed(2));
      handleInputChange('twelfth_cutoff_marks', cutoff);
    }
  };

  const handleSaveDraft = async () => {
    try {
      setSaving(true);
      setErrorMsg(null);
      const updated = await applicationService.updateDraft(formData);
      setAppData(updated);
      setChecklist(updated.checklist || []);
      const comp = await applicationService.getCompletion();
      setCompletion(comp);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to save draft');
    } finally {
      setSaving(false);
    }
  };

  const handleFileUpload = async (code: string, file: File) => {
    try {
      setUploadingCode(code);
      setErrorMsg(null);
      const res = await documentService.uploadDocument(code, file);
      // Automatically trigger prototype AI classification & preprocessing
      if (res.document_id) {
        try {
          await documentService.processDocument(res.document_id);
          await documentService.preprocessDocument(res.document_id);
        } catch {
          // Non-blocking assistive processing
        }
      }
      // Refresh checklist & completion
      const updatedList = await applicationService.getChecklist();
      setChecklist(updatedList);
      const comp = await applicationService.getCompletion();
      setCompletion(comp);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || `Failed to upload document for ${code}`);
    } finally {
      setUploadingCode(null);
    }
  };

  const handleProcessDocument = async (documentId: string) => {
    try {
      setProcessingDocId(documentId);
      await documentService.processDocument(documentId, true);
      const updatedList = await applicationService.getChecklist();
      setChecklist(updatedList);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to trigger prototype AI document processing');
    } finally {
      setProcessingDocId(null);
    }
  };

  const handlePreprocessDocument = async (documentId: string) => {
    try {
      setProcessingDocId(documentId);
      await documentService.preprocessDocument(documentId);
      const updatedList = await applicationService.getChecklist();
      setChecklist(updatedList);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to trigger OpenCV image preprocessing');
    } finally {
      setProcessingDocId(null);
    }
  };

  const handleViewVersions = async (item: ChecklistItem) => {
    if (!item.document_id) return;
    try {
      setSelectedDocForVersions(item);
      setLoadingVersions(true);
      const vers = await documentService.getDocumentVersions(item.document_id);
      setDocVersions(vers);
    } catch (err: any) {
      setErrorMsg('Failed to load version history');
    } finally {
      setLoadingVersions(false);
    }
  };

  const handleSubmitApplication = async () => {
    if (!formData.declaration_accepted) {
      setErrorMsg('You must agree to the declaration statement before submitting.');
      return;
    }
    try {
      setSubmitting(true);
      setErrorMsg(null);
      // Save draft first
      await applicationService.updateDraft(formData);
      await applicationService.submitApplication(true);
      navigate('/application/status');
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Submission failed. Please verify all mandatory items.');
    } finally {
      setSubmitting(false);
    }
  };

  const steps = [
    { id: 1, title: 'Allotment Info', icon: ShieldCheck, desc: 'Verified TNEA Details' },
    { id: 2, title: 'Personal', icon: User, desc: 'Identity & Nationality' },
    { id: 3, title: 'Address', icon: MapPin, desc: 'Domicile & Contact' },
    { id: 4, title: 'Parent / Family', icon: Users, desc: 'Guardians & Income' },
    { id: 5, title: 'Academic Marks', icon: GraduationCap, desc: '10th & 12th Scores' },
    { id: 6, title: 'Document Checklist', icon: Upload, desc: 'Certificates Upload' },
    { id: 7, title: 'Review & Submit', icon: FileCheck, desc: 'Declaration & Finalize' },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center space-y-3">
          <RefreshCw className="w-8 h-8 animate-spin text-indigo-600" />
          <p className="text-sm font-medium text-slate-600">Loading Admission Application...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-16">
      {/* Top Header Card */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-3">
              <span className="px-3 py-1 bg-indigo-50 text-indigo-700 font-semibold text-xs rounded-full border border-indigo-100 uppercase tracking-wider">
                Academic Year 2026–27
              </span>
              <span className="text-xs font-medium text-slate-500">
                Application No: <strong className="text-slate-800">{appData?.application_number || 'Generating...'}</strong>
              </span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mt-2">
              Online Admission Application Form
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Please complete all 7 sections accurately. Your progress is continuously validated against TNEA guidelines.
            </p>
          </div>

          {/* Completion Meter */}
          <div className="flex items-center space-x-4 bg-slate-50 p-3 rounded-xl border border-slate-200">
            <div className="relative w-12 h-12 flex items-center justify-center">
              <svg className="w-12 h-12 -rotate-90" viewBox="0 0 36 36">
                <path
                  className="text-slate-200"
                  strokeWidth="3.5"
                  stroke="currentColor"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <path
                  className="text-indigo-600 transition-all duration-500"
                  strokeDasharray={`${completion?.overall_percentage || 0}, 100`}
                  strokeWidth="3.5"
                  strokeLinecap="round"
                  stroke="currentColor"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
              </svg>
              <span className="absolute text-xs font-bold text-slate-800">
                {completion?.overall_percentage || 0}%
              </span>
            </div>
            <div>
              <p className="text-xs font-bold text-slate-800 uppercase tracking-wider">Form Completion</p>
              <p className="text-xs text-slate-500">
                {completion?.mandatory_documents_uploaded || 0} of {completion?.mandatory_documents_total || 0} mandatory docs uploaded
              </p>
            </div>
          </div>
        </div>

        {/* Global Save / Feedback Alert */}
        {saveSuccess && (
          <div className="mt-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center space-x-2 text-emerald-800 text-sm">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>Draft saved successfully. Your progress has been updated.</span>
          </div>
        )}

        {errorMsg && (
          <div className="mt-4 p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-center space-x-2 text-rose-800 text-sm">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}
      </div>

      {/* Step Navigation Bar */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200/80 p-2 overflow-x-auto">
        <div className="flex items-center min-w-max space-x-1">
          {steps.map((step) => {
            const Icon = step.icon;
            const isActive = currentStep === step.id;
            const isCompleted = currentStep > step.id;
            return (
              <button
                key={step.id}
                onClick={() => setCurrentStep(step.id)}
                className={`flex items-center space-x-3 px-4 py-2.5 rounded-lg text-left transition-all ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : isCompleted
                    ? 'bg-indigo-50/60 text-indigo-900 hover:bg-indigo-100/60'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                    isActive
                      ? 'bg-white text-indigo-600'
                      : isCompleted
                      ? 'bg-indigo-200 text-indigo-800'
                      : 'bg-slate-200 text-slate-700'
                  }`}
                >
                  {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : <Icon className="w-3.5 h-3.5" />}
                </div>
                <div>
                  <p className="text-xs font-bold leading-none">{step.title}</p>
                  <p className={`text-[10px] mt-0.5 ${isActive ? 'text-indigo-100' : 'text-slate-400'}`}>
                    {step.desc}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Step Content Container */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 md:p-8">
        {/* Step 1: Read-Only TNEA Allotment Summary */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <div className="border-b border-slate-100 pb-4">
              <h2 className="text-lg font-bold text-slate-900">1. TNEA Allotment Provenance & Academic Allocation</h2>
              <p className="text-sm text-slate-500 mt-1">
                These details are officially locked from your Tamil Nadu Engineering Admissions (TNEA 2026) allotment order.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                <p className="text-xs font-medium text-slate-500">Student Full Name</p>
                <p className="text-base font-bold text-slate-900 mt-1">{appData?.student_name}</p>
              </div>
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                <p className="text-xs font-medium text-slate-500">TNEA Application Number</p>
                <p className="text-base font-bold text-indigo-600 font-mono mt-1">{appData?.tnea_application_number}</p>
              </div>
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                <p className="text-xs font-medium text-slate-500">Allotment Order Number</p>
                <p className="text-base font-bold text-slate-900 font-mono mt-1">{appData?.allotment_order_number || `ALT-${appData?.tnea_application_number}`}</p>
              </div>
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                <p className="text-xs font-medium text-slate-500">Allotted College Code & Name</p>
                <p className="text-base font-bold text-slate-900 mt-1">{appData?.allotted_college_code || 'XYZ'} — XYZ Engineering College</p>
              </div>
              <div className="p-4 bg-indigo-50/50 rounded-xl border border-indigo-100">
                <p className="text-xs font-medium text-indigo-600">Allotted Engineering Branch</p>
                <p className="text-base font-bold text-indigo-950 mt-1">{appData?.allotted_branch_name || appData?.allotted_branch}</p>
              </div>
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                <p className="text-xs font-medium text-slate-500">Admission Quota & Community Category</p>
                <p className="text-base font-bold text-slate-900 mt-1">
                  {appData?.allotment_quota || appData?.quota || 'General'} ({appData?.allotted_category || appData?.community || 'OC'})
                </p>
              </div>
            </div>

            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-start space-x-3 text-amber-900 text-sm">
              <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="font-semibold">Read-Only Provenance Lock:</strong>
                <p className="text-xs text-amber-800 mt-0.5">
                  If any branch or allotment mismatch is noticed, contact the Admission Head scrutiny desk immediately before submitting.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Personal & Identity Details */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <div className="border-b border-slate-100 pb-4">
              <h2 className="text-lg font-bold text-slate-900">2. Personal & Identity Details</h2>
              <p className="text-sm text-slate-500 mt-1">Enter demographic and identity details as printed on official records.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Gender *</label>
                <select
                  value={formData.gender || ''}
                  onChange={(e) => handleInputChange('gender', e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Transgender">Transgender</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Blood Group *</label>
                <select
                  value={formData.blood_group || ''}
                  onChange={(e) => handleInputChange('blood_group', e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="O+ve">O +ve</option>
                  <option value="O-ve">O -ve</option>
                  <option value="A+ve">A +ve</option>
                  <option value="A-ve">A -ve</option>
                  <option value="B+ve">B +ve</option>
                  <option value="B-ve">B -ve</option>
                  <option value="AB+ve">AB +ve</option>
                  <option value="AB-ve">AB -ve</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Nationality *</label>
                <input
                  type="text"
                  value={formData.nationality || 'Indian'}
                  onChange={(e) => handleInputChange('nationality', e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Religion *</label>
                <input
                  type="text"
                  placeholder="e.g. Hindu, Islam, Christian"
                  value={formData.religion || ''}
                  onChange={(e) => handleInputChange('religion', e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Community / Caste *</label>
                <input
                  type="text"
                  placeholder="e.g. BC, MBC, SC, OC"
                  value={formData.caste || ''}
                  onChange={(e) => handleInputChange('caste', e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Mother Tongue *</label>
                <input
                  type="text"
                  value={formData.mother_tongue || 'Tamil'}
                  onChange={(e) => handleInputChange('mother_tongue', e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="md:col-span-3">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Aadhaar Card Number * (12 Digits)</label>
                <input
                  type="text"
                  maxLength={19}
                  placeholder="XXXX XXXX XXXX"
                  value={formData.aadhaar_number || ''}
                  onChange={(e) => handleInputChange('aadhaar_number', e.target.value)}
                  className="w-full max-w-md px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm font-mono text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Address & Emergency Contact */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <div className="border-b border-slate-100 pb-4">
              <h2 className="text-lg font-bold text-slate-900">3. Permanent Address & Emergency Contact</h2>
              <p className="text-sm text-slate-500 mt-1">Provide current residential address for official dispatch and campus records.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="md:col-span-2">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Address Line 1 (Door No, Building, Street) *</label>
                <input
                  type="text"
                  placeholder="Door No, Street Name"
                  value={formData.address_line1 || ''}
                  onChange={(e) => handleInputChange('address_line1', e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Address Line 2 (Area, Landmark)</label>
                <input
                  type="text"
                  placeholder="Area / Landmark"
                  value={formData.address_line2 || ''}
                  onChange={(e) => handleInputChange('address_line2', e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">City / Town *</label>
                <input
                  type="text"
                  placeholder="e.g. Chennai, Coimbatore, Madurai"
                  value={formData.city || ''}
                  onChange={(e) => handleInputChange('city', e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">District *</label>
                <input
                  type="text"
                  placeholder="District"
                  value={formData.district || ''}
                  onChange={(e) => handleInputChange('district', e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">State *</label>
                <input
                  type="text"
                  value={formData.state || 'Tamil Nadu'}
                  onChange={(e) => handleInputChange('state', e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">PIN Code *</label>
                <input
                  type="text"
                  maxLength={6}
                  placeholder="600001"
                  value={formData.pincode || ''}
                  onChange={(e) => handleInputChange('pincode', e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm font-mono text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100">
              <h3 className="text-sm font-bold text-slate-800 mb-3">Emergency Contact Details</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Contact Person Name *</label>
                  <input
                    type="text"
                    placeholder="Full Name"
                    value={formData.emergency_contact_name || ''}
                    onChange={(e) => handleInputChange('emergency_contact_name', e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Phone Number *</label>
                  <input
                    type="tel"
                    placeholder="+91 XXXXX XXXXX"
                    value={formData.emergency_contact_phone || ''}
                    onChange={(e) => handleInputChange('emergency_contact_phone', e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Relationship *</label>
                  <select
                    value={formData.emergency_contact_relation || 'Father'}
                    onChange={(e) => handleInputChange('emergency_contact_relation', e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="Father">Father</option>
                    <option value="Mother">Mother</option>
                    <option value="Guardian">Guardian</option>
                    <option value="Sibling">Sibling</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Parent / Guardian & Family Income */}
        {currentStep === 4 && (
          <div className="space-y-6">
            <div className="border-b border-slate-100 pb-4">
              <h2 className="text-lg font-bold text-slate-900">4. Parent / Guardian & Family Income</h2>
              <p className="text-sm text-slate-500 mt-1">Provide family income and parent details (used for scholarship and concession checks).</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Father Details */}
              <div className="space-y-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
                <h3 className="text-xs font-bold text-indigo-900 uppercase tracking-wider">Father's Details</h3>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Father's Name</label>
                  <input
                    type="text"
                    value={formData.father_name || ''}
                    onChange={(e) => handleInputChange('father_name', e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Occupation</label>
                  <input
                    type="text"
                    value={formData.father_occupation || ''}
                    onChange={(e) => handleInputChange('father_occupation', e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Mobile Number</label>
                  <input
                    type="tel"
                    value={formData.father_mobile || ''}
                    onChange={(e) => handleInputChange('father_mobile', e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              {/* Mother Details */}
              <div className="space-y-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
                <h3 className="text-xs font-bold text-indigo-900 uppercase tracking-wider">Mother's Details</h3>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Mother's Name</label>
                  <input
                    type="text"
                    value={formData.mother_name || ''}
                    onChange={(e) => handleInputChange('mother_name', e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Occupation</label>
                  <input
                    type="text"
                    value={formData.mother_occupation || ''}
                    onChange={(e) => handleInputChange('mother_occupation', e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Mobile Number</label>
                  <input
                    type="tel"
                    value={formData.mother_mobile || ''}
                    onChange={(e) => handleInputChange('mother_mobile', e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              {/* Annual Family Income */}
              <div className="md:col-span-2 p-4 bg-indigo-50/40 rounded-xl border border-indigo-100">
                <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider mb-1">
                  Annual Family Income (in INR ₹) *
                </label>
                <p className="text-xs text-slate-500 mb-2">
                  Required for scholarship grants and fee waivers. If ≤ ₹2,50,000, Income Certificate becomes mandatory.
                </p>
                <input
                  type="number"
                  placeholder="e.g. 180000"
                  value={formData.annual_family_income || ''}
                  onChange={(e) => handleInputChange('annual_family_income', Number(e.target.value))}
                  className="w-full max-w-xs px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm font-semibold text-slate-900"
                />
              </div>

              {/* Special Quota Flags */}
              <div className="md:col-span-2 space-y-3">
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Concession & Facility Options</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <label className="flex items-center space-x-3 p-3 bg-slate-50 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-100">
                    <input
                      type="checkbox"
                      checked={formData.is_first_graduate || false}
                      onChange={(e) => handleInputChange('is_first_graduate', e.target.checked)}
                      className="w-4 h-4 text-indigo-600 rounded"
                    />
                    <span className="text-xs font-medium text-slate-800">
                      Availing <strong>First Graduate (FG)</strong> Tuition Fee Concession
                    </span>
                  </label>

                  <label className="flex items-center space-x-3 p-3 bg-slate-50 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-100">
                    <input
                      type="checkbox"
                      checked={formData.is_pmss_scholarship || false}
                      onChange={(e) => handleInputChange('is_pmss_scholarship', e.target.checked)}
                      className="w-4 h-4 text-indigo-600 rounded"
                    />
                    <span className="text-xs font-medium text-slate-800">
                      Availing <strong>Post-Matric / PMSS Scholarship</strong>
                    </span>
                  </label>

                  <label className="flex items-center space-x-3 p-3 bg-slate-50 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-100">
                    <input
                      type="checkbox"
                      checked={formData.is_7_5_govt_quota || false}
                      onChange={(e) => handleInputChange('is_7_5_govt_quota', e.target.checked)}
                      className="w-4 h-4 text-indigo-600 rounded"
                    />
                    <span className="text-xs font-medium text-slate-800">
                      Allotted under <strong>7.5% Govt School Quota</strong>
                    </span>
                  </label>

                  <label className="flex items-center space-x-3 p-3 bg-slate-50 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-100">
                    <input
                      type="checkbox"
                      checked={formData.is_hostel_required || false}
                      onChange={(e) => handleInputChange('is_hostel_required', e.target.checked)}
                      className="w-4 h-4 text-indigo-600 rounded"
                    />
                    <span className="text-xs font-medium text-slate-800">
                      Hostel Accommodation Required
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 5: Academic Qualifications (10th & 12th) */}
        {currentStep === 5 && (
          <div className="space-y-6">
            <div className="border-b border-slate-100 pb-4">
              <h2 className="text-lg font-bold text-slate-900">5. Academic Qualifications & Cutoff Verification</h2>
              <p className="text-sm text-slate-500 mt-1">Enter marks from 10th and 12th standard marksheets accurately.</p>
            </div>

            {/* 10th Standard */}
            <div className="space-y-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
              <h3 className="text-xs font-bold text-indigo-900 uppercase tracking-wider">10th Standard / SSLC Examination</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-slate-600 mb-1">School Name Last Studied *</label>
                  <input
                    type="text"
                    value={formData.tenth_school_name || ''}
                    onChange={(e) => handleInputChange('tenth_school_name', e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Board *</label>
                  <select
                    value={formData.tenth_board || 'State Board'}
                    onChange={(e) => handleInputChange('tenth_board', e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm"
                  >
                    <option value="State Board">Tamil Nadu State Board</option>
                    <option value="CBSE">CBSE</option>
                    <option value="ICSE">ICSE</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Year of Passing *</label>
                  <input
                    type="number"
                    value={formData.tenth_year_of_passing || 2024}
                    onChange={(e) => handleInputChange('tenth_year_of_passing', Number(e.target.value))}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Registration / Roll No *</label>
                  <input
                    type="text"
                    value={formData.tenth_registration_number || ''}
                    onChange={(e) => handleInputChange('tenth_registration_number', e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Total Marks / Max Marks *</label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="number"
                      placeholder="Marks"
                      value={formData.tenth_total_marks || ''}
                      onChange={(e) => handleInputChange('tenth_total_marks', Number(e.target.value))}
                      className="w-1/2 px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm"
                    />
                    <span className="text-slate-400">/</span>
                    <input
                      type="number"
                      value={formData.tenth_max_marks || 500}
                      onChange={(e) => handleInputChange('tenth_max_marks', Number(e.target.value))}
                      className="w-1/2 px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* 12th Standard & Cutoff */}
            <div className="space-y-4 p-4 bg-indigo-50/40 rounded-xl border border-indigo-100">
              <h3 className="text-xs font-bold text-indigo-950 uppercase tracking-wider">12th Standard / HSC Examination & Core Subject Marks</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-slate-600 mb-1">12th School Name *</label>
                  <input
                    type="text"
                    value={formData.twelfth_school_name || ''}
                    onChange={(e) => handleInputChange('twelfth_school_name', e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">12th Registration / Roll No *</label>
                  <input
                    type="text"
                    value={formData.twelfth_registration_number || ''}
                    onChange={(e) => handleInputChange('twelfth_registration_number', e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Mathematics Mark (Max 100) *</label>
                  <input
                    type="number"
                    max={100}
                    placeholder="e.g. 98"
                    value={formData.twelfth_maths_marks || ''}
                    onChange={(e) => {
                      handleInputChange('twelfth_maths_marks', Number(e.target.value));
                    }}
                    onBlur={calculateCutoff}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm font-semibold"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Physics Mark (Max 100) *</label>
                  <input
                    type="number"
                    max={100}
                    placeholder="e.g. 95"
                    value={formData.twelfth_physics_marks || ''}
                    onChange={(e) => {
                      handleInputChange('twelfth_physics_marks', Number(e.target.value));
                    }}
                    onBlur={calculateCutoff}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm font-semibold"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Chemistry Mark (Max 100) *</label>
                  <input
                    type="number"
                    max={100}
                    placeholder="e.g. 96"
                    value={formData.twelfth_chemistry_marks || ''}
                    onChange={(e) => {
                      handleInputChange('twelfth_chemistry_marks', Number(e.target.value));
                    }}
                    onBlur={calculateCutoff}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm font-semibold"
                  />
                </div>

                <div className="md:col-span-3 flex flex-col md:flex-row md:items-center justify-between p-3.5 bg-indigo-600 text-white rounded-xl gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-wider text-indigo-200">Engineering Cutoff Score (out of 200)</p>
                    <p className="text-2xl font-bold font-mono mt-0.5">{formData.twelfth_cutoff_marks || '0.00'}</p>
                    <p className="text-[11px] text-indigo-100">Formula: Maths (100) + Physics (50) + Chemistry (50)</p>
                  </div>
                  <button
                    type="button"
                    onClick={calculateCutoff}
                    className="px-4 py-2 bg-white text-indigo-700 hover:bg-indigo-50 font-bold text-xs rounded-lg transition"
                  >
                    Recalculate Cutoff
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 6: Dynamic Document Checklist */}
        {currentStep === 6 && (
          <div className="space-y-6">
            <div className="border-b border-slate-100 pb-4 flex flex-col md:flex-row md:items-center justify-between gap-2">
              <div>
                <h2 className="text-lg font-bold text-slate-900">6. Dynamic Document Checklist & Uploads</h2>
                <p className="text-sm text-slate-500 mt-1">
                  Certificates tailored to your reservation category, First Graduate claim, and TNEA guidelines.
                </p>
              </div>
              <span className="text-xs bg-slate-100 text-slate-700 px-3 py-1 rounded-full font-medium self-start">
                Allowed formats: PDF, PNG, JPG (Max 5MB each)
              </span>
            </div>

            <div className="space-y-4">
              {checklist.map((item) => {
                const isUploaded = item.document_status !== 'NOT_UPLOADED';
                const isUploading = uploadingCode === item.code;
                return (
                  <div
                    key={item.code}
                    className={`p-4 rounded-xl border transition-all ${
                      isUploaded
                        ? 'bg-emerald-50/40 border-emerald-200'
                        : item.is_mandatory
                        ? 'bg-white border-slate-300'
                        : 'bg-slate-50/50 border-slate-200'
                    }`}
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <h4 className="text-sm font-bold text-slate-900">{item.name}</h4>
                          {item.is_mandatory ? (
                            <span className="px-2 py-0.5 bg-rose-100 text-rose-700 text-[10px] font-bold rounded-full">
                              MANDATORY
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-[10px] font-bold rounded-full">
                              OPTIONAL
                            </span>
                          )}
                          {isUploaded && (
                            <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 text-[10px] font-bold rounded-full flex items-center space-x-1">
                              <CheckCircle2 className="w-3 h-3" />
                              <span>v{item.active_version || 1} UPLOADED</span>
                            </span>
                          )}
                        </div>

                        {item.description && (
                          <p className="text-xs text-slate-500">{item.description}</p>
                        )}
                        {item.mandatory_reason && (
                          <p className="text-[11px] text-indigo-700 font-medium">
                            Rule: {item.mandatory_reason}
                          </p>
                        )}

                        {isUploaded && item.original_filename && (
                          <p className="text-xs font-mono text-slate-700 mt-1">
                            File: <strong>{item.original_filename}</strong> ({((item.file_size_bytes || 0) / 1024).toFixed(1)} KB)
                          </p>
                        )}

                        {/* Prototype AI Classification Status */}
                        {isUploaded && (
                          <div className="mt-2 pt-2 border-t border-slate-200/60">
                            {item.processing_status === 'COMPLETED' ? (
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 text-purple-900 rounded-md text-[11px] font-medium shadow-xs">
                                  <Sparkles className="w-3 h-3 text-purple-600" />
                                  <span>Prototype AI: <strong>{item.predicted_document_type_name || item.predicted_document_type}</strong></span>
                                  <span className="bg-purple-200 text-purple-800 text-[10px] px-1.5 py-0.2 rounded font-bold">
                                    {((item.heuristic_confidence || 0.5) * 100).toFixed(0)}% heuristic
                                  </span>
                                </span>
                                <span className="text-[10px] text-slate-500 italic">
                                  Prototype heuristic result — not verification
                                </span>
                              </div>
                            ) : item.processing_status === 'PROCESSING' || item.processing_status === 'QUEUED' ? (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-medium rounded">
                                <RefreshCw className="w-3 h-3 animate-spin text-blue-600" />
                                <span>AI Classification {item.processing_status === 'QUEUED' ? 'Queued' : 'In Progress'}...</span>
                              </span>
                            ) : item.processing_status === 'FAILED' ? (
                              <div className="flex items-center space-x-2">
                                <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-amber-50 text-amber-800 border border-amber-200 text-[10px] font-medium rounded">
                                  <AlertCircle className="w-3 h-3 text-amber-600" />
                                  <span>AI Processing Retry Recommended</span>
                                </span>
                                {item.document_id && (
                                  <button
                                    type="button"
                                    onClick={() => handleProcessDocument(item.document_id!)}
                                    disabled={processingDocId === item.document_id}
                                    className="text-[11px] text-indigo-600 hover:underline font-semibold"
                                  >
                                    {processingDocId === item.document_id ? 'Retrying...' : 'Retry AI Scan'}
                                  </button>
                                )}
                              </div>
                            ) : (
                              <div className="flex items-center space-x-2">
                                <span className="text-[10px] text-slate-400">AI Classification: Not Processed</span>
                                {item.document_id && (
                                  <button
                                    type="button"
                                    onClick={() => handleProcessDocument(item.document_id!)}
                                    disabled={processingDocId === item.document_id}
                                    className="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold flex items-center space-x-1"
                                  >
                                    <Sparkles className="w-3 h-3" />
                                    <span>{processingDocId === item.document_id ? 'Analyzing...' : 'Run Prototype AI Check'}</span>
                                  </button>
                                )}
                              </div>
                            )}
                            {/* Image Preprocessing Status */}
                            <div className="mt-1.5 flex flex-wrap items-center gap-2">
                              {item.preprocessing_status === 'COMPLETED' ? (
                                <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-medium rounded">
                                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                                  <span>Image Preprocessing: Ready for OCR (Deskewed & Enhanced)</span>
                                </span>
                              ) : item.preprocessing_status === 'PROCESSING' || item.preprocessing_status === 'QUEUED' ? (
                                <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-medium rounded">
                                  <RefreshCw className="w-3 h-3 animate-spin text-blue-600" />
                                  <span>Image Preprocessing in Progress...</span>
                                </span>
                              ) : item.preprocessing_status === 'FAILED' ? (
                                <div className="flex items-center space-x-2">
                                  <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-medium rounded">
                                    <AlertCircle className="w-3 h-3 text-amber-600" />
                                    <span>Image Preprocessing: Failed</span>
                                  </span>
                                  {item.document_id && (
                                    <button
                                      type="button"
                                      onClick={() => handlePreprocessDocument(item.document_id!)}
                                      disabled={processingDocId === item.document_id}
                                      className="text-[11px] text-indigo-600 hover:underline font-semibold"
                                    >
                                      {processingDocId === item.document_id ? 'Retrying...' : 'Retry Preprocessing'}
                                    </button>
                                  )}
                                </div>
                              ) : null}
                            </div>
                            {/* OCR Extraction Status (Non-Technical) */}
                            <div className="mt-1 flex flex-wrap items-center gap-2">
                              {item.ocr_status === 'COMPLETED' ? (
                                <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-indigo-50 text-indigo-700 border border-indigo-200 text-[10px] font-medium rounded">
                                  <FileCheck className="w-3 h-3 text-indigo-600" />
                                  <span>OCR Text Extraction: Completed</span>
                                </span>
                              ) : item.ocr_status === 'PROCESSING' || item.ocr_status === 'QUEUED' ? (
                                <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-medium rounded">
                                  <RefreshCw className="w-3 h-3 animate-spin text-blue-600" />
                                  <span>OCR Processing in Progress...</span>
                                </span>
                              ) : item.ocr_status === 'FAILED' ? (
                                <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-medium rounded">
                                  <AlertCircle className="w-3 h-3 text-amber-600" />
                                  <span>OCR Processing: Failed / Pending Scrutiny</span>
                                </span>
                              ) : item.preprocessing_status === 'COMPLETED' ? (
                                <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-slate-50 text-slate-600 border border-slate-200 text-[10px] font-medium rounded">
                                  <span>OCR Status: Ready for OCR Extraction</span>
                                </span>
                              ) : null}
                            </div>
                            {/* Structured Field Extraction Status */}
                            {item.extraction_status === 'COMPLETED' && (
                              <div className="mt-1 flex flex-wrap items-center gap-2">
                                <span className="inline-flex items-center space-x-1 px-2 py-0.5 bg-purple-50 text-purple-700 border border-purple-200 text-[10px] font-medium rounded">
                                  <Sparkles className="w-3 h-3 text-purple-600" />
                                  <span>Structured Field Extraction: Completed</span>
                                </span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Upload and actions */}
                      <div className="flex items-center space-x-2 self-start md:self-center">
                        {isUploaded && item.document_id && (
                          <>
                            <button
                              type="button"
                              onClick={() => handleViewVersions(item)}
                              className="px-2.5 py-1.5 bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 rounded-lg text-xs font-medium flex items-center space-x-1"
                              title="View Version History"
                            >
                              <History className="w-3.5 h-3.5 text-slate-500" />
                              <span>v{item.active_version}</span>
                            </button>
                            <a
                              href={documentService.getDocumentDownloadUrl(item.document_id)}
                              target="_blank"
                              rel="noreferrer"
                              className="px-2.5 py-1.5 bg-indigo-50 border border-indigo-200 text-indigo-700 hover:bg-indigo-100 rounded-lg text-xs font-medium flex items-center space-x-1"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              <span>View</span>
                            </a>
                          </>
                        )}

                        <label className="relative cursor-pointer">
                          <input
                            type="file"
                            accept=".pdf,.png,.jpg,.jpeg"
                            disabled={isUploading}
                            className="hidden"
                            onChange={(e) => {
                              if (e.target.files && e.target.files[0]) {
                                handleFileUpload(item.code, e.target.files[0]);
                              }
                            }}
                          />
                          <span
                            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold flex items-center space-x-1.5 transition ${
                              isUploaded
                                ? 'bg-slate-100 hover:bg-slate-200 text-slate-800'
                                : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm'
                            } ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}`}
                          >
                            {isUploading ? (
                              <>
                                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                <span>Uploading...</span>
                              </>
                            ) : (
                              <>
                                <Upload className="w-3.5 h-3.5" />
                                <span>{isUploaded ? 'Replace (New Version)' : 'Upload File'}</span>
                              </>
                            )}
                          </span>
                        </label>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Step 7: Review, Digital Declaration & Submission */}
        {currentStep === 7 && (
          <div className="space-y-6">
            <div className="border-b border-slate-100 pb-4">
              <h2 className="text-lg font-bold text-slate-900">7. Final Application Review & Digital Declaration</h2>
              <p className="text-sm text-slate-500 mt-1">
                Carefully review all entries before submitting. Once submitted, records are locked for admission scrutiny.
              </p>
            </div>

            {/* Blockers alert if not ready */}
            {completion && !completion.can_submit && completion.blockers.length > 0 && (
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-2">
                <div className="flex items-center space-x-2 text-amber-900 font-bold text-sm">
                  <AlertCircle className="w-4 h-4 text-amber-600" />
                  <span>Submission Blockers ({completion.blockers.length} Unresolved Items):</span>
                </div>
                <ul className="list-disc list-inside text-xs text-amber-800 space-y-1">
                  {completion.blockers.map((b, idx) => (
                    <li key={idx}>{b}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Application Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Candidate & Quota</p>
                <p className="font-bold text-slate-900">{appData?.student_name}</p>
                <p className="text-xs text-slate-600">{appData?.tnea_application_number} | {formData.caste || appData?.community}</p>
                <p className="text-xs text-indigo-700 font-semibold">{appData?.allotted_branch_name || appData?.allotted_branch}</p>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Contact & Domicile</p>
                <p className="font-medium text-slate-800">{formData.city}, {formData.district}</p>
                <p className="text-xs text-slate-600">{formData.state} - {formData.pincode}</p>
                <p className="text-xs text-slate-600">Emergency: {formData.emergency_contact_name} ({formData.emergency_contact_phone})</p>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Academic & Cutoff</p>
                <p className="font-bold text-indigo-900 font-mono">Cutoff: {formData.twelfth_cutoff_marks || 'N/A'}</p>
                <p className="text-xs text-slate-600">10th: {formData.tenth_total_marks}/{formData.tenth_max_marks}</p>
                <p className="text-xs text-slate-600">12th: {formData.twelfth_total_marks}/{formData.twelfth_max_marks}</p>
              </div>
            </div>

            {/* Phase 4E Pre-Submission Consistency Pre-Check (Assistive) */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center space-x-2">
                  <div className="p-1.5 bg-indigo-100 text-indigo-700 rounded-lg">
                    <GitCompare className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Cross-Document Consistency Pre-Check (Assistive)
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      Cross-checks your form entries with uploaded certificates and TNEA baseline.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleRunStudentReconciliation}
                  disabled={runningStudentRecon}
                  className="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-lg text-xs font-bold transition inline-flex items-center space-x-1 self-start sm:self-auto disabled:opacity-50"
                >
                  <RefreshCw className={`w-3 h-3 ${runningStudentRecon ? 'animate-spin' : ''}`} />
                  <span>{runningStudentRecon ? 'Checking...' : 'Run Consistency Check'}</span>
                </button>
              </div>

              {studentRecon && (
                <div className="pt-2 border-t border-slate-200 space-y-2">
                  <div className="flex items-center space-x-2 text-xs">
                    <span className="font-semibold text-slate-600">Pre-Check Result:</span>
                    <span
                      className={`px-2 py-0.5 rounded font-bold text-[11px] ${
                        studentRecon.overall_status === 'MATCH'
                          ? 'bg-emerald-100 text-emerald-800'
                          : studentRecon.overall_status === 'DISCREPANCY_DETECTED'
                          ? 'bg-rose-100 text-rose-800'
                          : studentRecon.overall_status === 'PENDING_SCRUTINY'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-slate-200 text-slate-800'
                      }`}
                    >
                      {studentRecon.overall_status}
                    </span>
                    <span className="text-[11px] text-slate-500">
                      ({studentRecon.passed_rules_count}/{studentRecon.total_rules_evaluated} checks passed)
                    </span>
                  </div>

                  {studentRecon.discrepancy_summary && studentRecon.discrepancy_summary.length > 0 && (
                    <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-[11px] text-amber-900 space-y-1">
                      <strong className="block font-semibold">Items flagged for review:</strong>
                      <ul className="list-disc list-inside space-y-0.5">
                        {studentRecon.discrepancy_summary.map((d, idx) => (
                          <li key={idx}>{d}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              <p className="text-[10px] text-slate-400 italic">
                * Note: This pre-check is assistive only to help detect typos and does not represent official document verification.
              </p>
            </div>

            {/* Digital Declaration Box */}
            <div className="p-5 bg-slate-900 text-slate-100 rounded-2xl space-y-4">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="w-5 h-5 text-indigo-400" />
                <h3 className="text-sm font-bold tracking-wide uppercase text-indigo-300">
                  Statutory Declaration & Verification Undertaking
                </h3>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                I hereby declare that all information furnished above and the certificates uploaded are genuine, authentic,
                and correct to the best of my knowledge. I understand that any false or misleading declaration will lead to
                immediate cancellation of my admission at XYZ Engineering College and forfeiture of fees under TNEA regulations.
              </p>

              <label className="flex items-start space-x-3 p-3 bg-slate-800/80 rounded-xl border border-slate-700 cursor-pointer hover:bg-slate-800 transition">
                <input
                  type="checkbox"
                  checked={formData.declaration_accepted || false}
                  onChange={(e) => handleInputChange('declaration_accepted', e.target.checked)}
                  className="w-4 h-4 text-indigo-500 rounded mt-0.5"
                />
                <span className="text-xs font-semibold text-white">
                  I accept and solemnly affirm the declaration above on behalf of myself and my parent/guardian.
                </span>
              </label>
            </div>
          </div>
        )}

        {/* Bottom Actions Bar */}
        <div className="mt-8 pt-6 border-t border-slate-100 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            {currentStep > 1 && (
              <button
                type="button"
                onClick={() => setCurrentStep(prev => prev - 1)}
                className="px-4 py-2 bg-slate-100 text-slate-700 hover:bg-slate-200 font-semibold text-xs rounded-lg flex items-center space-x-1.5 transition"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Previous Step</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleSaveDraft}
              disabled={saving}
              className="px-4 py-2 bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 font-semibold text-xs rounded-lg flex items-center space-x-1.5 transition"
            >
              <Save className="w-4 h-4 text-slate-500" />
              <span>{saving ? 'Saving Draft...' : 'Save Draft'}</span>
            </button>
          </div>

          <div className="flex items-center space-x-3">
            {currentStep < 7 ? (
              <button
                type="button"
                onClick={async () => {
                  await handleSaveDraft();
                  setCurrentStep(prev => prev + 1);
                }}
                className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-lg flex items-center space-x-2 shadow-sm transition"
              >
                <span>Save & Continue</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSubmitApplication}
                disabled={submitting || !formData.declaration_accepted || (completion ? !completion.can_submit : false)}
                className={`px-6 py-2.5 rounded-lg font-bold text-xs flex items-center space-x-2 transition ${
                  formData.declaration_accepted && completion?.can_submit
                    ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-md'
                    : 'bg-slate-300 text-slate-500 cursor-not-allowed'
                }`}
              >
                {submitting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Submitting Application...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Finalize & Submit Application</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Version History Modal */}
      {selectedDocForVersions && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Document Version History</h3>
                <p className="text-xs text-slate-500">{selectedDocForVersions.name}</p>
              </div>
              <button
                onClick={() => setSelectedDocForVersions(null)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold px-2 py-1"
              >
                ✕
              </button>
            </div>

            {loadingVersions ? (
              <div className="py-8 flex justify-center">
                <RefreshCw className="w-6 h-6 animate-spin text-indigo-600" />
              </div>
            ) : (
              <div className="space-y-3 max-h-80 overflow-y-auto">
                {docVersions.map((v) => (
                  <div key={v.id} className="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-center justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs font-bold rounded">
                          v{v.version_number}
                        </span>
                        <p className="text-xs font-bold text-slate-800">{v.original_filename}</p>
                      </div>
                      <p className="text-[10px] text-slate-400 mt-1">
                        SHA-256: <span className="font-mono">{v.file_hash_sha256?.substring(0, 16)}...</span>
                      </p>
                      <p className="text-[10px] text-slate-500">
                        Uploaded: {new Date(v.uploaded_at).toLocaleString()}
                      </p>
                    </div>

                    <a
                      href={documentService.getDocumentDownloadUrl(v.document_id, v.version_number)}
                      target="_blank"
                      rel="noreferrer"
                      className="px-2.5 py-1.5 bg-white border border-slate-200 text-indigo-600 hover:bg-indigo-50 rounded-lg text-xs font-bold flex items-center space-x-1"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Download</span>
                    </a>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
