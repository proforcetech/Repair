from enum import Enum


class Role(str, Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    TECHNICIAN = "TECHNICIAN"
    ACCOUNTANT = "ACCOUNTANT"
    FRONT_DESK = "FRONT_DESK"


class InvoiceStatus(str, Enum):
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ON_HOLD = "ON_HOLD"


class OrderStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class AppointmentStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class POStatus(str, Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    RECEIVED = "RECEIVED"


class ClaimStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_MORE_INFO = "NEEDS_MORE_INFO"


class EstimateStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_CUSTOMER_APPROVAL = "PENDING_CUSTOMER_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RecurrenceType(str, Enum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"
