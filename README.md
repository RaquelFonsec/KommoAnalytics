# 📊 Kommo Analytics Dashboard

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)
![Kommo API](https://img.shields.io/badge/Kommo%20API-v2-green.svg)

**Sistema completo de Analytics para Kommo CRM com 6 módulos ETL e Dashboard interativo**

[�� Começar](#-instalação-rápida) • [📊 Dashboard](#-dashboard) • [🔧 Configuração](#-configuração) • [📈 Métricas](#-métricas-disponíveis)

</div>

---

## �� Sobre o Projeto

O **Kommo Analytics Dashboard** é uma solução completa de Business Intelligence para o Kommo CRM, desenvolvida para transformar dados brutos em insights acionáveis. O sistema integra 6 módulos ETL especializados que processam dados em tempo real, oferecendo uma visão 360° do funil de vendas.

### ✨ Características Principais

- �� **ETL Automatizado** - 6 módulos especializados processando dados em tempo real
- 📊 **Dashboard Interativo** - Interface Streamlit moderna e responsiva
- �� **Automação Completa** - Cron jobs para atualizações diárias
- 📈 **Métricas Avançadas** - KPIs, funil de conversão e previsões
- 🔍 **Validação de Qualidade** - Sistema de monitoramento e alertas
- 📱 **Responsivo** - Funciona em desktop e mobile

---

## 🏗️ Arquitetura do Sistema
KommoAnalytics/
├── 📁 ETL/ # Sistema de Extração, Transformação e Carga
│ ├── 🎯 Módulo 1: Leads # Entrada e origem de leads
│ ├── 🔄 Módulo 2: Funil # Funil de conversão
│ ├── 📞 Módulo 3: Atividades # Atividades comerciais
│ ├── 💰 Módulo 4: Vendas # Conversão e receita
│ ├── 👥 Módulo 5: Performance # Performance por pessoa e canal
│ └── �� Módulo 6: Forecast # Previsibilidade e metas
├── 🌐 DASHBOARD/ # Interface Streamlit
├── 🗄️ DATABASE/ # Scripts de banco de dados
├── ⚙️ AUTOMATION/ # Scripts de automação
├── 📊 DATA/ # Dados processados
└── 📋 LOGS/ # Logs do sistema




---

## 🚀 Instalação Rápida

### Pré-requisitos

- **Python 3.8+**
- **MySQL 8.0+**
- **Conta Kommo CRM** com API habilitada
- **Linux/Ubuntu** (recomendado para automação)

### 1️⃣ Clone o Repositório

```bash
git clone https://github.com/RaquelFonsec/KommoAnalytics.git
cd KommoAnalytics
```

### 2️⃣ Configure o Ambiente Virtual

```bash
python3 -m venv dashboard_env
source dashboard_env/bin/activate
pip install -r requirements.txt
```

### 3️⃣ Configure o Banco de Dados

```bash
# Instalar MySQL (se necessário)
sudo apt update
sudo apt install mysql-server -y

# Configurar banco
python DATABASE/setup_database.py
```

### 4️⃣ Configure as Credenciais

```bash
# Copiar template de configuração
cp env_template.txt .env

# Editar com suas credenciais
nano .env
```

**Exemplo de configuração (.env):**
```env
# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=kommo_analytics
DB_PASSWORD=sua_senha_segura
DB_NAME=kommo_analytics

# Kommo API Configuration
KOMMO_CLIENT_ID=seu_client_id
KOMMO_CLIENT_SECRET=seu_client_secret
KOMMO_REDIRECT_URI=http://localhost:8080/callback
```

### 5️⃣ Execute os ETLs

```bash
# Executar todos os módulos
bash AUTOMATION/run_all_etls.sh

# Ou executar individualmente
python ETL/kommo_etl_modulo1_leads.py
python ETL/kommo_etl_modulo2_funil.py
python ETL/kommo_etl_modulo3_atividades.py
python ETL/kommo_etl_modulo4_conversao.py
python ETL/kommo_etl_modulo5_performance.py
python ETL/kommo_etl_modulo6_forecast_integrado.py
```

### 6️⃣ Inicie o Dashboard

```bash
streamlit run DASHBOARD/main_app.py
```

**🌐 Acesse:** http://localhost:8501

---

## 📊 Dashboard

### 🎯 Interface Principal

O dashboard oferece uma experiência intuitiva com:

- **�� KPIs em Tempo Real** - Métricas principais sempre visíveis
- **��️ Filtros Dinâmicos** - Períodos personalizáveis (7, 15, 30 dias)
- **📊 Gráficos Interativos** - Visualizações Plotly responsivas
- **📱 Design Responsivo** - Funciona em qualquer dispositivo

### 📋 Módulos Disponíveis

#### 🎯 **Módulo 1: Entrada e Origem de Leads**
- Total de leads recebidos
- Distribuição por canal de origem
- Tempo médio de resposta
- Custo por lead por canal

#### 🔄 **Módulo 2: Funil de Conversão**
- Conversão por etapa do funil
- Tempo médio em cada etapa
- Taxa de abandono
- Análise de gargalos

#### �� **Módulo 3: Atividades Comerciais**
- Contatos realizados por vendedor
- Reuniões agendadas e realizadas
- Follow-ups e taxas de conclusão
- Performance de atividades

#### 💰 **Módulo 4: Conversão e Receita**
- Vendas fechadas e perdidas
- Receita total e ticket médio
- Win rate por vendedor
- Análise de motivos de perda

#### 👥 **Módulo 5: Performance por Pessoa e Canal**
- Ranking de vendedores
- Performance por canal de origem
- Conversão por pessoa
- Análise de produtividade

#### �� **Módulo 6: Previsibilidade (Forecast)**
- Previsão de receita
- Análise de gaps vs metas
- Alertas de risco
- Recomendações de ações

---

## ⚙️ Automação

### 🔄 Cron Jobs

O sistema está configurado para execução automática:

```bash
# Configurar automação
bash AUTOMATION/setup_cron.sh
```

**📅 Cronograma Automático:**
- **�� 6h diariamente** - Execução completa de todos ETLs
- **⏰ A cada 15 min** - Monitoramento do dashboard
- **📊 Domingos 8h** - Relatórios semanais

### �� Monitoramento

```bash
# Verificar status do sistema
python AUTOMATION/validate_metrics.py

# Monitorar atualizações
python AUTOMATION/monitor_daily_updates.py

# Garantia de qualidade
python AUTOMATION/quality_assurance.py
```

### 📋 Logs e Relatórios

- **📁 LOGS/** - Logs detalhados de todas as operações
- **📊 Relatórios automáticos** - Status de execução
- **⚠️ Alertas** - Notificações de problemas
- **📈 Métricas de saúde** - Performance do sistema

---

## �� Configuração Avançada

### 🗄️ Banco de Dados

**Tabelas Principais:**
- `leads_metrics` - Dados de leads e origens
- `funnel_history` - Histórico do funil de vendas
- `commercial_activities` - Atividades comerciais
- `sales_metrics` - Métricas de vendas e receita
- `performance_vendedores` - Performance por vendedor
- `monthly_forecasts` - Previsões e metas

### 🔐 Segurança

- **Credenciais criptografadas** no arquivo .env
- **Acesso restrito** ao banco de dados
- **Logs de auditoria** para todas as operações
- **Backup automático** dos dados

### 📈 Escalabilidade

- **Processamento em lotes** para grandes volumes
- **Otimização de queries** para performance
- **Cache inteligente** para consultas frequentes
- **Arquitetura modular** para fácil expansão

---

## 📈 Métricas Disponíveis

### �� KPIs Principais

| Métrica | Descrição | Fórmula |
|---------|-----------|---------|
| **Total de Leads** | Leads recebidos no período | `COUNT(leads)` |
| **Win Rate** | Taxa de conversão | `vendas_ganhas / total_vendas * 100` |
| **Ticket Médio** | Valor médio por venda | `receita_total / vendas_ganhas` |
| **Tempo de Resposta** | Tempo médio para responder leads | `AVG(response_time_hours)` |
| **Taxa de Conclusão** | Atividades concluídas | `atividades_concluidas / total_atividades * 100` |

### 📊 Relatórios Automáticos

- **�� Relatório Diário** - Resumo das métricas do dia
- **📊 Relatório Semanal** - Análise de tendências
- **�� Relatório Mensal** - Performance vs metas
- **⚠️ Alertas** - Notificações de problemas

---

## ��️ Desenvolvimento

### 🏗️ Estrutura de Desenvolvimento

```bash
# Ambiente de desenvolvimento
python3 -m venv dev_env
source dev_env/bin/activate
pip install -r requirements.txt

# Executar testes
python AUTOMATION/quality_assurance.py

# Verificar métricas
python AUTOMATION/validate_metrics.py
```

### �� Personalização

**Adicionar novos módulos:**
1. Criar script ETL em `ETL/`
2. Adicionar queries no dashboard
3. Configurar automação
4. Atualizar documentação

**Modificar métricas:**
1. Editar queries SQL
2. Atualizar visualizações
3. Testar validações
4. Deploy automático

---

## 📞 Suporte e Contribuição

### �� Reportar Problemas

- **GitHub Issues**: [Criar Issue](https://github.com/RaquelFonsec/KommoAnalytics/issues)
- **Email**: raquel.fonseca@example.com
- **Documentação**: [Wiki do Projeto](https://github.com/RaquelFonsec/KommoAnalytics/wiki)

### �� Contribuir

1. **Fork** o projeto
2. **Crie** uma branch para sua feature
3. **Commit** suas mudanças
4. **Push** para a branch
5. **Abra** um Pull Request

### �� Documentação

- **📖 Wiki**: Documentação completa
- **🎥 Vídeos**: Tutoriais em vídeo
- **📋 Guias**: Passo a passo detalhado
- **🔧 FAQ**: Perguntas frequentes

---

## 📄 Licença

Este projeto está sob a licença **MIT**. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## 🙏 Agradecimentos

- **Kommo CRM** pela API robusta
- **Streamlit** pela plataforma de dashboard
- **MySQL** pelo banco de dados confiável
- **Comunidade Python** pelas bibliotecas

---

<div align="center">

**⭐ Se este projeto te ajudou, considere dar uma estrela no GitHub!**

[![GitHub stars](https://img.shields.io/github/stars/RaquelFonsec/KommoAnalytics?style=social)](https://github.com/RaquelFonsec/KommoAnalytics)
[![GitHub forks](https://img.shields.io/github/forks/RaquelFonsec/KommoAnalytics?style=social)](https://github.com/RaquelFonsec/KommoAnalytics)
[![GitHub issues](https://img.shields.io/github/issues/RaquelFonsec/KommoAnalytics)](https://github.com/RaquelFonsec/KommoAnalytics/issues)

**Desenvolvido com ❤️ por Raquel Fonseca**

</div>

