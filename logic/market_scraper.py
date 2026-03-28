"""
Módulo de Scraping y Análisis de Mercado Inmobiliario
Extrae datos de portales inmobiliarios argentinos y genera estadísticas de mercado
"""
import os
import sys
import json
import time
import random
import logging
import re
import requests
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ========================================
# ESTRUCTURAS DE DATOS
# ========================================

@dataclass
class PropertyData:
    """Representa una propiedad extraída de cualquier portal"""
    source: str
    external_id: str
    title: str
    price_amount: float
    price_currency: str
    price_per_m2: float
    surface_total: float
    surface_covered: float
    location: str
    address: str
    property_type: str
    operation_type: str
    rooms: Optional[int] = None
    url: str = ""
    raw_data: Dict = field(default_factory=dict)

@dataclass
class MarketStats:
    """Estadísticas calculadas del mercado"""
    zone: str
    operation_type: str
    property_type: str
    sample_size: int
    average_price_per_m2: Optional[float]
    average_total_price: Optional[float]
    median_price_per_m2: Optional[float]
    min_price_per_m2: Optional[float]
    max_price_per_m2: Optional[float]
    price_range_total: Optional[str]
    currency_distribution: Dict[str, int]
    source_breakdown: Dict[str, int]
    properties: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

# ========================================
# CLASE BASE DEL SCRAPER
# ========================================

