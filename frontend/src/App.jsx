import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { RequireAdmin, RequireAuth } from './components/RouteGuards'
import Login from './pages/Login'
import Collections from './pages/Collections'
import CollectionView from './pages/CollectionView'
import EpubReader from './pages/EpubReader'
import ComicReader from './pages/ComicReader'
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
            {/* :name/* captures the rest of the path as one splat param so CollectionView
                can handle arbitrarily nested subdirectories itself. */}
            <Route path="/collections/:name/*" element={<CollectionView />} />
            <Route path="/reader/:magazineId" element={<EpubReader />} />
            <Route path="/comic/:magazineId" element={<ComicReader />} />
            <Route path="/settings/ui" element={<UISettings />} />

            {/* Nested under RequireAuth so these also get the outer login redirect. */}
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
