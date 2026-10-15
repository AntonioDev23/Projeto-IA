"""Primeiro experimento: enviar uma pergunta ao modelo Ollama local."""

import json
from urllib.error import URLError
from urllib.request import Request, urlopen


ENDPOINT = "http://localhost:11434/api/chat"
MODEL = "qwen3.5:4b-q4_K_M"


def perguntar(texto: str) -> str:
    dados = {
        "model": MODEL,
        "messages": [{"role": "user", "content": texto}],
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
    texto = input("Você: ").strip()
    if not texto:
        print("Digite uma pergunta para continuar.")
        return

    try:
        resposta = perguntar(texto)
        print(f"IA: {resposta}")
    except URLError as erro:
        print("Não consegui acessar o Ollama local. Confira se ele está aberto.")
        print(f"Detalhe: {erro}")


if __name__ == "__main__":
    main()
