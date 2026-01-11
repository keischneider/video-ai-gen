"""
Multi-engine Text-to-Speech client supporting:
- gTTS (Google Text-to-Speech, online)
- edge-tts (Microsoft Edge TTS, online)
"""
import os
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class TTSEngine(str, Enum):
    """Available TTS engines"""
    GTTS = "gtts"
    EDGE_TTS = "edge-tts"


class BaseTTSEngine(ABC):
    """Abstract base class for TTS engines"""

    @abstractmethod
    def synthesize(self, text: str, output_path: str, **kwargs) -> str:
        """Synthesize speech from text and save to file"""
        pass

    @abstractmethod
    def list_voices(self) -> List[Dict[str, Any]]:
        """List available voices for this engine"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name"""
        pass


class GTTSEngine(BaseTTSEngine):
    """Google Text-to-Speech (online, free)"""

    def __init__(self):
        try:
            import gtts
            self._gtts = gtts
        except ImportError:
            raise ImportError("gTTS not installed. Run: pip install gTTS")

    @property
    def name(self) -> str:
        return "gTTS"

    def synthesize(
        self,
        text: str,
        output_path: str,
        lang: str = "en",
        tld: str = "com",
        slow: bool = False,
        **kwargs
    ) -> str:
        """
        Synthesize speech using Google TTS

        Args:
            text: Text to convert
            output_path: Output file path (mp3 format)
            lang: Language code (e.g., 'en', 'es', 'fr')
            tld: Top-level domain for accent (e.g., 'com', 'co.uk', 'com.au')
            slow: Slow speech mode
        """
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        tts = self._gtts.gTTS(text=text, lang=lang, tld=tld, slow=slow)
        tts.save(output_path)

        logger.info(f"[gTTS] Generated speech saved to {output_path}")
        return output_path

    def list_voices(self) -> List[Dict[str, Any]]:
        """List available languages (gTTS uses languages, not voices)"""
        from gtts.lang import tts_langs
        langs = tts_langs()
        return [
            {'id': code, 'name': name, 'type': 'language'}
            for code, name in langs.items()
        ]


class EdgeTTSEngine(BaseTTSEngine):
    """Microsoft Edge TTS (online, free, high quality)"""

    def __init__(self):
        try:
            import edge_tts
            self._edge_tts = edge_tts
        except ImportError:
            raise ImportError("edge-tts not installed. Run: pip install edge-tts")

    @property
    def name(self) -> str:
        return "edge-tts"

    def synthesize(
        self,
        text: str,
        output_path: str,
        voice: str = "en-US-AriaNeural",
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
        **kwargs
    ) -> str:
        """
        Synthesize speech using Microsoft Edge TTS

        Args:
            text: Text to convert
            output_path: Output file path (mp3 format)
            voice: Voice name (e.g., 'en-US-AriaNeural', 'en-GB-SoniaNeural')
            rate: Speech rate adjustment (e.g., '+10%', '-20%')
            volume: Volume adjustment (e.g., '+10%', '-20%')
            pitch: Pitch adjustment (e.g., '+10Hz', '-20Hz')
        """
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        async def _synthesize():
            communicate = self._edge_tts.Communicate(
                text,
                voice,
                rate=rate,
                volume=volume,
                pitch=pitch
            )
            await communicate.save(output_path)

        asyncio.run(_synthesize())

        logger.info(f"[edge-tts] Generated speech saved to {output_path}")
        return output_path

    def list_voices(self) -> List[Dict[str, Any]]:
        """List available Edge TTS voices"""
        async def _list():
            voices = await self._edge_tts.list_voices()
            return voices

        voices = asyncio.run(_list())
        return [
            {
                'id': v['ShortName'],
                'name': v['FriendlyName'],
                'locale': v['Locale'],
                'gender': v['Gender'],
            }
            for v in voices
        ]


class MultiTTSClient:
    """Unified client for multiple TTS engines"""

    ENGINES = {
        TTSEngine.GTTS: GTTSEngine,
        TTSEngine.EDGE_TTS: EdgeTTSEngine,
    }

    def __init__(self, default_engine: TTSEngine = TTSEngine.EDGE_TTS):
        self.default_engine = default_engine
        self._engine_instances: Dict[TTSEngine, BaseTTSEngine] = {}

    def get_engine(self, engine: Optional[TTSEngine] = None) -> BaseTTSEngine:
        """Get or create an engine instance"""
        engine = engine or self.default_engine

        if engine not in self._engine_instances:
            engine_class = self.ENGINES.get(engine)
            if not engine_class:
                raise ValueError(f"Unknown engine: {engine}")
            self._engine_instances[engine] = engine_class()

        return self._engine_instances[engine]

    def synthesize(
        self,
        text: str,
        output_path: str,
        engine: Optional[TTSEngine] = None,
        **kwargs
    ) -> str:
        """
        Synthesize speech using specified engine

        Args:
            text: Text to convert to speech
            output_path: Output file path
            engine: TTS engine to use
            **kwargs: Engine-specific options
        """
        tts_engine = self.get_engine(engine)
        return tts_engine.synthesize(text, output_path, **kwargs)

    def list_voices(self, engine: Optional[TTSEngine] = None) -> List[Dict[str, Any]]:
        """List voices/models for specified engine"""
        tts_engine = self.get_engine(engine)
        return tts_engine.list_voices()

    @staticmethod
    def available_engines() -> List[str]:
        """List all available engine names"""
        return [e.value for e in TTSEngine]
