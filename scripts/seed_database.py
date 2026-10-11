import json
import os
import sys
import hashlib
from datetime import datetime, date, timedelta, timezone

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database.session import sync_engine, SyncSessionLocal
from app.database.base import Base
from app.models.institution import Institution
from app.models.role import Role
from app.models.user import User
from app.models.student import Student
from app.models.admission import AdmissionApplication, AdmissionStatusHistory
from app.models.tnea_allotment import TNEAAllotment, TNEAImportBatch
from app.models.activation_token import StudentActivationToken
from app.models.document import DocumentType, DocumentRule, Document, DocumentVersion
from app.core.security import get_password_hash
from app.core.config import settings


def seed():
    print(f"\n[*] Seeding database for '{settings.INSTITUTION_NAME}' ({settings.ACADEMIC_YEAR})...")

    # Re-create tables
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)

    session = SyncSessionLocal()
    try:
        # 1. Ensure Roles
        roles_data = [
            ("STUDENT", "Enrolled candidate undergoing admission and onboarding"),
            ("ADMIN_VERIFIER", "Admission scrutiny officer reviewing applications and certificates"),
            ("FINANCE_OFFICER", "Accounts and finance officer verifying fee payments & DDs"),
            ("ADMISSION_HEAD", "Senior admission authority managing branches and enrollment"),
            ("SUPER_ADMIN", "System administrator with full technical access"),
        ]
        
        role_map = {}
        for role_name, desc in roles_data:
            role = session.query(Role).filter(Role.name == role_name).first()
            if not role:
                role = Role(name=role_name, description=desc)
                session.add(role)
                session.flush()
            role_map[role_name] = role
        print("  [+] Roles initialized")

        # 2. Ensure Institution
        inst = session.query(Institution).filter(Institution.code == settings.INSTITUTION_CODE).first()
        if not inst:
            inst = Institution(
                code=settings.INSTITUTION_CODE,
                name=settings.INSTITUTION_NAME,
                academic_year=settings.ACADEMIC_YEAR,
                environment=settings.ENVIRONMENT,
                config={
                    "branches": [
                        "Computer Science and Engineering",
                        "Electronics and Communication Engineering",
                        "Information Technology",
                        "Artificial Intelligence and Data Science",
                        "Electrical and Electronics Engineering",
                        "Mechanical Engineering"
                    ],
                    "mock_integrations": {
                        "tnea": True,
                        "erp": True,
                        "payment": True,
                        "notification": True
                    }
                }
            )
            session.add(inst)
            session.flush()
        print(f"  [+] Institution '{inst.name}' ({inst.code}) verified")

        # 3. Seed Staff Demo Accounts
        staff_accounts = [
            ("admin@xyz.edu.demo", "Admin@1234", "ADMIN_VERIFIER"),
            ("verifier@xyz.edu.demo", "Verifier@1234", "ADMIN_VERIFIER"),
            ("finance@xyz.edu.demo", "Finance@1234", "FINANCE_OFFICER"),
            ("head@xyz.edu.demo", "Head@1234", "ADMISSION_HEAD"),
            ("superadmin@xyz.edu.demo", "SuperAdmin@1234", "SUPER_ADMIN"),
        ]

        for email, password, role_name in staff_accounts:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    hashed_password=get_password_hash(password),
                    role_id=role_map[role_name].id,
                    is_active=True
                )
                session.add(user)
                session.flush()
            else:
                user.hashed_password = get_password_hash(password)
                user.role_id = role_map[role_name].id
                user.is_active = True
                session.flush()
        print("  [+] Staff demo accounts verified")

        # 4. Seed Standard Document Types & Dynamic Rules
        doc_types_def = [
            {
                "code": "TENTH_MARKSHEET",
                "name": "10th Standard Marksheet / Pass Certificate",
                "description": "Original Secondary School Leaving Certificate (SSLC) / Class X Marksheet",
                "category": "ACADEMIC",
                "allowed_extensions": ["pdf", "png", "jpg", "jpeg"],
                "max_size_mb": 5,
                "sort_order": 1,
                "rules": [
                    {"required": True, "applicable_conditions": {"always": True}, "priority": 10}
                ]
            },
            {
                "code": "TWELFTH_MARKSHEET",
                "name": "12th Standard / HSC Marksheet",
                "description": "Original Higher Secondary Certificate (HSC) / Class XII Marksheet",
                "category": "ACADEMIC",
                "allowed_extensions": ["pdf", "png", "jpg", "jpeg"],
                "max_size_mb": 5,
                "sort_order": 2,
                "rules": [
                    {"required": True, "applicable_conditions": {"always": True}, "priority": 10}
                ]
            },
            {
                "code": "TRANSFER_CERTIFICATE",
                "name": "Transfer Certificate (TC)",
                "description": "Transfer Certificate issued by the school last studied",
                "category": "ACADEMIC",
                "allowed_extensions": ["pdf", "png", "jpg", "jpeg"],
                "max_size_mb": 5,
                "sort_order": 3,
                "rules": [
                    {"required": True, "applicable_conditions": {"always": True}, "priority": 10}
                ]
            },
            {
                "code": "ALLOTMENT_ORDER",
                "name": "TNEA Allotment Order 2026",
                "description": "Provisional Allotment Order issued by the Directorate of Technical Education (DoTE) / TNEA",
                "category": "ALLOTMENT",
                "allowed_extensions": ["pdf", "png", "jpg", "jpeg"],
                "max_size_mb": 5,
                "sort_order": 4,
                "rules": [
                    {"required": True, "applicable_conditions": {"always": True}, "priority": 10}
                ]
            },
            {
                "code": "COMMUNITY_CERTIFICATE",
                "name": "Permanent Community Certificate Card",
                "description": "Permanent Community Certificate Card issued by Revenue Authorities (Required for BC, BCM, MBC/DNC, SC, SCA, ST)",
                "category": "IDENTITY_CATEGORY",
                "allowed_extensions": ["pdf", "png", "jpg", "jpeg"],
                "max_size_mb": 5,
                "sort_order": 5,
                "rules": [
                    {"required": True, "applicable_conditions": {"community": ["BC", "BCM", "MBC", "MBC_DNC", "SC", "SCA", "ST"]}, "priority": 20}
                ]
            },
            {
                "code": "FIRST_GRADUATE_CERTIFICATE",
                "name": "First Graduate Certificate & Joint Declaration",
                "description": "Certificate issued by Tahsildar along with signed Joint Declaration by candidate and parents",
                "category": "FINANCIAL",
                "allowed_extensions": ["pdf", "png", "jpg", "jpeg"],
                "max_size_mb": 5,
                "sort_order": 6,
                "rules": [
                    {"required": True, "applicable_conditions": {"is_first_graduate": True}, "priority": 30}
                ]
            },
            {
                "code": "INCOME_CERTIFICATE",
                "name": "Income Certificate",
                "description": "Annual Family Income Certificate issued by competent Revenue Authority (Mandatory for PMSS / Post-Matric Scholarship / Fee waiver)",
                "category": "FINANCIAL",
                "allowed_extensions": ["pdf", "png", "jpg", "jpeg"],
                "max_size_mb": 5,
                "sort_order": 7,
                "rules": [
                    {"required": True, "applicable_conditions": {"is_pmss_scholarship": True}, "priority": 40},
                    {"required": True, "applicable_conditions": {"income_under_250k": True}, "priority": 45}
                ]
            },
            {
                "code": "SPECIAL_RESERVATION_CERTIFICATE",
                "name": "Special Reservation Certificate (7.5% Govt Quota / Sports / PWD / Ex-Serviceman)",
                "description": "Bonafide certificate for 6th-12th TN Govt school study or relevant quota certificate",
                "category": "IDENTITY_CATEGORY",
                "allowed_extensions": ["pdf", "png", "jpg", "jpeg"],
                "max_size_mb": 5,
                "sort_order": 8,
                "rules": [
                    {"required": True, "applicable_conditions": {"is_7_5_govt_quota": True}, "priority": 50}
                ]
            },
            {
                "code": "NATIVITY_CERTIFICATE",
                "name": "Nativity Certificate",
                "description": "Tamil Nadu Nativity Certificate (Required if studied VIII to XII outside Tamil Nadu or claiming TN nativity)",
                "category": "IDENTITY_CATEGORY",
                "allowed_extensions": ["pdf", "png", "jpg", "jpeg"],
                "max_size_mb": 5,
                "sort_order": 9,
                "rules": [
                    {"required": True, "applicable_conditions": {"non_tn_resident": True}, "priority": 60}
                ]
            }
        ]

        doc_type_map = {}
        for dt_data in doc_types_def:
            dt = session.query(DocumentType).filter(DocumentType.code == dt_data["code"]).first()
            if not dt:
                dt = DocumentType(
                    code=dt_data["code"],
                    name=dt_data["name"],
                    description=dt_data["description"],
                    category=dt_data["category"],
                    allowed_extensions=dt_data["allowed_extensions"],
                    max_size_mb=dt_data["max_size_mb"],
                    sort_order=dt_data["sort_order"],
                    is_active=True
                )
                session.add(dt)
                session.flush()
            doc_type_map[dt_data["code"]] = dt

            # Rules
            for r_data in dt_data.get("rules", []):
                existing_rule = session.query(DocumentRule).filter(
                    DocumentRule.document_type_id == dt.id,
                    DocumentRule.academic_year == settings.ACADEMIC_YEAR
                ).first()
                if not existing_rule:
                    rule = DocumentRule(
                        document_type_id=dt.id,
                        required=r_data["required"],
                        applicable_conditions=r_data["applicable_conditions"],
                        priority=r_data["priority"],
                        academic_year=settings.ACADEMIC_YEAR,
                        is_active=True
                    )
                    session.add(rule)
                    session.flush()

        print("  [+] Standard Document Types and Rules initialized")

        # 5. Seed Synthetic Students
        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic", "demo_students.json")
        with open(data_path, "r", encoding="utf-8") as f:
            students_data = json.load(f)

        student_pwd_hash = get_password_hash("Student@1234")

        for idx, s_data in enumerate(students_data, 1):
            app_no = s_data["tnea_application_number"]
            email = s_data["email"]
            adm_app_num = f"XYZADM2026{idx:05d}"

            # User account
            user = session.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    hashed_password=student_pwd_hash,
                    role_id=role_map["STUDENT"].id,
                    is_active=True
                )
                session.add(user)
                session.flush()
            else:
                user.hashed_password = student_pwd_hash
                user.role_id = role_map["STUDENT"].id
                user.is_active = True
                session.flush()

            # Student profile
            student = session.query(Student).filter(Student.tnea_application_number == app_no).first()
            if not student:
                student = Student(
                    user_id=user.id,
                    institution_id=inst.id,
                    tnea_application_number=app_no,
                    full_name=s_data["full_name"],
                    date_of_birth=date.fromisoformat(s_data["date_of_birth"]),
                    email=email,
                    mobile=s_data["mobile"],
                    community=s_data["community"],
                    allotted_branch=s_data["allotted_branch"],
                    quota=s_data["quota"],
                    status=s_data["status"]
                )
                session.add(student)
                session.flush()

            # Admission Application
            app = session.query(AdmissionApplication).filter(AdmissionApplication.student_id == student.id).first()
            if not app:
                is_fg = (s_data.get("quota") == "First Graduate")
                is_75 = ("7.5" in s_data.get("quota", ""))
                app = AdmissionApplication(
                    student_id=student.id,
                    application_number=adm_app_num,
                    status=s_data["status"],
                    completion_percentage=s_data["completion_percentage"],
                    gender="Male" if "Karthik" in s_data["full_name"] or "Praveen" in s_data["full_name"] or "Riyaz" in s_data["full_name"] else "Female",
                    blood_group="O+ve",
                    nationality="Indian",
                    religion="Hindu" if "Riyaz" not in s_data["full_name"] else "Islam",
                    caste=s_data["community"],
                    mother_tongue="Tamil",
                    aadhaar_number=f"9876 5432 {1000 + idx:04d}",
                    address_line1=f"No. {12 + idx}, Anna Nagar 2nd Street",
                    city="Chennai",
                    district="Chennai",
                    state="Tamil Nadu",
                    pincode="600040",
                    emergency_contact_name=f"Parent of {s_data['full_name']}",
                    emergency_contact_phone=s_data["mobile"],
                    emergency_contact_relation="Father",
                    father_name=f"Father of {s_data['full_name']}",
                    father_occupation="Private Employee",
                    father_mobile=s_data["mobile"],
                    mother_name=f"Mother of {s_data['full_name']}",
                    mother_occupation="Homemaker",
                    mother_mobile="+91 94444 11223",
                    annual_family_income=180000.0 if is_fg or is_75 else 450000.0,
                    tenth_school_name="Govt Higher Secondary School" if is_75 else "DAV Higher Secondary School",
                    tenth_board="State Board",
                    tenth_year_of_passing=2024,
                    tenth_registration_number=f"TN10{100000 + idx}",
                    tenth_total_marks=475.0,
                    tenth_max_marks=500.0,
                    tenth_percentage=95.0,
                    twelfth_school_name="Govt Higher Secondary School" if is_75 else "DAV Higher Secondary School",
                    twelfth_board="State Board",
                    twelfth_year_of_passing=2026,
                    twelfth_registration_number=f"TN12{200000 + idx}",
                    twelfth_total_marks=570.0,
                    twelfth_max_marks=600.0,
                    twelfth_percentage=95.0,
                    twelfth_maths_marks=98.0,
                    twelfth_physics_marks=95.0,
                    twelfth_chemistry_marks=96.0,
                    twelfth_cutoff_marks=192.5,
                    allotment_order_number=f"TNEA-2026-ALT-{app_no}",
                    allotment_quota=s_data.get("quota", "General"),
                    allotted_category=s_data.get("community", "OC"),
                    allotted_college_code=settings.INSTITUTION_CODE,
                    allotted_branch_name=s_data["allotted_branch"],
                    is_first_graduate=is_fg,
                    is_pmss_scholarship=False,
                    is_7_5_govt_quota=is_75,
                    is_hostel_required=False,
                    is_transport_required=True,
                    declaration_accepted=(s_data["status"] in ["APPLICATION_SUBMITTED", "DOCUMENT_REVIEW", "DOCUMENTS_VERIFIED", "ADMISSION_CONFIRMED"]),
                    declaration_accepted_at=datetime.now(timezone.utc) if (s_data["status"] in ["APPLICATION_SUBMITTED", "DOCUMENT_REVIEW"]) else None,
                    submitted_at=datetime.now(timezone.utc) if (s_data["status"] in ["APPLICATION_SUBMITTED", "DOCUMENT_REVIEW"]) else None,
                    personal_data={
                        "candidate_name": s_data["full_name"],
                        "dob": s_data["date_of_birth"],
                        "mobile": s_data["mobile"],
                        "email": email,
                        "community": s_data["community"],
                    },
                    academic_data={
                        "allotted_branch": s_data["allotted_branch"],
                        "quota": s_data["quota"],
                        "tnea_app_no": app_no
                    }
                )
                session.add(app)
                session.flush()

                # Add initial status history
                history = AdmissionStatusHistory(
                    admission_application_id=app.id,
                    previous_status="ALLOTTED",
                    new_status=s_data["status"],
                    changed_by="system@admissionai.local",
                    actor_role="SYSTEM",
                    reason=f"Synthetic seed profile initialized with state '{s_data['status']}'",
                    metadata_info={"scenario": s_data.get("scenario_notes", "")}
                )
                session.add(history)

            # TNEA Allotment record
            allotment = session.query(TNEAAllotment).filter(TNEAAllotment.tnea_application_number == app_no).first()
            if not allotment:
                allotment = TNEAAllotment(
                    student_id=student.id,
                    tnea_application_number=app_no,
                    allotment_number=f"ALT-{app_no}",
                    college_code=settings.INSTITUTION_CODE,
                    college_name=settings.INSTITUTION_NAME,
                    branch_code=s_data["allotted_branch"][:3].upper(),
                    branch_name=s_data["allotted_branch"],
                    community=s_data.get("community", "OC"),
                    quota=s_data.get("quota", "GOVERNMENT"),
                    cutoff_mark=192.5,
                    allotment_date=date(2026, 8, 1),
                    joining_deadline=date(2026, 8, 20),
                    allotment_status="ALLOTTED",
                    source="SEED_DEMO",
                )
                session.add(allotment)
                session.flush()

            # Activation Token (if not activated or for demo testing)
            act_token = session.query(StudentActivationToken).filter(StudentActivationToken.student_id == student.id).first()
            if not act_token:
                demo_raw = f"ACT-{app_no}-DEMO2026"
                t_hash = hashlib.sha256(demo_raw.encode("utf-8")).hexdigest()
                act_token = StudentActivationToken(
                    student_id=student.id,
                    token_hash=t_hash,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                    is_used=(s_data["status"] != "ACTIVATION_PENDING"),
                    used_at=datetime.now(timezone.utc) if s_data["status"] != "ACTIVATION_PENDING" else None
                )
                session.add(act_token)
                session.flush()

        session.commit()
        print("  [+] 5 Synthetic student personas and applications seeded")
        print("\n============================================================")
        print("DEMO CREDENTIALS SUMMARY (XYZ Engineering College 2026-27)")
        print("============================================================")
        print("STAFF ACCOUNTS:")
        print("  Admin / Verifier:  admin@xyz.edu.demo        / Admin@1234")
        print("  Document Verifier: verifier@xyz.edu.demo     / Verifier@1234")
        print("  Finance Officer:   finance@xyz.edu.demo      / Finance@1234")
        print("  Admission Head:    head@xyz.edu.demo         / Head@1234")
        print("  Super Admin:       superadmin@xyz.edu.demo   / SuperAdmin@1234")
        print("\nSYNTHETIC STUDENT ACCOUNTS (Password: Student@1234):")
        for s_data in students_data:
            print(f"  {s_data['tnea_application_number']} | {s_data['full_name']:<18} | State: {s_data['status']:<22} | {s_data['email']}")
        print("============================================================\n")

    except Exception as e:
        session.rollback()
        print(f"[-] Error during database seeding: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed()
