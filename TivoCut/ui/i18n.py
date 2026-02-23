def prix_mode_to_fr(mode: str) -> str:
    if mode == "PER_SHEET":
        return "Par panneau"
    if mode == "PER_M2":
        return "Par m²"
    return "" if mode is None else str(mode)


def prix_mode_from_fr(label: str) -> str:
    if label == "Par panneau":
        return "PER_SHEET"
    if label == "Par m²":
        return "PER_M2"
    return label


def grain_rule_to_fr(rule: str) -> str:
    if rule == "NONE":
        return "Sans"
    if rule == "OPTIONAL":
        return "Optionnelle"
    if rule == "REQUIRED":
        return "Obligatoire"
    return "" if rule is None else str(rule)


def grain_rule_from_fr(label: str) -> str:
    if label == "Sans":
        return "NONE"
    if label == "Optionnelle":
        return "OPTIONAL"
    if label == "Obligatoire":
        return "REQUIRED"
    return label
    
def grain_constraint_from_fr(label: str) -> str:
    if label == "Sans":
        return "NONE"
    if label == "Vertical":
        return "VERTICAL"
    if label == "Horizontal":
        return "HORIZONTAL"
    return "NONE"


def grain_constraint_to_fr(code: str) -> str:
    if code == "NONE":
        return "Sans"
    if code == "VERTICAL":
        return "Vertical"
    if code == "HORIZONTAL":
        return "Horizontal"
    return "Sans"