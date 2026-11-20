import { Component, lazy, Suspense, useEffect, useState, type ErrorInfo, type ReactNode } from 'react';
import { motion } from 'motion/react';
import { Link, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import ScrollbarControl from '../components/ScrollbarControl';
import SiteHeader from '../components/SiteHeader';
import HomePage from '../pages/HomePage';
import PapersPage from '../pages/PapersPage';
import ProductPage from '../pages/ProductPage';
import StudioShell from '../components/StudioShell';
import { Library, NewProject, ProjectList, ProjectView } from '../pages/StudioLists';
import StudioPage from '../pages/StudioPage';
import StudioWelcome from '../pages/StudioWelcome';
import VisionPage from '../pages/VisionPage';

// Os manuscritos (~374 KB de texto) so carregam quando alguem abre um artigo.
const ArticlePage = lazy(() => import('../pages/ArticlePage'));

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
          <Route path="/papers/:n" element={
            <ArticleLoadBoundary key={location.pathname}>
              <Suspense fallback={<ArticleLoading />}><ArticlePage /></Suspense>
            </ArticleLoadBoundary>
          } />
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

function ArticleLoading() {
  return (
    <main className="article" id="page-content" aria-live="polite">
      <p>Carregando artigo…</p>
    </main>
  );
}

class ArticleLoadBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Failed to load article', error, info);
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="article" id="page-content">
          <Link className="article-back" to="/papers">← papers</Link>
          <p role="alert">Não foi possível carregar este artigo. Volte à lista ou tente novamente.</p>
        </main>
      );
    }
    return this.props.children;
  }
}
