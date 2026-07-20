# app/database/seed.py

from datetime import date, datetime, timedelta
import random
from sqlalchemy.orm import Session
from app.database.models import (
    Site, Workman, Equipment, Material, Incident,
    SiteStatus, WorkerRole, WorkerType,
    EquipmentStatus, MaterialUnit, IncidentSeverity, IncidentStatus
)
from app.database.connection import SessionLocal, init_db
import logging

logger = logging.getLogger(__name__)

# ── Seed Data Definitions ─────────────────────────────────────────
# These are the realistic values we draw from when generating data

SITES = [
    {
        "site_name": "Alpha Tower",
        "location": "Dubai Marina, Dubai",
        "project_type": "Residential Tower",
        "status": SiteStatus.ACTIVE.value,
        "start_date": date(2024, 1, 15),
        "expected_end_date": date(2026, 6, 30),
        "total_budget": 45000000.0,
        "spent_budget": 28000000.0,
        "project_manager": "Rajesh Kumar",
        "client_name": "Emirates Properties LLC"
    },
    {
        "site_name": "Beta Highway",
        "location": "Abu Dhabi-Dubai Highway, Sharjah",
        "project_type": "Highway Construction",
        "status": SiteStatus.ACTIVE.value,
        "start_date": date(2023, 8, 1),
        "expected_end_date": date(2025, 12, 31),
        "total_budget": 120000000.0,
        "spent_budget": 95000000.0,
        "project_manager": "Mohammed Al Rashid",
        "client_name": "Roads and Transport Authority"
    },
    {
        "site_name": "Gamma Industrial",
        "location": "KIZAD, Abu Dhabi",
        "project_type": "Industrial Plant",
        "status": SiteStatus.ACTIVE.value,
        "start_date": date(2024, 3, 1),
        "expected_end_date": date(2027, 3, 1),
        "total_budget": 200000000.0,
        "spent_budget": 45000000.0,
        "project_manager": "Sarah Thompson",
        "client_name": "ADNOC Engineering"
    },
    {
        "site_name": "Delta Mall",
        "location": "Yas Island, Abu Dhabi",
        "project_type": "Commercial Complex",
        "status": SiteStatus.ON_HOLD.value,
        "start_date": date(2023, 5, 1),
        "expected_end_date": date(2026, 5, 1),
        "total_budget": 80000000.0,
        "spent_budget": 32000000.0,
        "project_manager": "Priya Nair",
        "client_name": "Aldar Properties"
    },
    {
        "site_name": "Epsilon Bridge",
        "location": "Creek Harbour, Dubai",
        "project_type": "Infrastructure",
        "status": SiteStatus.ACTIVE.value,
        "start_date": date(2024, 6, 1),
        "expected_end_date": date(2026, 12, 31),
        "total_budget": 65000000.0,
        "spent_budget": 12000000.0,
        "project_manager": "Ahmed Hassan",
        "client_name": "Dubai Municipality"
    }
]

WORKER_NAMES = [
    "Ravi Shankar", "Mohammed Al Ali", "John Mathew", "Suresh Babu",
    "Khalid Al Mansouri", "David Okafor", "Arun Prakash", "Omar Farooq",
    "Vijay Kumar", "Hassan Al Zaabi", "Peter Nkosi", "Ramesh Pillai",
    "Abdullah Al Hashmi", "Michael Osei", "Santhosh Kumar", "Tariq Al Ameri",
    "Ganesh Rao", "Faisal Al Nuaimi", "James Mwangi", "Deepak Nair",
    "Yusuf Al Kaabi", "Samuel Otieno", "Manoj Tiwari", "Ali Al Marzouqi",
    "Robert Mensah", "Anand Krishnan", "Hamad Al Suwaidi", "Felix Okonkwo"
]

CONTRACTOR_COMPANIES = [
    "Gulf Tech Contractors", "Al Futtaim Engineering",
    "Shapoorji Pallonji UAE", "Drake & Scull",
    "Arabtec Construction", "BESIX Group"
]

NATIONALITIES = [
    "Indian", "Pakistani", "Filipino", "Egyptian",
    "Bangladeshi", "Nepali", "Emirati", "British"
]

EQUIPMENT_LIST = [
    ("Tower Crane TC-1", "Heavy Machinery"),
    ("Tower Crane TC-2", "Heavy Machinery"),
    ("Excavator EX-200", "Heavy Machinery"),
    ("Concrete Mixer CM-1", "Heavy Machinery"),
    ("Concrete Pump CP-1", "Heavy Machinery"),
    ("Bulldozer BD-1", "Heavy Machinery"),
    ("Forklift FL-1", "Vehicle"),
    ("Dump Truck DT-1", "Vehicle"),
    ("Dump Truck DT-2", "Vehicle"),
    ("Generator GN-1", "Electrical"),
    ("Compressor CP-2", "Tool"),
    ("Scaffolding Set SS-1", "Tool"),
]

