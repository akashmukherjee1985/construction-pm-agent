# app/database/models.py

from sqlalchemy import (
    Column,        # defines a column in a table
    Integer,       # integer data type
    String,        # variable length string
    Float,         # decimal number
    Date,          # date without time
    DateTime,      # date with time
    Enum,          # restricted set of string values
    ForeignKey,    # links one table to another
    Text,          # long text (no length limit)
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum

# Base is the parent class all our models inherit from
# SQLAlchemy uses it to track all table definitions
# Think of it as the registry of all tables in our database
Base = declarative_base()


# ── Python Enums for restricted value columns ─────────────────────
# Enums ensure only valid values go into these columns
# The database enforces this constraint automatically

class SiteStatus(str, enum.Enum):
    """Possible statuses for a construction site"""
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    PLANNING = "planning"


class WorkerRole(str, enum.Enum):
    """Job roles for workers on site"""
    ENGINEER = "engineer"
    FOREMAN = "foreman"
    LABOURER = "labourer"
    ELECTRICIAN = "electrician"
    PLUMBER = "plumber"
    WELDER = "welder"
    SUPERVISOR = "supervisor"
    SAFETY_OFFICER = "safety_officer"


class WorkerType(str, enum.Enum):
    """Whether worker is directly employed or through contractor"""
    DIRECT = "direct"
    CONTRACTOR = "contractor"


class EquipmentStatus(str, enum.Enum):
    """Current operational status of equipment"""
    OPERATIONAL = "operational"
    UNDER_MAINTENANCE = "under_maintenance"
    BREAKDOWN = "breakdown"
    IDLE = "idle"


class MaterialUnit(str, enum.Enum):
    """Units of measurement for materials"""
    TONNES = "tonnes"
    CUBIC_METRES = "cubic_metres"
    PIECES = "pieces"
    LITRES = "litres"
    METRES = "metres"


class IncidentSeverity(str, enum.Enum):
    """Safety incident severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, enum.Enum):
    """Resolution status of a safety incident"""
    OPEN = "open"
    UNDER_INVESTIGATION = "under_investigation"
    RESOLVED = "resolved"


# ── Table 1: Sites ────────────────────────────────────────────────
class Site(Base):
    """
    Master table of all construction sites.
    Every other table references this via site_name.
    
    In a real system this would use site_id as foreign key,
    but we use site_name for readability in SQL query results
    that the LLM will interpret.
    """
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # primary_key=True → this column uniquely identifies each row
    # autoincrement=True → database assigns the next number automatically

    site_name = Column(String(100), unique=True, nullable=False)
    # unique=True → no two sites can have the same name
    # nullable=False → this column cannot be empty

    location = Column(String(200), nullable=False)
    project_type = Column(String(100), nullable=False)
    # e.g. "Residential Tower", "Highway", "Industrial Plant"

    status = Column(String(20), default=SiteStatus.ACTIVE.value)
    # We store the string value of the enum, not the enum itself
    # default= means if no value given, use this

    start_date = Column(Date, nullable=False)
    expected_end_date = Column(Date, nullable=False)
    actual_end_date = Column(Date, nullable=True)
    # nullable=True → this can be empty (site not finished yet)

    total_budget = Column(Float, nullable=False)
    # Budget in USD
    spent_budget = Column(Float, default=0.0)

    project_manager = Column(String(100), nullable=False)
    client_name = Column(String(100), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    # default=datetime.utcnow → automatically set to current time
    # Note: we pass the function, not the result — utcnow not utcnow()
    # SQLAlchemy calls it at insert time, not at class definition time


# ── Table 2: Workmen ──────────────────────────────────────────────
class Workman(Base):
    """
    Individual workers assigned to construction sites.
    Tracks attendance, role, contractor, and daily wage.
    """
    __tablename__ = "workmen"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)

    site_name = Column(
        String(100),
        ForeignKey("sites.site_name"),
        nullable=False
    )
    # ForeignKey("sites.site_name") → this column must contain a value
    # that exists in the site_name column of the sites table
    # This enforces referential integrity — you cannot add a worker
    # to a site that doesn't exist

    role = Column(String(50), nullable=False)
    worker_type = Column(String(20), default=WorkerType.DIRECT.value)
    contractor_company = Column(String(100), nullable=True)
    # Only filled if worker_type = "contractor"

    daily_wage = Column(Float, nullable=False)
    # In USD

    attendance_status = Column(String(20), default="present")
    # present / absent / on_leave

    joining_date = Column(Date, nullable=False)
    nationality = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# ── Table 3: Equipment Inventory ──────────────────────────────────
class Equipment(Base):
    """
    All machinery and tools across construction sites.
    Tracks utilisation, maintenance schedules, and operational status.
    """
    __tablename__ = "equipment_inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_name = Column(String(100), nullable=False)
    # e.g. "Tower Crane", "Excavator", "Concrete Mixer"

    equipment_type = Column(String(50), nullable=False)
    # e.g. "Heavy Machinery", "Vehicle", "Tool"

    site_name = Column(
        String(100),
        ForeignKey("sites.site_name"),
        nullable=False
    )

    status = Column(String(30), default=EquipmentStatus.OPERATIONAL.value)

    utilisation_percent = Column(Float, default=0.0)
    # 0.0 to 100.0 — how much of working hours it was in use

    last_maintenance_date = Column(Date, nullable=True)
    next_maintenance_date = Column(Date, nullable=True)

    purchase_cost = Column(Float, nullable=True)
    daily_rental_cost = Column(Float, nullable=True)
    # Either purchased or rented — one of these will be filled

    operator_name = Column(String(100), nullable=True)
    # The worker responsible for this equipment

    created_at = Column(DateTime, default=datetime.utcnow)


# ── Table 4: Materials ────────────────────────────────────────────
class Material(Base):
    """
    Material inventory and consumption tracking per site.
    Tracks stock levels, supplier info, and costs.
    """
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_name = Column(String(100), nullable=False)
    # e.g. "Cement", "Steel Rebar", "Aggregate", "Timber"

    material_type = Column(String(50), nullable=False)
    # e.g. "Structural", "Finishing", "Electrical", "Plumbing"

    site_name = Column(
        String(100),
        ForeignKey("sites.site_name"),
        nullable=False
    )

    unit = Column(String(20), nullable=False)
    # Uses MaterialUnit enum values

    quantity_in_stock = Column(Float, default=0.0)
    quantity_consumed = Column(Float, default=0.0)
    minimum_stock_level = Column(Float, default=0.0)
    # If quantity_in_stock drops below this, it flags low stock

    unit_cost = Column(Float, nullable=False)
    # Cost per unit in USD

    supplier_name = Column(String(100), nullable=True)
    last_restock_date = Column(Date, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# ── Table 5: Incidents ────────────────────────────────────────────
class Incident(Base):
    """
    Safety incidents and near-misses across all sites.
    Critical for safety compliance tracking and reporting.
    """
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)

    site_name = Column(
        String(100),
        ForeignKey("sites.site_name"),
        nullable=False
    )

    incident_date = Column(Date, nullable=False)
    incident_type = Column(String(100), nullable=False)
    # e.g. "Fall from height", "Equipment failure", "Near miss"

    severity = Column(String(20), nullable=False)
    # Uses IncidentSeverity enum values

    description = Column(Text, nullable=False)
    # Full description — Text type has no length limit

    injured_person = Column(String(100), nullable=True)
    # Name of injured worker if applicable

    reported_by = Column(String(100), nullable=False)
    status = Column(String(30), default=IncidentStatus.OPEN.value)

    resolution_notes = Column(Text, nullable=True)
    resolved_date = Column(Date, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)