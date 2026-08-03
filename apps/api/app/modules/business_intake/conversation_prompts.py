from __future__ import annotations

START_BUTTON_TEXTS = {"/start", "/start negocio", "comenzar registro", "iniciar registro", "registrar negocio"}

START_REPLY_MARKUP = {
    "keyboard": [[{"text": "Comenzar registro"}]],
    "resize_keyboard": True,
    "one_time_keyboard": False,
    "input_field_placeholder": "Escribe tu codigo de referencia",
}

REMOVE_REPLY_MARKUP = {"remove_keyboard": True}

STEP_PROMPTS = {
    "awaiting_referral_code": (
        "Bienvenido a NODO Registro Negocios.\n\n"
        "Para comenzar, escribe tu codigo de referencia."
    ),
    "awaiting_whatsapp_phone": "Ahora escribe tu numero de WhatsApp para poder contactarte sobre la solicitud.",
    "awaiting_contact": "Escribe tu numero de WhatsApp para poder contactarte sobre la solicitud.",
    "awaiting_business_name": "Escribe el nombre comercial del negocio.",
    "awaiting_business_tax_id": "Escribe el RIF o numero de registro del negocio.",
    "awaiting_responsible_name": "Escribe el nombre de la persona responsable.",
    "awaiting_responsible_id_number": "Escribe la cedula o documento de identidad del responsable.",
    "awaiting_city": "Indica la ciudad donde opera el negocio.",
    "awaiting_business_phone": "Escribe el telefono operativo del negocio.",
    "awaiting_operation": "Indica si el negocio compra USD, vende USD o ambas.",
    "awaiting_banks": "Indica los bancos con los que trabajas, separados por coma.",
    "awaiting_methods": "Indica los metodos disponibles: Zelle, USDT o ambos. NODO asigna de inicio 20 a 100 USD por operacion y 1000 USD diarios.",
    "awaiting_min_amount": "NODO asigna automaticamente el rango inicial: 20 a 100 USD por operacion y 1000 USD diarios. Ahora comparte tus redes sociales obligatorias.",
    "awaiting_max_amount": "NODO asigna automaticamente el rango inicial: 20 a 100 USD por operacion y 1000 USD diarios. Ahora comparte tus redes sociales obligatorias.",
    "awaiting_schedule": "No necesitamos horario; el negocio decide cuando operar con el boton online/offline. Comparte tus redes sociales obligatorias.",
    "awaiting_references": "Redes sociales obligatorias: comparte Instagram, TikTok, Google Maps, web o referencias publicas del negocio. No escribas 'no'.",
    "awaiting_documents": "Puedes adjuntar cedula/pasaporte, RIF, foto del local o referencias. Aceptamos imagenes y PDF de hasta 5 MB. Cuando termines, envia 'finalizar'.",
}
