import { Routes, Route } from 'react-router-dom';
import { Layout } from './components';
import { DashboardPage, AuthPage, DownloadPage, BatchPage, ConsultaPage } from './pages';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/auth" element={<AuthPage />} />
        <Route path="/download" element={<DownloadPage />} />
        <Route path="/batch" element={<BatchPage />} />
        <Route path="/consulta" element={<ConsultaPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
