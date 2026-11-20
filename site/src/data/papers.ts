/**
 * Propostas de artigo da coleção em docs/research (rascunhos conceituais: nenhuma delas é resultado validado).
 * Os textos aqui são resumos curtos dos "Resumo" de cada proposta.
 */
export interface Paper {
  n: string;
  short: string;
  title: string;
  blurb: string;
}

export const papers: Paper[] = [
  { n: '01', short: 'geometria da folha', title: 'Representação geométrica de páginas e traços em sistemas de desenho assistidos por câmera', blurb: 'Como perspectiva e mudança de pose da folha afetam a coerência dos traços que a câmera enxerga.' },
  { n: '02', short: 'achar a página', title: 'Detecção de páginas em cenas de desenho capturadas por câmera: condições de uso e limites', blurb: 'Onde a página é encontrada, e onde não é, sob luz, rotação e enquadramento variados.' },
  { n: '03', short: 'identidade da folha', title: 'Continuidade de identidade de páginas em sistemas de desenho assistidos por câmera', blurb: 'Quando a folha sai da cena e volta, como saber se é a mesma página ou uma nova.' },
  { n: '04', short: 'preservar a tinta', title: 'Estabilidade da reconstrução de traços durante o movimento da página', blurb: 'Manter o desenho estável e contínuo enquanto o papel muda de posição e de perspectiva.' },
  { n: '05', short: 'mão e caneta', title: 'Efeitos de oclusão na percepção de páginas e traços em sistemas de desenho por câmera', blurb: 'A mão sobre a folha não é exceção: é o uso normal. O que ela esconde, e o que isso custa.' },
  { n: '06', short: 'mundo real', title: 'Avaliação da robustez de sistemas de visão computacional para desenho em ambientes cotidianos', blurb: 'Reflexos, sombras, desfoque e dobras: caracterizar os limites de funcionamento.' },
  { n: '07', short: 'dados sintéticos', title: 'Simulação e dados sintéticos para avaliar sistemas de desenho por câmera', blurb: 'Cenários simulados como complemento às gravações reais, e até onde eles servem.' },
  { n: '08', short: 'tempo de resposta', title: 'Desempenho temporal em sistemas de desenho assistidos por visão computacional', blurb: 'A rapidez da resposta e a continuidade que a pessoa percebe enquanto desenha.' },
  { n: '09', short: 'do papel ao arquivo', title: 'Fidelidade geométrica na exportação de desenhos capturados em papel', blurb: 'O que do desenho sobrevive quando ele vira um artefato digital para outras ferramentas.' },
  { n: '10', short: 'reprodutibilidade', title: 'Reprodutibilidade experimental em sistemas de visão computacional com modelos externos', blurb: 'Rastrear modelos, dados e configurações para que um resultado possa ser repetido.' },
  { n: '11', short: 'acessibilidade', title: 'Acessibilidade e diversidade de uso em sistemas de desenho assistidos por câmera', blurb: 'Quem consegue usar, em que contextos, e onde estão as barreiras.' },
  { n: '12', short: 'experiência', title: 'Qualidade e continuidade da experiência em sistemas de desenho assistidos por câmera', blurb: 'Ligar as medidas técnicas ao que as pessoas realmente percebem ao desenhar.' },
];

/** Frases do palco: curtas e honestas, a coleção é de propostas, não de resultados. */
export const paperLines = [
  'Doze perguntas sobre o que acontece entre o papel e o pixel.',
  'Propostas de pesquisa: perguntas antes de promessas.',
  'Da geometria da folha à experiência de quem desenha.',
  'O que a gente construiu, escrito para ser questionado.',
  'Cada traço merece ser medido com cuidado.',
];
