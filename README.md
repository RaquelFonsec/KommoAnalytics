
# 📊 Kommo Analytics Dashboard

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)
![Kommo API](https://img.shields.io/badge/Kommo%20API-v2-green.svg)

**Sistema completo de Business Intelligence para Kommo CRM com ETL automatizado e dashboard interativo em tempo real**

[🚀 Começar](#-instalação) • [📊 Dashboard](#-módulos-do-dashboard) • [📈 Métricas](#-métricas-detalhadas) • [⚙️ Automação](#️-automação)

</div>

---

## 🌟 Visão Geral

O **Kommo Analytics Dashboard** é uma solução de Business Intelligence que transforma dados brutos do Kommo CRM em insights acionáveis. Integra 6 módulos ETL especializados que processam dados em tempo real, oferecendo uma visão completa do funil de vendas.

### ✨ Características Principais

- 🔄 **ETL Automatizado** - 6 módulos especializados processando dados em tempo real
- 📊 **Dashboard Interativo** - Interface Streamlit moderna e responsiva
- ⚙️ **Automação Completa** - Cron jobs para atualizações automáticas
- 📈 **Métricas Avançadas** - KPIs, funil de conversão e previsões
- 🔍 **Validação de Qualidade** - Sistema de monitoramento e alertas
- 📱 **Design Responsivo** - Funciona em desktop e mobile

---

## 🏗️ Arquitetura

```
KommoAnalytics/
├── ETL/                    # Sistema de Extração, Transformação e Carga
│   ├── modulo1_leads.py           # Entrada e origem de leads
│   ├── modulo2_funil.py           # Funil de conversão
│   ├── modulo3_atividades.py      # Atividades comerciais
│   ├── modulo4_vendas.py          # Conversão e receita
│   ├── modulo5_performance.py     # Performance por pessoa e canal
│   └── modulo6_forecast.py        # Previsibilidade e metas
├── DASHBOARD/              # Interface Streamlit
│   └── main_app.py
├── DATABASE/               # Scripts de banco de dados
│   └── setup_database.py
├── AUTOMATION/             # Scripts de automação
│   ├── run_all_etls.sh
│   ├── setup_cron.sh
│   └── monitor_system.py
├── DATA/                   # Dados processados
├── LOGS/                   # Logs do sistema
└── requirements.txt
```

---

## 🚀 Instalação

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

## 📊 Módulos do Dashboard

### 🎯 **Módulo 1: Entrada e Origem de Leads**
- **📈 Total de leads** recebidos no período
- **🌐 Distribuição por canal** de origem (orgânico, pago, indicação)
- **⏱️ Tempo médio de resposta** ao lead
- **💰 Custo por lead** por canal de origem
- **📊 Análise de UTMs** e campanhas

### 🔄 **Módulo 2: Funil de Conversão**
- **📊 Conversão por etapa** do funil de vendas
- **⏰ Tempo médio** em cada etapa
- **📉 Taxa de abandono** por etapa
- **🔍 Análise de gargalos** no processo
- **📈 Velocidade de conversão** por lead

### 📞 **Módulo 3: Atividades Comerciais**
- **📞 Contatos realizados** por vendedor
- **🗓️ Reuniões agendadas** e realizadas
- **✅ Follow-ups** e taxas de conclusão
- **📊 Performance de atividades** por tipo
- **⏱️ Tempo médio** por atividade

### 💰 **Módulo 4: Conversão e Receita**
- **✅ Vendas fechadas** e perdidas
- **💰 Receita total** e ticket médio
- **📈 Win rate** por vendedor
- **❌ Análise de motivos** de perda
- **📊 Ciclo de vendas** médio

### 👥 **Módulo 5: Performance por Pessoa e Canal**
- **🏆 Ranking de vendedores** por receita
- **📊 Performance por canal** de origem
- **📈 Conversão por pessoa** e canal
- **📋 Análise de produtividade** detalhada
- **🎯 Metas vs realizado** por vendedor

### 🎯 **Módulo 6: Previsibilidade (Forecast)**
- **📊 Previsão de receita** baseada em dados históricos
- **📈 Análise de gaps** vs metas estabelecidas
- **⚠️ Alertas de risco** para metas
- **💡 Recomendações de ações** para atingir metas
- **📋 Análise de tendências** e sazonalidade

---

## 📈 Métricas Detalhadas

### 🎯 **KPIs Principais**

| Métrica | Descrição | Fórmula | Meta |
|---------|-----------|---------|------|
| **Total de Leads** | Leads recebidos no período | `COUNT(leads)` | Crescimento mensal |
| **Win Rate** | Taxa de conversão de vendas | `vendas_ganhas / total_vendas * 100` | > 25% |
| **Ticket Médio** | Valor médio por venda | `receita_total / vendas_ganhas` | > R$ 5.000 |
| **Tempo de Resposta** | Tempo médio para responder leads | `AVG(response_time_hours)` | < 2 horas |
| **Taxa de Conclusão** | Atividades concluídas | `atividades_concluidas / total_atividades * 100` | > 80% |
| **Ciclo de Vendas** | Tempo médio do lead à venda | `AVG(sales_cycle_days)` | < 30 dias |
| **Custo por Lead** | Custo médio de aquisição | `custo_total / total_leads` | < R$ 200 |
| **ROI Marketing** | Retorno sobre investimento | `(receita - custo) / custo * 100` | > 300% |

### 📊 **Métricas por Canal** *(Exemplos de Benchmark)*

| Canal | Leads | Conversão | Custo/Lead | ROI |
|-------|-------|-----------|------------|-----|
| **Orgânico** | 45% | 28% | R$ 0 | ∞ |
| **Pago** | 25% | 22% | R$ 150 | 250% |
| **Indicação** | 20% | 35% | R$ 50 | 400% |
| **Outbound** | 10% | 15% | R$ 80 | 180% |

*💡 **Nota:** Valores acima são benchmarks de mercado. Seus dados reais serão exibidos no dashboard.*

### 👥 **Métricas por Vendedor** *(Exemplos de Benchmark)*

| Vendedor | Leads | Vendas | Win Rate | Receita | Ticket Médio |
|----------|-------|--------|----------|---------|--------------|
| **Vendedor A** | 150 | 45 | 30% | R$ 225.000 | R$ 5.000 |
| **Vendedor B** | 120 | 36 | 30% | R$ 180.000 | R$ 5.000 |
| **Vendedor C** | 100 | 25 | 25% | R$ 125.000 | R$ 5.000 |

*💡 **Nota:** Valores acima são exemplos. Seus dados reais de vendedores serão exibidos no dashboard.*

### 📊 **Métricas de Crescimento** *(Exemplos de Benchmark)*

| Período | Leads | Crescimento | Vendas | Crescimento | Receita | Crescimento |
|---------|-------|-------------|--------|-------------|---------|-------------|
| **Mês 1** | 1.000 | - | 250 | - | R$ 1.250.000 | - |
| **Mês 2** | 1.200 | +20% | 300 | +20% | R$ 1.500.000 | +20% |
| **Mês 3** | 1.440 | +20% | 360 | +20% | R$ 1.800.000 | +20% |

*💡 **Nota:** Valores acima são exemplos de crescimento saudável. Seus dados reais de crescimento serão calculados automaticamente.*

### 🎯 **Como Ver Suas Métricas Reais:**

1. **Execute o dashboard:** `streamlit run DASHBOARD/main_app.py`
2. **Acesse:** http://localhost:8501
3. **Visualize:** Todos os 6 módulos com dados reais do seu Kommo CRM
4. **Analise:** KPIs, funil de conversão, performance de vendedores e previsões

### 📈 **Métricas Reais Disponíveis no Dashboard:**

- ✅ **Total de leads** recebidos no período selecionado
- ✅ **Win rate** real baseado em vendas ganhas/perdidas
- ✅ **Ticket médio** calculado a partir de vendas fechadas
- ✅ **Tempo de resposta** médio por canal
- ✅ **Taxa de conclusão** de atividades comerciais
- ✅ **Performance por vendedor** com dados reais
- ✅ **Análise de canais** com conversão real
- ✅ **Previsões** baseadas em dados históricos

---

## ⚙️ Automação

### 🔄 **Configurar Cron Jobs**

```bash
bash AUTOMATION/setup_cron.sh
```

### 📅 **Cronograma Automático**

| Horário | Atividade | Descrição |
|---------|-----------|-----------|
| **06:00 diariamente** | ETL Completo | Execução de todos os 6 módulos ETL |
| **A cada 15 min** | Monitor Dashboard | Verificação de saúde do sistema |
| **Domingos 08:00** | Relatórios Semanais | Geração de relatórios de performance |

### 🔍 **Monitoramento**

```bash
# Verificar status do sistema
python AUTOMATION/validate_metrics.py

# Monitorar atualizações
python AUTOMATION/monitor_daily_updates.py

# Garantia de qualidade
python AUTOMATION/quality_assurance.py
```

### 📋 **Logs e Alertas**

- **LOGS/** - Logs detalhados de todas as operações
- **📊 Relatórios automáticos** - Status de execução diário
- **⚠️ Alertas** - Notificações de problemas em tempo real
- **📈 Métricas de saúde** - Performance do sistema

---

## 🗄️ Estrutura do Banco de Dados

### 🏗️ **Principais Tabelas**

| Tabela | Registros | Descrição |
|--------|-----------|-----------|
| **leads_metrics** | ~50.000 | Dados de leads e origens |
| **funnel_history** | ~100.000 | Histórico do funil de vendas |
| **commercial_activities** | ~200.000 | Atividades comerciais |
| **sales_metrics** | ~25.000 | Métricas de vendas e receita |
| **performance_vendedores** | ~1.000 | Performance por vendedor |
| **monthly_forecasts** | ~12 | Previsões e metas mensais |

### 🔍 **Queries Principais**

```sql
-- KPIs Gerais
SELECT 
    COUNT(DISTINCT lead_id) as total_leads,
    COUNT(DISTINCT CASE WHEN status = 'won' THEN lead_id END) as vendas_ganhas,
    ROUND(COUNT(DISTINCT CASE WHEN status = 'won' THEN lead_id END) / 
          COUNT(DISTINCT lead_id) * 100, 2) as win_rate
FROM leads_metrics;

-- Performance por Vendedor
SELECT 
    vendedor,
    COUNT(*) as total_leads,
    COUNT(CASE WHEN status = 'won' THEN 1 END) as vendas,
    ROUND(COUNT(CASE WHEN status = 'won' THEN 1 END) / COUNT(*) * 100, 2) as win_rate
FROM sales_metrics
GROUP BY vendedor
ORDER BY vendas DESC;
```

---

## 🔧 Desenvolvimento

### 🛠️ **Ambiente de Desenvolvimento**

```bash
python3 -m venv dev_env
source dev_env/bin/activate
pip install -r requirements.txt

# Executar testes
python AUTOMATION/quality_assurance.py

# Verificar métricas
python AUTOMATION/validate_metrics.py
```

### ➕ **Adicionar Novos Módulos**

1. **Criar script ETL** em `ETL/`
2. **Adicionar queries** no dashboard
3. **Configurar automação** no cron
4. **Atualizar documentação** e testes

### 🧪 **Testes e Validação**

```bash
# Teste completo do sistema
python AUTOMATION/quality_assurance.py

# Validação de métricas
python AUTOMATION/validate_metrics.py

# Monitoramento de atualizações
python AUTOMATION/monitor_daily_updates.py
```

---

##  Suporte

### 🆘 **Canais de Suporte**

- **Issues**: [GitHub Issues](https://github.com/RaquelFonsec/KommoAnalytics/issues)
- ** Email**: raquel.promptia@gmail.com

### 📋 **FAQ Frequente**

**Q: Como configurar a API do Kommo?**
A: Siga o guia de configuração em `DOCS/api_setup.md`

**Q: O dashboard não carrega, o que fazer?**
A: Execute `python AUTOMATION/health_check.sh` para diagnóstico

**Q: Como adicionar novos KPIs?**
A: Edite o arquivo `DASHBOARD/main_app.py` e adicione suas métricas

---



**Desenvolvido c por Raquel Fonseca**

[![GitHub stars](https://img.shields.io/github/stars/RaquelFonsec/KommoAnalytics?style=social)](https://github.com/RaquelFonsec/KommoAnalytics)
[![GitHub forks](https://img.shields.io/github/forks/RaquelFonsec/KommoAnalytics?style=social)](https://github.com/RaquelFonsec/KommoAnalytics)
[![GitHub issues](https://img.shields.io/github/issues/RaquelFonsec/KommoAnalytics)](https://github.com/RaquelFonsec/KommoAnalytics/issues)


</div>
