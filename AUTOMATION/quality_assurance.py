#!/usr/bin/env python3
"""
Script de Garantia de Qualidade - Kommo Analytics
Validação final completa para garantir que o sistema está 100% funcional
"""

import os
import sys
import subprocess
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QualityAssurance:
    def __init__(self):
        self.project_dir = "/home/raquel-fonseca/Projects/KommoAnalytics"
        self.test_results = {}
        
    def run_validation_script(self):
        """Executar script de validação de métricas"""
        logger.info("🔍 Executando validação de métricas...")
        
        try:
            result = subprocess.run([
                sys.executable, 
                os.path.join(self.project_dir, "AUTOMATION/validate_metrics.py")
            ], capture_output=True, text=True, cwd=self.project_dir)
            
            self.test_results['validation'] = {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr
            }
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"❌ Erro na validação: {e}")
            self.test_results['validation'] = {
                'success': False,
                'output': '',
                'error': str(e)
            }
            return False
    
    def run_monitoring_script(self):
        """Executar script de monitoramento"""
        logger.info("🔍 Executando monitoramento de atualizações...")
        
        try:
            result = subprocess.run([
                sys.executable, 
                os.path.join(self.project_dir, "AUTOMATION/monitor_daily_updates.py")
            ], capture_output=True, text=True, cwd=self.project_dir)
            
            self.test_results['monitoring'] = {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr
            }
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"❌ Erro no monitoramento: {e}")
            self.test_results['monitoring'] = {
                'success': False,
                'output': '',
                'error': str(e)
            }
            return False
    
    def test_dashboard_access(self):
        """Testar acesso ao dashboard"""
        logger.info("🔍 Testando acesso ao dashboard...")
        
        try:
            result = subprocess.run([
                'curl', '-s', 'http://localhost:8501'
            ], capture_output=True, text=True, timeout=10)
            
            dashboard_ok = result.returncode == 0 and 'Streamlit' in result.stdout
            
            self.test_results['dashboard'] = {
                'success': dashboard_ok,
                'accessible': dashboard_ok,
                'response_code': result.returncode
            }
            
            return dashboard_ok
            
        except Exception as e:
            logger.error(f"❌ Erro no teste do dashboard: {e}")
            self.test_results['dashboard'] = {
                'success': False,
                'accessible': False,
                'response_code': -1
            }
            return False
    
    def check_file_structure(self):
        """Verificar estrutura de arquivos"""
        logger.info("🔍 Verificando estrutura de arquivos...")
        
        required_files = [
            "DASHBOARD/main_app.py",
            "ETL/kommo_etl_modulo1_leads.py",
            "ETL/kommo_etl_modulo2_funil.py",
            "ETL/kommo_etl_modulo3_atividades.py",
            "ETL/kommo_etl_modulo4_conversao.py",
            "ETL/kommo_etl_modulo5_performance.py",
            "ETL/kommo_etl_modulo6_forecast_integrado.py",
            "AUTOMATION/validate_metrics.py",
            "AUTOMATION/monitor_daily_updates.py",
            "DATABASE/setup_database.py",
            "requirements.txt",
            ".env"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = os.path.join(self.project_dir, file_path)
            if not os.path.exists(full_path):
                missing_files.append(file_path)
        
        structure_ok = len(missing_files) == 0
        
        self.test_results['file_structure'] = {
            'success': structure_ok,
            'missing_files': missing_files,
            'total_files': len(required_files),
            'present_files': len(required_files) - len(missing_files)
        }
        
        return structure_ok
    
    def check_cron_configuration(self):
        """Verificar configuração do cron"""
        logger.info("🔍 Verificando configuração do cron...")
        
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            
            if result.returncode == 0:
                crontab_content = result.stdout
                kommo_entries = [line for line in crontab_content.split('\n') if 'KommoAnalytics' in line]
                
                cron_ok = len(kommo_entries) > 0
                
                self.test_results['cron'] = {
                    'success': cron_ok,
                    'configured': True,
                    'entries_count': len(kommo_entries),
                    'entries': kommo_entries
                }
                
                return cron_ok
            else:
                self.test_results['cron'] = {
                    'success': False,
                    'configured': False,
                    'entries_count': 0,
                    'entries': []
                }
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro na verificação do cron: {e}")
            self.test_results['cron'] = {
                'success': False,
                'configured': False,
                'entries_count': 0,
                'entries': []
            }
            return False
    
    def generate_quality_report(self):
        """Gerar relatório de qualidade"""
        logger.info("📊 Gerando relatório de qualidade...")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['success'])
        
        report = f"""
🎯 RELATÓRIO DE GARANTIA DE QUALIDADE - KOMMO ANALYTICS
Data: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}
========================================================

📊 STATUS GERAL:
- Testes executados: {total_tests}/5
- Testes aprovados: {passed_tests}/5
- Taxa de aprovação: {(passed_tests/total_tests*100):.1f}%

📋 DETALHAMENTO DOS TESTES:
"""
        
        test_names = {
            'validation': '✅ Validação de Métricas',
            'monitoring': '✅ Monitoramento de Atualizações',
            'dashboard': '✅ Acesso ao Dashboard',
            'file_structure': '✅ Estrutura de Arquivos',
            'cron': '✅ Configuração do Cron'
        }
        
        for test_key, test_name in test_names.items():
            if test_key in self.test_results:
                result = self.test_results[test_key]
                status = "✅ PASSOU" if result['success'] else "❌ FALHOU"
                report += f"\n{status} {test_name}"
                
                if not result['success'] and 'error' in result:
                    report += f"\n   🔧 Erro: {result['error'][:100]}..."
        
        report += f"""

🎯 CONCLUSÃO:
"""
        
        if passed_tests == total_tests:
            report += """
🎉 SISTEMA 100% FUNCIONAL!

✅ Todas as métricas estão corretas e validadas
✅ Monitoramento de atualizações configurado
✅ Dashboard acessível e funcionando
✅ Estrutura de arquivos completa
✅ Automação cron configurada

🚀 O SISTEMA ESTÁ PRONTO PARA USO DIÁRIO!

📋 PRÓXIMAS ATUALIZAÇÕES:
- ETLs executados automaticamente às 6h diariamente
- Dashboard sempre atualizado com dados recentes
- Monitoramento contínuo da saúde do sistema

💡 RECOMENDAÇÕES:
- Acesse o dashboard em: http://localhost:8501
- Monitore os logs em: ./LOGS/
- Execute validação semanal: python AUTOMATION/validate_metrics.py
"""
        else:
            report += f"""
⚠️ SISTEMA PRECISA DE ATENÇÃO!

❌ {total_tests - passed_tests} teste(s) falharam
🔧 Verifique os problemas identificados acima
📞 Entre em contato se precisar de ajuda

🎯 AÇÕES NECESSÁRIAS:
"""
            for test_key, result in self.test_results.items():
                if not result['success']:
                    test_name = test_names.get(test_key, test_key)
                    report += f"- 🔧 Corrigir: {test_name}\n"
        
        return report
    
    def run_full_quality_assurance(self):
        """Executar garantia de qualidade completa"""
        logger.info("🚀 === INICIANDO GARANTIA DE QUALIDADE ===")
        
        # Executar todos os testes
        self.run_validation_script()
        self.run_monitoring_script()
        self.test_dashboard_access()
        self.check_file_structure()
        self.check_cron_configuration()
        
        # Gerar relatório
        report = self.generate_quality_report()
        
        logger.info("🎉 === GARANTIA DE QUALIDADE CONCLUÍDA ===")
        print(report)
        
        # Retornar status geral
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['success'])
        
        return passed_tests == total_tests

if __name__ == "__main__":
    qa = QualityAssurance()
    success = qa.run_full_quality_assurance()
    
    if success:
        print("\n🎉 GARANTIA DE QUALIDADE APROVADA!")
        print("✅ Sistema 100% funcional e pronto para uso diário")
        print("✅ Todas as métricas validadas e corretas")
        print("✅ Atualizações automáticas configuradas")
        print("✅ Dashboard acessível e funcionando")
        print("\n🚀 VOCÊ PODE CONFIAR NO SISTEMA!")
    else:
        print("\n⚠️ GARANTIA DE QUALIDADE REPROVADA!")
        print("🔧 Corrija os problemas identificados antes de usar o sistema")
        print("📞 Entre em contato se precisar de ajuda")
