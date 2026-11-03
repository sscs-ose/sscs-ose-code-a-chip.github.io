# PVT and Monte Carlo Mismatch Characterization of a 130-nm CMOS Current-Starved Ring Oscillator Using Open-Source Tools

**Análise de robustez de um CSRO-VCO em tecnologia CMOS de 130 nm**

![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)
![Technology](https://img.shields.io/badge/Technology-SkyWater%20SKY130A-00599C)
![Design](https://img.shields.io/badge/Design-Analog%20%2F%20RF-informational)
![Status](https://img.shields.io/badge/Implementation-Pre--layout-orange)

> Projeto acadêmico de caracterização por simulação de um oscilador em anel controlado por corrente (*Current-Starved Ring Oscillator Voltage-Controlled Oscillator*, CSRO-VCO), desenvolvido utilizando a tecnologia CMOS de 130 nm da SkyWater e ferramentas de código aberto.

---

## 1. Visão geral

Este projeto apresenta o desenvolvimento e a caracterização pré-layout de um **Current-Starved Ring Oscillator (CSRO)** utilizado como **Voltage-Controlled Oscillator (VCO)**, empregando a tecnologia CMOS de 130 nm da SkyWater.

O estudo concentra-se na análise da estabilidade da frequência de oscilação e da capacidade de sintonia do circuito em relação à banda ISM de 2,4 GHz.

A frequência nominal de referência é **2,45 GHz**, dentro da faixa de interesse de **2,4000 GHz a 2,4835 GHz**, utilizada por diferentes sistemas de comunicação sem fio, incluindo Bluetooth, Wi-Fi e Zigbee.

O trabalho investiga a influência de diferentes parâmetros sobre o comportamento do oscilador:

- Tensão de controle do VCO;
- Tensão de alimentação;
- Temperatura;
- Variações de processo;
- Mismatch estatístico entre dispositivos.

O objetivo não é apenas obter uma frequência nominal próxima de 2,45 GHz, mas avaliar a robustez do circuito diante das variações elétricas e estatísticas consideradas.

### Objetivos específicos

1. Estudar o funcionamento de inversores CMOS e sua relação com o atraso de propagação.
2. Compreender os princípios de funcionamento de um oscilador em anel.
3. Desenvolver uma estrutura de oscilador em anel com limitação de corrente.
4. Estimar a corrente de polarização necessária para a faixa de frequência desejada.
5. Caracterizar a resposta temporal e a curva frequência versus tensão de controle.
6. Avaliar o ganho de sintonia $K_{\mathrm{VCO}}$.
7. Investigar a sensibilidade do circuito às condições PVT e ao mismatch.
8. Estabelecer um fluxo de simulação reproduzível utilizando ferramentas open source.

---

## 2. Escopo e estado atual do projeto

O projeto encontra-se concentrado na **caracterização elétrica pré-layout**.

As atividades contempladas incluem:

- Desenvolvimento e análise do circuito esquemático;
- Simulação elétrica com modelos da tecnologia SKY130;
- Caracterização temporal do oscilador;
- Análise da frequência em função da tensão de controle;
- Avaliação do ganho de sintonia;
- Análises de variações PVT;
- Caracterização estatística por Monte Carlo mismatch.

As seguintes etapas permanecem como possibilidades de continuidade:

- Implementação do layout físico;
- Verificação DRC (*Design Rule Check*);
- Verificação LVS (*Layout Versus Schematic*);
- Extração de capacitâncias e resistências parasitas;
- Simulação pós-layout;
- Validação experimental.

Portanto, os resultados apresentados não incorporam integralmente os efeitos parasitas de interconexões e do layout físico. O circuito não deve ser considerado pronto para fabricação.

---

## 3. Especificações do projeto

| Parâmetro | Valor |
|---|---:|
| Tecnologia CMOS | SkyWater 130 nm |
| Variante do PDK | `sky130A` |
| Topologia | Current-Starved Ring Oscillator |
| Número de estágios de referência | 3 |
| Tensão nominal de alimentação | 1,8 V |
| Frequência nominal de referência | 2,45 GHz |
| Frequência mínima de interesse | 2,4000 GHz |
| Frequência máxima de interesse | 2,4835 GHz |
| Tensão de controle | $V_{\mathrm{cont}}$ |
| Tipo de caracterização | Pré-layout |

Os valores teóricos de corrente e capacitância utilizados no dimensionamento inicial são aproximações de primeira ordem. O comportamento definitivo depende dos modelos dos dispositivos e das condições de simulação.

---

## 4. Organização do estudo

O notebook está organizado em sete capítulos:

| Capítulo | Tema |
|---|---|
| 01 | Contextualização |
| 02 | O inversor CMOS |
| 03 | Ring Oscillator |
| 04 | Current-Starved Ring Oscillator-Based VCO |
| 05 | PVT and Monte Carlo Mismatch |
| 06 | Reproducibility |
| 07 | Conclusions |

A sequência de desenvolvimento é:

**Contextualização → Inversor CMOS → Oscilador em anel → CSRO-VCO → Análise PVT e mismatch → Reprodutibilidade → Conclusões.**

---

## 5. Ferramentas utilizadas

O fluxo de desenvolvimento utiliza ferramentas de código aberto para captura esquemática, simulação elétrica e análise dos resultados.

| Ferramenta | Funcionalidade | Versão registrada |
|---|---|---|
| SkyWater SKY130 PDK | Modelos de dispositivos e tecnologia CMOS | `sky130A` |
| Xschem | Captura e edição de esquemáticos | 3.4.8RC |
| ngspice | Simulação elétrica SPICE | 45 |
| Python | Automação e pós-processamento | 3.10.12 |
| Matplotlib | Visualização e geração de gráficos | 3.10.7 |
| Git | Controle de versão | 2.34.1 |

**Observação:** as versões acima correspondem às informações registradas no material do projeto. O ambiente Python indicado nos metadados do notebook também registra a versão 3.12.3. Para reprodução rigorosa, deve-se registrar a versão efetivamente utilizada em cada execução.

### 5.1 Função de cada ferramenta

**SkyWater SKY130 PDK**

Disponibiliza os modelos de dispositivos e parâmetros tecnológicos necessários para simular circuitos CMOS na tecnologia de 130 nm.

**Xschem**

Utilizado para captura esquemática e descrição gráfica dos circuitos eletrônicos.

**ngspice**

Responsável pelas simulações elétricas, permitindo analisar a resposta temporal e o comportamento do oscilador sob diferentes condições de operação.

**Python**

Utilizado no pós-processamento dos dados, extração de métricas e automação das análises.

**Matplotlib**

Utilizado para geração dos gráficos de resposta temporal, frequência de oscilação e ganho de sintonia.

**Git**

Permite controlar as versões dos arquivos e acompanhar alterações realizadas durante o desenvolvimento.

---

## 6. Fundamentos teóricos

### 6.1 Inversor CMOS

O inversor CMOS é composto por dois transistores complementares: um PMOS conectado ao caminho de alimentação e um NMOS conectado ao terra.

Quando a entrada está em nível baixo, o PMOS conduz e carrega a capacitância de saída. Quando a entrada está em nível alto, o NMOS conduz e descarrega essa capacitância.

Os principais atrasos de propagação são:

- $t_{PLH}$: atraso associado à transição da saída de nível baixo para alto;
- $t_{PHL}$: atraso associado à transição da saída de nível alto para baixo.

O atraso médio é:

$$
t_p=\frac{t_{PLH}+t_{PHL}}{2}
$$

### 6.2 Ring Oscillator

Um oscilador em anel é formado por uma quantidade ímpar de estágios inversores conectados em realimentação.

Para três estágios aproximadamente idênticos, o período pode ser estimado por:

$$
T_{\mathrm{osc}}\approx 3(t_{PHL}+t_{PLH})
$$

Consequentemente:

$$
f_{\mathrm{osc}}\approx
\frac{1}{3(t_{PHL}+t_{PLH})}
$$

Utilizando o atraso médio:

$$
f_{\mathrm{osc}}\approx\frac{1}{6t_p}
$$

Essas expressões são aproximações de primeira ordem e não substituem a simulação com os modelos reais dos dispositivos.

### 6.3 Current-Starved Ring Oscillator

No CSRO, a corrente disponível para carregar e descarregar os nós internos é limitada por transistores de controle.

A alteração da tensão de controle modifica a corrente de polarização e, consequentemente, o atraso dos estágios inversores.

A frequência pode ser representada por:

$$
f_{\mathrm{osc}}=f(V_{\mathrm{cont}})
$$

O ganho de sintonia é definido por:

$$
K_{\mathrm{VCO}}=
\frac{df_{\mathrm{osc}}}{dV_{\mathrm{cont}}}
$$

Essa grandeza representa a sensibilidade da frequência de oscilação às variações da tensão de controle.

---

## 7. Estimativa inicial da corrente de polarização

Para um oscilador em anel de três estágios, utiliza-se a aproximação:

$$
f_0=\frac{I}{NCV_{DD}}
$$

Isolando a corrente:

$$
I=f_0NCV_{DD}
$$

Adotando:

- Capacitância por estágio: $C=3\,\mathrm{fF}$;
- Número de estágios: $N=3$;
- Tensão de alimentação: $V_{DD}=1{,}8\,\mathrm{V}$.

A estimativa de corrente para cada frequência é:

| Frequência | Corrente estimada | Atraso médio por estágio |
|---:|---:|---:|
| 2,4000 GHz | 38,88 µA | 69,44 ps |
| 2,4500 GHz | 39,69 µA | 68,03 ps |
| 2,4835 GHz | 40,23 µA | 67,11 ps |

O atraso médio por estágio é estimado por:

$$
t_{\mathrm{center}}=\frac{1}{2Nf_0}
$$

Esses resultados fornecem uma referência inicial para o dimensionamento dos transistores limitadores de corrente. O dimensionamento definitivo deve ser validado por simulação, considerando as características dos dispositivos e as capacitâncias efetivas do circuito.

---

## 8. Caracterização do VCO

A caracterização do CSRO-VCO é dividida em três análises principais.

### 8.1 Resposta temporal

A resposta temporal permite verificar a forma de onda de saída, a inicialização da oscilação e a estabilidade do sinal em regime permanente.

### 8.2 Característica de sintonia

A frequência de oscilação é avaliada em função da tensão de controle:

$$
f_{\mathrm{osc}}=f(V_{\mathrm{cont}})
$$

A curva permite identificar a faixa de sintonia e verificar se os limites de frequência desejados podem ser alcançados.

### 8.3 Ganho de sintonia

O ganho de sintonia é dado por:

$$
K_{\mathrm{VCO}}(V_{\mathrm{cont}})
=
\frac{df_{\mathrm{osc}}}{dV_{\mathrm{cont}}}
$$

A análise permite avaliar a linearidade e a sensibilidade do VCO ao longo da faixa de controle.

### 8.4 Figuras geradas

As seguintes figuras fazem parte da documentação do projeto:

| Arquivo | Descrição |
|---|---|
| `figures/grafico_tensao_vs_tempo.png` | Resposta temporal da saída |
| `figures/grafico_freq_vs_vcont.png` | Frequência em função da tensão de controle |
| `figures/grafico_kvco_vs_vcont.png` | Ganho de sintonia em função da tensão de controle |

Os arquivos devem ser mantidos nos caminhos indicados para que sejam exibidos corretamente no notebook.

---

## 9. Análise PVT e Monte Carlo Mismatch

### 9.1 PVT

PVT corresponde a *Process, Voltage and Temperature*:

- **Process:** variações dos parâmetros dos dispositivos decorrentes do processo de fabricação;
- **Voltage:** variações da tensão de alimentação;
- **Temperature:** variações da temperatura de operação.

Essas variações podem modificar a corrente, os atrasos dos estágios e, consequentemente, a frequência de oscilação.

### 9.2 Monte Carlo mismatch

O mismatch representa diferenças locais entre dispositivos nominalmente idênticos, decorrentes de variações estatísticas do processo de fabricação.

A análise de Monte Carlo permite investigar como essas diferenças afetam a distribuição das métricas do circuito, incluindo a frequência de oscilação.

### 9.3 Configuração da campanha de simulação

A configuração de varredura registrada no desenvolvimento considera:

| Parâmetro | Configuração |
|---|---:|
| Corner de processo | TT |
| Tensão mínima | 1,71 V |
| Tensão máxima | 1,89 V |
| Passo de tensão | 0,01 V |
| Número de valores de tensão | 19 |
| Temperatura mínima | −25 °C |
| Temperatura máxima | 85 °C |
| Passo de temperatura | 5 °C |
| Número de valores de temperatura | 23 |
| Amostras de mismatch por condição | 200 |

O número total de combinações PVT é:

$$
N_{\mathrm{PVT}}=19\times23=437
$$

Considerando 200 amostras de mismatch por combinação:

$$
N_{\mathrm{simulações}}=437\times200
$$

$$
\boxed{N_{\mathrm{simulações}}=87\,400}
$$

Essa quantidade representa o total planejado para a campanha quando todas as combinações e amostras são executadas.

Para reprodução rigorosa, devem ser preservados os arquivos de configuração, modelos estatísticos, sementes aleatórias quando aplicáveis e resultados brutos.

---

## 10. Dependências

São necessárias:

- SkyWater SKY130 PDK;
- Xschem;
- ngspice;
- Python;
- Matplotlib;
- Bibliotecas adicionais utilizadas pelo notebook.


## 11. Limitações e trabalhos futuros

A caracterização pré-layout não contempla integralmente os efeitos físicos de interconexões e parasitas.

Entre as principais possibilidades de continuidade estão:

1. Implementação do layout físico;
2. Verificação DRC;
3. Verificação LVS;
4. Extração de parasitas;
5. Simulação pós-layout;
6. Avaliação de ruído de fase e jitter;
7. Estudo de técnicas de calibração e trimming;
8. Reavaliação da cobertura da banda ISM sob condições PVT e mismatch.

Uma etapa particularmente importante consiste em investigar mecanismos de compensação das variações de frequência, permitindo aumentar a robustez do oscilador diante de condições distintas de operação e fabricação.

---

## 12. Licença

Este projeto é distribuído sob os termos da **Apache License, Version 2.0**.

A licença permite:

- Uso pessoal e acadêmico;
- Reprodução dos arquivos;
- Modificação e criação de trabalhos derivados;
- Redistribuição do código e da documentação;
- Uso comercial, respeitando os termos da licença.

Consulte o arquivo `LICENSE` para obter o texto integral.

A licença aplica-se aos materiais originais deste repositório. Ferramentas, modelos, bibliotecas, PDKs, imagens e outros materiais de terceiros permanecem sujeitos às respectivas licenças e condições de uso.

---

## 13. Referências e recursos

- [IEEE SSCS — Code-a-Chip Travel Grant Awards](https://sscs.ieee.org/membership/awards/ieee-sscs-code-a-chip-travel-grant-awards/)
- [SkyWater SKY130 PDK](https://github.com/google/skywater-pdk)
- [Xschem](https://github.com/StefanSchippers/xschem)
- [ngspice](https://ngspice.sourceforge.io/)
- [Matplotlib](https://matplotlib.org/stable/)
- [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)

---

## 14. Aviso

Este repositório apresenta um estudo acadêmico baseado em simulações. Os resultados dependem dos modelos, versões de ferramentas, configurações e condições documentadas.

Não há garantia de desempenho, fabricação, conformidade regulatória ou adequação a uma aplicação específica. O uso do projeto como referência não substitui verificação independente.