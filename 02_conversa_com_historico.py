"""Segunda etapa: manter o contexto enquanto esta conversa estiver aberta."""

import json
from urllib.error import URLError
from urllib.request import Request, urlopen


ENDPOINT = "http://localhost:11434/api/chat"
MODEL = "qwen3.5:4b-q4_K_M"
INSTRUCAO = (
    "Responda em português, de forma direta. "
    "Não acrescente detalhes que não sejam necessários à pergunta."
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
    historico: list[dict[str, str]] = []
    print("IA local pronta. Digite /sair para encerrar a conversa.\n")

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

        print(f"IA: {resposta}\n")
        historico.append({"role": "assistant", "content": resposta})


if __name__ == "__main__":
    main()
