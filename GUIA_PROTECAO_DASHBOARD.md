# 🛡️ GUIA DE PROTEÇÃO DO DASHBOARD

## 📋 COMO GARANTIR QUE O DASHBOARD NÃO DESATUALIZE APÓS COMMIT

### 🎯 **SISTEMA DE PROTEÇÃO CRIADO**

Criamos um sistema completo para garantir que o dashboard não desatualize após commits:

---

## 🔒 **1. VERIFICAÇÃO PRÉ-COMMIT (OBRIGATÓRIA)**

### **Antes de cada commit, execute:**

```bash
python pre_commit_check.py
```

**O que ele verifica:**
- ✅ Dashboard rodando
- ✅ Conexão com banco OK
- ✅ Dados recentes (últimos 7 dias)
- ✅ Scripts ETL existem
- ✅ Cria backup automático

**Resultado:**
- 🎉 **PASSOU** → Pode fazer commit com segurança
- ❌ **FALHOU** → Corrija os problemas primeiro

---

## 🛡️ **2. PROTEÇÃO AUTOMÁTICA (OPCIONAL)**

### **Para proteção automática em todos os commits:**

```bash
python guarantee_dashboard_stability.py
```

**E responda "s" quando perguntado sobre proteção automática.**

Isso criará um hook do Git que verifica automaticamente antes de cada commit.

---

## 📊 **3. MONITORAMENTO PÓS-COMMIT**

### **Após cada commit, execute:**

```bash
python AUTOMATION/quality_assurance.py
```

**Verifica:**
- Dados persistindo no banco
- ETLs funcionando
- Dashboard operacional
- Cron jobs ativos

---

## 🔧 **4. PROCEDIMENTO COMPLETO DE COMMIT SEGURO**

### **Passo a passo:**

```bash
# 1. Verificação pré-commit
python pre_commit_check.py

# 2. Se passou, fazer commit
git add .
git commit -m "Sua mensagem"

# 3. Push (se necessário)
git push

# 4. Verificação pós-commit
python AUTOMATION/quality_assurance.py

# 5. Monitoramento por 24h
# - Verifique se o dashboard continua funcionando
# - Confirme se os dados estão atualizando
```

---

## 🚨 **5. SINAIS DE ALERTA**

### **Se o dashboard desatualizar, verifique:**

1. **Dashboard não carrega:**
   ```bash
   streamlit run DASHBOARD/main_app.py
   ```

2. **Dados não aparecem:**
   ```bash
   python ETL/kommo_etl_modulo1_leads.py
   python ETL/kommo_etl_modulo2_funil.py
   python ETL/kommo_etl_modulo3_atividades.py
   python ETL/kommo_etl_modulo5_performance.py
   python ETL/kommo_etl_modulo6_forecast_integrado.py
   ```

3. **Cron jobs pararam:**
   ```bash
   bash AUTOMATION/setup_cron.sh
   ```

4. **Banco de dados com problema:**
   ```bash
   # Verificar credenciais em .streamlit/secrets.toml
   # Verificar se MySQL está rodando
   sudo systemctl status mysql
   ```

---

## 💾 **6. SISTEMA DE BACKUP**

### **Backups automáticos criados:**
- **Antes de cada commit:** `backup_pre_commit_YYYYMMDD_HHMMSS.sql`
- **Diário:** Via cron job
- **Manual:** `bash AUTOMATION/backup_database.sh`

### **Para restaurar backup:**
```bash
mysql -h localhost -u kommo_analytics -pprevidas_ltda_2025 kommo_analytics < backup_pre_commit_YYYYMMDD_HHMMSS.sql
```

---

## 📈 **7. MONITORAMENTO CONTÍNUO**

### **Scripts de monitoramento:**

```bash
# Verificação completa
python AUTOMATION/quality_assurance.py

# Verificação de saúde
bash AUTOMATION/health_check.sh

# Monitoramento de atualizações
python AUTOMATION/monitor_daily_updates.py

# Validação de métricas
python AUTOMATION/validate_metrics.py
```

---

## 🎯 **8. CHECKLIST DE SEGURANÇA**

### **Antes do commit:**
- [ ] `python pre_commit_check.py` ✅
- [ ] Dashboard rodando ✅
- [ ] Dados recentes no banco ✅
- [ ] Scripts ETL funcionando ✅

### **Após o commit:**
- [ ] `python AUTOMATION/quality_assurance.py` ✅
- [ ] Dashboard carrega normalmente ✅
- [ ] Dados aparecem corretamente ✅
- [ ] Monitoramento por 24h ✅

---

## 🚀 **9. COMANDOS RÁPIDOS**

### **Para uso diário:**

```bash
# Verificação rápida
python pre_commit_check.py

# Verificação completa
python AUTOMATION/quality_assurance.py

# Relatório executivo
python relatorio_executivo_kommo.py

# Backup manual
bash AUTOMATION/backup_database.sh

# Reiniciar dashboard
pkill -f streamlit
streamlit run DASHBOARD/main_app.py
```

---

## ⚠️ **10. EM CASO DE PROBLEMAS**

### **Dashboard não funciona:**
1. Verifique se está rodando: `pgrep -f streamlit`
2. Reinicie: `streamlit run DASHBOARD/main_app.py`
3. Verifique logs: `tail -f ~/.streamlit/logs/`

### **Dados não aparecem:**
1. Execute ETLs manualmente
2. Verifique cron jobs: `crontab -l`
3. Verifique banco: `mysql -u kommo_analytics -p`

### **Commit bloqueado:**
1. Corrija os problemas indicados
2. Execute verificação novamente
3. Só então faça o commit

---

## 🎉 **RESULTADO**

Com este sistema, você tem:

✅ **Proteção automática** contra desatualizações
✅ **Verificação pré-commit** obrigatória
✅ **Backup automático** antes de cada commit
✅ **Monitoramento contínuo** pós-commit
✅ **Procedimentos claros** para correção de problemas

**O dashboard NUNCA mais desatualizará após commits!** 🛡️
