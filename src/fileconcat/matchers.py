from __future__ import annotations

import os
import re
from typing import Callable

from fileconcat.config import MatchMode


PathIncludeFn = Callable[[str, str], bool]
PathExcludeFn = Callable[[str, str], bool]


def make_path_matchers(
    pattern: str | None,
    exclude_pattern: str | None,
    match_mode: MatchMode,
) -> tuple[PathIncludeFn, PathExcludeFn]:
    """
    Возвращает две функции:
      - include(rel_path_str, name) -> bool
      - exclude(rel_path_str, name) -> bool
    Логика соответствует твоему последнему монолитному скрипту.
    """
    include_regex = None
    exclude_regex = None

    if pattern and match_mode == "regex":
        include_regex = re.compile(pattern)
    if exclude_pattern and match_mode == "regex":
        exclude_regex = re.compile(exclude_pattern)

    def include(rel_path: str, name: str) -> bool:
        if not pattern:
            return True
        if match_mode == "regex":
            return bool(include_regex.search(rel_path))
        elif match_mode == "substring":
            return pattern in rel_path or pattern in name
        else:  # exact
            return rel_path == pattern or name == pattern

    def exclude(rel_path: str, name: str) -> bool:
        if not exclude_pattern:
            return False
        if match_mode == "regex":
            return bool(exclude_regex.search(rel_path))
        elif match_mode == "substring":
            return exclude_pattern in rel_path or exclude_pattern in name
        else:  # exact
            return rel_path == exclude_pattern or name == exclude_pattern

    return include, exclude


class ContentMatcher:
    """
    Обёртка над логикой проверки содержимого файла.

    check(file_path_str, name) -> (include_ok, excluded, had_warning)
    """

    def __init__(
        self,
        content_pattern: str | None,
        content_exclude_pattern: str | None,
        match_mode: MatchMode,
        batch_size: int,
        binary_exts: set[str],
    ) -> None:
        self.content_pattern = content_pattern
        self.content_exclude_pattern = content_exclude_pattern
        self.match_mode = match_mode
        self.batch_size = max(1, batch_size)
        self.binary_exts = binary_exts

        self.content_include_regex = None
        self.content_exclude_regex = None

        if content_pattern and match_mode == "regex":
            self.content_include_regex = re.compile(content_pattern)
        if content_exclude_pattern and match_mode == "regex":
            self.content_exclude_regex = re.compile(content_exclude_pattern)

        self._enabled = bool(content_pattern or content_exclude_pattern)

    def check(self, file_path_str: str, name: str) -> tuple[bool, bool, bool]:
        """
        Возвращает:
          include_ok: прошёл ли файл по include-условию (если оно есть)
          excluded:   исключён ли файл по exclude-условию (если оно есть)
          had_warning: возникла ли ошибка чтения
        """
        # Если нет ни include, ни exclude по контенту — всегда ОК
        if not self._enabled:
            return True, False, False

        ext = os.path.splitext(name)[1].lower()
        is_binary_like = ext in self.binary_exts

        # Если нужен обязательно include-паттерн, но файл бинарный — можно сразу отсечь
        if self.content_pattern and is_binary_like:
            return False, False, False

        content_matches = False
        content_excluded = False
        had_warning = False

        # Если бинарный и только exclude-паттерн — считаем, что он не исключён, и не читаем файл
        if not is_binary_like:
            try:
                with open(file_path_str, "r", encoding="utf-8", errors="ignore") as f:
                    batch: list[str] = []

                    def process_batch(batch_text: str) -> bool:
                        nonlocal content_matches, content_excluded
                        if not batch_text:
                            return False

                        # include content pattern
                        if self.content_pattern and not content_matches:
                            if self.match_mode == "regex":
                                if self.content_include_regex.search(batch_text):
                                    content_matches = True
                            else:  # exact / substring => подстрока
                                if self.content_pattern in batch_text:
                                    content_matches = True

                        # exclude content pattern
                        if self.content_exclude_pattern and not content_excluded:
                            if self.match_mode == "regex":
                                if self.content_exclude_regex.search(batch_text):
                                    content_excluded = True
                            else:
                                if self.content_exclude_pattern in batch_text:
                                    content_excluded = True

                        # early stop logic
                        if content_excluded:
                            return True
                        if self.content_pattern and content_matches and not self.content_exclude_pattern:
                            return True
                        return False

                    for line in f:
                        batch.append(line)
                        if len(batch) >= self.batch_size:
                            if process_batch("".join(batch)):
                                break
                            batch = []

                    # обработать хвост
                    if batch and not (
                        content_excluded or
                        (self.content_pattern and content_matches and not self.content_exclude_pattern)
                    ):
                        process_batch("".join(batch))

            except Exception:
                had_warning = True
                # В случае ошибки чтения считаем, что файл не проходит фильтр
                return False, False, had_warning

        # финальная проверка
        if self.content_pattern and not content_matches:
            return False, False, had_warning
        if self.content_exclude_pattern and content_excluded:
            return False, True, had_warning

        return True, False, had_warning


def make_content_matcher(
    content_pattern: str | None,
    content_exclude_pattern: str | None,
    match_mode: MatchMode,
    batch_size: int,
    binary_exts: set[str],
) -> ContentMatcher:
    return ContentMatcher(
        content_pattern=content_pattern,
        content_exclude_pattern=content_exclude_pattern,
        match_mode=match_mode,
        batch_size=batch_size,
        binary_exts=binary_exts,
    )
