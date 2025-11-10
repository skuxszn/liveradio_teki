"""Tests for assets API."""

import io
import json

def test_upload_list_update_delete_asset(client, auth_headers):
    # Upload a fake mp4
    content = b"\x00\x00\x00 ftypisom\x00\x00\x02\x00isomiso2avc1mp41"  # minimal header-ish
    files = {"file": ("test_video.mp4", io.BytesIO(content), "video/mp4")}
    data = {"tags": json.dumps(["intro", "promo"])}
    r = client.post("/api/v1/assets", headers=auth_headers, files=files, data=data)
    assert r.status_code == 201, r.text
    asset = r.json()
    asset_id = asset["id"]
    assert asset["filename"].endswith(".mp4")
    assert asset["tags"] == ["intro", "promo"]

    # List with pagination and search
    r = client.get("/api/v1/assets", headers=auth_headers, params={"page": 1, "limit": 10, "search": "intro"})
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and "pagination" in body
    assert any(i["id"] == asset_id for i in body["items"])

    # Update filename and tags
    r = client.put(
        f"/api/v1/assets/{asset_id}",
        headers=auth_headers,
        json={"filename": "renamed_test_video.mp4", "tags": ["updated"]},
    )
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["filename"].startswith("renamed_test_video")
    assert updated["tags"] == ["updated"]

    # Get by id
    r = client.get(f"/api/v1/assets/{asset_id}", headers=auth_headers)
    assert r.status_code == 200
    fetched = r.json()
    assert fetched["id"] == asset_id

    # Delete by id
    r = client.delete(f"/api/v1/assets/id/{asset_id}", headers=auth_headers)
    assert r.status_code in (200, 204)