MATERIALS_LIST = [
    ("Cement OPC 53", "Structural", "tonnes"),
    ("Steel Rebar TMT", "Structural", "tonnes"),
    ("Aggregate 20mm", "Structural", "cubic_metres"),
    ("River Sand", "Structural", "cubic_metres"),
    ("Ready Mix Concrete", "Structural", "cubic_metres"),
    ("Timber Planks", "Finishing", "pieces"),
    ("Electrical Cables", "Electrical", "metres"),
    ("PVC Pipes 4 inch", "Plumbing", "metres"),
    ("Waterproofing Membrane", "Finishing", "cubic_metres"),
    ("Ceramic Tiles", "Finishing", "pieces"),
]

INCIDENT_TYPES = [
    "Fall from height", "Equipment failure", "Near miss",
    "Material handling injury", "Electrical hazard",
    "Slip and trip", "Heat exhaustion", "Chemical exposure"
]


def seed_sites(db: Session) -> None:
    """Insert all construction sites into the database."""
    logger.info("Seeding sites...")
    for site_data in SITES:
        # Check if site already exists — avoid duplicate seeding
        exists = db.query(Site).filter(
            Site.site_name == site_data["site_name"]
        ).first()

        if not exists:
            site = Site(**site_data)
            # **site_data unpacks the dictionary as keyword arguments
            # Site(site_name="Alpha Tower", location="Dubai Marina", ...)
            db.add(site)

    db.commit()
    logger.info(f"Seeded {len(SITES)} sites.")


def seed_workmen(db: Session) -> None:
    """Insert realistic workers for each site."""
    logger.info("Seeding workmen...")

    # How many workers per site — realistic for construction
    workers_per_site = {
        "Alpha Tower": 45,
        "Beta Highway": 80,
        "Gamma Industrial": 60,
        "Delta Mall": 20,
        "Epsilon Bridge": 35,
    }

    roles = [role.value for role in WorkerRole]
    attendance_options = ["present", "present", "present", "absent", "on_leave"]
    # present appears 3 times → 60% probability of present
    # This makes attendance data realistic

    for site_name, count in workers_per_site.items():
        existing = db.query(Workman).filter(
            Workman.site_name == site_name
        ).count()

        if existing == 0:
            for i in range(count):
                worker_type = random.choice(
                    [WorkerType.DIRECT.value, WorkerType.DIRECT.value,
                     WorkerType.CONTRACTOR.value]
                )
                # DIRECT appears twice → 66% direct, 33% contractor

                workman = Workman(
                    name=random.choice(WORKER_NAMES),
                    site_name=site_name,
                    role=random.choice(roles),
                    worker_type=worker_type,
                    contractor_company=(
                        random.choice(CONTRACTOR_COMPANIES)
                        if worker_type == WorkerType.CONTRACTOR.value
                        else None
                        # conditional expression: value_if_true if condition else value_if_false
                    ),
                    daily_wage=random.uniform(80, 350),
                    # random.uniform() → random float between two values
                    attendance_status=random.choice(attendance_options),
                    joining_date=date(2023, 1, 1) + timedelta(
                        days=random.randint(0, 365)
                    ),
                    nationality=random.choice(NATIONALITIES),
                )
                db.add(workman)

    db.commit()
    logger.info("Workmen seeded.")


def seed_equipment(db: Session) -> None:
    """Insert equipment records for each site."""
    logger.info("Seeding equipment...")

    statuses = [
        EquipmentStatus.OPERATIONAL.value,
        EquipmentStatus.OPERATIONAL.value,
        EquipmentStatus.OPERATIONAL.value,
        EquipmentStatus.UNDER_MAINTENANCE.value,
        EquipmentStatus.IDLE.value,
    ]

    for site_data in SITES:
        site_name = site_data["site_name"]
        existing = db.query(Equipment).filter(
            Equipment.site_name == site_name
        ).count()

        if existing == 0:
            # Give each site a random subset of equipment
            site_equipment = random.sample(
                EQUIPMENT_LIST,
                k=random.randint(4, 8)
                # random.sample() picks k unique items from a list
            )

            for equip_name, equip_type in site_equipment:
                status = random.choice(statuses)
                equipment = Equipment(
                    equipment_name=equip_name,
                    equipment_type=equip_type,
                    site_name=site_name,
                    status=status,
                    utilisation_percent=round(
                        random.uniform(20, 95), 1
                    ),
                    last_maintenance_date=date(2024, 1, 1) + timedelta(
                        days=random.randint(0, 200)
                    ),
                    next_maintenance_date=date(2024, 8, 1) + timedelta(
                        days=random.randint(0, 180)
                    ),
                    purchase_cost=random.choice([
                        round(random.uniform(50000, 500000), 2),
                        None
                    ]),
                    daily_rental_cost=round(random.uniform(200, 2000), 2),
                    operator_name=random.choice(WORKER_NAMES),
                )
                db.add(equipment)

    db.commit()
    logger.info("Equipment seeded.")


