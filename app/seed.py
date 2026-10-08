from app.database import SessionLocal
from app.models import Role

roles = [
    "Admin",
    "Warehouse Manager",
    "Fulfillment Agent",
    "Customer",
]

db = SessionLocal()

try:
    for role_name in roles:
        existing_role = db.query(Role).filter(
            Role.name == role_name
        ).first()

        if not existing_role:
            db.add(Role(name=role_name))

    db.commit()

    print("Roles seeded successfully.")

finally:
    db.close()