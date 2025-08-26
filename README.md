# 📊 Kommo Analytics Dashboard

Sistema completo de ETL e Dashboard para análise de dados do Kommo CRM.

## 🚀 Instalação Rápida

```bash
# 1. Clonar repositório
git clone https://github.com/RaquelFonsec/KommoAnalytics.git
cd KommoAnalytics

# 2. Configurar credenciais
cp env_template.txt .env
# Edite o .env com suas credenciais

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar banco de dados
python DATABASE/setup_database.py

# 5. Executar ETLs
python ETL/kommo_etl_modulo1_leads.py
python ETL/kommo_etl_modulo2_funil.py
python ETL/kommo_etl_modulo3_atividades.py
python ETL/kommo_etl_modulo4_conversao.py
python ETL/kommo_etl_modulo5_performance.py
python ETL/kommo_etl_modulo6_forecast_integrado.py

# 6. Iniciar dashboard
streamlit run DASHBOARD/main_app.py
```

## 📁 Estrutura do Projeto

```
KommoAnalytics/
├── ETL/                    # Sistema ETL (6 módulos)
│   ├── kommo_etl_modulo1_leads.py
│   ├── kommo_etl_modulo2_funil.py
│   ├── kommo_etl_modulo3_atividades.py
│   ├── kommo_etl_modulo4_conversao.py
│   ├── kommo_etl_modulo5_performance.py
│   └── kommo_etl_modulo6_forecast_integrado.py
├── DASHBOARD/              # Dashboard Streamlit
│   └── main_app.py
├── DATABASE/               # Scripts SQL
├── AUTOMATION/             # Scripts de automação
├── DATA/                   # Dados gerados
└── LOGS/                   # Logs do sistema
```

## 🎯 Como Usar

### 1. Executar ETLs
```bash
# Executar todos os ETLs
bash AUTOMATION/run_all_etls.sh

# Ou executar individualmente
python ETL/kommo_etl_modulo1_leads.py
```

### 2. Ver Dashboard
```bash
streamlit run DASHBOARD/main_app.py
# Acesse: http://localhost:8501
```

### 3. Automação
```bash
# Configurar atualização automática
bash AUTOMATION/setup_cron.sh
```

## 📊 Métricas Disponíveis

- ✅ **Módulo 1 - Entrada de Leads**: Total, por canal, tempo resposta
- ✅ **Módulo 2 - Funil de Vendas**: Conversão por etapa, tempo por etapa  
- ✅ **Módulo 3 - Atividade Comercial**: Contatos, reuniões, follow-ups
- ✅ **Módulo 4 - Receita**: Vendas fechadas, ticket médio, win rate
- ✅ **Módulo 5 - Performance**: Rankings, análise por canal
- ✅ **Módulo 6 - Forecast**: Pipeline atual, previsões

## 🔧 Configuração

Edite o arquivo `.env` com suas credenciais:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=kommo_analytics
DB_PASSWORD=sua_senha_mysql
DB_NAME=kommo_analytics
```

## 🚀 Automação

O sistema está configurado para:
- ✅ **Atualização diária** às 6h
- ✅ **Monitoramento contínuo** do dashboard
- ✅ **Validação automática** de métricas
- ✅ **Logs detalhados** de todas as operações

## 📞 Suporte

- 📖 Documentação: ./DOCS/
- 🐛 Issues: [GitHub Issues](https://github.com/RaquelFonsec/KommoAnalytics/issues)
- 📧 Contato: raquel.fonseca@example.com
