"""Terceira etapa: salvar e recarregar mensagens usando SQLite."""

import json
import sqlite3
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


ENDPOINT = "http://localhost:11434/api/chat"
MODEL = "qwen3.5:4b-q4_K_M"
INSTRUCAO = (
    "Responda em português, de forma direta. "
    "Não acrescente detalhes que não sejam necessários à pergunta."
)
CAMINHO_BANCO = Path(__file__).with_name("conversa.db")
MAX_MENSAGENS_NO_CONTEXTO = 12


def abrir_banco() -> sqlite3.Connection:
    banco = sqlite3.connect(CAMINHO_BANCO)
    banco.execute(
        """
        CREATE TABLE IF NOT EXISTS mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    banco.commit()
    return banco


def carregar_historico(banco: sqlite3.Connection) -> list[dict[str, str]]:
    linhas = banco.execute(
        "SELECT role, content FROM mensagens ORDER BY id DESC LIMIT ?",
        (MAX_MENSAGENS_NO_CONTEXTO,),
    ).fetchall()
    linhas.reverse()
    return [{"role": role, "content": content} for role, content in linhas]


def salvar_troca(
    banco: sqlite3.Connection, pergunta: str, resposta: str
) -> None:
    with banco:
        banco.executemany(
            "INSERT INTO mensagens (role, content) VALUES (?, ?)",
            [("user", pergunta), ("assistant", resposta)],
        )


def perguntar(historico: list[dict[str, str]]) -> str:
    mensagens = [{"role": "system", "content": INSTRUCAO}, *historico]
    dados = {
        "model": MODEL,
        "messages": mensagens,
        "think": False,
        "stream": False,
        "options": {"num_ctx": 4096},
    }

    requisicao = Request(
        ENDPOINT,
        data=json.dumps(dados).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(requisicao, timeout=180) as resposta:
        resultado = json.loads(resposta.read().decode("utf-8"))

    return resultado["message"]["content"]


def main() -> None:
    banco = abrir_banco()
    historico = carregar_historico(banco)
    print("IA local pronta. Digite /sair para encerrar a conversa.")
    print(f"Histórico carregado: {len(historico)} mensagens.\n")

    try:
        while True:
            texto = input("Você: ").strip()
            if texto.lower() == "/sair":
                print("Conversa encerrada.")
                break
            if not texto:
                continue

            historico.append({"role": "user", "content": texto})

            try:
                resposta = perguntar(historico)
            except URLError as erro:
                historico.pop()
                print("Não consegui acessar o Ollama local. Confira se ele está aberto.")
                print(f"Detalhe: {erro}\n")
                continue

            salvar_troca(banco, texto, resposta)
            print(f"IA: {resposta}\n")
            historico.append({"role": "assistant", "content": resposta})
            historico = historico[-MAX_MENSAGENS_NO_CONTEXTO:]
    finally:
        banco.close()


if __name__ == "__main__":
    main()
