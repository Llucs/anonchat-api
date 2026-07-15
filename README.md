# anonchat-api

Unofficial ChatGPT guest mode API — **não precisa de login, não precisa de chave, não precisa de conta**. Compatível com o formato OpenAI.

Usa o modo anônimo do `chatgpt.com` (guest mode) com resolução automática de Turnstile + Proof-of-Work. Nada de simulado — as informações (modelo, tokens) vêm diretamente do servidor.

---

## Funcionalidades

- **Sem conta, sem login, sem chave**
- **Formato OpenAI** (`/v1/chat/completions`) — funciona com qualquer SDK OpenAI
- **Modelo real** — extraído dinamicamente do servidor (`server_ste_metadata.model_slug`)
- **Tokens reais** — contados via `tiktoken` (o200k_base)
- **Streaming** (`stream: true/false`)
- **Proxy** — útil se seu IP for flagado
- **CLI direto** — use sem ligar servidor nenhum
- **Servidor HTTP** — FastAPI, pronto pra deploy com Docker

---

## CLI (sem servidor)

```bash
# Mensagem direta
anonchat "Qual a capital do Brasil?"

# Saída JSON (modelo + texto)
anonchat --json "Explain quantum computing in one sentence"

# Streaming (printa caractere por caractere)
anonchat --stream "Write a short poem"

# Com proxy
anonchat --proxy http://user:pass@ip:port "Hello"

# Pipe-friendly
echo "Count to 10" | anonchat --json
```

### Argumentos

| Flag | Descrição |
|------|-----------|
| `--json` | Saída em JSON (model, text) |
| `--stream` | Printa conforme chega |
| `--proxy` | Proxy HTTP (formato `http://user:pass@ip:port`) |
| `--model` | Modelo (sempre `auto`, o servidor decide) |
| `--temperature`, `--top-p`, `--max-tokens`, `--seed` | Aceitos (enviados ao servidor quando possível) |

---

## Servidor HTTP

```bash
# Direto
pip install -r requirements.txt
python app.py

# Docker
docker build -t anonchat-api .
docker run -p 8000:8000 anonchat-api
```

### Endpoints

#### `POST /v1/chat/completions`

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false,
    "proxy": null
  }'
```

Resposta:

```json
{
  "id": "chatcmpl-a1b2c3d4e5f6g7h8",
  "object": "chat.completion",
  "created": 1700000000,
  "model": "gpt-5-5",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help you today?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 5,
    "completion_tokens": 10,
    "total_tokens": 15
  }
}
```

#### `GET /v1/models`

```bash
curl http://localhost:8000/v1/models
```

Retorna `auto` + todos os modelos já vistos em respostas do servidor.

#### `GET /health`

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

### Com SDK OpenAI

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="x")

resp = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Hello"}],
)

print(resp.model)         # gpt-5-5 (dinâmico)
print(resp.choices[0].message.content)
print(resp.usage)
```

Streaming também funciona:

```python
stream = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")
```

### Parâmetros aceitos

| Parâmetro | Tipo | Padrão |
|-----------|------|--------|
| `messages` | `array` | obrigatório |
| `model` | `string` | `"auto"` |
| `stream` | `boolean` | `false` |
| `proxy` | `string \| null` | `null` |
| `temperature` | `float \| null` | — |
| `top_p` | `float \| null` | — |
| `n` | `int \| null` | — |
| `max_tokens` / `max_completion_tokens` | `int \| null` | — |
| `stop` | `string \| array \| null` | — |
| `frequency_penalty` | `float \| null` | — |
| `presence_penalty` | `float \| null` | — |
| `seed` | `int \| null` | — |
| `user` | `string \| null` | — |

> Nota: o ChatGPT guest mode ignora muitos desses parâmetros (o servidor decide tudo). Eles estão aqui para compatibilidade com SDKs.

---

## Como funciona

1. Abre sessão anônima em `chatgpt.com` (sem cookies de login)
2. Resolve **Turnstile** (Cloudflare) + **Proof-of-Work** automaticamente
3. Envia a mensagem para `backend-anon/f/conversation`
4. Extrai a resposta + `model_slug` do stream SSE
5. Conta tokens com `tiktoken` (encoding real do modelo)

---

## Proxy

Se o IP for flagado:

```bash
anonchat --proxy http://user:pass@ip:8080 "message"

# Ou na API:
curl -X POST ... -d '{"proxy": "http://user:pass@ip:8080", ...}'
```

---

## Dependências

**Mínimas** (CLI):

```
curl_cffi    → TLS fingerprint Chrome (essencial)
esprima      → Parser JS para resolver Turnstile
```

**Opcionais** (servidor HTTP):

```
fastapi, uvicorn, pydantic  → API server
tiktoken                     → contagem precisa de tokens
Pillow                       → upload de imagens
```

O CLI funciona com `pip install curl_cffi esprima` apenas.

## Docker

```bash
docker build -t anonchat-api .
docker run -d --name anonchat -p 8000:8000 --restart unless-stopped anonchat-api
```

---

## Notas

- O modelo retornado é **sempre o que o servidor escolheu** — não tem como forçar um modelo específico no guest mode
- Tokens de raciocínio/reasoning são detectados se o servidor retornar (blocos ` `)
- O IP pode ser flagado após várias requisições — use proxy rotation se for usar em produção
- Nada é hardcoded: modelo, tokens, tudo vem do servidor em tempo real
