"""Quarta etapa: registrar memórias separadas do histórico de conversa."""

import json
import sqlite3
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


ENDPOINT = "http://localhost:11434/api/chat"
MODEL = "qwen3.5:4b-q4_K_M"
INSTRUCAO = (
    "Responda em português, de forma direta e sem detalhes desnecessários. "
    "As memórias abaixo são dados que o usuário pediu para guardar; "
    "use-as apenas quando forem relevantes."
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
    banco.execute(
        """
        CREATE TABLE IF NOT EXISTS memorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conteudo TEXT NOT NULL,
            criada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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


def carregar_memorias(banco: sqlite3.Connection) -> list[tuple[int, str]]:
    return banco.execute(
        "SELECT id, conteudo FROM memorias ORDER BY id"
    ).fetchall()


def salvar_troca(
    banco: sqlite3.Connection, pergunta: str, resposta: str
) -> None:
    with banco:
        banco.executemany(
            "INSERT INTO mensagens (role, content) VALUES (?, ?)",
            [("user", pergunta), ("assistant", resposta)],
        )


def perguntar(
    historico: list[dict[str, str]], memorias: list[tuple[int, str]]
) -> str:
    if memorias:
        texto_memorias = "\n".join(f"- {conteudo}" for _, conteudo in memorias)
    else:
        texto_memorias = "(nenhuma memória salva)"

    instrucao_com_memorias = (
        f"{INSTRUCAO}\n\nMemórias salvas pelo usuário:\n{texto_memorias}"
    )
    mensagens = [
        {"role": "system", "content": instrucao_com_memorias},
        *historico,
    ]
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


def processar_comando_memoria(texto: str, banco: sqlite3.Connection) -> bool:
    if texto == "/memorias":
        memorias = carregar_memorias(banco)
        if not memorias:
            print("Nenhuma memória salva. Use /lembrar <informação>.\n")
        else:
            print("Memórias salvas:")
            for memoria_id, conteudo in memorias:
                print(f"{memoria_id}. {conteudo}")
            print()
        return True

    if texto == "/lembrar" or texto.startswith("/lembrar "):
        conteudo = texto[len("/lembrar"):].strip()
        if not conteudo:
            print("Use: /lembrar <informação que quer guardar>\n")
        else:
            with banco:
                banco.execute(
                    "INSERT INTO memorias (conteudo) VALUES (?)", (conteudo,)
                )
            print("Memória salva no banco local.\n")
        return True

    if texto == "/esquecer" or texto.startswith("/esquecer "):
        partes = texto.split(maxsplit=1)
        if len(partes) != 2 or not partes[1].isdigit():
            print("Use: /esquecer <número da memória>, mostrado em /memorias.\n")
            return True

        memoria_id = int(partes[1])
        linha = banco.execute(
            "SELECT conteudo FROM memorias WHERE id = ?", (memoria_id,)
        ).fetchone()
        if linha is None:
            print("Não encontrei essa memória.\n")
            return True

        confirmacao = input(
            f"Apagar a memória '{linha[0]}'? Digite s para confirmar: "
        ).strip().lower()
        if confirmacao == "s":
            with banco:
                banco.execute("DELETE FROM memorias WHERE id = ?", (memoria_id,))
            print("Memória apagada.\n")
        else:
            print("Memória mantida.\n")
        return True

    return False


def main() -> None:
    banco = abrir_banco()
    historico = carregar_historico(banco)
    print("IA local pronta. Digite /sair para encerrar.")
    print("Comandos de memória: /lembrar, /memorias e /esquecer.\n")

    try:
        while True:
            texto = input("Você: ").strip()
            if texto.lower() == "/sair":
                print("Conversa encerrada.")
                break
            if not texto:
                continue
            if processar_comando_memoria(texto, banco):
                continue

            historico.append({"role": "user", "content": texto})

            try:
                resposta = perguntar(historico, carregar_memorias(banco))
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
