"""Edit known TOML/JSONC paths without rewriting unrelated configuration."""

from __future__ import annotations

import json
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

import json5
import tomlkit
from json5.dumper import ModelDumper
from json5.loader import ModelLoader
from json5.model import JSONObject


def _dump(value: Any) -> str:
    # The public annotation excludes json-five's own stateful model dumper.
    dumper: Any = ModelDumper()
    return json5.dumps(value, dumper=dumper)


class ConfigDocument:
    """A round-trip document. Paths are key sequences, never dotted strings."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.original = path.read_bytes()
        text = self.original.decode("utf-8-sig")
        self.newline = "\r\n" if "\r\n" in text else "\n"
        text = text.replace("\r\n", "\n")
        self.toml = path.suffix == ".toml"
        self.tree: Any = (
            tomlkit.parse(text)
            if self.toml
            else json5.loads(text, loader=ModelLoader())
        )
        if not self.toml:
            self._check_keys(self.tree.value)

    @staticmethod
    def _check_keys(node: Any) -> None:
        if isinstance(node, JSONObject):
            keys = [str(json5.loads(_dump(key))) for key in node.keys]
            if len(keys) != len(set(keys)):
                raise ValueError(
                    "Duplicate JSON configuration keys require manual review"
                )
            for child in node.values:
                ConfigDocument._check_keys(child)
        elif hasattr(node, "values"):
            for child in node.values:
                ConfigDocument._check_keys(child)

    def _parent(self, path: list[str], *, create: bool = False) -> tuple[Any, str]:
        if not path or any(not isinstance(part, str) or not part for part in path):
            raise ValueError("Configuration paths must contain non-empty keys")
        node = self.tree if self.toml else self.tree.value
        for key in path[:-1]:
            if self.toml:
                if not isinstance(node, MutableMapping):
                    raise ValueError("A configuration parent is not a table")
                if key not in node:
                    if not create:
                        raise KeyError(key)
                    node[key] = tomlkit.table()
                node = node[key]
            else:
                if not isinstance(node, JSONObject):
                    raise ValueError("A configuration parent is not an object")
                index = self._index(node, key)
                if index is None:
                    if not create:
                        raise KeyError(key)
                    fragment = json5.loads(
                        json.dumps({key: {}}), loader=ModelLoader()
                    ).value
                    node.keys.append(fragment.keys[0])
                    node.values.append(fragment.values[0])
                    index = len(node.keys) - 1
                node = node.values[index]
        return node, path[-1]

    @staticmethod
    def _index(node: Any, key: str) -> int | None:
        if not isinstance(node, JSONObject):
            raise ValueError("A configuration parent is not an object")
        for index, candidate in enumerate(node.keys):
            name = json5.loads(_dump(candidate))
            if str(name) == key:
                return index
        return None

    def has(self, path: list[str]) -> bool:
        try:
            self.get(path)
        except KeyError:
            return False
        return True

    def get(self, path: list[str]) -> Any:
        parent, key = self._parent(path)
        if self.toml:
            value = parent[key]
            return value.unwrap() if hasattr(value, "unwrap") else value
        index = self._index(parent, key)
        if index is None:
            raise KeyError(key)
        return json5.loads(_dump(parent.values[index]))

    def set(self, path: list[str], value: Any) -> None:
        parent, key = self._parent(path, create=True)
        if self.toml:
            parent[key] = value
            return
        index = self._index(parent, key)
        replacement = json5.loads(json.dumps(value), loader=ModelLoader()).value
        if index is None:
            fragment = json5.loads(json.dumps({key: value}), loader=ModelLoader()).value
            parent.keys.append(fragment.keys[0])
            parent.values.append(fragment.values[0])
        else:
            old = parent.values[index]
            replacement.wsc_before = old.wsc_before
            replacement.wsc_after = old.wsc_after
            parent.values[index] = replacement

    def remove(self, path: list[str]) -> None:
        parent, key = self._parent(path)
        if self.toml:
            del parent[key]
        else:
            index = self._index(parent, key)
            if index is None:
                raise KeyError(key)
            parent.keys.pop(index)
            parent.values.pop(index)

    def move(self, source: list[str], destination: list[str]) -> None:
        old_parent, old_key = self._parent(source)
        new_parent, new_key = self._parent(destination, create=True)
        if self.toml:
            item = old_parent.item(old_key)
            del old_parent[old_key]
            new_parent[new_key] = item
        else:
            index = self._index(old_parent, old_key)
            if index is None:
                raise KeyError(old_key)
            key, value = old_parent.keys.pop(index), old_parent.values.pop(index)
            replacement = json5.loads(
                json.dumps({new_key: None}), loader=ModelLoader()
            ).value.keys[0]
            replacement.wsc_before = key.wsc_before
            replacement.wsc_after = key.wsc_after
            new_parent.keys.append(replacement)
            new_parent.values.append(value)

    def content(self) -> bytes:
        text = tomlkit.dumps(self.tree) if self.toml else _dump(self.tree)
        # Validate model edits before a byte can reach the user's project.
        if self.toml:
            tomlkit.parse(text)
        elif self.path.suffix == ".json" and self.path.name == "package.json":
            json.loads(text)
        else:
            json5.loads(text)
        if self.newline == "\r\n":
            text = text.replace("\n", "\r\n")
        prefix = b"\xef\xbb\xbf" if self.original.startswith(b"\xef\xbb\xbf") else b""
        return prefix + text.encode("utf-8")

    def write(self) -> None:
        self.path.write_bytes(self.content())
