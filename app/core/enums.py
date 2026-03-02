import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class SubscriptionTier(str, enum.Enum):
    free = "free"
    premium = "premium"


class QuantityLevel(str, enum.Enum):
    full = "full"
    half = "half"
    low = "low"


class RecipeSource(str, enum.Enum):
    generated = "generated"
    imported = "imported"
    manual = "manual"


class RecipeDifficulty(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class ScanType(str, enum.Enum):
    packaged = "packaged"
    fresh = "fresh"


class ScanStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"

class UnitType(str, enum.Enum):
    WEIGHT = "WEIGHT"
    VOLUME = "VOLUME"
    COUNT = "COUNT"
