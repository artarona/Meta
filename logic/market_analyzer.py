"""
Módulo de Análisis de Mercado Inmobiliario Local
Analiza propiedades desde propiedades.json y genera estadísticas de mercado
"""
import json
import os
import statistics
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

# ========================================
# ESTRUCTURAS DE DATOS
# ========================================

@dataclass
class PropertyStats:
    """Estadísticas calculadas para una propiedad individual"""
    id_temporal: str
    titulo: str
    barrio: str
    precio: float
    precio_normalizado_usd: float  # Precio convertido a USD para comparación
    moneda: str
    operacion: str
    tipo: str
    metros_cuadrados: float
    precio_por_m2: float
    ambientes: int
    direccion: str
    precio_m2_normalizado: float  # Precio/m2 en USD para comparación

@dataclass
class BarrioStats:
    """Estadísticas agregadas por barrio"""
    nombre: str
    cantidad_propiedades: int
    precio_promedio: float
    precio_mediana: float
    precio_minimo: float
    precio_maximo: float
    precio_m2_promedio: float
    precio_m2_mediana: float
    metros_promedio: float
    ambientes_promedio: float
    distribucion_tipos: Dict[str, int]
    distribucion_operacion: Dict[str, int]
    propiedades: List[Dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class MarketOverview:
    """Vista general del mercado"""
    total_propiedades: int
    barrios_unicos: List[str]
    barrios_stats: List[Dict]
    precio_promedio_general: float
    precio_m2_promedio_general: float
    distribucion_monto: Dict[str, int]
    distribucion_tipos: Dict[str, int]
    distribucion_operacion: Dict[str, int]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

# ========================================
# CONSTANTES DE CONVERSIÓN
# ========================================

# Tipo de cambio aproximado (ARS a USD) - Se actualiza periódicamente
TIPO_CAMBIO_ARS_A_USD = 1050.0  # Valor referencial - ajustar según mercado

# ========================================
# CLASE ANALIZADORA DE MERCADO
# ========================================

class LocalMarketAnalyzer:
    """Analiza el mercado inmobiliario desde el archivo local propiedades.json"""
    
    def __init__(self, propiedades_file: str = None, use_scraper: bool = False):
        """
        Inicializa el analizador
        
        Args:
            propiedades_file: Ruta al archivo propiedades.json
            use_scraper: Si True, usa el scraper para obtener datos reales del mercado
        """
        self.use_scraper = use_scraper
        
        if not use_scraper:
            if propiedades_file is None:
                # Buscar en backend/ (ubicación estándar del proyecto)
                # __file__ = /workspace/backend/logic/market_analyzer.py
                script_dir = os.path.dirname(os.path.abspath(__file__))  # /workspace/backend/logic
                backend_dir = os.path.dirname(script_dir)  # /workspace/backend
                propiedades_file = os.path.join(backend_dir, "propiedades.json")
            
            self.propiedades_file = propiedades_file
            self.propiedades = []
            self._load_properties()
        else:
            self.propiedades = []
            self.scraper_data = None
    
    def _load_properties(self) -> None:
        """Carga las propiedades desde el archivo JSON"""
        try:
            if os.path.exists(self.propiedades_file):
                with open(self.propiedades_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Normalizar a lista
                    if isinstance(data, dict):
                        self.propiedades = list(data.values())
                    elif isinstance(data, list):
                        self.propiedades = data
                    else:
                        self.propiedades = []
                        
                print(f"📊 Cargadas {len(self.propiedades)} propiedades para análisis")
            else:
                print(f"⚠️ No se encontró el archivo: {self.propiedades_file}")
                self.propiedades = []
        except Exception as e:
            print(f"❌ Error cargando propiedades: {e}")
            self.propiedades = []
    
    def reload(self) -> None:
        """Recarga las propiedades desde el archivo"""
        self._load_properties()
    
    def scrape_market_data(self, zone: str, operation: str = "venta", 
                           property_type: str = "departamento") -> None:
        """
        Ejecuta el scraper para obtener datos reales del mercado
        
        Args:
            zone: Barrio o zona a analizar
            operation: Tipo de operación (venta/alquiler)
            property_type: Tipo de propiedad
        """
        try:
            # Importación directa que funciona en Windows y Linux
            import importlib.util
            scraper_path = os.path.join(os.path.dirname(__file__), 'market_scraper.py')
            spec = importlib.util.spec_from_file_location("market_scraper", scraper_path)
            market_scraper = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(market_scraper)
            ScrapingManager = market_scraper.ScrapingManager
            
            print(f"🌐 Ejecutando scraper para {zone} ({operation}, {property_type})...")
            
            manager = ScrapingManager()
            result = manager.scrape_market(zone, operation, property_type)
            
            # El scraper devuelve un diccionario con sample_size y statistics
            sample_size = result.get('sample_size', 0)
            if sample_size > 0:
                self.scraper_data = result
                print(f"✅ Obtenidas {sample_size} propiedades del mercado")
            else:
                print(f"❌ Error en scraper: {result.get('message', result.get('errors', ['Error desconocido']))}")
                self.scraper_data = None
                
        except Exception as e:
            print(f"⚠️ No se pudo importar el scraper: {e}")
            self.scraper_data = None
    
    def get_scraped_properties(self) -> List[Dict]:
        """
        Convierte datos del scraper al formato interno para análisis
        
        Returns:
            Lista de propiedades en formato interno
        """
        if not self.scraper_data:
            return []
        
        propiedades = []
        for prop in self.scraper_data.get('properties_sample', []):
            propiedades.append({
                'id_temporal': prop.get('source', 'scraper') + '_' + str(len(propiedades)),
                'titulo': prop.get('title', 'Propiedad'),
                'barrio': self.scraper_data.get('zone', 'Desconocido'),
                'precio': prop.get('price', 0),
                'moneda_precio': prop.get('currency', 'USD'),
                'operacion': self.scraper_data.get('operation_type', 'venta'),
                'tipo': self.scraper_data.get('property_type', 'departamento'),
                'metros_cuadrados': prop.get('surface', 0),
                'ambientes': 0,  # El scraper no siempre tiene esta info
                'direccion': prop.get('address', ''),
                'precio_m2': prop.get('price_m2', 0),
                'precio_usd': prop.get('price', 0) if prop.get('currency') == 'USD' else 0
            })
        
        return propiedades
    
    def _normalizar_precio_a_usd(self, precio: float, moneda: str) -> float:
        """
        Normaliza un precio a USD para comparación
        
        Args:
            precio: Precio en la moneda original
            moneda: Moneda del precio (USD o ARS)
            
        Returns:
            Precio convertido a USD
        """
        if moneda.upper() == "USD":
            return float(precio)
        elif moneda.upper() == "ARS":
            return float(precio) / TIPO_CAMBIO_ARS_A_USD
        else:
            return float(precio)
    
    def _calcular_precio_por_m2(self, precio: float, metros: float) -> float:
        """Calcula el precio por metro cuadrado"""
        if metros <= 0:
            return 0.0
        return precio / metros
    
    def get_barrios_unicos(self) -> List[str]:
        """Obtiene la lista de barrios únicos en el dataset"""
        barrios = set()
        for prop in self.propiedades:
            barrio = prop.get("barrio", "").strip()
            if barrio:
                barrios.add(barrio)
        return sorted(list(barrios))
    
    def get_propiedades_validas(self, precio_minimo: float = 1000) -> List[Dict]:
        """
        Obtiene propiedades con datos válidos para análisis
        
        Args:
            precio_minimo: Precio mínimo para considerar válida una propiedad
        """
        validas = []
        for prop in self.propiedades:
            precio = float(prop.get("precio", 0) or 0)
            moneda = prop.get("moneda_precio", "USD")
            metros = float(prop.get("metros_cuadrados", 0) or 0)
            
            # Filtrar propiedades sin precio o precio muy bajo
            if precio < precio_minimo:
                continue
                
            # Filtrar propiedades sin metros cuadrados (para cálculos de m2)
            validas.append(prop)
            
        return validas
    
    def get_propiedades_por_barrio(self, barrio: str = None) -> List[Dict]:
        """
        Obtiene propiedades filtradas por barrio
        
        Args:
            barrio: Nombre del barrio (None para todas)
        """
        if barrio:
            barrio_lower = barrio.lower().strip()
            return [p for p in self.propiedades 
                   if p.get("barrio", "").lower().strip() == barrio_lower]
        return self.propiedades
    
    def get_propiedades_por_operacion(self, operacion: str = None) -> List[Dict]:
        """
        Obtiene propiedades filtradas por tipo de operación
        
        Args:
            operacion: Tipo de operación (venta/alquiler)
        """
        if operacion:
            op_lower = operacion.lower().strip()
            return [p for p in self.propiedades 
                   if p.get("operacion", "").lower().strip() == op_lower]
        return self.propiedades
    
    def get_propiedades_filtradas(self, barrio: str = None, 
                                   operacion: str = None,
                                   tipo: str = None) -> List[Dict]:
        """
        Obtiene propiedades con múltiples filtros
        
        Args:
            barrio: Filtrar por barrio
            operacion: Filtrar por operación (venta/alquiler)
            tipo: Filtrar por tipo de propiedad
        """
        propiedades = self.propiedades
        
        if barrio:
            barrio_lower = barrio.lower().strip()
            propiedades = [p for p in propiedades 
                          if p.get("barrio", "").lower().strip() == barrio_lower]
        
        if operacion:
            op_lower = operacion.lower().strip()
            propiedades = [p for p in propiedades 
                          if p.get("operacion", "").lower().strip() == op_lower]
        
        if tipo:
            tipo_lower = tipo.lower().strip()
            propiedades = [p for p in propiedades 
                          if p.get("tipo", "").lower().strip() == tipo_lower]
        
        return propiedades
    
    def calculate_barrio_stats(self, barrio: str = None) -> BarrioStats:
        """
        Calcula estadísticas para un barrio específico o global
        
        Args:
            barrio: Nombre del barrio (None para todos)
        """
        propiedades = self.get_propiedades_filtradas(barrio=barrio, operacion=None)
        
        # Filtrar propiedades con precio válido
        propiedades_validas = []
        precios = []
        precios_m2 = []
        metros_list = []
        ambientes_list = []
        tipos_dist = {}
        operacion_dist = {}
        
        for prop in propiedades:
            precio = float(prop.get("precio", 0) or 0)
            moneda = prop.get("moneda_precio", "USD")
            metros = float(prop.get("metros_cuadrados", 0) or 0)
            ambientes = int(prop.get("ambientes", 0) or 0)
            operacion = prop.get("operacion", "venta").lower()
            tipo = prop.get("tipo", "departamento").lower()
            
            if precio < 1000:  # Filtrar precios irrisorios
                continue
            
            # Normalizar precio a USD
            precio_usd = self._normalizar_precio_a_usd(precio, moneda)
            
            # Calcular precio por m2
            precio_m2 = self._calcular_precio_por_m2(precio_usd, metros) if metros > 0 else 0
            
            propiedades_validas.append({
                "id_temporal": prop.get("id_temporal", ""),
                "titulo": prop.get("titulo", ""),
                "barrio": prop.get("barrio", ""),
                "precio": precio,
                "precio_usd": precio_usd,
                "moneda": moneda,
                "operacion": operacion,
                "tipo": tipo,
                "metros": metros,
                "precio_m2": precio_m2,
                "ambientes": ambientes,
                "direccion": prop.get("direccion", ""),
                "estado": prop.get("estado", ""),
                "antiguedad": prop.get("antiguedad", 0)
            })
            
            precios.append(precio_usd)
            if metros > 0:
                precios_m2.append(precio_m2)
            if metros > 0:
                metros_list.append(metros)
            if ambientes > 0:
                ambientes_list.append(ambientes)
            
            # Distribuciones
            tipos_dist[tipo] = tipos_dist.get(tipo, 0) + 1
            operacion_dist[operacion] = operacion_dist.get(operacion, 0) + 1
        
        # Calcular estadísticas
        nombre_barrio = barrio if barrio else "General"
        
        if not precios:
            return BarrioStats(
                nombre=nombre_barrio,
                cantidad_propiedades=0,
                precio_promedio=None,
                precio_mediana=None,
                precio_minimo=None,
                precio_maximo=None,
                precio_m2_promedio=None,
                precio_m2_mediana=None,
                metros_promedio=None,
                ambientes_promedio=None,
                distribucion_tipos={},
                distribucion_operacion={},
                propiedades=[]
            )
        
        return BarrioStats(
            nombre=nombre_barrio,
            cantidad_propiedades=len(propiedades_validas),
            precio_promedio=statistics.mean(precios),
            precio_mediana=statistics.median(precios),
            precio_minimo=min(precios),
            precio_maximo=max(precios),
            precio_m2_promedio=statistics.mean(precios_m2) if precios_m2 else None,
            precio_m2_mediana=statistics.median(precios_m2) if precios_m2 else None,
            metros_promedio=statistics.mean(metros_list) if metros_list else None,
            ambientes_promedio=statistics.mean(ambientes_list) if ambientes_list else None,
            distribucion_tipos=tipos_dist,
            distribucion_operacion=operacion_dist,
            propiedades=propiedades_validas
        )
    
    def calculate_all_barrios_stats(self) -> List[BarrioStats]:
        """Calcula estadísticas para todos los barrios"""
        barrios = self.get_barrios_unicos()
        stats_list = []
        
        for barrio in barrios:
            stats = self.calculate_barrio_stats(barrio)
            stats_list.append(stats)
        
        return stats_list
    
    def get_market_overview(self) -> MarketOverview:
        """Genera una vista general del mercado"""
        all_stats = self.calculate_all_barrios_stats()
        barrios = self.get_barrios_unicos()
        
        # Calcular estadísticas globales
        todos_precios = []
        todos_precios_m2 = []
        tipos_dist = {}
        operacion_dist = {}
        
        for stats in all_stats:
            for prop in stats.propiedades:
                todos_precios.append(prop["precio_usd"])
                if prop["precio_m2"] > 0:
                    todos_precios_m2.append(prop["precio_m2"])
                
                tipos_dist[prop["tipo"]] = tipos_dist.get(prop["tipo"], 0) + 1
                operacion_dist[prop["operacion"]] = operacion_dist.get(prop["operacion"], 0) + 1
        
        # Distribución por rango de precio
        distribucion_monto = self._get_distribucion_precio(todos_precios)
        
        return MarketOverview(
            total_propiedades=len(self.propiedades),
            barrios_unicos=barrios,
            barrios_stats=[self._barrio_stats_to_dict(s) for s in all_stats],
            precio_promedio_general=statistics.mean(todos_precios) if todos_precios else None,
            precio_m2_promedio_general=statistics.mean(todos_precios_m2) if todos_precios_m2 else None,
            distribucion_monto=distribucion_monto,
            distribucion_tipos=tipos_dist,
            distribucion_operacion=operacion_dist
        )
    
    def _get_distribucion_precio(self, precios: List[float]) -> Dict[str, int]:
        """Genera distribución de precios por rangos"""
        rangos = {
            "0-50k": 0,
            "50k-100k": 0,
            "100k-200k": 0,
            "200k-500k": 0,
            "500k-1M": 0,
            "1M+": 0
        }
        
        for precio in precios:
            if precio < 50000:
                rangos["0-50k"] += 1
            elif precio < 100000:
                rangos["50k-100k"] += 1
            elif precio < 200000:
                rangos["100k-200k"] += 1
            elif precio < 500000:
                rangos["200k-500k"] += 1
            elif precio < 1000000:
                rangos["500k-1M"] += 1
            else:
                rangos["1M+"] += 1
        
        return rangos
    
    def _barrio_stats_to_dict(self, stats: BarrioStats) -> Dict:
        """Convierte BarrioStats a diccionario"""
        return {
            "nombre": stats.nombre,
            "cantidad_propiedades": stats.cantidad_propiedades,
            "precio_promedio": round(stats.precio_promedio, 2) if stats.precio_promedio else None,
            "precio_mediana": round(stats.precio_mediana, 2) if stats.precio_mediana else None,
            "precio_minimo": round(stats.precio_minimo, 2) if stats.precio_minimo else None,
            "precio_maximo": round(stats.precio_maximo, 2) if stats.precio_maximo else None,
            "precio_m2_promedio": round(stats.precio_m2_promedio, 2) if stats.precio_m2_promedio else None,
            "precio_m2_mediana": round(stats.precio_m2_mediana, 2) if stats.precio_m2_mediana else None,
            "metros_promedio": round(stats.metros_promedio, 2) if stats.metros_promedio else None,
            "ambientes_promedio": round(stats.ambientes_promedio, 2) if stats.ambientes_promedio else None,
            "distribucion_tipos": stats.distribucion_tipos,
            "distribucion_operacion": stats.distribucion_operacion,
            "timestamp": stats.timestamp
        }
    
    def to_api_response(self, include_properties: bool = False) -> Dict[str, Any]:
        """Genera respuesta completa para la API"""
        overview = self.get_market_overview()
        
        response = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "data_source": self.propiedades_file,
            "tipo_cambio_usd": TIPO_CAMBIO_ARS_A_USD,
            "overview": {
                "total_propiedades": overview.total_propiedades,
                "barrios_analizados": len(overview.barrios_unicos),
                "lista_barrios": overview.barrios_unicos,
                "precio_promedio_general_usd": round(overview.precio_promedio_general, 2) if overview.precio_promedio_general else None,
                "precio_m2_promedio_general_usd": round(overview.precio_m2_promedio_general, 2) if overview.precio_m2_promedio_general else None,
                "distribucion_precios": overview.distribucion_monto,
                "distribucion_tipos": overview.distribucion_tipos,
                "distribucion_operacion": overview.distribucion_operacion
            },
            "barrios": overview.barrios_stats
        }
        
        if include_properties:
            # Incluir propiedades detalladas por barrio
            response["detalle_propiedades"] = {}
            for stats in self.calculate_all_barrios_stats():
                if stats.propiedades:
                    response["detalle_propiedades"][stats.nombre] = stats.propiedades
        
        return response
    
    def get_scatter_data(self, barrio: str = None) -> List[Dict]:
        """
        Genera datos para gráfico de dispersión (precio vs superficie)
        
        Args:
            barrio: Filtrar por barrio específico
        """
        propiedades = self.get_propiedades_filtradas(barrio=barrio)
        scatter_data = []
        
        for prop in propiedades:
            precio = float(prop.get("precio", 0) or 0)
            moneda = prop.get("moneda_precio", "USD")
            metros = float(prop.get("metros_cuadrados", 0) or 0)
            
            if precio < 1000 or metros <= 0:
                continue
            
            precio_usd = self._normalizar_precio_a_usd(precio, moneda)
            precio_m2 = precio_usd / metros
            
            scatter_data.append({
                "x": metros,
                "y": precio_usd,
                "z": precio_m2,  # Precio por m2 para color
                "titulo": prop.get("titulo", ""),
                "barrio": prop.get("barrio", ""),
                "operacion": prop.get("operacion", ""),
                "tipo": prop.get("tipo", ""),
                "direccion": prop.get("direccion", ""),
                "id": prop.get("id_temporal", "")
            })
        
        return scatter_data


# ========================================
# INTEGRACIÓN CON CMS
# ========================================

def integrate_with_cms(app):
    """
    Integra el analizador de mercado con la aplicación FastAPI del CMS
    
    Args:
        app: Instancia de FastAPI
    """
    from fastapi import Query
    
    # Inicializar analizador
    analyzer = LocalMarketAnalyzer()
    
    @app.get("/api/stats/overview")
    def get_market_overview():
        """
        Obtiene vista general del mercado inmobiliario
        """
        try:
            response = analyzer.to_api_response(include_properties=False)
            return response
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @app.get("/api/stats/barrios")
    def get_all_barrios_stats():
        """
        Obtiene estadísticas para todos los barrios
        """
        try:
            stats_list = analyzer.calculate_all_barrios_stats()
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "barrios": [analyzer._barrio_stats_to_dict(s) for s in stats_list]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @app.get("/api/stats/barrio/{nombre}")
    def get_barrio_stats(nombre: str):
        """
        Obtiene estadísticas para un barrio específico
        
        Args:
            nombre: Nombre del barrio
        """
        try:
            stats = analyzer.calculate_barrio_stats(nombre)
            result = analyzer._barrio_stats_to_dict(stats)
            result["propiedades"] = stats.propiedades if stats.propiedades else []
            return {
                "success": True,
                "data": result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @app.get("/api/stats/scatter")
    def get_scatter_data(barrio: str = None):
        """
        Obtiene datos para gráfico de dispersión
        
        Args:
            barrio: Filtrar por barrio (opcional)
        """
        try:
            data = analyzer.get_scatter_data(barrio)
            return {
                "success": True,
                "data": data,
                "count": len(data)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @app.get("/api/stats/filter")
    def get_filtered_stats(
        barrio: str = Query(None, description="Filtrar por barrio"),
        operacion: str = Query(None, description="Filtrar por operación (venta/alquiler)"),
        tipo: str = Query(None, description="Filtrar por tipo de propiedad")
    ):
        """
        Obtiene estadísticas con filtros múltiples
        """
        try:
            propiedades = analyzer.get_propiedades_filtradas(
                barrio=barrio,
                operacion=operacion,
                tipo=tipo
            )
            
            # Calcular estadísticas rápido
            precios = []
            precios_m2 = []
            metros_list = []
            
            for prop in propiedades:
                precio = float(prop.get("precio", 0) or 0)
                if precio < 1000:
                    continue
                    
                moneda = prop.get("moneda_precio", "USD")
                metros = float(prop.get("metros_cuadrados", 0) or 0)
                
                precio_usd = analyzer._normalizar_precio_a_usd(precio, moneda)
                precios.append(precio_usd)
                
                if metros > 0:
                    precios_m2.append(precio_usd / metros)
                    metros_list.append(metros)
            
            return {
                "success": True,
                "filters_applied": {
                    "barrio": barrio,
                    "operacion": operacion,
                    "tipo": tipo
                },
                "result_count": len(propiedades),
                "statistics": {
                    "precio_promedio_usd": round(statistics.mean(precios), 2) if precios else None,
                    "precio_mediana_usd": round(statistics.median(precios), 2) if precios else None,
                    "precio_minimo_usd": min(precios) if precios else None,
                    "precio_maximo_usd": max(precios) if precios else None,
                    "precio_m2_promedio_usd": round(statistics.mean(precios_m2), 2) if precios_m2 else None,
                    "metros_promedio": round(statistics.mean(metros_list), 2) if metros_list else None
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @app.post("/api/stats/refresh")
    def refresh_data():
        """
        Recarga los datos desde el archivo propiedades.json
        """
        try:
            analyzer.reload()
            return {
                "success": True,
                "message": "Datos recargados correctamente",
                "total_propiedades": len(analyzer.propiedades)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @app.get("/api/stats/scrape")
    def scrape_market_stats(
        zone: str = Query(..., description="Barrio o zona a analizar"),
        operation: str = Query("venta", description="Tipo de operación"),
        property_type: str = Query("departamento", description="Tipo de propiedad")
    ):
        """
        Ejecuta el scraper para obtener datos reales del mercado inmobiliario
        
        Uso:
        - GET /api/stats/scrape?zone=microcentro
        - GET /api/stats/scrape?zone=palermo&operation=alquiler&property_type=casa
        """
        try:
            print(f"🌐 Scraping mercado: {zone} ({operation}, {property_type})")
            
            # Ejecutar scraper
            analyzer.scrape_market_data(zone, operation, property_type)
            
            if analyzer.scraper_data:
                return {
                    "success": True,
                    "message": f"Analizadas {analyzer.scraper_data.get('sample_size', 0)} propiedades",
                    "data": analyzer.scraper_data,
                    "statistics": analyzer.scraper_data.get('statistics', {})
                }
            else:
                return {
                    "success": False,
                    "message": "No se pudieron obtener datos del mercado",
                    "zone": zone
                }
        except Exception as e:
            print(f"❌ Error en scraping: {e}")
            return {"success": False, "error": str(e)}
    
    print("✅ Módulo de Estadísticas de Mercado integrado en FastAPI")


# ========================================
# EJECUCIÓN DIRECTA
# ========================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analizador de Mercado Inmobiliario Local")
    parser.add_argument("--barrio", help="Barrio específico a analizar")
    parser.add_argument("--json", action="store_true", help="Salida en formato JSON")
    
    args = parser.parse_args()
    
    analyzer = LocalMarketAnalyzer()
    
    if args.barrio:
        stats = analyzer.calculate_barrio_stats(args.barrio)
        result = analyzer._barrio_stats_to_dict(stats)
        result["propiedades"] = stats.propiedades
        
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"\n📊 Estadísticas para: {stats.nombre}")
            print(f"   Propiedades analizadas: {stats.cantidad_propiedades}")
            print(f"   Precio promedio: USD {stats.precio_promedio:,.2f}" if stats.precio_promedio else "   N/A")
            print(f"   Precio mediana: USD {stats.precio_mediana:,.2f}" if stats.precio_mediana else "   N/A")
            print(f"   Rango: USD {stats.precio_minimo:,.2f} - USD {stats.precio_maximo:,.2f}" if stats.precio_minimo else "   N/A")
            print(f"   Precio m² promedio: USD {stats.precio_m2_promedio:,.2f}" if stats.precio_m2_promedio else "   N/A")
            print(f"   Superficie promedio: {stats.metros_promedio:.1f} m²" if stats.metros_promedio else "   N/A")
    else:
        # Vista general
        overview = analyzer.to_api_response()
        if args.json:
            print(json.dumps(overview, indent=2, ensure_ascii=False))
        else:
            print("\n🏠 VISTA GENERAL DEL MERCADO")
            print("=" * 50)
            print(f"Total propiedades: {overview['overview']['total_propiedades']}")
            print(f"Barrios analizados: {overview['overview']['barrios_analizados']}")
            print(f"Precio promedio general: USD {overview['overview']['precio_promedio_general_usd']:,.2f}" if overview['overview']['precio_promedio_general_usd'] else "N/A")
            print(f"Precio m² promedio: USD {overview['overview']['precio_m2_promedio_general_usd']:,.2f}" if overview['overview']['precio_m2_promedio_general_usd'] else "N/A")
            print("\n📍 POR BARRIO:")
            for barrio in overview['barrios']:
                print(f"  • {barrio['nombre']}: {barrio['cantidad_propiedades']} propiedades, USD {barrio['precio_promedio']:,.0f} promedio" if barrio['precio_promedio'] else f"  • {barrio['nombre']}: Sin datos suficientes")
