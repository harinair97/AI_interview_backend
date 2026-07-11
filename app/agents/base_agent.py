from typing import Protocol, TypeVar

InputT = TypeVar("InputT", contravariant=True)
OutputT = TypeVar("OutputT", covariant=True)


class Agent(Protocol[InputT, OutputT]):
    """Small provider-independent contract used by workflow nodes."""

    def invoke(self, agent_input: InputT) -> OutputT: ...
