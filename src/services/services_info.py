def get_service_info(service_name):
    services = {
        "service_1": {
            "description": "Descripción del servicio 1",
            "price": "$100"
        },
        "service_2": {
            "description": "Descripción del servicio 2",
            "price": "$200"
        },
        "service_3": {
            "description": "Descripción del servicio 3",
            "price": "$300"
        },
        "service_4": {
            "description": "Descripción del servicio 4",
            "price": "$400"
        },
        "service_5": {
            "description": "Descripción del servicio 5",
            "price": "$500"
        }
    }
    
    return services.get(service_name, "Servicio no encontrado")

def list_services():
    return {
        "service_1": "Descripción del servicio 1",
        "service_2": "Descripción del servicio 2",
        "service_3": "Descripción del servicio 3",
        "service_4": "Descripción del servicio 4",
        "service_5": "Descripción del servicio 5"
    }