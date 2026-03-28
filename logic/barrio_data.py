"""
Información complementaria de Gastronomía y Servicios Financieros para barrios de CABA
Esta información se usa para enriquecer los análisis de IA cuando no puede generarla completamente.
"""
from typing import Dict, List, Any

# ========================================
# GASTRONOMÍA POR BARRIO
# ========================================
# Zonas gastronómicas, restaurantes destacados, bares y cafes por barrio

GASTRONOMY_DATA = {
    "palermo": {
        "puntuacion": 95,
        "descripcion": "Palermo es el epicentro gastronómico de Buenos Aires, con una oferta enorme y diversa. Desde parrillas premium hasta restaurantes internacionales, pasando por food halls y cafes de especialidad.",
        "restaurantes_destacados": [
            "Don Julio (parrilla - mejor de LATAM)",
            "El Sanjuanino (parrilla)",
            "Caldén del Soho (parrilla)",
            "Hierro Parrilla",
            "Aramburu (gastronomía)",
            "Mishima (japonesa)"
        ],
        "zonas_gastronomicas": [
            "Palermo Soho - Honduras y Nicaragua",
            "Palermo Hollywood",
            "Botánico",
            "Costanera Norte"
        ],
        "tipo_comida": ["Parrillas", "Internacional", "Japonesa", "Italiana", "Vegetariana", "Food Trucks"],
        "bares_notables": [
            "Antares Palermo",
            "The Craft",
            "Verne Hotel"
        ],
        "cafes_especialidad": [
            "Lab Tostadores",
            "Café Kunstmann",
            "Saint Germain"
        ]
    },
    "recoleta": {
        "puntuacion": 85,
        "descripcion": "Zona elegante con alta concentración de restaurantes de categoría, cafes históricos y opciones gourmet. Ideal para ocasiones especiales y reuniones de negocios.",
        "restaurantes_destacados": [
            "La Cabaña (parrilla)",
            "Elena (gastronomía)",
            "Duhau Restaurant & Vinoteca",
            "Gioia Cocina Botánica",
            "Bis Bistró"
        ],
        "zonas_gastronomicas": [
            "Avenida Alvear",
            "Pedestrianas del centro histórico"
        ],
        "tipo_comida": ["Francesa", "Italiana", "Parrillas", "Gastronomía", "Cafes Históricos"],
        "bares_notables": [
            "Café Tortoni",
            "Bar Los Galgos",
            "Regio Bar"
        ],
        "cafes_especialidad": [
            "Café La Biela",
            "Café Tortoni",
            "Martínez"
        ]
    },
    "microcentro": {
        "puntuacion": 80,
        "descripcion": "Gran concentración de opciones para almuerzos de trabajo, bodegones clásicos y restaurantes rápidos. También cuenta con la peatonal Florida con múltiples cafes y快餐.",
        "restaurantes_destacados": [
            "Café Tortoni (histórico)",
            "El Obrero (bodegón)",
            "Pizzeria Guerrín",
            "Restaurante 1880",
            "Mercado San Miguel"
        ],
        "zonas_gastronomicas": [
            "Peatonal Florida",
            "San Nicolás",
            "Puerto Madero cercano"
        ],
        "tipo_comida": ["Bodegones", "Pizzerías", "Comida Rápida", "Cafes", "Empanadas"],
        "bares_notables": [
            "The Craft (cervecería)",
            "Antares"
        ],
        "cafes_especialidad": [
            "Café Tortoni",
            "Bar Federal",
            "Coffee Town"
        ]
    },
    "san telmo": {
        "puntuacion": 90,
        "descripcion": "Barrio bohemio con propuesta gastronómica ecléctica. Mezcla bodegones tradicionales, restaurantes modernos y una vibrante vida nocturna con bares y speakeasies.",
        "restaurantes_destacados": [
            "Hierro Parrilla San Telmo",
            "Anafe",
            "Anchoita",
            "Bar 878",
            "Café San Juan"
        ],
        "zonas_gastronomicas": [
            "Mercado de San Telmo",
            "Calle Defensa",
            "Parque Lezama"
        ],
        "tipo_comida": ["Parrillas", "Tapas", "Internacional", "Vegetariana", "Vinos"],
        "bares_notables": [
            "Bar 878",
            "The Boticario",
            "Florería Atlantico",
            "Doppelganger"
        ],
        "cafes_especialidad": [
            "Ninina Bakery",
            "Café con Libros"
        ]
    },
    "belgrano": {
        "puntuacion": 82,
        "descripcion": "Barrio residencial con excelente oferta gastronómica, especialmente en la zona de Chinatown y lungo calle Corrientes. Combina opciones familiares con restaurantes de nicho.",
        "restaurantes_destacados": [
            "Chinatown (zona gastronómica)",
            "Sarkis (armenia)",
            "Moe",
            "La Cervecería"
        ],
        "zonas_gastronomicas": [
            "Chinatown - Belgrano",
            "Corrientes al 9000",
            "Barrio Chino"
        ],
        "tipo_comida": ["China", "Armenia", "Parrillas", "Casera", "Internacional"],
        "bares_notables": [
            "Antares Belgrano",
            "Casona del Botánico"
        ],
        "cafes_especialidad": [
            "Matear",
            "Café 788"
        ]
    },
    "caballito": {
        "puntuacion": 75,
        "descripcion": "Barrio familiar con buena oferta de restaurantes tradicionales, Parrillas y cafes de barrio. La zona de Acoyte y Rivadavia ofrece opciones para todos los gustos.",
        "restaurantes_destacados": [
            "Pucara (parrilla)",
            "RonConCon (caribeña)",
            "The Oldest",
            "Aires de Campo"
        ],
        "zonas_gastronomicas": [
            "Avenida Acoyte",
            "Parque Rivadavia",
            "Centro comercial Caballito"
        ],
        "tipo_comida": ["Parrillas", "Casera", "Vegetariana", "Cafes de Barrio"],
        "bares_notables": [
            "The Oldest",
            "La Casona de Hortensia"
        ],
        "cafes_especialidad": [
            "Pichincha",
            "Café del Parque"
        ]
    },
    "villa crespo": {
        "puntuacion": 88,
        "descripcion": "Barrio en auge gastronómico con propuesta trendy y accesibles. Antigua industria reconvertida en locales de comida, con fuerte presencia de burgers, pizzas y bowles.",
        "restaurantes_destacados": [
            "Don Benito (bodegón)",
            "Mambo Burdo",
            "Burdo",
            "Sandro"
        ],
        "zonas_gastronomicas": [
            "Calle Aguirre",
            "Corrientes al 5600",
            "Malcolm"
        ],
        "tipo_comida": ["Bodegones", "Burgers", "Pizzas", "Vegana", "Internacional"],
        "bares_notables": [
            "Antares Villa Crespo",
            "Blest",
            "Para Vos"
        ],
        "cafes_especialidad": [
            "Mishka",
            "Hello Coffee"
        ]
    },
    "coghlan": {
        "puntuacion": 70,
        "descripcion": "Barrio residencial tranquilo con opciones principalmente locales y familiares. Menos turística pero con buena calidad en sus restaurants de barrio.",
        "restaurantes_destacados": [
            "Restaurantes de Avenida Constituyentes",
            "Parrillas locales"
        ],
        "zonas_gastronomicas": [
            "Avenida Constituyentes",
            "Avenida Melián"
        ],
        "tipo_comida": ["Parrillas", "Casera", "Comida Rápida"],
        "bares_notables": [
            "Bares de barrio"
        ],
        "cafes_especialidad": [
            "Cafes locales"
        ]
    },
    "núñez": {
        "puntuacion": 72,
        "descripcion": "Barrio mainly residencial con oferta gastronómica centrada en opciones de barrio y algunos restaurants cerca del centro comercial.",
        "restaurantes_destacados": [
            "Libertad (parrilla)",
            "Restaurantes de zona"
        ],
        "zonas_gastronomicas": [
            "Avenida Libertador",
            "Ciudad Universitaria"
        ],
        "tipo_comida": ["Parrillas", "Casera"],
        "bares_notables": [
            "Bares tradicionales"
        ],
        "cafes_especialidad": [
            "Cafes de barrio"
        ]
    },
    "saavedra": {
        "puntuacion": 68,
        "descripcion": "Barrio periférico con opciones principalmente de barrio. Menos diversidad pero con buenos restaurants familiares y Parrillas.",
        "restaurantes_destacados": [
            "Las Cuartetas (parrilla)",
            "Restaurantes de糯米Balkans"
        ],
        "zonas_gastronomicas": [
            "Avenida García del Río",
            "Avenida Melián"
        ],
        "tipo_comida": ["Parrillas", "Casera", "Balkánica"],
        "bares_notables": [
            "Bares de barrio"
        ],
        "cafes_especialidad": [
            "Cafes locales"
        ]
    },
    "chacarita": {
        "puntuacion": 92,
        "descripcion": "Chacarita es uno de los barrios más cool de Buenos Aires, seleccionado por Time Out como uno de los mejores del mundo. Centro gastronómico emergente con propuesta innovadora y ambiente bohemio.",
        "restaurantes_destacados": [
            "Anchoita (vinos y platitos)",
            "El Imperio de la Pizza",
            "Albamonte Ristorante",
            "Ajo Negro",
            "El Puelche (parrilla)",
            "Sarkis (armenio)"
        ],
        "zonas_gastronomicas": [
            "Circuito Newbery (Avenida Dorrego)",
            "Avenida Jorge Newbery",
            "Calle Honduras"
        ],
        "tipo_comida": ["Parrillas", "Italiana", "Pizza", "Vinos", "Armenia", "Creativa"],
        "bares_notables": [
            "La Fuerza Bar",
            "Lardito",
            "Mil y pico",
            "Ipolitina",
            "Bar Guevara"
        ],
        "cafes_especialidad": [
            "Malcriada Cafe",
            "Bilbo Café",
            "La Esquina",
            "Adorado"
        ]
    },
    "flores": {
        "puntuacion": 78,
        "descripcion": "Barrio familiar con oferta gastronómica centrada en Parrillas, bodegones y cafeterías. Zona comercial activa con opciones para todos los días.",
        "restaurantes_destacados": [
            "Garibaldi Restaurante",
            "Caldén del Soho",
            "Fogón (steakhouse)",
            "La Pizzeria de Flores",
            "Cocina Orillera",
            "Doc Brown"
        ],
        "zonas_gastronomicas": [
            "Avenida Avellaneda",
            "Plaza Flores",
            "Avenida Nazca"
        ],
        "tipo_comida": ["Parrillas", "Pizzerías", "Cafés", "Casera", "Steakhouse"],
        "bares_notables": [
            "Bar Flores",
            "La Cervecería"
        ],
        "cafes_especialidad": [
            "Lab Sucré (pastelería)",
            "Fiamma Café"
        ]
    },
    "almagro": {
        "puntuacion": 80,
        "descripcion": "Barrio clásico con oferta gastronómica متنوعة. Desde bodegones tradicionales hasta restaurants modernos, especialmente en la zona de Corrientes.",
        "restaurantes_destacados": [
            "El Obrero (bodegón)",
            "Santos Alghero (italiana)",
            "La Estancia (parrilla)",
            "Café San Ignacio"
        ],
        "zonas_gastronomicas": [
            "Avenida Corrientes",
            "Calle Bulnes",
            "Plaza Almagro"
        ],
        "tipo_comida": ["Bodegones", "Parrillas", "Italiana", "Cafes"],
        "bares_notables": [
            "Bar El Federal",
            "Antares Almagro"
        ],
        "cafes_especialidad": [
            "Café del Museo",
            "Café Varsoviana"
        ]
    },
    "boedo": {
        "puntuacion": 72,
        "descripcion": "Barrio tanguero con oferta gastronómica tradicional. Famoso por sus Parrillas y bodegones de barrio.",
        "restaurantes_destacados": [
            "Parrilla Boedo",
            "El Club de la Parrilla",
            "Casa del Folklore"
        ],
        "zonas_gastronomicas": [
            "Avenida Boedo",
            "Avenida San Juan"
        ],
        "tipo_comida": ["Parrillas", "Casera", "Tanguera"],
        "bares_notables": [
            "Bar El Ancla"
        ],
        "cafes_especialidad": [
            "Cafes de barrio"
        ]
    },
    "balvanera": {
        "puntuacion": 75,
        "descripcion": "Barrio comercial con oferta gastronómica variada. Gran concentración de opciones económicas y kioscos.",
        "restaurantes_destacados": [
            "Restaurantes de Avenida Corrientes",
            "Kioscos de la zona",
            "Comida rápida local"
        ],
        "zonas_gastronomicas": [
            "Avenida Corrientes",
            "Avenida 9 de Julio"
        ],
        "tipo_comida": ["Comida Rápida", "Kioscos", "Casera"],
        "bares_notables": [
            "Bares de Corrientes"
        ],
        "cafes_especialidad": [
            "Cafes 24 horas"
        ]
    },
    "barracas": {
        "puntuacion": 76,
        "descripcion": "Barrio en transformación con creciente oferta gastronómica. Mezcla de locaux tradicionales y nuevos restaurants.",
        "restaurantes_destacados": [
            "Los Galgos (clásico)",
            "Bendita Pizza",
            "Café Negro"
        ],
        "zonas_gastronomicas": [
            "Avenida Montes de Oca",
            "Calle Lavardén"
        ],
        "tipo_comida": ["Parrillas", "Pizza", "Creativa"],
        "bares_notables": [
            "Los Galgos",
            "Antares Barracas"
        ],
        "cafes_especialidad": [
            "Café Negro"
        ]
    },
    "la boca": {
        "puntuacion": 70,
        "descripcion": "Barrio turístico con oferta gastronómica centrada en Parrillas y comida camsinera. Caminito atrae muchos restaurants.",
        "restaurantes_destacados": [
            "El Ranchón (camsinero)",
            "Parrilla La Boca",
            "Restaurante Caminito"
        ],
        "zonas_gastronomicas": [
            "Caminito",
            "Avenida Pedro de Mendoza"
        ],
        "tipo_comida": ["Parrillas", "Camsinera", "Turística"],
        "bares_notables": [
            "Bar de la Vuelta"
        ],
        "cafes_especialidad": [
            "Cafes turísticos"
        ]
    },
    "puerto madero": {
        "puntuacion": 95,
        "descripcion": "Zona premium con restaurants de alta gama y vistas al río. Gran concentración de gastronomía upscale.",
        "restaurantes_destacados": [
            "Restó SCA (Michelin)",
            "Cabaña Las Lilas",
            "Santos Brasas del Mar",
            "Il Gatto Pizza",
            "Una y Uma"
        ],
        "zonas_gastronomicas": [
            "Dique 4",
            "Puerto Madero Central",
            "Muelle Dique 3"
        ],
        "tipo_comida": ["Gastronomía", "Mariscos", "Parrillas Premium", "Italiana"],
        "bares_notables": [
            "Mojito Bar",
            "Sky Bar"
        ],
        "cafes_especialidad": [
            "Starbucks Reserve",
            "Café Martínez"
        ]
    },
    "retiro": {
        "puntuacion": 85,
        "descripcion": "Zona céntrica con oferta mixta. Desde restaurants de negocios hasta opciones rápidas.",
        "restaurantes_destacados": [
            "Hard Rock Cafe",
            "Café Tortoni",
            "Restaurant 1880"
        ],
        "zonas_gastronomicas": [
            "Plaza San Martín",
            "Avenida Leandro N. Alem"
        ],
        "tipo_comida": ["Internacional", "Cafes Históricos", "Comida Rápida"],
        "bares_notables": [
            "Café Tortoni",
            "Bar El Federal"
        ],
        "cafes_especialidad": [
            "Café Tortoni",
            "Coffee Town"
        ]
    },
    "villa lugano": {
        "puntuacion": 65,
        "descripcion": "Barrio periférico con opciones gastronómicas básicas de barrio. Menor diversidad pero precios accesibles.",
        "restaurantes_destacados": [
            "Parrillas de barrio",
            "Comida casera"
        ],
        "zonas_gastronomicas": [
            "Avenida Roca",
            "Avenida Fernandez de la Cruz"
        ],
        "tipo_comida": ["Parrillas", "Casera", "Comida Rápida"],
        "bares_notables": [
            "Bares de barrio"
        ],
        "cafes_especialidad": [
            "Cafes locales"
        ]
    },
    "mataderos": {
        "puntuacion": 68,
        "descripcion": "Barrio tradicional con oferta gastronómica centrada en Parrillas y comida criolla. Famoso por su Feria de Mataderos.",
        "restaurantes_destacados": [
            "Parrilla Los Dos Hermanos",
            "Restaurantes de la Feria",
            "El Rodeo (parrilla)"
        ],
        "zonas_gastronomicas": [
            "Feria de Mataderos",
            "Avenida Alberdi"
        ],
        "tipo_comida": ["Parrillas", "Criolla", "Casera"],
        "bares_notables": [
            "Bares de la Feria"
        ],
        "cafes_especialidad": [
            "Cafes de barrio"
        ]
    },
    "liniers": {
        "puntuacion": 70,
        "descripcion": "Barrio comercial con oferta gastronómica variada. Buena presencia de Parrillas y restaurants familiares.",
        "restaurantes_destacados": [
            "Parrilla Liniers",
            "El Sanjuanino",
            "Restaurantes de Av. Rivadavia"
        ],
        "zonas_gastronomicas": [
            "Avenida Rivadavia",
            "Avenida Bilbao"
        ],
        "tipo_comida": ["Parrillas", "Casera"],
        "bares_notables": [
            "Bares de barrio"
        ],
        "cafes_especialidad": [
            "Cafes locales"
        ]
    },
    "constitucion": {
        "puntuacion": 72,
        "descripcion": "Zona de transbordo con oferta gastronómica práctica. Muchas opciones para viajeros.",
        "restaurantes_destacados": [
            "Restaurantes de la terminal",
            "Comida rápida"
        ],
        "zonas_gastronomicas": [
            "Plaza Constitución",
            "Avenida Juan B. Justo"
        ],
        "tipo_comida": ["Comida Rápida", "Casera"],
        "bares_notables": [
            "Bares de la zona"
        ],
        "cafes_especialidad": [
            "Kioscos y cafes"
        ]
    },
    "villa devoto": {
        "puntuacion": 75,
        "descripcion": "Barrio residencial italiano con excelente oferta gastronómica. Parrillas, trattorias y cafes de calidad.",
        "restaurantes_destacados": [
            "El Fuego (parrilla)",
            "Trattoria Devoto",
            "Café Tortoni Jr."
        ],
        "zonas_gastronomicas": [
            "Avenida San Martín",
            "Avenida Nazca"
        ],
        "tipo_comida": ["Parrillas", "Italiana", "Cafes"],
        "bares_notables": [
            "Antares Devoto",
            "Bar de la Plaza"
        ],
        "cafes_especialidad": [
            "Cafe de la Plaza",
            "Devoto Coffee"
        ]
    },
    "villa del parque": {
        "puntuacion": 72,
        "descripcion": "Barrio familiar con oferta gastronómica tradicional. Buenos restaurants de barrio y Parrillas.",
        "restaurantes_destacados": [
            "Parrilla Villa del Parque",
            "Restaurantes familiares"
        ],
        "zonas_gastronomicas": [
            "Avenida Nazca",
            "Avenida Galvan"
        ],
        "tipo_comida": ["Parrillas", "Casera"],
        "bares_notables": [
            "Bares de barrio"
        ],
        "cafes_especialidad": [
            "Cafes locales"
        ]
    },
    "villa urquiza": {
        "puntuacion": 78,
        "descripcion": "Barrio residencial con buena oferta gastronómica. Mezcla de Parrillas tradicionales y nuevos cafes.",
        "restaurantes_destacados": [
            "Don Julio Jr.",
            "La Glorieta",
            "Parrilla Urquiza"
        ],
        "zonas_gastronomicas": [
            "Avenida Triunvirato",
            "Avenida Monroe"
        ],
        "tipo_comida": ["Parrillas", "Cafes", "Casera"],
        "bares_notables": [
            "Antares Urquiza",
            "Bar La Plaza"
        ],
        "cafes_especialidad": [
            "Café Urquiza",
            "Milky Way"
        ]
    },
    "villa ortuzar": {
        "puntuacion": 73,
        "descripcion": "Barrio residencial tranquilo con oferta gastronómica básica de barrio.",
        "restaurantes_destacados": [
            "Restaurantes de zona"
        ],
        "zonas_gastronomicas": [
            "Avenida Corrientes",
            "Avenida Triunvirato"
        ],
        "tipo_comida": ["Parrillas", "Casera"],
        "bares_notables": [
            "Bares de barrio"
        ],
        "cafes_especialidad": [
            "Cafes locales"
        ]
    },
    "villa general mitre": {
        "puntuacion": 68,
        "descripcion": "Barrio periférico con servicios gastronómicos básicos.",
        "restaurantes_destacados": [
            "Parrillas locales"
        ],
        "zonas_gastronomicas": [
            "Avenida Lincoln",
            "Avenida San Martín"
        ],
        "tipo_comida": ["Parrillas", "Casera"],
        "bares_notables": [
            "Bares de barrio"
        ],
        "cafes_especialidad": [
            "Cafes locales"
        ]
    },
    "villa santa rita": {
        "puntuacion": 65,
        "descripcion": "Barrio con oferta gastronómica limitada de barrio.",
        "restaurantes_destacados": [
            "Comida de barrio"
        ],
        "zonas_gastronomicas": [
            "Avenida Rivadavia"
        ],
        "tipo_comida": ["Casera", "Comida Rápida"],
        "bares_notables": [
            "Bares locales"
        ],
        "cafes_especialidad": [
            "Cafes básicos"
        ]
    },
    "villa real": {
        "puntuacion": 62,
        "descripcion": "Barrio periférico con servicios gastronómicos básicos.",
        "restaurantes_destacados": [
            "Comida de barrio"
        ],
        "zonas_gastronomicas": [
            "Avenida Juan B. Justo"
        ],
        "tipo_comida": ["Casera", "Comida Rápida"],
        "bares_notables": [
            "Bares locales"
        ],
        "cafes_especialidad": [
            "Cafes básicos"
        ]
    },
    "villa pueyrredon": {
        "puntuacion": 70,
        "descripcion": "Barrio residencial con oferta gastronómica de barrio.",
        "restaurantes_destacados": [
            "Restaurantes locales"
        ],
        "zonas_gastronomicas": [
            "Avenida Dr. Ricardo Balbín"
        ],
        "tipo_comida": ["Parrillas", "Casera"],
        "bares_notables": [
            "Bares de zona"
        ],
        "cafes_especialidad": [
            "Cafes locales"
        ]
    },
    "villa luro": {
        "puntuacion": 72,
        "descripcion": "Barrio con oferta gastronómica centrada en Parrillas y restaurants familiares.",
        "restaurantes_destacados": [
            "Parrilla Luro",
            "El Palacio de la Parrilla"
        ],
        "zonas_gastronomicas": [
            "Avenida Luro",
            "Avenida Rivadavia"
        ],
        "tipo_comida": ["Parrillas", "Casera"],
        "bares_notables": [
            "Bares de barrio"
        ],
        "cafes_especialidad": [
            "Cafes locales"
        ]
    },
    "parque avellaneda": {
        "puntuacion": 68,
        "descripcion": "Barrio periférico con oferta gastronómica básica.",
        "restaurantes_destacados": [
            "Comida de barrio"
        ],
        "zonas_gastronomicas": [
            "Avenida Directorio"
        ],
        "tipo_comida": ["Casera", "Comida Rápida"],
        "bares_notables": [
            "Bares locales"
        ],
        "cafes_especialidad": [
            "Cafes básicos"
        ]
    },
    "parque chacabuco": {
        "puntuacion": 70,
        "descripcion": "Barrio con oferta gastronómica de barrio y algunas Parrillas.",
        "restaurantes_destacados": [
            "Parrilla del Parque"
        ],
        "zonas_gastronomicas": [
            "Avenida Directorio",
            "Avenida La Plata"
        ],
        "tipo_comida": ["Parrillas", "Casera"],
        "bares_notables": [
            "Bares de zona"
        ],
        "cafes_especialidad": [
            "Cafes locales"
        ]
    },
    "parque patricios": {
        "puntuacion": 68,
        "descripcion": "Barrio en desarrollo con oferta gastronómica emergente.",
        "restaurantes_destacados": [
            "Nuevos locales de la zona"
        ],
        "zonas_gastronomicas": [
            "Avenida Juan B. Justo",
            "Avenida Amancio Alcorta"
        ],
        "tipo_comida": ["Casera", "Comida Rápida"],
        "bares_notables": [
            "Bares emergentes"
        ],
        "cafes_especialidad": [
            "Cafes de la zona"
        ]
    },
    "nueva pompeya": {
        "puntuacion": 65,
        "descripcion": "Barrio periférico con servicios gastronómicos básicos.",
        "restaurantes_destacados": [
            "Comida de barrio"
        ],
        "zonas_gastronomicas": [
            "Avenida Sáenz"
        ],
        "tipo_comida": ["Casera", "Comida Rápida"],
        "bares_notables": [
            "Bares locales"
        ],
        "cafes_especialidad": [
            "Cafes básicos"
        ]
    },
    "monte castro": {
        "puntuacion": 65,
        "descripcion": "Barrio periférico con oferta gastronómica limitada.",
        "restaurantes_destacados": [
            "Comida de barrio"
        ],
        "zonas_gastronomicas": [
            "Avenida Juan B. Justo",
            "Avenida Luro"
        ],
        "tipo_comida": ["Casera", "Comida Rápida"],
        "bares_notables": [
            "Bares locales"
        ],
        "cafes_especialidad": [
            "Cafes básicos"
        ]
    },
    "la paternal": {
        "puntuacion": 72,
        "descripcion": "Barrio con oferta gastronómica emergente cerca de Chacarita.",
        "restaurantes_destacados": [
            "Nuevos restaurants",
            "Cafes de la zona"
        ],
        "zonas_gastronomicas": [
            "Avenida Corrientes",
            "Avenida San Martín"
        ],
        "tipo_comida": ["Creativa", "Cafes", "Casera"],
        "bares_notables": [
            "Bares emergentes"
        ],
        "cafes_especialidad": [
            "Cafes de zona"
        ]
    },
    "versailles": {
        "puntuacion": 65,
        "descripcion": "Barrio pequeño con servicios gastronómicos básicos.",
        "restaurantes_destacados": [
            "Comida de barrio"
        ],
        "zonas_gastronomicas": [
            "Avenida Rivadavia"
        ],
        "tipo_comida": ["Casera", "Comida Rápida"],
        "bares_notables": [
            "Bares locales"
        ],
        "cafes_especialidad": [
            "Cafes básicos"
        ]
    },
    "floresta": {
        "puntuacion": 68,
        "descripcion": "Barrio tradicional con oferta gastronómica de barrio.",
        "restaurantes_destacados": [
            "Parrilla Floresta",
            "Restaurantes familiares"
        ],
        "zonas_gastronomicas": [
            "Avenida Avellaneda",
            "Avenidaellan"
        ],
        "tipo_comida": ["Parrillas", "Casera"],
        "bares_notables": [
            "Bares de zona"
        ],
        "cafes_especialidad": [
            "Cafes locales"
        ]
    },
    "agronomia": {
        "puntuacion": 70,
        "descripcion": "Barrio académico con cafes y opciones sencillas.",
        "restaurantes_destacados": [
            "Cafes de la facultad",
            "Comida rápida"
        ],
        "zonas_gastronomicas": [
            "Avenida San Martín",
            "Avenida Nazca"
        ],
        "tipo_comida": ["Cafes", "Comida Rápida"],
        "bares_notables": [
            "Bares de la zona"
        ],
        "cafes_especialidad": [
            "Cafes académicos"
        ]
    },
    "colegiales": {
        "puntuacion": 78,
        "descripcion": "Barrio residencial con creciente oferta gastronómica. Mezcla de clasicos y nuevos locales.",
        "restaurantes_destacados": [
            "Parrilla Colegiales",
            "La Cervecería",
            "Cafes modernos"
        ],
        "zonas_gastronomicas": [
            "Avenida Córdoba",
            "Avenida_del Libertador"
        ],
        "tipo_comida": ["Parrillas", "Cafes", "Creativa"],
        "bares_notables": [
            "Antares Colegiales",
            "Blest"
        ],
        "cafes_especialidad": [
            "Cafes modernos",
            "Pastelerías"
        ]
    },
    "parque chas": {
        "puntuacion": 70,
        "descripcion": "Barrio residencial con oferta gastronómica básica de barrio.",
        "restaurantes_destacados": [
            "Restaurantes locales"
        ],
        "zonas_gastronomicas": [
            "Avenida Dr. Tristán Achá"
        ],
        "tipo_comida": ["Casera", "Comida Rápida"],
        "bares_notables": [
            "Bares de zona"
        ],
        "cafes_especialidad": [
            "Cafes locales"
        ]
    },
    "san cristobal": {
        "puntuacion": 72,
        "descripcion": "Barrio con oferta gastronómica variada, especialmente cerca de Boedo.",
        "restaurantes_destacados": [
            "Parrilla San Cristóbal",
            "Restaurantes de Avenida San Juan"
        ],
        "zonas_gastronomicas": [
            "Avenida San Juan",
            "Avenida Boedo"
        ],
        "tipo_comida": ["Parrillas", "Casera"],
        "bares_notables": [
            "Bares de zona"
        ],
        "cafes_especialidad": [
            "Cafes locales"
        ]
    },
    "san nicolas": {
        "puntuacion": 80,
        "descripcion": "Centro cultural con oferta gastronómica diverse. Teatro, cafes y restaurants.",
        "restaurantes_destacados": [
            "Cafes del Centro",
            "Restaurants de Avenida Corrientes",
            "Pizzerías clásicas"
        ],
        "zonas_gastronomicas": [
            "Avenida Corrientes",
            "Avenida 9 de Julio"
        ],
        "tipo_comida": ["Pizzas", "Cafes", "Casera"],
        "bares_notables": [
            "Bares de Corrientes",
            "Clásicos porteños"
        ],
        "cafes_especialidad": [
            "Cafes históricos"
        ]
    },
    "monserrat": {
        "puntuacion": 78,
        "descripcion": "Barrio histórico con oferta gastronómica enfocada en turistas y oficinistas.",
        "restaurantes_destacados": [
            "Café Tortoni",
            "El Federal",
            "Restaurantes de Mayo"
        ],
        "zonas_gastronomicas": [
            "Plaza de Mayo",
            "Avenida de Mayo"
        ],
        "tipo_comida": ["Cafes Históricos", "Casera", "Turística"],
        "bares_notables": [
            "Café Tortoni",
            "El Federal"
        ],
        "cafes_especialidad": [
            "Cafes históricos",
            "Confiterías"
        ]
    }
}

