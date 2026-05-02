import enum


class JobStatus(str, enum.Enum):
    DRAFT = 'draft'
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'


class FileStatus(str, enum.Enum):
    QUEUED = 'queued'
    PROCESSING = 'processing'
    DONE = 'done'
    FAILED = 'failed'


class FileType(str, enum.Enum):
    TEXT = 'text'
    IMAGE = 'image'
    AUDIO = 'audio'


class TransactionType(str, enum.Enum):
    TOPUP = 'topup'
    PROMO_CREDIT = 'promo_credit'
    HOLD = 'hold'
    CHARGE = 'charge'
    REFUND = 'refund'


class PromoCodeType(str, enum.Enum):
    FIXED = 'fixed'
    PERCENTAGE = 'percentage'
