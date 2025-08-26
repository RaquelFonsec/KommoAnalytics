# 📊 Kommo Analytics Dashboard

Sistema completo de ETL e Dashboard para análise de dados do Kommo CRM.

## 🚀 Instalação Rápida

```bash
# 1. Criar estrutura de pastas
python create_structure.py

# 2. Colocar seu código ETL
# Cole seu arquivo kommo_etl.py em: ETL/kommo_etl.py

# 3. Configurar credenciais
cp .env.template .env
# Edite o .env com suas credenciais

# 4. Instalar dependências
pip install -r SETUP/requirements.txt

# 5. Configurar banco de dados
mysql -u root -p < DATABASE/schema.sql

# 6. Executar sistema
python main.py
```

## 📁 Estrutura do Projeto

```
kommo-analytics/
├── ETL/                    # Sistema ETL
│   ├── kommo_etl.py       # 👈 SEU CÓDIGO AQUI
│   └── config.py          # Configurações
├── DASHBOARD/              # Dashboard Streamlit
├── DATABASE/               # Scripts SQL
├── DATA/                   # Dados gerados
└── main.py                # Script principal
```

## 🎯 Como Usar

### 1. Sincronizar Dados
```bash
python main.py
# Escolha opção 1
```

### 2. Ver Dashboard
```bash
python main.py  
# Escolha opção 2
# Acesse: http://localhost:8501
```

### 3. Modo Completo
```bash
python main.py
# Escolha opção 3 (sincroniza + dashboard)
```

## 📊 Métricas Disponíveis

- ✅ **Entrada de Leads**: Total, por canal, tempo resposta
- ✅ **Funil de Vendas**: Conversão por etapa, tempo por etapa  
- ✅ **Atividade Comercial**: Contatos, reuniões, follow-ups
- ✅ **Receita**: Vendas fechadas, ticket médio, win rate
- ✅ **Performance**: Rankings, análise por canal
- ✅ **Forecast**: Pipeline atual, previsões

## 🔧 Configuração

Edite o arquivo `.env` com suas credenciais:

```env
KOMMO_API_KEY=sua_api_key_aqui
KOMMO_ACCOUNT_ID=seu_account_id
DB_PASSWORD=sua_senha_mysql
```

## 📞 Suporte

- 📧 Email: suporte@empresa.com
- 📖 Docs: ./DOCS/
- 🐛 Issues: GitHub Issues
