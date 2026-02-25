import subprocess
import logging
import sys

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_script(script_name):
    logger.info(f"🏁 Iniciando sub-tarea: {script_name}")
    try:
        # Ejecuta el script y espera a que termine
        result = subprocess.run(['python', script_name], capture_output=True, text=True)
        
        # Loguear la salida
        if result.stdout:
            logger.info(f"Output de {script_name}:\n{result.stdout}")
        
        if result.returncode == 0:
            logger.info(f"✅ {script_name} finalizó correctamente.")
        else:
            logger.error(f"❌ {script_name} falló (código {result.returncode}). Error:\n{result.stderr}")
            
    except Exception as e:
        logger.error(f"🔥 Error crítico ejecutando {script_name}: {e}")

def main():
    logger.info("📅 INICIANDO PROCESO DIARIO DE AUTOMATIZACIÓN")
    logger.info("="*50)
    
    # 1. Ejecutar Recordatorios (Citas para mañana)
    run_script('recordatorio_citas.py')
    
    logger.info("-" * 50)
    
    # 2. Ejecutar Seguimiento Feedback (Citas de ayer)
    run_script('seguimiento_citas.py')
    
    logger.info("="*50)
    logger.info("✅ PROCESO DIARIO FINALIZADO")

if __name__ == "__main__":
    main()
