import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import ScrollbarControl from '../components/ScrollbarControl';
import SiteHeader from '../components/SiteHeader';
import HomePage from '../pages/HomePage';
import PapersPage from '../pages/PapersPage';
import ArticlePage from '../pages/ArticlePage';
import ProductPage from '../pages/ProductPage';
import StudioShell from '../components/StudioShell';
import { Library, NewProject, ProjectList, ProjectView } from '../pages/StudioLists';
import StudioPage from '../pages/StudioPage';
import StudioWelcome from '../pages/StudioWelcome';
import VisionPage from '../pages/VisionPage';

export default function App() {
  const location = useLocation();
  const [productRefresh, setProductRefresh] = useState(0);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' });
    document.body.classList.toggle('home-scroll', location.pathname === '/');
  }, [location.pathname]);

  const inStudio = /^\/app(\/|$)/.test(location.pathname); // o estudio e '/app' e tudo abaixo dele

  return (
    <>
      {!inStudio && <SiteHeader
        onRepeatProduct={() => {
          setProductRefresh((revision) => revision + 1);
          window.scrollTo({ top: 0, behavior: 'instant' });
        }}
      />}
      <motion.div
        className="route-transition"
        key={inStudio ? '/app' : location.pathname} // dentro do estudio a moldura continua montada entre as telas
        initial={false}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.28, ease: 'easeOut' }}
      >
        <Routes location={location}>
          <Route path="/" element={<HomePage />} />
          <Route path="/vision" element={<VisionPage />} />
          <Route path="/papers" element={<PapersPage />} />
          <Route path="/papers/:n" element={<ArticlePage />} />
          <Route path="/product" element={<ProductPage key={productRefresh} />} />
          <Route path="/app" element={<StudioShell />}>
            <Route index element={<StudioWelcome />} />
            <Route path="new" element={<NewProject />} />
            <Route path="projects" element={<ProjectList />} />
            <Route path="library" element={<Library />} />
            <Route path="p/:projectId" element={<ProjectView />} />
            <Route path="p/:projectId/d/:drawingId" element={<StudioPage />} />
            <Route path="*" element={<Navigate to="/app" replace />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </motion.div>
      {!inStudio && <ScrollbarControl />}
    </>
  );
}
