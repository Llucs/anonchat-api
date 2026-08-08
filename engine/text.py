"""Content assembly helpers shared between the engine and the wrapper.

ChatGPT's anonymous backend streams response text in two shapes:

1. **Full snapshots** - events whose ``v.message.content.parts`` carry the
   *entire* text produced so far for the assistant message.
2. **Deltas** - ``append``/``patch`` operations that extend the current text.

Merging both without deduplication produces duplicated or truncated output
(depending on the order the backend emits the snapshot relative to the deltas).

``TextAssembler`` applies these rules:

- an empty accumulator is initialized with the first chunk;
- a full snapshot that is a stale copy of what we already hold is skipped;
- a full snapshot that supersedes the accumulated text replaces it (or starts
  a brand new message);
- a delta entirely contained in the accumulated text is skipped (the backend
  periodically re-emits whole content);
- everything else is appended.

``text()`` returns the whole accumulated response (non-streaming path),
``suffix()`` returns only the part not yet handed out (streaming path, so
clients receive strict deltas and never duplicates).
"""


class TextAssembler:
    __slots__ = ('_parts', '_joined', '_emitted')

    def __init__(self):
        self._parts = []
        self._joined = ''
        self._emitted = 0

    def absorb(self, chunk, full_snapshot: bool = False) -> None:
        if not chunk:
            return
        if not self._parts:
            self._parts.append(chunk)
            self._joined = chunk
            return
        if full_snapshot:
            if self._joined.startswith(chunk):
                # Stale full copy - we already contain (at least) this text.
                return
            if chunk.startswith(self._joined):
                # The snapshot carries the current text plus more - replace.
                self._parts[:] = [chunk]
                self._joined = chunk
                return
            # Snapshot unrelated to what we have: a new/replacement message.
            self._parts[:] = [chunk]
            self._joined = chunk
            return
        if len(chunk) <= len(self._joined) and chunk in self._joined:
            return
        self._parts.append(chunk)
        self._joined += chunk

    def text(self) -> str:
        return self._joined

    def suffix(self) -> str:
        """Return the portion of the accumulated text not yet handed out."""
        if self._emitted >= len(self._joined):
            return ''
        new = self._joined[self._emitted:]
        self._emitted = len(self._joined)
        return new