def seed_materials(db: Session) -> None:
    """Insert material inventory for each site."""
    logger.info("Seeding materials...")

    for site_data in SITES:
        site_name = site_data["site_name"]
        existing = db.query(Material).filter(
            Material.site_name == site_name
        ).count()

        if existing == 0:
            for mat_name, mat_type, unit in MATERIALS_LIST:
                stock = round(random.uniform(10, 500), 2)
                minimum = round(random.uniform(20, 100), 2)

                material = Material(
                    material_name=mat_name,
                    material_type=mat_type,
                    site_name=site_name,
                    unit=unit,
                    quantity_in_stock=stock,
                    quantity_consumed=round(random.uniform(50, 800), 2),
                    minimum_stock_level=minimum,
                    unit_cost=round(random.uniform(5, 500), 2),
                    supplier_name=random.choice([
                        "Al Ghurair Cement", "Emirates Steel",
                        "Aggregate Industries", "RAK Ceramics",
                        "Gulf Cables", "National Pipes"
                    ]),
                    last_restock_date=date(2024, 1, 1) + timedelta(
                        days=random.randint(0, 200)
                    ),
                )
                db.add(material)

    db.commit()
    logger.info("Materials seeded.")


def seed_incidents(db: Session) -> None:
    """Insert safety incident records across sites."""
    logger.info("Seeding incidents...")

    severities = [
        IncidentSeverity.LOW.value,
        IncidentSeverity.LOW.value,
        IncidentSeverity.MEDIUM.value,
        IncidentSeverity.HIGH.value,
        IncidentSeverity.CRITICAL.value,
    ]

    statuses = [
        IncidentStatus.RESOLVED.value,
        IncidentStatus.RESOLVED.value,
        IncidentStatus.UNDER_INVESTIGATION.value,
        IncidentStatus.OPEN.value,
    ]

    incidents_per_site = {
        "Alpha Tower": 8,
        "Beta Highway": 15,
        "Gamma Industrial": 6,
        "Delta Mall": 3,
        "Epsilon Bridge": 5,
    }

    for site_name, count in incidents_per_site.items():
        existing = db.query(Incident).filter(
            Incident.site_name == site_name
        ).count()

        if existing == 0:
            for _ in range(count):
                # _ is used as variable name when you don't need
                # the loop variable — conventional Python idiom
                severity = random.choice(severities)
                status = random.choice(statuses)
                incident_date = date(2024, 1, 1) + timedelta(
                    days=random.randint(0, 300)
                )

                incident = Incident(
                    site_name=site_name,
                    incident_date=incident_date,
                    incident_type=random.choice(INCIDENT_TYPES),
                    severity=severity,
                    description=(
                        f"Incident reported at {site_name}. "
                        f"Type: {random.choice(INCIDENT_TYPES)}. "
                        f"Immediate action was taken by site supervisor."
                    ),
                    injured_person=(
                        random.choice(WORKER_NAMES)
                        if severity in [
                            IncidentSeverity.HIGH.value,
                            IncidentSeverity.CRITICAL.value
                        ]
                        else None
                    ),
                    reported_by=random.choice(WORKER_NAMES),
                    status=status,
                    resolution_notes=(
                        "Issue resolved after inspection and corrective measures."
                        if status == IncidentStatus.RESOLVED.value
                        else None
                    ),
                    resolved_date=(
                        incident_date + timedelta(days=random.randint(1, 30))
                        if status == IncidentStatus.RESOLVED.value
                        else None
                    ),
                )
                db.add(incident)

    db.commit()
    logger.info("Incidents seeded.")


def run_seed():
    """
    Main function that runs the full seeding process.
    Creates all tables first, then populates them in order.
    
    Order matters because of foreign keys:
    Sites must exist before Workmen, Equipment, Materials, Incidents
    can reference them.
    """
    logger.info("Starting database seed...")

    # Create tables
    init_db()

    # Open a session and seed all tables
    db = SessionLocal()
    try:
        seed_sites(db)
        seed_workmen(db)
        seed_equipment(db)
        seed_materials(db)
        seed_incidents(db)
        logger.info("Database seeding complete.")
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # This block only runs when you execute this file directly:
    # python app/database/seed.py
    #
    # It does NOT run when this file is imported by another module
    # This is a standard Python pattern for runnable modules
    import logging
    logging.basicConfig(level=logging.INFO)
    run_seed()