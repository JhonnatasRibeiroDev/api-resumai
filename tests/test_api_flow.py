import fitz
from fastapi.testclient import TestClient


def make_pdf_bytes(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


def auth_headers(client: TestClient) -> dict[str, str]:
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Maria Silva",
            "username": "maria",
            "email": "maria@example.com",
            "password": "senha-segura",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "maria@example.com", "password": "senha-segura"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def upload_pdf(client: TestClient, headers: dict[str, str], name: str, text: str) -> str:
    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": (name, make_pdf_bytes(text), "application/pdf")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == name
    assert body["extraction_status"] == "completed"
    assert body["summary_status"] == "pending"
    return body["id"]


def test_full_api_flow(client: TestClient) -> None:
    headers = auth_headers(client)

    me_response = client.get("/api/v1/users/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "maria"

    first_document_id = upload_pdf(
        client,
        headers,
        "primeiro.pdf",
        "Este é o primeiro documento sobre inteligência artificial.",
    )
    second_document_id = upload_pdf(
        client,
        headers,
        "segundo.pdf",
        "Este é o segundo documento sobre análise de textos.",
    )

    documents_response = client.get("/api/v1/documents", headers=headers)
    assert documents_response.status_code == 200
    assert len(documents_response.json()) == 2

    summary_response = client.post(
        f"/api/v1/documents/{first_document_id}/summarize",
        headers=headers,
    )
    assert summary_response.status_code == 201
    summary_body = summary_response.json()
    assert summary_body["document_id"] == first_document_id
    assert "Resumo fake" in summary_body["content"]

    get_summary_response = client.get(
        f"/api/v1/documents/{first_document_id}/summary",
        headers=headers,
    )
    assert get_summary_response.status_code == 200

    integrated_response = client.post(
        "/api/v1/summaries/integrated",
        headers=headers,
        json={
            "title": "Síntese geral",
            "document_ids": [first_document_id, second_document_id],
        },
    )
    assert integrated_response.status_code == 201
    assert integrated_response.json()["title"] == "Síntese geral"

    dashboard_response = client.get("/api/v1/dashboard", headers=headers)
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["total_documents"] == 2
    assert dashboard["total_individual_summaries"] == 1
    assert dashboard["total_integrated_summaries"] == 1


def test_rejects_non_pdf_upload(client: TestClient) -> None:
    headers = auth_headers(client)

    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("nota.txt", b"conteudo", "text/plain")},
    )

    assert response.status_code == 415
