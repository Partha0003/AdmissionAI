import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  CheckCircle2,
  Circle,
  AlertTriangle,
  UserCheck,
  Shield,
  Calendar,
  MapPin,
  Bus,
  Home,
  Users,
  Copy,
  Check,
  Send,
} from 'lucide-react';
import { onboardingService } from '../services/onboarding';
import {
  OnboardingProfile,
  OnboardingChecklistItem,
  StudentType,
  GuidanceCard,
  InaugurationEvent,
  TransportConfig,
} from '../types';

export const StudentOnboarding: React.FC = () => {
  const [profile, setProfile] = useState<OnboardingProfile | null>(null);
  const [checklist, setChecklist] = useState<OnboardingChecklistItem[]>([]);
  const [guidanceCards, setGuidanceCards] = useState<GuidanceCard[]>([]);
  const [inauguration, setInauguration] = useState<InaugurationEvent | null>(null);
  const [transport, setTransport] = useState<TransportConfig | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Parent Invitation State
  const [parentName, setParentName] = useState('');
  const [parentPhone, setParentPhone] = useState('');
  const [parentEmail, setParentEmail] = useState('');
  const [parentRel, setParentRel] = useState('FATHER');
  const [createdInviteToken, setCreatedInviteToken] = useState<string | null>(null);
  const [inviteCopied, setInviteCopied] = useState(false);

  useEffect(() => {
    loadOnboardingData();
  }, []);

  const loadOnboardingData = async () => {
    try {
      setLoading(true);
      setError(null);

      const prof = await onboardingService.getMyProfile();
      setProfile(prof);

      const [items, cards, inaug, trans] = await Promise.all([
        onboardingService.getMyChecklist(),
        onboardingService.getGuidance(),
        onboardingService.getInauguration(),
        onboardingService.getTransport(),
      ]);

      setChecklist(items);
      setGuidanceCards(cards);
      setInauguration(inaug);
      setTransport(trans);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Unable to load onboarding information.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleRequestStudentType = async (type: StudentType) => {
    try {
      setActionLoading(true);
      const updated = await onboardingService.requestStudentType(type);
      setProfile(updated);
      const [items, cards] = await Promise.all([
        onboardingService.getMyChecklist(),
        onboardingService.getGuidance(),
      ]);
      setChecklist(items);
      setGuidanceCards(cards);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update student type request.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAcknowledgeItem = async (itemKey: string) => {
    try {
      setActionLoading(true);
      await onboardingService.acknowledgeChecklistItem(itemKey);
      const [prof, items] = await Promise.all([
        onboardingService.getMyProfile(),
        onboardingService.getMyChecklist(),
      ]);
      setProfile(prof);
      setChecklist(items);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to acknowledge checklist item.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateParentInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!parentName.trim() || !parentPhone.trim()) return;

    try {
      setActionLoading(true);
      const res = await onboardingService.createParentInvitation({
        parent_name: parentName,
        phone: parentPhone,
        email: parentEmail.trim() || undefined,
        relationship: parentRel,
      });
      setCreatedInviteToken(res.invite_token);
      setParentName('');
      setParentPhone('');
      setParentEmail('');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to generate parent invitation token.');
    } finally {
      setActionLoading(false);
    }
  };

  const copyInviteToClipboard = () => {
    if (!createdInviteToken) return;
    navigator.clipboard.writeText(createdInviteToken);
    setInviteCopied(true);
    setTimeout(() => setInviteCopied(false), 2500);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-slate-600 font-medium">Loading First-Year Onboarding Portal...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto my-8 space-y-6">
        {/* Prototype Header */}
        <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white p-6 rounded-2xl shadow-xl">
          <div className="flex items-center justify-between">
            <div>
              <span className="inline-block px-3 py-1 bg-amber-500/20 border border-amber-400/40 text-amber-300 text-xs font-semibold rounded-full uppercase tracking-wider mb-2">
                Prototype / Demo Only
              </span>
              <h1 className="text-2xl font-bold">XYZ Engineering College (Code: XYZ)</h1>
              <p className="text-slate-300 text-sm">Academic Year 2026–27 • Student & Parent Onboarding Desk</p>
            </div>
          </div>
        </div>

        <div className="bg-amber-50 border border-amber-200 p-8 rounded-2xl text-center space-y-4">
          <AlertTriangle className="w-12 h-12 text-amber-600 mx-auto" />
          <h2 className="text-xl font-bold text-slate-800">Onboarding Status Notice</h2>
          <p className="text-slate-600 max-w-lg mx-auto font-medium">{error}</p>
          <p className="text-xs text-slate-500">
            Once your admission verification, fee payment, and ERP staging are finalized, this onboarding desk will activate automatically.
          </p>
        </div>
      </div>
    );
  }

  const completionPct = profile?.overall_completion_percentage || 0;
  const isInductionReady = profile?.onboarding_status === 'INDUCTION_READY';

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-16">
      {/* 1. Institutional Header */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white p-8 rounded-3xl shadow-xl relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-3 py-1 bg-amber-500/20 border border-amber-400/40 text-amber-300 text-xs font-semibold rounded-full uppercase tracking-wider">
                Prototype / Demo Only
              </span>
              <span className="px-3 py-1 bg-indigo-500/30 border border-indigo-400/40 text-indigo-200 text-xs font-semibold rounded-full">
                Phase 10: First-Year Onboarding
              </span>
            </div>
            <h1 className="text-3xl font-black tracking-tight">XYZ Engineering College (Code: XYZ)</h1>
            <p className="text-indigo-200 text-sm mt-1">
              Academic Year 2026–27 • Context-Aware Student, Parent & First-Year Induction Preparation
            </p>
          </div>

          {/* Completion Gauge */}
          <div className="bg-white/10 backdrop-blur-md border border-white/15 p-5 rounded-2xl flex items-center gap-5 min-w-[240px]">
            <div className="relative w-16 h-16 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <path
                  className="text-white/20"
                  strokeWidth="3.5"
                  stroke="currentColor"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <path
                  className={isInductionReady ? 'text-emerald-400' : 'text-indigo-400'}
                  strokeDasharray={`${completionPct}, 100`}
                  strokeWidth="3.5"
                  strokeLinecap="round"
                  stroke="currentColor"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
              </svg>
              <span className="absolute font-black text-sm text-white">{completionPct}%</span>
            </div>
            <div>
              <p className="text-xs uppercase font-bold tracking-wider text-indigo-200">Onboarding Readiness</p>
              <p className="text-lg font-black text-white">
                {isInductionReady ? 'Induction Ready' : `${checklist.filter(c => c.is_acknowledged).length}/${checklist.length} Completed`}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Controlled Student Type Workflow */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-indigo-600" />
              Student Accommodation & Commute Selection
            </h2>
            <p className="text-sm text-slate-500">
              Select your commute status. Changes enter <span className="font-semibold text-slate-700">STUDENT_REQUESTED</span> and are confirmed by the admission desk.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-slate-500">Workflow Status:</span>
            <span
              className={`px-3 py-1 text-xs font-bold rounded-full ${
                profile?.student_type_status === 'ADMIN_CONFIRMED'
                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                  : profile?.student_type_status === 'STUDENT_REQUESTED'
                  ? 'bg-amber-100 text-amber-800 border border-amber-300'
                  : 'bg-slate-100 text-slate-700 border border-slate-300'
              }`}
            >
              {profile?.student_type_status || 'UNSPECIFIED'}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
          {/* Day Scholar Option */}
          <button
            type="button"
            disabled={actionLoading}
            onClick={() => handleRequestStudentType('DAY_SCHOLAR')}
            className={`p-5 rounded-xl border-2 text-left transition-all flex items-start gap-4 ${
              profile?.student_type === 'DAY_SCHOLAR'
                ? 'border-indigo-600 bg-indigo-50/50 shadow-md ring-2 ring-indigo-500/20'
                : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
            }`}
          >
            <div className={`p-3 rounded-lg ${profile?.student_type === 'DAY_SCHOLAR' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600'}`}>
              <Bus className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-800">Day-Scholar</span>
                {profile?.student_type === 'DAY_SCHOLAR' && (
                  <span className="text-xs bg-indigo-600 text-white font-bold px-2 py-0.5 rounded">Selected</span>
                )}
              </div>
              <p className="text-xs text-slate-600 mt-1">
                Commuting daily via college bus routes or private transport. Includes bus pass instructions and day-scholar conduct guidelines.
              </p>
            </div>
          </button>

          {/* Hosteller Option */}
          <button
            type="button"
            disabled={actionLoading}
            onClick={() => handleRequestStudentType('HOSTELLER')}
            className={`p-5 rounded-xl border-2 text-left transition-all flex items-start gap-4 ${
              profile?.student_type === 'HOSTELLER'
                ? 'border-indigo-600 bg-indigo-50/50 shadow-md ring-2 ring-indigo-500/20'
                : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
            }`}
          >
            <div className={`p-3 rounded-lg ${profile?.student_type === 'HOSTELLER' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600'}`}>
              <Home className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-800">Hosteller (Campus Resident)</span>
                {profile?.student_type === 'HOSTELLER' && (
                  <span className="text-xs bg-indigo-600 text-white font-bold px-2 py-0.5 rounded">Selected</span>
                )}
              </div>
              <p className="text-xs text-slate-600 mt-1">
                Staying in on-campus student residences. Includes hostel room necessities, Hosteller mobile-phone guidance, Visitors' Form, and gate-pass protocols.
              </p>
            </div>
          </button>
        </div>
      </div>

      {/* 3. Inauguration Event Card */}
      {inauguration && (
        <div className="bg-gradient-to-br from-indigo-900 via-indigo-800 to-slate-900 text-white p-7 rounded-2xl shadow-md space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-white/10 rounded-xl">
                <Calendar className="w-6 h-6 text-indigo-300" />
              </div>
              <div>
                <h3 className="font-bold text-xl">{inauguration.event_name}</h3>
                <p className="text-indigo-200 text-xs">Academic Year {inauguration.academic_year}</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs uppercase font-bold text-indigo-200">Event Status:</span>
              <span
                className={`px-3 py-1 text-xs font-black rounded-full uppercase tracking-wider ${
                  inauguration.event_status === 'UPCOMING'
                    ? 'bg-amber-400 text-slate-900'
                    : inauguration.event_status === 'TODAY'
                    ? 'bg-emerald-400 text-slate-900 animate-pulse'
                    : 'bg-slate-600 text-white'
                }`}
              >
                {inauguration.event_status}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            <div className="bg-white/10 p-4 rounded-xl space-y-1">
              <div className="flex items-center gap-2 text-indigo-300 text-xs font-semibold">
                <Calendar className="w-4 h-4" /> Date & Schedule
              </div>
              <p className="font-black text-lg text-white">{inauguration.event_date}</p>
              <p className="text-xs text-indigo-200">Reporting: {inauguration.reporting_time}</p>
            </div>

            <div className="bg-white/10 p-4 rounded-xl space-y-1">
              <div className="flex items-center gap-2 text-indigo-300 text-xs font-semibold">
                <MapPin className="w-4 h-4" /> Ceremony Venue
              </div>
              <p className="font-bold text-sm text-white">{inauguration.venue}</p>
              <p className="text-xs text-indigo-200">Ceremony: {inauguration.ceremony_time}</p>
            </div>

            <div className="bg-white/10 p-4 rounded-xl space-y-1">
              <div className="flex items-center gap-2 text-indigo-300 text-xs font-semibold">
                <Users className="w-4 h-4" /> Parent Attendance
              </div>
              <p className="text-xs text-white/90">{inauguration.instructions_parent}</p>
            </div>
          </div>
        </div>
      )}

      {/* 4. Onboarding Checklist (Single Source of Truth) */}
      <div className="bg-white p-7 rounded-2xl border border-slate-200 shadow-sm space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-4 border-b border-slate-100 pb-4">
          <div>
            <h2 className="text-xl font-black text-slate-800 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-600" />
              First-Year Preparation Checklist
            </h2>
            <p className="text-sm text-slate-500">
              Personalized for your <span className="font-bold text-slate-700">{profile?.student_type}</span> profile. Review and acknowledge each item below.
            </p>
          </div>

          <div className="text-sm font-bold text-slate-600">
            {checklist.filter(i => i.is_acknowledged).length} of {checklist.length} Acknowledged
          </div>
        </div>

        <div className="space-y-3">
          {checklist.map((item) => (
            <div
              key={item.id}
              className={`p-4 rounded-xl border transition-all flex items-start justify-between gap-4 ${
                item.is_acknowledged
                  ? 'bg-emerald-50/40 border-emerald-200'
                  : 'bg-white border-slate-200 hover:border-indigo-300 hover:shadow-sm'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="mt-1">
                  {item.is_acknowledged ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  ) : (
                    <Circle className="w-5 h-5 text-slate-300" />
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className={`font-bold text-sm ${item.is_acknowledged ? 'text-slate-800' : 'text-slate-900'}`}>
                      {item.title}
                    </h4>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 bg-slate-100 text-slate-600 rounded">
                      {item.category}
                    </span>
                    {item.student_type_scope !== 'ALL' && (
                      <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded">
                        {item.student_type_scope}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-1">Ref: {item.source_reference}</p>
                </div>
              </div>

              <div>
                {item.is_acknowledged ? (
                  <span className="text-xs font-bold text-emerald-700 bg-emerald-100 px-3 py-1 rounded-full whitespace-nowrap">
                    Acknowledged
                  </span>
                ) : (
                  <button
                    type="button"
                    disabled={actionLoading}
                    onClick={() => handleAcknowledgeItem(item.item_key)}
                    className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg shadow-sm transition-all whitespace-nowrap"
                  >
                    Acknowledge
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 5. Secure Parent Invitation Widget */}
      <div className="bg-white p-7 rounded-2xl border border-slate-200 shadow-sm space-y-6">
        <div>
          <h2 className="text-xl font-black text-slate-800 flex items-center gap-2">
            <Shield className="w-5 h-5 text-indigo-600" />
            Secure Parent / Guardian Portal Invitation
          </h2>
          <p className="text-sm text-slate-500">
            Generate a single-use, 7-day cryptographically secure invite token for your parent/guardian to access the parent portal. (Parent linking is optional).
          </p>
        </div>

        {createdInviteToken ? (
          <div className="bg-emerald-50 border border-emerald-200 p-6 rounded-2xl space-y-4">
            <div className="flex items-center gap-2 text-emerald-800 font-bold">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              Invitation Token Generated Successfully!
            </div>
            <p className="text-xs text-slate-600">
              Share this single-use secure token with your parent. For security, only the SHA-256 hash is stored in our database; the raw token cannot be viewed again once dismissed.
            </p>

            <div className="flex items-center gap-3 bg-white p-3 rounded-xl border border-emerald-300">
              <code className="text-sm font-mono font-bold text-slate-800 flex-1 truncate select-all">
                {createdInviteToken}
              </code>
              <button
                type="button"
                onClick={copyInviteToClipboard}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white font-semibold text-xs rounded-lg hover:bg-emerald-700 transition"
              >
                {inviteCopied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                {inviteCopied ? 'Copied!' : 'Copy Token'}
              </button>
            </div>

            <p className="text-[11px] text-slate-500">
              Your parent should log in to the Parent Portal at <span className="font-semibold text-slate-700">/parent/dashboard</span> and enter this invitation token to link accounts.
            </p>
          </div>
        ) : (
          <form onSubmit={handleCreateParentInvite} className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Parent / Guardian Name *
              </label>
              <input
                type="text"
                required
                value={parentName}
                onChange={(e) => setParentName(e.target.value)}
                placeholder="e.g. S. Ramanathan"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Mobile Number *
              </label>
              <input
                type="text"
                required
                value={parentPhone}
                onChange={(e) => setParentPhone(e.target.value)}
                placeholder="+91 98765 43210"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Relationship *
              </label>
              <select
                value={parentRel}
                onChange={(e) => setParentRel(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
              >
                <option value="FATHER">Father</option>
                <option value="MOTHER">Mother</option>
                <option value="GUARDIAN">Guardian</option>
              </select>
            </div>

            <div className="flex items-end">
              <button
                type="submit"
                disabled={actionLoading}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-lg shadow-sm transition flex items-center justify-center gap-2"
              >
                <Send className="w-4 h-4" /> Generate Secure Invite
              </button>
            </div>
          </form>
        )}
      </div>

      {/* 6. Day-Scholar Commute / Transport Guidance */}
      {profile?.student_type === 'DAY_SCHOLAR' && transport && (
        <div className="bg-white p-7 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl">
              <Bus className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-black text-slate-800">College Bus & Commute Information</h2>
              <p className="text-sm text-slate-500">Transportation details for Day-Scholar students</p>
            </div>
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs space-y-2 text-slate-700">
            <p className="font-semibold text-slate-800">{transport.message || transport.general_instructions}</p>
            <p className="text-slate-500">For specific route timings and bus stops, please contact the college transport desk.</p>
          </div>
        </div>
      )}

      {/* 7. Guidance Cards Grid */}
      <div className="space-y-4">
        <h2 className="text-xl font-black text-slate-800">First-Year Institutional Guidelines & Support</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {guidanceCards.map((card, idx) => (
            <div key={idx} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-black uppercase tracking-wider px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded-md">
                  {card.category}
                </span>
                <span className="text-xs text-slate-400">Ref: {card.source_reference}</span>
              </div>
              <h3 className="font-bold text-slate-800 text-base">{card.title}</h3>

              {card.attribution && (
                <div className="text-[11px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 p-2 rounded-lg">
                  {card.attribution}
                </div>
              )}

              <div className="text-xs text-slate-600 space-y-2 pt-1">
                {Object.entries(card.data).map(([k, v]) => (
                  <div key={k} className="flex flex-col">
                    <span className="font-semibold text-slate-700 capitalize">{k.replace(/_/g, ' ')}:</span>
                    <span className="text-slate-600">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
