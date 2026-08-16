import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { AuthProvider } from './context/AuthContext'
import { AdminPage } from './pages/AdminPage'
import { DrinksPage } from './pages/DrinksPage'
import { HomePage } from './pages/HomePage'
import { LadderPage } from './pages/LadderPage'
import { LoginPage } from './pages/LoginPage'
import { PrivacyPage } from './pages/PrivacyPage'
import { ProfilePage } from './pages/ProfilePage'
import { RecommendPage } from './pages/RecommendPage'
import { RedemptionsPage } from './pages/RedemptionsPage'
import { RegisterPage } from './pages/RegisterPage'
import { RewardsPage } from './pages/RewardsPage'
import { SettledPage } from './pages/SettledPage'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="drinks" element={<DrinksPage />} />
            <Route path="recommend/:productId" element={<RecommendPage />} />
            <Route path="settled/:productId" element={<SettledPage />} />
            <Route path="ladder/:productId" element={<LadderPage />} />
            <Route path="login" element={<LoginPage />} />
            <Route path="register" element={<RegisterPage />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="rewards" element={<RewardsPage />} />
            <Route path="redemptions" element={<RedemptionsPage />} />
            <Route path="privacy" element={<PrivacyPage />} />
            <Route path="admin" element={<AdminPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
