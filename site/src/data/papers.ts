import type { Bilingual } from '../i18n';

/**
 * Propostas de artigo da coleção em docs/research (rascunhos conceituais: nenhuma delas é resultado validado).
 * Os textos aqui são resumos curtos dos "Resumo" de cada proposta.
 * short/title/blurb são o texto em português; en traz a tradução para inglês (mesma estrutura).
 */
export interface Paper {
  n: string;
  short: string;
  title: string;
  blurb: string;
  en: { short: string; title: string; blurb: string };
}

export const papers: Paper[] = [
  { n: '01', short: 'geometria da folha', title: 'Representação geométrica de páginas e traços em sistemas de desenho assistidos por câmera', blurb: 'Como perspectiva e mudança de pose da folha afetam a coerência dos traços que a câmera enxerga.', en: { short: 'sheet geometry', title: 'Geometric representation of pages and strokes in camera-assisted drawing systems', blurb: 'How perspective and changes in the sheet’s pose affect the consistency of the strokes the camera sees.' } },
  { n: '02', short: 'achar a página', title: 'Detecção de páginas em cenas de desenho capturadas por câmera: condições de uso e limites', blurb: 'Onde a página é encontrada, e onde não é, sob luz, rotação e enquadramento variados.', en: { short: 'finding the page', title: 'Page detection in camera-captured drawing scenes: conditions of use and limits', blurb: 'Where the page is found, and where it is not, under varied light, rotation and framing.' } },
  { n: '03', short: 'identidade da folha', title: 'Continuidade de identidade de páginas em sistemas de desenho assistidos por câmera', blurb: 'Quando a folha sai da cena e volta, como saber se é a mesma página ou uma nova.', en: { short: 'sheet identity', title: 'Page identity continuity in camera-assisted drawing systems', blurb: 'When the sheet leaves the scene and comes back, how to tell whether it is the same page or a new one.' } },
  { n: '04', short: 'preservar a tinta', title: 'Estabilidade da reconstrução de traços durante o movimento da página', blurb: 'Manter o desenho estável e contínuo enquanto o papel muda de posição e de perspectiva.', en: { short: 'preserving the ink', title: 'Stability of stroke reconstruction during page movement', blurb: 'Keeping the drawing stable and continuous while the paper changes position and perspective.' } },
  { n: '05', short: 'mão e caneta', title: 'Efeitos de oclusão na percepção de páginas e traços em sistemas de desenho por câmera', blurb: 'A mão sobre a folha não é exceção: é o uso normal. O que ela esconde, e o que isso custa.', en: { short: 'hand and pen', title: 'Occlusion effects on the perception of pages and strokes in camera drawing systems', blurb: 'The hand over the sheet is not an exception: it is normal use. What it hides, and what that costs.' } },
  { n: '06', short: 'mundo real', title: 'Avaliação da robustez de sistemas de visão computacional para desenho em ambientes cotidianos', blurb: 'Reflexos, sombras, desfoque e dobras: caracterizar os limites de funcionamento.', en: { short: 'real world', title: 'Assessing the robustness of computer vision systems for drawing in everyday environments', blurb: 'Reflections, shadows, blur and folds: characterizing the limits of operation.' } },
  { n: '07', short: 'dados sintéticos', title: 'Simulação e dados sintéticos para avaliar sistemas de desenho por câmera', blurb: 'Cenários simulados como complemento às gravações reais, e até onde eles servem.', en: { short: 'synthetic data', title: 'Simulation and synthetic data for evaluating camera drawing systems', blurb: 'Simulated scenarios as a complement to real recordings, and how far they are useful.' } },
  { n: '08', short: 'tempo de resposta', title: 'Desempenho temporal em sistemas de desenho assistidos por visão computacional', blurb: 'A rapidez da resposta e a continuidade que a pessoa percebe enquanto desenha.', en: { short: 'response time', title: 'Temporal performance in computer-vision-assisted drawing systems', blurb: 'The speed of the response and the continuity the person perceives while drawing.' } },
  { n: '09', short: 'do papel ao arquivo', title: 'Fidelidade geométrica na exportação de desenhos capturados em papel', blurb: 'O que do desenho sobrevive quando ele vira um artefato digital para outras ferramentas.', en: { short: 'from paper to file', title: 'Geometric fidelity in exporting drawings captured on paper', blurb: 'What of the drawing survives when it becomes a digital artifact for other tools.' } },
  { n: '10', short: 'reprodutibilidade', title: 'Reprodutibilidade experimental em sistemas de visão computacional com modelos externos', blurb: 'Rastrear modelos, dados e configurações para que um resultado possa ser repetido.', en: { short: 'reproducibility', title: 'Experimental reproducibility in computer vision systems with external models', blurb: 'Tracking models, data and configurations so that a result can be repeated.' } },
  { n: '11', short: 'acessibilidade', title: 'Acessibilidade e diversidade de uso em sistemas de desenho assistidos por câmera', blurb: 'Quem consegue usar, em que contextos, e onde estão as barreiras.', en: { short: 'accessibility', title: 'Accessibility and diversity of use in camera-assisted drawing systems', blurb: 'Who can use them, in which contexts, and where the barriers are.' } },
  { n: '12', short: 'experiência', title: 'Qualidade e continuidade da experiência em sistemas de desenho assistidos por câmera', blurb: 'Ligar as medidas técnicas ao que as pessoas realmente percebem ao desenhar.', en: { short: 'experience', title: 'Quality and continuity of the experience in camera-assisted drawing systems', blurb: 'Connecting technical measures to what people actually perceive when drawing.' } },
];

/** Frases do palco: curtas e honestas, a coleção é de propostas, não de resultados. */
export const paperLines: Bilingual[] = [
  { pt: 'Doze perguntas sobre o que acontece entre o papel e o pixel.', en: 'Twelve questions about what happens between the paper and the pixel.' },
  { pt: 'Propostas de pesquisa: perguntas antes de promessas.', en: 'Research proposals: questions before promises.' },
  { pt: 'Da geometria da folha à experiência de quem desenha.', en: 'From the geometry of the sheet to the experience of the person drawing.' },
  { pt: 'O que a gente construiu, escrito para ser questionado.', en: 'What we built, written to be questioned.' },
  { pt: 'Cada traço merece ser medido com cuidado.', en: 'Every stroke deserves to be measured with care.' },
];
