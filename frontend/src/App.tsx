import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthLayout } from './layouts/AuthLayout';
import { StudentLayout } from './layouts/StudentLayout';
import { AdminLayout } from './layouts/AdminLayout';
import { LoginPage } from './pages/LoginPage';
import { ActivationPage } from './pages/ActivationPage';
import { StudentDashboard } from './pages/StudentDashboard';
import { StudentApplicationWizard } from './pages/StudentApplicationWizard';
import { ApplicationSubmittedView } from './pages/ApplicationSubmittedView';
import { StudentChatAssistant } from './pages/StudentChatAssistant';
import { StudentOnboarding } from './pages/StudentOnboarding';
import { ParentDashboard } from './pages/ParentDashboard';
import { AdminDashboard } from './pages/AdminDashboard';
import { AdminTNEAImport } from './pages/AdminTNEAImport';
import { AdminAllotments } from './pages/AdminAllotments';
import { AdminApplications } from './pages/AdminApplications';
import { AdminApplicationDetail } from './pages/AdminApplicationDetail';
import { AdminPhysicalVerificationDesk } from './pages/AdminPhysicalVerificationDesk';
import { AdminPhysicalVerificationWorkspace } from './pages/AdminPhysicalVerificationWorkspace';
import { AdminPaymentDesk } from './pages/AdminPaymentDesk';
import { AdminERPDesk } from './pages/AdminERPDesk';
import { AdminKnowledgeDesk } from './pages/AdminKnowledgeDesk';
import { AdminOnboardingDesk } from './pages/AdminOnboardingDesk';
import { AdminAnalyticsDashboard } from './pages/AdminAnalyticsDashboard';
import { ProtectedRoute } from './components/ProtectedRoute';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Authentication & Activation Routes */}
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/activate" element={<ActivationPage />} />
        </Route>

        {/* Protected Student Routes */}
        <Route
          element={
            <ProtectedRoute allowedRoles={['STUDENT']}>
              <StudentLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/student/dashboard" element={<StudentDashboard />} />
          <Route path="/application/form" element={<StudentApplicationWizard />} />
          <Route path="/application/status" element={<ApplicationSubmittedView />} />
          <Route path="/student/chat" element={<StudentChatAssistant />} />
          <Route path="/student/onboarding" element={<StudentOnboarding />} />
        </Route>

        {/* Protected Parent Portal Routes */}
        <Route
          element={
            <ProtectedRoute allowedRoles={['PARENT', 'STUDENT']}>
              <StudentLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/parent/dashboard" element={<ParentDashboard />} />
        </Route>

        {/* Protected Admin Routes */}
        <Route
          element={
            <ProtectedRoute
              allowedRoles={[
                'ADMIN_VERIFIER',
                'FINANCE_OFFICER',
                'ADMISSION_HEAD',
                'SUPER_ADMIN',
              ]}
            >
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/admin/dashboard" element={<AdminDashboard />} />
          <Route path="/admin/tnea-import" element={<AdminTNEAImport />} />
          <Route path="/admin/allotments" element={<AdminAllotments />} />
          <Route path="/admin/applications" element={<AdminApplications />} />
          <Route path="/admin/applications/:id" element={<AdminApplicationDetail />} />
          <Route path="/admin/physical-verification" element={<AdminPhysicalVerificationDesk />} />
          <Route path="/admin/physical-verification/:sessionId" element={<AdminPhysicalVerificationWorkspace />} />
          <Route path="/admin/payments" element={<AdminPaymentDesk />} />
          <Route path="/admin/payments/:paymentId" element={<AdminPaymentDesk />} />
          <Route path="/admin/erp" element={<AdminERPDesk />} />
          <Route path="/admin/knowledge" element={<AdminKnowledgeDesk />} />
          <Route path="/admin/onboarding" element={<AdminOnboardingDesk />} />
          <Route path="/admin/analytics" element={<AdminAnalyticsDashboard />} />
        </Route>

        {/* Fallback & Default */}
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
