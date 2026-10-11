import React from 'react';
import { CheckCircle2, Circle, Clock } from 'lucide-react';
import { AdmissionLifecycleState } from '../types';

interface StatusTimelineProps {
  currentStatus: AdmissionLifecycleState | string;
}

interface Milestone {
  id: string;
  label: string;
  description: string;
  phase: number;
  isImplementedInPhase1: boolean;
}

const MILESTONES: Milestone[] = [
  { id: 'ALLOTTED', label: 'TNEA Allotment', description: 'Seat allotment ingested', phase: 1, isImplementedInPhase1: true },
  { id: 'ACTIVATED', label: 'Account Activation', description: 'Portal credentials active', phase: 1, isImplementedInPhase1: true },
  { id: 'APPLICATION', label: 'Online Application', description: 'Personal & academic details', phase: 1, isImplementedInPhase1: true },
  { id: 'DOCUMENTS', label: 'Document Verification', description: 'PaddleOCR & HITL review', phase: 4, isImplementedInPhase1: false },
  { id: 'VISIT', label: 'College Visit', description: 'Originals physical check', phase: 7, isImplementedInPhase1: false },
  { id: 'PAYMENT', label: 'Fee / DD Settlement', description: 'Finance clearance', phase: 8, isImplementedInPhase1: false },
  { id: 'CONFIRMATION', label: 'Admission Confirmed', description: 'Roll No. & ERP export', phase: 9, isImplementedInPhase1: false },
  { id: 'ONBOARDING', label: 'Student Onboarding', description: 'Induction & RAG chatbot', phase: 11, isImplementedInPhase1: false },
];

export const StatusTimeline: React.FC<StatusTimelineProps> = ({ currentStatus }) => {
  const getStageIndex = (st: string): number => {
    switch (st) {
      case 'ALLOTTED':
      case 'ACTIVATION_PENDING':
        return 0;
      case 'ACTIVATED':
        return 1;
      case 'APPLICATION_IN_PROGRESS':
      case 'APPLICATION_SUBMITTED':
        return 2;
      case 'DOCUMENT_PROCESSING':
      case 'DOCUMENT_REVIEW':
      case 'CORRECTION_REQUIRED':
      case 'DOCUMENTS_VERIFIED':
        return 3;
      case 'VISIT_SCHEDULED':
      case 'PHYSICAL_VERIFICATION':
        return 4;
      case 'PAYMENT_PENDING':
      case 'PAYMENT_SUBMITTED':
      case 'PAYMENT_VERIFICATION':
      case 'PAYMENT_VERIFIED':
        return 5;
      case 'ADMISSION_CONFIRMED':
      case 'ERP_SYNC_PENDING':
      case 'ERP_SYNCED':
        return 6;
      case 'ONBOARDING':
      case 'INDUCTION_READY':
      case 'ACTIVE_STUDENT':
        return 7;
      default:
        return 1;
    }
  };

  const activeIndex = getStageIndex(currentStatus);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-6 pb-3 border-b border-slate-100">
        <div>
          <h3 className="text-base font-semibold text-slate-800">Admission Progress Lifecycle</h3>
          <p className="text-xs text-slate-500 mt-0.5">Transparent milestone tracking from counselling to campus enrollment</p>
        </div>
        <span className="text-xs font-medium px-2.5 py-1 bg-slate-100 text-slate-600 rounded-md">
          Stage {activeIndex + 1} of {MILESTONES.length}
        </span>
      </div>

      <div className="relative">
        <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-8 gap-4">
          {MILESTONES.map((m, idx) => {
            const isCompleted = idx < activeIndex;
            const isCurrent = idx === activeIndex;
            const isPending = idx > activeIndex;

            return (
              <div
                key={m.id}
                className={`relative flex flex-col p-3 rounded-lg border transition-all ${
                  isCurrent
                    ? 'bg-blue-50/80 border-blue-400 shadow-sm ring-2 ring-blue-100'
                    : isCompleted
                    ? 'bg-emerald-50/50 border-emerald-200'
                    : 'bg-slate-50 border-slate-200 opacity-70'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono font-bold text-slate-400">0{idx + 1}</span>
                  {isCompleted && <CheckCircle2 className="w-4 h-4 text-emerald-600" />}
                  {isCurrent && <Clock className="w-4 h-4 text-blue-600 animate-spin" />}
                  {isPending && <Circle className="w-4 h-4 text-slate-300" />}
                </div>

                <div className="text-xs font-semibold text-slate-800 line-clamp-1">{m.label}</div>
                <div className="text-[11px] text-slate-500 mt-1 leading-snug line-clamp-2">{m.description}</div>

                {!m.isImplementedInPhase1 && (
                  <div className="mt-2 pt-2 border-t border-slate-200/60 text-[10px] text-amber-700 font-medium flex items-center">
                    <span>Phase {m.phase}</span>
                  </div>
                )}
                {m.isImplementedInPhase1 && (
                  <div className="mt-2 pt-2 border-t border-slate-200/60 text-[10px] text-blue-700 font-medium">
                    <span>Active in Phase 1</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
