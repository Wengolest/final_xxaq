import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Spin } from 'antd';
import MainLayout from './components/Layout/MainLayout';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const TargetManagement = lazy(() => import('./pages/TargetManagement'));
const AttackConfig = lazy(() => import('./pages/AttackConfig'));
const DefenseConfig = lazy(() => import('./pages/DefenseConfig'));
const ExperimentCenter = lazy(() => import('./pages/ExperimentCenter'));
const ExperimentDetail = lazy(() => import('./pages/ExperimentCenter/ExperimentDetail'));
const ResultAnalysis = lazy(() => import('./pages/ResultAnalysis'));
const VariantAnalysis = lazy(() => import('./pages/VariantAnalysis'));
const AuditLog = lazy(() => import('./pages/AuditLog'));

const PageLoading = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
    <Spin size="large" />
  </div>
);

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoading />}>
        <Routes>
          <Route element={<MainLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/targets" element={<TargetManagement />} />
            <Route path="/attacks" element={<AttackConfig />} />
            <Route path="/defenses" element={<DefenseConfig />} />
            <Route path="/experiments" element={<ExperimentCenter />} />
            <Route path="/experiments/:runId" element={<ExperimentDetail />} />
            <Route path="/results/:runId" element={<ResultAnalysis />} />
            <Route path="/variants" element={<VariantAnalysis />} />
            <Route path="/audit" element={<AuditLog />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