# ========================================
# SERVICIOS FINANCIEROS POR BARRIO
# ========================================
# Bancos, cajeros automáticos, sucursales y servicios financieros por barrio

FINANCIAL_DATA = {
    "microcentro": {
        "puntuacion": 100,
        "descripcion": "El Microcentro es el corazón financiero de Buenos Aires, con la mayor concentración de bancos, cajeros y servicios financieros de la ciudad. Todas las entidades bancarias principales tienen sucursales aquí.",
        "bancos": [
            "Banco de la Nación Argentina (Casa Central)",
            "Banco de la Provincia de Buenos Aires",
            "Banco Ciudad",
            "Banco Santander",
            "Banco BBVA",
            "Banco Macro",
            "Banco ICBC",
            "Banco Supervielle",
            "Banco Comafi",
            "Banco Hipotecario"
        ],
        "cajeros_automaticos": [
            "Alta concentración en Av. Corrientes, Florida, Sarmiento",
            "Red Banelco y Link disponibles 24/7",
            "Cajeros con función depósito en entidades principales"
        ],
        "sucursales_bancarias": [
            "Av. Rivadavia 8699 (BNA)",
            "Carlos Pellegrini 471 (Banco Ciudad)",
            "Av. Santa Fe 2299 (múltiples bancos)",
            "Av. Córdoba 900 (zona bancaria)"
        ],
        "otros_servicios": [
            "Casas de cambio (Florida)",
            "Compañías de seguros",
            "Bolsa de Comercio de Buenos Aires"
        ]
    },
    "recoleta": {
        "puntuacion": 90,
        "descripcion": "Zona premium con excelentes servicios financieros. Sucursales bancarias de primer nivel y cajeros automáticos distribuidos por toda la zona.",
        "bancos": [
            "Banco Ciudad (Sucursal Barrio Norte)",
            "Banco Supervielle",
            "Banco Santander",
            "Banco BBVA"
        ],
        "cajeros_automaticos": [
            "Alta disponibilidad en Av. Santa Fe, Cerrito",
            "Cajeros Link y Banelco",
            "Sucursales con terminal de autoservicio"
        ],
        "sucursales_bancarias": [
            "Av. Santa Fe 2600 (Banco Ciudad)",
            "Av. del Libertador 1500",
            "Avenida Alvear"
        ],
        "otros_servicios": [
            "Casas de cambio",
            "Financieras",
            "Fondos de inversión"
        ]
    },
    "palermo": {
        "puntuacion": 85,
        "descripcion": "Excelente cobertura de servicios financieros con sucursales bancarias y cajeros automáticos distribuidos en las zonas comerciales.",
        "bancos": [
            "Banco Ciudad",
            "Banco Supervielle",
            "Banco Macro",
            "Banco Santander"
        ],
        "cajeros_automaticos": [
            "Av. Santa Fe y Juan B. Justo",
            "Distrito Arcos",
            "Shopping Alta Málaga"
        ],
        "sucursales_bancarias": [
            "Av. Santa Fe 3200",
            "Av. Córdoba 4900",
            "Palermo Hollywood"
        ],
        "otros_servicios": [
            "Puntos de pago (Rapipago, PagoFácil)",
            "Casas de cambio",
            "Financieras"
        ]
    },
    "san telmo": {
        "puntuacion": 75,
        "descripcion": "Buena cobertura de servicios financieros básicos. Bancos tradicionales y puntos de pago distribuidos en el barrio.",
        "bancos": [
            "Banco Ciudad",
            "Banco Supervielle",
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Av. San Juan",
            "Calle Defensa",
            "Plaza Dorrego"
        ],
        "sucursales_bancarias": [
            "Av. San Juan 900",
            "Carlos Calvo 500"
        ],
        "otros_servicios": [
            "Puntos Rapipago",
            "PagoFácil",
            "Casas de cambio menores"
        ]
    },
    "belgrano": {
        "puntuacion": 82,
        "descripcion": "Buenos servicios financieros con presencia de bancos importantes y zona de Chinatown con casas de cambio.",
        "bancos": [
            "Banco Ciudad",
            "Banco Supervielle",
            "Banco Macro",
            "Banco Santander"
        ],
        "cajeros_automaticos": [
            "Avenida Monroe",
            "Avenida Cabildo",
            "Zona Chinatown"
        ],
        "sucursales_bancarias": [
            "Avenida Cabildo 2000",
            "Avenida Monroe 4500"
        ],
        "otros_servicios": [
            "Casas de cambio (Barrio Chino)",
            "Puntos de pago",
            "Financieras"
        ]
    },
    "caballito": {
        "puntuacion": 78,
        "descripcion": "Buenos servicios financieros con bancos y cajeros automáticos distribuidos por las avenues principales del barrio.",
        "bancos": [
            "Banco Ciudad",
            "Banco Supervielle",
            "Banco Macro",
            "Banco Santander"
        ],
        "cajeros_automaticos": [
            "Avenida Rivadavia",
            "Avenida Acoyte",
            "Parque Rivadavia"
        ],
        "sucursales_bancarias": [
            "Avenida Rivadavia 5400",
            "Avenida La Plata 537"
        ],
        "otros_servicios": [
            "Puntos Rapipago",
            "PagoFácil",
            "Cajas de seguridad (algunos bancos)"
        ]
    },
    "villa crespo": {
        "puntuacion": 72,
        "descripcion": "Servicios financieros básicos con bancos y cajeros automáticos en las zonas comerciales principales.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro",
            "Banco Supervielle"
        ],
        "cajeros_automaticos": [
            "Avenida Corrientes",
            "Calle Aguirre"
        ],
        "sucursales_bancarias": [
            "Avenida Corrientes 5600"
        ],
        "otros_servicios": [
            "Puntos de pago",
            "Financieras menores"
        ]
    },
    "núñez": {
        "puntuacion": 70,
        "descripcion": "Servicios financieros adecuados para un barrio residencial, con bancos y cajeros en las zonas comerciales.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Libertador",
            "Avenida Constituyentes"
        ],
        "sucursales_bancarias": [
            "Avenida Libertador 7500"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "saavedra": {
        "puntuacion": 65,
        "descripcion": "Servicios financieros básicos de barrio, suficientes para necesidades cotidianas.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida García del Río",
            "Avenida Melián"
        ],
        "sucursales_bancarias": [
            "Avenida García del Río 2700"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "coghlan": {
        "puntuacion": 68,
        "descripcion": "Servicios financieros de barrio con bancos y cajeros en las avenues principales.",
        "bancos": [
            "Banco Ciudad",
            "Banco Supervielle"
        ],
        "cajeros_automaticos": [
            "Avenida Constituyentes",
            "Avenida Melián"
        ],
        "sucursales_bancarias": [
            "Avenida Constituyentes 5100"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "chacarita": {
        "puntuacion": 80,
        "descripcion": "Buenos servicios financieros con presencia de bancos importantes en la zona. Chacarita tiene sucursales bancarias modernas y buena distribución de cajeros.",
        "bancos": [
            "Banco BBVA (Sucursal Av. Álvarez Thomas 402)",
            "Banco Ciudad",
            "Banco Supervielle",
            "Banco Macro",
            "Banco Santander"
        ],
        "cajeros_automaticos": [
            "Avenida Corrientes",
            "Avenida Dorrego",
            "Avenida Jorge Newbery"
        ],
        "sucursales_bancarias": [
            "Av. Álvarez Thomas 402 (BBVA)",
            "Avenida Corrientes 5300",
            "Avenida Dorrego 1200"
        ],
        "otros_servicios": [
            "Puntos Rapipago",
            "PagoFácil",
            "Casas de cambio"
        ]
    },
    "flores": {
        "puntuacion": 75,
        "descripcion": "Buenos servicios financieros con bancos y cajeros en las zonas comerciales principales del barrio.",
        "bancos": [
            "Banco Ciudad",
            "Banco Supervielle",
            "Banco Macro",
            "Banco Santander"
        ],
        "cajeros_automaticos": [
            "Avenida Avellaneda",
            "Avenida Nazca",
            "Plaza Flores"
        ],
        "sucursales_bancarias": [
            "Avenida Avellaneda 3200",
            "Avenida Nazca 2800"
        ],
        "otros_servicios": [
            "Puntos Rapipago",
            "PagoFácil",
            "Financieras"
        ]
    },
    "almagro": {
        "puntuacion": 78,
        "descripcion": "Buenos servicios financieros con bancos distribuidos por Avenida Corrientes y zonas comerciales.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro",
            "Banco Supervielle",
            "Banco BBVA"
        ],
        "cajeros_automaticos": [
            "Avenida Corrientes",
            "Avenida Rivadavia",
            "Avenida Bulnes"
        ],
        "sucursales_bancarias": [
            "Avenida Corrientes 3400",
            "Avenida Rivadavia 4200"
        ],
        "otros_servicios": [
            "Puntos Rapipago",
            "PagoFácil"
        ]
    },
    "boedo": {
        "puntuacion": 72,
        "descripcion": "Servicios financieros adecuados con bancos de barrio y cajeros automáticos.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Boedo",
            "Avenida San Juan"
        ],
        "sucursales_bancarias": [
            "Avenida Boedo 900",
            "Avenida San Juan 3800"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "balvanera": {
        "puntuacion": 75,
        "descripcion": "Gran concentración de servicios financieros por ser zona comercial céntrica.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro",
            "Banco BBVA",
            "Banco Supervielle"
        ],
        "cajeros_automaticos": [
            "Avenida Corrientes",
            "Avenida 9 de Julio",
            "Avenida Rivadavia"
        ],
        "sucursales_bancarias": [
            "Avenida Corrientes 2600",
            "Avenida Rivadavia 2800"
        ],
        "otros_servicios": [
            "Puntos Rapipago",
            "PagoFácil",
            "Casas de cambio"
        ]
    },
    "barracas": {
        "puntuacion": 70,
        "descripcion": "Servicios financieros en desarrollo con bancos y puntos de pago.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Montes de Oca",
            "Avenida Suárez"
        ],
        "sucursales_bancarias": [
            "Avenida Montes de Oca 700"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "la boca": {
        "puntuacion": 65,
        "descripcion": "Servicios financieros básicos con bancos y cajeros en la zona turística.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Pedro de Mendoza",
            "Calle Caminito"
        ],
        "sucursales_bancarias": [
            "Avenida Pedro de Mendoza 1100"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "puerto madero": {
        "puntuacion": 95,
        "descripcion": "Servicios financieros premium con bancos de primer nivel y cajeros modernos.",
        "bancos": [
            "Banco de la Nación Argentina",
            "Banco Ciudad",
            "Banco Santander",
            "Banco BBVA",
            "Banco Supervielle"
        ],
        "cajeros_automaticos": [
            "Dique 4",
            "Puerto Madero Central",
            "Avenida Alicia Moreau de Justo"
        ],
        "sucursales_bancarias": [
            "Avenida Alicia Moreau de Justo 1000",
            "Dique 4 200"
        ],
        "otros_servicios": [
            "Casas de cambio",
            "Financieras premium",
            "Cajas de seguridad"
        ]
    },
    "retiro": {
        "puntuacion": 88,
        "descripcion": "Excelentes servicios financieros cerca de la zona bancaria de Plaza San Martín.",
        "bancos": [
            "Banco de la Nación Argentina",
            "Banco Ciudad",
            "Banco BBVA",
            "Banco Santander"
        ],
        "cajeros_automaticos": [
            "Plaza San Martín",
            "Avenida Leandro N. Alem",
            "Avenida del Libertador"
        ],
        "sucursales_bancarias": [
            "Plaza San Martín",
            "Avenida del Libertador 100"
        ],
        "otros_servicios": [
            "Casas de cambio",
            "Financieras"
        ]
    },
    "villa lugano": {
        "puntuacion": 60,
        "descripcion": "Servicios financieros básicos de barrio.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Roca",
            "Avenida Fernández de la Cruz"
        ],
        "sucursales_bancarias": [
            "Avenida Roca 7600"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "mataderos": {
        "puntuacion": 65,
        "descripcion": "Servicios financieros básicos con bancos de barrio.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Alberdi",
            "Avenida Juan B. Justo"
        ],
        "sucursales_bancarias": [
            "Avenida Alberdi 6200"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "liniers": {
        "puntuacion": 68,
        "descripcion": "Buenos servicios financieros con bancos y cajeros en Avenida Rivadavia.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro",
            "Banco Supervielle"
        ],
        "cajeros_automaticos": [
            "Avenida Rivadavia",
            "Avenida Bilbao"
        ],
        "sucursales_bancarias": [
            "Avenida Rivadavia 10400"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "constitucion": {
        "puntuacion": 72,
        "descripcion": "Buenos servicios financieros con bancos y cajeros cerca de la terminal.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro",
            "Banco BBVA"
        ],
        "cajeros_automaticos": [
            "Plaza Constitución",
            "Avenida Juan B. Justo"
        ],
        "sucursales_bancarias": [
            "Plaza Constitución"
        ],
        "otros_servicios": [
            "Puntos de pago",
            "Casas de cambio"
        ]
    },
    "villa devoto": {
        "puntuacion": 75,
        "descripcion": "Buenos servicios financieros con bancos y cajeros en zonas comerciales.",
        "bancos": [
            "Banco Ciudad",
            "Banco Supervielle",
            "Banco Macro",
            "Banco BBVA"
        ],
        "cajeros_automaticos": [
            "Avenida San Martín",
            "Avenida Nazca"
        ],
        "sucursales_bancarias": [
            "Avenida San Martín 5300",
            "Avenida Nazca 4600"
        ],
        "otros_servicios": [
            "Puntos Rapipago",
            "PagoFácil"
        ]
    },
    "villa del parque": {
        "puntuacion": 70,
        "descripcion": "Servicios financieros de barrio con bancos y puntos de pago.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Nazca",
            "Avenida Galvan"
        ],
        "sucursales_bancarias": [
            "Avenida Nazca 3900"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "villa urquiza": {
        "puntuacion": 75,
        "descripcion": "Buenos servicios financieros con bancos y cajeros distribuidos.",
        "bancos": [
            "Banco Ciudad",
            "Banco Supervielle",
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Triunvirato",
            "Avenida Monroe"
        ],
        "sucursales_bancarias": [
            "Avenida Triunvirato 3000",
            "Avenida Monroe 4700"
        ],
        "otros_servicios": [
            "Puntos Rapipago",
            "PagoFácil"
        ]
    },
    "villa ortuzar": {
        "puntuacion": 68,
        "descripcion": "Servicios financieros básicos de barrio.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Corrientes",
            "Avenida Triunvirato"
        ],
        "sucursales_bancarias": [
            "Avenida Corrientes 5800"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "villa general mitre": {
        "puntuacion": 65,
        "descripcion": "Servicios financieros básicos.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Lincoln",
            "Avenida San Martín"
        ],
        "sucursales_bancarias": [
            "Avenida Lincoln 2800"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "villa santa rita": {
        "puntuacion": 60,
        "descripcion": "Servicios financieros limitados.",
        "bancos": [
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Rivadavia"
        ],
        "sucursales_bancarias": [
            "Avenida Rivadavia 7700"
        ],
        "otros_servicios": [
            "Puntos básicos"
        ]
    },
    "villa real": {
        "puntuacion": 58,
        "descripcion": "Servicios financieros básicos de barrio.",
        "bancos": [
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Juan B. Justo"
        ],
        "sucursales_bancarias": [
            "Avenida Juan B. Justo 7800"
        ],
        "otros_servicios": [
            "Puntos básicos"
        ]
    },
    "villa pueyrredon": {
        "puntuacion": 68,
        "descripcion": "Servicios financieros adecuados.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Dr. Ricardo Balbín"
        ],
        "sucursales_bancarias": [
            "Avenida Dr. Ricardo Balbín 4700"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "villa luro": {
        "puntuacion": 70,
        "descripcion": "Buenos servicios financieros de barrio.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Luro",
            "Avenida Rivadavia"
        ],
        "sucursales_bancarias": [
            "Avenida Luro 7000"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "parque avellaneda": {
        "puntuacion": 62,
        "descripcion": "Servicios financieros básicos.",
        "bancos": [
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Directorio"
        ],
        "sucursales_bancarias": [
            "Avenida Directorio 5000"
        ],
        "otros_servicios": [
            "Puntos básicos"
        ]
    },
    "parque chacabuco": {
        "puntuacion": 65,
        "descripcion": "Servicios financieros de barrio.",
        "bancos": [
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Directorio",
            "Avenida La Plata"
        ],
        "sucursales_bancarias": [
            "Avenida Directorio 4400"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "parque patricios": {
        "puntuacion": 65,
        "descripcion": "Servicios financieros en desarrollo.",
        "bancos": [
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Juan B. Justo"
        ],
        "sucursales_bancarias": [
            "Avenida Juan B. Justo 6000"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "nueva pompeya": {
        "puntuacion": 60,
        "descripcion": "Servicios financieros básicos.",
        "bancos": [
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Sáenz"
        ],
        "sucursales_bancarias": [
            "Avenida Sáenz 900"
        ],
        "otros_servicios": [
            "Puntos básicos"
        ]
    },
    "monte castro": {
        "puntuacion": 60,
        "descripcion": "Servicios financieros básicos.",
        "bancos": [
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Juan B. Justo",
            "Avenida Luro"
        ],
        "sucursales_bancarias": [
            "Avenida Juan B. Justo 9200"
        ],
        "otros_servicios": [
            "Puntos básicos"
        ]
    },
    "la paternal": {
        "puntuacion": 70,
        "descripcion": "Buenos servicios financieros cerca de Chacarita.",
        "bancos": [
            "Banco Ciudad",
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Corrientes",
            "Avenida San Martín"
        ],
        "sucursales_bancarias": [
            "Avenida Corrientes 5100"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "versailles": {
        "puntuacion": 60,
        "descripcion": "Servicios financieros limitados.",
        "bancos": [
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Rivadavia"
        ],
        "sucursales_bancarias": [
            "Avenida Rivadavia 7200"
        ],
        "otros_servicios": [
            "Puntos básicos"
        ]
    },
    "floresta": {
        "puntuacion": 65,
        "descripcion": "Servicios financieros de barrio.",
        "bancos": [
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Avellaneda",
            "Avenidaellan"
        ],
        "sucursales_bancarias": [
            "Avenida Avellaneda 4800"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "agronomia": {
        "puntuacion": 65,
        "descripcion": "Servicios financieros básicos cerca de facultades.",
        "bancos": [
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida San Martín",
            "Avenida Nazca"
        ],
        "sucursales_bancarias": [
            "Avenida San Martín 4700"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "colegiales": {
        "puntuacion": 75,
        "descripcion": "Buenos servicios financieros con bancos y cajeros.",
        "bancos": [
            "Banco Ciudad",
            "Banco Supervielle",
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Córdoba",
            "Avenida del Libertador"
        ],
        "sucursales_bancarias": [
            "Avenida Córdoba 5000",
            "Avenida del Libertador 6300"
        ],
        "otros_servicios": [
            "Puntos Rapipago",
            "PagoFácil"
        ]
    },
    "parque chas": {
        "puntuacion": 62,
        "descripcion": "Servicios financieros básicos de barrio.",
        "bancos": [
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida Dr. Tristán Achá"
        ],
        "sucursales_bancarias": [
            "Avenida Dr. Tristán Achá 2600"
        ],
        "otros_servicios": [
            "Puntos básicos"
        ]
    },
    "san cristobal": {
        "puntuacion": 70,
        "descripcion": "Buenos servicios financieros cerca de Boedo.",
        "bancos": [
            "Banco Macro"
        ],
        "cajeros_automaticos": [
            "Avenida San Juan",
            "Avenida Boedo"
        ],
        "sucursales_bancarias": [
            "Avenida San Juan 3000"
        ],
        "otros_servicios": [
            "Puntos de pago"
        ]
    },
    "san nicolas": {
        "puntuacion": 82,
        "descripcion": "Buenos servicios financieros en zona céntrica.",
        "bancos": [
            "Banco de la Nación Argentina",
            "Banco Ciudad",
            "Banco BBVA",
            "Banco Santander"
        ],
        "cajeros_automaticos": [
            "Avenida Corrientes",
            "Avenida 9 de Julio",
            "Avenida Córdoba"
        ],
        "sucursales_bancarias": [
            "Avenida Corrientes 1300",
            "Avenida Córdoba 800"
        ],
        "otros_servicios": [
            "Puntos Rapipago",
            "PagoFácil",
            "Casas de cambio"
        ]
    },
    "monserrat": {
        "puntuacion": 85,
        "descripcion": "Excelentes servicios financieros en zona histórica céntrica.",
        "bancos": [
            "Banco de la Nación Argentina",
            "Banco Ciudad",
            "Banco BBVA",
            "Banco Supervielle"
        ],
        "cajeros_automaticos": [
            "Plaza de Mayo",
            "Avenida de Mayo",
            "Avenida Julio Argentino Roca"
        ],
        "sucursales_bancarias": [
            "Avenida Julio Argentino Roca 1",
            "Avenida de Mayo 100"
        ],
        "otros_servicios": [
            "Casas de cambio",
            "Financieras"
        ]
    }
}

def get_gastronomy_info(zone: str) -> Dict[str, Any]:
    """Obtiene información de gastronomía para una zona específica"""
    zone_lower = zone.lower().strip()
    
    # Buscar coincidencia exacta
    if zone_lower in GASTRONOMY_DATA:
        return GASTRONOMY_DATA[zone_lower]
    
    # Buscar coincidencia parcial
    for key, value in GASTRONOMY_DATA.items():
        if key in zone_lower or zone_lower in key:
            return value
    
    # Retornar datos genéricos si no se encuentra
    return {
        "puntuacion": 60,
        "descripcion": "Información gastronómica no disponible para esta zona.",
        "restaurantes_destacados": [],
        "zonas_gastronomicas": [],
        "tipo_comida": [],
        "bares_notables": [],
        "cafes_especialidad": []
    }

def get_financial_info(zone: str) -> Dict[str, Any]:
    """Obtiene información de servicios financieros para una zona específica"""
    zone_lower = zone.lower().strip()
    
    # Buscar coincidencia exacta
    if zone_lower in FINANCIAL_DATA:
        return FINANCIAL_DATA[zone_lower]
    
    # Buscar coincidencia parcial
    for key, value in FINANCIAL_DATA.items():
        if key in zone_lower or zone_lower in key:
            return value
    
    # Retornar datos genéricos si no se encuentra
    return {
        "puntuacion": 50,
        "descripcion": "Información de servicios financieros no disponible para esta zona.",
        "bancos": [],
        "cajeros_automaticos": [],
        "sucursales_bancarias": [],
        "otros_servicios": []
    }

# ========================================
# DATOS ESPECÍFICOS POR UBICACIÓN (desde app.js)
# ========================================
# Estos datos incluyen información detallada con direcciones reales,
# servicios específicos y características particulares de cada barrio

LOCATION_SPECIFIC_DATA = {
    "pilar": {
        "transporte": "En {location} tienes acceso a la Autopista Acceso Norte Ramal Pilar y Ruta 8. Líneas de colectivo específicas: Línea 57, Línea 510 (Pilar Bus S.A.), Línea 176. Conexiones con Ruta Bus S.A. hacia Moreno, Areco, y Cardales.",
        "salud": "{location} cuenta con Hospital Universitario Austral (Juan Domingo Perón 1500, Derqui), Sanatorio del Pilar, Hospital Central de Emergencia y Alta Complejidad de Pilar, Centro Medico Pilares, y MAS Centro Médico (Moreno 565).",
        "comercio": "{location} tiene Las Palmas del Pilar (con Jumbo), Tortugas Open Mall (Panamericana Ramal Pilar Km 36,5), Paseo Pilar (Ruta Panamericana Km 44), Cardinal Shopping, y el supermercado Jumbo en Palmas del Pilar.",
        "servicios": "{location} cuenta con Farmacity, farmacias locales, centros de estética, servicios de lavandería, peluquerías, sucursales de bancos como Banco Santander y BBVA, y servicios profesionales completos.",
        "gastronomia": "{location} ofrece restaurantes variados, cafeterías especializadas, bares tradicionales, pizzerías locales, heladerías artesanales, y una plaza gastronómica en Cardinal Shopping.",
        "recreacion": "{location} tiene Las Palmas del Pilar, parques y plazas, canchas deportivas, centro cultural, bibliotecas, espacios familiares, y actividades al aire libre en la zona.",
        "servicios_financieros": "{location} cuenta con sucursales de Banco Santander, BBVA, Macro, cajeros automáticos en Las Palmas del Pilar y centros comerciales, casas de cambio, y servicios de seguros.",
        "educacion": "{location} tiene colegios privados como San Patricio, colegios públicos de calidad, cercanía a universidades (UBA), institutos técnicos, centros de idiomas, y academias especializadas."
    },
    "microcentro": {
        "transporte": "En {location} tienes acceso a las líneas de subte Línea D (conecta Palermo con el centro porteño) y Línea C (conecta Retiro y Constitución). Colectivos específicos: 105, 39, 59, 7, 8. Paradas estratégicas en el microcentro con acceso directo a todas las zonas de CABA.",
        "salud": "{location} cuenta con Hospital Italiano, Hospital Británico, centros de salud del Gobierno de la Ciudad, consultorios médicos especializados, Farmacity, y servicios de emergencia médica 24hs.",
        "comercio": "{location} tiene Galerías Pacífico, Florida Street (compras), Mercado San Telmo, centros comerciales, bancos principales, casas de cambio, y todas las cadenas comerciales importantes concentradas.",
        "servicios": "{location} cuenta con servicios completos: Farmacity, bancos principales (Banco Nación, Santander, BBVA), casas de cambio, servicios profesionales, centros de estética, lavanderías, y toda la infraestructura comercial del centro.",
        "gastronomia": "{location} ofrece la mayor concentración gastronómica de Buenos Aires: restaurantes premium, bares tradicionales, cafeterías históricas, pizzerías emblemáticas, y opciones desde comida rápida hasta fine dining.",
        "recreacion": "{location} tiene Plaza San Martín, Plaza de Mayo, Teatro Colón, Obelisco, museos (MAMBA, Fortabat), bibliotecas, y acceso directo a todos los espacios culturales de la ciudad.",
        "servicios_financieros": "{location} cuenta con la mayor concentración de servicios financieros: Banco Nación, Santander, BBVA, HSBC, casas de cambio (Cambios Alem, Miguel), seguros, y fintech.",
        "educacion": "{location} tiene acceso a universidades (UBA, UCA), colegios privados prestigiosos, institutos técnicos, centros de idiomas, academias, y toda la oferta educativa de CABA."
    },
    "boedo": {
        "transporte": "En {location} tienes conectividad con 31 líneas de colectivos de CABA (modernizadas en 2025 con color azul). Conexión directa con líneas de subte A, B, D, E, H. Paradas estratégicas y acceso rápido a todas las zonas de la ciudad.",
        "salud": "{location} cuenta con Hospital Durand, centros de salud comunitarios, consultorios médicos, Farmacity, centros de diagnóstico, y servicios de salud públicos y privados.",
        "comercio": "{location} tiene supermercados (Disco, Vea), centros comerciales, tiendas de barrio, librerías, jugueterías, y comercio local completo con acceso a centros comerciales mayores.",
        "servicios": "{location} cuenta con Farmacity, bancos locales, centros de estética, lavanderías, tintorerías, peluquerías, servicios profesionales, y toda la infraestructura de servicios.",
        "gastronomia": "{location} ofrece restaurantes variados, bares tradicionales, pizzerías familiares, cafeterías de barrio, heladerías artesanales, y opciones gastronómicas diversas.",
        "recreacion": "{location} tiene plazas del barrio, canchas deportivas, bibliotecas, centro cultural, espacios familiares, y acceso a parques y espacios verdes cercanos.",
        "servicios_financieros": "{location} cuenta con sucursales de bancos principales, cajeros automáticos en ubicaciones estratégicas, casas de cambio, servicios de seguros, y fintech.",
        "educacion": "{location} tiene colegios públicos y privados, institutos técnicos, cercanía a universidades, centros de idiomas, academias, y acceso a la oferta educativa de CABA."
    },
    "parque avellaneda": {
        "transporte": "En {location} tienes acceso a colectivos específicos: 114, 126, 180, 4, 55, 86, 50, 7. Tren SARMIENTO con estaciones cercanas. Conexión con líneas de subte A y E. Excelente conectividad con el resto de la ciudad.",
        "salud": "{location} cuenta con Centro de Salud Nivel 1 - CeSAC Nº 13 (Dirección 4210), nuevo CeSAC 15 (desde setiembre 2025), centros de salud comunitarios, consultorios médicos, y Farmacity.",
        "comercio": "{location} tiene supermercados locales, centros comerciales cercanos, tiendas de barrio, librerías, jugueterías, y acceso a centros comerciales mayores en zonas adyacentes.",
        "servicios": "{location} cuenta con Farmacity, bancos locales, centros de estética, lavanderías, tintorerías, peluquerías, servicios profesionales, y toda la infraestructura de servicios del barrio.",
        "gastronomia": "{location} ofrece restaurantes familiares, bares tradicionales, pizzerías locales, cafeterías de barrio, heladerías artesanales, y opciones gastronómicas de la zona.",
        "recreacion": "{location} tiene el propio Parque Avellaneda, canchas deportivas, espacios verdes, centro cultural, bibliotecas, actividades familiares, y espacios para recreación al aire libre.",
        "servicios_financieros": "{location} cuenta con sucursales de bancos locales, cajeros automáticos en el barrio, casas de cambio cercanas, servicios de seguros, y fintech.",
        "educacion": "{location} tiene colegios públicos y privados del barrio, institutos técnicos, centros de idiomas, academias, y acceso a la oferta educativa de CABA."
    }
}


def get_location_specific_info(zone: str) -> Dict[str, Any]:
    """
    Obtiene información específica detallada para una zona.
    Esta función retorna datos con direcciones reales, servicios específicos,
    y características particulares del barrio.
    """
    zone_lower = zone.lower().strip()
    
    # Buscar coincidencia exacta
    if zone_lower in LOCATION_SPECIFIC_DATA:
        return LOCATION_SPECIFIC_DATA[zone_lower]
    
    # Buscar coincidencia parcial
    for key, value in LOCATION_SPECIFIC_DATA.items():
        if key in zone_lower or zone_lower in key:
            return value
    
    # Retornar datos genéricos usando el template default
    return {
        "transporte": "En {location} tienes conectividad con líneas de colectivo locales, acceso a subte según la línea disponible, paradas de taxi estratégicas, y acceso a autopistas principales.",
        "salud": "{location} cuenta con hospitales públicos y privados, consultorios médicos especializados, centros de diagnóstico, farmacias 24hs, y servicios de emergencia.",
        "comercio": "{location} tiene supermercados de cadenas reconocidas, centros comerciales, tiendas especializadas, librerías, jugueterías, y servicios básicos.",
        "servicios": "{location} cuenta con farmacias, centros de estética, lavanderías, tintorerías, peluquerías, sucursales bancarias, y servicios profesionales.",
        "gastronomia": "{location} ofrece restaurantes variados, cafeterías especializadas, bares tradicionales, pizzerías, heladerías artesanales, y opciones gastronómicas diversas.",
        "recreacion": "{location} tiene plazas y parques, canchas deportivas, centros culturales, bibliotecas, teatros, museos, y espacios familiares.",
        "servicios_financieros": "{location} cuenta con sucursales de bancos principales, cajeros automáticos, casas de cambio, servicios de seguros, y fintech.",
        "educacion": "{location} tiene colegios primarios y secundarios, universidades cercanas, institutos técnicos, centros de idiomas, y academias."
    }
