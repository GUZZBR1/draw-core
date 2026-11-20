import type { Bilingual } from '../i18n';

export interface HistoricDrawing {
  artist: Bilingual;
  year: string;
  title: Bilingual;
  image: string;
  alt: Bilingual;
  source: string;
}

export const historicDrawings: HistoricDrawing[] = [
  {
    artist: { pt: 'Leonardo da Vinci', en: 'Leonardo da Vinci' },
    year: 'c. 1490',
    title: { pt: 'Homem Vitruviano', en: 'Vitruvian Man' },
    image: '/images/archive/vitruvian.jpg',
    alt: {
      pt: 'Estudo de proporções humanas de Leonardo da Vinci, desenhado a tinta.',
      en: 'Study of human proportions by Leonardo da Vinci, drawn in ink.',
    },
    source: 'https://commons.wikimedia.org/wiki/File:Vitruvian.jpg',
  },
  {
    artist: { pt: 'Charles Darwin', en: 'Charles Darwin' },
    year: '1837',
    title: { pt: '“I think”', en: '“I think”' },
    image: '/images/archive/darwin-tree.jpg',
    alt: {
      pt: 'Página do caderno de Darwin com a árvore da vida e as palavras “I think”.',
      en: 'Page from Darwin’s notebook with the tree of life and the words “I think”.',
    },
    source: 'https://commons.wikimedia.org/wiki/File:Darwin_Tree_1837.png',
  },
  {
    artist: { pt: 'Boulton & Watt', en: 'Boulton & Watt' },
    year: '1784',
    title: { pt: 'Motor de Watt', en: 'Watt’s engine' },
    image: '/images/archive/watt-steam-patent.jpg',
    alt: {
      pt: 'Esboço técnico do motor a vapor de Boulton & Watt com peças e mecanismos indicados.',
      en: 'Technical sketch of the Boulton & Watt steam engine, with parts and mechanisms labeled.',
    },
    source: 'https://commons.wikimedia.org/wiki/File:SteamEngine_Boulton%26Watt_1784.png',
  },
  {
    artist: { pt: 'Orville e Wilbur Wright', en: 'Orville and Wilbur Wright' },
    year: '1903 · pedido',
    title: { pt: 'Flying machine', en: 'Flying machine' },
    image: '/images/archive/wright-flying-machine.jpg',
    alt: {
      pt: 'Desenho técnico da máquina voadora dos irmãos Wright, patente requerida em 1903.',
      en: 'Technical drawing of the Wright brothers’ flying machine, patent filed in 1903.',
    },
    source: 'https://patents.google.com/patent/US821393A/en',
  },
  {
    artist: { pt: 'Alexander Graham Bell', en: 'Alexander Graham Bell' },
    year: '1876',
    title: { pt: 'Patente do telefone', en: 'Telephone patent' },
    image: '/images/archive/bell-telephone.jpg',
    alt: {
      pt: 'Folha de desenhos da patente de Bell, com diagramas dos aparelhos e do circuito.',
      en: 'Drawing sheet from Bell’s patent, with diagrams of the devices and the circuit.',
    },
    source: 'https://patents.google.com/patent/US174465A/en',
  },
  {
    artist: { pt: 'Robert Metcalfe', en: 'Robert Metcalfe' },
    year: '1976',
    title: { pt: 'Diagrama da Ethernet', en: 'Ethernet diagram' },
    image: '/images/archive/ethernet-1976.gif',
    alt: {
      pt: 'Diagrama desenhado à mão de uma estação ligada ao cabo Ether.',
      en: 'Hand-drawn diagram of a station connected to the Ether cable.',
    },
    source: 'https://grouper.ieee.org/groups/802/3/ethernet_diag.html',
  },
  {
    artist: { pt: 'Tim Berners-Lee', en: 'Tim Berners-Lee' },
    year: '1989',
    title: { pt: 'Proposta para a Web', en: 'Proposal for the Web' },
    image: '/images/archive/www-proposal.gif',
    alt: {
      pt: 'Página da proposta de gestão de informação de Tim Berners-Lee, com seu diagrama de conexões.',
      en: 'Page from Tim Berners-Lee’s information management proposal, with his diagram of connections.',
    },
    source: 'https://info.cern.ch/Proposal.html',
  },
  {
    artist: { pt: 'Apple', en: 'Apple' },
    year: '2007 · pedido',
    title: { pt: 'Design do iPhone', en: 'iPhone design' },
    image: '/images/archive/iphone-patent.jpg',
    alt: {
      pt: 'Desenho de patente do iPhone original, vista perspectiva do aparelho.',
      en: 'Patent drawing of the original iPhone, in perspective view of the device.',
    },
    source: 'https://patents.google.com/patent/USD558756S1/en',
  },
];
