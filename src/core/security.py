"""
Utilitários de segurança.
"""

import re
from typing import Any


def mask_cpf(cpf: str | None) -> str:
    """
    Mascara CPF para logs (LGPD compliance).
    
    Exemplo: 12345678900 -> 123.***.***-00
    """
    if not cpf:
        return "N/A"
    
    cpf = re.sub(r"[^\d]", "", cpf)
    
    if len(cpf) != 11:
        return "***INVALID***"
    
    return f"{cpf[:3]}.***.***-{cpf[-2:]}"


def mask_cnpj(cnpj: str | None) -> str:
    """
    Mascara CNPJ para logs.
    
    Exemplo: 12345678000190 -> 12.***.***/**90
    """
    if not cnpj:
        return "N/A"
    
    cnpj = re.sub(r"[^\d]", "", cnpj)
    
    if len(cnpj) != 14:
        return "***INVALID***"
    
    return f"{cnpj[:2]}.***.***/**{cnpj[-2:]}"


def mask_token(token: str | None, visible_chars: int = 8) -> str:
    """
    Mascara tokens para logs.
    
    Exemplo: eyJhbGciOi... -> eyJhbGci...***
    """
    if not token:
        return "N/A"
    
    if len(token) <= visible_chars:
        return "***"
    
    return f"{token[:visible_chars]}...***"


def sanitize_log_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitiza dicionário para logging seguro.
    Remove/mascara dados sensíveis.
    """
    sensitive_keys = {
        "cpf", "cnpj", "password", "senha", "token", 
        "api_key", "secret", "authorization", "cookie"
    }
    
    sanitized = {}
    
    for key, value in data.items():
        key_lower = key.lower()
        
        # Verifica se é chave sensível
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            if "cpf" in key_lower:
                sanitized[f"{key}_masked"] = mask_cpf(str(value))
            elif "cnpj" in key_lower:
                sanitized[f"{key}_masked"] = mask_cnpj(str(value))
            elif "token" in key_lower or "authorization" in key_lower:
                sanitized[f"{key}_masked"] = mask_token(str(value))
            else:
                sanitized[f"{key}_masked"] = "***REDACTED***"
        else:
            sanitized[key] = value
    
    return sanitized
