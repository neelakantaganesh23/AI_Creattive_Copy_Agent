import { Route, Routes } from 'react-router-dom';

import { AppLayout } from '@/layouts/AppLayout';
import { AudienceSegmentsPage } from '@/pages/AudienceSegmentsPage';
import { BrandsPage } from '@/pages/BrandsPage';
import { CtaRulesPage } from '@/pages/CtaRulesPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { GeneratePage } from '@/pages/GeneratePage';
import { HistoryPage } from '@/pages/HistoryPage';
import { LoginPage } from '@/pages/LoginPage';
import { LogsPage } from '@/pages/LogsPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { TemplatesPage } from '@/pages/TemplatesPage';
import { ProtectedRoute, PublicOnlyRoute } from '@/routes/ProtectedRoute';

export const AppRoutes = (): JSX.Element => (
  <Routes>
    <Route element={<PublicOnlyRoute />}>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
    </Route>

    <Route element={<ProtectedRoute />}>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/generate" element={<GeneratePage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/history/:generationId" element={<HistoryPage />} />
        <Route path="/templates" element={<TemplatesPage />} />
        <Route path="/brands" element={<BrandsPage />} />
        <Route path="/audience-segments" element={<AudienceSegmentsPage />} />
        <Route path="/cta-rules" element={<CtaRulesPage />} />
        <Route path="/logs" element={<LogsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Route>

    <Route path="*" element={<NotFoundPage />} />
  </Routes>
);
