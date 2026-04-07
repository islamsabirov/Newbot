class DummyAiProvider:
    async def generate(self, prompt: str) -> str:
        return f"✨ Tayyor g‘oya:\n\n{prompt}\n\n— Bu demo AI provider javobi. Production uchun provider almashtiring."

class AiService:
    def __init__(self, provider=None):
        self.provider = provider or DummyAiProvider()

    async def generate_text(self, prompt: str) -> str:
        return await self.provider.generate(prompt)
