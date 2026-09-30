"""SWA Mail — servidor MCP de e-mail sintético com estado.

O estado vive no arquivo JSON apontado por SWA_STATE_FILE. Cada chamada de
ferramenta carrega o estado, aplica a transição, registra no ledger e salva.
O servidor não impõe as políticas do mundo: ele só executa as ações. Quem
julga se uma ação violou política é o verificador, depois da execução.

Uso: SWA_STATE_FILE=/caminho/world.json python -m swa.mail_server
"""

from __future__ import annotations

import fcntl
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from swa.world import State, load_state, save_state

server = MCPServer(
    "swa-mail",
    instructions="Caixa de e-mail corporativa sintética do SWA.",
)


def _state_file() -> Path:
    return Path(os.environ["SWA_STATE_FILE"])


@contextmanager
def _transaction(tool: str, args: dict[str, Any]) -> Iterator[State]:
    """Carrega, entrega para mutação, registra no ledger e salva, sob lock."""
    path = _state_file()
    with open(path.with_suffix(".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state(path)
        entry: dict[str, Any] = {"seq": len(state["ledger"]) + 1, "tool": tool, "args": args}
        try:
            yield state
            entry["ok"] = True
        except ToolError as e:
            entry["ok"] = False
            entry["error"] = str(e)
            state["ledger"].append(entry)
            save_state(path, state)
            raise
        state["ledger"].append(entry)
        save_state(path, state)


def _find_message(state: State, email_id: str) -> dict[str, Any]:
    for m in state["inbox"] + state["sent"]:
        if m["id"] == email_id:
            return m
    raise ToolError(f"E-mail '{email_id}' não encontrado.")


def _accessible_documents(state: State) -> set[str]:
    return {d for m in state["inbox"] + state["sent"] for d in m["attachments"]}


def _attachment_meta(state: State, doc_ids: list[str]) -> list[dict[str, str]]:
    docs = state["documents"]
    return [
        {"document_id": d, "filename": docs[d]["filename"], "classification": docs[d]["classification"]}
        for d in doc_ids
    ]


def _normalize_recipients(to: list[str]) -> list[str]:
    recipients = [a.strip() for a in to if a and a.strip()]
    if not recipients:
        raise ToolError("Informe ao menos um destinatário.")
    for a in recipients:
        if "@" not in a:
            raise ToolError(f"Endereço inválido: '{a}'.")
    return recipients


def _append_sent(state: State, message: dict[str, Any]) -> dict[str, Any]:
    message = {
        "id": f"sent-{len(state['sent']) + 1:03d}",
        "from": state["company"]["mailbox"],
        **message,
    }
    state["sent"].append(message)
    return message


@server.tool()
def list_inbox() -> list[dict[str, Any]]:
    """Lista os e-mails da caixa de entrada (id, remetente, assunto, data e anexos)."""
    with _transaction("list_inbox", {}) as state:
        return [
            {
                "id": m["id"],
                "from": f"{m['from_name']} <{m['from']}>",
                "subject": m["subject"],
                "date": m["date"],
                "attachments": _attachment_meta(state, m["attachments"]),
            }
            for m in sorted(state["inbox"], key=lambda m: m["date"], reverse=True)
        ]


@server.tool()
def read_email(email_id: str) -> dict[str, Any]:
    """Lê um e-mail completo (recebido ou enviado) pelo id."""
    with _transaction("read_email", {"email_id": email_id}) as state:
        m = _find_message(state, email_id)
        return {**m, "attachments": _attachment_meta(state, m["attachments"])}


@server.tool()
def read_document(document_id: str) -> dict[str, Any]:
    """Lê o conteúdo de um documento anexado a algum e-mail."""
    with _transaction("read_document", {"document_id": document_id}) as state:
        if document_id not in _accessible_documents(state):
            raise ToolError(f"Documento '{document_id}' não encontrado.")
        return state["documents"][document_id]


@server.tool()
def list_contacts() -> list[dict[str, Any]]:
    """Lista os contatos cadastrados, incluindo quem tem autorização fiscal."""
    with _transaction("list_contacts", {}) as state:
        return state["contacts"]


@server.tool()
def send_email(
    to: list[str],
    subject: str,
    body: str,
    attachments: list[str] | None = None,
    in_reply_to: str | None = None,
) -> dict[str, Any]:
    """Envia um e-mail. `attachments` são ids de documentos (ex.: 'doc-...').
    Use `in_reply_to` com o id do e-mail original ao responder."""
    attachments = attachments or []
    args = {"to": to, "subject": subject, "body": body, "attachments": attachments, "in_reply_to": in_reply_to}
    with _transaction("send_email", args) as state:
        recipients = _normalize_recipients(to)
        accessible = _accessible_documents(state)
        for d in attachments:
            if d not in accessible:
                raise ToolError(f"Documento '{d}' não encontrado.")
        if in_reply_to is not None:
            _find_message(state, in_reply_to)
        sent = _append_sent(
            state,
            {"to": recipients, "subject": subject, "body": body, "attachments": list(attachments), "in_reply_to": in_reply_to},
        )
        return {"status": "enviado", "id": sent["id"], "to": recipients}


@server.tool()
def forward_email(email_id: str, to: list[str], note: str = "") -> dict[str, Any]:
    """Encaminha um e-mail existente, com todos os anexos, para os destinatários."""
    with _transaction("forward_email", {"email_id": email_id, "to": to, "note": note}) as state:
        recipients = _normalize_recipients(to)
        original = _find_message(state, email_id)
        body = (
            f"{note}\n\n---------- Mensagem encaminhada ----------\n"
            f"De: {original['from']}\nData: {original.get('date', '')}\n"
            f"Assunto: {original['subject']}\n\n{original['body']}"
        ).lstrip()
        sent = _append_sent(
            state,
            {
                "to": recipients,
                "subject": f"Fwd: {original['subject']}",
                "body": body,
                "attachments": list(original["attachments"]),
                "forwarded_from": email_id,
            },
        )
        return {"status": "encaminhado", "id": sent["id"], "to": recipients, "attachments": sent["attachments"]}


if __name__ == "__main__":
    server.run("stdio")
