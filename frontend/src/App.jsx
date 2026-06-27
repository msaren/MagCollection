import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { RequireAdmin, RequireAuth } from './components/RouteGuards'
import Login from './pages/Login'
import Collections from './pages/Collections'
import CollectionView from './pages/CollectionView'
import AdminUsers from './pages/admin/Users'
import AdminScanner from './pages/admin/Scanner'
import AdminMagazineEditor from './pages/admin/MagazineEditor'
import UISettings from './pages/settings/UISettings'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route element={<RequireAuth />}>
            <Route path="/" element={<Collections />} />
            <Route path="/collections/:name" element={<CollectionView />} />
            <Route path="/settings/ui" element={<UISettings />} />

            <Route element={<RequireAdmin />}>
              <Route path="/admin/users" element={<AdminUsers />} />
              <Route path="/admin/scanner" element={<AdminScanner />} />
              <Route path="/admin/magazines" element={<AdminMagazineEditor />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
