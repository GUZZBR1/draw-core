# Reprodutibilidade experimental em sistemas de visão computacional com modelos externos

**Tema:** Reprodutibilidade e integridade experimental  
**Tipo:** proposta de artigo conceitual e aplicada  
**Estado:** proposta conceitual; requer revisão bibliográfica e validação experimental.

## Resumo

Sistemas de visão computacional dependem de modelos, dados e configurações que podem mudar entre execuções. Este artigo propõe examinar como a rastreabilidade desses elementos afeta a possibilidade de reproduzir e comparar avaliações. O Draw-core serviria como estudo de caso, sem que detalhes internos de sua implementação sejam necessários para apresentar o argumento.

**Palavras-chave:** reprodutibilidade; integridade; rastreabilidade; modelos externos.

## Problema e pergunta de pesquisa

Resultados de avaliação perdem valor quando não é possível identificar com clareza quais artefatos e condições os produziram.

**Pergunta:** Quais práticas de registro e verificação ajudam a tornar avaliações de sistemas visuais reproduzíveis e auditáveis?

## Enquadramento e contribuição proposta

O artigo trataria reprodutibilidade como parte da qualidade experimental, e não apenas como documentação posterior. A contribuição proposta é um conjunto de princípios de alto nível para descrever dependências, versões, condições de avaliação e limites de validade. O estudo de caso ilustraria como esses princípios podem ser incorporados a um projeto de software.

## Panorama de avaliação

A análise poderia comparar a documentação disponível com uma descrição experimental mínima definida a partir da literatura. Também poderia verificar se um avaliador independente consegue interpretar os resultados e identificar as condições necessárias para comparações justas.

## Limitações e evidência necessária

O artigo não deve alegar que um mecanismo específico garante reprodução. A proposta depende de revisão bibliográfica e de uma auditoria documentada dos materiais experimentais do projeto. Qualquer conclusão sobre eficácia exigiria avaliação independente e escopo claramente delimitado.

## Revisão de divulgação

O rascunho permanece conceitual: não inclui algoritmos, parâmetros, detalhes internos do Draw, resultados quantitativos ou instruções suficientes para reproduzir sua implementação.
