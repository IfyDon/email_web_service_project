/**
 * Centralised route tree using React Router v6 lazy loading.
 *
 * Place: frontend/src/router.jsx
 */

import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Layout         from '@/components/layout/Layout';
import Spinner        from '@/components/common/Spinner';

// ── Auth pages (not behind ProtectedRoute) ────────────────────────────────────
const LoginPage   = lazy(() => import('@/pages/auth/LoginPage'));
const SignupPage  = lazy(() => import('@/pages/auth/SignupPage'));
const TwoFAPage   = lazy(() => import('@/pages/auth/TwoFAPage'));

// ── Dashboard pages ───────────────────────────────────────────────────────────
const DashboardPage    = lazy(() => import('@/pages/dashboard/DashboardPage'));
const MessagesPage     = lazy(() => import('@/pages/messages/MessagesPage'));
const MessageDetail    = lazy(() => import('@/pages/messages/MessageDetail'));
const DomainsPage      = lazy(() => import('@/pages/domains/DomainsPage'));
const TemplatesPage    = lazy(() => import('@/pages/templates/TemplatesPage'));
const AnalyticsPage    = lazy(() => import('@/pages/analytics/AnalyticsPage'));
const WebhooksPage     = lazy(() => import('@/pages/webhooks/WebhooksPage'));
const SuppressionsPage = lazy(() => import('@/pages/suppressions/SuppressionsPage'));
const APIKeysPage      = lazy(() => import('@/pages/settings/APIKeysPage'));
const AccountPage      = lazy(() => import('@/pages/settings/AccountPage'));

const Loading = () => (
  <div className="flex h-full items-center justify-center">
    <Spinner size="lg" />
  </div>
);

export default function Router() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        {/* ── Public ────────────────────────────────────────────────────── */}
        <Route path="/login"      element={<LoginPage />} />
        <Route path="/signup"     element={<SignupPage />} />
        <Route path="/login/2fa"  element={<TwoFAPage />} />

        {/* ── Protected (wrapped in sidebar layout) ────────────────────── */}
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route index                         element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard"             element={<DashboardPage />} />
            <Route path="/messages"              element={<MessagesPage />} />
            <Route path="/messages/:id"          element={<MessageDetail />} />
            <Route path="/domains"               element={<DomainsPage />} />
            <Route path="/templates"             element={<TemplatesPage />} />
            <Route path="/analytics"             element={<AnalyticsPage />} />
            <Route path="/webhooks"              element={<WebhooksPage />} />
            <Route path="/suppressions"          element={<SuppressionsPage />} />
            <Route path="/settings/api-keys"     element={<APIKeysPage />} />
            <Route path="/settings/account"      element={<AccountPage />} />
          </Route>
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}
