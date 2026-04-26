import requests
import json
from datetime import datetime, timedelta
from config import ACCESS_TOKEN, PHONE_NUMBER_ID

class WhatsAppTokenChecker:
    def __init__(self, token, phone_id):
        self.token = token
        self.phone_id = phone_id
        self.headers = {"Authorization": f"Bearer {token}"}
        self.results = {}
    
    def check_all(self):
        """Ejecuta todas las verificaciones"""
        print("=" * 70)
        print("SEARCH VERIFICACION AVANZADA DE TOKEN WHATSAPP")
        print("=" * 70)
        
        checks = [
            ("1. Conexión básica", self.check_basic_connection),
            ("2. Permisos del token", self.check_token_permissions),
            ("3. Configuración webhook", self.check_webhook),
            ("4. Prueba de envío", self.test_send_message),
            ("5. Plantillas disponibles", self.check_templates),
        ]
        
        for name, check_func in checks:
            print(f"\n{name}...")
            success, message = check_func()
            self.results[name] = {"success": success, "message": message}
            
            if success:
                print(f"   [OK] {message}")
            else:
                print(f"   [ERROR] {message}")
        
        self.print_summary()
    
    def check_basic_connection(self):
        """Verifica conexión básica al API"""
        try:
            url = f"https://graph.facebook.com/v19.0/{self.phone_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                info = f"Phone: {data.get('display_phone_number')}, Name: {data.get('verified_name', 'N/A')}"
                return True, info
            else:
                return False, f"Error {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, f"Error de conexión: {e}"
    
    def check_token_permissions(self):
        """Verifica permisos y expiración del token"""
        try:
            debug_url = "https://graph.facebook.com/debug_token"
            params = {"input_token": self.token, "access_token": self.token}
            response = requests.get(debug_url, params=params, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json().get('data', {})
                
                if not data.get('is_valid'):
                    return False, "Token marcado como inválido"
                
                # Verificar expiración
                expires_at = data.get('expires_at')
                if expires_at:
                    exp_date = datetime.fromtimestamp(expires_at)
                    now = datetime.now()
                    
                    if exp_date < now:
                        return False, f"Token expiró el {exp_date}"
                    
                    days_left = (exp_date - now).days
                    if days_left <= 7:
                        return True, f"Token expira en {days_left} días ({exp_date})"
                    else:
                        return True, f"Token válido por {days_left} días"
                
                return True, "Token válido (sin fecha de expiración)"
            else:
                return False, f"No se pudo debuguear token"
                
        except Exception as e:
            return False, f"Error: {e}"
    
    def check_webhook(self):
        """Verifica configuración de webhook"""
        try:
            url = f"https://graph.facebook.com/v19.0/{self.phone_id}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                webhook = data.get('webhook_configuration', {})
                
                if webhook:
                    app_url = webhook.get('application', 'N/A')
                    return True, f"Webhook configurado: {app_url}"
                else:
                    return False, "Webhook no configurado"
            else:
                return False, "No se pudo verificar webhook"
                
        except Exception as e:
            return False, f"Error: {e}"
    
    def test_send_message(self):
        """Prueba enviando un mensaje de prueba"""
        try:
            test_number = "54111551511579"  # Número transformado para sandbox
            
            url = f"https://graph.facebook.com/v19.0/{self.phone_id}/messages"
            payload = {
                "messaging_product": "whatsapp",
                "to": test_number,
                "type": "template",
                "template": {
                    "name": "hello_world",
                    "language": {"code": "en_US"}
                }
            }
            
            response = requests.post(url, json=payload, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                msg_id = response.json().get('messages', [{}])[0].get('id', 'N/A')
                return True, f"Mensaje enviado: {msg_id}"
            else:
                error = response.json().get('error', {})
                error_code = error.get('code', 'N/A')
                error_msg = error.get('message', 'N/A')
                return False, f"Error {error_code}: {error_msg}"
                
        except Exception as e:
            return False, f"Error de envío: {e}"
    
    def check_templates(self):
        """Verifica plantillas disponibles"""
        try:
            url = f"https://graph.facebook.com/v19.0/{self.phone_id}/message_templates"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                templates = response.json().get('data', [])
                approved = [t for t in templates if t.get('status') == 'APPROVED']
                return True, f"{len(approved)} plantillas aprobadas"
            else:
                return False, "No se pudieron obtener plantillas"
                
        except Exception as e:
            return False, f"Error: {e}"
    
    def print_summary(self):
        """Muestra resumen de verificaciones"""
        print("\nRESUMEN DE VERIFICACION")
        print("=" * 70)
        
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results.values() if r['success'])
        
        print(f"Checks realizados: {total_checks}")
        print(f"Checks exitosos: {passed_checks}")
        print(f"Checks fallidos: {total_checks - passed_checks}")
        
        if passed_checks == total_checks:
            print("\nESTADO: Token 100% FUNCIONAL")
        elif passed_checks >= total_checks - 1:
            print("\nESTADO: Token PARCIALMENTE funcional")
        else:
            print("\nESTADO: Token con PROBLEMAS")
        
        print("\nDetalles por check:")
        for check_name, result in self.results.items():
            status = "[OK]" if result['success'] else "[ERROR]"
            print(f"  {status} {check_name}: {result['message']}")
        
        print("=" * 70)



# Uso del checker
if __name__ == "__main__":
    # Usa las credenciales configuradas en el sistema
    TOKEN = ACCESS_TOKEN
    PHONE_ID = PHONE_NUMBER_ID
    
    checker = WhatsAppTokenChecker(TOKEN, PHONE_ID)
    checker.check_all()