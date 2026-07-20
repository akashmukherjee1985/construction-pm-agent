# app/dashboard/metadata.py
#
# Dashboard metadata defines what dashboards and widgets exist.
# This is a static config file — in production this might come
# from a PowerBI API or a config database.
#
# The agent reads this to decide which widget to highlight
# alongside its answer.

def get_dashboard_metadata() -> dict:
    """
    Returns the full dashboard and widget metadata.

    Structure:
        dashboards → list of dashboards
            each dashboard → name, description, widgets
                each widget → name, description, relevant_tables,
                              relevant_metrics, filters_supported
    """
    return {
        "dashboards": [
            {
                "name": "Site Overview",
                "description": "High-level view of all construction sites",
                "widgets": [
                    {
                        "name": "Active Sites Count",
                        "description": "Total number of currently active sites",
                        "relevant_tables": ["sites"],
                        "relevant_metrics": ["site count", "active sites"],
                        "filters_supported": ["status"]
                    },
                    {
                        "name": "Budget Utilisation",
                        "description": "Budget spent vs total per site",
                        "relevant_tables": ["sites"],
                        "relevant_metrics": [
                            "budget", "spent", "utilisation",
                            "cost", "financial"
                        ],
                        "filters_supported": ["site_name", "status"]
                    },
                    {
                        "name": "Project Timeline",
                        "description": "Site start and end dates, schedule status",
                        "relevant_tables": ["sites"],
                        "relevant_metrics": [
                            "timeline", "schedule", "deadline",
                            "completion", "delay"
                        ],
                        "filters_supported": ["site_name", "status"]
                    },
                    {
                        "name": "Site Summary Card",
                        "description": "Key metrics for a specific site",
                        "relevant_tables": [
                            "sites", "workmen",
                            "equipment_inventory", "incidents"
                        ],
                        "relevant_metrics": ["site details", "overview"],
                        "filters_supported": ["site_name"]
                    },
                ]
            },
            {
                "name": "Workforce Dashboard",
                "description": "Worker attendance, roles, and contractor data",
                "widgets": [
                    {
                        "name": "Attendance Rate",
                        "description": "Present vs absent vs on leave by site",
                        "relevant_tables": ["workmen"],
                        "relevant_metrics": [
                            "attendance", "present", "absent",
                            "leave", "headcount"
                        ],
                        "filters_supported": ["site_name", "attendance_status"]
                    },
                    {
                        "name": "Worker Count by Site",
                        "description": "Total workers deployed per site",
                        "relevant_tables": ["workmen"],
                        "relevant_metrics": [
                            "worker count", "workforce",
                            "headcount", "manpower"
                        ],
                        "filters_supported": ["site_name", "worker_type"]
                    },
                    {
                        "name": "Role Distribution",
                        "description": "Breakdown of worker roles across sites",
                        "relevant_tables": ["workmen"],
                        "relevant_metrics": [
                            "role", "engineer", "foreman",
                            "labourer", "supervisor"
                        ],
                        "filters_supported": ["site_name", "role"]
                    },
                    {
                        "name": "Contractor vs Direct",
                        "description": "Split between contractor and direct workers",
                        "relevant_tables": ["workmen"],
                        "relevant_metrics": [
                            "contractor", "direct", "worker type"
                        ],
                        "filters_supported": ["site_name", "worker_type"]
                    },
                    {
                        "name": "Daily Wage Analysis",
                        "description": "Average and total daily wages by site and role",
                        "relevant_tables": ["workmen"],
                        "relevant_metrics": [
                            "wage", "salary", "cost", "daily rate"
                        ],
                        "filters_supported": ["site_name", "role"]
                    },
                ]
            },
            {
                "name": "Safety and Equipment",
                "description": "Incident tracking and equipment health monitoring",
                "widgets": [
                    {
                        "name": "Incident Rate by Site",
                        "description": "Number of incidents per site over time",
                        "relevant_tables": ["incidents"],
                        "relevant_metrics": [
                            "incident", "safety", "accident",
                            "near miss", "injury"
                        ],
                        "filters_supported": [
                            "site_name", "severity", "status"
                        ]
                    },
                    {
                        "name": "Open Incidents Tracker",
                        "description": "All unresolved safety incidents",
                        "relevant_tables": ["incidents"],
                        "relevant_metrics": [
                            "open incident", "unresolved",
                            "under investigation"
                        ],
                        "filters_supported": [
                            "site_name", "severity", "status"
                        ]
                    },
                    {
                        "name": "Equipment Status Overview",
                        "description": "Operational vs maintenance vs breakdown",
                        "relevant_tables": ["equipment_inventory"],
                        "relevant_metrics": [
                            "equipment", "machinery", "operational",
                            "breakdown", "maintenance"
                        ],
                        "filters_supported": ["site_name", "status"]
                    },
                    {
                        "name": "Equipment Utilisation",
                        "description": "Utilisation percentage per equipment per site",
                        "relevant_tables": ["equipment_inventory"],
                        "relevant_metrics": [
                            "utilisation", "usage", "efficiency"
                        ],
                        "filters_supported": ["site_name", "equipment_type"]
                    },
                    {
                        "name": "Maintenance Schedule",
                        "description": "Upcoming and overdue maintenance",
                        "relevant_tables": ["equipment_inventory"],
                        "relevant_metrics": [
                            "maintenance", "service", "overdue",
                            "next service"
                        ],
                        "filters_supported": ["site_name", "status"]
                    },
                    {
                        "name": "Material Stock Levels",
                        "description": "Current stock vs minimum levels per site",
                        "relevant_tables": ["materials"],
                        "relevant_metrics": [
                            "material", "stock", "inventory",
                            "cement", "steel", "aggregate"
                        ],
                        "filters_supported": ["site_name", "material_type"]
                    },
                ]
            }
        ]
    }