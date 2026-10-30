from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import postgres_only
from tests.helpers import CLIP, FAKE_JPEG, FAKE_WEBM, SNAPSHOT, create_camera, create_event, media_files

BUG_UTC_SUFFIX = "Pydantic serialises UTC as Z, the contract says +00:00"
BASE_TIME = datetime(2026, 10, 29, 14, 0, tzinfo=timezone.utc)


def minutes_after(minutes):
    return (BASE_TIME + timedelta(minutes=minutes)).isoformat()


def list_events(client, owner, **params):
    response = client.get("/events", params=params, headers=owner["headers"])
    assert response.status_code == 200
    return response.json()


def review(client, headers, event_id, status):
    return client.post(f"/events/{event_id}/review", json={"status": status}, headers=headers)


def test_list_events_is_empty_at_first(client, owner):
    assert list_events(client, owner) == {"items": [], "total": 0}


def test_get_event_returns_it(client, owner, camera):
    event = create_event(client, owner, camera["id"])

    response = client.get(f"/events/{event['id']}", headers=owner["headers"])

    assert response.status_code == 200
    assert response.json()["id"] == event["id"]
    assert response.json()["camera_name"] == "Entrance"


def test_get_unknown_event_is_404(client, owner):
    assert client.get("/events/99999", headers=owner["headers"]).status_code == 404


def test_event_flow_from_agent_to_review(client, owner, camera):
    event = create_event(client, owner, camera["id"], clip=CLIP, snapshot=SNAPSHOT)
    url = f"/events/{event['id']}"

    assert [e["id"] for e in list_events(client, owner, status="pending")["items"]] == [event["id"]]
    assert client.get(f"{url}/clip", headers=owner["headers"]).content == FAKE_WEBM
    assert client.get(f"{url}/snapshot", headers=owner["headers"]).content == FAKE_JPEG

    reviewed = review(client, owner["headers"], event["id"], "dismissed")

    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "dismissed"
    assert reviewed.json()["reviewed_by"] == client.get("/auth/me", headers=owner["headers"]).json()["id"]
    assert reviewed.json()["reviewed_at"] is not None
    assert list_events(client, owner, status="pending")["items"] == []


def test_review_confirmed_is_saved(client, owner, camera):
    event = create_event(client, owner, camera["id"])

    review(client, owner["headers"], event["id"], "confirmed")

    assert client.get(f"/events/{event['id']}", headers=owner["headers"]).json()["status"] == "confirmed"


def test_review_again_changes_status_and_time(client, owner, camera):
    event = create_event(client, owner, camera["id"])
    first = review(client, owner["headers"], event["id"], "dismissed").json()

    second = review(client, owner["headers"], event["id"], "confirmed").json()

    assert second["status"] == "confirmed"
    assert datetime.fromisoformat(second["reviewed_at"]) > datetime.fromisoformat(first["reviewed_at"])


def test_review_unknown_event_is_404(client, owner):
    assert review(client, owner["headers"], 99999, "confirmed").status_code == 404


def test_events_are_newest_first_by_started_at(client, owner, camera):
    late = create_event(client, owner, camera["id"], started_at=minutes_after(10))
    early = create_event(client, owner, camera["id"], started_at=minutes_after(0))
    middle = create_event(client, owner, camera["id"], started_at=minutes_after(5))

    ids = [e["id"] for e in list_events(client, owner)["items"]]

    assert ids == [late["id"], middle["id"], early["id"]]


def test_events_with_same_time_are_newest_id_first(client, owner, camera):
    first = create_event(client, owner, camera["id"])
    second = create_event(client, owner, camera["id"])

    ids = [e["id"] for e in list_events(client, owner)["items"]]

    assert ids == [second["id"], first["id"]]


def test_after_id_returns_only_newer_events(client, owner, camera):
    first = create_event(client, owner, camera["id"])
    second = create_event(client, owner, camera["id"])

    body = list_events(client, owner, after_id=first["id"])

    assert [e["id"] for e in body["items"]] == [second["id"]]
    assert body["total"] == 1


