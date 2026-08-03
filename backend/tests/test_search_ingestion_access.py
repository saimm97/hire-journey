"""The public HTTP interface must not expose global job ingestion."""


async def test_authenticated_user_cannot_trigger_global_ingestion(client):
    response = await client.post("/api/v1/search/run")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
