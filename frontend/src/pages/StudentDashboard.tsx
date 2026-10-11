import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  ArrowRight, 
  Sparkles, 
  Building2,
  FileText,
  Calendar,
  QrCode,
  MapPin,
  UserCheck,
} from 'lucide-react';
import { admissionService } from '../services/admission';
import { tneaService } from '../services/tnea';
import { ScrutinyService } from '../services/scrutiny';
import { PhysicalVerificationService } from '../services/physicalVerification';
import { timelineService } from '../services/timeline';
import {
  StudentProfile,
  AdmissionApplication,
  TNEAAllotment,
  StudentCorrectionSummary,
  StudentPhysicalVerificationSummary,
  AvailableSlot,
  StudentJourneyTimeline as JourneyType,
} from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { StatusTimeline } from '../components/StatusTimeline';
import { StudentJourneyTimeline } from '../components/StudentJourneyTimeline';
import { StudentPaymentCard } from '../components/StudentPaymentCard';
import { institutionConfig } from '../config/institution';

export const StudentDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [admission, setAdmission] = useState<AdmissionApplication | null>(null);
  const [allotment, setAllotment] = useState<TNEAAllotment | null>(null);
  const [correctionData, setCorrectionData] = useState<StudentCorrectionSummary | null>(null);
  const [physicalSummary, setPhysicalSummary] = useState<StudentPhysicalVerificationSummary | null>(null);
  const [journey, setJourney] = useState<JourneyType | null>(null);
  const [slots, setSlots] = useState<AvailableSlot[]>([]);
  const [bookingDate, setBookingDate] = useState<string>(
    new Date(Date.now() + 86400000).toISOString().split('T')[0]
  );
  const [selectedSlot, setSelectedSlot] = useState<AvailableSlot | null>(null);
  const [showBookingModal, setShowBookingModal] = useState<boolean>(false);
  const [bookingNotes, setBookingNotes] = useState<string>('');
  const [bookingLoading, setBookingLoading] = useState<boolean>(false);
  const [showQrModal, setShowQrModal] = useState<boolean>(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [profData, admData] = await Promise.all([
        admissionService.getStudentProfile(),
        admissionService.getStudentAdmission(),
      ]);
      setProfile(profData);
      setAdmission(admData);

      try {
        const allotData = await tneaService.getMyAllotment();
        setAllotment(allotData);
      } catch {
        // Fallback
      }

      try {
        const corr = await ScrutinyService.getMyCorrections();
        setCorrectionData(corr);
      } catch {
        setCorrectionData(null);
      }

      try {
        const pSummary = await PhysicalVerificationService.getMySummary();
        setPhysicalSummary(pSummary);
      } catch {
        setPhysicalSummary(null);
      }

      try {
        const jData = await timelineService.getMyTimeline();
        setJourney(jData);
      } catch {
        setJourney(null);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load admission details.');
    } finally {
      setLoading(false);
    }
  };


  const loadSlots = async (dateStr: string) => {
    try {
      const availSlots = await PhysicalVerificationService.getSlots(dateStr);
      setSlots(availSlots);
      if (availSlots.length > 0) {
        setSelectedSlot(availSlots[0]);
      }
    } catch {
      setSlots([]);
    }
  };

  const handleOpenBooking = () => {
    loadSlots(bookingDate);
    setShowBookingModal(true);
  };

  const handleBookAppointment = async () => {
    if (!selectedSlot) return;
    setBookingLoading(true);
    try {
      await PhysicalVerificationService.createAppointment({
        appointment_date: bookingDate,
        start_time: selectedSlot.start_time,
        end_time: selectedSlot.end_time,
        notes: bookingNotes || undefined,
      });
      setShowBookingModal(false);
      await loadData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to schedule appointment');
    } finally {
      setBookingLoading(false);
    }
  };

  const handleConfirmAppointment = async (appointmentId: string) => {
    try {
      await PhysicalVerificationService.confirmAppointment(appointmentId);
      await loadData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to confirm appointment');
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-3">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-xs font-mono text-slate-500">Loading student admission workspace...</p>
      </div>
    );
  }

  if (!profile || !admission) {
    return (
      <div className="p-6 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-sm">
        {error || 'Unable to retrieve admission profile.'}
      </div>
    );
  }

  const currentStatus = admission.status;

  return (
    <div className="space-y-6">
      {/* Institutional Top Header */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 rounded-2xl p-6 lg:p-8 text-white shadow-lg relative overflow-hidden">
        <div className="relative z-10">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-mono uppercase tracking-widest text-blue-300 font-semibold bg-blue-950/80 px-2.5 py-1 rounded border border-blue-800">
                  {institutionConfig.name} &bull; Admissions {institutionConfig.academicYear}
                </span>
              </div>
              <h2 className="text-2xl lg:text-3xl font-bold mt-2.5 tracking-tight">
                {profile.full_name}
              </h2>
              <p className="text-xs sm:text-sm text-blue-200 mt-1 max-w-xl">
                TNEA Application No: <strong className="text-white font-mono">{profile.tnea_application_number}</strong> &bull; {profile.allotted_branch}
              </p>
            </div>

            <div className="text-right">
              <p className="text-[11px] text-blue-300 uppercase tracking-wider font-semibold">Admission Lifecycle State</p>
              <div className="mt-1.5">
                <StatusBadge status={currentStatus} size="lg" />
              </div>
            </div>
          </div>
        </div>

        {/* Decorative background blur */}
        <div className="absolute right-0 bottom-0 translate-x-8 translate-y-8 w-64 h-64 bg-blue-500/10 rounded-full blur-2xl"></div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start space-x-3 text-rose-700 text-xs">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Phase 4F Candidate Correction Requirement Alert */}
      {(currentStatus === 'CORRECTION_REQUIRED' || correctionData?.correction_required) && (
        <div className="p-5 bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-amber-300 rounded-2xl shadow-sm space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-3">
              <span className="p-2.5 bg-amber-200/80 text-amber-900 rounded-xl">
                <AlertCircle className="w-6 h-6 text-amber-700" />
              </span>
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-bold text-amber-950 uppercase tracking-wide">
                    Action Required: Scrutiny Correction Requested
                  </h3>
                  {correctionData?.correction_reason && (
                    <span className="px-2 py-0.5 bg-amber-200 text-amber-900 font-mono text-[10px] font-bold rounded">
                      {correctionData.correction_reason}
                    </span>
                  )}
                </div>
                <p className="text-xs text-amber-900 mt-0.5">
                  The admission verification desk has reviewed your submission and requested adjustments.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => navigate('/student/application')}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded-xl text-xs transition inline-flex items-center space-x-1.5 shadow-sm"
            >
              <span>Upload Corrected Documents</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {correctionData?.correction_instructions && (
            <div className="p-3 bg-white/80 border border-amber-200 rounded-xl text-xs text-amber-950">
              <span className="font-bold text-amber-900">Reviewer Instructions: </span>
              <span>"{correctionData.correction_instructions}"</span>
            </div>
          )}

          {correctionData?.affected_documents && correctionData.affected_documents.length > 0 && (
            <div className="text-xs space-y-1 pt-1">
              <span className="font-semibold text-amber-900 block text-[11px] uppercase tracking-wider">
                Document(s) Requiring Replacement:
              </span>
              <div className="flex flex-wrap gap-2">
                {correctionData.affected_documents.map((doc) => (
                  <span
                    key={doc.document_id}
                    className="px-2.5 py-1 bg-amber-100/90 text-amber-900 border border-amber-200 rounded-lg text-xs font-medium"
                  >
                    {doc.document_type_name} (Current: v{doc.current_version_number})
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Phase 5 Physical Verification Correction Alert */}
      {physicalSummary?.active_correction_request && (
        <div className="p-5 bg-gradient-to-r from-rose-50 to-amber-50 border-2 border-rose-300 rounded-2xl shadow-sm space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-3">
              <span className="p-2.5 bg-rose-200/80 text-rose-900 rounded-xl">
                <AlertCircle className="w-6 h-6 text-rose-700" />
              </span>
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-bold text-rose-950 uppercase tracking-wide">
                    Action Required: Physical Document Correction
                  </h3>
                  <span className="px-2 py-0.5 bg-rose-200 text-rose-900 font-mono text-[10px] font-bold rounded">
                    {physicalSummary.active_correction_request.reason}
                  </span>
                </div>
                <p className="text-xs text-rose-900 mt-0.5">
                  During your on-site physical document check, an officer requested document re-upload or clarification.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => navigate('/application/status')}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-xl text-xs transition inline-flex items-center space-x-1.5 shadow-sm"
            >
              <span>Resubmit Document Version</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="p-3 bg-white/80 border border-rose-200 rounded-xl text-xs text-rose-950">
            <span className="font-bold text-rose-900">Officer Instructions: </span>
            <span>"{physicalSummary.active_correction_request.notes}"</span>
            <div className="mt-1 text-[11px] text-slate-500 font-mono">
              Document: {physicalSummary.active_correction_request.document_type_code} (Inspected v{physicalSummary.active_correction_request.document_version_number})
            </div>
          </div>
        </div>
      )}

      {/* Visual Lifecycle Timeline */}
      <StatusTimeline currentStatus={currentStatus} />

      {/* Phase 8 Unified 8-Stage Multi-Domain Journey & Audit Trail */}
      <StudentJourneyTimeline journey={journey} />

      {/* Main Grid: Details & Next Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Allotment, Payment & Identity Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Phase 10 First-Year Onboarding Widget */}
          <div className="bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 text-white p-6 rounded-2xl shadow-md space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-white/10 rounded-xl">
                  <Sparkles className="w-6 h-6 text-indigo-300" />
                </div>
                <div>
                  <h3 className="font-bold text-lg">First-Year Student & Parent Onboarding</h3>
                  <p className="text-xs text-indigo-200">
                    Day-Scholar vs Hosteller guidelines, Faculty Member mentorship, and induction checklist.
                  </p>
                </div>
              </div>
              <button
                onClick={() => navigate('/student/onboarding')}
                className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white font-bold text-xs rounded-xl shadow transition flex items-center gap-1.5"
              >
                <span>Open Onboarding Desk</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Phase 6 Payment & Demand Draft Settlement Card */}
          <StudentPaymentCard onPaymentUpdated={loadData} />

          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4 pb-2 border-b border-slate-100 flex items-center">
              <Building2 className="w-4 h-4 mr-2 text-blue-600" />
              TNEA Allotment Order &amp; Candidate Identity
            </h3>


            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 font-medium">Candidate Full Name</span>
                <p className="font-bold text-slate-900 text-sm mt-0.5">{profile.full_name}</p>
              </div>

              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 font-medium">TNEA Application Number</span>
                <p className="font-bold text-slate-900 text-sm mt-0.5 font-mono">{profile.tnea_application_number}</p>
              </div>

              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 font-medium">Allotment Order Number</span>
                <p className="font-bold text-slate-900 text-sm mt-0.5 font-mono">
                  {allotment?.allotment_number || `ALT-${profile.tnea_application_number}`}
                </p>
              </div>

              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 font-medium">Allotted Branch</span>
                <p className="font-bold text-slate-900 text-sm mt-0.5">{profile.allotted_branch}</p>
              </div>

              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 font-medium">Community &amp; Quota</span>
                <p className="font-bold text-slate-900 text-sm mt-0.5">
                  {profile.community || 'OC'} &bull; {profile.quota || 'GOVERNMENT'}
                </p>
              </div>

              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 font-medium">TNEA Cutoff Mark</span>
                <p className="font-bold text-slate-900 text-sm mt-0.5 font-mono">
                  {allotment?.cutoff_mark !== null && allotment?.cutoff_mark !== undefined
                    ? allotment.cutoff_mark.toFixed(2)
                    : '192.50'}
                </p>
              </div>

              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 font-medium">Allotment Order Date</span>
                <p className="font-bold text-slate-900 text-sm mt-0.5 font-mono">
                  {allotment?.allotment_date || '2026-08-10'}
                </p>
              </div>

              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 font-medium">Prescribed Joining Deadline</span>
                <p className="font-bold text-amber-700 text-sm mt-0.5 font-mono">
                  {allotment?.joining_deadline || '2026-08-25'}
                </p>
              </div>
            </div>
          </div>

          {/* Status History & Audit Log */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4 pb-2 border-b border-slate-100 flex items-center">
              <Clock className="w-4 h-4 mr-2 text-indigo-600" />
              Admission Lifecycle Audit History
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                    <th className="py-2.5 px-3">Timestamp</th>
                    <th className="py-2.5 px-3">Transition</th>
                    <th className="py-2.5 px-3">Actor Role</th>
                    <th className="py-2.5 px-3">Reason / Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {admission.status_history && admission.status_history.length > 0 ? (
                    admission.status_history.map((h) => (
                      <tr key={h.id} className="hover:bg-slate-50/50">
                        <td className="py-2.5 px-3 text-slate-500 text-[11px]">
                          {new Date(h.created_at).toLocaleString()}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className="text-slate-400">{h.previous_status || 'INIT'}</span>
                          <span className="mx-1 text-slate-300">&rarr;</span>
                          <span className="font-semibold text-blue-700">{h.new_status}</span>
                        </td>
                        <td className="py-2.5 px-3">
                          <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] font-bold">
                            {h.actor_role}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-600 font-sans max-w-xs truncate">
                          {h.reason || '-'}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="py-4 text-center text-slate-400 italic">
                        No state history recorded yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Column: Actions & Physical Verification */}
        <div className="space-y-6">
          {/* Phase 5 Physical Verification Card */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center">
                <UserCheck className="w-4 h-4 mr-2 text-indigo-600" />
                Physical Verification
              </h3>
              <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 font-mono text-[10px] font-bold rounded">
                Phase 5
              </span>
            </div>

            {/* Case 1: No Appointment Booked */}
            {!physicalSummary?.appointment && (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-600">On-Site Appointment</span>
                  <span className="px-2 py-0.5 bg-slate-200 text-slate-700 font-mono text-[10px] font-bold rounded">
                    NOT SCHEDULED
                  </span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Book an appointment slot at <strong>{institutionConfig.name}</strong> to present your original documents for verification.
                </p>
                <button
                  type="button"
                  onClick={handleOpenBooking}
                  className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold shadow transition"
                >
                  <Calendar className="w-4 h-4" />
                  <span>Book Verification Slot</span>
                </button>
              </div>
            )}

            {/* Case 2: Appointment Exists */}
            {physicalSummary?.appointment && (
              <div className="space-y-3 text-xs">
                <div className="p-4 bg-indigo-50/70 border border-indigo-200 rounded-xl space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] font-bold text-indigo-900">
                      Token #{physicalSummary.appointment.token_number}
                    </span>
                    <span className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold uppercase ${
                      physicalSummary.appointment.appointment_status === 'CONFIRMED'
                        ? 'bg-emerald-100 text-emerald-800'
                        : physicalSummary.appointment.appointment_status === 'CHECKED_IN'
                        ? 'bg-blue-100 text-blue-800'
                        : physicalSummary.appointment.appointment_status === 'IN_PROGRESS'
                        ? 'bg-purple-100 text-purple-800'
                        : physicalSummary.appointment.appointment_status === 'COMPLETED'
                        ? 'bg-slate-200 text-slate-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}>
                      {physicalSummary.appointment.appointment_status}
                    </span>
                  </div>

                  <div className="space-y-1 text-slate-700 pt-1">
                    <div className="flex items-center space-x-2">
                      <Calendar className="w-3.5 h-3.5 text-indigo-600" />
                      <span>{physicalSummary.appointment.appointment_date} ({physicalSummary.appointment.start_time} - {physicalSummary.appointment.end_time})</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <MapPin className="w-3.5 h-3.5 text-indigo-600" />
                      <span>{physicalSummary.appointment.location} &bull; Desk {physicalSummary.appointment.counter || 'General'}</span>
                    </div>
                  </div>

                  {physicalSummary.appointment.appointment_status === 'SCHEDULED' && (
                    <div className="pt-2 flex items-center space-x-2">
                      <button
                        type="button"
                        onClick={() => handleConfirmAppointment(physicalSummary.appointment!.id)}
                        className="flex-1 py-1.5 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition shadow-sm"
                      >
                        Confirm Slot
                      </button>
                      <button
                        type="button"
                        onClick={handleOpenBooking}
                        className="py-1.5 px-3 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 rounded-lg text-xs font-medium transition"
                      >
                        Reschedule
                      </button>
                    </div>
                  )}

                  {['CONFIRMED', 'CHECKED_IN', 'IN_PROGRESS'].includes(physicalSummary.appointment.appointment_status) && (
                    <button
                      type="button"
                      onClick={() => setShowQrModal(true)}
                      className="w-full mt-2 py-2 px-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold flex items-center justify-center space-x-1.5 shadow-sm transition"
                    >
                      <QrCode className="w-4 h-4" />
                      <span>View Check-In QR Pass</span>
                    </button>
                  )}
                </div>

                {/* Session Outcome Details if Completed */}
                {physicalSummary.session && (
                  <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-slate-700">Verification Outcome:</span>
                      <span className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold ${
                        physicalSummary.session.overall_decision === 'VERIFIED'
                          ? 'bg-emerald-100 text-emerald-800'
                          : physicalSummary.session.overall_decision === 'CORRECTION_REQUIRED'
                          ? 'bg-amber-100 text-amber-800'
                          : physicalSummary.session.overall_decision === 'REJECTED'
                          ? 'bg-rose-100 text-rose-800'
                          : 'bg-slate-200 text-slate-700'
                      }`}>
                        {physicalSummary.session.overall_decision || physicalSummary.session.session_status}
                      </span>
                    </div>
                    {physicalSummary.session.officer_notes && (
                      <p className="text-[11px] text-slate-600 italic">
                        "{physicalSummary.session.officer_notes}"
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3 flex items-center">
              <Sparkles className="w-4 h-4 mr-2 text-amber-500" />
              Next Action
            </h3>

            {(currentStatus === 'ACTIVATED' || currentStatus === 'APPLICATION_IN_PROGRESS') && (
              <div className="p-4 bg-indigo-50/80 border border-indigo-200 rounded-xl space-y-3">
                <div className="flex items-center space-x-2 text-indigo-900 font-bold text-xs">
                  <FileText className="w-4 h-4 text-indigo-600" />
                  <span>Digital Application Form</span>
                </div>
                <p className="text-xs text-indigo-950 font-medium leading-relaxed">
                  Complete your 7-step digital admission form, upload required certificates, and submit your declaration.
                </p>
                <button
                  type="button"
                  onClick={() => navigate('/application/form')}
                  className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold shadow-md shadow-indigo-500/20 transition-all"
                >
                  <span>{currentStatus === 'ACTIVATED' ? 'Start Application Form' : 'Continue Application Form'}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {['APPLICATION_SUBMITTED', 'DOCUMENT_REVIEW', 'DOCUMENTS_VERIFIED', 'ADMISSION_CONFIRMED', 'ACTIVE_STUDENT'].includes(currentStatus) && (
              <div className="p-4 bg-emerald-50/80 border border-emerald-200 rounded-xl space-y-3">
                <div className="flex items-center space-x-2 text-emerald-800 font-bold text-xs">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>Application Submitted</span>
                </div>
                <p className="text-xs text-emerald-950 leading-relaxed">
                  Your admission application has been submitted and locked for document verification.
                </p>
                <button
                  type="button"
                  onClick={() => navigate('/application/status')}
                  className="w-full py-2 px-3 bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 rounded-lg text-xs font-bold shadow-sm transition-all flex items-center justify-center space-x-1.5"
                >
                  <FileText className="w-3.5 h-3.5 text-slate-600" />
                  <span>View Submitted Dossier</span>
                </button>
              </div>
            )}

            <div className="mt-4 pt-4 border-t border-slate-100 text-[11px] text-slate-500 space-y-1">
              <p className="font-semibold text-slate-700">Need Help with Admissions?</p>
              <p>Contact the Admission Helpdesk at <strong>admission@xyz.edu.demo</strong></p>
            </div>
          </div>
        </div>
      </div>

      {/* Appointment Booking Modal */}
      {showBookingModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900 flex items-center">
                <Calendar className="w-5 h-5 mr-2 text-indigo-600" />
                Schedule Physical Verification
              </h3>
              <button
                type="button"
                onClick={() => setShowBookingModal(false)}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold"
              >
                &times;
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Select Verification Date</label>
                <input
                  type="date"
                  value={bookingDate}
                  min={new Date().toISOString().split('T')[0]}
                  onChange={(e) => {
                    setBookingDate(e.target.value);
                    loadSlots(e.target.value);
                  }}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Available Time Slots</label>
                {slots.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No available slots for this date.</p>
                ) : (
                  <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto pr-1">
                    {slots.map((slot, idx) => (
                      <button
                        type="button"
                        key={idx}
                        onClick={() => setSelectedSlot(slot)}
                        className={`p-2.5 rounded-lg border text-left text-xs transition ${
                          selectedSlot?.start_time === slot.start_time
                            ? 'border-indigo-600 bg-indigo-50 text-indigo-900 font-bold'
                            : 'border-slate-200 hover:border-slate-300 text-slate-700'
                        }`}
                      >
                        <span className="block font-mono">{slot.start_time} - {slot.end_time}</span>
                        <span className="text-[10px] text-slate-500">{slot.available_capacity} slots left</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Candidate Notes (Optional)</label>
                <textarea
                  rows={2}
                  value={bookingNotes}
                  onChange={(e) => setBookingNotes(e.target.value)}
                  placeholder="e.g. Traveling from outstation on morning train"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-[11px] text-amber-900 leading-relaxed">
                <strong>Important:</strong> Bring all original certificates, community proof, 4 passport photos, and TNEA allotment order copy.
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end space-x-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setShowBookingModal(false)}
                className="px-4 py-2 border border-slate-200 text-slate-700 rounded-lg text-xs font-medium hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleBookAppointment}
                disabled={!selectedSlot || bookingLoading}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold shadow"
              >
                {bookingLoading ? 'Booking...' : 'Confirm Appointment'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Check-In QR Pass Modal */}
      {showQrModal && physicalSummary?.appointment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl text-center space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Verification Desk Check-In Pass
              </h3>
              <button
                type="button"
                onClick={() => setShowQrModal(false)}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold"
              >
                &times;
              </button>
            </div>

            <div className="p-5 bg-slate-50 rounded-2xl border border-slate-200 flex flex-col items-center justify-center space-y-3">
              <div className="w-36 h-36 bg-white border-2 border-slate-900 rounded-xl flex flex-col items-center justify-center p-2 shadow-inner">
                <QrCode className="w-24 h-24 text-slate-900" />
                <span className="text-[9px] font-mono text-slate-500 uppercase tracking-wider mt-1">Verification QR</span>
              </div>

              <div>
                <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Token Number</span>
                <p className="text-2xl font-black text-indigo-700 font-mono tracking-tight">
                  {physicalSummary.appointment.token_number}
                </p>
              </div>

              <div className="text-xs text-slate-600 space-y-0.5 font-mono">
                <p>App No: <strong>{profile.tnea_application_number}</strong></p>
                <p>Date: {physicalSummary.appointment.appointment_date}</p>
                <p>Slot: {physicalSummary.appointment.start_time} - {physicalSummary.appointment.end_time}</p>
              </div>
            </div>

            <p className="text-xs text-slate-500">
              Present this screen at the <strong>Admission Verification Desk ({physicalSummary.appointment.location})</strong> upon arrival.
            </p>

            <button
              type="button"
              onClick={() => setShowQrModal(false)}
              className="w-full py-2 bg-slate-900 hover:bg-black text-white rounded-lg text-xs font-bold transition"
            >
              Close Pass
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
