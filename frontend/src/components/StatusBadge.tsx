import React from 'react';
import { AdmissionLifecycleState } from '../types';

interface StatusBadgeProps {
  status: AdmissionLifecycleState | string;
  size?: 'sm' | 'md' | 'lg';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const getStatusColor = (st: string) => {
    switch (st) {
      case 'ALLOTTED':
      case 'ACTIVATION_PENDING':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'ACTIVATED':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'APPLICATION_IN_PROGRESS':
        return 'bg-indigo-100 text-indigo-800 border-indigo-300';
      case 'APPLICATION_SUBMITTED':
      case 'DOCUMENT_PROCESSING':
      case 'DOCUMENT_REVIEW':
        return 'bg-purple-100 text-purple-800 border-purple-300';
      case 'CORRECTION_REQUIRED':
      case 'VERIFICATION_FAILED':
      case 'PAYMENT_FAILED':
        return 'bg-rose-100 text-rose-800 border-rose-300';
      case 'DOCUMENTS_VERIFIED':
      case 'VISIT_SCHEDULED':
      case 'PHYSICAL_VERIFICATION':
        return 'bg-teal-100 text-teal-800 border-teal-300';
      case 'PAYMENT_PENDING':
      case 'PAYMENT_SUBMITTED':
      case 'PAYMENT_VERIFIED':
        return 'bg-emerald-100 text-emerald-800 border-emerald-300';
      case 'ADMISSION_CONFIRMED':
      case 'ERP_SYNCED':
      case 'ONBOARDING':
      case 'INDUCTION_READY':
      case 'ACTIVE_STUDENT':
        return 'bg-green-100 text-green-800 border-green-300';
      default:
        return 'bg-slate-100 text-slate-800 border-slate-300';
    }
  };

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-xs font-semibold px-2.5 py-1',
    lg: 'text-sm font-semibold px-3 py-1.5',
  };

  const formatLabel = (st: string) => {
    return st.replace(/_/g, ' ');
  };

  return (
    <span
      className={`inline-flex items-center rounded-full border ${sizeClasses[size]} ${getStatusColor(
        status
      )} uppercase tracking-wider font-mono`}
    >
      <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-current opacity-80 animate-pulse"></span>
      {formatLabel(status)}
    </span>
  );
};
