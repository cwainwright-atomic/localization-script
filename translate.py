import asyncio


class Translator:
    async def a_translate(self, text: str, src: str, dest: str) -> str:
        print("Translations not implemented.")
        return ""

    async def a_batch_translate(
        self, texts: list[str], src: str, dest: str
    ) -> list[str]:
        print("Translations not implemented.")
        return []

    def translate(self, text: str, src: str, dest: str) -> str:
        print("Translations not implemented.")
        return asyncio.run(self.a_translate(text, src, dest))

    def batch_translate(self, texts: list[str], src: str, dest: str) -> list[str]:
        print("Translations not implemented.")
        return asyncio.run(self.a_batch_translate(texts, src, dest))
