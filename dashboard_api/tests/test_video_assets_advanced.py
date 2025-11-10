import io
import json


def _fake_mp4_bytes(name: str = "a.mp4") -> tuple[str, io.BytesIO, str]:
  content = b"\x00\x00\x00 ftypisom\x00\x00\x02\x00isomiso2avc1mp41"
  return (name, io.BytesIO(content), "video/mp4")


def test_multi_upload_and_list_sorting(client, auth_headers):
  files = [
    ("files", _fake_mp4_bytes("zeta.mp4")),
    ("files", _fake_mp4_bytes("alpha.mp4")),
    ("files", _fake_mp4_bytes("beta.mp4")),
  ]
  data = {"tags": json.dumps(["batch", "test"])}
  r = client.post("/api/v1/assets", headers=auth_headers, files=files, data=data)
  assert r.status_code == 201, r.text
  body = r.json()
  assert "items" in body and len(body["items"]) == 3

  # Sorting by filename asc
  r = client.get("/api/v1/assets", headers=auth_headers, params={"sort": "filename", "direction": "asc", "limit": 10})
  assert r.status_code == 200
  names = [it["filename"] for it in r.json()["items"]]
  assert names == sorted(names)


def test_batch_tags_and_delete(client, auth_headers):
  # Upload two files
  ids = []
  for n in ["one.mp4", "two.mp4"]:
    r = client.post(
      "/api/v1/assets",
      headers=auth_headers,
      files={"file": _fake_mp4_bytes(n)},
      data={"tags": json.dumps(["x"])},
    )
    assert r.status_code == 201
    ids.append(r.json()["id"])

  # Add tags to both
  r = client.post("/api/v1/assets/batch/tags", headers=auth_headers, json={"ids": ids, "add": ["y", "z"]})
  assert r.status_code == 200
  # Verify
  for _id in ids:
    ri = client.get(f"/api/v1/assets/{_id}", headers=auth_headers)
    assert set(ri.json()["tags"]) >= {"x", "y", "z"}

  # Replace tags
  r = client.post("/api/v1/assets/batch/tags", headers=auth_headers, json={"ids": ids, "replace": ["solo"]})
  assert r.status_code == 200
  for _id in ids:
    ri = client.get(f"/api/v1/assets/{_id}", headers=auth_headers)
    assert ri.json()["tags"] == ["solo"]

  # Batch delete
  r = client.post("/api/v1/assets/batch/delete", headers=auth_headers, json={"ids": ids})
  assert r.status_code == 200
  results = r.json()["results"]
  assert all(item["success"] for item in results)


