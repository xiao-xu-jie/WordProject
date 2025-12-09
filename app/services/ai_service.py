"""
AI Service for data cleaning and content enrichment using LLM APIs.
"""
import logging
import json
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from app.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-powered data cleaning and content enrichment."""

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize AI service.

        Args:
            provider: AI provider ('openai' or 'anthropic')
            model: Model name (if None, uses default for provider)
            api_key: API key (if None, uses from settings)
        """
        self.provider = provider.lower()

        if self.provider == "openai":
            self.model = model or "gpt-4o-mini"
            api_key = api_key or settings.OPENAI_API_KEY
            self.client = AsyncOpenAI(api_key=api_key)
        elif self.provider == "anthropic":
            self.model = model or "claude-3-haiku-20240307"
            api_key = api_key or settings.ANTHROPIC_API_KEY
            self.client = AsyncAnthropic(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        logger.info(f"AI Service initialized with provider={provider}, model={self.model}")

    async def clean_ocr_data(
        self,
        ocr_text: str,
        context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Clean and structure OCR text into vocabulary entries.

        Args:
            ocr_text: Raw OCR text output
            context: Additional context about the source (e.g., "CET-4 vocabulary book")

        Returns:
            List of structured word entries with fields:
                - spelling: Word spelling
                - phonetic: Phonetic transcription
                - definitions: List of definitions with part of speech
                - sentences: Example sentences (if available in OCR)
                - tags: Relevant tags

        Raises:
            Exception: If API call fails
        """
        prompt = self._build_cleaning_prompt(ocr_text, context)

        try:
            if self.provider == "openai":
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert at extracting and structuring vocabulary data from OCR text. Always respond with valid JSON."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content

            elif self.provider == "anthropic":
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=0.1,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                content = response.content[0].text

            # Parse JSON response
            result = json.loads(content)
            words = result.get("words", [])

            logger.info(f"Cleaned OCR data: extracted {len(words)} words")
            return words

        except Exception as e:
            logger.error(f"Error cleaning OCR data: {str(e)}")
            raise

    async def enrich_word(
        self,
        word: str,
        existing_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enrich a word with AI-generated content (examples, mnemonics).

        Args:
            word: The word to enrich
            existing_data: Existing word data (definitions, etc.)

        Returns:
            Dictionary with enriched content:
                - sentences: List of example sentences (bilingual)
                - mnemonic: Memory technique/mnemonic
                - usage_notes: Usage notes and tips

        Raises:
            Exception: If API call fails
        """
        prompt = self._build_enrichment_prompt(word, existing_data)

        try:
            if self.provider == "openai":
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert English teacher creating engaging learning materials. Always respond with valid JSON."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content

            elif self.provider == "anthropic":
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    temperature=0.7,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                content = response.content[0].text

            # Parse JSON response
            enriched_data = json.loads(content)

            logger.info(f"Enriched word: {word}")
            return enriched_data

        except Exception as e:
            logger.error(f"Error enriching word {word}: {str(e)}")
            raise

    async def batch_enrich_words(
        self,
        words: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Enrich multiple words concurrently.

        Args:
            words: List of word dictionaries to enrich
            max_concurrent: Maximum number of concurrent API calls

        Returns:
            List of enriched word dictionaries
        """
        import asyncio

        async def enrich_single(word_data: Dict[str, Any]) -> Dict[str, Any]:
            try:
                spelling = word_data.get("spelling", "")
                enriched = await self.enrich_word(spelling, word_data)
                return {**word_data, **enriched}
            except Exception as e:
                logger.error(f"Failed to enrich {word_data.get('spelling')}: {str(e)}")
                return word_data

        # Process in batches to respect rate limits
        results = []
        for i in range(0, len(words), max_concurrent):
            batch = words[i:i + max_concurrent]
            batch_results = await asyncio.gather(*[enrich_single(w) for w in batch])
            results.extend(batch_results)

        logger.info(f"Batch enriched {len(results)} words")
        return results

    def _build_cleaning_prompt(self, ocr_text: str, context: Optional[str]) -> str:
        """Build prompt for OCR data cleaning."""
        context_str = f"\n\nContext: {context}" if context else ""

        return f"""Extract vocabulary words from the following OCR text and structure them as JSON.

OCR Text:
{ocr_text}{context_str}

Instructions:
1. Identify all vocabulary words in the text
2. Extract spelling, phonetic transcription, and definitions
3. Group multiple definitions by part of speech (pos)
4. Extract example sentences if available
5. Infer appropriate tags (e.g., "cet4", "toefl", "business")

Output format (JSON):
{{
  "words": [
    {{
      "spelling": "decorate",
      "phonetic": "/ˈdekəreɪt/",
      "definitions": [
        {{"pos": "vt", "cn": "装饰; 点缀", "en": "make something look more attractive"}},
        {{"pos": "n", "cn": "勋章", "en": "medal"}}
      ],
      "sentences": [
        {{"en": "They decorated the room with flowers.", "cn": "他们用花装饰了房间。"}}
      ],
      "tags": ["cet4", "common"]
    }}
  ]
}}

Important:
- Only include words that are clearly vocabulary entries
- Skip page numbers, headers, and irrelevant text
- Ensure all JSON is valid and properly formatted
- If phonetic is unclear, use empty string
- If no example sentences, use empty array"""

    def _build_enrichment_prompt(
        self,
        word: str,
        existing_data: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for word enrichment."""
        definitions_str = ""
        if existing_data and "definitions" in existing_data:
            defs = existing_data["definitions"]
            definitions_str = "\n".join([
                f"- {d.get('pos', '')}: {d.get('cn', '')} ({d.get('en', '')})"
                for d in defs
            ])

        return f"""Generate engaging learning materials for the English word "{word}".

{f"Existing definitions:\n{definitions_str}\n" if definitions_str else ""}

Please provide:

1. **Example Sentences** (2-3 sentences):
   - Use the word in realistic, college-level contexts
   - Provide both English and Chinese translations
   - Make them memorable and practical

2. **Mnemonic** (memory technique):
   - Use root/affix analysis if applicable
   - Or create a vivid association/story
   - Keep it concise and memorable
   - Explain in Chinese for better understanding

3. **Usage Notes** (optional):
   - Common collocations
   - Usage tips or common mistakes
   - Register (formal/informal)

Output format (JSON):
{{
  "sentences": [
    {{"en": "The artist decorated the gallery with her paintings.", "cn": "艺术家用她的画作装饰了画廊。"}},
    {{"en": "We need to decorate the house before the party.", "cn": "我们需要在派对前装饰房子。"}}
  ],
  "mnemonic": "de(加强) + cor(心) + ate → 用心装饰。想象用心装饰一个房间,让它变得更美。",
  "usage_notes": "常与 with 搭配使用,如 decorate with flowers。正式和非正式场合都可使用。"
}}

Make the content engaging, accurate, and helpful for Chinese learners of English."""

    async def validate_word_data(
        self,
        word_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate and correct word data using AI.

        Args:
            word_data: Word dictionary to validate

        Returns:
            Validated and corrected word data
        """
        prompt = f"""Review and correct the following vocabulary entry if needed:

{json.dumps(word_data, ensure_ascii=False, indent=2)}

Check for:
1. Spelling accuracy
2. Phonetic transcription correctness
3. Definition accuracy
4. Example sentence quality
5. Appropriate tags

Return the corrected version in the same JSON format. If everything is correct, return the original data."""

        try:
            if self.provider == "openai":
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert English teacher validating vocabulary data. Always respond with valid JSON."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content

            elif self.provider == "anthropic":
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    temperature=0.1,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                content = response.content[0].text

            validated_data = json.loads(content)
            logger.info(f"Validated word: {word_data.get('spelling')}")
            return validated_data

        except Exception as e:
            logger.error(f"Error validating word data: {str(e)}")
            return word_data  # Return original if validation fails


# Singleton instance
_ai_service: Optional[AIService] = None


def get_ai_service(
    provider: str = "openai",
    model: Optional[str] = None
) -> AIService:
    """
    Get or create AI service singleton.

    Args:
        provider: AI provider ('openai' or 'anthropic')
        model: Model name

    Returns:
        AIService instance
    """
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService(provider=provider, model=model)
    return _ai_service
