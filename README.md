# Enterprise Cyber Risk & GRC Governance Dashboard 🛡️📊

Uma plataforma interativa de Governação de Risco e Conformidade (GRC), desenhada para traduzir vulnerabilidades técnicas de cibersegurança numa linguagem executiva e financeira.

Este simulador permite à Administração visualizar de forma clara a exposição ao risco, gerir o apetite ao risco da organização e otimizar a alocação de orçamentos de segurança com base no Retorno do Investimento (ROI).

![Visão Global do Dashboard e KPIs](assets/dashboard_kpis.png)

## Principais Funcionalidades

* **Quantificação Financeira do Risco:** Avaliação do impacto monetário de vulnerabilidades corporativas, integrando automaticamente o peso de coimas regulamentares (ex: RGPD a 2% ou 4% da faturação).
* **Otimização de Orçamento (Knapsack 0/1):** Motor matemático que prioriza algoritmicamente que problemas corrigir primeiro. Maximiza a redução do risco perante um limite rígido de orçamento, garantindo o melhor ROI possível.
* **Master Registry Editável e Dinâmico:** Registo central de conformidade (ISO 27001, NIST, PCI-DSS) onde o utilizador pode adicionar, editar ou remover ativos. Qualquer alteração recalcula em tempo real todos os KPIs e a distribuição de verbas.
* **Mecanismos de Prevenção e Qualidade:** Validação de dados (ex: ativos com valor nulo ou sem departamento alocado) e sistema de alertas executivos caso um ativo não financiado ultrapasse o limite de tolerância (Apetite ao Risco) definido.

![Análise Visual e ROI](assets/graficos_roi.png)

## 🛠️ Instalação e Execução (Guia Rápido)

Para testar e correr este projeto no teu próprio computador, segue estes passos no terminal:

### 1. Clonar o repositório para o teu computador

```bash
git clone https://github.com/O-TEU-USERNAME/grc-cyber-risk-dashboard.git
cd grc-cyber-risk-dashboard
```

> Nota: Substitui `O-TEU-USERNAME` pelo teu nome de utilizador real do GitHub.

### 2. Instalar as dependências necessárias

O painel requer o Streamlit e algumas bibliotecas de dados. Executa o seguinte comando para instalar tudo:

```bash
python -m pip install streamlit pandas plotly openpyxl
```

### 3. Arrancar com a aplicação

Inicia o servidor local do Streamlit. O teu navegador vai abrir automaticamente a plataforma.

```bash
python -m streamlit run app.py
```

## Arquitetura de Software Modular

O projeto segue boas práticas de engenharia de software, separando a lógica de negócio da interface gráfica (Separation of Concerns):

* **app.py:** Orquestração da interface (UI), estado da sessão e visualizações interativas através do Streamlit e Plotly.
* **motor_risco.py:** O núcleo analítico. Processa a matemática, a imputação proporcional do RGPD e executa o algoritmo de otimização da Mochila 0/1.
* **gestor_dados.py:** Tratamento de dados brutos. Lida com a importação de ficheiros (CSV/Excel), criação de aliases de colunas, normalização de inputs e salvaguarda contra erros de introdução.

## 📋 Exportação e Auditoria

Após a simulação de investimento, todo o registo de risco atualizado (com as decisões estratégicas e o risco residual calculado) pode ser exportado para formato CSV, servindo como prova de governação para equipas de auditoria (ex: ISO 27001, SOC2).
