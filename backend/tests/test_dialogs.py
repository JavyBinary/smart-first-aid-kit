"""Unit and API integration tests for dialogs, EventBroker, and SSE streaming."""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from medai.auth.models import Role, User
from medai.auth.router import get_current_user
from medai.dialogs import (
    DialogEvent,
    DialogEventType,
    DialogNotFoundError,
    DialogService,
    InMemoryDialogEventBroker,
    InMemoryHistoryStore,
    make_title,
)
from medai.main import create_app
from medai.rag.analyzer import MorphAnalyzer
from medai.rag.index import load_package_from_yaml


def test_make_title_formatting():
    assert make_title("") == "Новый диалог"
    assert make_title("   ") == "Новый диалог"
    assert make_title("  Сильно    болит  зуб   ") == "Сильно болит зуб"
    long_text = "Очень длинный запрос пользователя о том, как правильно принимать различные медикаменты при простуде и гриппе"
    formatted = make_title(long_text, max_length=40)
    assert len(formatted) <= 40
    assert formatted.endswith("…")


@pytest.mark.asyncio
async def test_in_memory_event_broker_lifecycle():
    broker = InMemoryDialogEventBroker(queue_size=2)
    dialog_id = uuid4()

    sub = await broker.subscribe(dialog_id)
    assert not sub.closed

    # Publish an event
    ev1 = DialogEvent(type=DialogEventType.MESSAGE_START)
    await broker.publish(dialog_id, ev1)

    received = await sub.receive()
    assert received is not None
    assert received.type == DialogEventType.MESSAGE_START

    # Test overflow drop: offer 3 events to queue of size 2
    for _ in range(5):
        await broker.publish(
            dialog_id,
            DialogEvent(type=DialogEventType.MESSAGE_DELTA, delta="chunk"),
        )

    # Overflown subscriber must be automatically closed to prevent backpressure
    assert sub.closed

    # Close dialog
    sub2 = await broker.subscribe(dialog_id)
    await broker.close_dialog(dialog_id)
    closed_ev = await sub2.receive()
    assert closed_ev is None
    assert sub2.closed

    await broker.shutdown()


@pytest.mark.asyncio
async def test_in_memory_history_store():
    store = InMemoryHistoryStore()
    user_a = uuid4()
    user_b = uuid4()

    # Create dialog
    d_id = await store.create_dialog(user_a)

    # Append exchange
    user_msg, asst_msg = await store.append_exchange(
        owner_id=user_a,
        dialog_id=d_id,
        user_content="Болит голова",
        assistant_content="Примите Ибупрофен",
        rag_payload={"sources": []},
        title="Болит голова",
    )
    assert user_msg.position == 1
    assert user_msg.role == "user"
    assert asst_msg.position == 2
    assert asst_msg.role == "assistant"

    # List dialogs
    dialogs_a = await store.list_dialogs(user_a)
    assert len(dialogs_a) == 1
    assert dialogs_a[0].dialog_id == d_id
    assert dialogs_a[0].title == "Болит голова"

    # Transcript
    transcript = await store.get_transcript(user_a, d_id)
    assert len(transcript.messages) == 2

    # User isolation: user B cannot access user A's dialog
    with pytest.raises(DialogNotFoundError):
        await store.get_transcript(user_b, d_id)

    # Delete dialog
    deleted = await store.delete_dialog(user_a, d_id)
    assert deleted is True
    with pytest.raises(DialogNotFoundError):
        await store.get_transcript(user_a, d_id)


@pytest.mark.asyncio
async def test_dialog_service_processing():
    root = Path(__file__).resolve().parents[2]
    pkg_path = root / "data" / "medicines" / "package.yaml"
    analyzer = MorphAnalyzer()
    index = load_package_from_yaml(pkg_path, analyzer)

    history = InMemoryHistoryStore()
    broker = InMemoryDialogEventBroker()
    service = DialogService(
        history_store=history,
        event_broker=broker,
        bm25_index=index,
        analyzer=analyzer,
    )

    user_id = uuid4()
    dialog_id = await service.start_dialog(user_id)

    # Subscribe to events
    sub = await service.subscribe(user_id, dialog_id)

    # Submit query
    await service.submit_message(
        owner_id=user_id,
        dialog_id=dialog_id,
        content="Сильно ломит виски и болит голова",
    )

    # Gather events
    events: list[DialogEvent] = []
    while True:
        ev = await asyncio.wait_for(sub.receive(), timeout=2.0)
        if ev is None:
            break
        events.append(ev)
        if ev.type in (DialogEventType.MESSAGE_END, DialogEventType.MESSAGE_ERROR):
            break

    assert len(events) >= 3
    assert events[0].type == DialogEventType.MESSAGE_START
    assert events[-1].type == DialogEventType.MESSAGE_END
    assert events[-1].emergency_mode is False
    assert events[-1].sources is not None
    assert len(events[-1].sources) > 0

    # Verify database persistence
    transcript = await service.get_transcript(user_id, dialog_id)
    assert len(transcript.messages) == 2
    assert transcript.messages[0].role == "user"
    assert transcript.messages[1].role == "assistant"
    assert (
        "Ибупрофен" in transcript.messages[1].content
        or "Парацетамол" in transcript.messages[1].content
    )

    # Red flag emergency test
    dialog_id_em = await service.start_dialog(user_id)
    sub_em = await service.subscribe(user_id, dialog_id_em)
    await service.submit_message(
        owner_id=user_id,
        dialog_id=dialog_id_em,
        content="Термический ожог кипятком руки",
    )
    em_events = []
    while True:
        ev = await asyncio.wait_for(sub_em.receive(), timeout=2.0)
        if ev is None:
            break
        em_events.append(ev)
        if ev.type in (DialogEventType.MESSAGE_END, DialogEventType.MESSAGE_ERROR):
            break

    assert em_events[-1].emergency_mode is True
    await service.shutdown()