def test_pagination_returns_requested_page_and_full_total(client, owner, camera):
    ids = [create_event(client, owner, camera["id"], started_at=minutes_after(i))["id"] for i in range(5)]

    body = list_events(client, owner, limit=2, offset=2)

    assert [e["id"] for e in body["items"]] == [ids[2], ids[1]]
    assert body["total"] == 5


def test_offset_past_the_end_returns_no_items(client, owner, camera):
    create_event(client, owner, camera["id"])

    body = list_events(client, owner, offset=10)

    assert body["items"] == []
    assert body["total"] == 1


def test_limit_accepts_upper_bound(client, owner):
    assert list_events(client, owner, limit=200)["total"] == 0


def test_camera_id_filter_returns_only_that_camera(client, owner, camera):
    other = create_camera(client, owner, name="Other")
    create_event(client, owner, camera["id"])
    wanted = create_event(client, owner, other["id"])

    body = list_events(client, owner, camera_id=other["id"])

    assert [e["id"] for e in body["items"]] == [wanted["id"]]
    assert body["total"] == 1


def test_status_filter_counts_only_matching(client, owner, camera):
    event = create_event(client, owner, camera["id"])
    create_event(client, owner, camera["id"])
    review(client, owner["headers"], event["id"], "confirmed")

    assert list_events(client, owner, status="confirmed")["total"] == 1
    assert list_events(client, owner, status="pending")["total"] == 1
    assert list_events(client, owner, status="dismissed")["total"] == 0


def test_filters_combine(client, owner, camera):
    other = create_camera(client, owner, name="Other")
    first = create_event(client, owner, camera["id"])
    create_event(client, owner, other["id"])
    wanted = create_event(client, owner, camera["id"])

    body = list_events(client, owner, status="pending", camera_id=camera["id"], after_id=first["id"])

    assert [e["id"] for e in body["items"]] == [wanted["id"]]


def test_clip_of_event_without_clip_is_404(client, owner, camera):
    event = create_event(client, owner, camera["id"])

    assert client.get(f"/events/{event['id']}/clip", headers=owner["headers"]).status_code == 404


def test_snapshot_of_event_without_snapshot_is_404(client, owner, camera):
    event = create_event(client, owner, camera["id"])

    assert client.get(f"/events/{event['id']}/snapshot", headers=owner["headers"]).status_code == 404


def test_clip_missing_on_disk_is_404(client, owner, camera):
    event = create_event(client, owner, camera["id"], clip=CLIP)
    media_files()[0].unlink()

    assert client.get(f"/events/{event['id']}/clip", headers=owner["headers"]).status_code == 404


def test_clip_has_video_content_type(client, owner, camera):
    event = create_event(client, owner, camera["id"], clip=CLIP)

    response = client.get(f"/events/{event['id']}/clip", headers=owner["headers"])

    assert response.headers["content-type"] == "video/webm"


def test_clip_and_snapshot_of_unknown_event_are_404(client, owner):
    assert client.get("/events/99999/clip", headers=owner["headers"]).status_code == 404
    assert client.get("/events/99999/snapshot", headers=owner["headers"]).status_code == 404


def response_timestamps(client, owner, camera):
    event = create_event(client, owner, camera["id"])
    reviewed = review(client, owner["headers"], event["id"], "confirmed").json()
    me = client.get("/auth/me", headers=owner["headers"]).json()
    store = client.get("/stores/me", headers=owner["headers"]).json()
    return [reviewed["started_at"], reviewed["reviewed_at"], reviewed["created_at"],
            me["created_at"], store["created_at"], camera["created_at"]]


def test_timestamps_are_utc(client, owner, camera):
    values = response_timestamps(client, owner, camera)

    assert all(datetime.fromisoformat(value).utcoffset() == timedelta(0) for value in values), values


@pytest.mark.xfail(reason=BUG_UTC_SUFFIX)
def test_timestamps_end_with_utc_offset(client, owner, camera):
    values = response_timestamps(client, owner, camera)

    assert all(value.endswith("+00:00") for value in values), values


@postgres_only
def test_started_at_with_offset_keeps_the_same_moment(client, owner, camera):
    event = create_event(client, owner, camera["id"], started_at="2026-10-29T14:03:12+05:00")

    assert datetime.fromisoformat(event["started_at"]) == datetime(2026, 10, 29, 9, 3, 12, tzinfo=timezone.utc)


