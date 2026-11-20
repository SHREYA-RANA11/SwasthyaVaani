import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './useAuth';
import { HOME_BY_ROLE } from './roles';

import AuthPage from './pages/AuthPage';
import PatientDashboard from './pages/PatientDashboard';
import WorkerDashboard from './pages/WorkerDashboard';
import AdminDashboard from './pages/AdminDashboard';
import PrescriptionPage from './pages/PrescriptionPage';
import ProfilePage from './pages/ProfilePage';

// Only lets the right role into a page
function Protected({ role, roles, children }) {
  const allowed = roles || [role];
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="center-screen">Loading…</div>;
  }

  if (!user) {
    return <Navigate to="/" replace />;
  }

  if (!allowed.includes(user.role)) {
    return <Navigate to={HOME_BY_ROLE[user.role]} replace />;
  }

  return children;
}

function PublicOnly({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="center-screen">Loading…</div>;
  }

  if (user) {
    return <Navigate to={HOME_BY_ROLE[user.role]} replace />;
  }

  return children;
}

export default function App() {
  return (
    <Routes>
      {/* Authentication */}
      <Route
        path="/"
        element={
          <PublicOnly>
            <AuthPage />
          </PublicOnly>
        }
      />

      {/* Patient dashboard */}
      <Route
        path="/patient"
        element={
          <Protected role="patient">
            <PatientDashboard />
          </Protected>
        }
      />

      {/* Patient profile */}
      <Route
        path="/profile"
        element={
          <Protected role="patient">
            <ProfilePage />
          </Protected>
        }
      />

      {/* Healthcare worker dashboard */}
      <Route
        path="/worker"
        element={
          <Protected role="healthcare_worker">
            <WorkerDashboard />
          </Protected>
        }
      />

      {/* Admin dashboard */}
      <Route
        path="/admin"
        element={
          <Protected role="admin">
            <AdminDashboard />
          </Protected>
        }
      />

      {/* Prescription details */}
      <Route
        path="/prescriptions/:id"
        element={
          <Protected
            roles={['patient', 'healthcare_worker', 'admin']}
          >
            <PrescriptionPage />
          </Protected>
        }
      />

      {/* Unknown routes */}
      <Route
        path="*"
        element={<Navigate to="/" replace />}
      />
    </Routes>
  );
}