@pytest.mark.asyncio
async def test_dialog_api_http_and_chat_query():
    root = Path(__file__).resolve().parents[2]
    pkg_path = root / "data" / "medicines" / "package.yaml"
    analyzer = MorphAnalyzer()
    index = load_package_from_yaml(pkg_path, analyzer)

    history = InMemoryHistoryStore()
    broker = InMemoryDialogEventBroker()
    service = DialogService(
        history_store=history,
        event_broker=broker,
        bm25_index=index,
        analyzer=analyzer,
    )

    app = create_app(dialog_service=service)

    test_user = User(
        id=uuid4(),
        email="patient@bmstu.ru",
        name="Алексей",
        role=Role.USER,
        avatar_color="#4F46E5",
    )
    app.dependency_overrides[get_current_user] = lambda: test_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create dialog
        res_create = await client.post("/api/v1/dialogs")
        assert res_create.status_code == 201
        data_create = res_create.json()
        assert "dialog_id" in data_create
        dialog_id = data_create["dialog_id"]

        # 2. List dialogs
        res_list = await client.get("/api/v1/dialogs")
        assert res_list.status_code == 200
        assert len(res_list.json()["dialogs"]) == 1

        # 3. Submit message (202 Accepted)
        res_submit = await client.post(
            f"/api/v1/dialogs/{dialog_id}/messages",
            json={"content": "Сильно болит зуб, ломит челюсть"},
        )
        assert res_submit.status_code == 202

        # Await the background chain task to complete
        task = service._dialog_chains.get(UUID(dialog_id))
        if task:
            await task

        # 4. Get messages transcript
        res_msgs = await client.get(f"/api/v1/dialogs/{dialog_id}/messages")
        assert res_msgs.status_code == 200
        data_msgs = res_msgs.json()
        assert len(data_msgs["messages"]) == 2
        assert data_msgs["messages"][0]["role"] == "user"
        assert data_msgs["messages"][1]["role"] == "assistant"

        # 5. Delete dialog
        res_del = await client.delete(f"/api/v1/dialogs/{dialog_id}")
        assert res_del.status_code == 204

        # 6. Verify 404 after deletion
        res_not_found = await client.get(f"/api/v1/dialogs/{dialog_id}/messages")
        assert res_not_found.status_code == 404

        # 7. Synchronous /chat/query endpoint
        res_chat = await client.post(
            "/api/v1/chat/query",
            json={"query": "головная боль, мигрень", "include_kit_context": True},
        )
        assert res_chat.status_code == 200
        data_chat = res_chat.json()
        assert data_chat["status"] == "success"
        assert data_chat["emergency_mode"] is False
        assert data_chat["recommendation"] is not None
        assert any(
            name in data_chat["recommendation"]["medicine_name"]
            for name in ("Ибупрофен", "Парацетамол", "Пенталгин")
        )

        # 8. Synchronous /chat/query with Red Flags
        res_red_flag = await client.post(
            "/api/v1/chat/query",
            json={
                "query": "сильное артериальное кровотечение",
                "include_kit_context": True,
            },
        )
        assert res_red_flag.status_code == 200
        data_rf = res_red_flag.json()
        assert data_rf["emergency_mode"] is True
        assert "112" in data_rf["message"]

        # 9. Out-of-Domain Guardrail (e.g. blini)
        res_blini = await client.post(
            "/api/v1/chat/query",
            json={"query": "как готовить тонкие блины на молоке?"},
        )
        assert res_blini.status_code == 200
        data_blini = res_blini.json()
        assert data_blini["status"] == "out_of_domain"
        assert data_blini["recommendation"] is None
        assert "кулинарн" in data_blini["message"]

        # 10. Question about attached pill from kit
        res_pill = await client.post(
            "/api/v1/chat/query",
            json={"query": "что это", "selected_pills": ["Парацетамол"]},
        )
        assert res_pill.status_code == 200
        data_pill = res_pill.json()
        assert data_pill["status"] == "success"
        assert data_pill["recommendation"] is not None
        assert "Парацетамол" in data_pill["recommendation"]["medicine_name"]
