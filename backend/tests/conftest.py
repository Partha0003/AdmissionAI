import os
import sys
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import create_engine
from datetime import date

# Set test environment
os.environ["ENVIRONMENT"] = "TEST"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SYNC_DATABASE_URL"] = "sqlite:///:memory:"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app
from app.database.base import Base
from app.database.session import get_db
from app.models.institution import Institution
from app.models.role import Role
from app.models.user import User
from app.models.student import Student
from app.models.admission import AdmissionApplication, AdmissionStatusHistory
from app.models.document import DocumentType, DocumentRule
from app.core.security import get_password_hash, create_access_token


@pytest_asyncio.fixture(scope="function")
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        # Seed test institution and roles
        inst = Institution(
            id="inst-xyz-001",
            code="XYZ",
            name="XYZ Engineering College",
            academic_year="2026-27",
            environment="TEST"
        )
        session.add(inst)

        roles = {
            "STUDENT": Role(id=1, name="STUDENT", description="Student"),
            "ADMIN_VERIFIER": Role(id=2, name="ADMIN_VERIFIER", description="Verifier"),
            "FINANCE_OFFICER": Role(id=3, name="FINANCE_OFFICER", description="Finance"),
            "ADMISSION_HEAD": Role(id=4, name="ADMISSION_HEAD", description="Head"),
            "SUPER_ADMIN": Role(id=5, name="SUPER_ADMIN", description="SuperAdmin"),
            "PARENT": Role(id=6, name="PARENT", description="Parent/Guardian"),
        }
        for r in roles.values():
            session.add(r)
        await session.flush()

        # Seed Standard Document Types & Rules
        doc_types_def = [
            ("TENTH_MARKSHEET", "10th Marksheet", "ACADEMIC", 1, {"always": True}),
            ("TWELFTH_MARKSHEET", "12th Marksheet", "ACADEMIC", 2, {"always": True}),
            ("TRANSFER_CERTIFICATE", "Transfer Certificate", "ACADEMIC", 3, {"always": True}),
            ("ALLOTMENT_ORDER", "TNEA Allotment Order", "ALLOTMENT", 4, {"always": True}),
            ("COMMUNITY_CERTIFICATE", "Community Certificate", "IDENTITY_CATEGORY", 5, {"community": ["BC", "BCM", "MBC", "SC", "ST"]}),
            ("FIRST_GRADUATE_CERTIFICATE", "First Graduate Certificate", "FINANCIAL", 6, {"is_first_graduate": True}),
            ("INCOME_CERTIFICATE", "Income Certificate", "FINANCIAL", 7, {"is_pmss_scholarship": True}),
            ("SPECIAL_RESERVATION_CERTIFICATE", "Special Reservation Certificate", "IDENTITY_CATEGORY", 8, {"is_7_5_govt_quota": True}),
            ("NATIVITY_CERTIFICATE", "Nativity Certificate", "IDENTITY_CATEGORY", 9, {"non_tn_resident": True}),
        ]

        for code, name, cat, order, conds in doc_types_def:
            dt = DocumentType(
                code=code,
                name=name,
                category=cat,
                allowed_extensions=["pdf", "png", "jpg", "jpeg"],
                max_size_mb=5,
                sort_order=order,
                is_active=True
            )
            session.add(dt)
            await session.flush()

            rule = DocumentRule(
                document_type_id=dt.id,
                required=True,
                applicable_conditions=conds,
                priority=10,
                academic_year="2026-27",
                is_active=True
            )
            session.add(rule)
            await session.flush()

        # Seed Admin User
        admin_user = User(
            id="user-admin-001",
            email="admin@xyz.edu.demo",
            hashed_password=get_password_hash("Admin@1234"),
            role_id=roles["ADMIN_VERIFIER"].id,
            is_active=True
        )
        session.add(admin_user)

        # Seed Admission Head User
        head_user = User(
            id="user-head-001",
            email="head@xyz.edu.demo",
            hashed_password=get_password_hash("Head@1234"),
            role_id=roles["ADMISSION_HEAD"].id,
            is_active=True
        )
        session.add(head_user)

        # Seed Super Admin User
        super_user = User(
            id="user-super-001",
            email="superadmin@xyz.edu.demo",
            hashed_password=get_password_hash("Super@1234"),
            role_id=roles["SUPER_ADMIN"].id,
            is_active=True
        )
        session.add(super_user)

        # Seed Finance Officer User
        finance_user = User(
            id="user-finance-001",
            email="finance@xyz.edu.demo",
            hashed_password=get_password_hash("Finance@1234"),
            role_id=roles["FINANCE_OFFICER"].id,
            is_active=True
        )
        session.add(finance_user)

        # Seed Parent User
        parent_user = User(
            id="user-parent-001",
            email="parent@demo.admissionai.local",
            hashed_password=get_password_hash("Parent@1234"),
            role_id=roles["PARENT"].id,
            is_active=True
        )
        session.add(parent_user)

        # Seed Student 1 (Karthik - BC, General)
        student1_user = User(
            id="user-student-001",
            email="karthik.xyz2026001@demo.admissionai.local",
            hashed_password=get_password_hash("Student@1234"),
            role_id=roles["STUDENT"].id,
            is_active=True
        )
        session.add(student1_user)
        await session.flush()

        student1 = Student(
            id="student-001",
            user_id=student1_user.id,
            institution_id=inst.id,
            tnea_application_number="XYZ2026001",
            full_name="Karthikeyan S",
            date_of_birth=date(2008, 5, 14),
            email="karthik.xyz2026001@demo.admissionai.local",
            mobile="+91 98765 43210",
            community="BC",
            allotted_branch="Computer Science and Engineering",
            quota="General",
            status="ACTIVATED"
        )
        session.add(student1)
        await session.flush()

        app1 = AdmissionApplication(
            id="app-001",
            student_id=student1.id,
            application_number="XYZADM202600001",
            status="ACTIVATED",
            completion_percentage=25,
            nationality="Indian",
            state="Tamil Nadu",
            caste="BC"
        )
        session.add(app1)

        # Seed Student 2 (Ananya - OC, General)
        student2_user = User(
            id="user-student-002",
            email="ananya.xyz2026002@demo.admissionai.local",
            hashed_password=get_password_hash("Student@1234"),
            role_id=roles["STUDENT"].id,
            is_active=True
        )
        session.add(student2_user)
        await session.flush()

        student2 = Student(
            id="student-002",
            user_id=student2_user.id,
            institution_id=inst.id,
            tnea_application_number="XYZ2026002",
            full_name="Ananya Ramesh",
            date_of_birth=date(2008, 8, 22),
            email="ananya.xyz2026002@demo.admissionai.local",
            mobile="+91 98765 43211",
            community="OC",
            allotted_branch="Electronics and Communication Engineering",
            quota="General",
            status="APPLICATION_IN_PROGRESS"
        )
        session.add(student2)
        await session.flush()

        app2 = AdmissionApplication(
            id="app-002",
            student_id=student2.id,
            application_number="XYZADM202600002",
            status="APPLICATION_IN_PROGRESS",
            completion_percentage=60,
            nationality="Indian",
            state="Tamil Nadu",
            caste="OC"
        )
        session.add(app2)

        await session.commit()
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(test_db):
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def student1_token():
    return create_access_token(
        subject="user-student-001",
        role="STUDENT",
        claims={"email": "karthik.xyz2026001@demo.admissionai.local"}
    )


@pytest.fixture
def student2_token():
    return create_access_token(
        subject="user-student-002",
        role="STUDENT",
        claims={"email": "ananya.xyz2026002@demo.admissionai.local"}
    )


@pytest.fixture
def admin_token():
    return create_access_token(
        subject="user-admin-001",
        role="ADMIN_VERIFIER",
        claims={"email": "admin@xyz.edu.demo"}
    )


@pytest.fixture
def finance_token():
    return create_access_token(
        subject="user-finance-001",
        role="FINANCE_OFFICER",
        claims={"email": "finance@xyz.edu.demo"}
    )


@pytest.fixture
def head_token():
    return create_access_token(
        subject="user-head-001",
        role="ADMISSION_HEAD",
        claims={"email": "head@xyz.edu.demo"}
    )


@pytest.fixture
def super_admin_token():
    return create_access_token(
        subject="user-super-001",
        role="SUPER_ADMIN",
        claims={"email": "superadmin@xyz.edu.demo"}
    )


@pytest.fixture
def parent_token():
    return create_access_token(
        subject="user-parent-001",
        role="PARENT",
        claims={"email": "parent@demo.admissionai.local"}
    )

