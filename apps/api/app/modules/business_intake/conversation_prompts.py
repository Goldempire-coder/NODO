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
    "awaiting_responsible_name": "Escribe el nombre de la persona responsable.",
    "awaiting_city": "Indica la ciudad donde opera el negocio.",
    "awaiting_business_phone": "Escribe el telefono operativo del negocio.",
    "awaiting_operation": "Indica si el negocio compra USD, vende USD o ambas.",
    "awaiting_banks": "Indica los bancos con los que trabajas, separados por coma.",
    "awaiting_methods": "Indica los metodos disponibles: Zelle, USDT TRC20 o ambos.",
    "awaiting_min_amount": "Indica el monto minimo aproximado en USD.",
    "awaiting_max_amount": "Indica el monto maximo aproximado en USD.",
    "awaiting_schedule": "Indica tu horario habitual de atencion.",
    "awaiting_references": "Comparte redes sociales, referencias o informacion adicional que ayude a revisar el negocio.",
    "awaiting_documents": "Puedes adjuntar cedula/pasaporte, RIF, foto del local o referencias. Aceptamos imagenes y PDF de hasta 5 MB. Cuando termines, envia 'finalizar'.",
}
