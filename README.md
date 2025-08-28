<<<<<<< HEAD
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
=======
# KommoAnalytics
>>>>>>> abc062144b064fd89eba2e98b8de3788ce386ac2
