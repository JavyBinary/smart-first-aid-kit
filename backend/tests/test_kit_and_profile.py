"""Unit and API integration tests for user kit and health profile endpoints."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from medai.auth.models import Role, User
from medai.auth.router import get_current_user
from medai.dialogs import InMemoryDialogEventBroker, InMemoryHistoryStore
from medai.dialogs.service import DialogService
from medai.kit import (
    CreateKitItemRequest,
    InMemoryKitStore,
    KitItem,
    UpdateKitItemRequest,
)
from medai.main import create_app
from medai.profile import (
    InMemoryProfileStore,
    UpdateHealthProfileRequest,
)


def test_kit_item_expiry_computation():
    future_item = KitItem.create(
        id="item_1",
        name="Ибупрофен",
        dosage="200 мг",
        form="таблетки",
        category="НПВП",
        expiry="2030-01-01",
    )
    assert future_item.is_expired is False

    past_item = KitItem.create(
        id="item_2",
        name="Парацетамол",
        dosage="500 мг",
        form="таблетки",
        category="Анальгетики",
        expiry="2020-01-01",
    )
    assert past_item.is_expired is True


@pytest.mark.asyncio
async def test_in_memory_kit_store_crud_and_isolation():
    store = InMemoryKitStore()
    user_a = uuid4()
    user_b = uuid4()

    # 1. Add item for User A
    req = CreateKitItemRequest(
        name="Амоксициллин",
        dosage="500 мг",
        form="капсулы",
        category="Антибиотики",
        tags=["антибиотик", "инфекции"],
        quantity=2,
        expiry="2027-10-10",
        status="rx",
    )
    item_a = await store.add_item(user_a, req)
    assert item_a.name == "Амоксициллин"
    assert item_a.quantity == 2
    assert item_a.status == "rx"

    # 2. List items
    items_a = await store.list_items(user_a)
    assert len(items_a) == 1
    items_b = await store.list_items(user_b)
    assert len(items_b) == 0

    # 3. Update item
    upd_req = UpdateKitItemRequest(quantity=5, dosage="1000 мг")
    updated = await store.update_item(user_a, item_a.id, upd_req)
    assert updated.quantity == 5
    assert updated.dosage == "1000 мг"

    # 4. User B cannot delete User A's item
    deleted_b = await store.delete_item(user_b, item_a.id)
    assert deleted_b is False

    # 5. User A deletes item
    deleted_a = await store.delete_item(user_a, item_a.id)
    assert deleted_a is True
    assert len(await store.list_items(user_a)) == 0


@pytest.mark.asyncio
async def test_in_memory_profile_store():
    store = InMemoryProfileStore()
    user = uuid4()

    # Get default profile
    default_p = await store.get_profile(user)
    assert default_p.age == 25
    assert default_p.weight_kg == 70.0
    assert default_p.chronic_diseases == []
    assert default_p.allergies == []

    # Update profile
    upd_req = UpdateHealthProfileRequest(
        age=30,
        weight_kg=78.5,
        chronic=["Гастрит"],
        allergies=["Пенициллины"],
        special_notes="Принимает витамин D",
    )
    updated = await store.update_profile(user, upd_req)
    assert updated.age == 30
    assert updated.weight_kg == 78.5
    assert updated.chronic_diseases == ["Гастрит"]
    assert updated.allergies == ["Пенициллины"]
    assert updated.special_notes == "Принимает витамин D"


@pytest.mark.asyncio
async def test_kit_and_profile_api_endpoints():
    kit_store = InMemoryKitStore()
    profile_store = InMemoryProfileStore()
    history = InMemoryHistoryStore()
    broker = InMemoryDialogEventBroker()
    d_service = DialogService(history, broker)

    app = create_app(
        dialog_service=d_service,
        kit_store=kit_store,
        profile_store=profile_store,
    )

    user_a = User(
        id=uuid4(),
        email="alex@bmstu.ru",
        name="Алексей",
        role=Role.USER,
        avatar_color="#4F46E5",
    )
    user_b = User(
        id=uuid4(),
        email="kate@bmstu.ru",
        name="Екатерина",
        role=Role.USER,
        avatar_color="#EC4899",
    )

    current_user_holder = [user_a]
    app.dependency_overrides[get_current_user] = lambda: current_user_holder[0]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # --- KIT API ---
        # 1. Initially empty kit
        res_kit_empty = await client.get("/api/v1/kit")
        assert res_kit_empty.status_code == 200
        assert res_kit_empty.json()["total"] == 0

        # 2. Add medication
        res_add = await client.post(
            "/api/v1/kit/items",
            json={
                "name": "Ибупрофен",
                "dosage": "200 мг",
                "form": "таблетки",
                "category": "Обезболивающие",
                "tags": ["головная боль", "жар"],
                "quantity": 3,
                "expiry": "2028-05-01",
                "status": "otc",
            },
        )
        assert res_add.status_code == 201
        data_add = res_add.json()
        assert data_add["status"] == "created"
        item_id = data_add["id"]

        # 3. List kit items
        res_list = await client.get("/api/v1/kit")
        assert res_list.status_code == 200
        assert res_list.json()["total"] == 1
        assert res_list.json()["items"][0]["name"] == "Ибупрофен"

        # 4. Update kit item
        res_upd = await client.put(
            f"/api/v1/kit/items/{item_id}",
            json={"quantity": 10},
        )
        assert res_upd.status_code == 200
        assert res_upd.json()["quantity"] == 10

        # 5. User B isolation check (cannot modify or delete User A's item)
        current_user_holder[0] = user_b
        res_del_foreign = await client.delete(f"/api/v1/kit/items/{item_id}")
        assert res_del_foreign.status_code == 404

        # Switch back to User A and delete
        current_user_holder[0] = user_a
        res_del = await client.delete(f"/api/v1/kit/items/{item_id}")
        assert res_del.status_code == 200
        assert res_del.json()["status"] == "deleted"

        # --- PROFILE API ---
        # 6. Get initial health profile
        res_prof = await client.get("/api/v1/profile")
        assert res_prof.status_code == 200
        assert res_prof.json()["age"] == 25

        # 7. Update health profile
        res_prof_upd = await client.put(
            "/api/v1/profile",
            json={
                "age": 28,
                "weight_kg": 72.0,
                "chronic": ["Язвенная болезнь ЖКТ"],
                "allergies": ["НПВП (Аспирин/Ибупрофен)"],
            },
        )
        assert res_prof_upd.status_code == 200
        prof_data = res_prof_upd.json()
        assert prof_data["age"] == 28
        assert prof_data["weight_kg"] == 72.0
        assert "Язвенная болезнь ЖКТ" in prof_data["chronic_diseases"]
        assert "НПВП (Аспирин/Ибупрофен)" in prof_data["allergies"]

        # 8. Check validation constraint (age > 130)
        res_invalid_age = await client.put(
            "/api/v1/profile",
            json={"age": 200},
        )
        assert res_invalid_age.status_code == 422