class BaseScraper(ABC):
    """Clase base para todos los scrapers de portales inmobiliarios"""
    
    def __init__(self, base_url: str, source_name: str):
        self.base_url = base_url
        self.source_name = source_name
        self.target_zone = ""  # Barrio actual que se está buscando
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """Configura la sesión con headers anti-bot"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        ]
        
        self.session.headers.update({
            "User-Agent": random.choice(user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        })
    
    def _normalize_zone(self, zone: str) -> str:
        """Normaliza el nombre del barrio para URLs"""
        if not zone:
            return ""
        z = zone.lower().strip()
        
        # Eliminar 's' final de error común (luganos -> lugano)
        # pero NO para barrios que terminan en s (flores, mataderos, etc)
        barrios_con_s = ["flores", "mataderos", "lomas", "pompeya", "chacrita"] # pompeya no, mataderos sí
        if z.endswith('s') and z not in barrios_con_s and not z.endswith('es'):
             z = z[:-1]

        # Mapeo manual de barrios CABA para URLs
        mapping = {
            "lugano": "villa-lugano",
            "villa lugano": "villa-lugano",
            "villa luganos": "villa-lugano",
            "barracas": "barracas",
            "constitucion": "constitucion",
            "once": "balvanera",
            "microcentro": "san-nicolas",
            "abasto": "almagro",
            "congreso": "balvanera"
        }
        
        if z in mapping:
            return mapping[z]
            
        return z.replace(" ", "-")

    def _clean_price(self, price_text: str) -> tuple:
        """
        Limpia texto de precio y devuelve (amount, currency).
        """
        
        if not price_text:
            return 0.0, "ARS"
        
        original_text = price_text
        price_text = price_text.strip().upper()
        
        # ========================================
        # 1. DETECCIÓN DE MONEDA (MEJORADA)
        # ========================================
        currency = "ARS"  # Por defecto
        
        # Detectar explícitamente dólares
        usd_indicators = ["US$", "U$S", "USD", "DÓLARES", "DOLARES", "USS"]
        for indicator in usd_indicators:
            if indicator in price_text:
                currency = "USD"
                # Si encontramos US$, eliminamos el símbolo para no confundir después
                if indicator == "US$" or indicator == "U$S":
                    price_text = price_text.replace(indicator, "")
                break
        
        # ========================================
        # 2. LIMPIEZA DE TEXTO
        # ========================================
        # Manejar casos con "+" (precio + expensas)
        if '+' in price_text:
            price_text = price_text.split('+')[0].strip()
        
        # Eliminar "EXPENSAS" y textos similares
        price_text = re.sub(r'EXPENSAS.*', '', price_text, flags=re.IGNORECASE)
        price_text = re.sub(r'ALQUILER.*', '', price_text, flags=re.IGNORECASE)
        price_text = re.sub(r'VENTA.*', '', price_text, flags=re.IGNORECASE)
        
        # Eliminar cualquier símbolo de moneda que haya quedado
        price_text = re.sub(r'[$€]', '', price_text)
        
        # ========================================
        # 3. EXTRACCIÓN DE NÚMEROS
        # ========================================
        # Extraer todos los números (incluyendo los que tienen puntos)
        all_numbers = re.findall(r'[\d.]+', price_text)
        
        if not all_numbers:
            return 0.0, currency
        
        # Limpiar puntos de miles y convertir a número
        clean_numbers = []
        for num_str in all_numbers:
            # Eliminar puntos (separadores de miles) pero mantener el número
            clean_num = num_str.replace('.', '')
            if clean_num.isdigit():
                clean_numbers.append(clean_num)
        
        if not clean_numbers:
            return 0.0, currency
        
        # ========================================
        # 4. SELECCIONAR EL NÚMERO MÁS PROBABLE
        # ========================================
        # El primer número suele ser el precio principal
        full_number = clean_numbers[0]
        
        # Si hay más números y el primero es muy corto, considerar unirlos
        if len(clean_numbers) >= 2 and len(clean_numbers[0]) < 4:
            # Posiblemente es un número partido (ej: "150" "000")
            full_number = ''.join(clean_numbers[:3])  # Unir hasta 3 grupos
        
        try:
            value = float(full_number)
        except ValueError:
            return 0.0, currency
        
        # ========================================
        # 5. VALIDACIÓN POR RANGOS (MEJORADA)
        # ========================================
        # Rangos realistas para inmuebles en Argentina
        if currency == "USD":
            # USD: 10,000 - 3,000,000 (alquileres desde 10k USD, propiedades hasta 3M USD)
            min_price = 5_000
            max_price = 3_000_000
            
            # Si el precio está fuera de rango pero es plausible como ARS, corregir moneda
            if value < min_price or value > max_price:
                # Verificar si es un precio típico en ARS
                if 50_000 <= value <= 500_000_000:
                    currency = "ARS"
        else:
            # ARS: 30,000 - 500,000,000
            min_price = 30_000
            max_price = 500_000_000
            
            # Si el precio es muy bajo para ARS pero típico en USD, corregir
            if value < min_price and 10_000 <= value <= 3_000_000:
                currency = "USD"
        
        # Validar rango final
        if min_price <= value <= max_price:
            return value, currency
        
        # ========================================
        # 6. FALLBACK: intentar con otros números
        # ========================================
        for num_str in clean_numbers[1:4]:  # Probar los siguientes números
            try:
                val = float(num_str)
                if min_price <= val <= max_price:
                    return val, currency
            except ValueError:
                continue
        
        return 0.0, currency
    
    
    
    
    
    def _clean_surface(self, surface_text: str) -> float:
        """
        Limpia texto de superficie y devuelve metros cuadrados
        Ej: "85 m²" -> 85.0
        """
        if not surface_text:
            return 0.0
        
        # Extraer números
        numbers = re.findall(r'[\d.,]+', surface_text)
        if not numbers:
            return 0.0
        
        try:
            surface = float(numbers[0].replace(',', '.'))
            return surface
        except ValueError:
            return 0.0
    
    def _calculate_price_per_m2(self, price: float, surface: float, currency: str) -> float:
        """Calcula precio por metro cuadrado"""
        if surface <= 0:
            return 0.0
        return price / surface
    
    def _make_request(self, url: str, max_retries: int = 3) -> Optional[str]:
        """Realiza request con reintentos y delay"""
        for attempt in range(max_retries):
            try:
                # Delay aleatorio para evitar bloqueos
                time.sleep(random.uniform(1.5, 3.5))
                
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    return response.text
                elif response.status_code in [429, 403, 503]:
                    wait_time = (2 ** attempt) * random.uniform(2, 4)
                    logger.warning(f"[{self.source_name}] Error {response.status_code}, esperando {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"[{self.source_name}] Error {response.status_code}: {url}")
                    
            except Exception as e:
                logger.error(f"[{self.source_name}] Exception: {e}")
                time.sleep(random.uniform(2, 4))
        
        logger.error(f"[{self.source_name}] Falló después de {max_retries} intentos")
        return None
    
    @abstractmethod
    def build_url(self, zone: str, operation: str, property_type: str) -> str:
        """Construye la URL de búsqueda"""
        pass
    
    @abstractmethod
    def parse_properties(self, html: str) -> List[PropertyData]:
        """Parsea el HTML y extrae propiedades"""
        pass

    def _render_with_selenium(self, url: str) -> Optional[str]:
        """
        Usa Selenium con Edge para renderizar JavaScript.
        """
        # Evitar en Render si falla o no es necesario
        if os.environ.get('RENDER') or os.environ.get('SCRAPER_NO_BROWSER'):
            logger.info(f"[{self.source_name}] Saltando Selenium por estar en entorno Render/No-Browser")
            return None

        driver = None
        try:
            from selenium import webdriver
            from selenium.webdriver.edge.options import Options
            from selenium.webdriver.edge.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            import time
            
            # Configurar Edge en modo headless
            edge_options = Options()
            edge_options.add_argument("--headless")
            edge_options.add_argument("--no-sandbox")
            edge_options.add_argument("--disable-dev-shm-usage")
            edge_options.add_argument("--disable-gpu")
            edge_options.add_argument("--window-size=1920,1080")
            # User agent real para evitar detección de headless
            edge_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0")
            edge_options.add_argument("--disable-blink-features=AutomationControlled")
            edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            edge_options.add_experimental_option("useAutomationExtension", False)
            
            # Inicializar driver con manager para asegurar que el driver existe
            try:
                service = Service(EdgeChromiumDriverManager().install())
                driver = webdriver.Edge(service=service, options=edge_options)
            except Exception as e_driver:
                logger.warning(f"[{self.source_name}] No se pudo usar webdriver-manager, intentando directo: {e_driver}")
                driver = webdriver.Edge(options=edge_options)
            
            # Ejecutar script para deshabilitar indicador de webdriver
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })
            
            logger.info(f"[{self.source_name}] Navegando a: {url}")
            driver.get(url)
            
            # Esperar a que aparezcan los resultados (más robusto que sleep fijo)
            wait = WebDriverWait(driver, 15)
            try:
                # Buscar cualquier indicador de que hay contenido
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
                # Dar un tiempo extra para JS dinámico
                time.sleep(random.uniform(5, 8))
            except:
                logger.warning(f"[{self.source_name}] Timeout esperando carga completa, continuando...")
            
            # Intentar scroll para cargar contenido perezoso
            try:
                driver.execute_script("window.scrollTo(0, 800);")
                time.sleep(1)
            except:
                pass
            
            html = driver.page_source
            logger.info(f"[{self.source_name}] Exito: {len(html)} bytes")
            return html
            
        except Exception as e:
            logger.error(f"[{self.source_name}] Error fatal en Selenium: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def _render_with_playwright(self, url: str) -> Optional[str]:
        """Fallback con Playwright si Selenium falla"""
        if os.environ.get('RENDER') or os.environ.get('SCRAPER_NO_BROWSER'):
            return None
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=60000)
                html = page.content()
                browser.close()
                return html
        except Exception as e:
            logger.error(f"[{self.source_name}] Error con Playwright: {e}")
            return None

# ========================================
# SCRAPER DE ARGENPROP
# ========================================

class ArgenpropScraper(BaseScraper):
    """Scraper específico para Argenprop"""
    
    def __init__(self):
        super().__init__("https://www.argenprop.com", "argenprop")
    
    def build_url(self, zone: str, operation: str, property_type: str) -> str:
        """Construye URL para Argenprop"""
        # Mapeo de operaciones
        op_map = {
            "venta": "venta",
            "alquiler": "alquiler"
        }
        
        # Mapeo de tipos de propiedad
        type_map = {
            "departamento": "departamentos",
            "casa": "casas",
            "ph": "ph",
            "terreno": "terrenos",
            "local": "locales-comerciales",
            "oficina": "oficinas",
            "cochera": "cocheras",
            "deposito": "depositos-galpones"
        }
        
        op = op_map.get(operation.lower(), "venta")
        p_type = type_map.get(property_type.lower(), "departamentos")
        
        # Normalizar zona
        z_norm = self._normalize_zone(zone)
        
        # Construir URL
        if z_norm:
            url = f"{self.base_url}/{p_type}/{op}/{z_norm}"
        else:
            url = f"{self.base_url}/{p_type}/{op}"
        
        return url
    
    def parse_properties(self, html: str, operation: str = "venta", property_type: str = "departamento") -> List[PropertyData]:
        """Parsea propiedades de Argenprop"""
        properties = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Selectores para Argenprop (adaptativos a cambios)
            cards = soup.select('div.listing__item, div.card, div[class*="listing__item"]')
            
            if not cards:
                # Intentar selectores alternativos
                cards = soup.select('article.posting-card, div.posting-card, .listing-item')
            
            for card in cards:
                try:
                    prop = self._parse_card(card, operation, property_type)
                    if prop:
                        properties.append(prop)
                except Exception as e:
                    logger.debug(f"Error parseando tarjeta: {e}")
                    continue
            
            logger.info(f"[Argenprop] Extraídas {len(properties)} propiedades")
            
        except ImportError:
            logger.error("BeautifulSoup no instalado. Instalar: pip install beautifulsoup4")
        except Exception as e:
            logger.error(f"[Argenprop] Error parseando: {e}")
        
        return properties
    
    def _parse_card(self, card, operation: str = "venta", property_type: str = "departamento") -> Optional[PropertyData]:
        """Parsea una tarjeta individual de Argenprop"""
        try:
            # Extraer precio
            price_elem = card.select_one('.card__price, [data-qa="card-price"], .price')
            price_text = ""
            if price_elem:
                # Argenprop suele tener la moneda en un span
                currency_span = price_elem.select_one('.card__currency')
                if currency_span:
                    currency_text = currency_span.get_text(strip=True)
                    # Eliminar el span para obtener solo el número
                    temp_price = price_elem.get_text(strip=True).replace(currency_text, "").strip()
                    price_text = f"{currency_text} {temp_price}"
                else:
                    price_text = price_elem.get_text(strip=True)
            
            price, currency = self._clean_price(price_text)
            
            if price == 0:
                return None  # Saltar propiedades sin precio
            
            # Extraer dirección
            addr_elem = card.select_one('.card__address, [data-qa="card-address"], .address')
            address = addr_elem.get_text(strip=True) if addr_elem else ""
            
            # Extraer título
            title_elem = card.select_one('.card__title, h2, h3, [data-qa="card-title"]')
            title = title_elem.get_text(strip=True) if title_elem else address
            
            # Extraer superficie
            surface_elem = card.select_one('.card__main-features, [data-qa="card-features"]')
            surface_text = surface_elem.get_text(strip=True) if surface_elem else ""
            surface = self._clean_surface(surface_text)
            
            # Calcular precio por m2
            price_m2 = self._calculate_price_per_m2(price, surface, currency)
            
            # Extraer URL
            link_elem = card.select_one('a[href]')
            url = link_elem['href'] if link_elem and link_elem.has_attr('href') else ""
            if url and not url.startswith('http'):
                url = f"{self.base_url}{url}"
            
            # Extraer ID externo
            prop_id = ""
            if card.has_attr('data-id'):
                prop_id = card['data-id']
            elif card.has_attr('id'):
                prop_id = card['id']
            
            # Ubicación y Dirección
            location = address.split(',')[-1].strip() if ',' in address else address
            
            # Enriquecer ubicación con el barrio buscado si no está presente
            if self.target_zone and self.target_zone.lower() not in location.lower():
                location = f"{location}, {self.target_zone}"

            return PropertyData(
                source=self.source_name,
                external_id=prop_id or url.split('/')[-1] if url else "",
                title=title,
                price_amount=price,
                price_currency=currency,
                price_per_m2=price_m2,
                surface_total=surface,
                surface_covered=surface,
                location=location,
                address=address,
                property_type=property_type,
                operation_type=operation,
                url=url
            )
            
        except Exception as e:
            logger.debug(f"Error en _parse_card: {e}")
            return None

# ========================================
# SCRAPER DE ZONAPROP
# ========================================

class ZonapropScraper(BaseScraper):
    """Scraper específico para Zonaprop"""
    
    def __init__(self):
        super().__init__("https://www.zonaprop.com.ar", "zonaprop")
    
    def build_url(self, zone: str, operation: str, property_type: str) -> str:
        """Construye URL para Zonaprop"""
        op_map = {
            "venta": "venta",
            "alquiler": "alquiler"
        }
        
        type_map = {
            "departamento": "departamentos",
            "casa": "casas",
            "ph": "ph",
            "terreno": "terrenos",
            "local": "locales",
            "oficina": "oficinas"
        }
        
        op = op_map.get(operation.lower(), "venta")
        p_type = type_map.get(property_type.lower(), "departamentos")
        
        # Zonaprop ahora usa preferentemente formato con guiones
        # departamentos-venta-villa-lugano.html
        z_norm = self._normalize_zone(zone)
        
        if z_norm:
            url = f"{self.base_url}/{p_type}-{op}-{z_norm}.html"
        else:
            url = f"{self.base_url}/{p_type}-{op}.html"
        
        return url
    
    def parse_properties(self, html: str, operation: str = "venta", property_type: str = "departamento") -> List[PropertyData]:
        """Parsea propiedades de Zonaprop"""
        properties = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Selectores para Zonaprop
            # Las tarjetas ahora tienen data-qa="posting PROPERTY"
            cards = soup.select('[data-qa*="posting"], div[class*="posting-card"], div[data-id]')
            
            if not cards:
                cards = soup.select('.postingsList-module__card-container > div')
            
            for card in cards:
                try:
                    prop = self._parse_card(card, operation, property_type)
                    if prop:
                        properties.append(prop)
                except Exception as e:
                    logger.debug(f"Error parseando tarjeta: {e}")
                    continue
            
            logger.info(f"[Zonaprop] Extraídas {len(properties)} propiedades")
            
        except ImportError:
            logger.error("BeautifulSoup no instalado")
        except Exception as e:
            logger.error(f"[Zonaprop] Error parseando: {e}")
        
        return properties
    
    def _parse_card(self, card, operation: str = "venta", property_type: str = "departamento") -> Optional[PropertyData]:
        """Parsea una tarjeta individual de Zonaprop"""
        try:
            # Extraer precio
            price_elem = card.select_one('[data-qa="POSTING_CARD_PRICE"], .postingPrices-module__price, .price')
            price_text = price_elem.get_text(strip=True) if price_elem else ""
            price, currency = self._clean_price(price_text)
            
            if price == 0:
                # Intentar buscar en otros formatos de precio
                price_elem = card.select_one('[class*="price"]')
                if price_elem:
                    price, currency = self._clean_price(price_elem.get_text())
                
                if price == 0:
                    return None
            
            # Extraer dirección y ubicación
            addr_elem = card.select_one('.postingLocations-module__location-address, .address')
            loc_elem = card.select_one('[data-qa="POSTING_CARD_LOCATION"], .location')
            
            address = addr_elem.get_text(strip=True) if addr_elem else ""
            location = loc_elem.get_text(strip=True) if loc_elem else ""
            
            if not address and location:
                address = location
            
            if not location and address:
                location = address
                
            # Enriquecer ubicación con el barrio buscado si no está presente
            if self.target_zone and self.target_zone.lower() not in location.lower():
                location = f"{location}, {self.target_zone}"
            
            # Extraer título / descripción
            title_elem = card.select_one('[data-qa="POSTING_CARD_DESCRIPTION"], .postingCard-module__posting-description, h2')
            title = title_elem.get_text(strip=True) if title_elem else address
            
            # Extraer superficie y características
            features_elem = card.select_one('[data-qa="POSTING_CARD_FEATURES"], .postingMainFeatures-module__posting-main-features-block')
            surface = 0
            if features_elem:
                features_text = features_elem.get_text(" ", strip=True)
                surface = self._clean_surface(features_text)
            
            # Extraer URL
            link_elem = card.select_one('a[href], [data-to-posting]')
            url = ""
            if link_elem:
                if link_elem.has_attr('href'):
                    url = link_elem['href']
                elif link_elem.has_attr('data-to-posting'):
                    url = link_elem['data-to-posting']
            
            if url and not url.startswith('http'):
                url = f"{self.base_url}{url}"
            
            # Extraer ID externo
            prop_id = ""
            if card.has_attr('data-id'):
                prop_id = card['data-id']
            elif card.has_attr('id'):
                prop_id = card['id']
            
            # Calcular precio por m2
            price_m2 = self._calculate_price_per_m2(price, surface, currency)
            
            return PropertyData(
                source=self.source_name,
                external_id=prop_id or (url.split('/')[-1].replace('.html', '') if url else ""),
                title=title,
                price_amount=price,
                price_currency=currency,
                price_per_m2=price_m2,
                surface_total=surface,
                surface_covered=surface,
                location=location or (address.split(',')[-1].strip() if ',' in address else address),
                address=address,
                property_type=property_type,
                operation_type=operation,
                url=url
            )
            
            # Superficie
            features = card.select('[data-qa="POSTING_CARD_FEATURES"], .features, .posting-features li')
            surface = 0.0
            for feature in features:
                text = feature.get_text(strip=True)
                if 'm²' in text or 'm2' in text.lower():
                    surface = self._clean_surface(text)
                    break
            
            # Calcular precio por m2
            price_m2 = self._calculate_price_per_m2(price, surface, currency)
            
            return PropertyData(
                source=self.source_name,
                external_id=url.split('/')[-1].replace('.html', '') if url else "",
                title=title,
                price_amount=price,
                price_currency=currency,
                price_per_m2=price_m2,
                surface_total=surface,
                surface_covered=surface,
                location=address,
                address=address,
                property_type=property_type,
                operation_type=operation,
                url=url
            )
            
        except Exception as e:
            logger.debug(f"Error en _parse_card: {e}")
            return None

# ========================================
# SCRAPER DE MERCADOLIBRE
# ========================================

class MercadoLibreScraper(BaseScraper):
    """Scraper específico para MercadoLibre Inmuebles"""
    
    def __init__(self):
        super().__init__("https://inmuebles.mercadolibre.com.ar", "mercadolibre")
    
    def build_url(self, zone: str, operation: str, property_type: str) -> str:
        """Construye URL para MercadoLibre Inmuebles"""
        # Mapeo de operaciones
        op_map = {
            "venta": "venta",
            "alquiler": "alquiler"
        }
        
        # Mapeo de tipos de propiedad
        type_map = {
            "departamento": "departamentos",
            "casa": "casas",
            "ph": "ph",
            "terreno": "terrenos",
            "local": "locales-comerciales",
            "oficina": "oficinas",
            "cochera": "cocheras",
            "deposito": "depositos-galpones"
        }
        
        op = op_map.get(operation.lower(), "venta")
        p_type = type_map.get(property_type.lower(), "departamentos")
        
        # MercadoLibre usa estructura: /tipo/op/provincia/ciudad/
        if zone:
            # Asumimos que zone ya viene formateada o la pasamos tal cual
            url = f"{self.base_url}/{p_type}/{op}/{zone}/"
        else:
            url = f"{self.base_url}/{p_type}/{op}/"
        
        return url
    
    def parse_properties(self, html: str, operation: str = "venta", property_type: str = "departamento") -> List[PropertyData]:
        """Parsea propiedades de MercadoLibre usando Playwright para renderizar JS"""
        properties = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Selectores para MercadoLibre Inmuebles - nueva estructura poly-component
            cards = soup.select('li.ui-search-layout__item')
            
            # Estrategia 2: Buscar en ol.ui-search-layout
            if not cards:
                ol_layout = soup.select_one('ol.ui-search-layout')
                if ol_layout:
                    cards = ol_layout.select('li')
            
            # Estrategia 3: Buscar por artículos con clase de resultado (estructura vieja)
            if not cards:
                cards = soup.select('article.ui-search-result')
            
            # Estrategia 4: Buscar divs con classe de item
            if not cards:
                cards = soup.select('div.ui-search-result__item')
            
            # Estrategia 5: Buscar por data-qa attribute
            if not cards:
                cards = soup.select('[data-qa="listing-item"]')
            
            # Estrategia 6: Buscar todos los enlaces con /ML y filtrar por container
            if not cards:
                ml_items = soup.select('a[href*="/ML"]')
                for item in ml_items[:50]:
                    card = item.find_parent(['li', 'div', 'article'], limit=5)
                    if card and card not in cards:
                        cards.append(card)
            
            logger.info(f"[MercadoLibre] Encontradas {len(cards)} tarjetas candidatas")
            
            for card in cards:
                try:
                    prop = self._parse_card(card, operation, property_type)
                    if prop and prop.price_amount > 0:
                        properties.append(prop)
                except Exception as e:
                    logger.debug(f"Error parseando tarjeta ML: {e}")
                    continue
            
            logger.info(f"[MercadoLibre] Extraídas {len(properties)} propiedades válidas")
            
        except ImportError:
            logger.error("BeautifulSoup no instalado. Instalar: pip install beautifulsoup4")
        except Exception as e:
            logger.error(f"[MercadoLibre] Error parseando: {e}")
        
        return properties
    
    def _parse_card(self, card, operation: str = "venta", property_type: str = "departamento") -> Optional[PropertyData]:
        """Parsea una tarjeta individual de MercadoLibre"""
        try:
            # Extraer precio - nueva estructura poly-component
            price_text = ""
            price = 0.0
            currency = "ARS"
            
            # Estrategia 1: poly-component__price con andes-money-amount
            price_elem = card.select_one('.poly-component__price')
            if price_elem:
                symbol_elem = price_elem.select_one('.andes-money-amount__currency-symbol')
                fraction_elem = price_elem.select_one('.andes-money-amount__fraction')
                
                if symbol_elem and fraction_elem:
                    symbol = symbol_elem.get_text(strip=True)
                    fraction = fraction_elem.get_text(strip=True)
                    price_text = f"{symbol} {fraction}"
                else:
                    price_text = price_elem.get_text(strip=True)
            
            # Estrategia 2: Buscar cualquier andes-money-amount en la tarjeta
            if not price_text:
                money_elem = card.select_one('.andes-money-amount')
                if money_elem:
                    symbol_elem = money_elem.select_one('.andes-money-amount__currency-symbol')
                    fraction_elem = money_elem.select_one('.andes-money-amount__fraction')
                    
                    if symbol_elem and fraction_elem:
                        symbol = symbol_elem.get_text(strip=True)
                        fraction = fraction_elem.get_text(strip=True)
                        price_text = f"{symbol} {fraction}"
            
            # Estrategia 3: ui-search-price (estructura vieja)
            if not price_text:
                price_elem = card.select_one('.ui-search-price__part--medium')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
            
            price, currency = self._clean_price(price_text)
            
            # Extraer título - nueva estructura poly-component
            title = ""
            
            # Estrategia 1: poly-component__title > a
            title_elem = card.select_one('.poly-component__title a')
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Estrategia 2: img con atributo alt
            if not title:
                img_elem = card.select_one('.poly-component__picture')
                if img_elem and img_elem.has_attr('alt'):
                    title = img_elem['alt']
            
            # Estrategia 3: ui-search-item__title (estructura vieja)
            if not title:
                title_elem = card.select_one('.ui-search-item__title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
            
            # Extraer URL
            url = ""
            link_elem = card.select_one('.poly-component__title a')
            if link_elem and link_elem.has_attr('href'):
                url = link_elem['href']
            else:
                link_elem = card.select_one('a[href*="/ML"]')
                if link_elem:
                    url = link_elem['href']
            
            # Extraer ubicación - nueva estructura poly-component
            address = ""
            location_elem = card.select_one('.poly-component__location')
            if location_elem:
                address = location_elem.get_text(strip=True)
            
            if not address:
                location_elem = card.select_one('.ui-search-item__location')
                if location_elem:
                    address = location_elem.get_text(strip=True)
            
            # Extraer atributos (superficie, ambientes) - MEJORADO
            surface = 0.0
            rooms = None
            
            # Estrategia 1: Buscar en poly-component__card con todos los atributos
            card_content = card.select_one('.poly-component__card, .poly-card')
            if card_content:
                all_text = card_content.get_text(strip=True)
                # Buscar patrón de superficie en todo el texto
                surface_patterns = re.findall(r'(\d{1,4})\s*(?:m²|m2|mts2|mts²)', all_text, re.IGNORECASE)
                if surface_patterns:
                    surface = float(surface_patterns[0])
            
            # Estrategia 2: Buscar en contenedores de atributos específicos
            if surface == 0:
                attrs_containers = card.select('.poly-card__attributes, .poly-component__attributes, .poly-card__card, .ui-search-result-attributes, .ui-search-card-attributes')
                for attrs_container in attrs_containers:
                    attr_items = attrs_container.select('li, span, div')
                    for attr in attr_items:
                        text = attr.get_text(strip=True)
                        if 'm²' in text or 'm2' in text.lower():
                            surface = self._clean_surface(text)
                            if surface > 0:
                                break
                        elif 'dorm' in text.lower() or 'ambiente' in text.lower():
                            room_nums = re.findall(r'\d+', text)
                            if room_nums:
                                rooms = int(room_nums[0])
                    if surface > 0:
                        break
            
            # Estrategia 3: Buscar elementos con clase que contenga 'surface' o 'area'
            if surface == 0:
                surface_elems = card.select('[class*="surface"], [class*="area"], [class*="m2"], [data-qa*="surface"]')
                for elem in surface_elems:
                    text = elem.get_text(strip=True)
                    if 'm²' in text or 'm2' in text.lower():
                        surface = self._clean_surface(text)
                        if surface > 0:
                            break
            
            # Estrategia 4: Buscar en toda la tarjeta elementos que contengan m²
            if surface == 0:
                m2_elements = card.select('span:contains("m²"), span:contains("m2"), div:contains("m²")')
                for elem in m2_elements:
                    text = elem.get_text(strip=True)
                    surface = self._clean_surface(text)
                    if surface > 0:
                        break
            
            # Estrategia 5: Buscar en el título por patrones de superficie
            if surface == 0 and title:
                surface_patterns = re.findall(r'(\d{1,4})\s*(?:m²|m2|mts2|mts²)', title, re.IGNORECASE)
                if surface_patterns:
                    surface = float(surface_patterns[0])
            
            # Estrategia 6: Buscar elementos específicos de ML con aria-label o title
            if surface == 0:
                area_elements = card.select('[aria-label*="superficie"], [title*="superficie"], [title*="m²"]')
                for elem in area_elements:
                    text = elem.get_text(strip=True) or elem.get('title', '')
                    if 'm²' in text or 'm2' in text.lower():
                        surface = self._clean_surface(text)
                        if surface > 0:
                            break
            
            # Estrategia 7: Buscar en etiquetas svg que contengan m²
            if surface == 0:
                svg_elements = card.select('svg')
                for svg in svg_elements:
                    next_siblings = svg.find_next_siblings(['span', 'div', 'li'])
                    for sibling in next_siblings[:2]:  # Solo primeros 2 hermanos
                        text = sibling.get_text(strip=True)
                        if 'm²' in text or 'm2' in text.lower():
                            surface = self._clean_surface(text)
                            if surface > 0:
                                break
                    if surface > 0:
                        break
            
            # Calcular precio por m2
            price_m2 = self._calculate_price_per_m2(price, surface, currency)
            
            # Extraer ID externo de la URL
            prop_id = ""
            if url:
                id_match = re.search(r'/ML[A-Z]?-?\d+', url)
                if id_match:
                    prop_id = id_match.group(0).replace('/', '')
                else:
                    prop_id = url.split('/')[-1].replace('.html', '').replace('_JM', '')
            
            # Extraer thumbnail
            thumbnail = ""
            img_elem = card.select_one('.poly-component__picture')
            if img_elem:
                if img_elem.has_attr('src'):
                    thumbnail = img_elem['src']
                elif img_elem.has_attr('data-src'):
                    thumbnail = img_elem['data-src']
            
            return PropertyData(
                source=self.source_name,
                external_id=prop_id or url.split('/')[-1] if url else "",
                title=title if title else "Sin título",
                price_amount=price,
                price_currency=currency,
                price_per_m2=price_m2,
                surface_total=surface,
                surface_covered=surface,
                location=address.split(',')[-1].strip() if ',' in address else address,
                address=address,
                property_type=property_type,
                operation_type=operation,
                url=url,
                raw_data={"thumbnail": thumbnail} if thumbnail else {}
            )
            
        except Exception as e:
            logger.debug(f"Error en _parse_card ML: {e}")
            return None


# ========================================
# ANALIZADOR DE MERCADO
# ========================================

class MarketAnalyzer:
    """Analiza datos del mercado inmobiliario"""
    
    # Umbral mínimo de superficie (en m²) para estadísticas válidas
    MIN_SURFACE_THRESHOLD = 10
    
    @staticmethod
    def _is_in_zone(prop_location: str, prop_address: str, zone: str) -> bool:
        """Verifica si la propiedad está realmente en la zona solicitada"""
        # Caso especial: Si no hay información de ubicación, confiamos en la URL 
        # (pero marcamos para revisión si fuera necesario)
        if not prop_location and not prop_address:
            return True
            
        zone_clean = zone.lower().replace("villa ", "").strip()
        loc_text = f"{prop_location} {prop_address}".lower()
        
        # Lugano / Villa Lugano special case
        if "lugano" in zone_clean and "lugano" in loc_text:
            return True
            
        # Caso general: que el nombre del barrio esté en la ubicación o dirección
        if zone.lower() in loc_text or zone_clean in loc_text:
            return True
            
        # Si no hay coincidencia directa, rechazar (Zonaprop suele meter Belgrano en Villa Lugano)
        return False

    @staticmethod
    def calculate_stats(properties: List[PropertyData], zone: str, operation: str, prop_type: str) -> MarketStats:
        """Calcula estadísticas del mercado desde propiedades scrappeadas"""
        errors = []
        source_breakdown = {}
        currency_dist = {}
        properties_list = []
        low_surface_count = 0  # Contador de propiedades con superficie muy baja
        
        if not properties:
            return MarketStats(
                zone=zone,
                operation_type=operation,
                property_type=prop_type,
                sample_size=0,
                average_price_per_m2=None,
                average_total_price=None,
                median_price_per_m2=None,
                min_price_per_m2=None,
                max_price_per_m2=None,
                price_range_total=None,
                currency_distribution={},
                source_breakdown={},
                properties=[],
                errors=["No se pudieron obtener datos del mercado"]
            )
        
        # Recopilar precios por m2
        prices_per_m2 = []
        total_prices = []
        
        for prop in properties:
            # FILTRO DE BARRIO: Evitar que Zonaprop meta Belgrano en Villa Lugano
            if not MarketAnalyzer._is_in_zone(prop.location, prop.address, zone):
                continue
                
            # Verificar si tiene superficie muy baja (menor a 10m²)
            has_low_surface = prop.surface_total < MarketAnalyzer.MIN_SURFACE_THRESHOLD
            
            if has_low_surface:
                low_surface_count += 1
            
            # Contabilizar por fuente
            source_breakdown[prop.source] = source_breakdown.get(prop.source, 0) + 1
            
            # Contabilizar por moneda
            currency_dist[prop.price_currency] = currency_dist.get(prop.price_currency, 0) + 1
            
            # Solo calcular estadísticas para propiedades con superficie válida
            # Esto evita que departamentos de 1-9m² alteren los promedios
            if not has_low_surface and prop.price_per_m2 > 0:
                prices_per_m2.append(prop.price_per_m2)
            
            if not has_low_surface and prop.price_amount > 0:
                total_prices.append(prop.price_amount)
            
            # Agregar a lista de propiedades (todas, incluyendo las con superficie baja)
            # Las que tienen superficie baja tendrán surface_warning: true
            properties_list.append({
                "source": prop.source,
                "title": prop.title,
                "price": prop.price_amount,
                "currency": prop.price_currency,
                "price_m2": prop.price_per_m2,
                "surface": prop.surface_total,
                "address": prop.address,
                "url": prop.url,
                "operation_type": prop.operation_type,
                "property_type": prop.property_type,
                "surface_warning": has_low_surface  # Marcar propiedades con superficie irreal
            })
        
        # Calcular estadísticas
        from statistics import mean, median, stdev
        
        avg_price_m2 = None
        median_price_m2 = None
        min_price_m2 = None
        max_price_m2 = None
        
        if prices_per_m2:
            avg_price_m2 = mean(prices_per_m2)
            median_price_m2 = median(prices_per_m2)
            min_price_m2 = min(prices_per_m2)
            max_price_m2 = max(prices_per_m2)
        
        avg_total = None
        if total_prices:
            avg_total = mean(total_prices)
        
        # Rango de precios total
        price_range = None
        if total_prices:
            min_p = min(total_prices)
            max_p = max(total_prices)
            price_range = f"{min_p:,.0f} - {max_p:,.0f}"
        
        # Agregar advertencia si hay propiedades con superficie baja
        warnings = []
        if low_surface_count > 0:
            warnings.append(f"{low_surface_count} propiedades con superficie < {MarketAnalyzer.MIN_SURFACE_THRESHOLD}m² excluidas del promedio")
        
        return MarketStats(
            zone=zone,
            operation_type=operation,
            property_type=prop_type,
            sample_size=len(properties),
            average_price_per_m2=avg_price_m2,
            average_total_price=avg_total,
            median_price_per_m2=median_price_m2,
            min_price_per_m2=min_price_m2,
            max_price_per_m2=max_price_m2,
            price_range_total=price_range,
            currency_distribution=currency_dist,
            source_breakdown=source_breakdown,
            properties=properties_list,
            errors=warnings if warnings else errors
        )
    
    @staticmethod
    def to_dict(stats: MarketStats) -> Dict:
        """Convierte MarketStats a diccionario para JSON"""
        return {
            "zone": stats.zone,
            "operation_type": stats.operation_type,
            "property_type": stats.property_type,
            "sample_size": stats.sample_size,
            "statistics": {
                "average_price_per_m2": round(stats.average_price_per_m2, 2) if stats.average_price_per_m2 else None,
                "average_total_price": round(stats.average_total_price, 2) if stats.average_total_price else None,
                "median_price_per_m2": round(stats.median_price_per_m2, 2) if stats.median_price_per_m2 else None,
                "min_price_per_m2": round(stats.min_price_per_m2, 2) if stats.min_price_per_m2 else None,
                "max_price_per_m2": round(stats.max_price_per_m2, 2) if stats.max_price_per_m2 else None,
                "price_range_total": stats.price_range_total
            },
            "currency_distribution": stats.currency_distribution,
            "source_breakdown": stats.source_breakdown,
            "properties_sample": stats.properties,  # Primeros 50
            "total_properties_analyzed": len(stats.properties),
            "analysis_timestamp": datetime.now().isoformat(),
            "errors": stats.errors
        }


# ========================================
# GESTOR DE SCRAPING
# ========================================

class ScrapingManager:
    """Gestiona el scraping de múltiples portales"""
    
    def __init__(self):
        self.argenprop = ArgenpropScraper()
        self.zonaprop = ZonapropScraper()
        self.mercadolibre = MercadoLibreScraper()
        self.analyzer = MarketAnalyzer()
    
    def scrape_market(self, zone: str, operation: str = "venta", 
                      property_type: str = "departamento") -> Dict[str, Any]:
        """
        Realiza scraping de mercado inmobiliario
        
        Args:
            zone: Barrio o zona (ej: "palermo", "microcentro")
            operation: Tipo de operación ("venta" o "alquiler")
            property_type: Tipo de propiedad ("departamento", "casa", etc.)
        
        Returns:
            Diccionario con estadísticas del mercado
        """
        # Normalizar barrio para la búsqueda (ej: Lugano -> Villa Lugano)
        search_zone = zone
        if "lugano" in zone.lower() and "villa" not in zone.lower():
            search_zone = "villa lugano"
            
        logger.info(f"[ScrapingManager] Iniciando scraping para {search_zone} ({operation}, {property_type})")
        
        all_properties = []
        errors = []
        
        # Escanear Argenprop
        try:
            self.argenprop.target_zone = search_zone
            argenprop_url = self.argenprop.build_url(search_zone, operation, property_type)
            logger.info(f"[Argenprop] URL: {argenprop_url}")
            
            # Intentar con requests primero (más liviano para Render)
            html = self.argenprop._make_request(argenprop_url)
            
            # Si falla y no estamos en Render, intentar Selenium
            if not html and not os.environ.get('RENDER'):
                logger.info("[Argenprop] Requests falló, intentando con Selenium...")
                html = self.argenprop._render_with_selenium(argenprop_url)
            
            if html:
                properties = self.argenprop.parse_properties(html, operation, property_type)
                all_properties.extend(properties)
            else:
                errors.append("Argenprop: No se pudo obtener respuesta")
        except Exception as e:
            errors.append(f"Argenprop: {str(e)}")
        
        # Escanear Zonaprop
        try:
            self.zonaprop.target_zone = search_zone
            zonaprop_url = self.zonaprop.build_url(search_zone, operation, property_type)
            logger.info(f"[Zonaprop] URL: {zonaprop_url}")
            
            # Intentar con requests primero
            html = self.zonaprop._make_request(zonaprop_url)
            
            # Zonaprop suele requerir JS, pero probamos requests en Render por estabilidad
            if not html and not os.environ.get('RENDER'):
                logger.info("[Zonaprop] Requests falló, intentando con Selenium...")
                html = self.zonaprop._render_with_selenium(zonaprop_url)
            
            if html:
                properties = self.zonaprop.parse_properties(html, operation, property_type)
                all_properties.extend(properties)
            else:
                errors.append("Zonaprop: No se pudo obtener respuesta")
        except Exception as e:
            errors.append(f"Zonaprop: {str(e)}")
        
        # Escanear MercadoLibre
        try:
            self.mercadolibre.target_zone = search_zone
            mercadolibre_url = self.mercadolibre.build_url(search_zone, operation, property_type)
            logger.info(f"[MercadoLibre] URL: {mercadolibre_url}")
            
            # MercadoLibre funciona bien con requests
            html = self.mercadolibre._make_request(mercadolibre_url)
            
            if not html and not os.environ.get('RENDER'):
                html = self.mercadolibre._render_with_selenium(mercadolibre_url)
            
            if html:
                properties = self.mercadolibre.parse_properties(html, operation, property_type)
                all_properties.extend(properties)
            else:
                errors.append("MercadoLibre: No se pudo obtener respuesta")
        except Exception as e:
            errors.append(f"MercadoLibre: {str(e)}")
        
        # Calcular estadísticas
        stats = self.analyzer.calculate_stats(all_properties, search_zone, operation, property_type)
        
        if errors:
            stats.errors.extend(errors)
        
        # Convertir a diccionario
        result = MarketAnalyzer.to_dict(stats)
        result['raw_properties_count'] = len(all_properties)
        
        logger.info(f"[ScrapingManager] Completado: {stats.sample_size} propiedades analizadas")
        
        return result


# ========================================
# INTEGRACIÓN CON MAIN-AI
# ========================================

def integrate_with_main_ai(app, gemini_client_func=None):
    """
    Integra el scraper con la aplicación FastAPI existente
    
    Args:
        app: Instancia de FastAPI
        gemini_client_func: Función opcional para análisis con IA
    """
    from fastapi import Query
    
    scraping_manager = ScrapingManager()
    
    @app.get("/market/scraping")
    def scrape_market_data(
        zone: str = Query(..., description="Barrio o zona a analizar"),
        operation: str = Query("venta", description="Tipo de operación"),
        property_type: str = Query("departamento", description="Tipo de propiedad")
    ):
        """
        Endpoint para obtener datos de mercado mediante scraping
        
        Uso:
        - GET /market/scraping?zone=palermo
        - GET /market/scraping?zone=belgrano&operation=venta&property_type=casa
        """
        logger.info(f"📊 Solicitud de scraping: zone={zone}, op={operation}, type={property_type}")
        
        try:
            result = scraping_manager.scrape_market(zone, operation, property_type)
            
            if result.get('sample_size', 0) == 0:
                return {
                    "success": False,
                    "message": "No se pudieron obtener datos del mercado",
                    "zone": zone,
                    "errors": result.get('errors', [])
                }
            
            return {
                "success": True,
                "message": f"Analizadas {result['sample_size']} propiedades",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Error en scraping: {e}")
            return {
                "success": False,
                "error": str(e),
                "zone": zone
            }
    
    @app.get("/market/stats/{zone}")
    def get_market_stats(
        zone: str,
        operation: str = "venta",
        property_type: str = "departamento"
    ):
        """
        Obtiene estadísticas resumidas del mercado para una zona
        """
        try:
            result = scraping_manager.scrape_market(zone, operation, property_type)
            
            # Resumen condensado
            return {
                "zone": zone,
                "sample_size": result['sample_size'],
                "average_price_m2": result['statistics']['average_price_per_m2'],
                "median_price_m2": result['statistics']['median_price_per_m2'],
                "price_range": result['statistics']['price_range_total'],
                "sources": result['source_breakdown'],
                "currencies": result['currency_distribution']
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    logger.info("✅ Scraping endpoints integrados en FastAPI")


# ========================================
# EJECUCIÓN DIRECTA
# ========================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Scraper de Mercado Inmobiliario")
    parser.add_argument("zone", help="Zona a analizar (ej: palermo, microcentro)")
    parser.add_argument("--operation", default="venta", help="Tipo de operación")
    parser.add_argument("--type", default="departamento", help="Tipo de propiedad")
    
    args = parser.parse_args()
    
    manager = ScrapingManager()
    result = manager.scrape_market(args.zone, args.operation, args.type)
    
    print("\n" + "=" * 70)
    print("📊 RESULTADO DEL ANÁLISIS DE MERCADO")
    print("=" * 70)
    print(json.dumps(result, indent=2, ensure_ascii=False))
