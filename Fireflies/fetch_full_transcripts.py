#!/usr/bin/env python3
"""
Скачивает полные транскрипты из Fireflies через MCP/API и сохраняет в .txt.
Запуск: нужен доступ к Fireflies (например, через Cursor с MCP).
ID встреч — в начале каждого .md в папке Fireflies.
"""
from pathlib import Path

# ID из файлов Fireflies (ключ — имя без _transcript.txt)
TRANSCRIPT_IDS = {
    "2026-01-30_19-10_Untitled_Marina": "01KG7TQZAV4P4X8F2QTTDD579Z",
    "2026-01-30_15-01_Разработка": "01KG7PS5J1RFG8SBH6AX4X2MCQ",
    "2026-01-30_13-33_Григорий_техника": "01KG7HPVK13Q6K3EE0FVXZQ7H9",
    "2026-01-30_12-04_Контент-завод": "01KG7CMP7A5NPQTM2058A3B965",
    "2026-01-29_16-02_Untitled_карточки": "01KG4XJS27TQK82JKAKYVNCAF5",
    "2026-01-29_15-04_Untitled_капли": "01KG4T8C620K9ETHT84VZQ8H8H",
    "2026-01-28_18-19_раздачи": "01KG2XA25CMS06MJ3K0G7KBE48",
    "2026-01-28_13-12_Надя": "01KG2BPZCMAFYVJ3S2NN5SKC6C",
    "2026-01-27_17-02_Станислав_Раздачи": "01KG06GCHGKBW9DE2CG971FA1B",
    "2026-01-27_15-40_техника": "01KG01SBSW2VJAMC1P36F9JJDT",
    "2026-01-24_12-00_Untitled_P2P": "01KFQKQ5KGQSN7RPXSN1MAYB0H",
}

DIR = Path(__file__).resolve().parent


def format_sentences(sentences: str) -> str:
    """Speaker: text -> **Speaker:** text."""
    lines = []
    for line in sentences.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if ": " in line:
            speaker, _, text = line.partition(": ")
            lines.append(f"**{speaker}:** {text}")
        else:
            lines.append(line)
    return "\n\n".join(lines)


def save_transcript(prefix: str, sentences: str) -> Path:
    out = DIR / f"{prefix}_transcript.txt"
    out.write_text(format_sentences(sentences), encoding="utf-8")
    return out


if __name__ == "__main__":
    print("Транскрипты нужно получать через Fireflies MCP (fireflies_get_transcript).")
    print("ID встреч:", list(TRANSCRIPT_IDS.values()))
    print("После получения Sentences вызовите save_transcript(prefix, sentences).")
