# Kommo Analytics Dashboard

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-red)
![MySQL](https://img.shields.io/badge/MySQL-8.0%2B-orange)
![License](https://img.shields.io/badge/License-MIT-green)

Sistema completo de Business Intelligence para Kommo CRM com ETL automatizado e dashboard interativo em tempo real.

## 🌟 Visão Geral

O **Kommo Analytics Dashboard** é uma solução de Business Intelligence que transforma dados brutos do Kommo CRM em insights acionáveis. Integra 6 módulos ETL especializados que processam dados em tempo real, oferecendo uma visão completa do funil de vendas.

### ✨ Características Principais

- **ETL Automatizado**: 6 módulos especializados processando dados em tempo real
- **Dashboard Interativo**: Interface Streamlit moderna e responsiva
- **Automação Completa**: Cron jobs para atualizações automáticas
- **Métricas Avançadas**: KPIs, funil de conversão e previsões
- **Validação de Qualidade**: Sistema de monitoramento e alertas
- **Design Responsivo**: Funciona em desktop e mobile

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

## 🚀 Instalação

### Pré-requisitos

- Python 3.8+
- MySQL 8.0+
- Conta Kommo CRM com API habilitada
- Linux/Ubuntu (recomendado para automação)

### 1. Clone o Repositório

```bash
git clone https://github.com/RaquelFonsec/KommoAnalytics.git
cd KommoAnalytics
```

### 2. Configure o Ambiente Virtual

```bash
python3 -m venv dashboard_env
source dashboard_env/bin/activate
pip install -r requirements.txt
```

### 3. Configure o Banco de Dados

```bash
# Instalar MySQL (se necessário)
sudo apt update
sudo apt install mysql-server -y

# Configurar banco
python DATABASE/setup_database.py
```

### 4. Configure as Credenciais

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

### 5. Execute os ETLs

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

### 6. Inicie o Dashboard

```bash
streamlit run DASHBOARD/main_app.py
```

**Acesse:** [http://localhost:8501](http://localhost:8501)

## 📊 Módulos do Dashboard

### 🎯 Módulo 1: Entrada e Origem de Leads
- Total de leads recebidos
- Distribuição por canal de origem
- Tempo médio de resposta
- Custo por lead por canal

### 🔄 Módulo 2: Funil de Conversão
- Conversão por etapa do funil
- Tempo médio em cada etapa
- Taxa de abandono
- Análise de gargalos

### 📞 Módulo 3: Atividades Comerciais
- Contatos realizados por vendedor
- Reuniões agendadas e realizadas
- Follow-ups e taxas de conclusão
- Performance de atividades

### 💰 Módulo 4: Conversão e Receita
- Vendas fechadas e perdidas
- Receita total e ticket médio
- Win rate por vendedor
- Análise de motivos de perda

### 👥 Módulo 5: Performance por Pessoa e Canal
- Ranking de vendedores
- Performance por canal de origem
- Conversão por pessoa
- Análise de produtividade

### 🎯 Módulo 6: Previsibilidade (Forecast)
- Previsão de receita
- Análise de gaps vs metas
- Alertas de risco
- Recomendações de ações

## ⚙️ Automação

### Configurar Cron Jobs

```bash
bash AUTOMATION/setup_cron.sh
```

### Cronograma Automático

- **06:00 diariamente** - Execução completa de todos ETLs
- **A cada 15 min** - Monitoramento do dashboard
- **Domingos 08:00** - Relatórios semanais

### Monitoramento

```bash
# Verificar status do sistema
python AUTOMATION/validate_metrics.py

# Monitorar atualizações
python AUTOMATION/monitor_daily_updates.py

# Garantia de qualidade
python AUTOMATION/quality_assurance.py
```

## 📈 Principais Métricas

| Métrica | Descrição | Fórmula |
|---------|-----------|---------|
| Total de Leads | Leads recebidos no período | COUNT(leads) |
| Win Rate | Taxa de conversão | vendas_ganhas / total_vendas * 100 |
| Ticket Médio | Valor médio por venda | receita_total / vendas_ganhas |
| Tempo de Resposta | Tempo médio para responder leads | AVG(response_time_hours) |
| Taxa de Conclusão | Atividades concluídas | atividades_concluidas / total_atividades * 100 |

## 🗄️ Estrutura do Banco de Dados

### Principais Tabelas

- **leads_metrics** - Dados de leads e origens
- **funnel_history** - Histórico do funil de vendas
- **commercial_activities** - Atividades comerciais
- **sales_metrics** - Métricas de vendas e receita
- **performance_vendedores** - Performance por vendedor
- **monthly_forecasts** - Previsões e metas

## 🔧 Desenvolvimento

### Ambiente de Desenvolvimento

```bash
python3 -m venv dev_env
source dev_env/bin/activate
pip install -r requirements.txt

# Executar testes
python AUTOMATION/quality_assurance.py

# Verificar métricas
python AUTOMATION/validate_metrics.py
```

### Adicionar Novos Módulos

1. Criar script ETL em `ETL/`
2. Adicionar queries no dashboard
3. Configurar automação
4. Atualizar documentação

##  Suporte

- **Issues**: [GitHub Issues](https://github.com/RaquelFonsec/KommoAnalytics/issues)
- **Email**: raquel.promptia@gmail.com
- **Documentação**: [Wiki do Projeto](https://github.com/RaquelFonsec/KommoAnalytics/wiki)




**Desenvolvido  por [Raquel Fonseca](https://github.com/RaquelFonsec)**
