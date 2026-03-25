import anthropic

api_key = "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"

client = anthropic.Anthropic(api_key=api_key)

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Say hello in Hindi and English"}
    ]
)

print(message.content[0].text)